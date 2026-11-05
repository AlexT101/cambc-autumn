"""Evaluate frozen predictors and retain every error with a replay/step key."""
import argparse
import collections
import gzip
import hashlib
import json
from pathlib import Path
from model import base_rank, effective_hp, heal_value, predict_priority, predict_attack, predict_heal


def evaluate(features, output):
    with gzip.open(features) as f:
        data = json.load(f)
    rows = data['rows']
    errors = []
    result = {'features': str(features), 'games': len(data['games']), 'metrics': {}}

    def measure(name, observations, predictor, actual, baseline=None):
        n = good = covered = base_good = 0
        per_game = collections.defaultdict(lambda: [0, 0])
        for r in observations:
            n += 1
            prediction = predictor(r)
            if prediction is None:
                continue
            covered += 1
            ok = prediction == actual(r)
            good += ok
            if baseline:
                base_good += baseline(r) == actual(r)
            per_game[r['game']][0] += ok
            per_game[r['game']][1] += 1
            if not ok:
                errors.append(dict(metric=name, predicted=prediction, actual=actual(r), observation=r))
        result['metrics'][name] = dict(eligible=n, predicted=covered, correct=good,
            accuracy=good/covered if covered else None, coverage=covered/n if n else None,
            baseline_correct=base_good if baseline else None, per_game=dict(per_game))

    measure('quiet_priority_write', rows['priority'], predict_priority, lambda r: r['value'],
            lambda r: -base_rank(r['rank_types'], r['type']))
    measure('attack_target', rows['attack'], predict_attack, lambda r: r['target'],
            lambda r: min(r['candidates'], key=lambda c: (c['hp'], c['id']))['id'])
    measure('attack_target_multiple', [r for r in rows['attack'] if len(r['candidates']) > 1], predict_attack, lambda r: r['target'],
            lambda r: min(r['candidates'], key=lambda c: (c['hp'], c['id']))['id'])
    measure('heal_target', rows['heal'], predict_heal, lambda r: r['target'],
            lambda r: min(r['candidates'], key=lambda c: (c['hp']/c['maxHp'], c['id']))['id'])
    measure('heal_target_multiple', [r for r in rows['heal'] if len(r['candidates']) > 1], predict_heal, lambda r: r['target'],
            lambda r: min(r['candidates'], key=lambda c: (c['hp']/c['maxHp'], c['id']))['id'])
    result['priority_sign_vs_direct_champion_target'] = {str(k): v for k,v in collections.Counter(
        (r['attacked_champion'], (r['value']>0)-(r['value']<0)) for r in rows['priority']).items()}
    result['attack_champion_when_available'] = dict(total=len(rows['attack']), champion=sum(r['target'] is not None for r in rows['attack']))
    result['sha256'] = {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in (
        Path(__file__).with_name('model.py'), Path(__file__).resolve().parents[2]/'research/fish-2026-11-05/priority-ranks.json')}
    dest = Path(output)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(result, indent=2)+'\n')
    with gzip.open(dest.with_suffix('.errors.json.gz'), 'wt') as f:
        json.dump(errors, f, separators=(',', ':'))
    print(json.dumps({k: {a:b for a,b in v.items() if a!='per_game'} for k,v in result['metrics'].items()}, indent=2))


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('features')
    p.add_argument('output')
    a = p.parse_args()
    evaluate(a.features, a.output)
