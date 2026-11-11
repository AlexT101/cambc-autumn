# P(a body damages a champion this round | Chebyshev distance to the nearest enemy champion at the end of the previous round),
# by melee/ranged, rounds <= 250, and what it does instead. hitrate.py NAME=GAMES.pkl[:OPP][:us] ...
import sys, pickle, json, gzip, collections
RANGED = {'Cassi', 'Vesper Vale', 'Prism', 'Stellar', 'Tavi', 'Willow'}
def cheb(a, b): return max(abs(a[0] - b[0]), abs(a[1] - b[1]))
def run(name, path, opp, ours):
    seen = set(); S = collections.defaultdict(collections.Counter)
    for g in pickle.load(open(path, 'rb')):
        if g['opp'] != opp or g['match'] in seen: continue
        seen.add(g['match']); d0 = g['dir']; side = g['us'] if ours else 1 - g['us']
        meta = json.load(open(d0 + '/meta.json')); R = json.load(gzip.open(d0 + '/rounds.json.gz')); ch = R['champions']
        typ = {c['id']: c['name'] for c in meta['champions']}
        hit = collections.defaultdict(set); camp = collections.defaultdict(set)
        for l in gzip.open(d0 + '/events.jsonl.gz', 'rt'):
            e = json.loads(l)
            if e['r'] > 250: break
            if e['k'] in ('attack', 'cast'):
                if e.get('dmg') or e.get('stun'): hit[e['r']].add(e['a'])
                if 'cdmg' in e or 'camp' in e: camp[e['r']].add(e['a'])
        n = min(250, len(R['round']))
        for r in range(2, n + 1):
            i = r - 2
            foes = [(c['x'][i], c['y'][i]) for c in ch if c['team'] != side and c['alive'][i]]
            if not foes: continue
            for c in ch:
                if c['team'] != side or not c['alive'][i] or not c['alive'][i + 1] and c['id'] not in hit[r] or c['stun'][i] > 0: continue
                if typ[c['id']] == 'Willow': continue
                p = (c['x'][i], c['y'][i]); d = min(cheb(p, f) for f in foes)
                if d > 6: continue
                hpf = c['hp'][i] / c['maxHp'][i]
                k = ('R' if typ[c['id']] in RANGED else 'M', d, 'healthy' if hpf > 0.5 else 'hurt')
                s = S[k]; s['n'] += 1; s['hit'] += c['id'] in hit[r]; s['camp'] += c['id'] in camp[r] and c['id'] not in hit[r]
                q = (c['x'][i + 1], c['y'][i + 1]) if c['alive'][i + 1] else p
                d2 = min(cheb(q, f) for f in foes)   # against the foes' old positions: the body's own step
                s['closer'] += d2 < d; s['away'] += d2 > d
    print(name)
    for kind in 'MR':
        for h in ('healthy', 'hurt'):
            print('  %s %-7s' % (kind, h) + ' | '.join('d%d n%5d hit %2.0f%% camp %2.0f%% closer %2.0f%% away %2.0f%%' % (d, S[(kind, d, h)]['n'], *(100 * S[(kind, d, h)][x] / max(1, S[(kind, d, h)]['n']) for x in ('hit', 'camp', 'closer', 'away'))) for d in range(1, 7)))
for a in sys.argv[1:]:
    name, spec = a.split('=', 1); parts = spec.split(':')
    run(name, parts[0], parts[1] if len(parts) > 1 else 'Inte', len(parts) > 2 and parts[2] == 'us')
