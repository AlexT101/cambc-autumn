"""Recover observed roster ranks and bound the carrying multiplier on training data."""
import argparse
import gzip
import json
from pathlib import Path


def fit(features, ranks_out, evidence_out):
    with gzip.open(features) as f:
        data = json.load(f)
    rows = data['rows']['priority']
    ranks = {}
    for p in rows:
        if (p['alive'] and not p['gems'] and p['hp'] >= p['maxhp'] and not p['enemies']
                and 2 <= -p['value'] <= p['n'] + 1):
            key = ','.join(map(str, sorted(p['rank_types'])))
            table = ranks.setdefault(key, {})
            previous = table.setdefault(p['type'], -p['value'])
            if previous != -p['value']:
                raise ValueError('inconsistent full-health rank')
    low, high, count = 0, 1, 0
    for p in rows:
        if not (p['gems'] and p['alive'] and not p['enemies'] and not p['start_enemies'] and -100 < p['value'] < 0):
            continue
        rank = ranks[','.join(map(str, sorted(p['rank_types'])))][p['type']]
        band = (-p['value'] - rank) / (p['n'] + 1)
        ratio = min(1, (p['hp'] + p['shield']) / p['maxhp'])
        low = max(low, (3-band)/(4*ratio))
        high = min(high, (4-band)/(4*ratio))
        count += 1
    Path(ranks_out).write_text(json.dumps(ranks, indent=2)+'\n')
    Path(evidence_out).write_text(json.dumps(dict(observations=count,
        multiplier_lower_exclusive=low, multiplier_upper_inclusive=high,
        caveat='Bounds conditional on the recovered floor formula; floating arithmetic affects the final digit.'), indent=2)+'\n')


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('features')
    p.add_argument('ranks_out')
    p.add_argument('evidence_out')
    a = p.parse_args()
    fit(a.features, a.ranks_out, a.evidence_out)
