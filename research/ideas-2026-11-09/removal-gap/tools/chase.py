"""Chase episodes of team T's champions on carriers of the other team (5+ gems): at round r a T champion is 4-8 from
the carrier and 3 rounds later 2+ closer (and within 5). Over r..r+12: damage target->chaser team, chaser team->target,
target killed by T, chaser killed, target's distance to its nearest altar change, gems the target banked."""
import beh, json, sys, os, collections
from multiprocessing import Pool
import lockcut_run as L
def episodes(d, T):
    meta, rd, ev = beh.load(d)
    ch = rd['champions']; R = rd['round']; n = len(R)
    team = {c['id']: c['team'] for c in ch}
    byid = {c['id']: c for c in ch}
    ri = {r: i for i, r in enumerate(R)}
    dmg = collections.defaultdict(float)  # (round, src, dst)
    deaths = {}
    for e in ev:
        if e['k'] in ('attack', 'cast'):
            for tgt, amt in e.get('dmg', []) or []:
                dmg[(e['r'], e['a'], tgt)] += amt
        elif e['k'] == 'death':
            deaths.setdefault(e['v'], []).append((e['r'], e.get('by')))
    out = []
    for c in ch:  # chaser
        if c['team'] != T: continue
        last = -99
        for i in range(n - 3):
            if not c['alive'][i] or i - last < 10: continue
            for o in ch:
                if o['team'] == T or not o['alive'][i] or o['gems'][i] < 5: continue
                d0 = max(abs(o['x'][i] - c['x'][i]), abs(o['y'][i] - c['y'][i]))
                if not 4 <= d0 <= 8 or not (o['alive'][i + 3] and c['alive'][i + 3]): continue
                d3 = max(abs(o['x'][i + 3] - c['x'][i + 3]), abs(o['y'][i + 3] - c['y'][i + 3]))
                if d3 > min(5, d0 - 2): continue
                r = R[i]; w = range(r, r + 13)
                ours = [x['id'] for x in ch if x['team'] == T]
                tin = sum(dmg[(rr, o['id'], a)] for rr in w for a in ours)
                tout = sum(dmg[(rr, a, o['id'])] for rr in w for a in ours)
                tk = any(r <= dr <= r + 12 and team.get(by) == T for dr, by in deaths.get(o['id'], []))
                ck = any(r <= dr <= r + 12 for dr, by in deaths.get(c['id'], []))
                d6 = max(abs(o['x'][i + 6] - c['x'][i + 6]), abs(o['y'][i + 6] - c['y'][i + 6])) if i + 6 < n and o['alive'][i + 6] and c['alive'][i + 6] else -1
                mates = sum(1 for x in ch if x['team'] == o['team'] and x['id'] != o['id'] and x['alive'][i] and max(abs(x['x'][i] - o['x'][i]), abs(x['y'][i] - o['y'][i])) <= 4)
                helpers = sum(1 for x in ch if x['team'] == T and x['id'] != c['id'] and x['alive'][i] and max(abs(x['x'][i] - o['x'][i]), abs(x['y'][i] - o['y'][i])) <= 6)
                out.append({'d6': d6, 'mates': mates, 'helpers': helpers, 'gems': o['gems'][i], 'hp': o['hp'][i] / o['maxHp'][i], 'chp': c['hp'][i] / c['maxHp'][i], 'tin': tin, 'tout': tout,
                            'tk': tk, 'ck': ck, 'type': o.get('id')})
                last = i; break
    return out
def run(j):
    k, d, T = j
    try: return (k, episodes(d, T))
    except Exception as e: return (k, [])
if __name__ == '__main__':
    A = sys.argv[1]; jobs = L.jl() + (L.jloc(A, 1) + L.jloc(A, 0) if A != '-' else [])
    with Pool(40) as p: res = p.map(run, jobs, chunksize=4)
    G = collections.defaultdict(list); N = collections.Counter()
    for k, o in res: G[k] += o; N[k] += 1
    import statistics as st
    for k, E in G.items():
        for lab, sel in (('5-39', lambda e: e['gems'] < 40), ('40+', lambda e: e['gems'] >= 40)):
            S = [e for e in E if sel(e)]
            if not S: continue
            print(f"{k:14} bag {lab:5} n={len(S)/N[k]:.2f}/g  target killed {st.mean(e['tk'] for e in S):.3f} chaser died {st.mean(e['ck'] for e in S):.3f}"
                  f"  dmg target->us {st.mean(e['tin'] for e in S):.0f} us->target {st.mean(e['tout'] for e in S):.0f}  ratio {st.mean(e['tin'] for e in S)/max(1,st.mean(e['tout'] for e in S)):.2f}  tgt hp {st.mean(e['hp'] for e in S):.2f}  d6>=6 {st.mean(e['d6']>=6 for e in S if e['d6']>=0):.2f} d6<=2 {st.mean(0<=e['d6']<=2 for e in S if e['d6']>=0):.2f} mates {st.mean(e['mates'] for e in S):.2f} helpers {st.mean(e['helpers'] for e in S):.2f}")
