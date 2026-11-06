"""Pursuit beyond sight and hunting (ENGAGE.md section 3), from the engage rows.

Lost-sight event: a free Fish turn with no enemy in any of its own contexts this turn, where an enemy
seen in its previous turn (round r-1) is still alive (liveness is readable). L = that enemy's last
seen tile (own memory); placebo P = the mirror of L through the actor's tile. Over the next k own
turns (k = 1, 3, 5) we measure the share of turns closing on L and on P, and whether the actor
reaches L (Chebyshev <= 1). `target`: the actor hit that enemy within the last 2 rounds.

Hunting: free turns with no enemy in sight, no camp hit and not capturing, whose memory holds an alive
enemy seen 2-10 rounds ago at distance >= 9; label: the step closes on its last-seen tile; placebo
its mirror.

  python3 tools/fish/engage_lost.py research/fish-2026-11-05/engage-lost.json [--held fifth sixth]
"""
import argparse
import collections
import gzip
import json
import multiprocessing as mp

from engage_common import FIT, HELD, NAMES, ROWS, free, write


def cheb(a, b):
    return max(abs(a[0] - b[0]), abs(a[1] - b[1]))


def one(line):
    g = json.loads(line)
    lost, hunt = [], []
    for aid, rows in g['actors'].items():
        for i, r in enumerate(rows):
            x, y = r.get('x'), r.get('y')
            if not (x and y and free(x)) or x['E'] or x['later'] or i == 0:
                continue
            p = (x['x'], x['y'])
            cand = [m for m in x['M'] if m['r'] == r['r'] - 1 and m.get('alive')]
            if cand and rows[i - 1]['r'] == r['r'] - 1:
                m = min(cand, key=lambda q: q['d'])
                L = (m['x'], m['y']); P = (2 * p[0] - L[0], 2 * p[1] - L[1])
                d0 = cheb(p, L)
                target = x['lhit'] is not None and x['lhit'][1] == m['id'] and x['lhit'][0] <= 2
                tr = []
                for q in rows[i:i + 5]:
                    qx, qy = q.get('x'), q.get('y')
                    if not (qx and qy):
                        break
                    tr.append(((qx['x'], qx['y']), (qy['ex'], qy['ey']), any(e['id'] == m['id'] for e in qx['E'])))
                if tr:
                    lost.append(dict(cohort=g['cohort'], game=g['game'], group=g['group'], round=r['r'], actor=int(aid),
                                     type=x['type'], target=target, d0=d0, hpf=x['hp'] / x['mhp'], ehpf=m['hp'] / m['mhp'],
                                     cl=[cheb(b, L) < cheb(a, L) for a, b, _ in tr], op=[cheb(b, L) > cheb(a, L) for a, b, _ in tr],
                                     clp=[cheb(b, P) < cheb(a, P) for a, b, _ in tr],
                                     reach=min(cheb(b, L) for _, b, _ in tr) <= 1, resight=next((k for k, t in enumerate(tr) if t[2]), None),
                                     camp=any(q.get('y') and q['y']['camp'] for q in rows[i:i + 5])))
            if y['camp'] or x['gst'] == 2 or (x['lc'] is not None and x['lc'] <= 1):
                continue
            mem = [m for m in x['M'] if m.get('alive') and 2 <= r['r'] - m['r'] <= 10 and m['d'] >= 9]
            if mem and p != (y['ex'], y['ey']):
                m = min(mem, key=lambda q: q['d'])
                L = (m['x'], m['y']); P = (2 * p[0] - L[0], 2 * p[1] - L[1]); e1 = (y['ex'], y['ey'])
                hunt.append((g['cohort'], cheb(e1, L) < cheb(p, L), cheb(e1, P) < cheb(p, P), m['gems'] > 0,
                             m['hp'] / m['mhp'] < 0.4))
    return lost, hunt


def split(rows, cohorts):
    return [r for r in rows if r['cohort'] in cohorts]


def summary(L):
    n = len(L)
    if not n:
        return dict(n=0)
    out = dict(n=n, games=len({r['game'] for r in L}), groups=len({r['group'] for r in L}))
    for k in (1, 3, 5):
        S = [r for r in L if len(r['cl']) >= k]
        t = sum(k for _ in S)
        out[f'k{k}'] = dict(episodes=len(S), close_L=round(sum(sum(r['cl'][:k]) for r in S) / t, 4),
                            open_L=round(sum(sum(r['op'][:k]) for r in S) / t, 4),
                            close_placebo=round(sum(sum(r['clp'][:k]) for r in S) / t, 4))
    out['reach_L_5'] = round(sum(r['reach'] for r in L) / n, 4)
    out['resight_5'] = round(sum(r['resight'] is not None for r in L) / n, 4)
    out['camp_hit_5'] = round(sum(r['camp'] for r in L) / n, 4)
    return out


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('out')
    p.add_argument('--held', nargs='+', default=HELD)
    p.add_argument('--jobs', type=int, default=6)
    a = p.parse_args()
    lost, hunt = [], []
    with mp.Pool(a.jobs) as pool:
        for c in FIT + a.held:
            with gzip.open(ROWS / f'{c}-rows-v1.jsonl.gz', 'rt') as fh:
                for l, h in pool.imap_unordered(one, fh, chunksize=2):
                    lost += l; hunt += h
    res = dict(definition=__doc__, held=a.held)
    for name, cs in (('fit', FIT), ('held', a.held)):
        L = split(lost, cs)
        res[name] = dict(all=summary(L), target=summary([r for r in L if r['target']]),
                         target_d0_ge3=summary([r for r in L if r['target'] and r['d0'] >= 3]),
                         target_weak=summary([r for r in L if r['target'] and r['ehpf'] < 0.4]),
                         other=summary([r for r in L if not r['target']]))
        H = [h for h in hunt if h[0] in cs]
        res[name]['hunt'] = dict(n=len(H), close_L=round(sum(h[1] for h in H) / max(1, len(H)), 4),
                                 close_placebo=round(sum(h[2] for h in H) / max(1, len(H)), 4),
                                 carrier=dict(n=sum(h[3] for h in H), close_L=round(sum(h[1] for h in H if h[3]) / max(1, sum(h[3] for h in H)), 4),
                                              close_placebo=round(sum(h[2] for h in H if h[3]) / max(1, sum(h[3] for h in H)), 4)),
                                 weak=dict(n=sum(h[4] for h in H), close_L=round(sum(h[1] for h in H if h[4]) / max(1, sum(h[4] for h in H)), 4),
                                           close_placebo=round(sum(h[2] for h in H if h[4]) / max(1, sum(h[4] for h in H)), 4)))
    # Rule scored: "no pursuit": a lost target's last-seen tile is not closed on more than its placebo.
    ex = [dict(game=r['game'], round=r['round'], actor=r['actor'], type=NAMES[r['type']], d0=r['d0'])
          for r in split(lost, a.held) if r['target'] and r['d0'] >= 3 and all(r['cl'][:3]) and len(r['cl']) >= 3][:12]
    res['counterexamples_pursue_3_turns'] = ex
    write(a.out, res)
    for name in ('fit', 'held'):
        print(name, json.dumps({k: res[name][k] for k in ('all', 'target', 'hunt')}))


if __name__ == '__main__':
    main()
