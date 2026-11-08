# Loss-mode tables from feats.py output. Weighted by copies (every scrim game counts, deterministic repeats included).
# usage: lossmodes.py FEATS.pkl
import pickle, sys, collections
import numpy as np

R = pickle.load(open(sys.argv[1], 'rb'))
L = [r for r in R if not r['win']]; W = [r for r in R if r['win']]
print(f'games {len(R)}  losses {len(L)}  win% {100*len(W)/len(R):.1f}')
for o in ('Intercontinental Fish', 'Mite'):
    rs = [r for r in R if r['opp'] == o]; print(f'  {o}: {len(rs)} games, win {100*np.mean([r["win"] for r in rs]):.1f}')

def m(rs, f): return np.mean([f(r) for r in rs]) if rs else float('nan')

print('\n== End-state accounting (mean per game; me / opp) ==')
for nm, f in [('rounds', lambda r: r['rounds']), ('tributed', 'trib_end'), ('carried at end', 'car_end'), ('capture gems', 'cap'),
              ('kill transfers (net)', 'killx'), ('camp-death loss', 'campl'), ('kills', 'kills'), ('deaths', 'deaths'),
              ('deaths to camps', 'campdeaths'), ('gems carried into deaths', 'gemsdied'), ('lifetime gold', 'gold_end'),
              ('tributes', 'tribs'), ('tribute cancelled by lock (gems)', 'lockcancel'), ('tribute cancelled by stun (gems)', 'stuncancel'),
              ('locks placed', 'lockplace'), ('capture resets', 'capres'), ('OOF turns', 'oof')]:
    if callable(f):
        print(f'{nm:34s} L {m(L,f):8.1f}            W {m(W,f):8.1f}')
    else:
        print(f'{nm:34s} L {m(L,lambda r:r[f][0]):8.1f} / {m(L,lambda r:r[f][1]):8.1f}   W {m(W,lambda r:r[f][0]):8.1f} / {m(W,lambda r:r[f][1]):8.1f}')

print('\n== Owned-gem gap decomposition in losses (me - opp; owned = tributed + carried) ==')
for o in (None, 'Intercontinental Fish', 'Mite'):
    rs = [r for r in L if o is None or r['opp'] == o]
    capg = m(rs, lambda r: r['cap'][0] - r['cap'][1]); kg = m(rs, lambda r: r['killx'][0] - r['killx'][1]); cg = m(rs, lambda r: r['campl'][0] - r['campl'][1])
    print(f'{str(o)[:12]:12s} n={len(rs):4d} capture {capg:+7.1f}  kills {kg:+7.1f}  camps {cg:+7.1f}  total {capg+kg+cg:+7.1f}  '
          f'(end owned gap {m(rs, lambda r: sum(r["trib_end"][:1])+r["car_end"][0]-r["trib_end"][1]-r["car_end"][1]):+.1f})')

print('\n== Checkpoint gaps (me - opp): losses | wins ==')
print('round  ' + '  '.join(f'{k:>22s}' for k in ['owned L|W', 'capture L|W', 'kill L|W', 'alive L|W', 'gold L|W']))
for c in [100, 200, 300, 400, 600, 800, 1000]:
    def g(rs, key):
        v = [r['ck'][c][key][0] - r['ck'][c][key][1] for r in rs if not r['ck'][c]['past']]
        return np.mean(v) if v else float('nan')
    def owned(rs):
        v = [r['ck'][c]['trib'][0] + r['ck'][c]['car'][0] - r['ck'][c]['trib'][1] - r['ck'][c]['car'][1] for r in rs if not r['ck'][c]['past']]
        return np.mean(v)
    nl = sum(not r['ck'][c]['past'] for r in L)
    print(f'{c:5d}  {owned(L):+9.1f} | {owned(W):+9.1f}  {g(L,"cap"):+9.1f} | {g(W,"cap"):+9.1f}  {g(L,"killx"):+9.1f} | {g(W,"killx"):+9.1f}'
          f'  {g(L,"alive"):+9.2f} | {g(W,"alive"):+9.2f}  {g(L,"gold"):+9.0f} | {g(W,"gold"):+9.0f}  (losses alive {nl})')

