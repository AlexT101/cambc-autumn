"""What explains a Prism's capture income by r<=RMAX: paired (both teams' Prisms in one game) differences of
gems captured against its time use (camp-hit rounds, hold rounds, recall rounds, dead rounds), captures, gems per
capture, shared captures, and ally capture gems within 8 of it.

    python3 pincome.py EXTRACT_DIR [--rmax 300]
"""
import argparse, gzip, json
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path


def cheb(a, b):
    return max(abs(a[0] - b[0]), abs(a[1] - b[1]))


def one(args):
    d, rmax = args
    d = Path(d)
    try:
        meta = json.loads((d / 'meta.json').read_text())
        mp = json.loads((d / meta['mapFile']).resolve().read_text())
        R = json.load(gzip.open(d / 'rounds.json.gz'))
        ev = [json.loads(l) for l in gzip.open(d / 'events.jsonl.gz', 'rt')]
    except Exception:
        return None
    pr = {m['id']: m['team'] for m in meta['champions'] if m['name'] == 'Prism'}
    if len(set(pr.values())) != 2:
        return None
    ch = {c['id']: c for c in R['champions']}
    gt = defaultdict(set)
    for c in mp['camps']:
        gt[c['group']].add((c['x'], c['y']))
    out = {t: defaultdict(float) for t in (0, 1)}
    P = {t: i for i, t in pr.items()}
    camp_r = defaultdict(set)
    hold_r = defaultdict(set)
    open_h = {}
    for e in ev:
        if e['r'] > rmax:
            break
        k = e['k']
        if k in ('attack', 'cast') and 'camp' in e and e['a'] in pr:
            camp_r[e['a']].add(e['r'])
        elif k == 'capture_hold':
            open_h.setdefault(e['g'], e['r'])
        elif k == 'capture':
            s = open_h.pop(e['g'], e['r'])
            t = e['team']
            p = P[t]
            gems = sum(x[1] for x in e['shares'])
            mine = [x for x in e['shares'] if x[0] == p]
            if mine:
                o = out[t]
                o['caps'] += 1
                o['gems'] += mine[0][1]
                o['gold'] += mine[0][2]
                o['group_gems'] += gems
                o['shared'] += len(e['shares']) > 1
                hold_r[p].update(range(s, e['r'] + 1))
            else:
                c = ch[P[t]]
                ix = e['r'] - 1
                if c['alive'][ix] and c['x'][ix] is not None:
                    dmin = min(cheb((c['x'][ix], c['y'][ix]), q) for q in gt[e['g']])
                    if dmin <= 8:
                        out[t]['ally_near_gems'] += gems
                    out[t]['ally_gems'] += gems
        elif k == 'group_respawn':
            open_h.pop(e['g'], None)
    for t in (0, 1):
        p = P[t]
        c = ch[p]
        o = out[t]
        for ix in range(min(rmax, len(c['alive']))):
            r = ix + 1
            if not c['alive'][ix]:
                o['dead'] += 1
            elif r in camp_r[p]:
                o['camp'] += 1
            elif r in hold_r[p]:
                o['hold'] += 1
            elif c['chan'][ix] and c['chanT'][ix] and c['chanT'][ix] > 0:
                o['chan'] += 1
            else:
                o['other'] += 1
        o['win'] = meta['result']['winner'] == t
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('dir')
    ap.add_argument('--rmax', type=int, default=300)
    a = ap.parse_args()
    dirs = [str(p.parent) for p in Path(a.dir).glob('*/meta.json')]
    with ProcessPoolExecutor(16) as ex:
        rs = [r for r in ex.map(one, [(x, a.rmax) for x in dirs], chunksize=8) if r]
    keys = ['gems', 'gold', 'caps', 'group_gems', 'shared', 'camp', 'hold', 'chan', 'dead', 'other', 'ally_near_gems', 'ally_gems']
    import statistics as S
    n = len(rs)
    print(n, 'games; per Prism means; then for the Prism with more gems vs fewer (paired)')
    hi = {k: [] for k in keys}
    lo = {k: [] for k in keys}
    for r in rs:
        a_, b_ = (r[0], r[1]) if r[0]['gems'] >= r[1]['gems'] else (r[1], r[0])
        for k in keys:
            hi[k].append(a_.get(k, 0))
            lo[k].append(b_.get(k, 0))
    print(f"{'metric':16s} {'richer':>8s} {'poorer':>8s}")
    for k in keys:
        print(f'{k:16s} {S.mean(hi[k]):8.1f} {S.mean(lo[k]):8.1f}')
    # correlation of diff in gems with diff in each
    import math
    dg = [h - l for h, l in zip(hi['gems'], lo['gems'])]
    for k in keys[1:]:
        dk = [h - l for h, l in zip(hi[k], lo[k])]
        mx, my = S.mean(dk), S.mean(dg)
        cov = sum((x - mx) * (y - my) for x, y in zip(dk, dg))
        vx = sum((x - mx) ** 2 for x in dk)
        vy = sum((y - my) ** 2 for y in dg)
        print(f'corr(dgems, d{k}) = {cov / math.sqrt(vx * vy) if vx and vy else 0:+.2f}')


if __name__ == '__main__':
    main()
