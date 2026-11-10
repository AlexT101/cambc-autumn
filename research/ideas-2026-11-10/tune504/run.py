"""One reviewed, exclusive tune8 job: fixed506 training and sole200k candidate evaluation."""
import argparse
import fcntl
import hashlib
import importlib.util
import io
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import tarfile
import time

R = Path('/home/ubuntu/cambc-autumn')
D = Path('/home/ubuntu/tmp-offload/localq/rounds/tune8')
T = Path(__file__).resolve().parent
BASE = 'variants/oc-dfuel-506'
VEHICLE = 'variants/oc506-tune8-vehicle'
CAND = 'variants/oc506-tune8-export'
APPLIED = 'variants/oc506-tune8-applied'
RUN = 'oc506-tune8'


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
        assert sha(p) == h, f'Sealed input/tool drift: {p}'
    for bot, files in m['sources'].items():
        assert source(bot) == files, f'Sealed source drift: {bot}'
    for p, h in m['validation_maps'].items():
        assert sha(p) == h, p
    if (D / 'maps.json').exists():
        for row in json.loads((D / 'maps.json').read_text())['selected']:
            assert sha(row['path']) == row['sha256'], row['path']
    if (D / 'opponents.json').exists():
        for bot, files in json.loads((D / 'opponents.json').read_text()).items():
            assert source(bot) == files, bot
    return m


def start_base_check(policy, committed, sealed):
    digest = hashlib.sha256(json.dumps(sorted(sealed.items()), separators=(',', ':')).encode()).hexdigest()
    return policy.get('base') == BASE and policy.get('base_source_sha256') == digest and committed == sealed


def preflight():
    policy = json.loads(Path('/home/ubuntu/tmp-offload/localq/base-policy.json').read_text())
    head = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=R, text=True).strip()
    raw = subprocess.check_output(['git', 'archive', head, 'bots/ocean/src'], cwd=R)
    with tarfile.open(fileobj=io.BytesIO(raw)) as archive:
        committed = {x.name.removeprefix('bots/ocean/src/'): hashlib.sha256(archive.extractfile(x).read()).hexdigest()
                     for x in archive.getmembers() if x.isfile()}
    sealed = json.loads((D / 'manifest.json').read_text())['sources'][BASE]
    token = Path('/home/ubuntu/tmp-offload/localq/state/draft17-reviewdone/done').exists()
    return {'ready': token and start_base_check(policy, committed, sealed), 'review_token': token, 'head': head,
            'policy_base': policy.get('base'), 'committed_main_matches': committed == sealed}


def first_start():
    marker = D / 'first-heavy-start.json'
    if marker.exists():
        return  # Preserve an already started frozen job if main later advances.
    evidence = preflight()
    actual_engine = subprocess.check_output(['cambc','--version'],cwd=R,text=True).strip()
    assert actual_engine == json.loads((D/'manifest.json').read_text())['engine'], 'Engine drift before training'
    if not evidence['ready']:
        write(D / 'review-required.json', {'stage': 'HOLD before heavy work', 'evidence': evidence,
              'decision': 'Explicit coordinator review/reseal required; no automatic rebase.'})
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


def step(name, fn):
    done = D / (name + '.done')
    if done.exists():
        return
    verify()
    with (D / 'events.jsonl').open('a') as f:
        f.write(json.dumps({'phase': name, 'event': 'start', 'time': time.time()}) + '\n')
    fn()
    verify()
    done.write_text(time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()) + '\n')
    with (D / 'events.jsonl').open('a') as f:
        f.write(json.dumps({'phase': name, 'event': 'complete', 'time': time.time()}) + '\n')


def prepare_maps():
    manifest = verify()
    old = set(manifest['validation_maps'].values())
    generated, selected, seen = [], [], set(old)
    def generate(seed):
        directory = D / 'maps' / f'fresh-{seed}'
        assert not directory.exists(), 'Partial map preparation requires review'
        pooled(1, ['node', 'tools/mapgen/mapgen.mjs', 'suite', '--jobs', '1', '--mix', 'ladder-v2', '--seed', str(seed), '--out', directory], 'maps.log')
        generated.append(seed)
        for p in sorted(directory.glob('*.map26a')):
            h = sha(p)
            if h in seen or len(selected) == 10240:
                continue
            seen.add(h)
            link = D / 'selected' / p.name
            link.parent.mkdir(exist_ok=True)
            assert not link.exists()
            link.symlink_to(p)
            selected.append({'path': str(link), 'sha256': h})
    for seed in range(2413000, 2413040):
        generate(seed)
    for seed in range(2413040, 2413044):
        if len(selected) == 10240:
            break
        generate(seed)
    assert len(selected) == 10240, 'Not enough unique training maps; no automatic broader generation'
    write(D / 'maps.json', {'selected': selected, 'generated_seeds': generated,
          'scope': 'Exact content deduplication within training and against1024standard gate maps+128ladder maps. Reserved seed provenance; no universal archive novelty claim.'})


def opponents():
    # Only source generation here; compilation happens under pooled init.
    code = "import sys;sys.path.insert(0,'research/ideas-2026-11-09/freshgate-tools');import fgate\nfor k in (1001,1002,1003):\n fgate.build_seed(k)\n for b in ('Flp4','Mt3q'):fgate.build_body(k,b)\n"
    pooled(1, [sys.executable, '-c', code], 'opponents.log')
    write(D / 'opponents.json', {f'variants/spar-dvn{k}-{b}': source(f'variants/spar-dvn{k}-{b}')
                                for k in (1001,1002,1003) for b in ('Flp4','Mt3q')})