print('\n== When are losses decided ==')
ll = np.array([r['last_lead'] for r in L]); fr = np.array([r['last_lead'] / r['rounds'] for r in L])
print('last round we led (owned):', np.percentile(ll, [10, 25, 50, 75, 90]).round(), ' as share of game:', np.percentile(fr, [25, 50, 75]).round(2))
print('never led after r50:', np.mean(ll < 50).round(3))
# P(loss | behind by X at round c) from all games
for c in [200, 400, 600]:
    rows = [(r['ck'][c]['trib'][0] + r['ck'][c]['car'][0] - r['ck'][c]['trib'][1] - r['ck'][c]['car'][1], r['win']) for r in R if not r['ck'][c]['past']]
    a = np.array(rows)
    bins = [-2000, -200, -100, -50, 0, 50, 100, 200, 2000]
    s = ' '.join(f'[{bins[i]},{bins[i+1]}): {100*a[(a[:,0]>=bins[i])&(a[:,0]<bins[i+1]),1].mean():.0f}% n={((a[:,0]>=bins[i])&(a[:,0]<bins[i+1])).sum()}' for i in range(len(bins)-1))
    print(f'r{c} owned gap -> our win%: {s}')

print('\n== Worst 100-round window in losses: flow split ==')
fl = np.array([[r['worst'][2]['cap'], r['worst'][2]['kill'], r['worst'][2]['camp'], r['worst'][1], r['worst'][0]] for r in L])
print('mean swing', fl[:, 3].mean().round(1), 'start round median', np.median(fl[:, 4]), ' capture', fl[:, 0].mean().round(1), 'kill', fl[:, 1].mean().round(1), 'camp', fl[:, 2].mean().round(1))
kind = collections.Counter('kill-led' if abs(x[1]) > abs(x[0]) else 'capture-led' for x in fl)
print('dominant flow in worst window:', dict(kind))

print('\n== Loss types ==')
def typ(r):
    capg = r['cap'][0] - r['cap'][1]; kg = r['killx'][0] - r['killx'][1]
    if r['rounds'] >= 2000: t = 'timeout'
    else: t = 'race'
    return t + ('/kills' if kg < capg else '/captures')
c = collections.Counter(typ(r) for r in L); print(dict(c))
print('losses at 2000:', sum(r['rounds'] >= 2000 for r in L), ' wins at 2000:', sum(r['rounds'] >= 2000 for r in W))
print('carried-at-end in losses at 2000 (me/opp):', m([r for r in L if r['rounds'] >= 2000], lambda r: r['car_end'][0]), m([r for r in L if r['rounds'] >= 2000], lambda r: r['car_end'][1]))
print('trib gap at 2000 losses:', m([r for r in L if r['rounds'] >= 2000], lambda r: r['trib_end'][0] - r['trib_end'][1]))
print('race losses: our tributed when they hit 1000:', np.percentile([r['trib_end'][0] for r in L if r['rounds'] < 2000], [10, 25, 50, 75, 90]))
print('race losses: our owned when they hit 1000:', np.percentile([r['trib_end'][0] + r['car_end'][0] for r in L if r['rounds'] < 2000], [10, 25, 50, 75, 90]))

print('\n== Big-bag deaths (>=50 gems) per game: me (camp/champ) | opp ==')
for nm, rs in (('L', L), ('W', W)):
    mine = [sum(1 for x in r['big_deaths'] if x[1]) for r in rs]; theirs = [sum(1 for x in r['big_deaths'] if not x[1]) for r in rs]
    gm = [sum(x[2] for x in r['big_deaths'] if x[1]) for r in rs]; gt = [sum(x[2] for x in r['big_deaths'] if not x[1]) for r in rs]
    print(f'{nm}: me {np.mean(mine):.2f} ({np.mean(gm):.0f} gems)  opp {np.mean(theirs):.2f} ({np.mean(gt):.0f} gems)')
