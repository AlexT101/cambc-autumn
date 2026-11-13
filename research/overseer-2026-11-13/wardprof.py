"""Ward-policy fuel from an instrumented nyx-vl copy's bench games (WPROF lines), joined with OOF lines.

    python3 research/overseer-2026-11-13/wardprof.py replays/fuel/wardfuel/g-nyx-vl-fprof

WPROF round handle start entry total memo grow site old cand ncand exit site_built
exit: 0 early (fuel/cluster shortcut), 1 memo hit, 2 bound fails margin, 3 no candidate passes, 4 cut, 5 tried.
"""
import collections
import glob
import statistics
import sys
import zipfile


def pct(xs, q):
    xs = sorted(xs)
    return xs[min(len(xs) - 1, int(q * len(xs)))] if xs else 0


def main():
    calls = []
    oof_rounds = 0
    oof_with_start_ward = collections.Counter()
    games = 0
    inside = collections.Counter()
    # A second directory limits the games to those it has finished too (paired subsets).
    only = {f.split("/")[-2] for f in glob.glob(sys.argv[2] + "/*/*.repl26a")} if len(sys.argv) > 2 else None
    for f in sorted(glob.glob(sys.argv[1] + "/*/*.repl26a")):
        if only is not None and f.split("/")[-2] not in only:
            continue
        side = f.split("/")[-2][-1]  # our bot plays team `side`
        z = zipfile.ZipFile(f)
        out = z.read(f"team-{side}.stdout").decode(errors="replace").splitlines()
        games += 1
        per_round = collections.defaultdict(int)  # (round, handle) -> start-ward spend
        oofs = []
        for line in out:
            if line.startswith("WPROF "):
                v = line.split()
                if len(v) != 14 or not all(x.isdigit() for x in v[1:]):
                    continue  # cut by the 1 MiB stdout cap
                c = dict(zip("round handle start entry total memo grow site old cand ncand exit built".split(), map(int, v[1:])))
                if c["total"] > 10**7:  # ran out inside and resumed next round
                    inside[c["start"]] += 1
                    per_round[c["round"]] += 10**6
                    continue
                calls.append(c)
                per_round[c["round"]] += c["total"]
            elif line.startswith("OOF "):
                oofs.append(int(line.split()[1]))
        for r in oofs:
            oof_rounds += 1
            s = per_round.get(r, 0)
            oof_with_start_ward["0" if s == 0 else "<5k" if s < 5000 else "5-15k" if s < 15000 else "15-30k" if s < 30000 else "30k+" if s < 10**6 else "inside"] += 1
    print(f"{games} games, {len(calls)} place_ward calls past the cooldown, {oof_rounds} OOF turns")
    for start in (1, 0):
        cs = [c for c in calls if c["start"] == start]
        if not cs:
            continue
        tot = [c["total"] for c in cs]
        print(f"\nstart={start}: {len(cs)} calls, sum {sum(tot)/1e6:.1f}M, mean {statistics.mean(tot):.0f}, p50 {pct(tot,.5)}, p90 {pct(tot,.9)}, p99 {pct(tot,.99)}, max {max(tot)}")
        ex = collections.Counter(c["exit"] for c in cs)
        for e in sorted(ex):
            sub = [c for c in cs if c["exit"] == e]
            print(f"  exit {e}: {len(sub)} calls, mean total {statistics.mean(c['total'] for c in sub):.0f}")
        for k in ("memo", "grow", "site", "old", "cand"):
            xs = [c[k] for c in cs]
            print(f"  {k:5s}: sum {sum(xs)/1e6:.2f}M ({100*sum(xs)/max(1,sum(tot)):.0f}%), p99 {pct(xs,.99)}, max {max(xs)}")
        nc = [c["ncand"] for c in cs if c["ncand"] > 0]
        if nc:
            per = [c["cand"] / c["ncand"] for c in cs if c["ncand"] > 0]
            print(f"  candidates: {len(nc)} loops, mean {statistics.mean(nc):.1f} a loop, {statistics.mean(per):.0f} fuel each")
        print(f"  site boards built: {sum(c['built'] for c in cs)}")
    print("ran out inside place_ward (by start flag):", dict(inside))
    print("\nOOF turns by that round's place_ward spend (both calls):", dict(oof_with_start_ward))


main()
