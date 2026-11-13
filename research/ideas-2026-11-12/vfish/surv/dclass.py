"""dclass.py EXT [--maxr 300]: classify the candidate's early deaths from the trace."""
import sys, collections, random, statistics as st
sys.path.insert(0, '/home/ubuntu/cambc-autumn/research/ideas-2026-11-12/vfish/surv')
from tracelib import *
ext = sys.argv[1]; maxr = int(sys.argv[sys.argv.index('--maxr') + 1]) if '--maxr' in sys.argv else 300
rows = []
ngames = 0
for gm in games(ext):
    ngames += 1
    typ = gm.typ; team = gm.team; cand = gm.cand
    for d in gm.deaths(maxr):
        v = d['v']; r = d['r']; c = gm.ch[v]
        by = d.get('by'); killer = typ[by] if by in typ and team[by] != cand else 'camp'
        def hp(rr):  # share at the start of round rr
            i = rr - 2
            return c['hp'][i] / max(1, c['maxHp'][i]) if i >= 0 and c['alive'][i] else None
        def near(rr, rad, enemy=True):
            me = gm.pos(v, rr - 1)
            if me is None: return []
            return [k for k in gm.ch if (team[k] != cand) == enemy and k != v and gm.pos(k, rr - 1) and cheb(gm.pos(k, rr - 1), me) <= rad]
        # final R run
        k = 1; run = 0
        while gm.dec(v, r - k) == 'R': run += 1; k += 1
        t0 = r - k  # last non-R turn
        row = {'victim': typ[v], 'killer': killer, 'r': r, 'run': run, 'win': gm.win, 'game': gm.g['source'].split('/')[-1]}
        row['d0'] = gm.dec(v, r)
        row['dec_t0'] = gm.dec(v, t0)
        row['hp_t0'] = hp(t0); row['hp_run'] = hp(t0 + 1); row['hp_1'] = hp(r - 1); row['hp_3'] = hp(r - 3); row['hp_6'] = hp(r - 6)
        wh = gm.lines(v, t0 + 1, 'WH'); row['wh_run'] = wh[0][6] if wh and run > 0 else '-'
        row['en_t0'] = len(near(t0, 6)); row['al_t0'] = len(near(t0, 5, False))
        row['en_run'] = len(near(t0 + 1, 6)); row['al_run'] = len(near(t0 + 1, 5, False))
        stl = gm.lines(v, t0, 'ST'); row['st_t0'] = (stl[0][5], stl[0][6]) if stl else None
        # damage taken from champions before the run start
        took_before = False
        for rr in range(max(1, t0 - 2), t0 + 1):
            for e in gm.byr[rr]:
                if e['k'] in ('attack', 'cast') and any(x[0] == v for x in (e.get('dmg') or [])): took_before = True
        row['hit_before_run'] = took_before
        # flaps: R -> non-R transitions in the 15 rounds before death while an enemy within 8
        seq = ''.join(gm.dec(v, rr) for rr in range(max(1, r - 15), r))
        row['seq'] = seq
        row['flaps'] = sum(1 for i in range(len(seq) - 1) if seq[i] == 'R' and seq[i + 1] in 'FCAPXBG')
        # hurt work: turns in the last 10 rounds with D in F/C/A/X/G/B, hp < 0.5, an enemy within 8
        hw = 0
        for rr in range(max(2, r - 10), r):
            h = hp(rr)
            if h is not None and h < 0.5 and gm.dec(v, rr) in 'FCAXGBP' and near(rr, 8): hw += 1
        row['hurt_work'] = hw
        row['chase'] = sum(1 for rr in range(max(1, r - 6), r) if gm.dec(v, rr) == 'C')
        so = gm.spawn_c(cand); row['spawn_d'] = cheb(tuple(d['at']), so); 
        # home progress during the run
        p0 = gm.pos(v, t0)
        row['home_gain'] = (cheb(p0, so) - cheb(tuple(d['at']), so)) if p0 else None
        # stunned turns during the last 4 rounds
        row['stunned'] = sum(1 for rr in range(max(1, r - 4), r + 1) if c['turn'][rr - 1] == 5)
        row['oof'] = sum(1 for rr in range(max(1, r - 4), r + 1) if c['turn'][rr - 1] == 6)
        rows.append(row)
N = len(rows); print(ngames, 'games,', N, 'deaths by r', maxr, f'({N/ngames:.2f} a game)')
def frac(L, f): return f"{sum(1 for x in L if f(x))}/{len(L)} ({sum(1 for x in L if f(x)) / max(1, len(L)):.2f})"
med = lambda L: (round(st.median(L), 2) if L else None)
print('final R run length:', collections.Counter(min(x['run'], 8) for x in rows).most_common())
print('hp share at -6/-3/-1:', med([x['hp_6'] for x in rows if x['hp_6'] is not None]), med([x['hp_3'] for x in rows if x['hp_3'] is not None]), med([x['hp_1'] for x in rows if x['hp_1'] is not None]))
print('stunned in last 4 rounds:', frac(rows, lambda x: x['stunned'] > 0), ' out of fuel:', frac(rows, lambda x: x['oof'] > 0))
print('flaps (R then work) in the last 15 rounds: 1+', frac(rows, lambda x: x['flaps'] >= 1), ' 2+', frac(rows, lambda x: x['flaps'] >= 2))
print('hurt work turns (hp<0.5, enemy within 8, F/C/A/X/G/B/P) in last 10: 1+', frac(rows, lambda x: x['hurt_work'] >= 1), '3+', frac(rows, lambda x: x['hurt_work'] >= 3))
print('a chase turn in the last 6:', frac(rows, lambda x: x['chase'] >= 1))
R = [x for x in rows if x['run'] > 0]
print(f"\nwith a final retreat run: {len(R)}; at the run's first turn: hp {med([x['hp_run'] for x in R if x['hp_run'] is not None])}, reason", collections.Counter(x['wh_run'] for x in R).most_common(), 'enemies within 6', round(st.mean(x['en_run'] for x in R), 2), 'allies within 5', round(st.mean(x['al_run'] for x in R), 2))
print('   hit by a champion in the 3 rounds before the run:', frac(R, lambda x: x['hit_before_run']), '| steps gained toward spawn in the run: median', med([x['home_gain'] for x in R if x['home_gain'] is not None]), '| run hp>=0.6 at start', frac(R, lambda x: (x['hp_run'] or 0) >= 0.6), ' hp<0.32', frac(R, lambda x: (x['hp_run'] or 0) < 0.3155))
print('   branch on the turn before the run:', collections.Counter(x['dec_t0'] for x in R).most_common(8), '| ST there (lost, self_falls):', collections.Counter(x['st_t0'] for x in R).most_common(5))
Z = [x for x in rows if x['run'] == 0]
print(f"no retreat before death: {len(Z)}; last branch", collections.Counter(x['dec_t0'] for x in Z).most_common(8), 'hp -1:', med([x['hp_1'] for x in Z if x['hp_1'] is not None]), 'hp -3', med([x['hp_3'] for x in Z if x['hp_3'] is not None]), 'killers', collections.Counter(x['killer'] for x in Z).most_common(5))
for lab, f in (('wins', lambda x: x['win']), ('losses', lambda x: not x['win'])):
    s = [x for x in rows if f(x)]; print(lab, len(s))
import json; json.dump(rows, open('/home/ubuntu/cambc-autumn/research/ideas-2026-11-12/vfish/surv/dclass.json', 'w'))
