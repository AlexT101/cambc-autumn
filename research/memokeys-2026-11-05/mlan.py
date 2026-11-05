"""mlan.py BASE_GAMES CAND_GAMES: loop fuel from mklite.py's ML lines (or mkprof.py's MK lines), by class
(cut/uncut, banking/not, opening); with matching games (100M), also paired per loop."""
import collections, sys, zipfile
from pathlib import Path


def loops(d):
    out = {}
    for b in sorted(Path(d).rglob("*.repl26a")):
        with zipfile.ZipFile(b) as z:
            for team in "ab":
                try:
                    text = z.read(f"team-{team}.stdout").replace(b"\0", b"").decode("utf-8", "replace")
                except KeyError:
                    continue
                for line in text.splitlines():
                    t = line.split()
                    try:
                        if t[:1] == ["ML"] and len(t) == 9:
                            r, h, o, bk, c, k, n, L = map(int, t[1:])
                        elif t[:1] == ["MK"]:
                            kv = {x[0]: x[1:] for x in t[3:10]}
                            r, h = int(t[1]), int(t[2])
                            o, bk, c, k, n, L = (int(kv[q]) for q in "obcknL")
                        else:
                            continue
                    except (ValueError, KeyError):
                        continue
                    if L > 10**7:
                        continue
                    key = (b.parent.name, team, r, h)
                    out.setdefault(key, (o, bk, c, k, n, L))
    return out


def cls(v):
    o, bk, c = v[:3]
    return ("cut" if c else "uncut") + "/" + ("bank" if bk else "nb") + ("/open" if o else "")


def summary(name, ls):
    by = collections.defaultdict(list)
    for v in ls.values():
        by[cls(v)].append(v)
        by["all"].append(v)
    print(f"{name}: {len(ls)} loops, {sum(v[2] for v in ls.values())} cut")
    for k in sorted(by, key=lambda k: -len(by[k])):
        xs = by[k]
        print(f"  {k:<16} n {len(xs):>7}  loop fuel mean {sum(v[5] for v in xs) / len(xs):>7.0f}  p50 {sorted(v[5] for v in xs)[len(xs) // 2]:>6}"
              f"  per group reached {sum(v[5] for v in xs) / max(1, sum(v[3] for v in xs)):>5.0f}")


a, b = loops(sys.argv[1]), loops(sys.argv[2])
summary("base", a)
summary("cand", b)
common = [k for k in a if k in b and a[k][:5] == b[k][:5]]
if len(common) > 0.5 * len(a):
    by = collections.defaultdict(lambda: [0, 0, 0])
    for k in common:
        for c in (cls(a[k]), "all"):
            s = by[c]
            s[0] += 1
            s[1] += a[k][5]
            s[2] += b[k][5]
    print(f"paired ({len(common)} loops with the same class and groups reached):")
    for c, (n, x, y) in sorted(by.items(), key=lambda kv: -kv[1][0]):
        print(f"  {c:<16} n {n:>7}  base {x / n:>7.0f}  cand {y / n:>7.0f}  {100 * (y - x) / x:+.2f}%")
