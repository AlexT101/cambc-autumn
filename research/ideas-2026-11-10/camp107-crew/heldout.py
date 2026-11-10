"""Fixed unused-map confirmation; queue ops launches only after selection.json is sealed."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import fcntl
import hashlib
import json
import math
import os
from pathlib import Path
import statistics
import subprocess
import sys
import time

R = Path('/home/ubuntu/cambc-autumn')
D = Path('/home/ubuntu/tmp-offload/camp107-mechanism/heldout')


def read(p):
    return json.loads(p.read_text())


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def verify():
    manifest = read(D / 'manifest.json')
    selection = read(D / 'selection.json')
    assert selection['manifest_sha256'] == sha(D / 'manifest.json')
    assert manifest['protocol_sha256'] == sha(D / 'protocol.json')
    assert manifest['novelty_audit_sha256'] == sha(D / 'novelty-audit.json')
    assert manifest['launcher_sha256'] == sha(Path(__file__))
    candidate = selection['candidate']
    assert candidate in ('variants/c107-wakeheal2', 'variants/c107-wakecrew3')
    for name, record in manifest['sources'].items():
        root = R / 'bots' / name
        for rel, digest in record['files'].items():
            assert sha(root / rel) == digest, (name, rel, 'source changed')
        actual = {str(p.relative_to(root)) for p in (root / 'src').rglob('*') if p.is_file()}
        assert actual == {p for p in record['files'] if p.startswith('src/')}
    for m in manifest['maps']:
        assert sha(Path(m['path'])) == m['sha256'], m['path']
    names = [Path(m['path']).stem for m in manifest['maps']]
    assert len(names) == len(set(names)) == 4096
    assert len(manifest['blocks']) == 8
    assert {b['noise'] for b in manifest['blocks']} == set(range(1, 9))
    assigned = [m for b in manifest['blocks'] for m in b['names']]
    assert len(assigned) == len(set(assigned)) == 4096 and set(assigned) == set(names)
    for block in manifest['blocks']:
        assert len(block['names']) == 512
        assert {p.stem for p in Path(block['suite']).glob('*.map26a')} == set(block['names'])
    assert subprocess.check_output(['cambc', '--version'], text=True).split()[-1] == '5.0.1'
    return manifest, selection


def run_name(candidate, role, k, opponent):
    return f'hc107-{Path(candidate).name}-63671800-{role}-b{k}-{opponent}-e501-f100k'


def summary(name, count, bot, opponent):
    p = R / 'replays/ab' / name / 'summary.json'
    if not p.exists():
        return None
    s = read(p)
    assert s['games'] == count and s['errors'] == 0, (name, 'incomplete/errors')
    assert s['release'] is True and s['cambc'] == '5.0.1' and s['fuel'] == 100000
    assert s['cand']['path'] == f'bots/{bot}' and s['ref']['path'] == f'bots/{opponent}'
    assert all(v == 0 for v in s['handoff_failures'].values()), (name, 'draft handoff failure')
    return s


def cells(name, count, bot, opponent):
    s = summary(name, count, bot, opponent)
    assert s is not None
    result = {}
    for suite in s['suites']:
        for m in read(R / suite['batch'] / 'results.json')['matches']:
            assert m.get('winner') in (0, 1), (name, 'missing winner')
            key = (Path(m['map']).stem, 'a' if m['order'][0] == 0 else 'b')
            assert key not in result
            result[key] = float(m['winner'] == 0)
    assert len(result) == count
    return result


def estimate(values):
    mean = statistics.mean(values)
    # Same paired-map convention as fgate.est; these maps are each sampled once.
    half = 1.96 * statistics.pstdev(values) / math.sqrt(len(values))
    return {'map_units': len(values), 'gain_pp': 100 * mean,
            'ci95_gain_pp': [100 * (mean - half), 100 * (mean + half)],
            'equivalent_win_pct': 50 + 100 * mean}


def report(manifest, selection):
    candidate = selection['candidate']
    groups = {'all': [], 'Fish': [], 'Mite': []}
    units = {}
    validity = {'early_losses': {'cand': 0, 'base': 0, 'opponent': 0},
                'capped_drafts': {'cand': 0, 'base': 0, 'opponent': 0}}
    for block in manifest['blocks']:
        k, names = block['noise'], set(block['names'])
        count = 2 * len(names)
        by_opponent = {}
        for o in ('F', 'M'):
            opponent = f'variants/spar-dvn{k}-' + ('Flp4' if o == 'F' else 'Mt3q')
            c = cells(run_name(candidate, 'cand', k, o), count, candidate, opponent)
            b = cells(run_name(candidate, 'base', k, o), count, manifest['base'], opponent)
            for role, bot in (('cand', candidate), ('base', manifest['base'])):
                s = summary(run_name(candidate, role, k, o), count, bot, opponent)
                for key in validity:
                    validity[key][role] += s[key]['cand']
                    validity[key]['opponent'] += s[key]['ref']
            expected = {(m, side) for m in names for side in ('a', 'b')}
            assert set(c) == set(b) == expected
            by_opponent[o] = {m: statistics.mean(c[m, side] - b[m, side] for side in ('a', 'b')) for m in names}
        for m in sorted(names):
            f, t = by_opponent['F'][m], by_opponent['M'][m]
            units[m] = {'noise': k, 'Fish': f, 'Mite': t, 'all': (f + t) / 2}
            groups['Fish'].append(f)
            groups['Mite'].append(t)
            groups['all'].append((f + t) / 2)
    assert len(units) == manifest['map_count'] == 4096
    result = {'candidate': candidate, 'base': manifest['base'], 'fuel': 100000,
              'engine': '5.0.1', 'release': True, 'fixed_sample': True,
              'games_base_plus_candidate': 8 * len(units),
              'manifest_sha256': sha(D / 'manifest.json'), 'selection': selection,
              'validity': validity,
              'reads': {k: estimate(v) for k, v in groups.items()},
              'finished_utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}
    (D / 'units.json').write_text(json.dumps(units, indent=1) + '\n')
    temporary = D / 'result.json.tmp'
    temporary.write_text(json.dumps(result, indent=2) + '\n')
    temporary.replace(D / 'result.json')
    print(json.dumps(result), flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--jobs', type=int, default=4)
    ap.add_argument('--check', action='store_true')
    ap.add_argument('--report', action='store_true')
    args = ap.parse_args()
    manifest, selection = verify()
    if args.check:
        print('Sources, map suite, selection and launcher seals verified')
        return
    if args.report:
        report(manifest, selection)
        return
    lock = (D / 'run.lock').open('w')
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    (D / 'run.pid').write_text(str(os.getpid()) + '\n')
    candidate = selection['candidate']
    env = dict(os.environ, CAMBC_BIN=str(R / 'tools/fastengine/runner/fastrunner'), FASTRUNNER_MODE='native')
    tasks = [(block, o, role, bot) for block in manifest['blocks'] for o in ('F', 'M')
             for role, bot in (('base', manifest['base']), ('cand', candidate))]

    def play(task):
        block, o, role, bot = task
        k = block['noise']
        name = run_name(candidate, role, k, o)
        count = 2 * len(block['names'])
        opponent = f'variants/spar-dvn{k}-' + ('Flp4' if o == 'F' else 'Mt3q')
        if summary(name, count, bot, opponent) is not None:
            return
        cmd = [sys.executable, str(R / 'tools/ab.py'), bot, opponent, '--no-test-draft',
               '--suites', block['suite'], '--fuel', '100000', '--name', name, '--keep-replays', '1']
        with (D / 'logs' / (name + '.log')).open('w') as log:
            subprocess.run(cmd, cwd=R, env=env, stdout=log, stderr=subprocess.STDOUT, check=True)
        summary(name, count, bot, opponent)
        print(f'completed {name}', flush=True)

    (D / 'logs').mkdir(exist_ok=True)
    with ThreadPoolExecutor(max_workers=args.jobs) as pool:
        list(pool.map(play, tasks))
    verify()
    report(manifest, selection)


if __name__ == '__main__':
    main()
