# Fight starts by us (our hit with no cross-team hit within 12 tiles in the previous 10 rounds): which decision made the hit,
# and the numbers within 8 of the hit (previous round end). Trusted trace rounds only.
import sys, os
sys.path.insert(0, os.path.dirname(__file__)); sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'extract'))
from tlib import *
import common as C
from concurrent.futures import ProcessPoolExecutor
MAN = {g['replay']: g['group'][:8] + '-' + str(g['position']) for g in json.load(open('replays/v66/manifest.json'))['games']}
def one(g):
    key = MAN.get(g['source'])
    if not key or not os.path.exists(f'{ROOT}/{key}/trace.stdout.gz'): return []
    m = C.meta(g['dir']); R = C.rounds(g['dir']); team = {c['id']: c['team'] for c in m['champions']}
    CH = {c['id']: c for c in R['champions']}; us = g['us']
    hits = []
    for e in C.events(g['dir']):
        if e['k'] in ('attack', 'cast'):
            if any(v in team and team[v] != team[e['a']] for v, a in (e.get('dmg') or [])) or any(v in team and team[v] != team[e['a']] for v in (e.get('stun') or [])):
                hits.append((e['r'], e['a'], tuple(e['f']), e['k'], e.get('ab')))
    starts = []
    for i, h in enumerate(hits):
        if team[h[1]] != us: continue
        if any(h[0] - 10 <= x[0] < h[0] or (x[0] == h[0] and j < i) for j, x in enumerate(hits) if j != i and C.cheb(x[2], h[2]) <= 12 and x[0] >= h[0] - 10 and (x[0] < h[0] or j < i)): continue
        starts.append(h)
    if not starts: return []
    T, TV = load(key); out = []
    for (r, a, f, k, ab) in starts:
        L = T.get((r, a))
        if not L or not L['TT']: continue
        j = r - 2
        if j < 0: continue
        na = sum(1 for c in CH if team[c] == us and CH[c]['alive'][j] and C.cheb((CH[c]['x'][j], CH[c]['y'][j]), f) <= 8)
        ne = sum(1 for c in CH if team[c] != us and CH[c]['alive'][j] and C.cheb((CH[c]['x'][j], CH[c]['y'][j]), f) <= 8)
        tt = L['TT'][0]
        site = next((x.get('s') for x in L['TA'] if x['a'] in ('attack', 'cast_with_result') and x.get('rc') == '0' and x.get('s') not in ('recall_start',)), '-')
        home = [x for x in L['TE'] if x.get('k') == 'home']
        # did the attacker die within 15 rounds; kills by us within 15 rounds near
        died = any(not CH[a]['alive'][jj] for jj in range(r - 1, min(len(R['round']), r + 15)))
        out.append(dict(key=key, r=r, c=a, t=TV.get(a, {}).get('t'), na=na, ne=ne, d=tt.get('d'), site=site, fs=tt.get('fs'),
                        home=(home[-1].get('v'), home[-1].get('why')) if home else None, died=died, hp=float(tt['hp']) / float(tt['mh'])))
    return out
if __name__ == '__main__':
    G = C.games()
    with ProcessPoolExecutor(30) as ex: res = [x for o in ex.map(one, G) for x in o]
    json.dump(res, open('replays/v66-analysis/initiate.json', 'w'))
    for lab, sel in (('outnumbered', lambda x: x['ne'] > x['na']), ('even', lambda x: x['ne'] == x['na']), ('ahead', lambda x: x['ne'] < x['na'])):
        X = [x for x in res if sel(x)]
        print('==', lab, len(X), 'attacker died within 15: %.2f' % (sum(x['died'] for x in X) / max(1, len(X))))
        print('   branch/site', Counter((x['d'], x['site']) for x in X).most_common(8))
        print('   home', Counter(tuple(x['home']) if x['home'] else None for x in X).most_common(6))
        print('   type', Counter(x['t'] for x in X).most_common(6))
        fsl = Counter()
        for x in X:
            fs = x['fs']
            fsl['none/?' if not fs or fs in ('?', 'none') else ('sim_lost' if fs.split(':')[0] == '1' else 'sim_ok')] += 1
        print('   fight sim at start tile', fsl.most_common())
