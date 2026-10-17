"""Free double moves: champion u, visible enemy e within 5 at the start of u's turn in round r, e acted before u in r.
u gets n_e = 0 (two turns in a row against e) iff u acts before e in round r+1. Measure how often teams take it,
and how often the enemy got n_e = 2 against u (u before e in r, e before u in r+1) while within 5.

  py freedouble.py 100000                                     # the report: ladder games of the top six and us
  py freedouble.py --src replays/batch-20261017-091937-928141 --team nemesis rival
Selection options: gamesel.py.
"""
import json, gzip, os, sys, collections
from concurrent.futures import ProcessPoolExecutor
import gamesel
ROOT = gamesel.ROOT


def game(args):
    d, tn = args
    try:
        m = json.load(open(os.path.join(ROOT, d, 'meta.json'), encoding='utf-8'))
        R = json.load(gzip.open(os.path.join(ROOT, d, 'rounds.json.gz')))
    except Exception:
        return collections.Counter()
    champs = m['champions']; ids = [c['id'] for c in champs]
    team = {c['id']: c['team'] for c in champs}; idx = {c['id']: i for i, c in enumerate(champs)}
    rix = {r: i for i, r in enumerate(R['round'])}

    def order(r):
        pi = rix.get(r - 1)
        key = lambda c: (-(R['champions'][idx[c]]['prio'][pi] if pi is not None else 0), c)
        A = sorted([c for c in ids if team[c] == 0], key=key); B = sorted([c for c in ids if team[c] == 1], key=key)
        f, s = (A, B) if r % 2 == 1 else (B, A)
        seq = []
        for i in range(max(len(A), len(B))):
            if i < len(f): seq.append(f[i])
            if i < len(s): seq.append(s[i])
        return {c: k for k, c in enumerate(seq)}
    out = collections.Counter()
    nR = len(R['round'])
    for i in range(1, nR - 1):
        r = R['round'][i]
        o, o2 = order(r), order(r + 1)
        for u in ids:
            cu = R['champions'][idx[u]]
            if not cu['alive'][i - 1]: continue
            pu = (cu['x'][i - 1], cu['y'][i - 1])
            for e in cu['sees'][i]:
                ce = R['champions'][idx[e]]
                if not ce['alive'][i - 1]: continue
                if max(abs(pu[0] - ce['x'][i - 1]), abs(pu[1] - ce['y'][i - 1])) > 5: continue
                t = tn[team[u]]
                if o[e] < o[u]:
                    out[(t, 'opp')] += 1
                    out[(t, 'took')] += o2[u] < o2[e]
                else:
                    out[(t, 'risk')] += 1
                    out[(t, 'gave')] += o2[e] < o2[u]
    return out


if __name__ == '__main__':
    p = gamesel.parser(__doc__, team=gamesel.TOPS)
    p.add_argument('n', nargs='?', type=int, help='first N games (as --limit)')
    a = p.parse_args()
    a.limit = a.n or a.limit
    gs = gamesel.select(a)
    tot = collections.Counter()
    with ProcessPoolExecutor(a.threads) as ex:
        for r in ex.map(game, gs, chunksize=8): tot += r
    print('enemy within 5 and acted before u this round -> u ranked before it next round (free double move taken);')
    print('u acted first this round -> enemy ranked before u next round (double move given away)')
    for t in a.team:
        o, k, rk, gv = tot[(t, 'opp')], tot[(t, 'took')], tot[(t, 'risk')], tot[(t, 'gave')]
        if o: print(f'  {t[:22]:22s} taken {k / o:.3f} (n {o:7d})   given away {gv / max(1, rk):.3f} (n {rk:7d})   acted first {rk / (o + rk):.3f}')
