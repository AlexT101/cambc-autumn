"""Find champions that oscillate, get stuck or keep switching targets, from astraeus-trace's per-turn "D" lines.

    py tools/replay/osc_detect.py DIR [DIR ...] [--bot NAME] [--out OUT_DIR] [--jobs N]

DIR: replay dirs (an ab.py run's replays/ab/<name>/ batch dirs, or any dir of .repl26a zips, searched
recursively). Our bot is the one whose name (from results.json) starts with --bot (default astraeus-trace);
its team's stdout must carry the trace (bots/variants/astraeus-trace, a debug build).

D line: D round handle branch farm claim wait_altar sx sy ex ey hp gems prey champ_atk camp_g casts
        walks fails goal_n gnx gny goal_dist gcx gcy tags fbest fmode fval fsec fsecval siege crew why

Output in OUT_DIR (default replays/osc/): episodes.jsonl (one episode a line), games.tsv (per game
counts), summary.md (counts by kind, champion type, branch pattern and reason tags, plus examples).
"""
import argparse
import collections
import json
import os
import re
import subprocess
import sys
import zipfile
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

FIELDS = ("round h br farm claim wait sx sy ex ey hp gems prey catk campg casts walks fails gn gnx gny gd gcx gcy "
          "tags fbest fmode fval fsec fsecval siege crew why").split()
INT = set(FIELDS) - {"br", "tags", "fmode", "fval", "fsecval", "why"}
D_RE = re.compile(r"(?:^|\s)D (\d+ \d+ [^\s] (?:-?\d+ ){21}[^\s]+ -?\d+ [^\s] [^\s]+ -?\d+ [^\s]+ \d \d [^\s]+)")
MOVE_BRANCHES = set("FRCBGXSWEhr")  # branches whose turn is about where to go
STILL_OK = set("PWTKQHtk")          # holding, waiting at an altar, channels, mending: standing still is the point


def parse(text):
    rows = collections.defaultdict(list)
    for m in D_RE.finditer(text):
        parts = m.group(1).split()
        if len(parts) != len(FIELDS):
            continue
        r = {}
        for k, v in zip(FIELDS, parts):
            r[k] = int(v) if k in INT else v
        r["fval"] = float(r["fval"])
        r["fsecval"] = float(r["fsecval"])
        r["moved"] = (r["sx"], r["sy"]) != (r["ex"], r["ey"])
        r["hit"] = r["catk"] >= 0 or r["campg"] >= 0
        rows[r["h"]].append(r)
    for h in rows:
        rows[h].sort(key=lambda r: r["round"])
    return rows


def runs(seq):
    """Split a champion's rows into runs of consecutive rounds, alive at both ends."""
    cur = []
    for r in seq:
        if r["sx"] < 0 or r["ex"] < 0:
            if cur:
                yield cur
            cur = []
            continue
        if cur and r["round"] != cur[-1]["round"] + 1:
            yield cur
            cur = []
        cur.append(r)
    if cur:
        yield cur


def cheb(a, b):
    return max(abs(a[0] - b[0]), abs(a[1] - b[1]))


def context(rows):
    br = collections.Counter(r["br"] for r in rows)
    why = collections.Counter(w for r in rows for w in r["why"].split(",") if w != "-")
    return {
        "branches": "".join(r["br"] for r in rows),
        "branch_counts": dict(br),
        "why": dict(why.most_common(6)),
        "claims": sorted({r["claim"] for r in rows}),
        "prey": sorted({r["prey"] for r in rows if r["prey"] >= 0}),
        "champ_hits": sum(r["catk"] >= 0 for r in rows),
        "camp_hits": sum(r["campg"] >= 0 for r in rows),
        "casts": sum(r["casts"] for r in rows),
        "hp": [rows[0]["hp"], rows[-1]["hp"]],
        "gems": [rows[0]["gems"], rows[-1]["gems"]],
        "path": [(r["ex"], r["ey"]) for r in rows][:40],
        "tags": [r["tags"] for r in rows][:40],
        "goal_dist": [r["gd"] for r in rows][:40],
        "tiles": len({(r["ex"], r["ey"]) for r in rows}),
        "moves": sum(r["moved"] for r in rows),
        "net": cheb((rows[0]["sx"], rows[0]["sy"]), (rows[-1]["ex"], rows[-1]["ey"])),
        # signature: the branches used and the top two reasons, for grouping
        "sig": "".join(sorted(br)) + "|" + ",".join(w for w, _ in why.most_common(2)),
    }


