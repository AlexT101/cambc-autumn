"""Time use of one champion type r<=RMAX (default Prism): camp-hit, hold (on a hold of its team in progress), dead,
recall (the 5 rounds before a completed recall), on own spawn, walking toward the next camp hit (empty / with a
bag), toward an altar tribute, other. Also the rounds a recall trip costs: recall_end -> next camp hit or hold.

    python3 ptime.py EXTRACT_DIR [--type Prism] [--rmax 400]
"""
import argparse, gzip, json
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path


def one(args):
    d, typ, rmax = args
    d = Path(d)
    try:
        meta = json.loads((d / 'meta.json').read_text())
        mp = json.loads((d / meta['mapFile']).resolve().read_text())
        R = json.load(gzip.open(d / 'rounds.json.gz'))
        ev = [json.loads(l) for l in gzip.open(d / 'events.jsonl.gz', 'rt')]
    except Exception:
        return None
    ids = {m['id'] for m in meta['champions'] if m['name'] == typ}
    if not ids:
        return None
    ch = {c['id']: c for c in R['champions']}
    sp = mp['spawn']
    gt = defaultdict(set)
    for c in mp['camps']:
        gt[c['group']].add((c['x'], c['y']))
    camp = defaultdict(set)
    recall = defaultdict(set)
    trib = defaultdict(set)
    holds = defaultdict(set)  # round -> (team, tile)
    open_h = {}
    open_t = {}
    rend = defaultdict(list)
    for e in ev:
        k = e['k']
        r = e['r']
        if k in ('attack', 'cast') and 'camp' in e:
            camp[e['a']].add(r)
        elif k == 'recall_end':
            recall[e['a']].update(range(r - 5, r))
            rend[e['a']].append(r)
        elif k == 'tribute_start':
            open_t[e['a']] = r
        elif k in ('tribute_end', 'tribute_cancel'):
            s = open_t.pop(e['a'], None)
            if s:
                trib[e['a']].update(range(s, r + 1))
        elif k == 'capture_hold':
            open_h.setdefault(e['g'], (r, e['team']))
        elif k in ('capture', 'group_respawn'):
            h = open_h.pop(e['g'], None)
            if h:
                for rr in range(h[0], r + 1):
                    for t in gt[e['g']]:
                        holds[rr].add((h[1], t))
    out = Counter()
    for cid in ids:
        c = ch[cid]
        t = c['team']
        s = sp[t]
        hits = sorted(x for x in camp[cid] | {rr for rr in range(1, rmax + 1) if False})
        for ix in range(min(rmax, len(c['alive']))):
            r = ix + 1
            if not c['alive'][ix]:
                k = 'dead'
            elif r in camp[cid]:
                k = 'camp'
            elif (t, (c['x'][ix], c['y'][ix])) in holds[r]:
                k = 'hold'
            elif r in trib[cid]:
                k = 'tribute'
            elif r in recall[cid]:
                k = 'recall'
            elif s['minX'] <= c['x'][ix] <= s['maxX'] and s['minY'] <= c['y'][ix] <= s['maxY']:
                k = 'spawn'
            elif ix > 0 and c['x'][ix - 1] == c['x'][ix] and c['y'][ix - 1] == c['y'][ix]:
                k = 'still'
            else:
                k = 'moving'
            out[k] += 1
        for r in rend[cid]:
            if r > rmax:
                continue
            nxt = [x for x in camp[cid] if x > r]
            if nxt:
                out['trips'] += 1
                out['trip_out_rounds'] += min(nxt) - r
        out['bodies'] += 1
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('dir')
    ap.add_argument('--type', default='Prism')
    ap.add_argument('--rmax', type=int, default=400)
    a = ap.parse_args()
    dirs = [str(p.parent) for p in Path(a.dir).glob('*/meta.json')]
    tot = Counter()
    with ProcessPoolExecutor(16) as ex:
        for r in ex.map(one, [(x, a.type, a.rmax) for x in dirs], chunksize=8):
            if r:
                tot.update(r)
    b = tot['bodies']
    print(f"{a.type}: {b} bodies, r<={a.rmax}, rounds per body")
    for k in ('camp', 'hold', 'tribute', 'recall', 'spawn', 'still', 'moving', 'dead'):
        print(f'{k:12s} {tot[k] / b:7.1f}  ({100 * tot[k] / (a.rmax * b):4.1f}%)')
    print(f"completed recalls {tot['trips'] / b:.1f} a body; rounds from arrival to the next camp hit {tot['trip_out_rounds'] / max(tot['trips'], 1):.1f}")


if __name__ == '__main__':
    main()
