"""Kills and deaths a game for CAND and REF of ab.py runs, from extract.mjs output (kill-value.md). A Cassi & Issac
death counts once (linked deaths skipped).

usage: python3 kill_kd.py EXTRACT_DIR [EXTRACT_DIR ...]   (one per run; CAND is the team named first in ab's batches)
"""
import gzip
import json
import os
import sys
from multiprocessing import Pool


def game(args):
    ex, row = args
    d = os.path.join(ex, row['dir'])
    try:
        meta = json.load(open(os.path.join(d, 'meta.json')))
    except OSError:
        return None
    # run_batched's -12: bot 1 (CAND) is team A
    cand = 0 if row['source'].endswith('-12.repl26a') else 1
    team = {c['id']: c['team'] for c in meta['champions']}
    out = {'kills': [0, 0], 'deaths': [0, 0], 'camp_deaths': [0, 0]}
    for l in gzip.open(os.path.join(d, 'events.jsonl.gz'), 'rt'):
        if '"death"' not in l:
            continue
        e = json.loads(l)
        if e['k'] != 'death' or e.get('linked'):
            continue
        v = team[e['v']]
        side = 0 if v == cand else 1  # 0: CAND died
        out['deaths'][side] += 1
        if e.get('camp'):
            out['camp_deaths'][side] += 1
        else:
            out['kills'][1 - side] += 1
    return row['source'].split('/')[-1], out


def run(ex):
    rows = [r for r in json.load(open(os.path.join(ex, 'index.json')))['games'] if r['ok']]
    with Pool(16) as pool:
        res = [x for x in pool.map(game, [(ex, r) for r in rows], chunksize=16) if x]
    return dict(res)


def main():
    runs = {ex: run(ex) for ex in sys.argv[1:]}
    for ex, res in runs.items():
        n = len(res)
        s = {k: [sum(o[k][i] for o in res.values()) / n for i in (0, 1)] for k in ('kills', 'deaths', 'camp_deaths')}
        print(f'{ex}: {n} games; CAND kills {s["kills"][0]:.2f} deaths {s["deaths"][0]:.2f} (camps {s["camp_deaths"][0]:.2f}); '
              f'REF kills {s["kills"][1]:.2f} deaths {s["deaths"][1]:.2f} (camps {s["camp_deaths"][1]:.2f})')
    names = list(runs)
    if len(names) > 1:
        base = runs[names[0]]
        for ex in names[1:]:
            keys = sorted(set(base) & set(runs[ex]))
            for k in ('kills', 'deaths'):
                diff = [runs[ex][g][k][0] - base[g][k][0] for g in keys]
                m = sum(diff) / len(diff)
                sd = (sum((x - m) ** 2 for x in diff) / (len(diff) - 1)) ** 0.5
                print(f'  {ex} - {names[0]} CAND {k}: {m:+.3f} a game (95% CI {m - 1.96 * sd / len(diff) ** 0.5:+.3f}..'
                      f'{m + 1.96 * sd / len(diff) ** 0.5:+.3f}), {len(keys)} games')


if __name__ == '__main__':
    main()
