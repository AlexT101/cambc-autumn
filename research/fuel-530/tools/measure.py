"""Paired real-budget bench metrics, plus a stdout-cap sensitivity check.

Usage: py research/fuel-530/tools/measure.py BASE CAND AUDIT_JSON OUT
AUDIT_JSON comes from audit.py and must contain both arms.
"""
import collections
import importlib.util
import json
from pathlib import Path
import sys

spec = importlib.util.spec_from_file_location('measure527', Path(__file__).parents[2] / 'fuel-527/measure.py')
measure = importlib.util.module_from_spec(spec)
spec.loader.exec_module(measure)
base, cand, audit, output = sys.argv[1:]
a, b = measure.bench(base), measure.bench(cand)
assert a.keys() == b.keys()
audit = json.loads(Path(audit).read_text())
assert {base, cand} <= {r['file'] for r in audit}
omit = {r['key'].rsplit('-', 1)[0] for arm in audit if arm['file'] in (base, cand) for r in arm['censored']}
grouped = collections.defaultdict(lambda: [0] * 8)
for k in a:
    grouped[k[0]] = [x + y for x, y in zip(grouped[k[0]], a[k] + b[k])]

def summarize(rows):
    def metrics(s):
        return [s[4] / s[0] - 1, s[5] / s[1] - 1,
                (s[6] / s[7]) / (s[2] / s[3]) - 1,
                (s[4] / s[7]) / (s[0] / s[3]) - 1,
                (s[5] / s[7]) / (s[1] / s[3]) - 1]
    totals, point, cis = measure.interval(rows, metrics)
    names = ('oof', 'shortcuts', 'mean_fuel', 'oof_per_turn', 'shortcuts_per_turn')
    return dict(maps=len(rows), games=2 * len(rows),
                baseline=dict(zip(('oof', 'shortcuts', 'fuel', 'turns'), totals[:4])),
                candidate=dict(zip(('oof', 'shortcuts', 'fuel', 'turns'), totals[4:])),
                change_pct={n: dict(estimate=100 * p, ci95=[100 * v for v in ci])
                            for n, p, ci in zip(names, point, cis)})

out = dict(full=summarize([grouped[k] for k in sorted(grouped)]),
           uncensored=summarize([grouped[k] for k in sorted(grouped) if k not in omit]),
           omitted_maps=sorted(omit),
           bootstrap=dict(unit='map, both sides together', samples=2000, seed=527),
           pairs={k: grouped[k] for k in sorted(grouped)})
Path(output).write_text(json.dumps(out, indent=2) + '\n')
print(json.dumps({k: v for k, v in out.items() if k != 'pairs'}, indent=2))
