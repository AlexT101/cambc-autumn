"""Home trips: every arrival on own spawn (recall_end, or walking onto it) while alive and not from death respawn.
For each: hp fraction on arrival, gold, gems; shop spend; rounds until leaving spawn; walk-out rounds until the
next camp hit / capture hold. Per champion type and winner/loser.
py hometrips.py EXTRACT_DIR"""
import gzip, json, sys, os
from pathlib import Path
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor


def game(d):
    try:
        meta = json.loads((d / 'meta.json').read_text())
        R = json.load(gzip.open(d / 'rounds.json.gz'))
        mp = json.load(open(os.path.join(d, meta['mapFile'])))
    except Exception:
        return None
    w = meta['result']['winner']
    n = len(R['round'])
    sp = mp['spawn']
    ch = R['champions']
    names = {int(c['id']): c.get('name') for c in meta['champions']}
    team = {int(c['id']): int(c['team']) for c in meta['champions']}
    recall_end = defaultdict(set)
    shop = defaultdict(float)
    campdmg = defaultdict(set)
    for l in gzip.open(d / 'events.jsonl.gz', 'rt'):
        e = json.loads(l)
        k = e['k']
        if k == 'recall_end':
            recall_end[e['a']].add(e['r'])
        elif k == 'shop':
            shop[(e['a'], e['r'])] += -e.get('gold', 0)
        elif k == 'camp_attack':
            pass
    out = []
    for c in ch:
        cid = int(c['id']); t = int(c['team']); s = sp[t]
        on = lambda i: s['minX'] <= c['x'][i] <= s['maxX'] and s['minY'] <= c['y'][i] <= s['maxY']
        i = 1
        while i < n:
            if c['alive'][i] and c['alive'][i - 1] and on(i) and not on(i - 1):
                how = 'recall' if (i + 1) in recall_end[cid] or i in recall_end[cid] or (i + 2) in recall_end[cid] else 'walk'
                hp = c['hp'][i - 1] / max(1, c['maxHp'][i - 1])
                gold = c['gold'][i - 1]
                gems = c['gems'][i - 1]
                j = i
                spent = 0
                while j < n and c['alive'][j] and on(j):
                    spent += shop.get((cid, j + 1), 0) + shop.get((cid, j), 0)
                    j += 1
                out.append(dict(name=names.get(cid), win=t == w, how=how, hp=hp, gold=gold, gems=gems, stay=j - i,
                                spent=spent, round=i + 1))
                i = j
            else:
                i += 1
    return out


def main():
    root = Path(sys.argv[1])
    dirs = [d for d in root.iterdir() if (d / 'meta.json').exists()]
    with ProcessPoolExecutor(32) as ex:
        res = [r for r in ex.map(game, dirs, chunksize=8) if r is not None]
    HI = int(os.environ.get('HI', '99999'))
    trips = [t for r in res for t in r if t['round'] <= HI]
    print('hp<0.3', sum(t['hp']<0.3 for t in trips)/(2*len(res)), '0.3-0.6', sum(0.3<=t['hp']<0.6 for t in trips)/(2*len(res)), '0.6-0.9', sum(0.6<=t['hp']<0.9 for t in trips)/(2*len(res)), '>=0.9', sum(t['hp']>=0.9 for t in trips)/(2*len(res)))
    G = len(res)
    print('games', G, 'home arrivals per team-game', len(trips) / (2 * G))
    by = defaultdict(list)
    for t in trips:
        by[(t['name'])].append(t)
    print(f"{'type':14s} {'n/game':>6s} {'recall%':>7s} {'hp>=.9':>6s} {'hp<.5':>6s} {'gold':>5s} {'spent':>5s} {'spent0%':>7s} {'stay':>5s} {'gems>0%':>7s}")
    for k, v in sorted(by.items(), key=lambda kv: -len(kv[1])):
        m = len(v)
        print(f"{str(k):14s} {m/(2*G):6.2f} {sum(t['how']=='recall' for t in v)/m:7.2f} {sum(t['hp']>=.9 for t in v)/m:6.2f} {sum(t['hp']<.5 for t in v)/m:6.2f} "
              f"{sum(t['gold'] for t in v)/m:5.0f} {sum(t['spent'] for t in v)/m:5.0f} {sum(t['spent']==0 for t in v)/m:7.2f} {sum(t['stay'] for t in v)/m:5.1f} {sum(t['gems']>0 for t in v)/m:7.2f}")
    # reasons: hp>=.9 and spent==0 -> pure travel
    trav = [t for t in trips if t['hp'] >= 0.9 and t['spent'] == 0]
    print('arrivals at hp>=0.9 that buy nothing:', len(trav) / (2 * G), 'a team-game; of which with gems', sum(t['gems'] > 0 for t in trav) / max(1, len(trav)))
    full_shop = [t for t in trips if t['hp'] >= 0.9 and t['spent'] > 0]
    print('arrivals at hp>=0.9 that shop:', len(full_shop) / (2 * G))


if __name__ == '__main__':
    main()
