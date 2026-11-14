"""One final fixed-sample read; both sides are averaged before map-level uncertainty."""
import math
import statistics


def interval(values):
    assert len(values) > 1
    n = len(values)
    mean = statistics.mean(values)
    variance = statistics.variance(values)
    radius = 1.96 * math.sqrt(variance / n)
    # The bounded diagnostic stays nonzero for an all-identical sample; it is not a second decision rule.
    bounded = math.sqrt(2 * variance * math.log(40) / n) + 14 * math.log(40) / (3 * (n - 1))
    return {'maps': n, 'mean': mean, 'standard_error': math.sqrt(variance / n),
            'normal_95': [mean - radius, mean + radius],
            'bounded_95': [max(-1, mean - bounded), min(1, mean + bounded)]}


def cells(rows, expected):
    out = {}
    for row in rows:
        from pathlib import Path
        key = (Path(row['map']).stem, tuple(row['order']))
        assert row.get('winner') in (0, 1) and key[1] in ((0, 1), (1, 0))
        assert key not in out, ('Duplicate map/side', key)
        out[key] = int(row['winner'] == 0)
    assert set(out) == {(name, side) for name in expected for side in ((0, 1), (1, 0))}
    return out


def paired(candidate, reference):
    assert candidate.keys() == reference.keys()
    maps = sorted({m for m, _ in candidate})
    return {m: sum(candidate[(m, s)] - reference[(m, s)] for s in ((0, 1), (1, 0))) / 2
            for m in maps}


def decision(target, other):
    if target['normal_95'][0] > 0 and other['normal_95'][0] > -0.0025:
        return 'POSITIVE SCREEN: coordinator review; no automatic normal-fuel run'
    if target['normal_95'][1] < 0:
        return 'NEGATIVE: target regression'
    if other['normal_95'][1] < -0.0025:
        return 'OFF-TARGET HARM: coordinator review'
    return 'UNRESOLVED: fixed allocation complete'
