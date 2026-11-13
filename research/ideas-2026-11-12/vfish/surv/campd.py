"""campd.py EXT [--show N]: camp deaths of both teams by r300: counts, and timelines of the candidate's with no enemy near."""
import sys, collections
sys.path.insert(0, '/home/ubuntu/cambc-autumn/research/ideas-2026-11-12/vfish/surv')
from tracelib import *
ext = sys.argv[1]; show = int(sys.argv[sys.argv.index('--show') + 1]) if '--show' in sys.argv else 0
C = collections.Counter(); ng = 0; shown = 0
for gm in games(ext):
    ng += 1; typ = gm.typ; team = gm.team; cand = gm.cand
    camps = {c['id']: c for c in gm.map['camps']}
    for ours in (True, False):
        for d in gm.deaths(300, ours):
            by = d.get('by'); champ = by in typ and team[by] != team[d['v']]
            if champ: continue
            C['cand' if ours else 'ref'] += 1
            v = d['v']; r = d['r']; c = gm.ch[v]
            me = tuple(d['at'])
            en = [k for k in gm.ch if team[k] != team[v] and gm.pos(k, r - 1) and cheb(gm.pos(k, r - 1), me) <= 8]
            # champion damage in the last 6 rounds
            cdmg = sum(dm for rr in range(max(1, r - 6), r + 1) for e in gm.byr[rr] if e['k'] in ('attack', 'cast') for (t, dm) in (e.get('dmg') or []) if t == v)
            kind = 'no champion damage in 6 rounds' if cdmg == 0 else 'with champion damage'
            C[('cand ' if ours else 'ref ') + kind] += 1
            if ours and cdmg == 0 and shown < show:
                shown += 1
                print(f"\n=== {gm.g['source'].split('/')[-1]} {typ[v]}#{v} r{r} at {d['at']} camp {d.get('camp')} {camps.get(d.get('camp'), {}).get('type')}")
                for rr in range(max(2, r - 9), r + 1):
                    p = gm.pos(v, rr - 1)
                    if p is None: continue
                    al = [(typ[k][:4], cheb(gm.pos(k, rr - 1), p), int(gm.ch[k]['hp'][rr - 2])) for k in gm.ch if team[k] == cand and k != v and gm.pos(k, rr - 1) and cheb(gm.pos(k, rr - 1), p) <= 6]
                    wh = gm.lines(v, rr, 'WH')
                    hits = [(e['g'], camps[e['camp']]['type'][:5], int(e.get('dmg') or 0)) for e in gm.byr[rr] if e['k'] == 'camp_attack' and e.get('tgt') == v]
                    other = [(typ[e['tgt']][:4], camps[e['camp']]['type'][:5], int(e.get('dmg') or 0)) for e in gm.byr[rr] if e['k'] == 'camp_attack' and e.get('tgt') in typ and e.get('tgt') != v and team[e['tgt']] == cand]
                    acts = [(e['k'], e.get('to') if e['k'] == 'move' else ('camp' if e.get('camp') is not None else typ.get(e.get('tgt')))) for e in gm.byr[rr] if e.get('a') == v and e['k'] in ('move', 'attack', 'cast')]
                    deaths = [typ[e['v']] for e in gm.byr[rr] if e['k'] == 'death']
                    print(f"  r{rr} D={gm.dec(v, rr)} WH={wh[0][6] if wh else '-'} at {p} hp {int(c['hp'][rr-2])}/{int(c['maxHp'][rr-2])} | camp hits on me {hits} on allies {other} | acts {acts} | allies {al} {'deaths ' + str(deaths) if deaths else ''}")
print(ng, 'games'); [print(' ', v, k) for k, v in sorted(C.items(), key=str)]
