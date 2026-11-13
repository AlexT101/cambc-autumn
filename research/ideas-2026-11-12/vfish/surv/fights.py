"""fights.py EXT [--maxr 300] [--all]: for each early death (cand = team vfish*, and the reference's for comparison), the fight that led to it.
The fight starts at the first champion-damage event involving the victim (dealt or taken) in an unbroken run (gaps <= 4 rounds) ending at the death."""
import json, gzip, os, sys, collections, statistics as st
ext = sys.argv[1]
maxr = int(sys.argv[sys.argv.index('--maxr') + 1]) if '--maxr' in sys.argv else 300
lost_only = '--all' not in sys.argv
idx = json.load(open(ext + '/index.json'))['games']
def cheb(a, b): return max(abs(a[0] - b[0]), abs(a[1] - b[1]))
rows = {0: [], 1: []}  # 0 = cand deaths, 1 = ref deaths
ngames = 0
for g in idx:
    cand = 0 if g['teams'][0].startswith('vfish') else 1
    if lost_only and g['winner'] == cand: continue
    p = f"{ext}/{g['dir']}"; meta = json.load(open(p + '/meta.json'))
    typ = {c['id']: c['name'] for c in meta['champions']}; team = {c['id']: c['team'] for c in meta['champions']}
    if not any(typ[i] == 'Prism' and team[i] != cand for i in typ): continue
    ngames += 1
    R = json.load(gzip.open(p + '/rounds.json.gz'))
    ev = [json.loads(l) for l in gzip.open(p + '/events.jsonl.gz', 'rt')]
    ch = {c['id']: c for c in R['champions']}
    mp = json.load(open(f"{ext}/maps/{meta['map']['hash']}.json"))
    def spawn_c(t):
        s = mp['spawn'][t]; return ((s['minX'] + s['maxX']) / 2, (s['minY'] + s['maxY']) / 2)
    grp_tiles = {}
    for gr in mp['groups']:
        for t in gr['tiles']: grp_tiles[tuple(t)] = gr['id']
    camp_pos = [(c['x'], c['y']) for c in mp['camps']]
    # per-champion damage involvement by round
    inv = collections.defaultdict(list)  # id -> [(s, r, kind, other)]
    acts = collections.defaultdict(lambda: collections.defaultdict(list))
    for e in ev:
        k = e['k']
        if k in ('attack', 'cast'):
            a = e['a']
            for (t, d) in (e.get('dmg') or []):
                if t in typ and team[t] != team[a] and d > 0:
                    inv[a].append((e['s'], e['r'], 'dealt', t)); inv[t].append((e['s'], e['r'], 'taken', a))
            for t in (e.get('stun') or []):
                if t in typ and team[t] != team[a]: inv[t].append((e['s'], e['r'], 'taken', a)); inv[a].append((e['s'], e['r'], 'dealt', t))
        if k in ('move', 'attack', 'cast') : acts[e['a']][e['r']].append(e)
        if k == 'camp_attack' and e.get('tgt') in typ: acts[e['tgt']][e['r']].append(e)
    def pos(i, ri):
        c = ch[i]
        return (c['x'][ri], c['y'][ri]) if 0 <= ri < len(c['alive']) and c['alive'][ri] else None
    for e in ev:
        if e['k'] != 'death' or 'linked' in e or e['r'] > maxr: continue
        v = e['v']; side = 0 if team[v] == cand else 1; r = e['r']
        by = e.get('by'); bychamp = by in typ and team[by] != team[v]
        L = [x for x in inv[v] if x[1] <= r]
        # walk back the run
        start = None; last = r
        for x in reversed(L):
            if last - x[1] > 4: break
            start = x; last = x[1]
        row = {'killer': typ[by] if bychamp else 'camp', 'victim': typ[v], 'r': r}
        if start is None:
            row['nofight'] = 1; rows[side].append(row); continue
        r0 = start[1]; ri = r0 - 2
        me = pos(v, ri) or tuple(e['at'])
        row['len'] = r - r0 + 1
        row['init'] = start[2]  # dealt = victim struck first, taken = was struck first
        row['hp0'] = ch[v]['hp'][max(ri, 0)] / max(1, ch[v]['maxHp'][max(ri, 0)])
        al = [k for k in ch if team[k] == team[v] and k != v and pos(k, ri) and cheb(pos(k, ri), me) <= 5]
        en = [k for k in ch if team[k] != team[v] and pos(k, ri) and cheb(pos(k, ri), me) <= 6]
        row['al0'] = len(al); row['en0'] = len(en)
        # at the death
        rd = r - 2; md = pos(v, rd) or tuple(e['at'])
        row['al1'] = len([k for k in ch if team[k] == team[v] and k != v and pos(k, rd) and cheb(pos(k, rd), md) <= 5])
        row['en1'] = len([k for k in ch if team[k] != team[v] and pos(k, rd) and cheb(pos(k, rd), md) <= 6])
        so = spawn_c(team[v]); se = spawn_c(1 - team[v])
        row['own_half'] = cheb(me, so) <= cheb(me, se)
        row['spawn_d'] = cheb(me, so)
        row['on_group'] = me in grp_tiles
        row['near_camp'] = any(cheb(me, c) <= 4 for c in camp_pos)
        # distance moved toward own spawn over the fight
        row['home_gain'] = cheb(me, so) - cheb(tuple(e['at']), so)
        # victim's actions during the fight
        hits = sum(1 for rr in range(r0, r + 1) for a in acts[v][rr] if a['k'] in ('attack', 'cast') and any(t in typ for (t, d) in (a.get('dmg') or [])))
        moves = sum(1 for rr in range(r0, r + 1) for a in acts[v][rr] if a['k'] == 'move')
        camph = sum(1 for rr in range(r0, r + 1) for a in acts[v][rr] if a['k'] in ('attack', 'cast') and a.get('camp') is not None)
        campd = sum(a.get('dmg', 0) or 0 for rr in range(r0, r + 1) for a in acts[v][rr] if a['k'] == 'camp_attack')
        row['hits'] = hits; row['moves'] = moves; row['camph'] = camph; row['campd'] = campd
        # the 5 rounds before the fight: what was it doing
        pre_camp = sum(1 for rr in range(r0 - 5, r0) for a in acts[v][rr] if a['k'] in ('attack', 'cast') and a.get('camp') is not None)
        row['pre_camp'] = pre_camp > 0
        row['seen0'] = len(ch[v]['sees'][max(ri, 0)])
        rows[side].append(row)
