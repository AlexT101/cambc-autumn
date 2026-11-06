#!/usr/bin/env python3
"""logsel.py AB_NAME [--json OUT]: the random gambit logger's data (CAND = oc-cb-log*). Each CAND-cooked game: the
gambit set drawn at its first cook (CBK mask), the scores and round then, the outcome, and map features from the
suites' index.json. Prints comeback by gambit overall and by state bins; --json keeps the rows for fitting."""
import json, os, sys, glob, zipfile, collections, math

NAMES = {0: 'normal', 1: 'pull', 4: 'deny', 8: 'items', 64: 'snipe', 2: 'hunt', 10: 'hunt+items', 16: 'ambush', 32: 'hop'}

def index_metrics():
    out = {}
    for ix in glob.glob('maps/suites/fresh/fresh-5443*/index.json'):
        d = json.load(open(ix))
        for m in d.get('maps', d if isinstance(d, list) else []):
            name = m.get('file') or m.get('name')
            if name: out[os.path.basename(name).replace('.map26a', '')] = m
    return out

def main():
    name = sys.argv[1]
    out = sys.argv[sys.argv.index('--json') + 1] if '--json' in sys.argv else None
    rows = []
    for b in sorted(glob.glob(f'replays/batch-*-ab-{name}-*')):
        for m in json.load(open(f'{b}/results.json'))['matches']:
            if m.get('winner') is None: continue
            f = m['replay']
            cand_a = m['order'][0] == 0
            try:
                txt = zipfile.ZipFile(f).read('team-a.stdout' if cand_a else 'team-b.stdout').decode(errors='replace')
            except Exception:
                continue
            first = None
            for line in txt.splitlines():
                p = line.split()
                if len(p) >= 8 and p[0] == 'CBK' and p[3] == '0' and int(p[4]) >= 1:
                    first = p; break
            if not first: continue
            r, lvl, mask, us, them = int(first[1]), int(first[4]), int(first[5]), int(first[6]), int(first[7])
            rows.append({'map': os.path.basename(m['map']).replace('.map26a', ''), 'cand_a': cand_a, 'round': r, 'level': lvl,
                         'mask': mask, 'us': us, 'them': them, 'won': int(m['winner'] == 0), 'end': m['rounds']})
    if out: json.dump(rows, open(out, 'w'))
    by = collections.defaultdict(list)
    for x in rows: by[x['mask']].append(x['won'])
    print(f'cooked games {len(rows)}')
    for k, v in sorted(by.items(), key=lambda kv: -sum(kv[1]) / len(kv[1])):
        p = sum(v) / len(v)
        print(f'  {NAMES.get(k, k):12s} n {len(v):5d} comeback {100 * p:5.1f} ± {196 * math.sqrt(p * (1 - p) / len(v)):.1f}')
    def binned(label, key, edges):
        print(label)
        for lo, hi in zip(edges, edges[1:]):
            sel = [x for x in rows if lo <= key(x) < hi]
            if not sel: continue
            base = [x['won'] for x in sel if x['mask'] == 0]
            line = f'  [{lo},{hi}) n {len(sel)}: normal {100 * sum(base) / max(1, len(base)):.1f} ({len(base)})'
            for k in sorted(by):
                if k == 0: continue
                v = [x['won'] for x in sel if x['mask'] == k]
                if v: line += f' | {NAMES.get(k, k)} {100 * sum(v) / len(v) - 100 * sum(base) / max(1, len(base)):+.1f}'
            print(line)
    binned('by cook round', lambda x: x['round'], [0, 400, 550, 700, 900, 2001])
    binned('by their need over ours (ratio)', lambda x: (1000 - x['us']) / max(1, 1000 - x['them']), [0, 1.4, 1.7, 2.0, 2.5, 100])
    binned('by gap', lambda x: x['them'] - x['us'], [0, 175, 225, 300, 1000])

if __name__ == '__main__':
    main()
