"""rrun.py EXT: what the turns of the final retreat run before each early death did."""
import sys, collections, statistics as st
sys.path.insert(0, '/home/ubuntu/cambc-autumn/research/ideas-2026-11-12/vfish/surv')
from tracelib import *
ext = sys.argv[1]
C = collections.Counter(); runs = 0; perrun = collections.Counter()
for gm in games(ext):
    typ = gm.typ; team = gm.team; cand = gm.cand; so = gm.spawn_c(cand)
    for d in gm.deaths(300):
        v = d['v']; r = d['r']; c = gm.ch[v]
        k = 1
        while gm.dec(v, r - k) == 'R': k += 1
        if k == 1: continue
        runs += 1; anymove = False; home = 0
        for rr in range(r - k + 1, r):
            tcode = c['turn'][rr - 1]
            mv = [e for e in gm.byr[rr] if e.get('a') == v and (e['k'] == 'move' or (e['k'] == 'cast' and e.get('moved')))]
            hit = any(e.get('a') == v and e['k'] in ('attack', 'cast') and any(t in typ for (t, dm) in (e.get('dmg') or [])) for e in gm.byr[rr])
            rec = any(e.get('a') == v and e['k'] == 'recall_start' for e in gm.byr[rr])
            if tcode == 5: C['stunned'] += 1
            elif tcode == 6: C['out of fuel'] += 1
            elif not mv: C['no move' + (' (hit a champion)' if hit else '')] += 1
            else:
                f = tuple(mv[0]['f']); to = tuple(mv[-1].get('moved') or mv[-1]['to'])
                g = cheb(f, so) - cheb(to, so)
                # nearest enemy distance change
                en = [gm.pos(x, rr - 1) for x in gm.ch if team[x] != cand and gm.pos(x, rr - 1)]
                dn0 = min((cheb(f, p) for p in en), default=99); dn1 = min((cheb(to, p) for p in en), default=99)
                C['moved nearer spawn' if g > 0 else 'moved level' if g == 0 else 'moved away from spawn'] += 1
                C['  move: gap to nearest enemy ' + ('grew' if dn1 > dn0 else 'same' if dn1 == dn0 else 'shrank')] += 1
                home += max(0, g)
        perrun[min(home, 5)] += 1
tot = sum(v for k, v in C.items() if not k.startswith('  '))
print(runs, 'final retreat runs;', tot, 'retreat turns')
for k, v in sorted(C.items(), key=lambda kv: -kv[1]): print(f"  {v:4d} {v/tot:.2f} {k}")
print('steps gained toward spawn per run:', sorted(perrun.items()))
