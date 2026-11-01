# For our outnumbered fight starts that the start-tile fight sim judged OK: were the enemies within 8 visible to the attacker,
# believed (tracked/comms) but unseen, or unknown? Uses initiate.json from initiate.py.
import sys, os
sys.path.insert(0, os.path.dirname(__file__)); sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'extract'))
from tlib import *
import common as C
from concurrent.futures import ProcessPoolExecutor
X = json.load(open('replays/v66-analysis/initiate.json'))
X = [x for x in X if x['ne'] > x['na'] and x['fs'] and x['fs'] not in ('?', 'none') and x['fs'].split(':')[0] == '0']
MAN = {g['group'][:8] + '-' + str(g['position']): g['replay'] for g in json.load(open('replays/v66/manifest.json'))['games']}
SRC = {g['source']: g for g in C.games(distinct=False)}
byk = defaultdict(list)
for x in X: byk[x['key']].append(x)
def one(key):
    g = SRC[MAN[key]]; m = C.meta(g['dir']); R = C.rounds(g['dir']); team = {c['id']: c['team'] for c in m['champions']}
    CH = {c['id']: c for c in R['champions']}
    T, TV = load(key); out = Counter()
    for x in byk[key]:
        L = T.get((x['r'], x['c']))
        if not L: continue
        j = x['r'] - 2; tt = L['TT'][0]; p = xy(tt['p'])
        tb = {int(b['h']): b for b in L['TB'] if b.get('s') == 'e'}
        for c in CH:
            if team[c] == g['us'] or not CH[c]['alive'][j]: continue
            q = (CH[c]['x'][j], CH[c]['y'][j])
            if C.cheb(q, p) > 8: continue
            b = tb.get(c)
            if b is None: out['no_belief'] += 1
            elif b.get('v') == '1': out['visible'] += 1
            else: out['unseen:' + b.get('src', '?')] += 1
            # was it visible to any ally this round? (extract sees field)
            i = j + 1
            seen_by_ally = any(c in CH[a]['sees'][i] for a in CH if team[a] == g['us'] and a != x['c'] and CH[a]['alive'][i])
            if not (b and b.get('v') == '1'): out['unseen_by_attacker_but_seen_by_ally' if seen_by_ally else 'unseen_by_whole_team'] += 1
    return out
if __name__ == '__main__':
    with ProcessPoolExecutor(30) as ex: res = list(ex.map(one, list(byk)))
    T = Counter()
    for o in res: T.update(o)
    print(T.most_common())
