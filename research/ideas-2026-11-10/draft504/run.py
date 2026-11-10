"""One explicitly authorized Ocean506 draft refit; queue operations owns admission."""
import argparse
import fcntl
import hashlib
import importlib.util
import io
import json
import math
import os
import re
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile
import time

R = Path('/home/ubuntu/cambc-autumn')
D = Path('/home/ubuntu/tmp-offload/localq/rounds/draft17')
T = Path(__file__).resolve().parent
LAB = 'lq-draft17'
BASE = 'variants/oc-dfuel-506'
CAND = 'variants/lq-draft17-506'
CANDS = {'control': CAND, 'flat': 'variants/lq-draft17-flat-506', 'conditional': 'variants/lq-draft17-conditional-506'}


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def source(bot):
    p = R / 'bots' / bot / 'src'
    return {str(x.relative_to(p)): sha(x) for x in sorted(p.rglob('*')) if x.is_file()}


def write(p, x):
    Path(p).write_text(json.dumps(x, indent=2) + '\n')


def verify():
    m = json.loads((D / 'manifest.json').read_text())
    for p, h in m['files'].items():
        assert sha(p) == h, f'Changed sealed input/tool: {p}'
    for bot, files in m['sources'].items():
        assert source(bot) == files, f'Changed frozen bot: {bot}'
    return m


def start_base_check(policy, committed, sealed):
    digest = hashlib.sha256(json.dumps(sorted(sealed.items()), separators=(',', ':')).encode()).hexdigest()
    return (policy.get('base') == BASE and policy.get('base_source_sha256') == digest and committed == sealed)


def preflight():
    policy = json.loads(Path('/home/ubuntu/tmp-offload/localq/base-policy.json').read_text())
    head = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=R, text=True).strip()
    raw = subprocess.check_output(['git', 'archive', head, 'bots/ocean/src'], cwd=R)
    with tarfile.open(fileobj=io.BytesIO(raw)) as archive:
        committed = {member.name.removeprefix('bots/ocean/src/'): hashlib.sha256(archive.extractfile(member).read()).hexdigest()
                     for member in archive.getmembers() if member.isfile()}
    sealed = json.loads((D / 'manifest.json').read_text())['sources'][BASE]
    return {'ready': start_base_check(policy, committed, sealed), 'head': head, 'approved_base': policy.get('base'),
            'approved_source_sha256': policy.get('base_source_sha256'), 'sealed_base': BASE,
            'committed_main_matches': committed == sealed}


def first_start():
    # Once a heavy phase starts, keep its frozen experiment even if main later advances.
    marker = D / 'first-heavy-start.json'
    if marker.exists():
        return
    evidence = preflight()
    if not evidence['ready']:
        write(D / 'start-held.json', evidence)
        write(D / 'review-required.json', {'stage': 'HOLD before heavy work: approved or committed base changed',
                                         'evidence': evidence, 'note': 'Coordinator must review/reseal; no automatic rebase.'})
        raise SystemExit(3)
    evidence.update(pid=os.getpid(), utc=time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()))
    write(marker, evidence)


def command(argv, log):
    with (D / log).open('a') as out:
        out.write('\n' + json.dumps([str(a) for a in argv]) + '\n')
        out.flush()
        subprocess.run([str(a) for a in argv], cwd=R, stdout=out, stderr=subprocess.STDOUT, check=True)


def pooled(n, argv, log):
    command([sys.executable, R / 'tools/pooled.py', str(n), '--', *argv], log)


def symlink(target, link):
    link.parent.mkdir(parents=True, exist_ok=True)
    if link.is_symlink():
        assert link.resolve() == target.resolve(), link
    else:
        assert not link.exists(), link
        link.symlink_to(target, target_is_directory=target.is_dir())


def step(name, fn):
    done = D / (name + '.done')
    if done.exists():
        return
    verify()
    fn()
    done.write_text(time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()) + '\n')


