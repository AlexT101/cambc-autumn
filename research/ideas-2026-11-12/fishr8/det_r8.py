"""opp_detect's Fish rule on Fish r8: det3 (bcexploit's mirror of opp_detect.cc) as is, and with the r8 fix: a value of
2^20 or more in size is read as v >> 20 (Fish r8 writes old << 20 plus 20 random bits) and Heart of Ruin ranks after
Varg on the base-health tie. Shares of instances per called class by round; also the other teams' datasets with the
fix, for false Fish reads.   py det_r8.py"""
import os, sys, pickle, collections
sys.path.insert(0, '/home/ubuntu/cambc-autumn/research/ideas-2026-11-12/bcexploit')
import det3
H = os.path.expanduser('~/tmp-offload/fishr8/'); B = os.path.expanduser('~/tmp-offload/bcexploit/')
r8 = [s for s in pickle.load(open(H + 'oppd-r8.pkl', 'rb')) if s['team'] == 'Intercontinental Fish']
r2 = [s for s in pickle.load(open(H + 'oppd-r2.pkl', 'rb')) if s['team'] == 'Intercontinental Fish']
print('== det3 as is'); det3.score({'Fish r8 (live)': r8, 'Fish r2 (live)': r2})
orig = det3.fish_token
def fixed(v, n, rank, hp, maxhp, shield, gems):
    if abs(v) >= 1 << 20: v >>= 20
    return orig(v, n, rank, hp, maxhp, shield, gems)
det3.fish_token = fixed; det3.TIE['Heart of Ruin'] = 12
print('== det3 with the r8 fix'); det3.score({'Fish r8 (live)': r8, 'Fish r2 (live)': r2})
G = collections.defaultdict(list)
for f in ('ds_scrim.pkl', 'ds_ladder.pkl'):
    if not os.path.exists(B + f): continue
    for s in pickle.load(open(B + f, 'rb')):
        t = s['team']
        if t in ('Mite', 'BattleCats', 'Intercontinental Fish'): G[f'{t} {f[3:-4]}'].append(s)
        elif t != 'stellar best girl': G[f'others {f[3:-4]}'].append(s)
print('== other datasets with the fix'); det3.score({k: v[:1200] for k, v in sorted(G.items())})
