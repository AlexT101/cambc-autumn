"""First Prism death of a game (both teams drafted Prism): the victim's branches in the 10 rounds before (D lines),
ground (own/mid/enemy half by distance to the spawns), Focus ratio victim/enemy Prism, allies/enemies within 8,
bag, round, killer. Needs debug replays with D lines and extract.mjs output.

    py research/mx-tethys/scripts/prism_death.py ANALYSIS_ROOT BATCH_NAME [MAX] [--by-bot CAND]
"""
import gzip, json, re, sys, zipfile
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

WT = Path('/home/ubuntu/wt/mx-tethys')
D_RE = re.compile(rb'^[\s\0]*D (\d+) (\d+) (\S) (-?\d+) (-?\d+)\s*$', re.M)
cheb = lambda a, b: max(abs(a[0] - b[0]), abs(a[1] - b[1]))


def one(dd):
    try:
        m = json.loads((dd / 'meta.json').read_text())
        mp = json.loads((dd / m['mapFile']).resolve().read_text())
        R = json.load(gzip.open(dd / 'rounds.json.gz'))
        ev = [json.loads(l) for l in gzip.open(dd / 'events.jsonl.gz', 'rt')]
        z = zipfile.ZipFile(WT / m['source'])
    except Exception:
        return None
    names = {c['id']: c['name'] for c in m['champions']}
    team = {c['id']: c['team'] for c in m['champions']}
    prisms = {team[i]: i for i in names if names[i] == 'Prism'}
    if len(prisms) != 2: return None
    first = next((e for e in ev if e['k'] == 'death' and e['v'] in prisms.values()), None)
    if not first: return {'none': 1, 'teams': [t['name'] for t in m['teams']], 'winner': m['result']['winner']}
    br = {}
    for name in ('team-a.stdout', 'team-b.stdout'):
        try: data = z.read(name)
        except KeyError: continue
        for r, cid, b, _, _ in D_RE.findall(data):
            br[(int(r), int(cid))] = b.decode()
    v = first['v']; t = team[v]; o = prisms[1 - t]
    rix = {r: i for i, r in enumerate(R['round'])}
    C = {c['id']: c for c in R['champions']}
    i = rix.get(first['r'] - 1, 0)
    vp = (C[v]['x'][i], C[v]['y'][i])
    if vp[0] is None: return None
    sp = mp['spawn']
    cen = lambda s: ((s['minX'] + s['maxX']) / 2, (s['minY'] + s['maxY']) / 2)
    da, de = cheb(vp, cen(sp[t])), cheb(vp, cen(sp[1 - t]))
    share = da / max(1e-9, da + de)
    ground = 'own' if share < 0.4 else 'enemy' if share > 0.6 else 'mid'
    fv, fo = C[v]['foc'][i] or 1, C[o]['foc'][i] if C[o]['alive'][i] else None
    na = ne = 0
    for c in R['champions']:
        if c['id'] == v or not c['alive'][i] or c['x'][i] is None: continue
        if cheb(vp, (c['x'][i], c['y'][i])) <= 8:
            if team[c['id']] == t: na += 1
            else: ne += 1
    last = [br.get((r, v), '?') for r in range(first['r'] - 10, first['r'])]
    i10 = rix.get(first['r'] - 10, 0)
    campdmg = sum(e['dmg'] for e in ev if e['k'] == 'camp_attack' and e.get('tgt') == v and first['r'] - 15 <= e['r'] <= first['r'])
    champdmg = 0.0
    for e in ev:
        if e['k'] in ('attack', 'cast') and first['r'] - 15 <= e['r'] <= first['r'] and e.get('dmg'):
            for tid, amt in (e['dmg'] if isinstance(e['dmg'], list) else []):
                if tid == v: champdmg += amt
    return {'teams': [x['name'] for x in m['teams']], 'winner': m['result']['winner'], 'vteam': t, 'r': first['r'],
            'ground': ground, 'ratio': (fv / fo) if fo else None, 'na': na, 'ne': ne, 'bag': first.get('gems') or 0,
            'killer': names.get(first.get('by'), 'camp'), 'last': last, 'hp_before': C[v]['hp'][max(0, i - 3)] / max(1, C[v]['maxHp'][i]), 'hp10': C[v]['hp'][i10] / max(1, C[v]['maxHp'][i10]), 'campdmg': campdmg / max(1, C[v]['maxHp'][i]), 'champdmg': champdmg / max(1, C[v]['maxHp'][i])}