def prepare_maps():
    p = json.loads((D / 'protocol.json').read_text())
    for kind, seeds in [('train', p['train_seeds']), *p['preference']['map_seeds'].items()]:
        pooled(1, ['node', 'tools/mapgen/mapgen.mjs', 'suite', '--jobs', '1', '--mix', 'ladder-v2', '--seed', seeds,
                   '--out', str(D / 'maps' / kind / 'fresh-{seed}')], 'maps.log')
    # New seed ranges are necessary, but duplicate generated geometry is possible.
    history = [R / 'maps', Path('/home/ubuntu/tmp-offload/diverse/fresh/pool'),
               Path('/home/ubuntu/tmp-offload/localq/maps/dl')]
    old = set()
    for root in history:
        paths = root.glob('*.map26a') if root == R / 'maps' else root.rglob('*.map26a')
        old.update(sha(x) for x in paths)
    seen = set(old)
    rows = {kind: [] for kind in ('train', 'selection', 'confirmation', 'normal')}
    for kind in rows:
        for path in sorted((D / 'maps' / kind).glob('fresh-*/*.map26a')):
            h = sha(path)
            # Preserve generated artifacts, while excluding duplicates from the selected pools.
            if h in seen:
                continue
            seen.add(h)
            selected = D / 'selected' / kind / path.name
            symlink(path, selected)
            rows[kind].append({'path': str(selected), 'sha256': h})
    assert len(rows['train']) >= 24000, len(rows['train'])
    for kind in ('selection', 'confirmation', 'normal'):
        for seed in p['preference']['replacement_seeds'][kind]:
            if len(rows[kind]) == 1024:
                break
            pooled(1, ['node', 'tools/mapgen/mapgen.mjs', 'suite', '--jobs', '1', '--mix', 'ladder-v2',
                       '--seed', str(seed), '--out', str(D / 'maps' / kind / f'fresh-{seed}')], 'maps.log')
            for path in sorted((D / 'maps' / kind / f'fresh-{seed}').glob('*.map26a')):
                h = sha(path)
                if h in seen or len(rows[kind]) == 1024:
                    continue
                seen.add(h)
                selected = D / 'selected' / kind / path.name
                symlink(path, selected)
                rows[kind].append({'path': str(selected), 'sha256': h})
        assert len(rows[kind]) == 1024, (kind, 'Reserved replacements exhausted; coordinator review required', len(rows[kind]))
        for j in range(8):
            directory = D / 'evaluation-maps' / kind / f'f{j}'
            directory.mkdir(parents=True, exist_ok=True)
            for row in rows[kind][j::8]:
                symlink(Path(row['path']), directory / Path(row['path']).name)
        pooled(1, ['node', 'tools/draftlab/features.mjs', D / 'selected' / kind,
                   '--out', D / 'evaluation-maps' / kind / 'feat.jsonl'], 'maps.log')
    write(D / 'maps.json', {'scope': [str(p) for p in history], 'historical_unique_hashes': len(old),
                           'selected': rows, 'note': 'Exact file-byte novelty and disjointness across all four pools; not a universal historical-map claim.'})


def initialise():
    (D / 'lab').mkdir(exist_ok=True)
    symlink(D / 'lab', R / 'replays/draftlab' / LAB)
    shutil.copyfile(D / 'config.json', D / 'lab/config.json')
    pooled(1, [sys.executable, 'tools/draftlab/lab.py', 'init', '--lab', LAB], 'init.log')
    for name in ('prior.json', 'ladder.jsonl'):
        shutil.copyfile(D / 'inputs' / name, D / 'lab' / name)
    cfg = json.loads((D / 'lab/config.json').read_text())
    assert cfg['source'] == 'bots/' + BASE
    assert cfg['current_lab'] == str(D / 'inputs/current')
    assert cfg['team_lock'] == {'require': [], 'ban': []}


