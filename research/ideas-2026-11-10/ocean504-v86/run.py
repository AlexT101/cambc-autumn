"""Fixed direct benchmark of shipped Ocean506 against exact v86; queue-owned heavy work."""
import argparse
import fcntl
import hashlib
import io
import json
import math
import os
from pathlib import Path
import statistics
import subprocess
import sys
import tarfile
import time

R = Path('/home/ubuntu/cambc-autumn')
D = Path('/home/ubuntu/tmp-offload/ocean504-v86')
CAND = 'variants/oc-dfuel-506'
REF = 'variants/oc-base23'
JOB = 'ocean504-v86-100k'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write(path, value):
    Path(path).write_text(json.dumps(value, indent=2) + '\n')


def source(bot):
    root = R / 'bots' / bot / 'src'
    return {str(p.relative_to(root)): sha(p) for p in sorted(root.rglob('*')) if p.is_file()}


def committed(ref):
    raw = subprocess.check_output(['git', 'archive', ref, 'bots/ocean/src'], cwd=R)
    with tarfile.open(fileobj=io.BytesIO(raw)) as archive:
        return {p.name.removeprefix('bots/ocean/src/'): hashlib.sha256(archive.extractfile(p).read()).hexdigest()
                for p in archive.getmembers() if p.isfile()}


def verify():
    m = json.loads((D / 'manifest.json').read_text())
    for path, digest in m['files'].items():
        assert sha(path) == digest, ('Input drift', path)
    for bot, files in m['sources'].items():
        assert source(bot) == files, ('Source drift', bot)
    if (D / 'maps-seal.json').exists():
        assert sha(D / 'maps.json') == json.loads((D / 'maps-seal.json').read_text())['sha256']
        maps = json.loads((D / 'maps.json').read_text())['selected']
        assert len(maps) == len({x['sha256'] for x in maps}) == 2048
        for x in maps:
            assert sha(x['path']) == x['sha256'], x['path']
    assert subprocess.check_output(['cambc', '--version'], text=True).strip().split()[-1] == '5.0.1'
    return m


def preflight():
    m = verify()
    assert committed('dd7002a8f85d4a543e68dfc5bad99c4c2fa6d40a') == m['sources'][REF]
    assert committed('183a1295c335a83d03679f93fcb11cdbde5617b2') == m['sources'][CAND]
    return {'ready': True, 'selected_version': 506, 'selected_commit': '183a1295c335a83d03679f93fcb11cdbde5617b2',
            'head': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=R, text=True).strip(),
            'manifest_sha256': sha(D / 'manifest.json'), 'historical_v86_source_exact': True}


def command(argv, log, pooled=False):
    if pooled:
        argv = [sys.executable, R / 'tools/pooled.py', '1', '--', *argv]
    with Path(log).open('a') as out:
        out.write(json.dumps(list(map(str, argv))) + '\n'); out.flush()
        subprocess.run(list(map(str, argv)), cwd=R, stdout=out, stderr=subprocess.STDOUT, check=True)


def maps():
    if (D / 'maps.done').exists():
        verify(); return
    assert not (D / 'maps.json').exists(), 'Partial map preparation requires review'
    roots = [R / 'maps', Path('/home/ubuntu/tmp-offload/diverse/fresh/pool'),
             Path('/home/ubuntu/tmp-offload/condarms/fresh/pool'), Path('/home/ubuntu/tmp-offload/localq/maps/dl')]
    seen = set(); coverage = []
    for root in roots:
        assert root.is_dir(), root
        paths = list(root.glob('*.map26a') if root == R / 'maps' else root.rglob('*.map26a'))
        assert paths, root
        hashes = {sha(p) for p in paths}; seen.update(hashes)
        coverage.append({'path': str(root), 'map_paths': len(paths), 'distinct_hashes': len(hashes)})
    selected = []; generated_seeds = []
    for seed in range(2416000, 2416012):
        if len(selected) == 2048:
            break
        out = D / 'generated' / f'fresh-{seed}'
        assert not out.exists(), 'Partial generation requires review, no silent regeneration'
        command(['node', 'tools/mapgen/mapgen.mjs', 'suite', '--mix', 'ladder-v2', '--jobs', '1', '--seed', seed, '--out', out], D / 'maps.log', pooled=True)
        generated_seeds.append(seed)
        for p in sorted(out.glob('*.map26a')):
            h = sha(p)
            if h in seen or len(selected) == 2048:
                continue
            seen.add(h); chunk = len(selected) % 4
            directory = D / 'pool' / f'b{chunk}'; directory.mkdir(parents=True, exist_ok=True)
            link = directory / p.name; assert not link.exists(); link.symlink_to(p)
            selected.append({'path': str(link), 'sha256': h, 'chunk': chunk})
    assert len(selected) == len({x['sha256'] for x in selected}) == 2048
    assert len({Path(x['path']).stem for x in selected}) == 2048
    write(D / 'maps.json', {'selected': selected, 'generated_seeds': generated_seeds, 'novelty_scope': coverage,
                          'qualification': 'Exact byte novelty only in declared scope, plus independently reserved seeds; no universal archive claim.'})
    write(D / 'maps-seal.json', {'sha256': sha(D / 'maps.json')})
    verify(); (D / 'maps.done').write_text('complete\n')