def merge(eps):
    """Merge overlapping episodes of one kind for one champion."""
    out = []
    for e in sorted(eps, key=lambda e: (e["kind"], e["h"], e["r0"])):
        if out and out[-1]["kind"] == e["kind"] and out[-1]["h"] == e["h"] and e["r0"] <= out[-1]["r1"] + 2:
            out[-1]["r1"] = max(out[-1]["r1"], e["r1"])
        else:
            out.append(dict(e))
    return out


def detect(run):
    eps = []
    n = len(run)
    pos = [(r["ex"], r["ey"]) for r in run]

    def ep(kind, i0, i1, **extra):
        eps.append({"kind": kind, "h": run[0]["h"], "r0": run[i0]["round"], "r1": run[i1]["round"], **extra})

    # Ping-pong: the end tile returns to the one two turns back, not standing still, 4+ times in a row.
    i = 2
    while i < n:
        j = i
        while j < n and pos[j] == pos[j - 2] and pos[j] != pos[j - 1]:
            j += 1
        if j - i >= 4:
            ep("pingpong", i - 2, j - 1)
        i = max(j, i + 1)
    # Jitter: a 12-turn window that moves 8+ times over at most 3 tiles.
    W = 12
    for i in range(0, n - W + 1):
        win = run[i:i + W]
        if sum(r["moved"] for r in win) >= 8 and len(set(pos[i:i + W])) <= 3:
            ep("jitter", i, i + W - 1)
    # Wander: 20 turns, one claim, 15+ moves, ending within 3 of where it began and never more than 5 away.
    W = 20
    for i in range(0, n - W + 1):
        win = run[i:i + W]
        if (sum(r["moved"] for r in win) >= 15 and cheb(pos[i], pos[i + W - 1]) <= 3
                and max(cheb(pos[i], p) for p in pos[i:i + W]) <= 5 and len({r["claim"] for r in win}) == 1
                and len(set(pos[i:i + W])) > 3):
            ep("wander", i, i + W - 1)
    # Branch flip: two movement branches alternating, 6+ changes in 10 turns.
    W = 10
    for i in range(0, n - W + 1):
        b = [r["br"] for r in run[i:i + W]]
        changes = sum(b[k] != b[k - 1] for k in range(1, W))
        kinds = set(b) & MOVE_BRANCHES
        if changes >= 6 and len(kinds) >= 2 and len(set(b)) <= 3:
            ep("branchflip", i, i + W - 1, pair="".join(sorted(set(b))))
    # Stuck, failing: 5+ turns in a row on one tile where every walk asked failed.
    i = 0
    while i < n:
        j = i
        while j < n and not run[j]["moved"] and run[j]["walks"] > 0 and run[j]["fails"] == run[j]["walks"]:
            j += 1
        if j - i >= 5:
            ep("stuck_fail", i, j - 1)
        i = max(j, i + 1)
    # Stuck, idle: 12+ turns on one tile, no hit, no cast, in a branch that should be going somewhere,
    # with a goal 2+ tiles off (or none asked).
    i = 0
    while i < n:
        j = i
        while (j < n and not run[j]["moved"] and not run[j]["hit"] and run[j]["casts"] == 0
               and run[j]["br"] not in STILL_OK and (run[j]["gd"] == -1 or run[j]["gd"] >= 2)):
            j += 1
        if j - i >= 12:
            ep("stuck_idle", i, j - 1)
        i = max(j, i + 1)
    # Claim switching: the claim (>= 0) comes back to an earlier one after another, 3+ times in 30 turns,
    # or 5+ changes in 30 turns.
    W = 30
    for i in range(0, n - W + 1):
        c = [r["claim"] for r in run[i:i + W] if r["claim"] >= 0]
        ch = [c[k] for k in range(len(c)) if k == 0 or c[k] != c[k - 1]]
        back = sum(1 for k in range(2, len(ch)) if ch[k] == ch[k - 2])
        if back >= 3 or len(ch) - 1 >= 5:
            ep("claimflip", i, i + W - 1, claims=ch)
    # Prey switching: 3+ changes of chase target in 10 turns.
    W = 10
    for i in range(0, n - W + 1):
        p = [r["prey"] for r in run[i:i + W] if r["prey"] >= 0]
        ch = [p[k] for k in range(len(p)) if k == 0 or p[k] != p[k - 1]]
        if len(ch) - 1 >= 3:
            ep("preyflip", i, i + W - 1, prey=ch)
    # Goal switching: the walk goal's centre jumps 6+ tiles and back (A-B-A), 3+ times in 12 turns.
    W = 12
    for i in range(0, n - W + 1):
        g = [(r["gcx"], r["gcy"]) for r in run[i:i + W] if r["gn"] > 0]
        jumps = [g[k] for k in range(len(g)) if k == 0 or cheb(g[k], g[k - 1]) >= 6]
        back = sum(1 for k in range(2, len(jumps)) if cheb(jumps[k], jumps[k - 2]) <= 2)
        if back >= 3:
            ep("goalflip", i, i + W - 1)
    # Retreat churn: 4+ separate entries into retreat (R) within 30 turns, each after a non-R turn.
    W = 30
    for i in range(0, n - W + 1):
        b = [r["br"] for r in run[i:i + W]]
        entries = sum(1 for k in range(1, W) if b[k] == "R" and b[k - 1] != "R")
        if entries >= 4:
            ep("retreatchurn", i, i + W - 1)
    eps = merge(eps)
    for e in eps:
        rows = [r for r in run if e["r0"] <= r["round"] <= e["r1"]]
        e["len"] = len(rows)
        e.update(context(rows))
    return eps


