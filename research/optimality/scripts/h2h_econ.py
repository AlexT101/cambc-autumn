"""Production breakdown in the first 300 rounds: captures and gems by camp type, camp damage, recalls, tributes,
deaths, carried gem-rounds, time budget; then rates per pick-round (one pick = one champion, Cassi and Issac
together), bag size at tribute, and Monolith groups on maps that have one.

  py h2h_econ.py procless                                     # the report: PTN Hyperion vs procless head to head
  py h2h_econ.py --team procless "Intercontinental Fish"      # any team's ladder games, whatever the opponent
  py h2h_econ.py --src replays/batch-20261017-091937-928141 --team nemesis
Selection options: gamesel.py.
"""
import json, gzip, os, sys, collections, statistics as st
import gamesel
ROOT = gamesel.ROOT
US = 'PTN Hyperion'
W = 300  # first 300 rounds window for rates

p = gamesel.parser(__doc__)
p.add_argument('opp', nargs='?', help="PTN Hyperion's head-to-head games against OPP, every source copy (the report)")
a = p.parse_args()
legacy = a.opp is not None or not a.team
OPP = a.opp or 'procless'
if legacy:
    a.team, a.together, a.copies = [US, OPP], True, True
teams = list(a.team)
games = gamesel.select(a)
agg = collections.defaultdict(lambda: collections.defaultdict(float))
bags = collections.defaultdict(list)
per_map = collections.defaultdict(lambda: collections.defaultdict(list))
for d, tname in games:
    m = json.load(open(os.path.join(ROOT, d, 'meta.json'), encoding='utf-8'))
    ev = [json.loads(l) for l in gzip.open(os.path.join(ROOT, d, 'events.jsonl.gz'), 'rt')]
    R = json.load(gzip.open(os.path.join(ROOT, d, 'rounds.json.gz')))
    mp = json.load(open(os.path.join(ROOT, 'maps', m['map']['hash'] + '.json')))
    team = {c['id']: c['team'] for c in m['champions']}
    gtypes = {grp['id']: '+'.join(sorted(set(grp['types']))) for grp in mp['groups']}
    gside = {grp['id']: grp['side'] for grp in mp['groups']}
    mono = {grp['id'] for grp in mp['groups'] if 'Monolith' in grp['types']}
    camp_group = {c['id']: c['group'] for c in mp['camps']}
    for t in (0, 1):
        x = agg[tname[t]]
        x['games'] += 1
        x['rounds'] += min(W, m['result']['rounds'])
        x['pick_rounds'] += len(m['draft']['picks'][t]) * min(W, m['result']['rounds'])
        if mono:
            x['mono_games'] += 1
    for e in ev:
        k = e['k']
        if mono and k == 'capture' and e['g'] in mono:
            x = agg[tname[e['team']]]
            x['mono_captures'] += 1; x['mono_gems'] += sum(s[1] for s in e['shares'])
        if mono and k in ('attack', 'cast') and e.get('cdmg'):
            agg[tname[team[e['a']]]]['mono_dmg'] += sum(v for c, v in e['cdmg'] if camp_group.get(c) in mono)
        if k == 'tribute_end':
            bags[tname[team[e['a']]]].append(e['gems'])
        if e['r'] > W: continue
        if k == 'capture':
            t = e['team']; x = agg[tname[t]]
            gems = sum(s[1] for s in e['shares']); gold = sum(s[2] for s in e['shares'])
            x['cap_gems'] += gems; x['cap_gold'] += gold; x['captures'] += 1
            own = gside.get(e['g'], -1) == t
            x['cap_gems_own_half' if own else 'cap_gems_other'] += gems
            x['cap_gems_' + gtypes.get(e['g'], '?')] += gems
        elif k == 'attack' and 'camp' in e:
            t = team[e['a']]; agg[tname[t]]['camp_attacks'] += 1
            agg[tname[t]]['camp_dmg'] += sum(v[1] for v in e.get('cdmg') or [])
        elif k == 'cast' and e.get('cdmg'):
            t = team[e['a']]; agg[tname[t]]['camp_dmg'] += sum(v[1] for v in e['cdmg'])
            agg[tname[t]]['camp_spell_dmg'] += sum(v[1] for v in e['cdmg'])
        elif k == 'camp_attack':
            t = team.get(e['tgt'])
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
    for c in R['champions']:
        t = c['team']; x = agg[tname[t]]
        for i, tr in enumerate(c['turn'][:W]):
            x['turn_' + str(tr)] += 1
            if c['alive'][i] and c['gems'][i] > 0: x['carry_rounds'] += 1
            if c['alive'][i]: x['carried_gems_sum'] += c['gems'][i]
    for t in (0, 1):
        per_map[m['map']['name']][tname[t]].append(R['gems'][t][min(W, len(R['gems'][t])) - 1])

SKIP = ('games', 'rounds', 'pick_rounds', 'mono_games', 'mono_captures', 'mono_gems', 'mono_dmg')
if a.opp is not None or legacy:
    print(f'{len(games)} games, first {W} rounds, per game:')
    keys = sorted((set(agg[US]) | set(agg[OPP])) - set(SKIP))
    for k in keys:
        u = agg[US][k] / max(1, agg[US]['games']); o = agg[OPP][k] / max(1, agg[OPP]['games'])
        print(f'  {k:32s} us {u:9.1f}  {OPP[:10]} {o:9.1f}  ratio {o / u if u else float("inf"):.2f}')
    print('tributed gems at round 300 by map (mean): map, n, us, them')
    for mname, x in sorted(per_map.items()):
        print(f'  {mname:14s} {len(x[US]):3d} {st.mean(x[US]):6.0f} {st.mean(x[OPP]):6.0f}')
else:
    print(f'{len(games)} games, first {W} rounds, per game:')
    print(f"  {'':32s}" + ''.join(f' {t[:12]:>12s}' for t in teams))
    for k in sorted(set().union(*(agg[t] for t in teams)) - set(SKIP)):
        print(f'  {k:32s}' + ''.join(f" {agg[t][k] / max(1, agg[t]['games']):12.1f}" for t in teams))

print(f'\nper 100 pick-rounds (first {W} rounds; a pick is one champion, Cassi and Issac together):')
print(f"  {'':32s}" + ''.join(f' {t[:12]:>12s}' for t in teams))
for k in ['camp_dmg', 'camp_spell_dmg', 'camp_dmg_taken', 'cap_gems', 'cap_gems_Wolf', 'cap_gems_Elk', 'cap_gems_Gem cluster',
          'cap_gems_Elk+Wolf', 'cap_gold', 'tributed', 'carry_rounds', 'carried_gems_sum', 'recalls', 'deaths', 'bag_lost']:
    print(f'  {k:32s}' + ''.join(f" {100 * agg[t][k] / max(1, agg[t]['pick_rounds']):12.2f}" for t in teams))
print('\nwhole game:')
for t in teams:
    b = bags[t]
    x = agg[t]
    line = f'  {t[:22]:22s} games {int(x["games"]):4d}  tributes/game {len(b) / max(1, x["games"]):5.1f}'
    if b:
        line += f'  bag at tribute median {st.median(b):5.1f} mean {st.mean(b):5.1f}'
    if x['mono_games']:
        line += (f'  | Monolith maps {int(x["mono_games"])}: captures/game {x["mono_captures"] / x["mono_games"]:.2f}'
                 f' gems/game {x["mono_gems"] / x["mono_games"]:.0f} Monolith-group dmg/game {x["mono_dmg"] / x["mono_games"]:.0f}')
    print(line)
