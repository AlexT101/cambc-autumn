"""Champion death rates by class: proto pocket (dead end on foot), brute pocket on foot (not proto),
off foot (crystal/dash island), the rest. Within-map expected counts at each map's 'rest' rate."""
import gzip, json, glob, os, sys, collections, pickle
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from proto import load, flood

ANA = sys.argv[1]
PP = pickle.load(open(os.path.join(ANA, 'proto.pkl'), 'rb'))
PK = pickle.load(open(os.path.join(ANA, 'pockets.pkl'), 'rb'))
DASH_TYPES = {'Vesper Vale', 'Vendetta', 'Ren', 'Heart of Ruin', 'Issac'}
foot_cache = {}
rounds_by = collections.Counter()
deaths_by = collections.Counter()
expected = collections.Counter()
camp_deaths = collections.Counter()
CL = ['proto', 'brute-foot', 'off-foot', 'narrow1', 'narrow2', 'narrow3', 'rest']
from proto import runwidth
for meta_path in sorted(glob.glob(os.path.join(ANA, '*', 'meta.json'))):
    d = os.path.dirname(meta_path)
    meta = json.load(open(meta_path))
    h = meta['map']['hash']
    if h not in foot_cache:
        mp = json.load(open(os.path.join(d, meta['mapFile'])))
        ft = []
        for team in (0, 1):
            w, hh, op, ours, theirs = load(mp, team)
            ft.append(flood(w, hh, op, list(ours)))
        brute = set().union(*[s for s, _ in PK[h]]) if PK[h] else set()
        w, hh, op, _, _ = load(mp, 0)
        wd = {(x, y): runwidth(w, hh, op, x, y) for y in range(hh) for x in range(w) if op[y][x]}
        foot_cache[h] = (ft, brute, wd)
    ft, brute, wd = foot_cache[h]
    names = {c['id']: (c['name'], c['team']) for c in meta['champions']}
    def cls(cid, p):
        nm, team = names[cid]
        if p in PP[h][(team, False)][0]:
            return 'proto'
        if p not in ft[team]:
            return 'off-foot'
        if p in brute:
            return 'brute-foot'
        r = wd.get(p, 9)
        if r <= 3:
            return 'narrow%d' % r
        return 'rest'
    rounds = json.load(gzip.open(os.path.join(d, 'rounds.json.gz')))
    local = collections.Counter()
    for c in rounds['champions']:
        for x, y, a in zip(c['x'], c['y'], c['alive']):
            if a and x is not None:
                local[cls(c['id'], (x, y))] += 1
    ld = collections.Counter()
    for line in gzip.open(os.path.join(d, 'events.jsonl.gz'), 'rt'):
        e = json.loads(line)
        if e['k'] != 'death' or e.get('linked') is not None:
            continue
        k = cls(e['v'], tuple(e['at']))
        if 'camp' in e:
            camp_deaths[k] += 1
        else:
            ld[k] += 1
    for k in CL:
        rounds_by[k] += local[k]
        deaths_by[k] += ld[k]
        if local['rest']:
            expected[k] += local[k] * ld['rest'] / local['rest']
for k in CL:
    print('%-11s rounds %8d champ deaths %5d (%.3f/1k)  camp deaths %4d  within-map x%.2f' % (
        k, rounds_by[k], deaths_by[k], 1000 * deaths_by[k] / max(1, rounds_by[k]), camp_deaths[k], deaths_by[k] / max(1e-9, expected[k])))
