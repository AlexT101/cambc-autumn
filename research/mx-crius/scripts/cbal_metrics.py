"""Per bot name over extracted A/B games: win %, champion-kill deaths a game, share of deaths outnumbered by 2+
bodies within 6 the round before, Prism deaths a game, mean nearest-ally distance (alive bodies, every 5th
round to r600), wealth (tributed + carried gems) and gold earned at r150/r300, share of alive rounds in contact
(an enemy within 6)."""
import json, gzip, glob, os, sys, collections
from concurrent.futures import ProcessPoolExecutor
ROOT = sys.argv[1]
def d(a, b, i): return max(abs(a['x'][i] - b['x'][i]), abs(a['y'][i] - b['y'][i]))
def one(p):
    dd = os.path.dirname(p); m = json.load(open(p))
    names = [t['name'] for t in m['teams']]; w = m['result']['winner']
    typ = {c['id']: c['name'] for c in m['champions']}
    R = json.load(gzip.open(dd + '/rounds.json.gz')); rounds = R['round']; ri = {r: i for i, r in enumerate(rounds)}; C = R['champions']
    out = {n: collections.Counter() for n in names}
    for t, n in enumerate(names):
        out[n]['games'] += 1; out[n]['wins'] += (w == t)
    for l in gzip.open(dd + '/events.jsonl.gz', 'rt'):
        e = json.loads(l)
        if e['k'] != 'death' or e.get('linked') or e.get('by', -1) < 0: continue
        v = next(c for c in C if c['id'] == e['v']); n = names[v['team']]
        out[n]['deaths'] += 1
        if 'Prism' in typ[v['id']]: out[n]['prism_deaths'] += 1
        i = ri.get(e['r'] - 1)
        if i is None or not v['alive'][i] or v['x'][i] is None: continue
        us = sum(1 for o in C if o['team'] == v['team'] and o['alive'][i] and o['x'][i] is not None and d(o, v, i) <= 6)
        th = sum(1 for o in C if o['team'] != v['team'] and o['alive'][i] and o['x'][i] is not None and d(o, v, i) <= 6)
        out[n]['dead_seen'] += 1; out[n]['outnumbered'] += (th - us >= 2)
    for i in range(0, min(len(rounds), 600), 5):
        al = [c for c in C if c['alive'][i] and c['x'][i] is not None]
        for c in al:
            n = names[c['team']]
            mates = [d(c, o, i) for o in al if o is not c and o['team'] == c['team']]
            if mates: out[n]['near_sum'] += min(mates); out[n]['near_n'] += 1
            out[n]['alive_n'] += 1; out[n]['contact'] += any(o['team'] != c['team'] and d(c, o, i) <= 6 for o in al)
    for T in (150, 300):
        i = ri.get(T)
        if i is None: continue
        for t, n in enumerate(names):
            out[n]['wealth%d' % T] += R['gems'][t][i] + sum(c['gems'][i] for c in C if c['team'] == t)
            out[n]['gold%d' % T] += sum(c['earned'][i] for c in C if c['team'] == t)
            out[n]['at%d' % T] += 1
    return out
if __name__ == '__main__':
    ps = glob.glob(ROOT + '/*/meta.json')
    tot = collections.defaultdict(collections.Counter)
    with ProcessPoolExecutor(32) as ex:
        for o in ex.map(one, ps, chunksize=4):
            for n, c in o.items(): tot[n].update(c)
    for n, c in sorted(tot.items()):
        g = c['games']
        print('%-12s games %5d win %.1f%% deaths/g %.2f outnumbered %.1f%% prism deaths/g %.2f nearest ally %.2f contact %.1f%% wealth150 %.0f wealth300 %.0f gold150 %.0f gold300 %.0f'
              % (n, g, 100 * c['wins'] / g, c['deaths'] / g, 100 * c['outnumbered'] / max(1, c['dead_seen']), c['prism_deaths'] / g,
                 c['near_sum'] / max(1, c['near_n']), 100 * c['contact'] / max(1, c['alive_n']), c['wealth150'] / max(1, c['at150']),
                 c['wealth300'] / max(1, c['at300']), c['gold150'] / max(1, c['at150']), c['gold300'] / max(1, c['at300'])))
