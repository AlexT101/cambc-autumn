"""Fuel gates in a --trace census: per gate, the fuel left when it fires, the share of its turns that still ran out,
and the fuel left after decide on its finished turns; which gates fire before which within a turn; and the first gate
of each turn that ran out. Reads only the census copy's stdout (its SHORTCUT lines carry the fuel left, and SLEFT
lines follow decide; instrument.py --trace adds both). Play the copy at the real budget (tools/README.md, Fuel).

    py tools/fuel/census/gates.py replays/fuel/cen [DIR ...]
"""
import sys, zipfile
from collections import Counter, defaultdict
from pathlib import Path


def q(xs, f):
    xs = sorted(xs)
    return xs[min(len(xs) - 1, int(f * len(xs)))] if xs else 0


GATES = {'step-guard-entry','step-guard-sim','step-guard-look','prey-cut-short','farm-partial-evaluation','comms-stale-vision','ward-no-bushes-clusters','turn-order','farm-no-route','farm-kept-target','crow-flies-farm','static-descend','siege-route-fuel','farm-no-attack-tiles','siege-no-tiles','spell-clear-no-tiles'}
fire = defaultdict(list)      # tag -> fuel left at firing
turn_tags = defaultdict(list)  # (game, round, handle) -> tags in order
oof, late, sleft, cen_ne = set(), set(), {}, {}
turns_seen = Counter()
games = 0
for root in sys.argv[1:]:
    for z in sorted(Path(root).rglob("*.repl26a")):
        with zipfile.ZipFile(z) as f:
            outs = [n for n in f.namelist() if n.endswith(".stdout")]
            for name in outs:
                text = f.read(name).replace(b"\0", b"").decode(errors="replace")
                if "SLEFT " not in text and "CEN " not in text:
                    continue
                games += 1
                g = (str(z), name)
                for ln in text.splitlines():
                    p = ln.split()
                    try:
                        if ln.startswith("SHORTCUT ") and len(p) >= 5:
                            key = (g, int(p[1]), int(p[2]))
                            if p[3] not in GATES:
                                continue
                            fire[p[3]].append(int(p[4]))
                            turn_tags[key].append(p[3])
                        elif ln.startswith("SLEFT "):
                            sleft[(g, int(p[1]), int(p[2]))] = int(p[3])
                        elif ln.startswith("CEN "):
                            key = (g, int(p[1]), int(p[2]))
                            if p[5] == "oof1":
                                oof.add(key)
                            if p[4] == "late1":
                                late.add(key)
                            cen_ne[key] = int(p[p.index("nn") + 1])
                    except (ValueError, IndexError):
                        pass

print(f"census stdouts read: {games}; OOF turns (CEN oof1): {len(oof)}; late turns: {len(late)}")
oof_tagged = sum(1 for k in oof if k in turn_tags)
print(f"OOF turns with any gate fired: {oof_tagged} ({100 * oof_tagged / max(1, len(oof)):.1f}%)")
print()
print(f"{'tag':28} {'fired':>7} {'turns':>7} {'left q10/q50/q90 at firing':>28} {'turn ran out':>13} "
      f"{'left after decide, finished q10/q50/q90':>40}")
by_tag_turns = defaultdict(set)
for k, tags in turn_tags.items():
    for t in set(tags):
        by_tag_turns[t].add(k)
for t in sorted(fire, key=lambda t: -len(fire[t])):
    ks = by_tag_turns[t]
    ran = sum(1 for k in ks if k in oof)
    left = [sleft[k] for k in ks if k in sleft and k not in oof]
    xs = fire[t]
    print(f"{t:28} {len(xs):7} {len(ks):7} {q(xs, .1):>9}/{q(xs, .5):>7}/{q(xs, .9):>7}   "
          f"{ran:6} {100 * ran / max(1, len(ks)):5.1f}%   {q(left, .1):>12}/{q(left, .5):>7}/{q(left, .9):>7} (n={len(left)})")

print("\nOrder within a turn: for each pair (A fired before B in the same turn), turns")
pairs = Counter()
for tags in turn_tags.values():
    seen = []
    for t in tags:
        for s in seen:
            if s != t:
                pairs[(s, t)] += 1
        if t not in seen:
            seen.append(t)
for (a, b), n in pairs.most_common(15):
    print(f"  {a:26} -> {b:26} {n}")

print("\nFirst gate of a turn that then ran out (OOF turns only):")
first = Counter(turn_tags[k][0] for k in oof if k in turn_tags)
for t, n in first.most_common():
    print(f"  {t:28} {n}")
