"""Score a frozen destination fit against the wait baseline; keep every failure."""
import argparse
import collections
import gzip
import hashlib
import json
from pathlib import Path

from choice_model import candidates, predict
from routes_model import route


def main(source, model, out):
    fit = json.loads(Path(model).read_text()); metrics = {}
    with gzip.open(Path(out).with_suffix('.errors.jsonl.gz'), 'xt') as errors:
        def check(name, r, p, y):
            m = metrics.setdefault(name, dict(n=0, correct=0, games=collections.defaultdict(lambda: [0, 0])))
            m['n'] += 1; m['correct'] += p == y
            m['games'][r['game']][0] += p == y; m['games'][r['game']][1] += 1
            if p != y:
                errors.write(json.dumps(dict(metric=name, predicted=p, actual=y, game=r['game'], round=r['round'],
                                             actor=r['actor'], step=r['step']), separators=(',', ':')) + '\n')
        with gzip.open(source, 'rt') as f:
            for line in f:
                r = json.loads(line); x = r['x']
                if x['reason'] == 'opening' or r['y']['status'] != 'hit':
                    continue
                y = r['y']['targets'][0]
                for name, p in (('logit', predict(x, fit)), ('wait', route(x, 'ready'))):
                    check(name, r, p, y); check(f'{name}/{x["reason"]}', r, p, y)
                    if len(candidates(x)) > 1:
                        check(f'{name}/multiple', r, p, y)
    for m in metrics.values():
        m['accuracy'] = m['correct'] / m['n']
    hashes = {p: hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in (source, model, 'tools/fish/choice_model.py')}
    with open(out, 'x') as f:
        json.dump(dict(hashes=hashes, metrics=metrics), f, indent=2); f.write('\n')
    for k, m in sorted(metrics.items()):
        print(f'{k:>16} {m["correct"]}/{m["n"]} {m["accuracy"]:.2%}')


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    for a in ('source', 'model', 'out'):
        p.add_argument(a)
    a = p.parse_args(); main(a.source, a.model, a.out)
