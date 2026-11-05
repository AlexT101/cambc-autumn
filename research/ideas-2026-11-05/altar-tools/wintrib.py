#!/usr/bin/env python3
"""wintrib.py ANA: tribute starts of winning bags (team score + bag >= 1000) and how they ended, by channel length."""
import json, gzip, os, sys, collections
ANA = sys.argv[1]
c = collections.Counter()
for d in os.listdir(ANA):
    if not os.path.exists(f'{ANA}/{d}/meta.json'): continue
    m = json.load(open(f'{ANA}/{d}/meta.json'))
    R = json.load(gzip.open(f'{ANA}/{d}/rounds.json.gz')); ri = {r: i for i, r in enumerate(R['round'])}
    team = {ch['id']: ch['team'] for ch in m['champions']}
    ev = [json.loads(l) for l in gzip.open(f'{ANA}/{d}/events.jsonl.gz', 'rt')]
    ends = {}
    for e in ev:
        if e['k'] in ('tribute_end', 'tribute_cancel'): ends.setdefault(e['a'], []).append(e)
    for e in ev:
        if e['k'] != 'tribute_start': continue
        t = team[e['a']]; i = ri.get(e['r'] - 1, 0)
        if R['gems'][t][i] + e['gems'] < 1000: continue
        out = next((x for x in ends.get(e['a'], []) if x['s'] > e['s']), None)
        res = 'end' if out and out['k'] == 'tribute_end' else ('cancel:' + out.get('cause', '?') if out else 'none')
        band = 'dur<=8' if e['dur'] <= 8 else ('dur9-30' if e['dur'] <= 30 else 'dur>30')
        kind = "one" if len(json.load(open(f"{ANA}/maps/{m['map']['hash']}.json"))["altars"]) == 1 else "multi"
        c[(kind, band, res)] += 1; c[(kind, band, "starts")] += 1
for k in sorted(c): print(k, c[k])