def main():
    root = Path(sys.argv[1]); bname = sys.argv[2]; mx = int(sys.argv[3]) if len(sys.argv) > 3 and not sys.argv[3].startswith('--') else 10**9
    cand = sys.argv[sys.argv.index('--by-bot') + 1] if '--by-bot' in sys.argv else None
    dirs = []
    for dd in sorted(root.iterdir()):
        mf = dd / 'meta.json'
        if mf.exists() and bname in (json.loads(mf.read_text()).get('source') or ''): dirs.append(dd)
        if len(dirs) >= mx: break
    rows = []
    with ProcessPoolExecutor(40) as ex:
        for x in ex.map(one, dirs, chunksize=4):
            if x: rows.append(x)
    if '--early' in sys.argv: rows = [x for x in rows if 'none' in x or x['r'] <= 300]
    if '--late' in sys.argv: rows = [x for x in rows if 'none' in x or x['r'] > 300]
    both = len(rows); none = sum(1 for x in rows if 'none' in x); rows = [x for x in rows if 'none' not in x]
    print(f'games with both Prisms {both}; no Prism death {none}; first Prism deaths {len(rows)}')
    if cand:
        mine = [x for x in rows if cand in x['teams'][x['vteam']]]
        print(f'{cand} Prism died first in {len(mine)}, the other in {len(rows) - len(mine)}')
    vic_lost = sum(1 for x in rows if x['winner'] != x['vteam'])
    print(f"victim's team lost {vic_lost / max(1, len(rows)) * 100:.1f}%")
    def dist(key, f):
        c = Counter(f(x) for x in rows)
        print(key, {k: f'{v / len(rows) * 100:.1f}%' for k, v in sorted(c.items(), key=lambda kv: -kv[1])})
    dist('ground', lambda x: x['ground'])
    dist('focus ratio', lambda x: 'n/a' if x['ratio'] is None else '<0.8' if x['ratio'] < 0.8 else '0.8-1.25' if x['ratio'] <= 1.25 else '>1.25')
    dist('allies-enemies within 8', lambda x: max(-3, min(3, x['na'] - x['ne'])))
    dist('killer', lambda x: x['killer'])
    dist('branch at death', lambda x: x['last'][-1])
    dist('main branch over last 10', lambda x: Counter(x['last']).most_common(1)[0][0])
    dist('phase', lambda x: 'r<=300' if x['r'] <= 300 else 'r301-600' if x['r'] <= 600 else 'r601+')
    dist('bag', lambda x: '0-49' if x['bag'] < 50 else '50-149' if x['bag'] < 150 else '150-399' if x['bag'] < 400 else '400+')
    dist('hp 10 rounds before', lambda x: '<=30%' if x['hp10'] <= 0.3 else '30-70%' if x['hp10'] <= 0.7 else '>70%')
    dist('camp dmg in last 15 (x max hp)', lambda x: '0' if x['campdmg'] == 0 else '<0.2' if x['campdmg'] < 0.2 else '0.2-0.5' if x['campdmg'] < 0.5 else '0.5+')
    dist('champion dmg in last 15 (x max hp)', lambda x: '<0.5' if x['champdmg'] < 0.5 else '0.5-1' if x['champdmg'] < 1 else '1+')
    dist('hp 3 rounds before', lambda x: '<=30%' if x['hp_before'] <= 0.3 else '30-70%' if x['hp_before'] <= 0.7 else '>70%')


if __name__ == '__main__':
    main()
