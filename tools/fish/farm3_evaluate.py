"""Score a farm3_fit.py fit (farm3 on team memory, farm2 on own memory) and the wait baseline.

Denominator: every non-opening episode labelled `hit`; unscoreable labels count as errors. Also a
match-group bootstrap of farm3 minus farm2. Writes OUT and OUT's sibling .errors.jsonl.gz (every
farm3 miss, with farm2's prediction); refuses to overwrite either.
  python3 tools/fish/farm3_evaluate.py FIT.json OUT.json COHORT[,COHORT...] [--also NAME=FARM2_FIT.json ...]
--also scores further farm2_fit.py fits (own memory, their own sets/options) on the same rows.
"""
import argparse
import gzip
import hashlib
import json
from pathlib import Path

from farm2_features import featurizer
from farm2_lib import wait_correct
from farm3_lib import accuracy, argmax, bootstrap, fmt, rows_of, score_rows


def main(fit_path, out, cohorts, also=()):
    errs = Path(out).with_suffix('.errors.jsonl.gz')
    for p in (out, errs):
        if Path(p).exists():
            raise SystemExit(f'refusing to overwrite {p}')
    fitted = json.loads(Path(fit_path).read_text())
    run = featurizer(fitted['sets'], fitted['opts'])
    res = dict(fit=fit_path, cohorts={}, hashes={})
    with gzip.open(errs, 'xt') as ef:
        for c in cohorts + (['all'] if len(cohorts) > 1 else []):
            names = cohorts if c == 'all' else [c]
            own = rows_of(names); team = rows_of(names, team=True)
            p2 = [argmax(i, s) for i, s in score_rows(own, fitted['models']['farm2'], run)]
            p3 = [argmax(i, s) for i, s in score_rows(team, fitted['models']['farm3'], run)]
            extra = {}
            for name, path in also:
                f2 = json.loads(Path(path).read_text())
                extra[name] = accuracy(own, [argmax(i, s) for i, s in score_rows(own, f2, featurizer(f2['sets'], f2['opts']))])
            wait = wait_correct(own)
            pw = [r['y']['targets'][0] if ok else -1 for r, ok in zip(own, wait)]
            res['cohorts'][c] = dict(farm3=accuracy(own, p3), farm2=accuracy(own, p2), wait=accuracy(own, pw),
                                     boot_farm3_minus_farm2=dict(all=bootstrap(own, p3, p2),
                                                                 spawn=bootstrap([r for r in own if r['x']['reason'] == 'spawn'],
                                                                                 [p for r, p in zip(own, p3) if r['x']['reason'] == 'spawn'],
                                                                                 [p for r, p in zip(own, p2) if r['x']['reason'] == 'spawn'])),
                                     **extra)
            for k in ('farm3', 'farm2', 'wait', *extra):
                print(f'{c:>8} {k:>6}: {fmt(res["cohorts"][c][k])}')
            b = res['cohorts'][c]['boot_farm3_minus_farm2']
            print(f'{c:>8}  farm3-farm2: all [{100 * b["all"]["lo"]:+.1f}, {100 * b["all"]["hi"]:+.1f}] spawn [{100 * b["spawn"]["lo"]:+.1f}, '
                  f'{100 * b["spawn"]["hi"]:+.1f}] ({b["all"]["units"]} groups)')
            if c != 'all':
                for r, a, b2 in zip(own, p3, p2):
                    if a != r['y']['targets'][0]:
                        ef.write(json.dumps(dict(cohort=c, game=r['game'], round=r['round'], actor=r['actor'], step=r['step'],
                                                 reason=r['x']['reason'], farm3=a, farm2=b2, actual=r['y']['targets'][0]),
                                            separators=(',', ':')) + '\n')
    for p in [fit_path, *(q for _, q in also), 'tools/fish/farm3_lib.py', 'tools/fish/farm3_memory.py', 'tools/fish/farm3_evaluate.py',
              'tools/fish/farm2_features.py', 'tools/fish/farm2_lib.py']:
        res['hashes'][p] = hashlib.sha256(Path(p).read_bytes()).hexdigest()
    with open(out, 'x') as f:
        json.dump(res, f, indent=1); f.write('\n')


if __name__ == '__main__':
    a = argparse.ArgumentParser(description=__doc__)
    a.add_argument('fit'); a.add_argument('out'); a.add_argument('cohorts'); a.add_argument('--also', action='append', default=[])
    x = a.parse_args()
    main(x.fit, x.out, x.cohorts.split(','), [tuple(v.split('=', 1)) for v in x.also])
