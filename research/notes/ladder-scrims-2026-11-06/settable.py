import json, sys
S = sys.argv[1]
rows = {r['name']: r for r in map(json.loads, open(f'{S}/maps.jsonl'))}
home = json.load(open(f'{S}/homemono.json'))
st = json.load(open('research/notes/ladder-scrims-2026-11-06/data/set-v1.json'))
why = {'04sunburst': 'sunburst (the ladder\'s invade move; EXPERIMENTS "sunfam")', '03homonoliths': 'home Monolith (CHANGES 407; a Monolith 1 from spawn)',
       '03the-front': '34 altars, 5 Monoliths, 1,324 gems a side', '00lanes': '18 altars, 90x30 lanes',
       '03one-gem': '3.5 gems a side: a tiebreak and kill map', '00great-wall': '2 Monoliths, 2 golems, 702 gems, walled halves',
       '00reverse-spiral': 'spawns adjacent (spawn distance 0)', '02treasure-box': 'one altar, spawns 3 apart',
       '01boss-battle': 'one altar and a Monolith', '00ambush': '100x100, dash access', '03ultrastarvation': 'one altar, dash access, 18 gems, 3 picks',
       '02the-pond': 'teleport access, 3 picks', '04spiral-moat': 'one altar, Monolith 9 from spawn, 3 picks',
       '03showdown': 'one altar, Monolith, 4 picks', '02guardians': 'one altar, Monolith, 27% walls',
       'adgato-gemcombat5': '99x99, one altar, 47% holes', '04two-kingdoms': '85x85, one altar, Monolith 7 from spawn',
       '02harvest': '100x100, 3 golems', '01starvation': '80x80, spawn distance 182', '03twisty': '90x70, spawn distance 330 (the longest)',
       '04terraces': '91x90, 49% holes, spawn distance 181'}
print('| # | map | picks | size | altars | Monoliths (distance to spawn) | why |')
print('|---|---|---|---|---|---|---|')
for i, m in enumerate(st['core'], 1):
    n = m['name'].replace('_', '-'); r = rows[n]; f = r['f']
    mono = f"{f['monoliths']:g} ({home[n]})" if f['monoliths'] else '-'
    print(f"| {i} | {m['name']} | {r['picks']} | {r['W']}x{r['H']} | {f['altars']:g} | {mono} | {why.get(n, 'pool coverage (facility location)')} |")