def drafts(paths):
    """{replay path: [team A picks, team B picks]} through drafts.mjs."""
    out = {}
    lst = Path(os.environ.get("TMPDIR", "/tmp")) / f"osc-drafts-{os.getpid()}.txt"
    lst.write_text("\n".join(str(p) for p in paths) + "\n")
    res = subprocess.run(["node", "tools/replay/drafts.mjs", str(lst)], capture_output=True, text=True, check=True)
    for line in res.stdout.splitlines():
        f, a, b = line.split("\t")
        out[f] = [a.split(","), b.split(",")]
    lst.unlink()
    return out


def handle_types(picks):
    """Handles in pick order, team A then team B; Cassi & Issac take two (Cassi first)."""
    types = []
    for team in picks:
        for p in team:
            types += ["Cassi", "Issac"] if "Cassi" in p or p == "cassi_and_issac" else [p]
    return types


def team_handles(picks, team):
    n_a = len(handle_types([picks[0]]))
    n = len(handle_types(picks))
    return range(0, n_a) if team == 0 else range(n_a, n)


def one(args):
    path, team, picks = args
    try:
        with zipfile.ZipFile(path) as z:
            text = z.read(f"team-{'ab'[team]}.stdout").decode("utf-8", "replace")
    except Exception as e:
        return path, team, [], 0, str(e)
    rows = parse(text)
    types = handle_types(picks) if picks else []
    eps = []
    for h, seq in rows.items():
        for run in runs(seq):
            for e in detect(run):
                e["type"] = types[h] if h < len(types) else "?"
                eps.append(e)
    last = max((r["round"] for seq in rows.values() for r in seq), default=0)
    return path, team, eps, last, None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("dirs", nargs="+")
    ap.add_argument("--bot", default="astraeus-trace")
    ap.add_argument("--out", default="replays/osc")
    ap.add_argument("--jobs", type=int, default=32)
    a = ap.parse_args()
    games = []  # (path, our team)
    for d in a.dirs:
        for res in Path(d).rglob("results.json"):
            data = json.loads(res.read_text())
            names = [Path(b).name if isinstance(b, str) else str(b) for b in data["bots"]]
            ours = [i for i, nme in enumerate(names) if nme.startswith(a.bot)]
            if not ours:
                print(f"skip {res}: no bot named {a.bot}* in {names}", file=sys.stderr)
                continue
            for m in data["matches"]:
                if not m.get("replay"):
                    continue
                team = m["order"].index(ours[0])
                games.append((m["replay"], team, m.get("winner") == ours[0], m.get("rounds"), Path(m["map"]).stem, res.parent.name))
    print(f"{len(games)} games", file=sys.stderr)
    dr = {}
    paths = [g[0] for g in games]
    chunks = [paths[i::a.jobs] for i in range(a.jobs)]
    with ProcessPoolExecutor(a.jobs) as ex:
        for part in ex.map(drafts, [c for c in chunks if c]):
            dr.update(part)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    meta = {g[0]: g for g in games}
    all_eps = []
    per_game = []
    with ProcessPoolExecutor(a.jobs) as ex:
        for path, team, eps, last, err in ex.map(one, [(g[0], g[1], dr.get(g[0])) for g in games], chunksize=4):
            g = meta[path]
            if err:
                print(f"error {path}: {err}", file=sys.stderr)
            picks = dr.get(path)
            for e in eps:
                e.update({"replay": path, "team": team, "won": g[2], "map": g[4], "suite": g[5]})
            all_eps += eps
            kinds = collections.Counter(e["kind"] for e in eps)
            per_game.append((path, team, g[2], g[3], last, len(eps), dict(kinds), ",".join(picks[team]) if picks else "?",
                             ",".join(picks[1 - team]) if picks else "?"))
    with open(out / "episodes.jsonl", "w") as f:
        for e in all_eps:
            f.write(json.dumps(e) + "\n")
    with open(out / "games.tsv", "w") as f:
        f.write("replay\tteam\twon\trounds\tlast_traced\tepisodes\tkinds\tour_draft\ttheir_draft\n")
        for row in sorted(per_game, key=lambda r: -r[5]):
            f.write("\t".join(str(x) for x in row) + "\n")
    # Summary.
    L = [f"# Oscillation / stuck / switching episodes\n", f"{len(games)} games, {len(all_eps)} episodes, "
         f"{sum(1 for r in per_game if r[5])} games with any.\n"]
    traced_short = sum(1 for r in per_game if r[3] and r[4] < r[3] - 5)
    if traced_short:
        L.append(f"**{traced_short} games' traces end before the game does** (stdout cap?).\n")
    by_kind = collections.Counter(e["kind"] for e in all_eps)
    L.append("\n## By kind\n\n| kind | episodes | games | turns | top champion types | top branches | top reasons |\n|---|---|---|---|---|---|---|")
    for k, c in by_kind.most_common():
        es = [e for e in all_eps if e["kind"] == k]
        types = collections.Counter(e["type"] for e in es).most_common(4)
        br = collections.Counter()
        why = collections.Counter()
        for e in es:
            br.update(e["branch_counts"])
            why.update(e["why"])
        L.append(f"| {k} | {c} | {len({e['replay'] for e in es})} | {sum(e['len'] for e in es)} | "
                 f"{', '.join(f'{t} {n}' for t, n in types)} | {', '.join(f'{b}:{n}' for b, n in br.most_common(5))} | "
                 f"{', '.join(f'{w} {n}' for w, n in why.most_common(4))} |")
    L.append("\n## Episodes per 100 champion-games by type\n")
    seen = collections.Counter()
    for r in per_game:
        for t in handle_types([r[7].split(",")]):
            seen[t] += 1
    tk = collections.Counter((e["type"], e["kind"]) for e in all_eps)
    kinds = [k for k, _ in by_kind.most_common()]
    L.append("| type | games | " + " | ".join(kinds) + " |\n|---|---|" + "---|" * len(kinds))
    for t, n in seen.most_common():
        L.append(f"| {t} | {n} | " + " | ".join(f"{100 * tk[(t, k)] / n:.0f}" for k in kinds) + " |")
    for k in ("pingpong", "jitter", "stuck_fail", "stuck_idle", "claimflip", "preyflip", "wander"):
        es = [e for e in all_eps if e["kind"] == k]
        if not es:
            continue
        L.append(f"\n## {k}: signatures by turns (branches|top reasons)\n\n| sig | episodes | games | turns | longest |\n|---|---|---|---|---|")
        sig = collections.defaultdict(list)
        for e in es:
            sig[e["sig"]].append(e)
        for sg, v in sorted(sig.items(), key=lambda kv: -sum(e["len"] for e in kv[1]))[:15]:
            L.append(f"| `{sg}` | {len(v)} | {len({e['replay'] for e in v})} | {sum(e['len'] for e in v)} | {max(e['len'] for e in v)} |")
    L.append("\n## Branch flip pairs\n")
    pairs = collections.Counter(e["pair"] for e in all_eps if e["kind"] == "branchflip")
    L.append(", ".join(f"`{p}` {n}" for p, n in pairs.most_common(15)))
    L.append("\n## Longest examples per kind\n")
    for k in kinds:
        L.append(f"\n### {k}\n")
        for e in sorted((e for e in all_eps if e["kind"] == k), key=lambda e: -e["len"])[:8]:
            L.append(f"- `{e['replay']}` team {'AB'[e['team']]} h{e['h']} {e['type']} r{e['r0']}-{e['r1']} ({e['len']} turns) "
                     f"branches `{e['branches'][:40]}` why {e['why']} claims {e['claims']} prey {e['prey']}")
    (out / "summary.md").write_text("\n".join(L) + "\n")
    print("\n".join(L[:40]))


if __name__ == "__main__":
    main()
