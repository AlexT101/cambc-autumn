"""Pair an arm's batch with the mirror batch game by game (map, order): CAND win rate, flips, paired diff.
usage: flips.py MIRROR_RESULTS ARM_RESULTS [--list N]"""
import json, sys, math, os
def load(p):
    r = json.load(open(p))
    out = {}
    for m in r['matches']:
        out[(os.path.basename(m['map']), tuple(m['order']))] = m
    return r, out
def cw(m):  # CAND (bot 0) wins
    return 1 if m['winner'] == 0 else 0
if __name__ == '__main__':
    r0, a = load(sys.argv[1]); r1, b = load(sys.argv[2])
    keys = sorted(set(a) & set(b))
    n = len(keys); wa = sum(cw(a[k]) for k in keys); wb = sum(cw(b[k]) for k in keys)
    up = [k for k in keys if cw(b[k]) > cw(a[k])]; dn = [k for k in keys if cw(b[k]) < cw(a[k])]
    # per-map paired diff (two orders per map)
    maps = {}
    for k in keys: maps.setdefault(k[0], []).append(cw(b[k]) - cw(a[k]))
    d = [sum(v) / len(v) for v in maps.values()]
    md = sum(d) / len(d); sd = math.sqrt(sum((x - md) ** 2 for x in d) / (len(d) - 1)) / math.sqrt(len(d))
    print(f'games {n}  mirror {100*wa/n:.2f}%  arm {100*wb/n:.2f}%  paired {100*md:+.2f} ±{196*sd:.2f}  flips +{len(up)} -{len(dn)} ({100*(len(up)+len(dn))/n:.1f}%)')
    if '--list' in sys.argv:
        N = int(sys.argv[sys.argv.index('--list') + 1])
        for k in up[:N]: print('UP', k, b[k]['rounds'], a[k]['rounds'])
        for k in dn[:N]: print('DN', k, b[k]['rounds'], a[k]['rounds'])
