"""stancefit.py EXTRACT_DIR BATCH_SUBSTR: the stance variant's STANCE component lines (debug builds) against the
replay's truth, to choose the enemy-bag estimator. A line: STANCE round handle state lead changed score_us
score_them our_posted_carried then per enemy alive:gems:rounds_unseen:type."""
import gzip, json, sys, zipfile, collections, math
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor

BATCH = sys.argv[2] if len(sys.argv) > 2 else ''

def g(d):
    meta = json.loads((d/'meta.json').read_text())
    if BATCH not in meta['source']: return []
    z = zipfile.ZipFile(meta['source'])
    for t, f in ((0, 'team-a.stdout'), (1, 'team-b.stdout')):
        try: L = [l.split() for l in z.read(f).decode(errors='replace').splitlines() if l.startswith('STANCE ') and len(l.split()) >= 9]
        except KeyError: continue
        if L: side = t; break
    else: return []
    R = json.load(gzip.open(d/'rounds.json.gz'))
    ch = R['champions']; n = len(R['round'])
    won = meta['result']['winner'] == side
    rows = []; seen = set()
    for p in L:
        r = int(p[1])
        if r % 10 or r in seen: continue
        seen.add(r)
        i = min(max(0, r - 1), n - 1)
        car = [sum(c['gems'][i] for c in ch if int(c['team']) == t and c['alive'][i]) for t in (0, 1)]
        en = [tuple(int(v) for v in q.split(':')) for q in p[9:]]
        rows.append(dict(r=r, su=int(p[6]), st=int(p[7]), ours=int(p[8]), en=en, true_ours=car[side], true_theirs=car[1 - side],
                         true_lead=R['gems'][side][i] + car[side] - R['gems'][1 - side][i] - car[1 - side], won=won, game=str(d)))
    return rows

def estimators(x):
    alive = [e for e in x['en'] if e[0]]
    known = sum(e[1] for e in alive)
    r = max(1, x['r'])
    nb = max(1, len(alive))
    rate = (x['su'] + x['ours']) / r / nb  # our collection per body-round
    out = {'known': known}
    for cap in (50, 100, 200, 10000):
        out[f'grow{cap}'] = sum(e[1] + rate * min(e[2], cap) for e in alive)
    out['atleast_ours'] = max(known, x['ours'])
    return out

if __name__ == '__main__':
    dirs = [d for d in Path(sys.argv[1]).iterdir() if (d/'meta.json').exists()]
    with ProcessPoolExecutor(32) as ex: X = [x for r in ex.map(g, dirs, chunksize=4) for x in r]
    print('rows', len(X), 'games', len({x['game'] for x in X}))
    names = list(estimators(X[0]).keys())
    print('our posted carried - true: mean %.1f' % (sum(x['ours'] - x['true_ours'] for x in X) / len(X)))
    for nm in names:
        for lo, hi in ((1, 300), (301, 700), (701, 2000), (1, 2000)):
            S = [x for x in X if lo <= x['r'] <= hi]
            e = [estimators(x)[nm] - x['true_theirs'] for x in S]
            mae = sum(abs(v) for v in e) / len(e)
            # predictive: AHEAD (lead >= 75) / BEHIND (<= -75) by this estimator's lead, win rate and share
            leads = [x['su'] - x['st'] + x['ours'] - estimators(x)[nm] for x in S]
            A = [x['won'] for x, l in zip(S, leads) if l >= 75]; B = [x['won'] for x, l in zip(S, leads) if l <= -75]
            T = [x['true_lead'] for x in S]
            agree = sum(1 for l, t in zip(leads, T) if (l >= 75) == (t >= 75) and (l <= -75) == (t <= -75)) / len(S)
            print(f'{nm:14s} r{lo}-{hi}: bias {sum(e)/len(e):7.1f} mae {mae:6.1f} | AHEAD {len(A)/len(S):.2f} wins {sum(A)/max(1,len(A)):.2f}'
                  f' | BEHIND {len(B)/len(S):.2f} wins {sum(B)/max(1,len(B)):.2f} | state agrees with truth {agree:.2f}')
    for lo, hi in ((1, 300), (301, 700), (701, 2000)):
        S = [x for x in X if lo <= x['r'] <= hi]
        A = [x['won'] for x in S if x['true_lead'] >= 75]; B = [x['won'] for x in S if x['true_lead'] <= -75]
        print(f'TRUTH          r{lo}-{hi}: AHEAD {len(A)/len(S):.2f} wins {sum(A)/max(1,len(A)):.2f} | BEHIND {len(B)/len(S):.2f} wins {sum(B)/max(1,len(B)):.2f}')
