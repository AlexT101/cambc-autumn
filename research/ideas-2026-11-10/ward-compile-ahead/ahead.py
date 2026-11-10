"""Prepare only an existing ward gate's current/next two noise bodies, never scored games."""
import argparse
from concurrent.futures import ProcessPoolExecutor
import fcntl
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time

R = Path('/home/ubuntu/cambc-autumn')
D = Path(__file__).resolve().parent
BLOCKS = Path('/home/ubuntu/tmp-offload/ward504-full/camp-blocks')
FG = R / 'research/ideas-2026-11-09/freshgate-tools/fgate.py'
CLI = R / 'tools/fastengine/runner/fastrunner'


def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p): return json.loads(Path(p).read_text())
def write(p, x):
    temp = Path(str(p) + '.tmp'); temp.write_text(json.dumps(x, indent=2) + '\n'); temp.replace(p)


def identity(pid):
    try:
        root = Path('/proc') / str(pid); a = (root / 'stat').read_text().split(') ', 1)[1].split()
        return {'pid': pid, 'start': a[19], 'cmdline': (root / 'cmdline').read_text().replace('\0', ' '), 'state': a[0]}
    except (OSError, IndexError): return None


def same_owner(owner):
    actual = identity(owner['pid'])
    return bool(actual and actual['state'] != 'Z' and all(actual[k] == owner[k] for k in ('pid', 'start', 'cmdline')))


def window(completed):
    return [(k, body) for k in range(completed + 1, min(1000, completed + 3) + 1) for body in ('Flp4', 'Mt3q')]


def verify():
    m = read(D / 'manifest.json')
    for p, h in m['files'].items(): assert sha(p) == h, ('Input drift', p)
    for root, files in m['sources'].items():
        actual = {str(p.relative_to(root)): sha(p) for p in Path(root).rglob('*') if p.is_file()}
        assert actual == files, ('Generator source drift', root)
    return m


def prepare(task):
    k, body = task
    m = verify()
    if not same_owner(m['owner']): return {'task': task, 'skipped': 'owner ended before reservation'}
    sys.path.insert(0, str(R / 'tools'))
    import cpu_slots
    import run_batched
    import cambc_env
    held = cpu_slots.acquire(1)
    try:
        if not same_owner(m['owner']): return {'task': task, 'skipped': 'owner ended while waiting'}
        begin = time.time()
        spec = importlib.util.spec_from_file_location('ahead_fgate', FG)
        fg = importlib.util.module_from_spec(spec); spec.loader.exec_module(fg)
        fg.BODY = {'F': 'Flp4', 'M': 'Mt3q'}
        fg.build_version(k)  # Existing per-seed/body locks serialize source construction with the gate.
        bot = R / 'bots/variants' / f'spar-dvn{k}-{body}'
        before = {str(p.relative_to(bot / 'src')): sha(p) for p in (bot / 'src').rglob('*') if p.is_file()}
        frozen = run_batched.freeze(bot)
        generated = time.time()
        log = D / 'logs' / f'{k}-{body}.log'; log.parent.mkdir(exist_ok=True)
        with cpu_slots.exclusive(frozen.parent / 'build.lock'):
            locked = time.time()
            if not same_owner(m['owner']): return {'task': task, 'skipped': 'owner ended before compile'}
            env = cambc_env.env(serial=True)
            env.update(RAYON_NUM_THREADS='1', OMP_NUM_THREADS='1', OPENBLAS_NUM_THREADS='1', CMAKE_BUILD_PARALLEL_LEVEL='1')
            with log.open('w') as stream:
                subprocess.run([str(CLI), 'build', str(frozen), '--release'], cwd=R, env=env, stdout=stream, stderr=subprocess.STDOUT, check=True)
                built = time.time()
        after = {str(p.relative_to(bot / 'src')): sha(p) for p in (bot / 'src').rglob('*') if p.is_file()}
        assert before == after, 'Body source changed during compilation'
        result = {'task': task, 'frozen': str(frozen), 'source': before, 'begin': begin, 'end': time.time(),
                  'source_and_freeze_seconds': generated-begin, 'lock_wait_seconds': locked-generated,
                  'compile_seconds': built-locked, 'warmed': False,
                  'owner_alive_at_end': same_owner(m['owner']), 'log_sha256': sha(log)}
        write(D / 'ready' / f'{k}-{body}.json', result)
        return result
    finally:
        cpu_slots.release(held)


def main():
    ap = argparse.ArgumentParser(description=__doc__); ap.add_argument('--check', action='store_true'); args = ap.parse_args()
    m = verify()
    if args.check:
        print(json.dumps({'owner_alive': same_owner(m['owner']), 'manifest_sha256': sha(D / 'manifest.json'),
                          'window': window(max(int(p.stem) for p in BLOCKS.glob('*.json')))})); return
    assert os.environ.get('CAMBC_SLOTS') == '86' and not os.environ.get('CAMBC_SLOT_DIR')
    assert os.environ.get('FASTRUNNER_MODE') == 'native'
    os.environ.update(CAMBC_SLOT_GROUP='ward-compile-ahead', CAMBC_SLOT_WEIGHT='1', OMP_NUM_THREADS='1',
                      OPENBLAS_NUM_THREADS='1', MKL_NUM_THREADS='1', NUMEXPR_NUM_THREADS='1', RAYON_NUM_THREADS='1')
    os.chdir(R); (D / 'ready').mkdir(exist_ok=True)
    with (D / 'run.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        write(D / 'started.json', {'pid': os.getpid(), 'at': time.time(), 'manifest_sha256': sha(D / 'manifest.json')})
        pending = {}; finished = set(); failed = None
        with ProcessPoolExecutor(max_workers=4) as pool:
            while same_owner(m['owner']) and failed is None:
                verify()
                for task, future in list(pending.items()):
                    if not future.done(): continue
                    try:
                        result = future.result(); print(json.dumps(result), flush=True); finished.add(task)
                    except Exception as exc:
                        failed = repr(exc); print(f'PREPARE FAILED {task}: {failed}', flush=True)
                    del pending[task]
                if failed: break
                current = max(int(p.stem) for p in BLOCKS.glob('*.json'))
                for task in window(current):
                    if len(pending) >= 4: break
                    if task in finished or task in pending: continue
                    marker = D / 'ready' / f'{task[0]}-{task[1]}.json'
                    if marker.exists(): finished.add(task); continue
                    pending[task] = pool.submit(prepare, task)
                time.sleep(2)
            # Already-started locked compiles drain; no new work after owner exit or an error.
        write(D / 'exit.json', {'at': time.time(), 'owner_alive': same_owner(m['owner']), 'error': failed,
                                'completed_tasks': sorted(finished), 'pending_at_dispatch_stop': list(pending)})


if __name__ == '__main__': main()
