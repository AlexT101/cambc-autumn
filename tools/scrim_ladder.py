"""Play unranked match groups between our live submission and the top ladder teams, on maps we choose.
Requires Python 3.10+ and `cambc login`.

Each group is `cambc match-groups create <team id> --maps <five map ids>` and spends one unit of the
team's unranked quota (`cambc match-groups quota`). The CLI has no side option and the requesting team
plays side A in all five games, so sides cannot be balanced. Each team gets as many distinct maps as the
pool allows, and any repeats are spread evenly. A run's plan, group ids and results go to
replays/scrims/<timestamp>/ (plan.json, summary.json), with the replays of each group in the layout
fetch_replays.py uses."""

import argparse
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import random
import re
import subprocess
import sys
from time import monotonic, sleep

from fetch_replays import MY_TEAM, ROOT, download_group, get_json


GAMES_PER_GROUP = 5
UUID = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}")
DONE = {"finished", "failed", "error", "cancelled", "canceled"}


def cambc(*args, retries=6):
    for attempt in range(retries + 1):
        r = subprocess.run(["cambc", *args], capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=300)
        wait = re.search(r"retry after (\d+) seconds", r.stderr + r.stdout)
        if r.returncode == 0 or not wait or attempt == retries:
            return r
        sleep(int(wait.group(1)) + 1)


def read_quota():
    r = cambc("match-groups", "quota", "--json")
    if r.returncode:
        sys.exit(f"cambc match-groups quota failed: {(r.stderr or r.stdout).strip()[-300:]}\nrun `cambc login` first")
    return json.loads(r.stdout)


def top_teams(n):
    teams = sorted((t for t in get_json("/ladder")["teams"] if t["teamId"] != MY_TEAM), key=lambda t: t["rank"])
    return teams[:n]


def draw_maps(pool, sets, rng):
    used = {m["id"]: 0 for m in pool}
    picks = []
    for _ in range(sets):
        order = sorted(pool, key=lambda m: (used[m["id"]], rng.random()))
        pick = [order[i % len(order)] for i in range(GAMES_PER_GROUP)]
        for m in pick:
            used[m["id"]] += 1
        picks.append(pick)
    return picks


def parse_sets(spec, teams):
    """`3` is 3 groups per team; `7x5,3x5` is 7 for each of the first 5 teams, then 3 each. The last count repeats."""
    counts = []
    for part in spec.split(","):
        n, _, k = part.partition("x")
        counts += [int(n)] * int(k or 1)
    return (counts + counts[-1:] * teams)[:teams]


def make_plan(teams, pool, sets, seed):
    groups = []
    for t, n in zip(teams, sets):
        rng = random.Random(f"{seed}:{t['teamId']}")
        for s, maps in enumerate(draw_maps(pool, n, rng), 1):
            groups.append({
                "rank": t["rank"], "team": t["name"], "teamId": t["teamId"], "set": s,
                "maps": [m["name"] for m in maps], "mapIds": [m["id"] for m in maps],
                "command": ["cambc", "match-groups", "create", t["teamId"], "--maps", ",".join(m["id"] for m in maps), "--json"],
                "groupId": None,
            })
    return groups


def problems(quota, groups):
    found = []
    if not quota.get("ready", True):
        found.append("quota reports not ready (is a submission live?)")
    q = quota.get("quota") or {}
    if q.get("limit") is not None and len(groups) > q["limit"] - q.get("used", 0):
        found.append(f"{len(groups)} groups planned but only {q['limit'] - q.get('used', 0)} of {q['limit']} left in the quota")
    gap, ranks, mine = quota.get("maxRankGap"), quota.get("opponentRanks") or {}, quota.get("requesterRank")
    for t in {g["teamId"]: g for g in groups}.values():
        if gap is not None and mine is not None and abs(ranks.get(t["teamId"], mine) - mine) > gap:
            found.append(f"{t['team']} is outside the allowed rank gap {gap}")
    return found


