"""Fit the farm3 destination model and its farm2 reference on the same cohorts (FARM3.md section 3).

farm3 = farm2's features and logit (sets base+hp+rate+home+stale+crew+size, gems at 3 gold, crew
Strength in the clear time) computed on team-union camp memory (farm3_memory.py) instead of the
actor's own memory. farm2 = the same fit on own memory. Payout and spawn weights separate, L2 0.1.
  python3 tools/fish/farm3_fit.py OUT.json COHORT[,COHORT...]
"""
import argparse
import hashlib
import json
from pathlib import Path

from farm3_lib import FARM2_OPTS, FARM2_SETS, fit_farm2, rows_of

CODE = ['tools/fish/farm3_lib.py', 'tools/fish/farm3_common.py', 'tools/fish/farm3_memory.py', 'tools/fish/farm3_fit.py',
        'tools/fish/farm2_lib.py', 'tools/fish/farm2_features.py', 'tools/fish/choice_model.py']


def main(out, cohorts):
    if Path(out).exists():
        raise SystemExit(f'refusing to overwrite {out}')
    res = dict(cohorts=cohorts, sets=FARM2_SETS, opts=FARM2_OPTS, l2=0.1, models={})
    for name, team in (('farm2', False), ('farm3', True)):
        model, _ = fit_farm2(rows_of(cohorts, team=team))
        res['models'][name] = dict(team_memory=team, weights=model['weights'])
        print(name, 'fitted')
    res['code'] = {p: hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in CODE}
    with open(out, 'x') as f:
        json.dump(res, f, indent=1); f.write('\n')


if __name__ == '__main__':
    a = argparse.ArgumentParser(description=__doc__)
    a.add_argument('out'); a.add_argument('cohorts')
    x = a.parse_args()
    main(x.out, x.cohorts.split(','))
