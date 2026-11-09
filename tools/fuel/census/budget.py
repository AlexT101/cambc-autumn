"""Per-component fuel budget table from the census's CHIST lines (census.h hist_on), over every play turn after round 1.

    py tools/fuel/census/budget.py DIR [DIR2]     # replays of an instrumented copy (bench.py --games DIR); two: side by side

Columns per label: share of turns it ran in (inclusive >= 1 fuel), then over those turns p50 / p90 / p99 / p99.9 / max
inclusive fuel (1k buckets, so percentiles are to the 1k below), and its mean over all turns. `@turn` is the whole turn.
A game's last < hist_period rounds are not printed by the bot, so counts fall a few percent short of the game's turns."""
import re, sys, zipfile, collections
from pathlib import Path


def load(d):
    H = collections.defaultdict(lambda: [0, 0, collections.Counter(), 0])  # n, max, buckets, sum
    turns = oof = 0
    for b in sorted(Path(d).rglob("*.repl26a")):
        m = re.match(r"(.+)-([ab])$", b.parent.name)
        sides = [m[2]] if m else ["a", "b"]
        with zipfile.ZipFile(b) as z:
            for s in sides:
                for l in z.read(f"team-{s}.stdout").replace(b"\0", b"").decode("utf-8", "replace").splitlines():
                    if l.startswith("CHT "):
                        p = l.split()
                        if len(p) == 5 and p[4].isdigit(): turns += int(p[3]); oof += int(p[4])
                    elif l.startswith("CHIST "):
                        tok = l.split(" ")[1:]
                        k = next((i for i, x in enumerate(tok) if ":" in x), len(tok))
                        if k < 4 or not all(t.isdigit() for t in tok[k - 3:k]): continue
                        label, n, sm, mx, bs = " ".join(tok[:k - 3]), int(tok[k - 3]), int(tok[k - 2]), int(tok[k - 1]), tok[k:]
                        h = H[label]; h[0] += n; h[1] = max(h[1], mx); h[3] += sm
                        for x in bs:
                            a, _, c = x.partition(":")
                            if a.isdigit() and c.isdigit(): h[2][int(a)] += int(c)  # a line cut by the stdout cap
    return turns, oof, H


def pct(bk, n, q):
    t = q * n; c = 0
    for k in sorted(bk):
        c += bk[k]
        if c >= t: return k
    return max(bk) if bk else 0


def row(turns, h):
    n, mx, bk, sm = h
    mean = sm / max(1, turns)
    return (f"{100 * n / max(1, turns):5.1f}% {pct(bk, n, .5):4d}k {pct(bk, n, .9):4d}k {pct(bk, n, .99):4d}k "
            f"{pct(bk, n, .999):4d}k {mx / 1000:6.1f}k {mean / 1000:6.1f}k")


def main():
    runs = [load(d) for d in sys.argv[1:]]
    hdr = "  ran   p50   p90   p99 p99.9    max   mean"
    for d, (t, o, _) in zip(sys.argv[1:], runs):
        print(f"{d}: {t} turns, {o} out of fuel ({1000 * o / max(1, t):.2f} per 1k turns)")
    print(f"{'label':<18}" + " | ".join([hdr] * len(runs)))
    first = runs[0][2]
    labels = sorted(set().union(*[r[2] for r in runs]), key=lambda k: -first[k][3] if k in first else 0)
    for k in labels:
        print(f"{k:<18}" + " | ".join(row(t, H[k]) if k in H else " " * len(hdr) for t, _, H in runs))


if __name__ == "__main__":
    main()
