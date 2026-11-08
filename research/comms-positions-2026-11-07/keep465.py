"""CHANGES 465 keep-or-revert: CAND (bot 1 of each batch) win %, paired by map, overall and split by Willow drafted.

py keep465.py DRAFTS_TSV BATCH_DIR [BATCH_DIR ...]

DRAFTS_TSV is tools/replay/drafts.mjs's output for the batches' replays (path, team A picks, team B picks). A map
counts as Willow if either game on it has Willow on either team (ocean's own draft picks it on both sides or neither).
The CI is over maps (each map's two games averaged), so the sides' correlation is accounted for.
"""
import collections, json, math, os, sys


def wilson(w, n):
    if n == 0: return (0, 0)
    p, z = w / n, 1.96
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return 100 * (c - h), 100 * (c + h)


def paired(scores):
    n = len(scores)
    if n < 2: return float('nan'), float('nan'), float('nan')
    m = sum(scores) / n
    v = sum((x - m) ** 2 for x in scores) / (n - 1)
    h = 1.96 * math.sqrt(v / n)
    return 100 * m, 100 * (m - h), 100 * (m + h)


def main():
    willow_games = set()
    for line in open(sys.argv[1]):
        p = line.rstrip('\n').split('\t')
        if len(p) >= 3 and ('Willow' in p[1] or 'Willow' in p[2]): willow_games.add(os.path.basename(p[0]))
    per_map = collections.defaultdict(list)  # map -> [cand score per game]
    willow_map = collections.defaultdict(bool)
    missing = 0
    for b in sys.argv[2:]:
        r = json.load(open(os.path.join(b, 'results.json')))
        for m in r['matches']:
            if m.get('winner') is None: continue
            per_map[m['map']].append(1.0 if m['winner'] == 0 else 0.0)
            rep = os.path.basename(m.get('replay') or '')
            if rep in willow_games: willow_map[m['map']] = True
    out = {}
    for label, keep in (('all', lambda k: True), ('willow', lambda k: willow_map[k]), ('non-willow', lambda k: not willow_map[k])):
        maps = [k for k in per_map if keep(k)]
        games = [x for k in maps for x in per_map[k]]
        w, n = sum(games), len(games)
        both = [sum(per_map[k]) / 2 for k in maps if len(per_map[k]) == 2]
        mean, lo, hi = paired(both)
        out[label] = dict(maps=len(maps), games=n, wins=w, pct=100 * w / n if n else float('nan'), wilson=wilson(w, n),
                          paired_maps=len(both), paired_pct=mean, paired_ci=(lo, hi))
        print(f"{label:11s} games {n:7d} maps {len(maps):6d}  win {out[label]['pct']:.2f}%  wilson {out[label]['wilson'][0]:.2f}-{out[label]['wilson'][1]:.2f}"
              f"  paired({len(both)} maps) {mean:.2f} [{lo:.2f}, {hi:.2f}]")
    print(json.dumps(out))


if __name__ == '__main__':
    main()