def train():
    command([sys.executable, T / 'training.py', 'train'], 'train.log')
    run = R / 'replays/tune' / RUN
    h = [json.loads(x) for x in (run / 'history.jsonl').read_text().splitlines()]
    g = [json.loads(x) for x in (run / 'games.jsonl').read_text().splitlines()]
    assert [x['k'] for x in h] == [x['k'] for x in g] == list(range(1,601))
    assert all(x['games'] == 1152 for x in h)
    for x in g:
        assert len(x['games']) == 144 and len(x['scores']) == 8
        assert all(len(scores) == 144 and all(s is not None and math.isfinite(s) for s in scores) for scores in x['scores'].values())
    cfg = json.loads((D / 'config.json').read_text())
    values = {n: lo + (hi - lo) * sum(row['x'][n] for row in h[300:600]) / 300 for n,(lo,hi,_) in cfg['params'].items()}
    write(D / 'endpoint.json', values)
    write(D / 'training-quality.json', {'iterations':600,'scored_games':691200,'endpoint_iterates':[301,600],
          'history_sha256':sha(run/'history.jsonl'),'games_sha256':sha(run/'games.jsonl'),
          'early_loss_and_cap_messages':[s for s in (run/'tune.log').read_text().splitlines() if '!!!' in s or 'capped' in s],
          'note':'Early draft losses retained; any missing score/run error stopped before gradient update.'})


def candidate():
    command([sys.executable, 'tools/tune/tune.py', 'apply', '--run', RUN, '--values', D / 'endpoint.json', '--out', 'bots/' + APPLIED], 'export.log')
    command([sys.executable, T / 'vehicle.py', R / 'bots' / CAND, '--values', D / 'endpoint.json'], 'export.log')
    c, b = source(CAND), source(BASE)
    allowed = {p['file'] for p in json.loads((T / 'parameters.json').read_text())['parameters']}
    assert c.keys() == b.keys() and all(c[p] == b[p] for p in b if p not in allowed)
    assert not (R / 'bots' / CAND / 'src/tune.h').exists()
    write(D / 'candidate-source.json', c)
    write(D / 'applied-source.json', source(APPLIED))
    command([sys.executable, T / 'identity.py', 'export', APPLIED, CAND], 'identity-export.log')


def gate():
    assert source(CAND) == json.loads((D / 'candidate-source.json').read_text())
    spec = importlib.util.spec_from_file_location('tune8_fgate', R / 'research/ideas-2026-11-09/freshgate-tools/fgate.py')
    fg = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(fg)
    fg.LOGS = str(D / 'gate-results')
    Path(fg.LOGS).mkdir(exist_ok=True)
    argv = [str(R / 'research/ideas-2026-11-09/freshgate-tools/fgate.py'), CAND, BASE,
            '--fuel','200000','--fish-body','Flp4','--mite-body','Mt3q','--ci','0','--zone-stop',
            '--max-seeds','1000','--jobs','4','--ahead','0','--seed','24138']
    write(D / 'gate-started.json', {'argv':argv,'pid':os.getpid(),'candidate_source_sha256':sha(D/'candidate-source.json')})
    from audit import validate_block
    original = fg.block_units
    audits = D / 'gate-blocks'
    audits.mkdir(exist_ok=True)
    def audited(cand, ref, k, rng):
        write(audits / f'{k:04d}.json', validate_block(fg,cand,ref,k,200000))
        return original(cand,ref,k,rng)
    fg.block_units = audited
    sys.argv = argv
    sys.path.insert(0,str(R/'tools'))
    from gate_compile_ahead import scope
    with scope(D / 'compile-ahead-gate',D/'manifest.json',audits,Path(fg.__file__),['Flp4','Mt3q']):
        fg.main()
    result = json.loads((Path(fg.LOGS) / f'fgate-{Path(CAND).name}--{Path(BASE).name}p4q-fuel200000.json').read_text())
    assert result['blocks'] == len(list(audits.glob('*.json')))
    result.update(note='Coordinator review only. ZONE is not rejection or proof of a positive95%interval; cap unresolved. No automatic100k test, merge, live submission, or next tune.',
                  manifest_sha256=sha(D/'manifest.json'),candidate_source_sha256=sha(D/'candidate-source.json'))
    write(D/'gate-200000.json',result)
    write(D/'review-required.json',{'stage':'200k gate complete','result':str(D/'gate-200000.json'),'decision':'No automatic follow-on.'})


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--check', action='store_true')
    args = ap.parse_args()
    verify()
    if args.check:
        print(json.dumps({'manifest_sha256':sha(D/'manifest.json'),'preflight':preflight(),'job':'tune8'}))
        return
    assert os.environ.get('LOCALQ_JOB') == 'tune8', 'Heavy work requires scheduler admission'
    assert os.environ.get('FASTRUNNER_MODE') == 'native'
    assert os.environ.get('CAMBC_SLOTS') == '86' and not os.environ.get('CAMBC_SLOT_DIR')
    os.environ['CAMBC_SLOT_GROUP'] = 'lq-tune8'
    os.environ['CAMBC_SLOT_WEIGHT'] = '1'
    os.environ['OMP_NUM_THREADS'] = os.environ['OPENBLAS_NUM_THREADS'] = '1'
    os.chdir(R)
    with (D / 'run.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX | fcntl.LOCK_NB)
        first_start()
        phases = [('maps',prepare_maps),('opponents',opponents),
                  ('default-identity',lambda:command([sys.executable,T/'identity.py','defaults',BASE,VEHICLE],'identity-defaults.log')),
                  ('init',lambda:command([sys.executable,T/'training.py','init'],'init.log')),
                  ('train',train),('candidate',candidate),('gate-200000',gate)]
        for name,fn in phases:
            step(name,fn)
        verify()


if __name__ == '__main__':
    main()
