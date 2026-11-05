"""Cross farm2_heading's move-consistency sets with a farm2 fit's post-spawn predictions.

For each held-out cohort's spawn episodes, after move k (1, 3, 6): is the actor still on a shortest
path to the label (Y) and/or to the predicted group (P)? Counts '-P' among misses are walks toward
our prediction that ended on another group (a re-decision on the way). Refuses to overwrite OUT.

usage: farm2_heading_report.py FIT OUT COHORT[,COHORT...]
"""
import argparse
import collections
import gzip
import json
from pathlib import Path

import numpy as np

from farm2_features import featurizer
from farm2_lib import Design, load, refuse


def main(fit_path, out, cohorts):
    refuse(out)
    f = json.loads(Path(fit_path).read_text()); fz = featurizer(f['sets'], f['opts'])
    w = f['weights']['spawn']; result = {}
    for c in cohorts:
        heading = {}
        with gzip.open(Path('replays/fish-farm2') / c / 'heading-v2.jsonl.gz', 'rt') as fh:
            for line in fh:
                h = json.loads(line); heading[h['game'], h['step']] = h['heading']
        rows = [r for r in load(c) if r['x']['reason'] == 'spawn']
        d = Design(rows, fz, keys=list(w)); pred = d.predict(np.array([w[k] for k in d.keys]))
        counts = collections.Counter()
        for r, p in zip(rows, pred):
            y = r['y']['targets'][0]; h = heading.get((r['game'], r['step']), {})
            ok = 'correct' if p == y else 'wrong'
            for k in (1, 3, 6):
                hk = h.get(str(k))
                key = 'no move' if hk is None else ('Y' if y in hk else '-') + ('P' if p in hk else '-')
                counts[f'{ok} k{k} {key}'] += 1
        result[c] = dict(sorted(counts.items()))
        print(c, json.dumps(result[c]))
    with open(out, 'x') as fo:
        json.dump(dict(fit=fit_path, cohorts=result), fo, indent=1); fo.write('\n')


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('fit'); p.add_argument('out'); p.add_argument('cohorts')
    a = p.parse_args(); main(a.fit, a.out, a.cohorts.split(','))
