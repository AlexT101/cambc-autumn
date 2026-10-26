"""Print the 15 rounds before pocket deaths: positions, hp, actions of victim and nearby enemies."""
import gzip, json, glob, os, sys, collections, random
sys.path.insert(0, os.path.dirname(__file__))
from chokes import pockets  # noqa

ANA = sys.argv[1]
N = int(sys.argv[2])
SEED = int(sys.argv[3]) if len(sys.argv) > 3 else 1
MAXSIZE = int(sys.argv[4]) if len(sys.argv) > 4 else 200
random.seed(SEED)
metas = sorted(glob.glob(os.path.join(ANA, '*', 'meta.json')))
random.shuffle(metas)
import pickle
from chokes import Grid
PK = pickle.load(open(os.path.join(ANA, 'pockets.pkl'), 'rb'))
mapcache = {}
shown = 0
for meta_path in metas:
    if shown >= N:
        break
    d = os.path.dirname(meta_path)
    meta = json.load(open(meta_path))
    h = meta['map']['hash']
    mp = json.load(open(os.path.join(d, meta['mapFile'])))
    if h not in mapcache:
        mapcache[h] = (Grid(mp), PK[h])
    g, pk = mapcache[h]
    if not pk:
        continue
    events = [json.loads(l) for l in gzip.open(os.path.join(d, 'events.jsonl.gz'), 'rt')]
    deaths = [e for e in events if e['k'] == 'death' and e.get('linked') is None and 'camp' not in e]
    rounds = json.load(gzip.open(os.path.join(d, 'rounds.json.gz')))
    champs = rounds['champions']
    names = {c['id']: c['name'] for c in meta['champions']}
    byid = {c['id']: c for c in champs}
    ri = {r: i for i, r in enumerate(rounds['round'])}
    camps = {(c['x'], c['y']): c['type'][0] for c in mp['camps']}
    for e in deaths:
        at = tuple(e['at'])
        cands = [(s, b) for s, b in pk if at in s and len(s) <= MAXSIZE]
        if not cands:
            continue
        s, block = min(cands, key=lambda sb: len(sb[0]))
        v, r = e['v'], e['r']
        killers = [k for k in [e.get('by')] + list(e.get('assists', [])) if k is not None]
        print('=' * 100)
        print(meta['map']['name'], d[-16:], 'round', r, 'victim', v, names[v], 'team', byid[v]['team'], 'gems', e.get('gems'),
              'killers', [(k, names[k]) for k in killers], 'pocket size', len(s))
        acts = collections.defaultdict(list)
        for ev in events:
            if r - 15 <= ev['r'] <= r and ev.get('a') in [v] + killers and ev['k'] not in ('move',):
                tag = ev['k'] + ('>camp' if 'camp' in ev else '>%s' % ev['tgt'] if 'tgt' in ev else '')
                acts[(ev['a'], ev['r'])].append(tag)
        allies = [c['id'] for c in champs if c['team'] == byid[v]['team'] and c['id'] != v]
        for rr in range(r - 15, r + 1):
            i = ri.get(rr)
            if i is None:
                continue
            def st(cid):
                c = byid[cid]
                if not c['alive'][i] or c['x'][i] is None:
                    return '%d:dead' % cid
                p = (c['x'][i], c['y'][i])
                tag = 'P' if p in s else 'X' if p in block else '-'
                return '%d@%d,%d%s hp%d %s' % (cid, p[0], p[1], tag, c['hp'][i], ','.join(acts.get((cid, rr), [])))
            sees = byid[v]['sees'][i]
            print('  r%-5d %-40s | %s | sees %s | allies %s' % (rr, st(v), ' ; '.join(st(k) for k in killers), sees,
                  ' '.join(st(a).split(' ')[0] for a in allies)))
        # map window
        xs = [p[0] for p in s] + [p[0] for p in block]
        ys = [p[1] for p in s] + [p[1] for p in block]
        x0, x1, y0, y1 = min(xs) - 3, max(xs) + 3, min(ys) - 3, max(ys) + 3
        for y in range(min(y1, g.h - 1), max(y0, 0) - 1, -1):
            row = ''
            for x in range(max(x0, 0), min(x1, g.w - 1) + 1):
                p = (x, y)
                row += ('#' if not g.open[y][x] else camps.get(p, 'X' if p in block else 'p' if p in s else '.'))
            print('    %3d %s' % (y, row))
        print('    x0=%d' % max(x0, 0))
        shown += 1
        break