def print_plan(seed, pool, quota, groups):
    q = quota.get("quota") or {}
    print(f"seed {seed}, {len(pool)} maps in the pool, quota {q.get('used')}/{q.get('limit')} used, "
          f"{len(groups)} groups ({len(groups) * GAMES_PER_GROUP} games) planned; we are side A in every game")
    for g in groups:
        if g["set"] == 1:
            print(f"\n#{g['rank']} {g['team']} ({g['teamId']})")
        print(f"  set {g['set']}: {', '.join(g['maps'])}")
        print(f"    {' '.join(g['command'])}")


def save(out, state):
    (out / "plan.json").write_text(json.dumps(state, indent=1, ensure_ascii=False), encoding="utf-8")


def created_group(stdout, opponent, known, since):
    try:
        data = json.loads(stdout)
    except ValueError:
        data = None
    if isinstance(data, dict):
        for d in (data, data.get("group") if isinstance(data.get("group"), dict) else {}):
            for k in ("groupId", "id"):
                if isinstance(d.get(k), str) and UUID.fullmatch(d[k]):
                    return d[k]
    for gid in UUID.findall(stdout):
        if gid not in known:
            return gid
    for g in get_json("/match-groups", scope="all", team=MY_TEAM, kind="unranked")["groups"]:
        if g["id"] not in known and g["createdAt"] >= since and any(s["teamId"] == opponent for s in g["sides"]):
            return g["id"]
    return None


def create_groups(out, state):
    known = {MY_TEAM} | {g["teamId"] for g in state["groups"]} | {i for g in state["groups"] for i in g["mapIds"]}
    for i, g in enumerate(state["groups"], 1):
        since = (datetime.now(timezone.utc) - timedelta(minutes=5)).isoformat().replace("+00:00", "Z")
        r = cambc(*g["command"][1:])
        g["createOutput"] = (r.stdout + r.stderr).strip()
        if r.returncode:
            save(out, state)
            sys.exit(f"[{i}/{len(state['groups'])}] {g['team']} set {g['set']} failed: {g['createOutput'][-300:]}")
        g["groupId"] = created_group(r.stdout, g["teamId"], known, since)
        known.add(g["groupId"])
        save(out, state)
        print(f"[{i}/{len(state['groups'])}] {g['team']} set {g['set']}: group {g['groupId'] or 'id not found, see plan.json'}")
        sleep(3)


def finished(detail):
    return detail["group"]["status"] in DONE or all(m["status"] in DONE for m in detail["matches"])


def wait_for(groups, timeout, poll):
    details, deadline = {}, monotonic() + timeout
    pending = [g["groupId"] for g in groups if g.get("groupId")]
    while pending:
        for gid in list(pending):
            d = get_json(f"/match-groups/{gid}")
            if finished(d):
                details[gid] = d
                pending.remove(gid)
        print(f"{len(details)}/{len(details) + len(pending)} groups finished")
        if not pending or monotonic() > deadline:
            break
        sleep(poll)
    return details


def our_result(match):
    side = next((s for s in match["sides"] if s["teamId"] == MY_TEAM), None)
    return side["result"] if side else None


def summarise(out, groups, details):
    rows, teams = [], {}
    for g in groups:
        d = details.get(g.get("groupId"))
        record = teams.setdefault(g["teamId"], {"rank": g["rank"], "team": g["team"], "wins": 0, "losses": 0, "other": 0, "unfinished": 0})
        if not d:
            record["unfinished"] += GAMES_PER_GROUP
            continue
        for m in sorted(d["matches"], key=lambda m: m["position"]):
            res = our_result(m)
            record["wins" if res == "win" else "losses" if res == "loss" else "other"] += 1
            rows.append({"team": g["team"], "set": g["set"], "position": m["position"], "map": m["map"], "result": res,
                         "rounds": m.get("rounds"), "endReason": m.get("endReason"), "groupId": g["groupId"], "matchId": m["id"]})
    print()
    for r in teams.values():
        played = r["wins"] + r["losses"]
        rate = f"{100 * r['wins'] / played:5.1f}%" if played else "    -"
        extra = "".join(f", {r[k]} {k}" for k in ("other", "unfinished") if r[k])
        print(f"#{r['rank']:<3} {r['team'][:28]:<28} {r['wins']:>2}-{r['losses']:<2} {rate}{extra}")
        print("     " + ", ".join(f"{x['map']} {(x['result'] or '?')[0].upper()}" for x in rows if x["team"] == r["team"]))
    w, l = sum(r["wins"] for r in teams.values()), sum(r["losses"] for r in teams.values())
    print(f"total {w}-{l}")
    (out / "summary.json").write_text(json.dumps({"teams": list(teams.values()), "matches": rows}, indent=1, ensure_ascii=False), encoding="utf-8")


