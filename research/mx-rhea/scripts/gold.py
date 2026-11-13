"""Gold held and earned, carried gems and max hp by champion type at rounds 150/300/500, winner vs loser, and the
share of capture gems by group side (own / mid / enemy). Usage: py gold.py ANALYSIS_DIR"""
import gzip, json, sys
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
MARKS = (150, 300, 500)

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
    names = {c['id']: c['name'] for c in meta['champions']}
    rix = {r: i for i, r in enumerate(R['round'])}
    acc = []
    for c in R['champions']:
        role = 'W' if c['team'] == winner else 'L'
        for m in MARKS:
            i = rix.get(m)
            if i is None: continue
            acc.append((role, names[c['id']], m, c['gold'][i], c['earned'][i], c['gems'][i], c['maxHp'][i] if 'maxHp' in c else 0))
    side = {g['id']: g['side'] for g in mp['groups']}
    caps = []
    for e in ev:
        if e['k'] == 'capture' and e['r'] <= 500:
            s = side.get(e['g'], -1)
            rel = 'mid' if s == -1 else ('own' if s == e['team'] else 'enemy')
            caps.append(('W' if e['team'] == winner else 'L', rel, sum(x[1] for x in e['shares'])))
    return acc, caps

def main():
    root = Path(sys.argv[1])
    dirs = [p for p in root.iterdir() if (p/'meta.json').exists()]
    T = defaultdict(lambda: [0, 0, 0, 0, 0]); C = defaultdict(int)
    with ProcessPoolExecutor(24) as ex:
        for o in ex.map(game, dirs, chunksize=4):
            if not o: continue
            for role, n, m, gold, earned, gems, hp in o[0]:
                t = T[(n, m, role)]; t[0] += 1; t[1] += gold; t[2] += earned; t[3] += gems; t[4] += hp
            for role, rel, g in o[1]: C[(role, rel)] += g
    print('type round role: n, gold held, earned, carried gems, maxHp')
    for k in sorted(T):
        n, g, e, gm, hp = T[k]
        if n < 30: continue
        print(f'{k[0]:12s} {k[1]:4d} {k[2]} n={n:4d} held {g/n:6.0f} earned {e/n:6.0f} gems {gm/n:5.0f} maxhp {hp/n:5.0f}')
    print('capture gems r<=500 by side:', {k: v for k, v in sorted(C.items())})

if __name__ == '__main__':
    main()
