# Does Fish/Mite's pick k depend on the opponent's earlier picks? Archive (11-04..07) and live scrims.
import pickle, collections, json
g = pickle.load(open('/home/ubuntu/tmp-offload/counter/games.pkl', 'rb'))
T = {'F': '1890540d-1ffc-4847-adbf-d0d08772f268', 'M': 'ee83f5e5-bcad-4923-86b4-b79ea6083d2e'}
for o, tid in T.items():
    for day in ['2026-11-05', '2026-11-06', '2026-11-07']:
        by = collections.defaultdict(lambda: collections.defaultdict(set))  # (map, side) -> prefix -> set(their pick k)
        teams = collections.defaultdict(set); n = 0
        for r in g['rows']:
            if r['day'] != day: continue
            if r['A'] == tid: mine, opp, s = r['pa'], r['pb'], 'a'
            elif r['B'] == tid: mine, opp, s = r['pb'], r['pa'], 'b'
            else: continue
            n += 1
            teams[(r['map'], s)].add(tuple(mine))
            for k in range(len(mine)):
                by[(r['map'], s)][(k, tuple(opp[:k]))].add(mine[k])
        # fraction of (map, side) with >1 distinct team; and for pick k, does it vary given the same opp prefix?
        multi = sum(len(v) > 1 for v in teams.values())
        incons = sum(len(x) > 1 for v in by.values() for x in v.values())
        tot = sum(len(v) for v in by.values())
        # does pick k vary across different opp prefixes, holding (map, side)?
        var_k = collections.Counter(); cnt_k = collections.Counter()
        for (m, s), v in by.items():
            for k in range(5):
                picks = set().union(*[x for (kk, p), x in v.items() if kk == k]) if any(kk == k for kk, _ in v) else set()
                if picks: cnt_k[k] += 1; var_k[k] += len(picks) > 1
        print(o, day, 'games', n, 'map-sides', len(teams), 'multi-team', multi, 'same-prefix-incons', incons, '/', tot,
              'pick k varies (per map-side):', {k: f'{var_k[k]}/{cnt_k[k]}' for k in sorted(cnt_k)})
