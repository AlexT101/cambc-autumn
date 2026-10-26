"""Off-foot (crystal/dash island) champion deaths: who, how they got there, what they did."""
import gzip, json, glob, os, sys, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from proto import load, flood

ANA = sys.argv[1]
DASH_TYPES = {'Vesper Vale', 'Vendetta', 'Ren', 'Heart of Ruin', 'Issac'}
cache = {}
st = collections.Counter()
maps = collections.Counter()
games_with = 0
for meta_path in sorted(glob.glob(os.path.join(ANA, '*', 'meta.json'))):
    d = os.path.dirname(meta_path)
    meta = json.load(open(meta_path))
    h = meta['map']['hash']
    if h not in cache:
        mp = json.load(open(os.path.join(d, meta['mapFile'])))
        ft = []
        for team in (0, 1):
            w, hh, op, ours, theirs = load(mp, team)
            dw, dh, dop, _, _ = load(mp, team, dash=True)
            ft.append((flood(w, hh, op, list(ours)), flood(dw, dh, dop, list(ours))))
        cache[h] = ft
    ft = cache[h]
    names = {c['id']: (c['name'], c['team']) for c in meta['champions']}
    events = [json.loads(l) for l in gzip.open(os.path.join(d, 'events.jsonl.gz'), 'rt')]
    deaths = [e for e in events if e['k'] == 'death' and e.get('linked') is None and 'camp' not in e
              and tuple(e['at']) not in ft[names[e['v']][1]][0]]
    if not deaths:
        continue
    games_with += 1
    maps[meta['map']['name'].rsplit('-', 1)[0]] += len(deaths)
    for e in deaths:
        v, r = e['v'], e['r']
        nm, team = names[v]
        dasher = nm in DASH_TYPES
        at = tuple(e['at'])
        st['victim dasher' if dasher else 'victim walker'] += 1
        st['dash-reachable' if at in ft[team][1] else 'crystal-only'] += 1
        # last arrival onto an off-foot tile by teleport or dash before death
        mode = 'walked/unknown'
        for ev in reversed([x for x in events if x['s'] < e['s'] and x.get('a') == v]):
            if ev['k'] == 'teleport_end':
                mode = 'teleport'
                break
            if ev['k'] == 'cast' and ev.get('moved') and tuple(ev['moved']) not in ft[team][0]:
                mode = 'dash'
                break
            if ev['k'] == 'respawn':
                break
        st['arrived by ' + mode] += 1
        killers = [k for k in [e.get('by')] + list(e.get('assists', [])) if k is not None]
        st['killers=%d' % min(3, len(killers))] += 1
        st['bag>0' if e.get('gems', 0) > 0 else 'bag=0'] += 1
print('games with off-foot champion deaths', games_with)
for k, v in sorted(st.items()):
    print('  %-24s %d' % (k, v))
print(maps.most_common(12))
