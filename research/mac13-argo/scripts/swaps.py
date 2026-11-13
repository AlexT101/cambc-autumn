"""Allocation slack: walk legs (maximal runs of moves) that end in a camp hit, per team; for two allies' legs starting
within 3 rounds of each other towards different groups, the Chebyshev steps saved if they swapped targets.
py swaps.py ANALYSIS_DIR [N]"""
import gzip, json, sys
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
def cheb(a, b): return max(abs(a[0]-b[0]), abs(a[1]-b[1]))
def one(d):
    try:
        meta = json.loads((d / 'meta.json').read_text())
        mp = json.loads((d / meta['mapFile']).resolve().read_text())
        R = json.load(gzip.open(d / 'rounds.json.gz'))
        ev = [json.loads(l) for l in gzip.open(d / 'events.jsonl.gz', 'rt')]
    except Exception:
        return None
    C = R['champions']; idx = {c['id']: i for i, c in enumerate(C)}; rid = {r: i for i, r in enumerate(R['round'])}
    camp_group = {c['id']: c['group'] for c in mp['camps']}
    gtiles = {g['id']: [tuple(t) for t in g['tiles']] for g in mp['groups']}
    hit = defaultdict(dict)
    for e in ev:
        if e['k'] == 'attack' and e.get('camp') is not None and e['r'] <= 600:
            hit[e['a']].setdefault(e['r'], camp_group.get(e['camp']))
    legs = []
    for c in C:
        start = None
        for i in range(1, min(len(R['round']), 600)):
            r = R['round'][i]
            moved = c['alive'][i] and c['alive'][i-1] and c['x'][i] is not None and c['x'][i-1] is not None and (c['x'][i], c['y'][i]) != (c['x'][i-1], c['y'][i-1])
            if moved and start is None: start = i - 1
            if start is not None and r in hit[c['id']]:
                g = hit[c['id']][r]
                if g is not None and i - start >= 3:
                    legs.append((c['team'], R['round'][start], (c['x'][start], c['y'][start]), g, c['id'], i - start))
                start = None
            elif start is not None and not moved and r not in hit[c['id']]:
                start = None if i - start > 40 else start
    total = sum(l[5] for l in legs); saved = 0; pairs = 0
    legs.sort(key=lambda l: l[1])
    for a in range(len(legs)):
        for b in range(a + 1, len(legs)):
            A, B = legs[a], legs[b]
            if B[1] - A[1] > 3: break
            if A[0] != B[0] or A[3] == B[3] or A[4] == B[4]: continue
            dA = min(cheb(A[2], t) for t in gtiles[A[3]]); dB = min(cheb(B[2], t) for t in gtiles[B[3]])
            sA = min(cheb(A[2], t) for t in gtiles[B[3]]); sB = min(cheb(B[2], t) for t in gtiles[A[3]])
            if sA + sB < dA + dB: saved += dA + dB - sA - sB; pairs += 1
    return total, saved, pairs, len(legs)
if __name__ == '__main__':
    root = Path(sys.argv[1]); n = int(sys.argv[2]) if len(sys.argv) > 2 else 600
    dirs = [p for p in root.iterdir() if (p / 'meta.json').exists()][:n]
    T = S = P = L = 0
    with ProcessPoolExecutor(24) as ex:
        for r in ex.map(one, dirs, chunksize=8):
            if r: T += r[0]; S += r[1]; P += r[2]; L += r[3]
    print(f'legs {L}, walk rounds in legs {T}, swappable pairs {P}, steps saved by pairwise swaps {S} ({100*S/max(1,T):.1f}% of leg walking)')
