"""Healthy shop trips per champion-game, by bot and champion type, over an extracted A/B (extract.mjs --out DIR).
A healthy shop trip is a completed recall started at >= 90% health that buys on spawn (a purchase from the
arrival until it leaves spawn, at most 10 rounds). Also: all completed recalls, gold a buying trip, and rounds
from recall start to the next camp hit (the trip's cost), whole game and r1-400.
    py research/mac13-argo/scripts/shoptrips.py EXTRACT_DIR [--procs N]"""

import argparse
import os
import sys
from collections import defaultdict
from multiprocessing import Pool
from pathlib import Path
from statistics import median

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'tools' / 'replay'))


def work(d):
    from analysis.data import Game
    try:
        g = Game(d)
        R, ev, n, mp = g.rounds, g.events, g.n_rounds, g.map
    except Exception as ex:
        return {'error': repr(ex), 'dir': d}
    champs = R['champions']
    hits, shops, recs, opn = defaultdict(set), defaultdict(list), [], {}
    for e in ev:
        k, r = e['k'], e['r']
        if k in ('attack', 'cast') and e.get('cdmg') and any(a > 0 for _, a in e['cdmg']):
            hits[e['a']].add(r)
        elif k == 'shop' and (e.get('gold') or 0) < 0:
            shops[e['a']].append((r, -e['gold']))
        elif k == 'recall_start':
            opn[e['a']] = r
        elif k == 'recall_cancel':
            opn.pop(e['a'], None)
        elif k == 'recall_end' and (r0 := opn.pop(e['a'], None)) is not None:
            recs.append((e['a'], r0, r))
    out = []  # (bot, type, cid, [(r0, healthy, bought, gold, cost)])
    for c in g.champs:
        cid = c['id']
        ch = champs[g.idx[cid]]
        nr = len(ch['x'])
        trips = []
        for a, r0, r1 in recs:
            if a != cid:
                continue
            i = max(0, r0 - 2)  # end of round r0-1
            hp, mx = ch['hp'][i], ch['maxHp'][i]
            healthy = bool(hp is not None and mx and hp / mx >= 0.9)
            leave = r1
            while leave <= min(n, r1 + 10) and leave - 1 < nr and ch['alive'][leave - 1] and ch['x'][leave - 1] is not None \
                    and mp.in_spawn(c['team'], (ch['x'][leave - 1], ch['y'][leave - 1])):
                leave += 1
            gold = sum(gg for rr, gg in shops[cid] if r1 <= rr <= leave)
            nxt = next((x for x in sorted(hits[cid]) if x > r0), None)
            trips.append((r0, healthy, gold > 0, gold, (nxt - r0) if nxt else None))
        out.append((g.names[c['team']], g.name_of[cid], trips))
    return {'champs': out}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('dir')
    ap.add_argument('--procs', type=int, default=16)
    a = ap.parse_args()
    ana = Path(a.dir).resolve()
    os.environ['CAMBC_ANALYSIS'] = str(ana)
    dirs = sorted(p.name for p in ana.iterdir() if (p / 'meta.json').exists())
    # (bot, type) -> champion-games, completed recalls, healthy shop trips (all / r1-400), gold, costs
    acc = defaultdict(lambda: {'cg': 0, 'rec': 0, 'rec400': 0, 'shop': 0, 'shop400': 0, 'gold': [], 'cost': []})
    bad = 0
    with Pool(a.procs) as pool:
        for o in pool.imap_unordered(work, dirs, chunksize=4):
            if 'error' in o:
                bad += 1
                continue
            for bot, typ, trips in o['champs']:
                for key in ((bot, typ), (bot, 'ALL')):
                    s = acc[key]
                    s['cg'] += 1
                    for r0, healthy, bought, gold, cost in trips:
                        s['rec'] += 1
                        s['rec400'] += r0 <= 400
                        if healthy and bought:
                            s['shop'] += 1
                            s['shop400'] += r0 <= 400
                            s['gold'].append(gold)
                            if cost is not None:
                                s['cost'].append(cost)
    print(f'# Healthy shop trips ({len(dirs) - bad} games, {bad} errors)\n')
    print('| bot | champion | champion-games | completed recalls / cg | r1-400 | healthy shop trips / cg | r1-400 | gold a trip median | start -> next camp hit median |')
    print('|---|---|---|---|---|---|---|---|---|')
    for (bot, typ), s in sorted(acc.items(), key=lambda kv: (kv[0][1] != 'ALL', kv[0][1], kv[0][0])):
        if s['cg'] < 20 and typ != 'ALL':
            continue
        cg = s['cg']
        print(f"| {bot} | {typ} | {cg} | {s['rec'] / cg:.2f} | {s['rec400'] / cg:.2f} | {s['shop'] / cg:.2f} | {s['shop400'] / cg:.2f} | "
              f"{median(s['gold']) if s['gold'] else '-'} | {median(s['cost']) if s['cost'] else '-'} |")


if __name__ == '__main__':
    main()
