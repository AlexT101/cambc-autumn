"""Live-ladder scrim job: unranked match groups against chosen teams, on a frozen set of maps and sides.
Requires `cambc login`. Data in research/ladder-scrims-2026-11-06/ (README.md, SET.md); replays in replays/ladder-scrims/.

    py tools/ladder_scrims.py plan --version 78 --sets core,ext --opps fish,mite      # append set tasks
    py tools/ladder_scrims.py plan --version 78 --sets core --opps vvvvv --one-side   # calibration: one side per map
    py tools/ladder_scrims.py plan --version 78 --repeat fish,mite                    # determinism: rerun ref groups
    setsid nohup py tools/ladder_scrims.py run >> research/ladder-scrims-2026-11-06/data/run.log 2>&1 &
    py tools/ladder_scrims.py status        # tasks, in-flight groups, quota
    py tools/ladder_scrims.py report [--version 78] [--by map|side|purpose]

A task is one five-game group: our submission version, an opponent, five (map, side) games, a pin and a priority.
`run` creates every pending task whose version is live, back to back, as far as the team's rolling quota (`cambc
match-groups quota`, 100 groups an hour since 2026-11-07) has room beyond `--reserve` (tasks of priority >= 100 may use
it), and looks again every `--pace` seconds, so quota that frees up is used at once. API requests have no proactive
pacing; server rate-limit responses are retried with backoff. It never switches the
live submission: tasks of another version wait (submit or `cambc submissions activate N` to run them). Pins: `ref`
plays the opponent's bot from the first group queued against it under that ref name (refs.json), usable once that
group has played, so every version meets the same opponent bot; `none` plays its current.
State is append-only jsonl, so `run` resumes where it stopped; it exits after `--max-errors` failures in a row.
The platform binds our bot to a group when the group is created, to the version *selected* then (2026-11-08: a group
created at live 93 / selected 94 played v94; 2026-11-12: a v117 group whose matches were all still queued when v118
was selected played v117). So `run` creates only while live == selected, labels a group's games with that version, and
re-reads both every --recheck creates and after each pass, all under live_lock (the scheduler switches under it too).
A switch seen at a re-read marks only the groups created since the previous read `suspect` (they may have bound to the
new selection); games() leaves suspect groups out. Groups in flight at a switch are unaffected."""

import argparse
from contextlib import contextmanager, nullcontext
from ladder_coordination import control_priority, live_lock, probe_active, wait_for_control
import fcntl
import hashlib
import json
import math
import os
from pathlib import Path
import re
import queue
import subprocess
import sys
import threading
import time
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "research" / "ladder-scrims-2026-11-06" / "data"
REPLAYS = ROOT / "replays" / "ladder-scrims"
MY_TEAM = "547efb5b-57e5-4355-8501-3b331f506d62"
UUID = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}")
DONE = {"finished", "failed", "error", "cancelled", "canceled"}
TEAMS = {  # short names for --opps; any team id also works
    "mite": ("ee83f5e5-bcad-4923-86b4-b79ea6083d2e", "Mite"),
    "fish": ("1890540d-1ffc-4847-adbf-d0d08772f268", "Intercontinental Fish"),
    "vvvvv": ("a4350547-b7a1-47b1-9031-4f7f084ad0d8", "Vvvvv @  2FA (Univardisty)"),
    "adastra": ("de0b1e3c-39fb-473c-8244-61c1133ad612", "Ad Astra"),
    "neet": ("882106d4-9deb-40cc-9d5c-8522c1d32129", "NEETCoders"),
    "cats": ("285f4eb5-e97f-4ea4-93c5-19e1590a1e5a", "BattleCats"),
}
CHAMPS = ["Ryth", "Vesper Vale", "Vendetta", "Cassi & Issac", "Stellar", "Prism", "Marcella", "Willow", "Ren", "Varg",
          "Tavi", "Heart of Ruin"]


def now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def log(msg):
    print(f"{now()} {msg}", flush=True)


def read_jsonl(path):
    if not path.exists():
        return []
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            try:
                out.append(json.loads(line))
            except ValueError:
                pass  # a line cut short by a crash
    return out


_APPEND = threading.Lock()  # `run` appends from its collector thread too


def append_jsonl(path, row):
    path.parent.mkdir(parents=True, exist_ok=True)
    with _APPEND, path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")


class CambcError(RuntimeError):
    pass


class ControlReadLimited(CambcError):
    def __init__(self, command, retry_after):
        super().__init__(f'{command}: HTTP 429 before creates')
        self.retry_after = retry_after


_READ_RETRY = threading.local()


@contextmanager
def defer_control_reads(enabled):
    previous = getattr(_READ_RETRY, 'defer', False)
    _READ_RETRY.defer = enabled
    try:
        yield
    finally:
        _READ_RETRY.defer = previous


