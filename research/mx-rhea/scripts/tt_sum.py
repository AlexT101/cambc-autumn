"""Summaries of tt_pursuit.py's pickle: unproductive pursuits (no hit on the group, no capture share) by how they
ended, their rounds and the rounds that did not advance the next target, per team-game, winners vs losers.
Usage: py tt_sum.py PKL [RMAX]"""
import pickle, sys
from collections import defaultdict, Counter

rows, rfs = pickle.load(open(sys.argv[1], 'rb'))
RMAX = int(sys.argv[2]) if len(sys.argv) > 2 else 600
games = sorted({r['game'] for r in rows})
tg = {(r['game'], r['team']): r['win'] for r in rows}
nW = sum(1 for v in tg.values() if v); nL = len(tg) - nW
alive_rounds = defaultdict(int)
for r in rows:
    if r['r0'] <= RMAX: alive_rounds[r['win']] += r['n']


def cat(r):
    if r['hits'] or r['share']: return 'productive'
    st = r['st1'] or (None, None, None, None)
    if r['died']: return 'died'
    if r['team'] in r['tcap'] or (st[0] == 2 and st[1] == r['team']): return 'ally took it'
    if (1 - r['team']) in r['tcap'] or (st[0] == 2 and st[1] == 1 - r['team']): return 'enemy took it'
    if st[0] == 3: return 'respawning (start)' if (r['st0'] or (0,))[0] == 3 else 'respawning (end)'
    if r['seen_end'] or r['nxt_br'] in ('R', 'C'): return 'enemy in view'
    if r['ally_on']: return 'ally on it'
    if r['nxt_br'] in ('K', 'k', 'S', 'B', 'W', 'T', 'H', 'E', 'G', 'X'): return 'branch ' + r['nxt_br']
    return 'retarget (no visible cause)'


def lost(r):
    a = r['adv_next']
    return r['n'] - max(0, a) if a is not None else r['n']


print(f'pursuits starting r<={RMAX}; team-games W {nW} L {nL}; pursuit-rounds W {alive_rounds[1]} L {alive_rounds[0]}')
T = defaultdict(lambda: [0, 0, 0, 0, 0, 0])  # cat -> [count W, count L, rounds W, rounds L, lost W, lost L]
for r in rows:
    if r['r0'] > RMAX or r['n'] < 3: continue
    c = cat(r)
    if c == 'productive': continue
    w = r['win']
    t = T[c]; t[1 - w] += 1; t[3 - w] += r['n']; t[5 - w] += lost(r)
print(f"{'unproductive pursuits (n>=3)':32s} {'perTG W':>8s} {'L':>6s} {'rounds/TG W':>11s} {'L':>6s} {'lost/TG W':>9s} {'L':>6s}")
for c, t in sorted(T.items(), key=lambda x: -(x[1][4] + x[1][5])):
    print(f'{c:32s} {t[0]/nW:8.1f} {t[1]/nL:6.1f} {t[2]/nW:11.1f} {t[3]/nL:6.1f} {t[4]/nW:9.1f} {t[5]/nL:6.1f}')
tot = [sum(t[i] for t in T.values()) for i in range(6)]
print(f"{'total':32s} {tot[0]/nW:8.1f} {tot[1]/nL:6.1f} {tot[2]/nW:11.1f} {tot[3]/nL:6.1f} {tot[4]/nW:9.1f} {tot[5]/nL:6.1f}")