def train():
    command([sys.executable, 'tools/draftlab/lab.py', 'run', '--lab', LAB, '--hours', '18'], 'train.log')
    m = json.loads((D / 'lab/model.json').read_text())
    assert 799000 <= m['games'] <= 800000, ('Incomplete single training run', m['games'])
    for pick in m['picks'].values():
        assert all(math.isfinite(x) for x in pick['theta'])
    text = (D / 'lab/lab.log').read_text()
    batches = re.findall(r'merged (\d+) games \((\d+) errors, (\d+) draft mismatches\)', text)
    assert batches and all(int(errors) == 0 for _, errors, _ in batches), 'Training run errors need review'
    write(D / 'training-quality.json', {'merged_batch_records': len(batches),
          'errors': sum(int(x[1]) for x in batches), 'draft_mismatches': sum(int(x[2]) for x in batches),
          'early_loss_log_lines': [line for line in text.splitlines() if '!!!' in line],
          'note': 'Mismatched drafts are excluded by the existing fitter. Early outcomes remain recorded for review.'})


def fit():
    (D / 'f92').mkdir(exist_ok=True)
    symlink(D / 'f92', R / 'replays/draftlab' / (LAB + '-f92'))
    for name in ('games.jsonl', 'games.slim.json', 'games.slim.jsonl', 'ladder.jsonl', 'maps.jsonl', 'prior.json'):
        symlink(D / 'lab' / name, D / 'f92' / name)
    cfg = json.loads((D / 'lab/config.json').read_text())
    old = json.loads((D / 'inputs/current/model.json').read_text())
    cfg.update(features=old['features'], initial_lam=old['lam'], link_of='replays/draftlab/' + LAB)
    write(D / 'f92/config.json', cfg)
    command([sys.executable, T / 'fit.py', D / 'f92'], 'fit.log')
    m = json.loads((D / 'f92/model.json').read_text())
    assert m['games'] == json.loads((D / 'lab/model.json').read_text())['games']
    assert len(m['features']) == 92
    assert all(math.isfinite(x) for p in m['picks'].values() for x in p['theta'])


def preferences():
    command([sys.executable, T / 'oof.py', D / 'f92', D / 'inputs/current/model.json', D / 'oof'], 'oof.log')
    pooled(1, [sys.executable, T / 'prepare_preferences.py'], 'preferences.log')


def candidates():
    (D / 'candidate-sources').mkdir(exist_ok=True)
    arms = {'bots': {}, 'aliases': {}, 'headers': {}}
    calibration = json.loads((D / 'preference-calibration.json').read_text())
    for arm, cand in CANDS.items():
        if arm != 'control' and calibration['arms'][arm]['lambda'] == 0:
            arms['aliases'][arm] = 'control'
            continue
        lab = D / 'f92' if arm == 'control' else D / 'models' / arm
        if (R / 'bots' / cand).exists():
            assert not (D / 'candidate-sources' / (arm + '.json')).exists(), 'Do not overwrite a sealed candidate'
        command(['./copybot', '-f', BASE, cand], 'candidate.log')
        header = R / 'bots' / cand / 'src/draft/draft_model.h'
        command(['node', 'tools/draftlab/model.mjs', 'cpp', '--lab', lab, '--out', header], 'candidate.log')
        b, c = source(BASE), source(cand)
        assert b.keys() == c.keys()
        assert [p for p in b if b[p] != c[p]] in ([], ['draft/draft_model.h'])
        same = next((name for name, h in arms['headers'].items() if h == sha(header)), None)
        if same:
            arms['aliases'][arm] = same
            continue
        arms['bots'][arm] = cand
        arms['headers'][arm] = sha(header)
        pooled(1, ['node', 'tools/draftlab/native.mjs', '--lab', lab, 'maps', D / 'selected/selection',
                   '--src', R / 'bots' / cand / 'src/draft'], 'parity-' + arm + '.log')
        text = (D / ('parity-' + arm + '.log')).read_text()
        lines = [line for line in text.splitlines() if 'team mismatches' in line]
        assert lines and '0 key mismatches' in lines[-1] and '0 team mismatches, 0 C++ failures' in lines[-1], 'Native draft parity failed'
        pooled(1, ['cambc', 'build', '--release', R / 'bots' / cand], 'candidate.log')
        write(D / 'candidate-sources' / (arm + '.json'), c)
    for label, bot in [('base', BASE), *arms['bots'].items()]:
        name = 'draft17-506-' + label
        command([sys.executable, T / 'reserve.py', '8', sys.executable, 'tools/draftlab/firstturn.py',
                 '--sample', D / 'lab/maps.jsonl', '--need', '--bot', 'bots/' + bot, '--jobs', '{n}',
                 '--name', name], 'firstturn-' + label + '.log')
        result = R / 'replays/draftlab/firstturn' / name / 'ft.jsonl'
        rows = [json.loads(line) for line in result.read_text().splitlines() if line]
        assert rows and all(r.get('ft') and r['ft'][2] <= 10000000 and r['ft'][3] == 1 and
                            r['ft'][4] == 1 and (len(r['ft']) < 6 or r['ft'][5] == 0) for r in rows), name
        write(D / ('firstturn-' + label + '.json'), {'source': bot, 'rows_sha256': sha(result),
              'team_drafts': len(rows), 'max_fuel': max(r['ft'][2] for r in rows)})
    write(D / 'arms.json', arms)


