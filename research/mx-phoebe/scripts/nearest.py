"""At each farm leg start (r<=RMAX; the round after a body's capture payout or its last camp hit before a gap), the
crow distance to the group it hit next vs the nearest group then alive and asleep (any; with gems; on own side or mid),
and how many such groups were nearer than the chosen one. Groups by side relative to the body's team.

    python3 nearest.py EXTRACT_DIR [--rmax 400]
"""
import argparse, gzip, json
from collections import Counter, defaultdict
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
    G = {g['id']: g for g in mp['groups']}
    tiles = defaultdict(list)
    for c in mp['camps']:
        tiles[c['group']].append((c['x'], c['y']))
    camp_group = {c['id']: c['group'] for c in mp['camps']}
    # group state per round: forward fill
    rows = defaultdict(list)
    for r in R['groups']:
        rows[r[1]].append(r)
    avail = defaultdict(set)  # round -> groups alive asleep
    for g, rs in rows.items():
        rs.sort()
        for j, r in enumerate(rs):
            r1 = rs[j + 1][0] if j + 1 < len(rs) else rmax + 1
            if r[2] == 1 and r[6] == 0:
                for rr in range(r[0], min(r1, rmax + 1)):
                    avail[rr].add(g)
    typ = {m['id']: m['name'] for m in meta['champions']}
    hits = defaultdict(list)
    for e in ev:
        if e['k'] in ('attack', 'cast') and 'camp' in e and e['r'] <= rmax:
            hits[e['a']].append((e['r'], camp_group[e['camp']]))
    out = Counter()
    for c in R['champions']:
        cid = c['id']
        t = c['team']
        hs = sorted(set(hits[cid]))
        for (r0, g0), (r1, g1) in zip(hs, hs[1:]):
            if g1 == g0 or r1 - r0 < 4:
                continue
            ix = r0  # round r0+1 start position
            if ix >= len(c['x']) or c['x'][ix] is None or not c['alive'][ix]:
                continue
            p = (c['x'][ix], c['y'][ix])
            dch = min(cheb(p, q) for q in tiles[g1])
            av = avail.get(r0 + 1, set())
            def side(g):
                s = G[g]['side']
                return 'mid' if s == -1 else ('own' if s == t else 'enemy')
            cand = [(min(cheb(p, q) for q in tiles[g]), g) for g in av if G[g]['gems'] > 0]
            cand_safe = [x for x in cand if side(x[1]) != 'enemy']
            out['legs'] += 1
            out['chosen_d'] += dch
            out['chosen_' + side(g1)] += 1
            out['chosen_gems'] += G[g1]['gems']
            if cand_safe:
                nd, ng = min(cand_safe)
                out['nearest_safe_d'] += nd
                out['nearest_safe_gems'] += G[ng]['gems']
                out['n_safe_nearer'] += sum(1 for x in cand_safe if x[0] < dch)
                out['has_safe'] += 1
                if nd + 5 <= dch:
                    out['nearer_by5'] += 1
            out['n_avail_gem_groups'] += len(cand)
            tn = typ[cid]
            out['legs_' + tn] += 1
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('dir')
    ap.add_argument('--rmax', type=int, default=400)
    a = ap.parse_args()
    dirs = [str(p.parent) for p in Path(a.dir).glob('*/meta.json')]
    tot = Counter()
    with ProcessPoolExecutor(16) as ex:
        for r in ex.map(one, [(x, a.rmax) for x in dirs], chunksize=8):
            if r:
                tot.update(r)
    L = tot['legs']
    print(f"legs {L}; chosen crow distance {tot['chosen_d'] / L:.1f}, chosen group gems {tot['chosen_gems'] / L:.1f}; sides own {tot['chosen_own'] / L:.2f} mid {tot['chosen_mid'] / L:.2f} enemy {tot['chosen_enemy'] / L:.2f}")
    h = tot['has_safe']
    print(f"available (alive, asleep) gem groups at leg start {tot['n_avail_gem_groups'] / L:.1f}; nearest own/mid one {tot['nearest_safe_d'] / h:.1f} tiles ({tot['nearest_safe_gems'] / h:.1f} gems); own/mid groups nearer than the chosen {tot['n_safe_nearer'] / h:.2f}; nearest is 5+ nearer {100 * tot['nearer_by5'] / h:.1f}%")


if __name__ == '__main__':
    main()
