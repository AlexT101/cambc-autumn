"""Draft search (research/hyperion/DRAFT.md, 2026-10-24): astraeus copies with forced per-pick-count drafts
(params::draft_three/four/five, draft_counters) against proxies of top-10 teams: astraeus playing each team's
main drafts (TEAMS). A library: import it, call run() with (picks, draft, counters, jobs) requests, then compare().

- Each vehicle bot carries one candidate per pick count, since a map only reads its own pick count's draft.
- jobs_for(picks) is every map of that pick count (ladder, maps/gen, maps/gen-s1), both sides, in a fixed shuffled
  order, so a prefix is a screening sample. Each (map, side) faces one fixed opponent, so candidates' results are
  paired and compare() reports the paired difference from INCUMBENT.
- Results go to replays/ds/db.jsonl keyed by (picks, draft, counters, map, side, opponent) and are reused.
- Needs cambc 3.x first on PATH (an old ~/.local/bin/cambc shadows it on some machines)."""
import hashlib, json, os, re, shutil, subprocess, sys, random, time, collections, math
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRATCH = ROOT / "replays" / "ds"
DB = SCRATCH / "db.jsonl"
VARIANTS = ROOT / "bots" / "variants"
SRC_BOT = ROOT / "bots" / "astraeus"
CAMBC = shutil.which("cambc") or "cambc"
sys.path.insert(0, str(ROOT / "tools"))
from run_batched import STATUS, REPLAY, ANSI  # noqa: E402

ENUM = ["ryth", "vesper_vale", "vendetta", "cassi_and_issac", "stellar", "prism", "marcella", "willow", "ren",
        "varg", "tavi", "heart_of_ruin"]
ALIAS = {"vesper": "vesper_vale", "cassi": "cassi_and_issac", "hor": "heart_of_ruin"}
SHORT = {"ryth": "Ryth", "vesper_vale": "Vesp", "vendetta": "Vend", "cassi_and_issac": "Cass", "stellar": "Stel",
         "prism": "Pris", "marcella": "Marc", "willow": "Will", "ren": "Ren", "varg": "Varg", "tavi": "Tavi",
         "heart_of_ruin": "HoR"}


def champ(t):
    t = t.strip().lower()
    t = ALIAS.get(t, t)
    assert t in ENUM, t
    return t


def D(text):
    return tuple(champ(t) for t in text.replace(",", " ").split())


def show(d):
    return " ".join(SHORT[c] for c in d)


INCUMBENT = {3: D("prism vesper hor"), 4: D("prism vesper marcella hor"),
             5: D("prism vesper marcella willow hor")}

# Top-10 teams' main drafts on 2026-10-24 (ranked, 10:20-17:10Z), each team's most common order.
TEAMS = {
    "claudus": {3: "vesper hor vendetta", 4: "vesper hor vendetta tavi", 5: "vesper hor vendetta tavi marcella"},
    "fish": {3: "vesper hor vendetta", 4: "vesper vendetta hor cassi", 5: "vesper vendetta hor cassi ryth"},
    "mite": {3: "marcella vendetta tavi", 4: "hor vesper marcella vendetta", 5: "vesper vendetta ryth tavi marcella"},
    "sponge": {3: "hor ryth marcella", 4: "vesper hor ryth marcella", 5: "hor ryth vendetta vesper marcella"},
    "trzy": {3: "marcella vendetta ryth", 4: "marcella vendetta ryth vesper", 5: "marcella vendetta ryth vesper hor"},
    "newteam": {3: "hor marcella vesper", 4: "hor marcella vesper ryth", 5: "hor marcella vesper ryth vendetta"},
    "policy": {3: "hor marcella vesper", 4: "hor vesper marcella ryth", 5: "marcella vesper tavi willow hor"},
    "prismbg": {3: "prism vesper hor", 4: "prism vesper marcella ryth", 5: "prism vesper marcella ryth hor"},
}
TEAMS = {k: {p: D(v) for p, v in d.items()} for k, d in TEAMS.items()}
SLOTS = list(TEAMS)