def cambc(*args, timeout=300, retries=4, limited_retries=8, spaced=True):
    """Unpaced CLI calls; control priority only suppresses competing background requests.

    spaced remains accepted for callers that distinguish local CLI operations.
    """
    command = args[:2]
    control = bool(args) and (args[0] == 'submissions' or command in
                             (('match-groups', 'quota'), ('match-groups', 'create')))
    background = command in (('matches', 'list'), ('matches', 'download'), ('matches', 'summary'),
                             ('match-groups', 'show'))
    with control_priority(DATA) if control else nullcontext(None) as renew:
        return _cambc(args, timeout, retries, limited_retries, renew, background)


def _cambc(args, timeout, retries, limited_retries, renew, background):
    attempt = limited = 0
    while True:
        if renew:
            renew()
        elif background:
            wait_for_control(DATA)
        try:
            r = subprocess.run(["cambc", *args], capture_output=True, text=True, encoding="utf-8", errors="replace",
                               timeout=timeout)
        except subprocess.TimeoutExpired:
            if attempt == retries:
                raise CambcError(f"cambc {' '.join(args[:3])}: timed out")
            attempt += 1
            time.sleep(30)
            continue
        out = r.stdout + r.stderr
        wait = re.search(r"retry after (\d+) seconds", out)
        if r.returncode == 0:
            return r.stdout
        status = re.search(r'HTTP\s+(4\d\d)\b', out)
        if (args[:2] == ('match-groups', 'create') and status and status.group(1) != '429'
                and re.search(r'quota|limit', out, re.I)):
            # A yielded quota snapshot is advisory: a definite refusal must end the pass, not monopolize the lock.
            raise CambcError(f"cambc {' '.join(args[:3])}: {out.strip()[-400:]}")
        if (getattr(_READ_RETRY, 'defer', False)
                and args[:2] in (('submissions', 'list'), ('match-groups', 'quota'))
                and re.search(r'HTTP\s+429\b', out)):
            raise ControlReadLimited(' '.join(args[:2]), int(wait.group(1)) if wait else 60)
        if wait and limited < limited_retries:
            limited += 1
            time.sleep(min(60, int(wait.group(1)) * 2 ** (limited - 1)))
            continue
        if attempt == retries:
            raise CambcError(f"cambc {' '.join(args[:3])}: {out.strip()[-400:]}")
        attempt += 1
        time.sleep(15 * attempt)


def quota():
    return json.loads(cambc("match-groups", "quota", "--json"))


def live_version():
    """(live, selected) submission versions from `cambc submissions list`."""
    out = cambc("submissions", "list")
    m = re.search(r"Live:\s*(\d+)\s+Selected:\s*(\d+)", out)
    if not m:
        raise CambcError(f"cannot read the live version: {out[:200]}")
    return int(m.group(1)), int(m.group(2))


def load_set(name):
    return json.loads((DATA / f"set-{name}.json").read_text(encoding="utf-8"))


def team_of(key):
    if key in TEAMS:
        return TEAMS[key]
    if UUID.fullmatch(key):
        return key, key
    sys.exit(f"unknown team {key!r}: use one of {', '.join(TEAMS)} or a team id")


# ---------------------------------------------------------------- planning

