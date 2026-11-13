"""What our champion was doing before a live Fish r8 kill: channel (recall/tribute) at death, distance to the killer
3 rounds before and 1 round before (closing or opening), the killer seen by the victim 3 rounds before, health.
    python3 before.py   (reads ~/tmp-offload/fishr8/live, deaths.json from deaths.py)"""
import gzip, json, os, collections, statistics as st
L = os.path.expanduser('~/tmp-offload/fishr8/live')
D = json.load(open(os.path.expanduser('~/tmp-offload/pdkg/deaths.json')))
byg = collections.defaultdict(list)
for o in D: byg[o['game']].append(o)
C = collections.Counter(); rows = []
for g, ds in byg.items():
    p = f'{L}/ext/{g}'
    m = json.load(open(p + '/meta.json'))
    R = json.load(gzip.open(p + '/rounds.json.gz', 'rt'))
    idx = {r: i for i, r in enumerate(R['round'])}
    ch = {c['id']: c for c in R['champions']}
    name = {c['id']: c['name'] for c in m['champions']}
    deaths = [json.loads(l) for l in gzip.open(p + '/events.jsonl.gz', 'rt')]
    deaths = [e for e in deaths if e.get('k') == 'death']
    for e in deaths:
        o = next((x for x in ds if x['r'] == e['r'] and x['victim'] == name[e['v']]), None)
        if o is None or o['kteam'] < 0: continue
        v = ch[e['v']]; k = ch.get(e.get('by'))
        if k is None: continue
        i = idx.get(e['r'])
        if i is None or i < 4: continue
        d = lambda j: max(abs(v['x'][j] - k['x'][j]), abs(v['y'][j] - k['y'][j]))
        chan = v['chan'][i - 1]
        seen3 = k['id'] in (v['sees'][i - 3] or []) if v['sees'][i - 3] is not None else None
        # our move between i-3 and i-1: towards (dist to the killer's old tile falls) or away
        ox, oy = k['x'][i - 3], k['y'][i - 3]
        ours = max(abs(v['x'][i - 1] - ox), abs(v['y'][i - 1] - oy)) - max(abs(v['x'][i - 3] - ox), abs(v['y'][i - 3] - oy))
        theirs = max(abs(k['x'][i - 1] - v['x'][i - 3]), abs(k['y'][i - 1] - v['y'][i - 3])) - d(i - 3)
        rows.append(dict(r=e['r'], hunter=o['hunter'], chan=chan, d3=d(i - 3), d1=d(i - 1), ours=ours, theirs=theirs, seen3=seen3,
                         hp3=o['hp3'], late=e['r'] >= 450, killer=o['killer']))
print('kills by Fish champions analysed', len(rows))
for lab, sel in (('all', lambda x: True), ('Hunter killer, r450+', lambda x: x['hunter'] and x['late'])):
    x = [r for r in rows if sel(r)]
    n = len(x)
    print(f'\n{lab}: {n}')
    print(f'  channel at r-1: recall {sum(r["chan"]==1 for r in x)/n:.0%}, tribute {sum(r["chan"]==2 for r in x)/n:.0%}, teleport {sum(r["chan"]==3 for r in x)/n:.0%}')
    print(f'  killer in our sight 3 rounds before: {sum(1 for r in x if r["seen3"])/n:.0%}')
    print(f'  distance to killer 3 rounds before: median {st.median(r["d3"] for r in x)}, <=6 {sum(r["d3"]<=6 for r in x)/n:.0%}; 1 round before: median {st.median(r["d1"] for r in x)}')
    print(f'  we walked towards its tile (r-3 to r-1): {sum(r["ours"]<0 for r in x)/n:.0%}, away {sum(r["ours"]>0 for r in x)/n:.0%}, held {sum(r["ours"]==0 for r in x)/n:.0%}')
    print(f'  it closed on our tile: {sum(r["theirs"]<0 for r in x)/n:.0%}')