# ---------- maps ----------
def map_pools():
    cache = SCRATCH / "map_picks.json"
    if cache.is_file():
        return {int(k): v for k, v in json.loads(cache.read_text()).items()}
    pools = {3: [], 4: [], 5: []}
    out = subprocess.run(["node", "tools/mapgen/mapgen.mjs", "check", "maps"], cwd=ROOT, capture_output=True,
                         text=True, encoding="utf-8", errors="replace").stdout
    for line in out.splitlines():
        m = re.match(r"ok\s+(\S+)\s+.*picks=(\d)", line)
        if m:
            pools[int(m.group(2))].append(str(ROOT / "maps" / f"{m.group(1)}.map26a"))
    for suite in ("gen", "gen-s1"):
        idx = json.loads((ROOT / "maps" / suite / "index.json").read_text(encoding="utf-8"))
        for m in idx["maps"]:
            p = (m.get("spec") or {}).get("picks") or (m.get("metrics") or {}).get("picks")
            pools[int(p)].append(str(ROOT / "maps" / suite / m["file"]))
    cache.parent.mkdir(parents=True, exist_ok=True)
    cache.write_text(json.dumps(pools, indent=1))
    return pools


def stable(text):
    return int(hashlib.sha256(text.encode()).hexdigest()[:12], 16)


def jobs_for(picks, pools=None, extra_dirs=()):
    """(map, side) for every map of this pick count, both sides, in a fixed shuffled order."""
    pools = pools or map_pools()
    maps = list(pools[picks])
    for d in extra_dirs:
        maps += extra_pool(d)[picks]
    jobs = [(m, s) for m in maps for s in (0, 1)]
    jobs.sort(key=lambda j: stable(f"{Path(j[0]).name}|{j[1]}"))
    return jobs


def extra_pool(d):
    d = Path(d)
    idx = json.loads((d / "index.json").read_text(encoding="utf-8"))
    pools = {3: [], 4: [], 5: []}
    for m in idx["maps"]:
        p = (m.get("spec") or {}).get("picks") or (m.get("metrics") or {}).get("picks")
        pools[int(p)].append(str(d / m["file"]))
    return pools


def slot_of(mapname, side, slots=None):
    slots = slots or SLOTS
    return slots[stable(f"opp|{Path(mapname).name}|{side}") % len(slots)]


# ---------- bots ----------
ARRAY = r"(\b{name}\s*\[\s*\]\s*=\s*\{{)(.*?)(\}};)"


def patch_params(text, drafts, counters):
    for picks, name in ((3, "draft_three"), (4, "draft_four"), (5, "draft_five")):
        body = "".join(f"\n    cambc::champion_draft::{c}," for c in drafts[picks]) + "\n"
        text, n = re.subn(ARRAY.format(name=name), lambda m: m.group(1) + body + m.group(3), text, count=1, flags=re.S)
        assert n == 1, name
    if counters:
        body = "".join(f"\n    {{{p}, {r}, cambc::champion_draft::{s}, cambc::champion_draft::{i}}},"
                       for p, r, s, i in counters) + "\n"
        text, n = re.subn(ARRAY.format(name="draft_counters"), lambda m: m.group(1) + body + m.group(3), text,
                          count=1, flags=re.S)
        assert n == 1
    return text


def bot_name(drafts, counters):
    key = json.dumps([[drafts[p] for p in (3, 4, 5)], counters])
    return "ds-" + hashlib.sha1(key.encode()).hexdigest()[:10]


def make_bot(drafts, counters=()):
    counters = [list(c) for c in counters]
    name = bot_name(drafts, counters)
    target = VARIANTS / name
    stamp = target / "ds.json"
    if stamp.is_file() and (target / ".cambc" / "build" / "bot-injected.wasm").is_file():
        return target, False
    if target.exists():
        shutil.rmtree(target)
    shutil.copytree(SRC_BOT / "src", target / "src")
    params = target / "src" / "params.h"
    params.write_text(patch_params(params.read_text(encoding="utf-8"), drafts, counters), encoding="utf-8")
    stamp.write_text(json.dumps({"drafts": {p: drafts[p] for p in (3, 4, 5)}, "counters": counters}))
    return target, True


