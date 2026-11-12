"""Fish's economy to round R (default 150), live or local (stats rows): gold by source (capture shares, kills, other),
captures and capture gold by group kind, holders per capture, Vesper's holds, group gold paid vs base, and which of
the map's groups (own-side / middle / enemy-side, by spawn distance) it takes.   py opening.py EXT ROWS.json [R]"""
import json, os, sys, collections, statistics as st
sys.path.insert(0, '/home/ubuntu/cambc-autumn/research/ideas-2026-11-12/mitefit')
from mstats import load
ext, rf = sys.argv[1:3]; RR = int(sys.argv[3]) if len(sys.argv) > 3 else 150
rows = json.load(open(rf)); idx = json.load(open(ext + '/index.json'))['games']
cheb = lambda a, b: max(abs(a[0] - b[0]), abs(a[1] - b[1]))
T = collections.Counter(); kind = collections.Counter(); kgold = collections.Counter(); hold = []; base = paid = 0; N = 0
for g in idx:
    mid = os.path.basename(g['source'])[:-8]
    if mid not in rows: continue
    fish = 1 if rows[mid]['side'] == 'a' else 0
    try: meta, R, ev, mp = load(ext, g['dir'])
    except Exception: continue
    n = len(R['round'])
    if n < RR: continue
    N += 1; typ = {c['id']: c['name'] for c in meta['champions']}; team = {c['id']: c['team'] for c in meta['champions']}
    G = {x['id']: x for x in mp['groups']}
    sp = [((s['minX'] + s['maxX']) / 2, (s['minY'] + s['maxY']) / 2) for s in mp['spawn']]
    T['earned'] += sum(c['earned'][RR - 1] for c in R['champions'] if c['team'] == fish)
    for e in ev:
        if e['r'] > RR: break
        if e['k'] == 'capture' and e['team'] == fish:
            gr = G[e['g']]; k = 'monolith' if 'Monolith' in gr['types'] else 'golem' if 'Golem' in gr['types'] else 'elk' if 'Elk' in gr['types'] else 'wolf' if 'Wolf' in gr['types'] else 'cluster'
            c0 = gr['tiles'][0]; d0, d1 = cheb(c0, sp[fish]), cheb(c0, sp[1 - fish]); loc = 'own' if d0 < d1 - 3 else 'enemy' if d1 < d0 - 3 else 'mid'
            go = sum(x[2] for x in e['shares']); kind[(k, loc)] += 1; kgold[k] += go; T['capgold'] += go; T['caps'] += 1
            base += gr['gold']; paid += go; hold.append(len(e['shares']))
            if any(typ[x[0]] == 'Vesper Vale' for x in e['shares']): T['vcaps'] += 1
        elif e['k'] == 'death' and e.get('by') in team and team[e['by']] == fish and team[e['v']] != fish: T['kills'] += 1
print(f'{N} games, to r{RR}: earned {T["earned"] / N:.0f}, capture gold {T["capgold"] / N:.0f} ({T["caps"] / N:.1f} captures, '
      f'{T["capgold"] / max(1, T["caps"]):.0f} a capture; paid / base gold {paid / max(1, base):.2f}), kills {T["kills"] / N:.2f}, '
      f'holders {st.mean(hold) if hold else 0:.2f}, Vesper holds {T["vcaps"] / max(1, T["caps"]):.2f}')
print('  captures a game by kind/location:', {f'{k}/{l}': round(v / N, 2) for (k, l), v in sorted(kind.items())})
print('  capture gold a game by kind:', {k: round(v / N) for k, v in sorted(kgold.items())})
