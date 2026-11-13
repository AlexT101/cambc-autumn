#!/usr/bin/env python3
"""Fish's non-Vesper bag spells in live r8 games: how each 50+ gem bag ends, and what we did while we saw it.

    python3 spells.py [EXT_DIR] [ROWS_JSON]

A spell is a run of rounds a Fish champion (not Vesper) is alive carrying 50+ gems. Its end: Fish tributed it,
we killed the carrier (its bag is ours), a camp killed it, or the game ended. 'opp' rounds are the ideation pass's:
one of ours sees the carrier, Fish's Vesper is more than 8 away from it (or dead), and 2+ of ours are within 6.
"""
import collections, gzip, json, os, sys, statistics as st

EXT = sys.argv[1] if len(sys.argv) > 1 else os.path.expanduser('~/tmp-offload/fishr8/live/ext')
ROWS = sys.argv[2] if len(sys.argv) > 2 else os.path.expanduser('~/tmp-offload/fishr8/live/rows-r8-all.json')
rows = json.load(open(ROWS))
cheb = lambda a, b: max(abs(a[0] - b[0]), abs(a[1] - b[1]))

out = collections.Counter()
spells = []
ng = 0
for d in sorted(os.listdir(EXT)):
    p = os.path.join(EXT, d)
    if not os.path.exists(p + '/meta.json'): continue
    m = json.load(open(p + '/meta.json'))
    key = os.path.basename(m['source']).split('.')[0]
    if key not in rows: continue
    r = rows[key]; P = m['draft']['picks']
    if 'our_picks' in r:
        cand = [t for t in (0, 1) if sorted(P[t]) == sorted(r['our_picks']) and sorted(P[1 - t]) == sorted(r['opp_picks'])]
    else:  # a local run (localrows.py): our bot is side a in NNN-map-12
        cand = [0 if r['side'] == 'a' else 1]
        r = dict(r, result='win' if m['result'].get('winner') == cand[0] else 'loss')
    if len(cand) != 1: continue
    us = cand[0]; ng += 1
    names = {c['id']: c['name'] for c in m['champions']}
    team = {c['id']: c['team'] for c in m['champions']}
    R = json.load(gzip.open(p + '/rounds.json.gz', 'rt'))
    C = R['champions']; n = len(R['round']); rnd = R['round']
    ours = [c for c in C if c['team'] == us]; fish = [c for c in C if c['team'] != us]
    fv = [c for c in fish if names[c['id']] == 'Vesper Vale']
    ev = [json.loads(l) for l in gzip.open(p + '/events.jsonl.gz', 'rt')]
    deaths = collections.defaultdict(list); tribs = collections.defaultdict(list); dmg = collections.defaultdict(float)
    for e in ev:
        if e['k'] == 'death': deaths[e['v']].append(e)
        elif e['k'] == 'tribute_end': tribs[e['a']].append(e)
        if e['k'] in ('attack', 'cast') and 'dmg' in e and team.get(e['a']) == us:
            for v, x in e['dmg']: dmg[(v, e['r'])] += x
    for f in fish:
        nm = names[f['id']]
        if nm == 'Vesper Vale': continue
        i = 0
        while i < n:
            if not (f['alive'][i] and f['gems'][i] >= 50): i += 1; continue
            j = i
            while j + 1 < n and f['alive'][j + 1] and f['gems'][j + 1] >= 50: j += 1
            r0, r1 = rnd[i], rnd[j]
            g = max(f['gems'][i:j + 1])
            # what ended it: the round after j
            end = 'game_end'
            dd = [e for e in deaths[f['id']] if r1 <= e['r'] <= r1 + 1]
            tt = [e for e in tribs[f['id']] if r1 <= e['r'] <= r1 + 1]
            if dd:
                b = dd[0].get('by')
                end = 'killed_by_us' if b is not None and team.get(b) == us else ('camp' if b is None else 'killed_by_fish?')
            elif tt: end = 'tribute'
            elif j + 1 < n: end = 'dropped'  # a gem count fall without an event in the window (tribute end off by one)
            seen = opp = opp1 = 0; hpf = []; ours_near = []; vd = []
            for k in range(i, j + 1):
                if not any(f['id'] in (o['sees'][k] or []) for o in ours if o['alive'][k]): continue
                seen += 1
                pos = (f['x'][k], f['y'][k])
                vfar = all((not v['alive'][k]) or cheb((v['x'][k], v['y'][k]), pos) > 8 for v in fv)
                near = sum(1 for o in ours if o['alive'][k] and cheb((o['x'][k], o['y'][k]), pos) <= 6)
                if vfar and near >= 1: opp1 += 1
                if vfar and near >= 2: opp += 1; hpf.append(f['hp'][k] / max(1, f['maxHp'][k])); ours_near.append(near)
            ourdmg = sum(dmg[(f['id'], rr)] for rr in range(r0, r1 + 2))
            spells.append(dict(game=key, champ=nm, r0=r0, r1=r1, len=r1 - r0 + 1, gems=g, end=end, seen=seen, opp=opp, opp1=opp1,
                               hpf=st.mean(hpf) if hpf else None, ourdmg=ourdmg, maxhp=f['maxHp'][i], result=r['result']))
            i = j + 1