def build(path):
    r = subprocess.run([CAMBC, "build", str(path)], cwd=ROOT, capture_output=True, text=True, encoding="utf-8",
                       errors="replace")
    return path, r.returncode, r.stdout[-2000:] + r.stderr[-2000:]


def build_all(paths, par=5):
    paths = list(dict.fromkeys(paths))
    if not paths:
        return
    t = time.time()
    with ThreadPoolExecutor(par) as ex:
        for path, code, out in ex.map(build, paths):
            if code:
                shutil.rmtree(path / ".cambc", ignore_errors=True)
                raise RuntimeError(f"build failed {path}:\n{out}")
    print(f"built {len(paths)} bots in {time.time() - t:.0f}s", flush=True)


def opp_bot(slot):
    return make_bot(TEAMS[slot])


# ---------- db ----------
def db_load():
    rows = []
    if DB.is_file():
        for line in DB.read_text(encoding="utf-8").splitlines():
            if line.strip():
                rows.append(json.loads(line))
    return rows


def rkey(picks, draft, counters, mapname, side, opp):
    return (picks, " ".join(draft), json.dumps([list(c) for c in counters]), Path(mapname).name, side, opp)


def db_index():
    return {(r["picks"], r["draft"], r["counters"], r["map"], r["side"], r["opp"]): r for r in db_load()}


# ---------- running ----------
def run(requests, threads=16, timeout=900, slots=None):
    """requests: list of (picks, draft, counters, jobs). Plays every missing game."""
    idx = db_index()
    by_picks = collections.defaultdict(list)
    for picks, draft, counters, jobs in requests:
        counters = tuple(tuple(c) for c in counters if c[0] == picks)
        if (picks, draft, counters) not in [(picks, d, c) for d, c, _ in by_picks[picks]]:
            by_picks[picks].append((tuple(draft), counters, jobs))
        else:
            for i, (d, c, j) in enumerate(by_picks[picks]):
                if d == tuple(draft) and c == counters:
                    by_picks[picks][i] = (d, c, list(dict.fromkeys(list(j) + list(jobs))))
    nveh = max((len(v) for v in by_picks.values()), default=0)
    work = []  # (vehicle path, opp path, map, side, picks, draft, counters, opp)
    to_build = []
    opp_paths = {}
    for s in (slots or SLOTS):
        p, new = opp_bot(s)
        opp_paths[s] = p
        if new or not (p / ".cambc/build/bot-injected.wasm").is_file():
            to_build.append(p)
    for v in range(nveh):
        drafts = dict(INCUMBENT)
        counters = []
        members = []
        for picks, lst in by_picks.items():
            if v < len(lst):
                d, c, jobs = lst[v]
                drafts[picks] = d
                counters += list(c)
                members.append((picks, d, c, jobs))
        missing = []
        for picks, d, c, jobs in members:
            for m, side in jobs:
                opp = slot_of(m, side, slots)
                if rkey(picks, d, c, m, side, opp) not in idx:
                    missing.append((m, side, picks, d, c, opp))
        if not missing:
            continue
        path, new = make_bot(drafts, counters)
        if new or not (path / ".cambc/build/bot-injected.wasm").is_file():
            to_build.append(path)
        for m, side, picks, d, c, opp in missing:
            work.append((path, opp_paths[opp], m, side, picks, d, c, opp))
    build_all(to_build)
    if not work:
        print("nothing to play")
        return
    out = SCRATCH / time.strftime("%Y%m%d-%H%M%S")
    out.mkdir(parents=True)
    # Big maps first so no long game runs alone at the end.
    size = {}
    def area(m):
        if m not in size:
            size[m] = Path(m).stat().st_size
        return size[m]
    work.sort(key=lambda w: -area(w[2]))
    stems = {}
    lines = []
    for i, w in enumerate(work):
        path, opp, m, side = w[:4]
        a, b = (path, opp) if side == 0 else (opp, path)
        stem = f"{i:05d}"
        stems[stem] = w
        lines.append(f"{a.as_posix()} {b.as_posix()} {Path(m).as_posix()} {stem}.repl26a\n")
    (out / "manifest.txt").write_text("".join(lines), encoding="utf-8")
    print(f"playing {len(work)} games ({nveh} vehicles) -> {out}", flush=True)
    env = os.environ.copy()
    env["NO_COLOR"] = "1"
    t0 = time.time()
    done = 0
    status = None
    with open(DB, "a", encoding="utf-8") as db, open(out / "run.log", "w", encoding="utf-8") as log, \
            subprocess.Popen([CAMBC, "run-batch", str(out / "manifest.txt"), "--jobs", str(threads), "--color",
                              "never", "--timeout", str(timeout), "--log-limit", "0"], cwd=out, env=env,
                             stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8",
                             errors="replace", bufsize=1) as proc:
        for raw in proc.stdout:
            log.write(raw)
            line = ANSI.sub("", raw.rstrip("\r\n"))
            if f := STATUS.match(line):
                status = f
                continue
            f = REPLAY.match(line)
            if not f or status is None:
                continue
            stem = re.split(r"[\\/]", f.group(1))[-1].removesuffix(".repl26a")
            kind, team, failure, rounds = status.groups()
            status = None
            if stem not in stems or kind == "STARTING":
                continue
            path, opp, m, side, picks, d, c, oppslot = stems[stem]
            (out / f"{stem}.repl26a").unlink(missing_ok=True)
            row = {"picks": picks, "draft": " ".join(d), "counters": json.dumps([list(x) for x in c]),
                   "map": Path(m).name, "side": side, "opp": oppslot}
            if failure is not None:
                row["error"] = failure
                print("ERROR", stem, failure, flush=True)
            else:
                row["win"] = (team == "A") == (side == 0)
                row["rounds"] = int(rounds)
            db.write(json.dumps(row) + "\n")
            db.flush()
            done += 1
            if done % 200 == 0:
                el = time.time() - t0
                print(f"  {done}/{len(work)} in {el:.0f}s ({done / el:.2f}/s)", flush=True)
    print(f"done {done}/{len(work)} in {time.time() - t0:.0f}s", flush=True)


