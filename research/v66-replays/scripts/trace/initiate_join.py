# For our outnumbered (within 8) fight starts the start-tile sim judged not lost: how many enemies actually joined
# (dealt champion damage to any of ours within 12 tiles of the start in the next 10 rounds) vs the sim's enemy count.
import sys, os
sys.path.insert(0, os.path.dirname(__file__)); sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'extract'))
from tlib import *
import common as C
from concurrent.futures import ProcessPoolExecutor
X = json.load(open('replays/v66-analysis/initiate.json'))
MAN = {g['group'][:8] + '-' + str(g['position']): g['replay'] for g in json.load(open('replays/v66/manifest.json'))['games']}
SRC = {g['source']: g for g in C.games(distinct=False)}
byk = defaultdict(list)
for x in X:
    if x['fs'] and x['fs'] not in ('?', 'none'): byk[x['key']].append(x)
def one(key):
    g = SRC[MAN[key]]; m = C.meta(g['dir']); team = {c['id']: c['team'] for c in m['champions']}
    hits = []
    for e in C.events(g['dir']):
        if e['k'] in ('attack', 'cast'):
            for v, a in (e.get('dmg') or []):
                if v in team and team[v] != team[e['a']]: hits.append((e['r'], e['a'], v, tuple(e['f'])))
    out = []
    for x in byk[key]:
        f = None
        for h in hits:
            if h[0] == x['r'] and h[1] == x['c']: f = h[3]; break
        if f is None: continue
        joined = {h[1] for h in hits if x['r'] <= h[0] <= x['r'] + 10 and team[h[1]] != g['us'] and C.cheb(h[3], f) <= 12}
        p = x['fs'].split(':')
        out.append(dict(x, joined=len(joined), simen=int(p[5]), simlost=p[0] == '1'))
    return out
if __name__ == '__main__':
    with ProcessPoolExecutor(30) as ex: res = [y for o in ex.map(one, list(byk)) for y in o]
    ok = [x for x in res if not x['simlost']]
    c = Counter(); d = defaultdict(lambda: [0, 0])
    for x in ok:
        k = 'joined>sim' if x['joined'] > x['simen'] else ('joined=sim' if x['joined'] == x['simen'] else 'joined<sim')
        c[k] += 1; d[k][0] += 1; d[k][1] += x['died']
    print('sim-ok starts', len(ok), {k: (v[0], 'attacker died %.2f' % (v[1] / v[0])) for k, v in d.items()})
    under = [x for x in ok if x['joined'] > x['simen']]
    print('under-counted: sim enemies 0 share %.2f' % (sum(x['simen'] == 0 for x in under) / len(under)))
    print('under-counted by (sim,joined):', Counter((x['simen'], x['joined']) for x in under).most_common(8))
    json.dump(res, open('replays/v66-analysis/initiate_join.json', 'w'))
