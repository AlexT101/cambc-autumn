#!/usr/bin/env python3
"""What our near units do in 'opp' rounds (a Fish non-Vesper 50+ carrier seen, Fish's Vesper >8 away, 2+ of ours within 6).

For each of ours within 6 of the carrier: does it close in next round, hold, or back off; does it hit the carrier
that round; its own health fraction. Also whether the carrier is tributing (a tribute_start..end window covers k).
"""
import collections, gzip, json, os, sys, statistics as st

EXT = os.path.expanduser('~/tmp-offload/fishr8/live/ext')
rows = json.load(open(os.path.expanduser('~/tmp-offload/fishr8/live/rows-r8-all.json')))
cheb = lambda a, b: max(abs(a[0] - b[0]), abs(a[1] - b[1]))
acts = collections.Counter(); tot = collections.Counter(); ng = 0
byend = collections.defaultdict(collections.Counter)
spells = {(s['game'], s['champ'], s['r0']): s for s in json.load(open(os.path.expanduser('~/tmp-offload/bag-carrier-prey/spells-live.json')))}
for d in sorted(os.listdir(EXT)):
    p = os.path.join(EXT, d)
    if not os.path.exists(p + '/meta.json'): continue
    m = json.load(open(p + '/meta.json'))
    key = os.path.basename(m['source']).split('.')[0]
    if key not in rows: continue
    r = rows[key]; P = m['draft']['picks']
    cand = [t for t in (0, 1) if sorted(P[t]) == sorted(r['our_picks']) and sorted(P[1 - t]) == sorted(r['opp_picks'])]
    if len(cand) != 1: continue
    us = cand[0]; ng += 1
    names = {c['id']: c['name'] for c in m['champions']}; team = {c['id']: c['team'] for c in m['champions']}
    R = json.load(gzip.open(p + '/rounds.json.gz', 'rt')); C = R['champions']; n = len(R['round']); rnd = R['round']
    ours = [c for c in C if c['team'] == us]; fish = [c for c in C if c['team'] != us]
    fv = [c for c in fish if names[c['id']] == 'Vesper Vale']
    ev = [json.loads(l) for l in gzip.open(p + '/events.jsonl.gz', 'rt')]
    hit = set(); trib = collections.defaultdict(list); tstart = {}
    for e in ev:
        if e['k'] in ('attack', 'cast') and 'dmg' in e and team.get(e['a']) == us:
            for v, x in e['dmg']: hit.add((e['a'], v, e['r']))
        if e['k'] == 'tribute_start': tstart[e['a']] = e['r']
        if e['k'] in ('tribute_end', 'tribute_cancel') and e['a'] in tstart: trib[e['a']].append((tstart.pop(e['a']), e['r']))
    idx = {rr: k for k, rr in enumerate(rnd)}
    for f in fish:
        if names[f['id']] == 'Vesper Vale': continue
        spell = None
        for k in range(n - 1):
            if not (f['alive'][k] and f['gems'][k] >= 50): spell = None; continue
            if spell is None:
                spell = spells.get((key, names[f['id']], rnd[k]))
            if not any(f['id'] in (o['sees'][k] or []) for o in ours if o['alive'][k]): continue
            pos = (f['x'][k], f['y'][k])
            if not all((not v['alive'][k]) or cheb((v['x'][k], v['y'][k]), pos) > 8 for v in fv): continue
            near = [o for o in ours if o['alive'][k] and cheb((o['x'][k], o['y'][k]), pos) <= 6]
            if len(near) < 2: continue
            tot['opp_rounds'] += 1
            tributing = any(a <= rnd[k] <= b for a, b in trib[f['id']])
            tot['carrier_tributing'] += tributing
            fishnear = sum(1 for g in fish if g is not f and g['alive'][k] and cheb((g['x'][k], g['y'][k]), pos) <= 6)
            tot['fish_allies_within6'] += fishnear
            end = spell['end'] if spell else '?'
            for o in near:
                d0 = cheb((o['x'][k], o['y'][k]), pos)
                if not o['alive'][k + 1]: a = 'died'
                elif not f['alive'][k + 1] or f['x'][k + 1] is None: a = 'carrier_died'
                else:
                    d1 = cheb((o['x'][k + 1], o['y'][k + 1]), (f['x'][k + 1], f['y'][k + 1]))
                    a = 'closer' if d1 < d0 else ('same' if d1 == d0 else 'away')
                h = (o['id'], f['id'], rnd[k]) in hit
                acts[a] += 1; acts['hit'] += h; acts['unit_rounds'] += 1
                byend[end][a] += 1; byend[end]['hit'] += h; byend[end]['n'] += 1
                if not h: acts['nohit_d%d' % min(d0, 5)] += 1
                acts['ourhp<0.5'] += o['hp'][k] < 0.5 * o['maxHp'][k]
print('games', ng)
for k, v in tot.items(): print(k, round(v / ng, 2), '/game')
print('unit-rounds', acts['unit_rounds'])
for k in ('closer', 'same', 'away', 'died', 'carrier_died', 'hit', 'ourhp<0.5'): print(f'  {k:10s} {acts[k]/acts["unit_rounds"]:.0%}')
print('  no hit by distance:', {k: acts[k] for k in sorted(acts) if k.startswith('nohit')})
for e, c in byend.items(): print(f"  spell end {e:14s} n {c['n']:5d}  closer {c['closer']/c['n']:.0%} away {c['away']/c['n']:.0%} hit {c['hit']/c['n']:.0%}")