# ---------- reporting ----------
def results(picks, draft, counters=(), jobs=None, slots=None):
    idx = db_index()
    counters = tuple(tuple(c) for c in counters if c[0] == picks)
    res = {}
    for m, side in jobs:
        opp = slot_of(m, side, slots)
        r = idx.get(rkey(picks, draft, counters, m, side, opp))
        if r and "win" in r:
            res[(Path(m).name, side)] = (r["win"], opp)
    return res


def compare(picks, cands, jobs, base=None, slots=None, title=""):
    """Win rate of each candidate and its paired difference from base on common games."""
    base = base or (INCUMBENT[picks], ())
    b = results(picks, base[0], base[1], jobs, slots)
    rows = []
    for d, c in cands:
        r = results(picks, d, c, jobs, slots)
        common = [k for k in r if k in b]
        n = len(common)
        if not n:
            continue
        w = sum(r[k][0] for k in common)
        bw = sum(b[k][0] for k in common)
        plus = sum(r[k][0] and not b[k][0] for k in common)
        minus = sum(b[k][0] and not r[k][0] for k in common)
        diff = (plus - minus) / n
        se = math.sqrt(max(plus + minus - (plus - minus) ** 2 / n, 1)) / n
        per = collections.defaultdict(lambda: [0, 0])
        for k in common:
            per[r[k][1]][0] += r[k][0]
            per[r[k][1]][1] += 1
        rows.append((diff, d, c, n, w, bw, se, per))
    rows.sort(key=lambda x: -x[0])
    print(f"\n== {title} {picks}-pick (base {show(base[0])})")
    for diff, d, c, n, w, bw, se, per in rows:
        tag = f" +{c}" if c else ""
        perteam = " ".join(f"{s[:4]}{100 * v[0] / v[1]:.0f}" for s, v in sorted(per.items()))
        print(f"{show(d) + tag:44} n={n:3} win {100 * w / n:5.1f}% base {100 * bw / n:5.1f}%  "
              f"diff {100 * diff:+5.1f} ±{200 * se:4.1f}  | {perteam}")
    return rows
