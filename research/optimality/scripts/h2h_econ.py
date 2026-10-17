# Production breakdown in head-to-head ladder games: PTN Hyperion vs an opponent (same maps, usually same comp).
import json, gzip, os, sys, collections, statistics as st
ROOT = r'C:\Users\alext\Github\cambc-autumn\replays\.analysis'
OPP = sys.argv[1] if len(sys.argv) > 1 else 'procless'
US = 'PTN Hyperion'
idxj = json.load(open(os.path.join(ROOT, 'index.json'), encoding='utf-8'))
games = [g for g in idxj['games'] if g['kind'] == 'ladder' and g['ok'] and US in g['teams'] and OPP in g['teams']
         and g['source'].split('/')[2][:8] >= '20261016']
agg = {US: collections.defaultdict(float), OPP: collections.defaultdict(float)}
per_map = collections.defaultdict(lambda: collections.defaultdict(list))
W = 300  # first 300 rounds window for rates
for g in games:
    m = json.load(open(os.path.join(ROOT, g['dir'], 'meta.json'), encoding='utf-8'))
    ev = [json.loads(l) for l in gzip.open(os.path.join(ROOT, g['dir'], 'events.jsonl.gz'), 'rt')]
    R = json.load(gzip.open(os.path.join(ROOT, g['dir'], 'rounds.json.gz')))
    mp = json.load(open(os.path.join(ROOT, 'maps', m['map']['hash'] + '.json')))
    team = {c['id']: c['team'] for c in m['champions']}
    tname = g['teams']
    gtypes = {grp['id']: '+'.join(sorted(set(grp['types']))) for grp in mp['groups']}
    gside = {grp['id']: grp['side'] for grp in mp['groups']}
    for t in (0, 1):
        a = agg[tname[t]]
        a['games'] += 1
        a['rounds'] += min(W, m['result']['rounds'])
    for e in ev:
        if e['r'] > W: continue
        k = e['k']
        if k == 'capture':
            t = e['team']; a = agg[tname[t]]
            gems = sum(s[1] for s in e['shares']); gold = sum(s[2] for s in e['shares'])
            a['cap_gems'] += gems; a['cap_gold'] += gold; a['captures'] += 1
            own = gside.get(e['g'], -1) == t
            a['cap_gems_own_half' if own else 'cap_gems_other'] += gems
            a['cap_gems_' + gtypes.get(e['g'], '?')] += gems
        elif k == 'attack' and 'camp' in e:
            t = team[e['a']]; agg[tname[t]]['camp_attacks'] += 1
            agg[tname[t]]['camp_dmg'] += sum(x[1] for x in e.get('cdmg') or [])
        elif k == 'cast' and e.get('cdmg'):
            t = team[e['a']]; agg[tname[t]]['camp_dmg'] += sum(x[1] for x in e['cdmg'])
            agg[tname[t]]['camp_spell_dmg'] += sum(x[1] for x in e['cdmg'])
        elif k == 'camp_attack':
            t = team.get(e['tgt']);
            if t is not None: agg[tname[t]]['camp_dmg_taken'] += e['dmg']
        elif k == 'tribute_end':
            t = team[e['a']]; agg[tname[t]]['tributed'] += e['gems']; agg[tname[t]]['tributes'] += 1
        elif k == 'recall_end':
            t = team[e['a']]; agg[tname[t]]['recalls'] += 1
        elif k == 'death':
            t = team[e['v']]; agg[tname[t]]['bag_lost'] += e.get('gems', 0) or 0
            if not e.get('linked'): agg[tname[t]]['deaths'] += 1
        elif k == 'capture_reset':
            t = e['team']; agg[tname[t]]['capture_resets'] += 1
    # time budget from rounds: idle / dead / channel
    for c in R['champions']:
        t = c['team']; a = agg[tname[t]]
        for i, tr in enumerate(c['turn'][:W]):
            a['turn_' + str(tr)] += 1
            if c['alive'][i] and c['gems'][i] > 0: a['carry_rounds'] += 1
            if c['alive'][i]: a['carried_gems_sum'] += c['gems'][i]
    for t in (0, 1):
        per_map[m['map']['name']][tname[t]].append(R['gems'][t][min(W, len(R['gems'][t])) - 1])
print(f'{len(games)} games, first {W} rounds, per game:')
keys = sorted(set(agg[US]) | set(agg[OPP]))
for k in keys:
    if k in ('games', 'rounds'): continue
    u = agg[US][k] / max(1, agg[US]['games']); o = agg[OPP][k] / max(1, agg[OPP]['games'])
    print(f'  {k:32s} us {u:9.1f}  {OPP[:10]} {o:9.1f}  ratio {o / u if u else float("inf"):.2f}')
print('tributed gems at round 300 by map (mean): map, n, us, them')
for mname, d in sorted(per_map.items()):
    print(f'  {mname:14s} {len(d[US]):3d} {st.mean(d[US]):6.0f} {st.mean(d[OPP]):6.0f}')
