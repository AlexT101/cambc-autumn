"""Line G (pursuit) counts, CAND side vs REF side, from an extracted A/B batch: kills, deaths (by champions, by camps),
gems taken by kills, a game; with --stdout BATCH_DIR also the PURSUE debug lines a game (one per champion turn) and
the share of those admitted chases whose chaser died within 10 rounds.

    py research/mx-tethys/scripts/pursue_stats.py ANALYSIS_ROOT BATCH_NAME CAND_NAME [--stdout BATCH_DIR]
"""
import gzip, json, sys, zipfile
from collections import Counter
from pathlib import Path

root, bname, cand = Path(sys.argv[1]), sys.argv[2], sys.argv[3]
stdout_dir = Path(sys.argv[sys.argv.index('--stdout') + 1]) if '--stdout' in sys.argv else None
c = {s: Counter() for s in ('CAND', 'REF')}
games = 0
for dd in sorted(root.iterdir()):
    mf = dd / 'meta.json'
    if not mf.exists():
        continue
    m = json.loads(mf.read_text())
    src = next((s for s in m.get('sources', []) if bname in s['source']), None)
    if not src:
        continue
    ev = [json.loads(l) for l in gzip.open(dd / 'events.jsonl.gz', 'rt')]
    games += 1
    side_of_team = {i: ('CAND' if t['name'] == cand else 'REF') for i, t in enumerate(src['teams'])}
    team = {x['id']: x['team'] for x in m['champions']}
    side = {i: side_of_team[t] for i, t in team.items()}
    w = m['result']['winner']
    c[side_of_team[w]]['wins'] += 1
    deaths = {}
    for e in ev:
        if e['k'] != 'death' or e['v'] not in side:
            continue
        deaths.setdefault(e['v'], []).append(e['r'])
        if e.get('linked') is not None:
            continue
        vs = side[e['v']]
        if e.get('by') in side:
            c[side[e['by']]]['kills'] += 1
            c[vs]['deaths_champ'] += 1
        else:
            c[vs]['deaths_camp'] += 1
    for e in ev:
        if e['k'] == 'death' and e.get('by') in side:
            c[side[e['by']]]['gems_by_kills'] += e.get('gemsTo', 0)
    if stdout_dir:
        f = stdout_dir / Path(src['source']).name
        if not f.exists():
            continue
        try:
            z = zipfile.ZipFile(f)
        except Exception:
            continue
        for ti, letter in ((0, 'a'), (1, 'b')):
            name = f'team-{letter}.stdout'
            if name not in z.namelist() or side_of_team[ti] != 'CAND':
                continue
            seen = set()
            for line in z.read(name).decode(errors='replace').splitlines():
                p = line.split()
                if len(p) < 4 or p[0] != 'PURSUE':
                    continue
                r, h = int(p[1]), int(p[2])
                if (r, h) in seen:
                    continue
                seen.add((r, h))
                c['CAND']['pursue'] += 1
                if any(r <= d <= r + 10 for d in deaths.get(h, [])):
                    c['CAND']['pursue_died10'] += 1
print('games', games)
for s in ('CAND', 'REF'):
    x = c[s]
    print(s, ' '.join(f'{k}={v / max(1, games):.3f}' for k, v in sorted(x.items())))
if c['CAND']['pursue']:
    print('pursue chaser died within 10 rounds:', f"{c['CAND']['pursue_died10'] / c['CAND']['pursue']:.3f}")
