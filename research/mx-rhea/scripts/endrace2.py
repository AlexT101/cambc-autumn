"""Completed winning tributes in endgame races (both sides held a winning bag at once): during the channel, how many
enemies were alive, the nearest living enemy's distance to the channeller (min over the channel), and whether the enemy's
stunners were dead. Usage: py endrace2.py ANALYSIS_DIR"""
import gzip, json, sys
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from endrace import game as race


def game(d):
    r = race(d)
    if not r: return None
    R = json.load(gzip.open(d/'rounds.json.gz'))
    meta = json.loads((d/'meta.json').read_text())
    w = r['w']
    fin = next((a for a in r['att'][w] if a['end'] == 'end'), None)
    if not fin: return dict(done=False)
    r0, r1 = fin['r'], fin['r'] + fin['dur']
    ch = {c['id']: c for c in R['champions']}
    me = next(c for c in meta['champions'] if c['name'] == fin['who'] and c['team'] == w)
    enemies = [c for c in R['champions'] if c['team'] != w]
    alive_min, near_min, dead_rounds = 99, 99, 0
    for i in range(r0 - 1, min(r1, len(R['round']))):
        al = [e for e in enemies if e['alive'][i]]
        alive_min = min(alive_min, len(al))
        mx, my = ch[me['id']]['x'][i], ch[me['id']]['y'][i]
        for e in al:
            if e['x'][i] is not None and mx is not None:
                near_min = min(near_min, max(abs(e['x'][i] - mx), abs(e['y'][i] - my)))
    prism = [e for e in enemies if next(c for c in meta['champions'] if c['id'] == e['id'])['name'] == 'Prism']
    pdead = sum(1 for e in prism for i in range(r0 - 1, min(r1, len(R['round']))) if not e['alive'][i])
    return dict(done=True, alive_min=alive_min, near=near_min, dur=fin['dur'], n_enemy=len(enemies), pdead=pdead, prism=bool(prism),
                wipe=alive_min == 0)


if __name__ == '__main__':
    dirs = [p for p in Path(sys.argv[1]).iterdir() if (p/'meta.json').exists()]
    rows = []
    with ProcessPoolExecutor(32) as ex:
        for o in ex.map(game, dirs, chunksize=8):
            if o: rows.append(o)
    D = [r for r in rows if r['done']]
    print(f'{len(D)} completed winning tributes in races')
    print('fewest enemies alive during the channel:', Counter(r['alive_min'] for r in D).most_common())
    print('nearest enemy over the channel (Chebyshev):', Counter(min(r['near'], 12) for r in D).most_common())
    P = [r for r in D if r['prism']]
    print(f'enemy had a Prism in {len(P)}; it was dead some of the channel in {sum(1 for r in P if r["pdead"])}, all of it in {sum(1 for r in P if r["pdead"] >= r["dur"])}')
