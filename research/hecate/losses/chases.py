"""Chase episodes: one of ours walks towards a visible enemy for 4+ rounds in a row without hitting it.

Outcome within 12 rounds of the end: we died, they died, we hit it, nothing. Also where it ends (half).
py research/hecate/losses/chases.py [--losses] [--examples N]
"""
import argparse
import collections
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from common import our_games  # noqa


def cheb(a, b):
    return max(abs(a[0] - b[0]), abs(a[1] - b[1]))


def chases(g):
    us = g.team_ids[g.us]
    them = g.team_ids[g.them]
    hit = collections.defaultdict(set)  # (a, r) -> victims hit
    for s, r, a, v, amt, ap, vp in g.champ_damage:
        hit[(a, r)].add(v)
    deaths = collections.defaultdict(list)
    for d in g.deaths:
        deaths[d['v']].append(d['r'])
    out = []
    n = len(g.rounds['round'])
    for c in us:
        ch = g.ch(c)
        cur = None
        for r in range(2, n + 1):
            i = r - 1
            p0, p1 = g.pos(c, i - 1), g.pos(c, i)
            step = None
            if p0 and p1 and p0 != p1:
                best = None
                for e in them:
                    if e not in (ch['sees'][i] or []):
                        continue
                    q0, q1 = g.pos(e, i - 1), g.pos(e, i)
                    if not q0 or not q1:
                        continue
                    if cheb(p1, q1) < cheb(p0, q1) and cheb(p1, q1) <= 8:
                        if best is None or cheb(p1, q1) < best[1]:
                            best = (e, cheb(p1, q1))
                if best and not hit[(c, r)]:
                    step = best[0]
            if step is not None and cur and cur['e'] == step:
                cur['last'] = r
                cur['len'] += 1
                continue
            if cur and cur['len'] >= 4:
                out.append(cur)
            cur = dict(c=c, e=step, first=r, last=r, len=1) if step is not None else None
        if cur and cur['len'] >= 4:
            out.append(cur)
    for x in out:
        L = x['last']
        x['we_died'] = any(L <= d <= L + 12 for d in deaths[x['c']])
        x['they_died'] = any(L <= d <= L + 12 for d in deaths[x['e']])
        x['hit'] = any(x['e'] in hit[(x['c'], rr)] for rr in range(L, L + 4))
        p = g.pos(x['c'], L - 1)
        x['half'] = g.map.half(g.map.own(g.us, p)) if p else None
        x['bag'] = g.ch(x['c'])['gems'][L - 1]
        e_hp = g.ch(x['e'])['hp'][x['first'] - 1] or 0
        x['e_frac'] = round(e_hp / (g.ch(x['e'])['maxHp'][x['first'] - 1] or 1), 2)
        x['allies'] = sum(1 for a in us if a != x['c'] and g.pos(a, L - 1) and p and cheb(g.pos(a, L - 1), p) <= 5)
        x['enemies'] = sum(1 for a in them if g.pos(a, L - 1) and p and cheb(g.pos(a, L - 1), p) <= 6)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--losses', action='store_true')
    ap.add_argument('--examples', type=int, default=0)
    a = ap.parse_args()
    agg = collections.defaultdict(collections.Counter)
    ex = []
    ngames = collections.Counter()
    for g in our_games():
        res = 'W' if g.winner == g.us else 'L'
        ngames[res] += 1
        for x in chases(g):
            o = 'we died' if x['we_died'] and not x['they_died'] else 'they died' if x['they_died'] and not x['we_died'] else 'both' if x['we_died'] else 'hit' if x['hit'] else 'nothing'
            agg[res][o] += 1
            agg[res]['n'] += 1
            agg[res]['rounds'] += x['len']
            if x['half'] == 1:
                agg[res]['in their half'] += 1
                agg[res]['their half: ' + o] += 1
            if res == 'L' and o in ('we died',):
                ex.append((g.dir, g.map_name, g.name_of[x['c']], 'chased', g.name_of[x['e']], x['first'], x['last'], 'e_hp', x['e_frac'], 'half', x['half'], 'allies', x['allies'], 'enemies', x['enemies']))
    for res, c in agg.items():
        print(res, ngames[res], 'games', {k: round(v / ngames[res], 2) for k, v in sorted(c.items())})
    for x in ex[:a.examples]:
        print(x)


if __name__ == '__main__':
    main()
