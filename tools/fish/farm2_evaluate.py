"""Score a farm2 fit on held-out cohorts against the wait baseline and the frozen choice logit.

Denominator: every non-opening episode labelled `hit`; rows whose label is not a candidate count as
errors. Per cohort and reason, plus a match-group bootstrap of farm2 minus choice-logit accuracy.
Writes OUT (JSON) and OUT's sibling .errors.jsonl.gz with every farm2 miss; refuses to overwrite.

usage: farm2_evaluate.py FIT OUT COHORT[,COHORT...]
"""
import argparse
import gzip
import hashlib
import json
from pathlib import Path

import numpy as np

import choice_model
from farm2_features import featurizer
from farm2_lib import Design, load, refuse, summary, wait_correct

MANIFESTS = {'model': 'research/fish-2026-11-05/manifest.json', 'third': 'research/fish-2026-11-05/third-manifest.json',
             'fourth': 'research/fish-2026-11-05/fourth-manifest.json', 'fifth': 'research/fish-2026-11-05/fifth-manifest.json',
             'confirm': 'research/fish-2026-11-05/confirmation-manifest.json'}


def match_groups(cohort):
    p = Path(MANIFESTS.get(cohort, ''))
    if not p.is_file():
        return {}
    # The 96-game confirmation manifest lacks group ids: fall back to the match id.
    return {e['sha256'][:16]: e.get('group') or e.get('match') or e['sha256'][:16] for e in json.loads(p.read_text())}


def main(fit_path, out, cohorts):
    refuse(out); err_path = Path(out).with_suffix('.errors.jsonl.gz'); refuse(err_path)
    fitted = json.loads(Path(fit_path).read_text())
    fz = featurizer(fitted['sets'], fitted['opts'])
    frozen = json.loads(Path('research/fish-2026-11-05/choice-fit.json').read_text())
    result = dict(fit=fit_path, cohorts={}, hashes={})
    rng = np.random.default_rng(0)
    with gzip.open(err_path, 'xt') as errors:
        for c in cohorts:
            rows = load(c)
            if any(r['e'] is None for r in rows):
                raise SystemExit(f'{c}: rows lack farm2 extras')
            ordered, ok, preds = [], [], []
            for reason in ('payout', 'spawn'):
                rs = [r for r in rows if r['x']['reason'] == reason]
                w = fitted['weights'][reason]
                d = Design(rs, fz, keys=list(w))
                ok.append(d.correct(np.array([w[k] for k in d.keys]))); preds.append(d.predict(np.array([w[k] for k in d.keys])))
                ordered += rs
            ok = np.concatenate(ok); preds = np.concatenate(preds)
            logit = np.array([choice_model.predict(r['x'], frozen) == r['y']['targets'][0] for r in ordered])
            wait = wait_correct(ordered)
            for r, k, p in zip(ordered, ok, preds):
                if not k:
                    errors.write(json.dumps(dict(cohort=c, game=r['game'], round=r['round'], actor=r['actor'], step=r['step'],
                                                 reason=r['x']['reason'], predicted=int(p), actual=r['y']['targets'][0]),
                                            separators=(',', ':')) + '\n')
            groups = match_groups(c)
            gid = np.array([groups.get(r['game'], r['game']) for r in ordered])
            boot = {}
            for reason in ('all', 'spawn'):
                m = np.array([reason == 'all' or r['x']['reason'] == reason for r in ordered])
                names = sorted(set(gid[m]))
                diff = {g: ((ok & m & (gid == g)).sum() - (logit & m & (gid == g)).sum(), (m & (gid == g)).sum()) for g in names}
                draws = []
                for _ in range(10000):
                    pick = rng.integers(0, len(names), len(names))
                    num = sum(diff[names[i]][0] for i in pick); den = sum(diff[names[i]][1] for i in pick)
                    draws.append(num / den)
                boot[reason] = dict(groups=len(names), lo=float(np.percentile(draws, 2.5)), hi=float(np.percentile(draws, 97.5)))
            result['cohorts'][c] = dict(farm2=summary(ordered, ok), choice_logit=summary(ordered, logit),
                                        wait=summary(ordered, wait), bootstrap_farm2_minus_logit=boot)
            for name in ('farm2', 'choice_logit', 'wait'):
                v = result['cohorts'][c][name]
                print(f'{c:>8} {name:>12}: ' + '  '.join(f"{k} {x['correct']}/{x['n']} {100 * x['accuracy']:.2f}%" for k, x in v.items()))
            print(f'{c:>8}   bootstrap farm2 - logit: ' + '  '.join(f"{k} [{100 * v['lo']:+.1f}, {100 * v['hi']:+.1f}] ({v['groups']} groups)" for k, v in boot.items()))
    for p in [fit_path, 'research/fish-2026-11-05/choice-fit.json', 'tools/fish/farm2_features.py', 'tools/fish/farm2_lib.py',
              'tools/fish/farm2_evaluate.py', 'tools/fish/choice_model.py']:
        result['hashes'][p] = hashlib.sha256(Path(p).read_bytes()).hexdigest()
    with open(out, 'x') as f:
        json.dump(result, f, indent=1); f.write('\n')


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('fit'); p.add_argument('out'); p.add_argument('cohorts')
    a = p.parse_args()
    main(a.fit, a.out, a.cohorts.split(','))
