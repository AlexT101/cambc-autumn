"""Why champions recall: HP fraction at start, gold spent on arrival, rounds until their next camp hit, by type.
Usage: py recalls.py ANALYSIS_DIR"""
import gzip, json, sys
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

def game(d):
    d = Path(d)
    try:
        meta = json.loads((d/'meta.json').read_text())
        R = json.load(gzip.open(d/'rounds.json.gz'))
        ev = [json.loads(l) for l in gzip.open(d/'events.jsonl.gz', 'rt')]
    except Exception:
        return None
    names = {c['id']: c['name'] for c in meta['champions']}
    idx = {c['id']: i for i, c in enumerate(R['champions'])}
    rix = {r: i for i, r in enumerate(R['round'])}
    starts = {}; out = []
    hits = defaultdict(list)
    for e in ev:
        if e['k'] in ('attack', 'cast') and 'camp' in e: hits[e['a']].append(e['r'])
    shops = defaultdict(list)
    for e in ev:
        if e['k'] == 'shop': shops[e['a']].append((e['r'], -e.get('gold', 0)))
    for e in ev:
        if e['k'] == 'recall_start':
            starts[e['a']] = e['r']
        elif e['k'] == 'recall_end' and e['a'] in starts:
            a = e['a']; r0 = starts.pop(a); r1 = e['r']
            c = R['champions'][idx[a]]; i = rix.get(r0 - 1, 0)
            hpf = c['hp'][i] / max(1, c['maxHp'][i])
            spent = sum(g for r, g in shops[a] if r1 <= r <= r1 + 2)
            nxt = next((r for r in hits[a] if r > r1), None)
            out.append((names[a], hpf, spent, (nxt - r1) if nxt else None, e.get('gems', 0)))
    return out

def main():
    root = Path(sys.argv[1])
    dirs = [p for p in root.iterdir() if (p/'meta.json').exists()]
    T = defaultdict(lambda: defaultdict(lambda: [0, 0, 0]))
    G = 0
    with ProcessPoolExecutor(24) as ex:
        for o in ex.map(game, dirs, chunksize=4):
            if o is None: continue
            G += 1
            for n, hpf, spent, nxt, gems in o:
                kind = 'heal' if hpf < 0.6 else ('shop' if spent >= 30 else 'other')
                t = T[n][kind]; t[0] += 1; t[1] += (nxt if nxt is not None and nxt < 200 else 0); t[2] += spent
    print('games', G, ' per game: count (mean rounds from arrival to next camp hit, mean gold spent)')
    for n in sorted(T):
        row = T[n]
        print(f'{n:13s}', '  '.join(f'{k}: {row[k][0]/G:5.2f} ({row[k][1]/max(1,row[k][0]):4.1f}r, {row[k][2]/max(1,row[k][0]):4.0f}g)' for k in ('heal', 'shop', 'other')))

if __name__ == '__main__':
    main()
