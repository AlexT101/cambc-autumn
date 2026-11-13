"""Mirror study from the enemy angle: deaths vs how long the killer was unseen; numbers at death;
what teams earn while enemies are dead. Usage: py enemy_angle.py ANALYSIS_DIR"""
import gzip, json, sys
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

def cheb(a, b): return max(abs(a[0]-b[0]), abs(a[1]-b[1]))

def game(d):
    d = Path(d)
    try:
        meta = json.loads((d/'meta.json').read_text())
        R = json.load(gzip.open(d/'rounds.json.gz'))
        ev = [json.loads(l) for l in gzip.open(d/'events.jsonl.gz', 'rt')]
    except Exception:
        return None
    winner = meta['result']['winner']
    ch = R['champions']; idx = {c['id']: i for i, c in enumerate(ch)}
    types = {c['id']: c['type'] for c in meta['champions']}
    n = len(R['round'])
    rix = {r: i for i, r in enumerate(R['round'])}
    out = {'unseen': Counter(), 'unseen_any': Counter(), 'numbers': Counter(), 'dead_cap': defaultdict(lambda: [0, 0]),
           'deaths_by_type': Counter(), 'first_prism_unseen': Counter()}
    # last round each enemy was seen by each champion / by the team
    def last_seen(victim, killer, r):
        vi = idx[victim]; team = ch[vi]['team']
        best_self = best_any = None
        for back in range(0, 31):
            i = rix.get(r - back)
            if i is None: break
            for c in ch:
                if c['team'] != team: continue
                s = c.get('sees')
                if not s: continue
                seen = s[i] or []
                if killer in seen:
                    if best_any is None: best_any = back
                    if c['id'] == victim and best_self is None: best_self = back
            if best_self is not None and best_any is not None: break
        return best_self, best_any
    def bucket(b):
        if b is None: return '31+'
        return '0-1' if b <= 1 else '2-3' if b <= 3 else '4-10' if b <= 10 else '11-30'
    prism_dead = set()
    for e in ev:
        if e['k'] != 'death' or 'by' not in e or e.get('linked'): continue
        v, k, r = e['v'], e['by'], e['r']
        if v not in idx or k not in idx: continue
        vt = ch[idx[v]]['team']
        role = 'W' if vt == winner else 'L'
        bs, ba = last_seen(v, k, r - 1)
        out['unseen'][(role, bucket(bs))] += 1
        out['unseen_any'][(role, bucket(ba))] += 1
        out['deaths_by_type'][(role, types.get(v))] += 1
        i = rix.get(r - 1)
        if i is not None and e.get('at'):
            at = e['at']
            al = en = 0
            for c in ch:
                if not c['alive'][i] or c['x'][i] is None: continue
                if c['id'] == v: continue
                p = (c['x'][i], c['y'][i])
                if cheb(p, at) <= 6:
                    if c['team'] == vt: al += 1
                    else: en += 1
            out['numbers'][(role, min(al, 3), min(en, 4))] += 1
    # captures by number of enemies dead
    caps = defaultdict(int)
    for e in ev:
        if e['k'] == 'capture':
            caps[(e['r'], e['team'])] += sum(s[1] for s in e['shares'])
    for i, r in enumerate(R['round']):
        for team in (0, 1):
            dead = sum(1 for c in ch if c['team'] != team and not c['alive'][i])
            role = 'W' if team == winner else 'L'
            acc = out['dead_cap'][(role, min(dead, 3))]
            acc[0] += 1; acc[1] += caps.get((r, team), 0)
    out['dead_cap'] = dict(out['dead_cap'])
    return out

def main():
    root = Path(sys.argv[1])
    dirs = [p for p in root.iterdir() if (p/'meta.json').exists()]
    tot = defaultdict(Counter); dc = defaultdict(lambda: [0, 0]); g = 0
    with ProcessPoolExecutor(24) as ex:
        for o in ex.map(game, dirs, chunksize=4):
            if not o: continue
            g += 1
            for key in ('unseen', 'unseen_any', 'numbers', 'deaths_by_type'):
                tot[key].update(o[key])
            for k, v in o['dead_cap'].items():
                dc[k][0] += v[0]; dc[k][1] += v[1]
    print('games', g)
    for key in ('unseen', 'unseen_any'):
        print(f'\n{key}: rounds since killer last seen by {"victim" if key=="unseen" else "victim team"}')
        for role in 'WL':
            row = {b: tot[key][(role, b)] for b in ['0-1', '2-3', '4-10', '11-30', '31+']}
            s = sum(row.values()) or 1
            print(role, s, ' '.join(f'{b}:{v} ({100*v/s:.0f}%)' for b, v in row.items()))
    print('\ndeaths by type (W/L)')
    for t in sorted({k[1] for k in tot['deaths_by_type']}, key=str):
        print(f'  {t}: {tot["deaths_by_type"][("W", t)]} / {tot["deaths_by_type"][("L", t)]}')
    print('\nnumbers at death (allies within 6 excl victim, enemies within 6)')
    for role in 'WL':
        items = sorted(((k[1], k[2]), v) for k, v in tot['numbers'].items() if k[0] == role)
        s = sum(v for _, v in items)
        print(role, ' '.join(f'a{a}e{e}:{100*v/s:.0f}%' for (a, e), v in items if v/s > 0.02))
    print('\ncapture gems per team-round by enemies dead')
    for role in 'WL':
        print(role, ' '.join(f'{d}dead: {dc[(role,d)][1]/max(1,dc[(role,d)][0]):.3f} ({dc[(role,d)][0]} rds)' for d in range(4)))

if __name__ == "__main__":
    main()