def collect(out, state, args):
    details = wait_for(state["groups"], args.wait_timeout, args.poll)
    if not args.no_download:
        for gid, d in details.items():
            try:
                folder, n = download_group(out, d["group"])
                print(f"{folder.name}" + (f" ({n} replays)" if n else " (cached)"))
            except Exception as e:
                print(f"FAILED download {gid}: {e}", file=sys.stderr)
    summarise(out, state["groups"], details)


def main():
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--teams", type=int, default=5, help="play the top N ladder teams other than us")
    p.add_argument("--sets", default="3", help="five-game groups per team, by rank: `3`, or `7x5,3x5` for 7 each for the top 5 then 3 each")
    p.add_argument("--seed", type=int, default=int(datetime.now().strftime("%Y%m%d")), help="map draw seed (default: today, YYYYMMDD)")
    p.add_argument("--dry-run", action="store_true", help="print the plan and the commands, queue nothing")
    p.add_argument("--yes", action="store_true", help="queue without asking")
    p.add_argument("--no-wait", action="store_true", help="exit once the groups are queued (collect later with --resume)")
    p.add_argument("--no-download", action="store_true", help="wait and summarise, but download no replays")
    p.add_argument("--resume", type=Path, help="wait for, download and summarise the groups of an earlier run's folder")
    p.add_argument("--wait-timeout", type=int, default=7200, help="seconds to wait for the groups to finish")
    p.add_argument("--poll", type=int, default=30, help="seconds between status checks")
    p.add_argument("--out", type=Path, help="default replays/scrims/<timestamp>/")
    args = p.parse_args()
    for stream in (sys.stdout, sys.stderr):
        stream.reconfigure(encoding="utf-8", errors="replace")

    if args.resume:
        collect(args.resume, json.loads((args.resume / "plan.json").read_text(encoding="utf-8")), args)
        return

    quota = read_quota()
    pool = sorted(quota.get("maps") or [], key=lambda m: m["name"])
    if not pool:
        sys.exit("cambc match-groups quota lists no maps")
    groups = make_plan(top_teams(args.teams), pool, parse_sets(args.sets, args.teams), args.seed)
    print_plan(args.seed, pool, quota, groups)
    found = problems(quota, groups)
    for f in found:
        print(f"PROBLEM: {f}", file=sys.stderr)
    if args.dry_run:
        print("\ndry run: nothing queued")
        return
    if found:
        sys.exit(1)
    if not args.yes:
        try:
            answer = input(f"\nSpend {len(groups)} unranked groups ({len(groups) * GAMES_PER_GROUP} games) on this plan? [y/N] ")
        except EOFError:
            answer = ""
        if answer.strip().lower() not in ("y", "yes"):
            sys.exit("nothing queued")

    out = args.out or ROOT / "replays" / "scrims" / datetime.now().strftime("%Y%m%d-%H%M%S")
    out.mkdir(parents=True, exist_ok=True)
    state = {"seed": args.seed, "created": datetime.now(timezone.utc).isoformat(), "pool": pool, "groups": groups}
    save(out, state)
    create_groups(out, state)
    print(f"plan and group ids: {out / 'plan.json'}")
    if not args.no_wait:
        collect(out, state, args)


if __name__ == "__main__":
    main()
