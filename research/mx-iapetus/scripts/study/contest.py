"""Contested mid cycles in farm windows (both teams targeted): numbers and hp within 8 of the group's tiles at the
round both were targeting, and the outcome. Also home captures by group type and clear crew size."""
import json, sys
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor
sys.path.insert(0, '/home/ubuntu/wt/mx-iapetus/tools/replay')
from analysis.data import Game, chebyshev  # noqa


def work(g):
    G = Game(g['dir'])
    R = G.rounds
    Wt = G.winner
    role = {Wt: 'W', 1 - Wt: 'L'}
    gm = {grp['id']: grp for grp in G.map.groups}
    out = []
    for c in g['cycles']:
        if not (c['W_tgt'] and c['L_tgt'] and c['cap'] in 'WL' and g['w0'] <= c['z'] <= g['w1']):
            continue
        rc = max(c['W_tgt_first'], c['L_tgt_first'])
        tiles = gm[c['g']]['tiles']
        res = {'side': c['side_L'], 'cap': c['cap'], 'gems': c['gems'], 'rc': rc, 'dir': g['dir'], 'g': c['g'], 'types': c['types']}
        for off in (0, 5):
            i = min(len(R['round']) - 1, max(0, rc - 1 + off))
            cnt = {'W': 0, 'L': 0}; hp = {'W': 0.0, 'L': 0.0}; prism = {'W': None, 'L': None}
            for ch in R['champions']:
                ro = role[ch['team']]
                if not ch['alive'][i] or ch['x'][i] is None: continue
                p = (ch['x'][i], ch['y'][i])
                if min(chebyshev(p, tuple(t)) for t in tiles) <= 8:
                    cnt[ro] += 1; hp[ro] += ch['hp'][i]
                    if G.name_of[ch['id']] == 'Prism': prism[ro] = ch['gems'][i] or 0
            res[f'n{off}'] = cnt; res[f'hp{off}'] = hp; res[f'prism{off}'] = prism
        # whole-team alive count at rc
        i = max(0, rc - 1)
        res['alive'] = {ro: sum(1 for ch in R['champions'] if role[ch['team']] == ro and ch['alive'][i]) for ro in 'WL'}
        out.append(res)
    return out


if __name__ == '__main__':
    C = [json.loads(l) for l in open('/tmp/mxi-study/cycles.jsonl')]
    with ProcessPoolExecutor(24) as ex:
        rows = [r for rs in ex.map(work, C, chunksize=4) for r in rs]
    json.dump(rows, open('/tmp/mxi-study/contest.json', 'w'))
    N = len(C)
    for side in ('mid', 'own', 'enemy'):
        S = [r for r in rows if r['side'] == side]
        print(f'\n## {side} contested cycles: {len(S)} ({len(S)/N:.2f}/game); W captures {sum(r["cap"]=="W" for r in S)/len(S):.0%}')
        for off in (0, 5):
            byd = defaultdict(lambda: [0, 0, 0, 0])
            for r in S:
                dn = r[f'n{off}']['W'] - r[f'n{off}']['L']
                k = max(-2, min(2, dn))
                b = byd[k]; b[0] += 1; b[1] += r['cap'] == 'W'; b[2] += r['gems'] * (r['cap'] == 'W'); b[3] += r['gems'] * (r['cap'] == 'L')
            print(f' +{off} rounds: W-L champions within 8 of tiles ->', ', '.join(f'{k:+d}: n {v[0]} Wwins {v[1]/v[0]:.0%} gemsW-L/game {(v[2]-v[3])/N:.1f}' for k, v in sorted(byd.items())))
            mw = sum(r[f'n{off}']['W'] for r in S) / len(S); ml = sum(r[f'n{off}']['L'] for r in S) / len(S)
            hw = sum(r[f'hp{off}']['W'] for r in S) / len(S); hl = sum(r[f'hp{off}']['L'] for r in S) / len(S)
            pw = sum(1 for r in S if r[f'prism{off}']['W'] is not None) / len(S); pl = sum(1 for r in S if r[f'prism{off}']['L'] is not None) / len(S)
            print(f'   mean near: W {mw:.2f} L {ml:.2f}; hp W {hw:.0f} L {hl:.0f}; Prism near W {pw:.0%} L {pl:.0%}')
        al = Counter((r['alive']['W'] - r['alive']['L']) for r in S)
        print('  whole-team alive W-L at contest start:', dict(sorted(al.items())))
