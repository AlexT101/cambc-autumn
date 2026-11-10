"""One sealed 512-map Fish-only 200k screen; never launches a normal-budget test."""
import argparse
import fcntl
import hashlib
import json
import math
import os
from pathlib import Path
import statistics
import subprocess
import sys

R = Path('/home/ubuntu/cambc-autumn')
D = Path('/home/ubuntu/tmp-offload/ward-fish503-screen')


def read(p):
    return json.loads(p.read_text())


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def verify():
    m = read(D / 'manifest.json')
    assert sha(Path(__file__)) == m['launcher_sha256']
    assert sha(D / 'protocol.json') == m['protocol_sha256']
    assert sha(D / 'novelty.json') == m['novelty_sha256']
    for bot, files in m['sources'].items():
        root = R / 'bots' / bot
        actual = {str(p.relative_to(root)): sha(p) for p in (root / 'src').rglob('*') if p.is_file()}
        assert actual == files, (bot, 'source changed')
    assert len(m['maps']) == len({x['sha256'] for x in m['maps']}) == 512
    assert set(p.name for p in (D / 'suite').glob('*.map26a')) == {Path(x['path']).name for x in m['maps']}
    for x in m['maps']:
        assert sha(Path(x['path'])) == x['sha256']
    assert subprocess.check_output(['cambc', '--version'], text=True).split()[-1] == '5.0.1'
    return m, read(D / 'protocol.json')


def estimate(candidate, baseline, names):
    expected = {(name, side) for name in names for side in ('a', 'b')}
    assert set(candidate) == set(baseline) == expected
    values = [sum(candidate[name, s] - baseline[name, s] for s in ('a', 'b')) / 2 for name in sorted(names)]
    mean = statistics.mean(values)
    half = 1.96 * statistics.stdev(values) / math.sqrt(len(values))
    return {'maps': len(values), 'gain_pp': mean * 100,
            'ci95_pp': [(mean - half) * 100, (mean + half) * 100]}


def cells(name, bot, opponent):
    s = read(R / 'replays/ab' / name / 'summary.json')
    assert s['games'] == 1024 and s['errors'] == 0
    assert s['release'] is True and s['fuel'] == 200000 and s['cambc'] == '5.0.1'
    assert s['cand']['path'] == 'bots/' + bot and s['ref']['path'] == 'bots/' + opponent
    result = {}
    for suite in s['suites']:
        batch = read(R / suite['batch'] / 'results.json')
        assert batch['completed'] == batch['scheduled'] == 1024 and batch['errors'] == 0
        assert batch['release'] is True and batch['fuel'] == 200000 and batch['one_side'] is False
        for x in batch['matches']:
            assert x['winner'] in (0, 1) and x['order'] in ([0, 1], [1, 0])
            key = (Path(x['map']).stem, 'a' if x['order'][0] == 0 else 'b')
            assert key not in result
            result[key] = float(x['winner'] == 0)
    return result, {k: s[k] for k in ('early_losses', 'handoff_failures', 'capped_drafts', 'oof')}


def report(m, p):
    c, cv = cells(p['names']['candidate'], p['candidate'], p['opponent'])
    b, bv = cells(p['names']['baseline'], p['baseline'], p['opponent'])
    result = estimate(c, b, {Path(x['path']).stem for x in m['maps']})
    result.update({'candidate': p['candidate'], 'baseline': p['baseline'], 'opponent': p['opponent'],
                   'fuel': 200000, 'games': 2048, 'valid_complete_cells': True,
                   'manifest_sha256': sha(D / 'manifest.json'), 'validity': {'candidate_run': cv, 'baseline_run': bv},
                   'decision': 'POSITIVE-SCREEN' if result['ci95_pp'][0] > 0 else 'HOLD',
                   'next_step': 'No automatic extension or 100k run; explicit coordinator decision required.'})
    (D / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    parser.add_argument('--report', action='store_true')
    args = parser.parse_args()
    m, p = verify()
    if args.check:
        print('Source, maps, protocol and launcher seals verified; 2048 games maximum.')
        return
    if args.report:
        report(m, p)
        return
    with (D / 'run.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        assert not (D / 'started.json').exists(), 'Already started: no automatic replay/resume'
        for name in p['names'].values():
            assert not (R / 'replays/ab' / name).exists(), 'Outcome identity already exists'
        (D / 'started.json').write_text(json.dumps({'pid': os.getpid(), 'manifest_sha256': sha(D / 'manifest.json')}))
        env = dict(os.environ, CAMBC_BIN=str(R / 'tools/fastengine/runner/fastrunner'), FASTRUNNER_MODE='native')
        for role in ('baseline', 'candidate'):
            cmd = [sys.executable, str(R / 'tools/ab.py'), p[role], p['opponent'], '--no-test-draft',
                   '--suites', str(D / 'suite'), '--fuel', '200000', '--threads', '8',
                   '--keep-replays', '0', '--name', p['names'][role]]
            with (D / (role + '.log')).open('w') as log:
                subprocess.run(cmd, cwd=R, env=env, stdout=log, stderr=subprocess.STDOUT, check=True)
        verify()
        report(m, p)


if __name__ == '__main__':
    main()