def evaluate(stage):
    command([sys.executable, T / 'fixed_eval.py', stage], stage + '.log')


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--check', action='store_true')
    ap.add_argument('--normal-admission', type=Path)
    args = ap.parse_args()
    verify()
    if args.check:
        print(json.dumps({'base': BASE, 'candidate': CAND, 'manifest_sha256': sha(D / 'manifest.json'),
                          'protocol': json.loads((D / 'protocol.json').read_text()), 'start_base_check': preflight()}))
        return
    assert os.environ.get('LOCALQ_JOB'), 'Heavy work must be admitted through localq'
    assert os.environ.get('FASTRUNNER_MODE') == 'native'
    assert os.environ.get('CAMBC_SLOTS') == '86' and not os.environ.get('CAMBC_SLOT_DIR')
    os.environ['CAMBC_SLOT_GROUP'] = 'lq-draft17'
    os.environ['CAMBC_SLOT_WEIGHT'] = '1'
    os.environ['NODE_OPTIONS'] = '--max-old-space-size=98304'
    os.environ['OMP_NUM_THREADS'] = os.environ['OPENBLAS_NUM_THREADS'] = '1'
    os.environ['CMAKE_BUILD_PARALLEL_LEVEL'] = os.environ['RAYON_NUM_THREADS'] = '1'
    os.chdir(R)
    with (D / 'run.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        if args.normal_admission:
            a = json.loads(args.normal_admission.read_text())
            assert a['authorized_by'] == 'coordinator' and a['decision'] == 'run normal fuel after reviewed 200k gain'
            assert a['confirmation200k_sha256'] == sha(D / 'confirmation.json')
            result = json.loads((D / 'confirmation.json').read_text())
            assert result['positive_gain'] and a['selected'] == result['selected']
            assert a['candidate_source_sha256'] == sha(D / 'candidate-sources' / (result['selected'] + '.json'))
            assert a['manifest_sha256'] == sha(D / 'manifest.json')
            step('normal', lambda: evaluate('normal'))
            return
        first_start()
        for name, fn in [('maps', prepare_maps), ('init', initialise), ('train', train), ('fit', fit),
                         ('preferences', preferences), ('candidates', candidates),
                         ('selection', lambda: evaluate('selection')), ('confirmation', lambda: evaluate('confirmation'))]:
            step(name, fn)
        verify()


if __name__ == '__main__':
    main()
