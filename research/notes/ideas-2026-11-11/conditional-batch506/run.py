"""Queue-owned large ordinary A/B batches with two reusable runtime-configured replicas."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import fcntl
import hashlib
import importlib.util
import json
import os
import signal
from pathlib import Path
import subprocess
import sys
from processes import drain, signal_group

R = Path('/home/ubuntu/cambc-autumn')
D = Path('/home/ubuntu/tmp-offload/conditional-batch506')
T = Path(__file__).resolve().parent
OLD = Path('/home/ubuntu/tmp-offload/cond504')
BASE = 'variants/oc-dfuel-506'
CAND = {'chanM': 'variants/oc506-chanM', 'bagfF': 'variants/oc506-bagfF'}
BODY = {'F': 'variants/runtime506-Flp4', 'M': 'variants/runtime506-Mt3qro'}
CONFIGS = [{'seed': 1330001 + i, 'salt': 20001 + i, 'unmetered': True} for i in range(8)]


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write(path, obj):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + '.tmp')
    tmp.write_text(json.dumps(obj, indent=2) + '\n')
    tmp.replace(path)


def source(bot):
    root = R / 'bots' / bot / 'src'
    return {str(p.relative_to(root)): sha(p) for p in sorted(root.rglob('*')) if p.is_file()}


def verify():
    manifest = json.loads((D / 'manifest.json').read_text())
    for path, digest in manifest['files'].items():
        assert sha(path) == digest, ('Tool/input drift', path)
    for bot, files in manifest['sources'].items():
        assert source(bot) == files, ('Source drift', bot)
    return manifest


def verify_runtime(manifest):
    for key in ('FASTRUNNER_UNLIMITED_BOTS', 'FASTRUNNER_BOT_FUEL', 'FASTRUNNER_NATIVE_SO', 'FASTRUNNER_PGO_UNMETERED'):
        assert not os.environ.get(key), ('Disallowed fuel/runtime override', key)
    for key, value in manifest['runtime']['environment'].items():
        assert os.environ.get(key) == value, ('Runtime environment drift', key)
    return manifest['runtime']


def command(argv, log):
    with Path(log).open('a') as out:
        out.write(json.dumps([str(x) for x in argv]) + '\n')
        out.flush()
        owned = os.environ.get('COND_RUNTIME_SESSION') != '1'
        process = subprocess.Popen([str(x) for x in argv], cwd=R, stdout=out, stderr=subprocess.STDOUT,
                                   start_new_session=owned, env=dict(os.environ, COND_RUNTIME_SESSION='1'))
        process.owns_group = owned
        try:
            code = process.wait()
        except BaseException:
            drain(process, interrupt=True)
            raise
        else:
            drain(process, interrupt=code != 0)
            if code:
                raise subprocess.CalledProcessError(code, argv)


def pooled(argv, log):
    command([sys.executable, R / 'tools/pooled.py', '1', '--', *argv], log)


def config_for(rows):
    ordered = sorted(rows, key=lambda row: (row['sha256'], row['name']))
    return {'schema': 1, 'opponent_index': 1,
            'maps': {row['name']: CONFIGS[i % 8] for i, row in enumerate(ordered)}}


def preflight(arm):
    policy = json.loads(Path('/home/ubuntu/tmp-offload/localq/base-policy.json').read_text())
    digest = hashlib.sha256(json.dumps(sorted(source(BASE).items()), separators=(',', ':')).encode()).hexdigest()
    review = Path('/home/ubuntu/tmp-offload/localq/state/exploit504-chanM-reviewdone/done')
    return {'ready': policy['base'] == BASE and policy['base_source_sha256'] == digest and
            (arm == 'chanM' or review.exists() and review.read_text().strip() == '0'),
            'base': BASE, 'base_source_sha256': digest}


def prepare_maps(arm):
    if arm == 'bagfF':
        rows = verify_maps('chanM')
        write(D / arm / 'shared-maps.json', {'source': str(D / 'chanM/maps.json'),
              'sha256': sha(D / 'chanM/maps.json'), 'prospective': True, 'fish_seed_reservation_unused': True})
        return rows
    out = D / arm
    if (out / 'maps.json').exists():
        return verify_maps(arm)
    reservation = json.loads((D / ('seeds-' + arm + '.json')).read_text())
    roots = [R / 'maps', Path('/home/ubuntu/tmp-offload/diverse/fresh/pool'),
             Path('/home/ubuntu/tmp-offload/condarms/fresh/pool'),
             Path('/home/ubuntu/tmp-offload/localq/maps/dl'), OLD / 'pool', OLD / 'mirror/pool']
    other = D / ('bagfF' if arm == 'chanM' else 'chanM') / 'maps.json'
    seen = set()
    scope = []
    for root in roots:
        assert root.is_dir(), root
        paths = list(root.glob('*.map26a') if root == R / 'maps' else root.rglob('*.map26a'))
        assert paths, root
        hashes = {sha(path) for path in paths}
        seen.update(hashes)
        scope.append({'root': str(root), 'paths': len(paths), 'distinct': len(hashes)})
    if other.exists():
        seen.update(row['sha256'] for row in json.loads(other.read_text())['selected'])
        scope.append({'other_arm_manifest': str(other), 'sha256': sha(other)})
    selected = []
    generated = []
    replacement_index = 0
    def generate(seed):
        directory = out / 'generated' / str(seed)
        assert not directory.exists(), 'Partial map preparation needs explicit recovery review'
        pooled(['node', 'tools/mapgen/mapgen.mjs', 'suite', '--jobs', '1', '--mix', 'ladder-v2',
                '--seed', str(seed), '--out', directory], out / ('mapgen-' + str(seed) + '.log'))
        return seed, directory
    for panel in range(4):
        seeds = reservation['primary_suites'][panel * 40:(panel + 1) * 40]
        rows = []
        while len(rows) < 10240:
            assert seeds, 'Reserved replacement seeds exhausted: HOLD'
            with ThreadPoolExecutor(max_workers=8) as workers:
                # executor.map preserves reservation order, regardless of completion order.
                directories = list(workers.map(generate, seeds))
            for seed, directory in directories:
                generated.append(seed)
                for path in sorted(directory.glob('*.map26a')):
                    digest = sha(path)
                    if digest in seen or len(rows) == 10240:
                        continue
                    seen.add(digest)
                    link = out / 'pool' / str(panel) / path.name
                    link.parent.mkdir(parents=True, exist_ok=True)
                    assert not link.exists(), 'Map name collision'
                    link.symlink_to(path)
                    rows.append({'path': str(link), 'name': path.stem, 'sha256': digest, 'panel': panel})
            assert len(rows) <= 10240
            if len(rows) < 10240:
                seeds = reservation['replacement_suites'][replacement_index:replacement_index + 8]
                replacement_index += len(seeds)
        write(out / ('config-' + str(panel) + '.json'), config_for(rows))
        selected.extend(rows)
    assert len(selected) == len({x['name'] for x in selected}) == len({x['sha256'] for x in selected}) == 40960
    write(out / 'maps.json', {'selected': selected, 'generated_seeds': generated, 'novelty_scope': scope})
    pooled(['node', 'tools/draftlab/features.mjs', *[out / 'pool' / str(i) for i in range(4)],
            '--out', out / 'features.jsonl'], out / 'maps.log')
    write(out / 'maps-seal.json', {str(p): sha(p) for p in [out / 'maps.json', out / 'features.jsonl',
          *[out / ('config-' + str(i) + '.json') for i in range(4)]]})
    return verify_maps(arm)


def verify_maps(arm):
    out = D / 'chanM'
    for path, digest in json.loads((out / 'maps-seal.json').read_text()).items():
        assert sha(path) == digest, path
    rows = json.loads((out / 'maps.json').read_text())['selected']
    for row in rows:
        assert sha(row['path']) == row['sha256'], row['path']
    return rows


def batch_name(arm, phase, label, body):
    owner = 'shared506' if label == 'base' else arm
    return f'cr506-{owner}-{phase}-{label}-{body}-f200000-oppunmetered'


def batch_jobs(arm, phase, suite, config):
    return [(batch_name(arm, phase, label, body), bot, BODY[body], suite, config)
            for label, bot in [('cand', CAND[arm]), ('base', BASE)] for body in 'FM']


def batch_identity(name, bot, body, suite, config):
    manifest = json.loads((D / 'manifest.json').read_text())
    return {'name': name, 'sources': {b: source(b) for b in (bot, body)}, 'runtime': manifest['runtime'],
            'config_sha256': sha(config), 'maps': {p.stem: sha(p) for p in sorted(Path(suite).glob('*.map26a'))},
            'our_turn_fuel': 200000, 'opponent_unmetered': True, 'release': True, 'own_drafts': True,
            'both_sides': True, 'game_timeout_seconds': 120}


def validate_receipt(name, bot, body, suite, config):
    receipt = D / 'batch-provenance' / (name + '.json')
    assert json.loads(receipt.read_text()) == batch_identity(name, bot, body, suite, config), ('Cached input mismatch', name)
    return sha(receipt)


def play_jobs(arm, jobs):
    # These are four large ordinary AB controllers; native games share the existing86-slot pool.
    processes = []
    handles = []
    try:
        for name, bot, body, suite, config in jobs:
            directory = R / 'replays/ab' / name
            receipt = D / 'batch-provenance' / (name + '.json')
            if directory.exists():
                assert (directory / 'summary.json').exists(), ('Partial batch needs explicit recovery', name)
                validate_receipt(name, bot, body, suite, config)
                continue
            identity = batch_identity(name, bot, body, suite, config)
            if receipt.exists():
                assert json.loads(receipt.read_text()) == identity
            else:
                write(receipt, identity)
            log = (D / arm / (name + '.log')).open('w')
            handles.append(log)
            argv = [sys.executable, R / 'tools/ab.py', bot, body, '--no-test-draft', '--fuel', '200000',
                    '--suites', suite, '--experiment-config', config, '--game-timeout', '120', '--keep-replays', '1', '--name', name]
            processes.append(subprocess.Popen([str(x) for x in argv], cwd=R, stdout=log, stderr=subprocess.STDOUT, start_new_session=True))
        codes = [p.wait() for p in processes]
        assert all(code == 0 for code in codes), ('Failed large batch: HOLD', codes)
    except BaseException:
        for process in processes:
            signal_group(process, signal.SIGINT)
        for process in processes:
            drain(process, interrupt=True)
        raise
    finally:
        for process in processes:
            drain(process)
        for handle in handles:
            handle.close()


def main():
    def interrupted(*_):
        raise KeyboardInterrupt
    signal.signal(signal.SIGTERM, interrupted)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('arm', choices=CAND)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    manifest = verify()
    check = preflight(args.arm)
    if args.check:
        print(json.dumps({'preflight': check, 'manifest_sha256': sha(D / 'manifest.json')}))
        return
    assert check['ready']
    runtime = verify_runtime(manifest)
    assert os.environ.get('LOCALQ_JOB') == 'cond-runtime-' + args.arm
    assert os.environ.get('FASTRUNNER_MODE') == 'native' and os.environ.get('CAMBC_SLOTS') == '86'
    assert not os.environ.get('CAMBC_SLOT_DIR')
    os.environ['CAMBC_SLOT_GROUP'] = 'cond-runtime-' + args.arm
    os.environ['CAMBC_SLOT_WEIGHT'] = '1'
    os.environ['OMP_NUM_THREADS'] = os.environ['OPENBLAS_NUM_THREADS'] = '1'
    os.environ['CAMBC_COMPILE_AHEAD'] = '0'
    out = D / args.arm
    out.mkdir(parents=True, exist_ok=True)
    with (out / 'run.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        assert not (out / 'first-heavy-start.json').exists(), 'Restart requires explicit recovery review'
        write(out / 'first-heavy-start.json', {'pid': os.getpid(), 'manifest_sha256': sha(D / 'manifest.json'),
              'runtime': runtime, 'our_turn_fuel': 200000, 'designated_replica_unmetered': True,
              'ocean_mirror_both_metered': True})
        command([sys.executable, T / 'smoke.py', args.arm], out / 'smoke.log')
        maps = prepare_maps(args.arm)
        map_directory = D / 'chanM'
        for panel in range(4):
            verify()
            play_jobs(args.arm, batch_jobs(args.arm, 'p' + str(panel), map_directory / 'pool' / str(panel), map_directory / ('config-' + str(panel) + '.json')))
            command([sys.executable, T / 'report.py', args.arm, '--validate-panel', str(panel)], out / 'validation.log')
        play_jobs(args.arm, batch_jobs(args.arm, 'ladder', R / 'maps', D / 'ladder-config.json'))
        command([sys.executable, T / 'report.py', args.arm], out / 'report.log')
        command([sys.executable, T / 'mirror.py', args.arm], out / 'mirror.log')
        verify()


if __name__ == '__main__':
    main()
