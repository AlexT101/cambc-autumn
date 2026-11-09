#!/usr/bin/env python3
"""Pooled hazard by X = fuel left after the plan, per first asker, 2k buckets; and the post-pricing rest.
usage: fgan4.py A.jsonl [B.jsonl]"""
import sys, json, collections

BEFORE_MOVE = {1, 2, 3, 4, 5, 6, 39, 7, 8}


def builds(v):
    return [dict(ask=v[16 + 4 * k], cost=v[17 + 4 * k], st=v[18 + 4 * k], who=v[19 + 4 * k]) for k in range(min(3, v[15]))]


def pct(xs, q):
    xs = sorted(xs)
    return xs[min(len(xs) - 1, int(q * len(xs)))] if xs else float("nan")


tab = collections.defaultdict(lambda: [0, 0, 0])
post = []      # after pricing (cp 8) to act end (12), finished
post_t = []    # to after turn order (38)
asks1 = []
for path in sys.argv[1:]:
    for l in open(path):
        r = json.loads(l)
        v = r["v"]
        if len(v) != 47 or (r["k"] == "FGO" and r["r"] <= 1) or not v[31]:
            continue
        b = builds(v)
        if r["k"] == "FG" and v[8]:
            post.append(v[8] - v[12])
            post_t.append(v[8] - v[38])
        if not b:
            continue
        # each active build, the fuel left after it, by its asker; one row per turn: the last active build
        act = [x for x in b if x["st"] == 2]
        if not act:
            continue
        x = act[-1]
        X = x["ask"] - x["cost"]
        if x["who"] == 1 and r["k"] == "FG":
            asks1.append(x["ask"])
        t = tab[(x["who"], X // 2000 * 2)]
        if r["k"] == "FG":
            t[0] += 1
        else:
            t[1 if v[35] in BEFORE_MOVE else 2] += 1
print("last active build's asker, X = fuel left after it (2k buckets): fin, oofB, oofA, rateB, rateAll")
for key in sorted(tab):
    if not 10 <= key[1] <= 64:
        continue
    f, a, b = tab[key]
    tot = f + a + b
    print(f"  asker={key[0]} X {key[1]:>2}-{key[1]+2}k: fin {f:>6} oofB {a:>4} oofA {b:>4} rateB {a/tot:6.2%} rateAll {(a+b)/tot:6.2%}")
print("post-pricing (cp8) to act end: p50 %.1fk p90 %.1fk p99 %.1fk p99.9 %.1fk" % tuple(pct(post, q) / 1000 for q in (.5, .9, .99, .999)))
print("post-pricing (cp8) to after turn order: p50 %.1fk p90 %.1fk p99 %.1fk p99.9 %.1fk" % tuple(pct(post_t, q) / 1000 for q in (.5, .9, .99, .999)))
h = collections.Counter(a // 5000 * 5 for a in asks1)
print("asker-1 active build ask fuel (finished turns):", sorted(h.items()))
