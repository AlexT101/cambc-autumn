"""Retain the prospectively authorized direct metered Ocean mirror, outside replica inference."""
import argparse
import json
import math
import statistics
from pathlib import Path
import sys
from run import R, D, OLD, BASE, CAND, sha, source, verify, command, write
from stats import cells


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('arm', choices=CAND)
    args = parser.parse_args()
    verify()
    old_manifest = json.loads((OLD / 'manifest.json').read_text())
    for bot in (BASE, CAND[args.arm]):
        assert old_manifest['sources'][bot] == source(bot)
    maps = json.loads((OLD / 'mirror/maps.json').read_text())['selected']
    assert len(maps) == len({x['sha256'] for x in maps}) == 8192
    for row in maps:
        assert sha(row['path']) == row['sha256']
    if args.arm == 'chanM':
        admission = json.loads((OLD / 'chanM/mirror-manual-admission.json').read_text())
        assert admission['outcomes_not_inspected'] is True and admission['fuel'] == 200000
        assert admission['candidate'] == CAND[args.arm] and admission['base'] == BASE
        result_path = OLD / 'chanM/mirror-result-200000.json'
        result = json.loads(result_path.read_text())
        assert result['games'] == 16384 and result['maps'] == 8192 and result['fuel'] == 200000
        assert result['candidate'] == CAND[args.arm] and result['opponent'] == BASE
        assert result['manifest_sha256'] == admission['manifest_sha256'] == sha(OLD / 'manifest.json')
        assert result['map_manifest_sha256'] == sha(OLD / 'mirror/maps.json')
        assert result['paired_scores_sha256'] == sha(OLD / 'chanM/mirror-paired-scores.json')
        for audit in result['audit']:
            assert sha(R / 'replays/ab' / audit['name'] / 'summary.json') == audit['summary_sha256']
            for path, digest in audit['batches'].items():
                assert sha(path) == digest
        result = {**result, 'reused_prospectively': True, 'original_result_sha256': sha(result_path),
                  'admission_sha256': sha(OLD / 'chanM/mirror-manual-admission.json'),
                  'old_strength_results_pooled': False}
    else:
        pool = D / 'mirror-pool'
        pool.mkdir(exist_ok=True)
        for row in maps:
            path = Path(row['path'])
            link = pool / path.name
            if not link.exists():
                link.symlink_to(path.resolve())
            assert sha(link) == row['sha256']
        name = 'cr506-bagfF-ocean-mirror-f200000'
        summary = R / 'replays/ab' / name / 'summary.json'
        assert not summary.parent.exists(), 'Partial/reused mirror needs explicit recovery review'
        command([sys.executable, R / 'tools/ab.py', CAND[args.arm], BASE, '--no-test-draft', '--fuel', '200000',
                 '--suites', pool, '--game-timeout', '120', '--keep-replays', '1', '--name', name], D / args.arm / 'mirror-runs.log')
        s = json.loads(summary.read_text())
        assert s['games'] == 16384 and s['errors'] == 0 and s['fuel'] == 200000 and s['release'] is True
        assert s['cambc'] == '5.0.1' and s.get('experiment_config') is None
        assert s['cand']['spec'] == CAND[args.arm] and s['ref']['spec'] == BASE
        rows = []
        audit = {}
        for suite in s['suites']:
            path = R / suite['batch'] / 'results.json'
            batch = json.loads(path.read_text())
            assert batch['scheduled'] == batch['completed'] == 16384 and batch['errors'] == 0
            assert batch['fuel'] == 200000 and batch.get('experiment_config') is None
            assert all(row.get('runtime_config') is None for row in batch['matches'])
            rows.extend(batch['matches'])
            audit[str(path)] = sha(path)
        expected = {Path(row['path']).stem for row in maps}
        observations = cells(rows, expected)
        scores = {m: sum(observations[(m, s)] for s in ((0, 1), (1, 0))) / 2 for m in expected}
        values = list(scores.values())
        mean = statistics.mean(values)
        radius = 1.96 * statistics.stdev(values) / math.sqrt(len(values))
        bounded = math.sqrt(2 * statistics.variance(values) * math.log(40) / len(values)) + 7 * math.log(40) / (3 * (len(values) - 1))
        write(D / args.arm / 'mirror-paired-scores.json', scores)
        result = {'candidate': CAND[args.arm], 'opponent': BASE, 'games': 16384, 'maps': 8192, 'fuel': 200000,
                  'opponent_unmetered': False, 'winrate': mean, 'normal_95': [mean - radius, mean + radius],
                  'bounded_95': [max(0, mean - bounded), min(1, mean + bounded)],
                  'pair_counts': {str(x): values.count(x) for x in (0, .5, 1)},
                  'audit': audit, 'summary_sha256': sha(summary), 'map_manifest_sha256': sha(OLD / 'mirror/maps.json')}
    verify()
    write(D / args.arm / 'mirror-result-200000.json', result)
    write(D / args.arm / 'review-required.json', {'complete': True, 'stage': 'fixed replica batches and mandatory mirror complete',
          'result_sha256': sha(D / args.arm / 'result-200000.json'), 'mirror_result_sha256': sha(D / args.arm / 'mirror-result-200000.json'),
          'decision': 'Coordinator review target, off-target and mirror jointly. No automatic100k, merge, live test or next-job release.'})


if __name__ == '__main__':
    main()
