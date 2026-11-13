"""Does a team shift its captures toward mid / enemy side while enemies are dead? Capture gems by side, and the up
(alive, not respawning) gems of mid/enemy-side groups, by enemies dead at capture time. Usage: py deadshift.py DIR"""
import gzip, json, sys
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

def game(d):
    d = Path(d)
    try:
        meta = json.loads((d/'meta.json').read_text())
        R = json.load(gzip.open(d/'rounds.json.gz'))
        mp = json.loads((d/meta['mapFile']).resolve().read_text())
        ev = [json.loads(l) for l in gzip.open(d/'events.jsonl.gz', 'rt')]
    except Exception:
        return None
    winner = meta['result']['winner']
    rix = {r: i for i, r in enumerate(R['round'])}
    ch = R['champions']
    side = {g['id']: g['side'] for g in mp['groups']}
    out = defaultdict(float)
    for e in ev:
        if e['k'] != 'capture' or e['r'] > 600: continue
        i = rix.get(e['r'])
        if i is None: continue
        team = e['team']
        n_enemy = sum(1 for c in ch if c['team'] != team)
        dead = sum(1 for c in ch if c['team'] != team and not c['alive'][i])
        frac = 'none' if dead == 0 else ('some' if dead < n_enemy / 2 else 'half+')
        s = side.get(e['g'], -1)
        rel = 'mid' if s == -1 else ('own' if s == team else 'enemy')
        g = sum(x[1] for x in e['shares'])
        role = 'W' if team == winner else 'L'
        out[(role, frac, rel)] += g
        out[(role, frac, 'all')] += g
    # rounds by dead fraction (r<=600) per team
    for i, r in enumerate(R['round']):
        if r > 600: break
        for team in (0, 1):
            n_enemy = sum(1 for c in ch if c['team'] != team)
            dead = sum(1 for c in ch if c['team'] != team and not c['alive'][i])
            frac = 'none' if dead == 0 else ('some' if dead < n_enemy / 2 else 'half+')
            out[('W' if team == winner else 'L', frac, 'rounds')] += 1
    return dict(out)

def main():
    root = Path(sys.argv[1])
    dirs = [p for p in root.iterdir() if (p/'meta.json').exists()]
    T = defaultdict(float)
    with ProcessPoolExecutor(24) as ex:
        for o in ex.map(game, dirs, chunksize=4):
            if o:
                for k, v in o.items(): T[k] += v
    for role in 'WL':
        for frac in ('none', 'some', 'half+'):
            rd = T[(role, frac, 'rounds')]; a = T[(role, frac, 'all')] or 1
            print(f'{role} {frac:5s} rounds {rd:7.0f} gems/round {a/max(1,rd):.2f}  own {100*T[(role,frac,"own")]/a:4.1f}% '
                  f'mid {100*T[(role,frac,"mid")]/a:4.1f}% enemy {100*T[(role,frac,"enemy")]/a:4.1f}%')

if __name__ == '__main__':
    main()
