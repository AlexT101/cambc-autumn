import json, math, sys
S = sys.argv[1]
rows = {r['name']: r for r in map(json.loads, open(f'{S}/maps.jsonl'))}
home = json.load(open(f'{S}/homemono.json'))
MUST = ['04sunburst', '03homonoliths', '03the-front', '00lanes', '03one-gem', '00great-wall', '00reverse-spiral',
        '02treasure-box', '01boss-battle', '00ambush', '03ultrastarvation', '02the-pond', '04spiral-moat',
        '03showdown', '02guardians', 'adgato-gemcombat5', '04two-kingdoms', '02harvest', '01starvation', '03twisty', '04terraces']
QUOTA = {3: 9, 4: 9, 5: 22}
def vec(r):
    f = r['f']
    return [math.log(r['W'] * r['H']), math.log(max(r['W'], r['H']) / min(r['W'], r['H'])), math.log(f['altars']),
            float(f['altars'] == 1) * 1.5, f['monoliths'] > 0, min(home.get(r['name'], 99), 40) / 40, f['golems'],
            math.log(1 + f['spawn_dist']), math.log(1 + f['gems_side']), f['shared_share'], f['contested_share'],
            f['walls'] * 4, f['bushes'] * 4, f['holes'] * 2, f['spawn_ring'], float(r['access'] != 'walk'),
            {'rotational': 0, 'horizontal': 1, 'vertical': 1}[r['sym']] * 0.5]
V = {n: [float(x) for x in vec(r)] for n, r in rows.items()}
k = len(next(iter(V.values())))
mu = [sum(v[i] for v in V.values()) / len(V) for i in range(k)]
sd = [max(1e-9, (sum((v[i] - mu[i]) ** 2 for v in V.values()) / len(V)) ** .5) for i in range(k)]
Z = {n: [(v[i] - mu[i]) / sd[i] for i in range(k)] for n, v in V.items()}
dist = lambda a, b: sum((x - y) ** 2 for x, y in zip(Z[a], Z[b])) ** .5
chosen = list(MUST)
count = {p: sum(rows[n]['picks'] == p for n in chosen) for p in QUOTA}
while len(chosen) < sum(QUOTA.values()):
    cost = lambda cand: sum(min(dist(m, c) for c in chosen + [cand]) for m in rows)
    best = min((n for n in rows if n not in chosen and count[rows[n]['picks']] < QUOTA[rows[n]['picks']]),
               key=lambda n: (cost(n), n))
    chosen.append(best); count[rows[best]['picks']] += 1
print(json.dumps(chosen))
print(count, file=sys.stderr)
