#!/usr/bin/env python3
"""shopmix.py ANA BATCH [E_MIN GAP]: what each side buys once cooked (cand cooked vs ref cooked, bot 1 = CAND):
shards by family, gold spent, and kills / deaths of the trailer after the cook point."""
import json, gzip, os, sys, collections
ANA, B = sys.argv[1], sys.argv[2]
E_MIN, GAP = (int(sys.argv[3]), int(sys.argv[4])) if len(sys.argv) > 4 else (400, 150)
ix = json.load(open(f'{ANA}/index.json'))
c = collections.Counter(); fam = collections.defaultdict(collections.Counter)
for g in ix['games']:
    f = os.path.basename(g['source']); cand = 0 if f[-10:-8] == '12' else 1
    d = f"{ANA}/{g['dir']}"
    try:
        m = json.load(open(f'{d}/meta.json')); R = json.load(gzip.open(f'{d}/rounds.json.gz'))
    except Exception:
        continue
    team = [x['team'] for x in R['champions']]
    hit = None
    for i in range(len(R['round'])):
        for t in (0, 1):
            if R['gems'][1 - t][i] >= E_MIN and R['gems'][1 - t][i] - R['gems'][t][i] >= GAP: hit = (t, R['round'][i])
        if hit: break
    if not hit: continue
    t, r0 = hit
    who = 'cand' if t == cand else 'ref'
    c[(who, 'n')] += 1; c[(who, 'won')] += m['result']['winner'] == t
    for l in gzip.open(f'{d}/events.jsonl.gz', 'rt'):
        e = json.loads(l)
        if e['r'] < r0: continue
        if e['k'] == 'shop' and team[e['a']] == t:
            c[(who, 'spent')] -= e.get('gold', 0)
            for name, k in e.get('items', {}).items():
                fam[who][name.split(' Shard')[0].split(' Emblem')[0]] += k
        elif e['k'] == 'death':
            if team[e['v']] == t: c[(who, 'deaths')] += 1
            elif e.get('by') is not None and e['by'] < len(team) and team[e['by']] == t: c[(who, 'kills')] += 1
for who in ('cand', 'ref'):
    n = max(1, c[(who, 'n')])
    print(f"{who}: cooked {c[(who, 'n')]}, comeback {100 * c[(who, 'won')] / n:.1f}%, gold spent {c[(who, 'spent')] / n:.0f}, kills {c[(who, 'kills')] / n:.2f}, deaths {c[(who, 'deaths')] / n:.2f}")
    print('   ', ', '.join(f'{k} {v / n:.2f}' for k, v in fam[who].most_common(12)))