print('games', ng, 'spells', len(spells))
json.dump(spells, open(os.path.expanduser(os.environ.get('SPELLS_OUT', '~/tmp-offload/bag-carrier-prey/spells-live.json')), 'w'))

def table(sel, label):
    S = [s for s in spells if sel(s)]
    if not S: return
    c = collections.Counter(s['end'] for s in S); gems = collections.Counter()
    for s in S: gems[s['end']] += s['gems']
    print(f"{label}: {len(S)} spells ({len(S)/ng:.2f}/game), {sum(s['len'] for s in S)/ng:.0f} rounds/game, bag gems {sum(s['gems'] for s in S)/ng:.0f}/game")
    for k, v in c.most_common(): print(f"   {k:16s} {v:4d} ({v/len(S):.0%})  gems/game {gems[k]/ng:.1f}")

table(lambda s: True, 'all spells')
table(lambda s: s['seen'] > 0, 'seen by us')
table(lambda s: s['opp1'] > 0, 'opp1 (Vesper far, 1+ of ours within 6)')
table(lambda s: s['opp'] > 0, 'opp (Vesper far, 2+ of ours within 6)')
table(lambda s: s['opp'] >= 3, 'opp >= 3 rounds')
print('\nby champion (all spells): spells/game, rounds/game, killed by us, tributed, mean bag')
by = collections.defaultdict(list)
for s in spells: by[s['champ']].append(s)
for k, S in sorted(by.items(), key=lambda kv: -sum(s['len'] for s in kv[1])):
    print(f"  {k:14s} {len(S)/ng:.2f} {sum(s['len'] for s in S)/ng:5.0f}  killed {sum(s['end']=='killed_by_us' for s in S):3d}  trib {sum(s['end'] in ('tribute','dropped') for s in S):3d}  opp-spells {sum(s['opp']>0 for s in S):3d}  bag {st.mean(s['gems'] for s in S):.0f}")
print('\nopp spells: carrier hp fraction (mean in opp rounds) quartiles, our damage dealt in spell')
O = [s for s in spells if s['opp'] > 0]
if O:
    h = sorted(s['hpf'] for s in O); print('  hpf q', [round(h[int(q * (len(h) - 1))], 2) for q in (0.1, 0.25, 0.5, 0.75, 0.9)])
    print('  dealt>0', sum(s['ourdmg'] > 0 for s in O), 'of', len(O), ' median dealt', st.median(s['ourdmg'] for s in O))
    for res in ('win', 'loss'):
        S = [s for s in O if s['result'] == res]; print(f"  {res}: {len(S)} opp spells, killed {sum(s['end']=='killed_by_us' for s in S)}")
