# Where the bodies are: share of body-rounds (rounds 30-250) nearer the enemy's spawn than their own, and the largest
# group on the enemy's half; then engagements by half. half.py NAME=ROWS.pkl[:OPP] ...
import sys, pickle, json, gzip, collections
sys.path.insert(0, __file__.rsplit('/', 1)[0])
from summ import mean
def cheb(a, b): return max(abs(a[0] - b[0]), abs(a[1] - b[1]))
for a in sys.argv[1:]:
    name, spec = a.split('=', 1); parts = spec.split(':'); path = parts[0]; opp = parts[1] if len(parts) > 1 else 'Inte'
    rows = [r for r in pickle.load(open(path, 'rb'))['rows'] if r['opp'] == opp]
    games = {}
    for r in rows: games[r['dir']] = r['us']
    S = collections.Counter()
    for d0, us in games.items():
        R = json.load(gzip.open(d0 + '/rounds.json.gz')); ch = R['champions']
        sp = [None, None]
        for t in (0, 1):
            xs = [(c['x'][0], c['y'][0]) for c in ch if c['team'] == t]; sp[t] = (sum(p[0] for p in xs) / len(xs), sum(p[1] for p in xs) / len(xs))
        n = min(250, len(R['round']))
        for i in range(29, n, 3):
            for side, lab in ((1 - us, 'them'), (us, 'us')):
                inv = 0
                for c in ch:
                    if c['team'] != side or not c['alive'][i]: continue
                    p = (c['x'][i], c['y'][i]); S[lab + '_n'] += 1
                    if cheb(p, sp[1 - side]) < cheb(p, sp[side]): S[lab + '_inv'] += 1; inv += 1
                S[lab + '_r'] += 1; S[lab + '_inv3'] += inv >= 3
    def cell(x):
        if not x: return 'n 0'
        return 'n %3d (%.2f a game) died %2.0f%% net %+.2f' % (len(x), len(x) / len(games), 100 * mean([r['died'] for r in x]), mean([r['kA'] - r['kD'] for r in x]))
    T1 = [r for r in rows if not r['by_us'] and r['nA'] > r['nD']]; T2 = [r for r in rows if r['by_us'] and r['nA'] < r['nD']]
    print('%-10s games %4d | their body-rounds on our half %.1f%%, rounds with 3+ of them there %.1f%% | ours on their half %.1f%%, 3+ %.1f%%' % (name, len(games), 100 * S['them_inv'] / S['them_n'], 100 * S['them_inv3'] / S['them_r'], 100 * S['us_inv'] / S['us_n'], 100 * S['us_inv3'] / S['us_r']))
    print('    T1 (they start with numbers; net for them) on our half:   ' + cell([r for r in T1 if r['home_D']]) + ' | on theirs: ' + cell([r for r in T1 if not r['home_D']]))
    print('    T2 (we start outnumbered; net for us)      on their half: ' + cell([r for r in T2 if r['home_D']]) + ' | on ours:   ' + cell([r for r in T2 if not r['home_D']]))