def set_groups(maps, filler, one_side=False, flip=False):
    """Five-game groups; a group needs five different maps. Each block of five maps is played as sides
    a,b,a,b,a and, unless one_side, again as b,a,b,a,b, so every map gets both sides against the same bot.
    A short last block is filled with the first set maps not in it (marked filler)."""
    groups = []
    for i in range(0, len(maps), 5):
        block = [dict(m) for m in maps[i:i + 5]]
        names = {m["name"] for m in block}
        block += [dict(m, filler=True) for m in filler if m["name"] not in names][:5 - len(block)]
        patterns = [(i // 5 + flip) % 2] if one_side else [0, 1]
        for p in patterns:
            groups.append([{"map": m["name"], "map_id": m["id"], "side": "ab"[(j + p) % 2],
                            **({"filler": True} if m.get("filler") else {})} for j, m in enumerate(block)])
    return groups


def cmd_plan(args):
    tasks = read_jsonl(DATA / "tasks.jsonl")
    have = {t["id"] for t in tasks}
    st = load_set(args.set)
    new = []
    if args.maps:
        # An ad-hoc map list (names from any set file): both sides of each, in five-game groups.
        known = {m["name"]: m for f in sorted(DATA.glob("set-*.json")) for part in json.loads(f.read_text()).values()
                 if isinstance(part, list) for m in part if isinstance(m, dict) and "id" in m}
        names = [n.strip() for n in args.maps.split(",") if n.strip()]
        missing = [n for n in names if n not in known]
        if missing or len(set(names)) < 5:
            sys.exit(f"--maps needs five or more known maps; unknown: {missing}")
        st = dict(st, maps=[known[n] for n in dict.fromkeys(names)])
        args.sets = "maps"
        args.set = "m" + hashlib.sha1(",".join(sorted(set(names))).encode()).hexdigest()[:6]
    opps = [team_of(o) for o in args.opps.split(",")] if args.opps else []
    if args.repeat:
        by_id = {t["id"]: t for t in tasks}
        refs_tasks = {e["opp_id"]: by_id[e["task"]] for e in read_jsonl(DATA / "events.jsonl")
                      if e["ev"] == "created" and e.get("is_ref") and e.get("refset") == args.refset}
        for o in args.repeat.split(","):
            tid, name = team_of(o)
            base = refs_tasks.get(tid)
            if not base:
                sys.exit(f"no ref task against {name} under ref {args.refset} yet")
            k = sum(t["id"].startswith(f"v{args.version}-repeat-{o}-") for t in tasks) + 1
            new.append(dict(base, id=f"v{args.version}-repeat-{o}-{k}", version=args.version, purpose="repeat",
                            pin="ref", is_ref=False, priority=args.priority or 60, planned=now()))
    for part in args.sets.split(",") if args.sets else []:
        maps = st[part]
        for j, (tid, name) in enumerate(opps):
            short = next((k for k, v in TEAMS.items() if v[0] == tid), tid[:8])
            purpose = args.purpose or ("calib" if args.one_side else "set")
            flip = (j % 2 == 1) != args.flip
            tag = ("-1s" + ("f" if args.flip else "")) if args.one_side else ""
            # r1's ids predate ref sets; later sets are tagged so one version can play several.
            tag += f"-{args.refset}" if args.refset != "r1" else ""
            groups = set_groups(maps, maps if part == "maps" else st["core"], args.one_side, flip=flip)
            for i, g in enumerate(groups[:args.groups] if args.groups else groups, 1):
                new.append({"id": f"v{args.version}-{args.set}{part}{tag}-{short}-{i:02d}",
                            "version": args.version, "set": args.set, "part": part, "purpose": purpose,
                            "opp_id": tid, "opp_name": name, "pin": args.pin, "refset": args.refset,
                            "games": g, "priority": args.priority or {"core": 50, "ext": 30, "maps": 95}.get(part, 20),
                            "order": i, "planned": now()})
    # Interleave opponents within a priority so a partial run stays balanced.
    new.sort(key=lambda t: (-t["priority"], t.get("order", 0)))
    added = 0
    for t in new:
        if t["id"] in have:
            continue
        append_jsonl(DATA / "tasks.jsonl", t)
        added += 1
    print(f"{added} tasks added ({len(new) - added} already planned), {5 * added} games")


# ---------------------------------------------------------------- state

def state():
    return state_ex()[:5]


def state_ex():
    """state() plus the groups whose matches are over (played or finished events; collection may lag)."""
    tasks = read_jsonl(DATA / "tasks.jsonl")
    events = read_jsonl(DATA / "events.jsonl")
    created = {e["task"]: e for e in events if e["ev"] == "created"}
    finished = {e["group"]: e for e in events if e["ev"] == "finished"}
    dropped = {e["task"] for e in events if e["ev"] == "dropped"}
    played = {e["group"] for e in events if e["ev"] in ("played", "finished")}
    refs = {}
    for e in events:
        if e["ev"] == "created" and e.get("is_ref"):
            refs.setdefault((e["refset"], e["opp_id"]), e["group"])
    return tasks, created, finished, dropped, refs, played


def pending_tasks(tasks, created, dropped):
    return [t for t in tasks if t["id"] not in created and t["id"] not in dropped]


# ---------------------------------------------------------------- results

def summary_fields(raw, side):
    """Rounds, tributed gems, kills and earned gold per side from a binary match summary."""
    try:
        d = json.loads(cambc("summary", str(raw), "-o", "-", timeout=120, spaced=False))   # converts locally
    except (CambcError, ValueError):
        return {}
    us, them = ("teamA", "teamB") if side == "a" else ("teamB", "teamA")
    gems = {t["team"]: float(t["submittedGems"]) for t in d.get("teams", [])}
    totals = {}
    for tl in d.get("championTimelines", []):
        if tl["metric"] in ("kills", "earnedGold") and tl["runs"]:
            key = (tl["owner"]["team"], tl["metric"])
            totals[key] = totals.get(key, 0) + float(tl["runs"][-1]["value"])
    m = d.get("match", {})
    return {"rounds": m.get("roundsCompleted"), "outcome": m.get("outcome"), "seed": m.get("seed"),
            "engine": m.get("engineVersion"), "engine_hash": (m.get("engineBuildHash") or "")[:12],
            "our_gems": gems.get(us), "opp_gems": gems.get(them),
            "our_kills": totals.get((us, "kills")), "opp_kills": totals.get((them, "kills")),
            "our_gold": totals.get((us, "earnedGold")), "opp_gold": totals.get((them, "earnedGold")),
            "draft": [f"{c['team'][-1]}:{c['champion']}" for c in d.get("roster", {}).get("draft", [])]}


def collect(task, ev, detail):
    """Writes one games.jsonl row per finished game and downloads its replay bundle and summary."""
    try:
        outcome_versions = json.loads((DATA / 'OUTCOME-ONLY-VERSIONS.json').read_text())
    except (OSError, ValueError):
        outcome_versions = []
    outcome_only = (isinstance(outcome_versions, list) and task['version'] in outcome_versions
                    and ev['live'] == task['version'] and task.get('purpose') == 'set'
                    and task.get('pin') == 'ref')
    try:
        wins_only_tasks = json.loads((DATA / 'WINS-ONLY-TASKS.json').read_text())
    except (OSError, ValueError):
        wins_only_tasks = []
    wins_only = (isinstance(wins_only_tasks, list) and task['id'] in wins_only_tasks
                 and ev['live'] == task['version'] and task.get('purpose') == 'set'
                 and task.get('pin') == 'ref')
    folder = REPLAYS / ev["group"]
    folder.mkdir(parents=True, exist_ok=True)
    rows = []
    for m in sorted(detail["matches"], key=lambda m: m["position"]):
        us = next((t for t in m["teams"] if t["teamId"] == MY_TEAM), None)
        them = next((t for t in m["teams"] if t["teamId"] != MY_TEAM), None)
        game = task["games"][m["position"] - 1] if m["position"] - 1 < len(task["games"]) else {}
        row = {"version": ev["live"], "task": task["id"], "purpose": task["purpose"], "set": task.get("set"),
               "part": task.get("part"), "filler": bool(game.get("filler")), "group": ev["group"],
               "source_group": ev.get("source_group"), "refset": task.get("refset"), "pin": task["pin"],
               "match": m["matchId"], "position": m["position"], "map": m["map"], "map_id": m["mapId"],
               "side": us["side"] if us else game.get("side"), "opp_id": task["opp_id"],
               "opp_name": them["name"] if them else task["opp_name"], "status": m["status"],
               "result": us.get("result") if us else None, "end_reason": m.get("endReason"),
               "our_picks": [CHAMPS[i] if 0 <= i < len(CHAMPS) else i for i in (us or {}).get("draftPicks", [])],
               "opp_picks": [CHAMPS[i] if 0 <= i < len(CHAMPS) else i for i in (them or {}).get("draftPicks", [])],
               "created": ev["at"], "finished": m.get("finishedAt")}
        if m["status"] == "finished" and outcome_only:
            # Host-loss selection needs outcomes and drafts; these are not replay-source or detector records.
            row.update(collection='outcome_only', replay=None)
        elif m["status"] == "finished" and wins_only and row['result'] == 'loss':
            # Only explicit losses may be omitted: unknown outcomes can still be winning book sources.
            bundle = folder / f"{m['position']}-{m['map']}.zip"
            row.update(collection='loss_outcome_only',
                       replay=str(bundle.relative_to(ROOT)) if bundle.exists() else None)
        elif m["status"] == "finished":
            stem = f"{m['position']}-{m['map']}"
            bundle, raw = folder / f"{stem}.zip", folder / f"{stem}.summary.bin"
            for path, what in ((bundle, "download"), (raw, "summary")):
                if not path.exists():
                    try:
                        cambc("matches", what, m["matchId"], "-o", str(path))
                    except CambcError as e:
                        log(f"warning: {what} {m['matchId']}: {e}")
            if raw.exists():
                row.update(summary_fields(raw, row["side"]))
            row["replay"] = str(bundle.relative_to(ROOT)) if bundle.exists() else None
        rows.append(row)
    for r in rows:
        append_jsonl(DATA / "games.jsonl", r)
    return rows


def group_detail(gid):
    return json.loads(cambc("match-groups", "show", gid, "--json"))


def group_done(detail):
    ms = detail.get("matches") or []
    return len(ms) >= 5 and all(m["status"] in DONE for m in ms)


# ---------------------------------------------------------------- run

def held_tasks():
    """Task ids the live scheduler holds back for now (data/HOLD-TASKS.json; e.g. control groups until candidates
    have played). They stay pending, not dropped."""
    try:
        return set(json.loads((DATA / "HOLD-TASKS.json").read_text()))
    except (OSError, ValueError):
        return set()


def create(task, source, retries=2):
    args = ["match-groups", "create", task["opp_id"], "--maps", ",".join(g["map_id"] for g in task["games"]),
            "--sides", ",".join(g["side"] for g in task["games"]), "--json"]
    if source:
        args += ["--source-group", source]
    out = cambc(*args, retries=retries)
    try:
        d = json.loads(out)
    except ValueError:
        d = {}
    for k in ("groupId", "id"):
        if isinstance(d, dict) and isinstance(d.get(k), str) and UUID.fullmatch(d[k]):
            return d[k], out
    if isinstance(d, dict) and isinstance(d.get("group"), dict) and UUID.fullmatch(str(d["group"].get("id", ""))):
        return d["group"]["id"], out
    ids = [i for i in UUID.findall(out) if i != task["opp_id"] and i not in {g["map_id"] for g in task["games"]}]
    if ids:
        return ids[0], out
    raise CambcError(f"no group id in: {out[:300]}")


def groups_over(want, pages=12):
    """The groups of `want` whose five matches are all over, with our results by position ("WLWW?"), from the team's
    unranked match list: 100 matches (20 groups) a call, newest first, against one `match-groups show` a group.
    Stops once every wanted group's five matches were seen or the list ends."""
    seen, cursor = {}, None
    for _ in range(pages):
        args = ["matches", "list", "--team", "me", "--kind", "unranked", "--limit", "100", "--json"]
        d = json.loads(cambc(*args, *(["--cursor", cursor] if cursor else [])))
        for m in d.get("matches") or []:
            if m.get("groupId") in want:
                us = next((t for t in m.get("teams") or [] if t.get("teamId") == MY_TEAM), {})
                seen.setdefault(m["groupId"], {})[m["matchId"]] = (m.get("position") or 0, m["status"],
                                                                   (us.get("result") or "?")[0].upper())
        cursor = d.get("nextCursor")
        if not cursor or not d.get("matches") or all(len(seen.get(g, ())) >= 5 for g in want):
            break
    return {g: "".join(r for _, _, r in sorted(ms.values())) for g, ms in seen.items()
            if len(ms) >= 5 and all(st in DONE for _, st, _ in ms.values())}


def activation_pending():
    try:
        return time.time() - (DATA / 'BATCH').stat().st_mtime < 90
    except FileNotFoundError:
        return False


def cmd_run(args):
    lock = open(DATA / "run.lock", "a+")
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        lock.close()
        sys.exit("another `ladder_scrims.py run` holds the lock")
    lock.seek(0)
    lock.truncate()
    lock.write(str(os.getpid()))
    lock.flush()
    log(f"run: pid {os.getpid()}, reserve {args.reserve}, inflight {args.inflight or 'no cap'}, pace {args.pace}s, "
        f"poll {args.poll}s")
    errors, last_pass, last_poll, no_task = 0, 0.0, 0.0, None
    limited_reads = 0
    waiting_note = None
    seen_ls = None
    # A played group's ten downloads take ten API calls. One collector thread keeps them serial and off the loop
    # (its calls wait while a create pass runs) and writes the finished event after the games, so the scheduler
    # sees a group as uncollected until its games are recorded.
    to_collect, collecting, collected = queue.LifoQueue(), set(), set()   # newest first: the games wanted soonest
    collecting_lock, stopping = threading.Lock(), threading.Event()

    def collector():
        while not stopping.is_set():
            try:
                task, ev = to_collect.get(timeout=1)
            except queue.Empty:
                continue
            try:
                rows = collect(task, ev, group_detail(ev["group"]))
                res = "".join((r["result"] or "?")[0].upper() for r in rows)
                with collecting_lock:
                    # With the event: a loop pass that read the events just before it must not queue the group again.
                    collected.add(ev["group"])
                    append_jsonl(DATA / "events.jsonl", {"ev": "finished", "group": ev["group"], "task": ev["task"],
                                                         "at": now(), "results": res})
                log(f"finished {ev['task']} {ev['group'][:8]}: {res}")
            except Exception as e:  # queued again by the next poll (collect skips files it already has)
                log(f"warning: collect {ev['task']} {ev['group'][:8]}: {e}")
            finally:
                with collecting_lock:
                    collecting.discard(ev["group"])

    threading.Thread(target=collector, daemon=True).start()

    def note(msg):
        nonlocal waiting_note
        if msg != waiting_note:
            log(msg)
            waiting_note = msg

    unconfirmed = []   # groups created since the last live/selected read
    pending_quota = None  # successful advisory read while a pre-create live read is rate-limited

    def check_live(why):
        # A switch between two reads may have bound the groups created between them to the new selection.
        nonlocal seen_ls
        cur = live_version()
        if seen_ls is not None and cur != seen_ls:
            log(f"live/selected changed v{seen_ls[0]}/v{seen_ls[1]} -> v{cur[0]}/v{cur[1]} ({why}): "
                f"{len(unconfirmed)} groups created since the last read marked suspect")
            append_jsonl(DATA / "events.jsonl", {"ev": "live_change", "at": now(), "from": list(seen_ls),
                                                 "to": list(cur), "unconfirmed": [e["group"] for e in unconfirmed]})
            for e in unconfirmed:
                append_jsonl(DATA / "events.jsonl", {"ev": "suspect", "group": e["group"], "task": e["task"],
                                                     "at": now(), "why": f"live/selected {list(seen_ls)} -> {list(cur)}"})
        seen_ls = cur
        unconfirmed.clear()
        return cur

    def runnable(pend, refs, over):
        """Pending tasks that only need the live version and quota, best priority first: (task, source, is_ref).
        A pinned task waits until its ref group has played; the first task of a new (refset, opponent) captures it."""
        held, out = held_tasks(), []
        for t in pend:
            if t["id"] in held:
                continue
            source, is_ref = None, False
            if t["pin"] == "ref":
                ref = refs.get((t["refset"], t["opp_id"]))
                if ref is None:
                    is_ref = True
                elif ref not in over:
                    continue
                else:
                    source = ref
            elif t["pin"] not in ("none", None):
                source = t["pin"]
            out.append((t, source, is_ref))
        out.sort(key=lambda x: -x[0]["priority"])
        return out

    def create_pass(cand, playing):
        """Creates every runnable task the quota has room for, back to back: one quota read and one live read, then
        only creates (the collector's calls wait), re-reading both every --recheck creates so a long burst cannot
        miss a teammate's quota use or a submission switch for long."""
        nonlocal waiting_note, pending_quota
        made = []
        with live_lock(DATA):
            if probe_active(DATA):
                pending_quota = None
                return made
            # Only an empty confirmation window can yield the switch lock on a read-only 429.
            with defer_control_reads(not unconfirmed):
                # Do not spend each newly available API token repeating quota before retrying live_version.
                # Only quota can survive a yielded lock: version/selection must always be read again here.
                q = pending_quota if pending_quota is not None and not unconfirmed else quota()
                pending_quota = None
                qq = q.get("quota") or {}
                used, limit = qq.get("used", 0), qq.get("limit") or 100
                if not q.get("ready", True):
                    note("quota not ready (no live submission?)")
                    return made
                if limit - used - (0 if cand[0][0]["priority"] >= 100 else args.reserve) <= 0:
                    note(f"quota {used}/{limit}, reserve {args.reserve}: waiting (resets {qq.get('resetsAt')})")
                    return made
                try:
                    live, selected = check_live("before create")
                except ControlReadLimited:
                    pending_quota = q
                    raise
            ready = [c for c in cand if c[0]["version"] == live] if selected == live else []
            if not ready:
                note(f"nothing runnable: live v{live}, selected v{selected}, pending versions "
                     f"{sorted({c[0]['version'] for c in cand})}")
                return None   # no task for the live version: the loop looks again later, or when the tasks change
            capturing = set()
            for t, source, is_ref in ready:
                if limit - used - (0 if t["priority"] >= 100 else args.reserve) <= 0:
                    break   # by priority: no later task may use more
                if args.inflight and len(playing) + len(made) >= args.inflight:
                    break
                key = (t.get("refset"), t["opp_id"])
                if is_ref:
                    if key in capturing:
                        continue   # one group captures the pin; the rest follow once it has played
                    capturing.add(key)
                try:
                    gid, out = create(t, source)
                except CambcError as e:
                    msg = str(e)
                    if "HTTP 429" in msg or not re.search(r"HTTP 4\d\d", msg):
                        raise
                    if re.search(r"quota|limit", msg, re.I):
                        log(f"create refused on quota, pass ends: {msg[-200:]}")
                        break
                    # A request the API refuses (4xx, e.g. an unknown map) is dropped; rate limits are retried.
                    append_jsonl(DATA / "events.jsonl", {"ev": "dropped", "task": t["id"], "at": now(),
                                                         "why": msg[-300:]})
                    log(f"dropped {t['id']}: {e}")
                    continue
                used += 1
                ev = {"ev": "created", "task": t["id"], "group": gid, "at": now(), "live": live,
                      "selected": selected, "source_group": source, "opp_id": t["opp_id"],
                      "refset": t.get("refset"), "is_ref": is_ref, "quota_used": used}
                append_jsonl(DATA / "events.jsonl", ev)
                made.append(ev)
                unconfirmed.append(ev)
                log(f"created {t['id']} -> {gid[:8]} (v{live}, quota {used}/{limit}"
                    f"{', ref' if is_ref else ''}{', pinned ' + source[:8] if source else ''})")
                if len(made) % args.recheck == 0:
                    if check_live("during create") != (live, selected):
                        return made
                    qq = quota().get("quota") or {}
                    used, limit = max(used, qq.get("used", used)), qq.get("limit") or limit
            if made:
                check_live("after create")
                waiting_note = None
        return made

    try:
        while True:
            if (DATA / "STOP").exists():
                log("STOP file present: exiting")
                return
            try:
                tasks, created, finished, dropped, refs, over = state_ex()
                by_id = {t["id"]: t for t in tasks}
                with collecting_lock:
                    busy = set(collecting)
                # Created and not yet recorded; `playing` are those whose matches may still run (the cap, a live switch).
                open_groups = [e for e in created.values() if e["group"] not in finished]
                playing = [e for e in open_groups if e["group"] not in over]
                pend = pending_tasks(tasks, created, dropped)
                if not pend and not open_groups:
                    if args.exit_when_done:
                        log("all tasks done: exiting")
                        return
                    time.sleep(args.idle)
                    errors = 0
                    continue
                # Creates first: quota that is free is used before anything else gets the API.
                if pend and not probe_active(DATA) and time.monotonic() - last_pass >= args.pace:
                    cand = runnable(pend, refs, over)
                    key = sorted(c[0]["id"] for c in cand)
                    # A pass that finds no task for the live version costs two calls: repeat it only every two
                    # minutes, except during a scheduler batch where activation can finish at any time.
                    retry_delay = args.pace if activation_pending() else max(120, args.pace)
                    if cand and (key != no_task or time.monotonic() - last_pass >= retry_delay):
                        last_pass = time.monotonic()
                        made = create_pass(cand, playing)
                        limited_reads = 0
                        no_task = key if made is None else None
                        playing += made or []
                # One sweep of the match list finds the groups that have played; a played group without its games
                # (also after a restart) goes to the collector.
                if time.monotonic() - last_poll >= args.poll:
                    last_poll = time.monotonic()
                    if playing:
                        done = groups_over({e["group"] for e in playing})
                        for ev in playing:
                            if ev["group"] in done:
                                # Its matches are over: a submission switch can no longer reach them (collection may lag).
                                append_jsonl(DATA / "events.jsonl", {"ev": "played", "group": ev["group"],
                                                                     "task": ev["task"], "at": now(),
                                                                     "results": done[ev["group"]]})
                                log(f"played {ev['task']} {ev['group'][:8]}: {done[ev['group']]}")
                                over.add(ev["group"])
                        playing = [e for e in playing if e["group"] not in done]
                    with collecting_lock:
                        for ev in open_groups:
                            if (ev["group"] in over and ev["group"] not in collecting
                                and ev["group"] not in collected and ev["task"] in by_id):
                                collecting.add(ev["group"])
                                to_collect.put((by_id[ev["task"]], ev))
                errors = 0
            except ControlReadLimited as e:
                limited_reads += 1
                wait = min(60, max(1, e.retry_after) * 2 ** min(limited_reads - 1, 6))
                log(f'{e}; switch lock released, retry in {wait}s')
                # Shared priority quiets downloads, but the scheduler can acquire it and activate now.
                with control_priority(DATA):
                    time.sleep(wait)
                continue
            except (CambcError, OSError, ValueError, KeyError) as e:
                errors += 1
                wait = min(1800, 60 * 2 ** (errors - 1))
                log(f"error {errors}/{args.max_errors}: {e}; backing off {wait}s")
                if errors >= args.max_errors:
                    log("too many errors in a row: exiting")
                    sys.exit(1)
                time.sleep(wait)
                continue
            time.sleep(args.tick)
    finally:
        stopping.set()   # the collector ends after the group it is on


# ---------------------------------------------------------------- reporting

def wilson(w, n, z=1.96):
    if not n:
        return (0.0, 0.0, 1.0)
    p = w / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return p, max(0.0, c - h), min(1.0, c + h)


def suspect_groups():
    return {e["group"] for e in read_jsonl(DATA / "events.jsonl") if e["ev"] == "suspect"}


def games(version=None, purposes=None, include_suspect=False):
    """Finished games, one per (version, opponent, ref set, map, side): live games are deterministic, so
    repeats and fillers add nothing and are dropped. Suspect groups (the live version changed while they were in
    flight, so they may have played another version) are left out."""
    rows, seen = [], set()
    bad = set() if include_suspect else suspect_groups()
    for r in read_jsonl(DATA / "games.jsonl"):
        k = (r["version"], r["opp_id"], r.get("refset") if r.get("pin") == "ref" else r.get("source_group"),
             r["map"], r["side"])
        if k in seen or r.get('filler') or r.get("result") not in ("win", "loss") or r["group"] in bad:
            continue
        if version and r["version"] != version or purposes and r["purpose"] not in purposes:
            continue
        seen.add(k)
        rows.append(r)
    return rows


def table(rows, key, title):
    agg = {}
    for r in rows:
        k = key(r)
        a = agg.setdefault(k, [0, 0])
        a[0] += r["result"] == "win"
        a[1] += 1
    print(f"\n{title}")
    for k, (w, n) in sorted(agg.items(), key=lambda kv: str(kv[0])):
        p, lo, hi = wilson(w, n)
        print(f"  {str(k)[:44]:<44} {w:>4}-{n - w:<4} {100 * p:5.1f}%  ({100 * lo:4.1f}-{100 * hi:4.1f})")


def cmd_report(args):
    purposes = set(args.purpose.split(",")) if args.purpose else None
    rows = games(args.version, purposes)
    print(f"{len(rows)} finished games" + (f" of v{args.version}" if args.version else ""))
    table(rows, lambda r: (f"v{r['version']}", r["opp_name"][:24], r["purpose"]), "by version, opponent, purpose")
    for by in (args.by or "").split(","):
        if by == "map":
            table(rows, lambda r: (r["opp_name"][:12], r["map"]), "by opponent and map")
        elif by == "side":
            table(rows, lambda r: (f"v{r['version']}", r["opp_name"][:24], r["side"]), "by side")
        elif by == "picks":
            table(rows, lambda r: (r["opp_name"][:24], len(r["our_picks"])), "by pick count")


def cmd_pair(args):
    """Version A against version B on the games both played: same opponent, ref set, map and side."""
    a, b = args.versions
    key = lambda r: (r["opp_id"], r.get("refset"), r["map"], r["side"])
    ra = {key(r): r for r in games(a) if r.get("purpose") != "oppcheck"}
    rb = {key(r): r for r in games(b) if r.get("purpose") != "oppcheck"}
    both = sorted(set(ra) & set(rb))
    print(f"v{a} against v{b}: {len(both)} paired games")
    per = {}
    for k in both:
        s = per.setdefault(ra[k]["opp_name"][:24], [0, 0, 0, 0])
        wa, wb = ra[k]["result"] == "win", rb[k]["result"] == "win"
        s[0] += wa; s[1] += wb; s[2] += wa and not wb; s[3] += wb and not wa
    for name, (wa, wb, only_a, only_b) in sorted(per.items()) + [("total", [sum(x) for x in zip(*per.values())])] if per else []:
        n = only_a + only_b
        # Sign test on the discordant games: the paired games' only information.
        z = (only_a - only_b) / math.sqrt(n) if n else 0.0
        print(f"  {name:<24} v{a} {wa} wins, v{b} {wb} wins; flips {only_a} for v{a}, {only_b} for v{b} (z {z:+.2f})")


def cmd_status(args):
    tasks, created, finished, dropped, refs = state()
    pend = pending_tasks(tasks, created, dropped)
    inflight = [e for e in created.values() if e["group"] not in finished]
    by = {}
    for t in tasks:
        k = (t["version"], t["purpose"], t.get("part"), t["opp_name"][:20])
        s = by.setdefault(k, [0, 0, 0])
        s[0] += 1
        s[1] += t["id"] in created and created[t["id"]]["group"] in finished
        s[2] += t["id"] in created and created[t["id"]]["group"] not in finished
    print(f"{len(tasks)} tasks: {len(pend)} pending, {len(inflight)} in flight, "
          f"{sum(e['group'] in finished for e in created.values())} finished, {len(dropped)} dropped")
    for k, (n, f, i) in sorted(by.items(), key=lambda kv: str(kv[0])):
        print(f"  v{k[0]} {k[1]:<7} {str(k[2]):<5} {k[3]:<20} {f:>3}/{n:<3} done, {i} in flight")
    print("refs:", {f"{k[0]}/{k[1][:8]}": v for k, v in refs.items()})
    try:
        q = quota()
        live, sel = live_version()
        print(f"quota {q['quota']}, live v{live}, selected v{sel}")
    except CambcError as e:
        print(f"quota/live unavailable: {e}")


def main():
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = p.add_subparsers(dest="cmd", required=True)
    pl = sub.add_parser("plan", help="append tasks")
    pl.add_argument("--version", type=int, required=True, help="our submission version that plays these tasks")
    pl.add_argument("--set", default="v1", help="frozen set name (data/set-NAME.json)")
    pl.add_argument("--sets", help="parts of the set: core, ext")
    pl.add_argument("--opps", help="opponents: " + ", ".join(TEAMS) + " or team ids")
    pl.add_argument("--maps", help="instead of --sets: five or more map names from any set file, comma separated")
    pl.add_argument("--groups", type=int, help="at most this many groups per opponent and part")
    pl.add_argument("--one-side", action="store_true", help="one side per map, alternating (calibration)")
    pl.add_argument("--flip", action="store_true", help="with --one-side: the other side of each map")
    pl.add_argument("--repeat", help="rerun each opponent's ref group (determinism check)")
    pl.add_argument("--pin", default="ref", help="ref (default), none, or a source group id")
    pl.add_argument("--refset", default="r2", help="name of the opponent-version pin set (default r2, from 2026-11-08)")
    pl.add_argument("--purpose", help="label (default set, calib with --one-side)")
    pl.add_argument("--priority", type=int, help="higher first; >= 100 may use the reserve (default core 50, ext 30)")
    ru = sub.add_parser("run", help="queue and collect groups until stopped (touch data/STOP to stop)")
    ru.add_argument("--reserve", type=int, default=0, help="quota groups kept free for priority >= 100 tasks")
    ru.add_argument("--inflight", type=int, default=0, help="most groups playing at once (0: no cap, the quota decides)")
    ru.add_argument("--batch-inflight", type=int, default=0, help="unused (kept for old command lines)")
    ru.add_argument("--pace", type=int, default=20, help="seconds between create passes (one quota read each)")
    ru.add_argument("--recheck", type=int, default=15, help="creates between quota and live re-reads within a pass")
    ru.add_argument("--poll", type=int, default=30, help="seconds between sweeps for played groups")
    ru.add_argument("--tick", type=int, default=20)
    ru.add_argument("--idle", type=int, default=300, help="sleep when nothing is pending")
    ru.add_argument("--max-errors", type=int, default=8)
    ru.add_argument("--exit-when-done", action="store_true")
    rp = sub.add_parser("report")
    rp.add_argument("--version", type=int)
    rp.add_argument("--purpose", help="comma list, e.g. set,repeat")
    rp.add_argument("--by", default="", help="comma list of map, side, picks")
    pa = sub.add_parser("pair", help="paired comparison of two of our versions")
    pa.add_argument("versions", type=int, nargs=2)
    sub.add_parser("status")
    args = p.parse_args()
    for stream in (sys.stdout, sys.stderr):
        stream.reconfigure(encoding="utf-8", errors="replace")
    DATA.mkdir(parents=True, exist_ok=True)
    {"plan": cmd_plan, "run": cmd_run, "report": cmd_report, "status": cmd_status, "pair": cmd_pair}[args.cmd](args)


if __name__ == "__main__":
    main()