def paired_scores(rows, expected):
    cells = {}
    for x in rows:
        assert x.get('winner') in (0, 1) and x['order'] in ([0, 1], [1, 0])
        key = (Path(x['map']).stem, tuple(x['order']))
        assert key not in cells, ('Duplicate cell', key)
        cells[key] = int(x['winner'] == 0)
    assert set(cells) == {(name, side) for name in expected for side in ((0, 1), (1, 0))}
    return {name: (cells[name, (0, 1)] + cells[name, (1, 0)]) / 2 for name in sorted(expected)}


def estimate(values):
    n = len(values); mean = statistics.mean(values); variance = statistics.variance(values)
    half = 1.96 * math.sqrt(variance / n)
    bounded = math.sqrt(2 * variance * math.log(40) / n) + 7 * math.log(40) / (3 * (n - 1))
    return {'maps': n, 'win_pct': 100 * mean, 'map_paired_normal_95ci_pct': [100 * max(0, mean-half), 100 * min(1, mean+half)],
            'map_paired_empirical_bernstein_95ci_pct': [100 * max(0, mean-bounded), 100 * min(1, mean+bounded)],
            'pair_counts': {str(x): values.count(x) for x in (0, .5, 1)}}


def report_chunk(j):
    name = f'ocean504-v86-2416000-b{j}-e501-f100k'
    sp = R / 'replays/ab' / name / 'summary.json'; s = json.loads(sp.read_text())
    games = 256 if j == 'L' else 1024
    assert s['games'] == games and s['errors'] == 0 and s['release'] is True and s['fuel'] == 100000 and s['cambc'] == '5.0.1'
    assert s['cand']['spec'] == CAND and s['ref']['spec'] == REF
    rows = []; batches = {}
    for suite in s['suites']:
        path = R / suite['batch'] / 'results.json'; b = json.loads(path.read_text())
        assert b['scheduled'] == b['completed'] == games and b['errors'] == 0
        rows.extend(b['matches']); batches[str(path)] = sha(path)
    expected = {Path(x['path']).stem for x in json.loads((D / 'maps.json').read_text())['selected'] if x['chunk'] == j}
    if j == 'L': expected = {p.stem for p in (R / 'maps').glob('*.map26a')}
    assert len(expected) == games // 2
    return paired_scores(rows, expected), {'name': name, 'summary_sha256': sha(sp), 'batches': batches,
        'counts': {k: s.get(k) for k in ('errors', 'oof', 'early_losses', 'handoff_failures', 'capped_drafts')}}


def run():
    maps(); scores = {}; ladder = {}; audit = []
    for j in ['L', 0, 1, 2, 3]:
        verify(); name = f'ocean504-v86-2416000-b{j}-e501-f100k'
        if not (R / 'replays/ab' / name / 'summary.json').exists():
            marker = D / f'chunk{j}.started'
            assert not marker.exists(), 'Interrupted batch requires review; never silently replay completed cells'
            marker.write_text(time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()))
            command([sys.executable, R / 'tools/ab.py', CAND, REF, '--no-test-draft', '--fuel', '100000', '--threads', '64',
                     '--suites', ('ladder' if j == 'L' else D / 'pool' / f'b{j}'), '--keep-replays', '1', '--name', name], D / 'games.log')
        chunk, record = report_chunk(j)
        if j == 'L': ladder = chunk
        else:
            assert not scores.keys() & chunk.keys(); scores.update(chunk)
        audit.append(record)
    assert len(scores) == 2048 and len(ladder) == 128
    verify(); write(D / 'paired-scores.json', {'fresh': scores, 'ladder': ladder})
    result = {'candidate': CAND, 'reference': REF, 'engine': '5.0.1', 'fuel': 100000, 'release': True,
              'fixed_sample_games': 4352, 'fresh_candidate_wins': round(2 * sum(scores.values())), 'fresh': estimate(list(scores.values())),
              'ladder_candidate_wins': round(2 * sum(ladder.values())), 'ladder': estimate(list(ladder.values())),
              'fresh_minus_ladder_pp': 100 * (statistics.mean(scores.values()) - statistics.mean(ladder.values())),
              'panel_note': 'Fresh is primary; ladder is a separate descriptive overfit diagnostic. No pooled primary, no interim decision.',
              'audit': audit, 'manifest_sha256': sha(D / 'manifest.json'), 'maps_sha256': sha(D / 'maps.json'),
              'scores_sha256': sha(D / 'paired-scores.json'),
              'interpretation': 'Direct whole-bundle benchmark; not per-feature attribution, live prediction or automatic promotion. All draft guard failures remain counted outcomes. No optional stopping or automatic extension.'}
    write(D / 'result.json', result); print(json.dumps(result), flush=True)


def main():
    ap = argparse.ArgumentParser(description=__doc__); ap.add_argument('--check', action='store_true'); a = ap.parse_args()
    verify()
    if a.check:
        print(json.dumps(preflight())); return
    assert os.environ.get('LOCALQ_JOB') == JOB
    assert os.environ.get('CAMBC_SLOTS') == '86' and os.environ.get('FASTRUNNER_MODE') == 'native' and not os.environ.get('CAMBC_SLOT_DIR')
    os.environ['CAMBC_SLOT_GROUP'] = JOB; os.environ['CAMBC_SLOT_WEIGHT'] = '1'
    os.environ['OMP_NUM_THREADS'] = os.environ['OPENBLAS_NUM_THREADS'] = '1'
    os.chdir(R)
    with (D / 'run.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        if not (D / 'first-heavy-start.json').exists():
            check = preflight()
            if not check['ready']:
                write(D / 'review-required.json', check); raise SystemExit(3)
            check['pid'] = os.getpid(); write(D / 'first-heavy-start.json', check)
        run()


if __name__ == '__main__':
    main()