print('games', ngames)
def frac(L, f): return sum(1 for x in L if f(x)) / max(1, len(L))
for side, name in ((0, 'CAND deaths'), (1, 'REF deaths')):
    L = rows[side]; F = [x for x in L if 'nofight' not in x]
    print(f"\n{name}: {len(L)} ({len(L)/ngames:.2f} a game), no champion fight before {len(L)-len(F)}")
    if not F: continue
    print(f"  fight length median {st.median(x['len'] for x in F)} rounds; victim struck first {frac(F, lambda x: x['init']=='dealt'):.2f}")
    print(f"  at fight start: hp {st.median(x['hp0'] for x in F):.2f} (under 0.5: {frac(F, lambda x: x['hp0']<0.5):.2f}), allies within 5 {st.mean(x['al0'] for x in F):.2f}, enemies within 6 {st.mean(x['en0'] for x in F):.2f}, outnumbered (en > al+1) {frac(F, lambda x: x['en0']>x['al0']+1):.2f}, sees0 {st.mean(x['seen0'] for x in F):.2f}")
    print(f"  at death: allies {st.mean(x['al1'] for x in F):.2f} enemies {st.mean(x['en1'] for x in F):.2f}")
    print(f"  own half {frac(F, lambda x: x['own_half']):.2f}; on a group tile {frac(F, lambda x: x['on_group']):.2f}; within 4 of a camp {frac(F, lambda x: x['near_camp']):.2f}; hitting a camp in the 5 rounds before {frac(F, lambda x: x['pre_camp']):.2f}; camp damage taken in fight >0 {frac(F, lambda x: x['campd']>0):.2f}")
    print(f"  in the fight: champion hits by victim {st.mean(x['hits'] for x in F):.2f}, moves {st.mean(x['moves'] for x in F):.2f}, camp hits {st.mean(x['camph'] for x in F):.2f}, steps gained toward spawn {st.mean(x['home_gain'] for x in F):.2f}")
    for lab, f in (('1 enemy', lambda x: x['en0'] <= 1), ('2 enemies', lambda x: x['en0'] == 2), ('3+ enemies', lambda x: x['en0'] >= 3)):
        s = [x for x in F if f(x)]
        if s: print(f"    {lab}: {len(s)} ({len(s)/len(F):.2f}) allies {st.mean(x['al0'] for x in s):.2f} hp0 {st.median(x['hp0'] for x in s):.2f} len {st.median(x['len'] for x in s)} struck first {frac(s, lambda x: x['init']=='dealt'):.2f}")
    c = collections.Counter(x['victim'] for x in L); print('  victims', c.most_common(8))
    c = collections.Counter(x['killer'] for x in L); print('  killers', c.most_common(8))
    for a, b in ((0, 60), (60, 120), (120, 200), (200, 300)):
        s = [x for x in L if a < x['r'] <= b]; print(f"  r{a}-{b}: {len(s)}", end='')
    print()
