"""Owner-bound compile-only cache preparation for an already-running sealed gate."""
import argparse
from concurrent.futures import ProcessPoolExecutor
from contextlib import contextmanager
import fcntl
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

R = Path('/home/ubuntu/cambc-autumn')
PLAN = None
D = None
CLI = R / 'tools/fastengine/runner/fastrunner'
DEFAULT_WORKERS = 16
DEFAULT_LOOKAHEAD = 8
STOP_REQUESTED = False


def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p): return json.loads(Path(p).read_text())
def write(p, x):
    temp = Path(str(p) + '.tmp'); temp.write_text(json.dumps(x, indent=2) + '\n'); temp.replace(p)


def identity(pid):
    try:
        root = Path('/proc') / str(pid); a = (root / 'stat').read_text().split(') ', 1)[1].split()
        return {'pid': pid, 'start': a[19], 'cmdline': (root / 'cmdline').read_text().replace('\0', ' '), 'state': a[0], 'ppid':int(a[1])}
    except (OSError, IndexError): return None


def same_owner(owner):
    actual = identity(owner['pid'])
    return bool(actual and actual['state'] != 'Z' and all(actual[k] == owner[k] for k in ('pid', 'start', 'cmdline')))


def interrupt_owned_tree(owner):
    """On explicit wrapper interruption, signal only the captured scored tree and drain it."""
    tracked={owner['pid']:owner};signaled=set()
    while True:
        try:
            table={int(p.name):x for p in Path('/proc').iterdir() if p.name.isdigit() and (x:=identity(int(p.name)))}
            live={pid:x for pid,x in tracked.items() if pid in table and table[pid]['start']==x['start'] and table[pid]['state']!='Z'}
            while True:
                children={pid:x for pid,x in table.items() if x['ppid'] in live and pid not in tracked and x['state']!='Z'}
                if not children:break
                tracked.update(children);live.update(children)
            if not live:return tracked
            for pid,x in live.items():
                key=(pid,x['start'])
                if key in signaled:continue
                actual=identity(pid)
                if actual and actual['start']==x['start'] and actual['state']!='Z':
                    try:os.kill(pid,signal.SIGINT)
                    except ProcessLookupError:pass
                signaled.add(key)
            time.sleep(.1)
        except KeyboardInterrupt:
            continue  # Finish the already-requested cleanup before returning the interruption.


def wait_drained(process):
    while True:
        try:return process.wait()
        except KeyboardInterrupt:continue


def interrupt_scored_children(owner, helper_pid=None):
    """The in-process gate's direct children own scored work; its helper is a sibling."""
    if not same_owner(owner):return {}
    roots=[]
    for entry in Path('/proc').iterdir():
        if not entry.name.isdigit():continue
        actual=identity(int(entry.name))
        if actual and actual['ppid']==owner['pid'] and actual['pid']!=helper_pid and actual['state']!='Z':
            roots.append(actual)
    return {root['pid']:interrupt_owned_tree(root) for root in roots}


def window(completed, first, last):
    current = max(first, completed + 1)
    return [(k, body) for k in range(current, min(last, current + PLAN.get('lookahead', DEFAULT_LOOKAHEAD)) + 1) for body in PLAN['bodies']]


def verify():
    assert sha(PLAN['manifest']) == PLAN['manifest_sha256'], 'Owner manifest drift'
    m = read(PLAN['manifest'])
    for p, h in m['files'].items(): assert sha(p) == h, ('Input drift', p)
    for bot, files in m['sources'].items():
        root = R / 'bots' / bot / 'src'
        actual = {str(p.relative_to(root)): sha(p) for p in root.rglob('*') if p.is_file()}
        assert actual == files, ('Owner/template source drift', bot)
    return m


def active():
    return not STOP_REQUESTED and not Path(PLAN['stop_file']).exists() and same_owner(PLAN['owner'])


def initialize(plan_path):
    global PLAN, D
    PLAN = read(plan_path); D = Path(PLAN['directory'])
    assert 1 <= PLAN['first'] <= PLAN['last'] and 1 <= PLAN['workers'] <= 32
    assert 0 <= PLAN.get('lookahead', DEFAULT_LOOKAHEAD) <= 32
    assert len(PLAN['bodies']) == 2 and len(set(PLAN['bodies'])) == 2
    assert Path(PLAN['gate_source']).is_file()
    os.environ.update(CAMBC_SLOT_GROUP=PLAN['group'], CAMBC_SLOT_WEIGHT='1', OMP_NUM_THREADS='1',
                      OPENBLAS_NUM_THREADS='1', MKL_NUM_THREADS='1', NUMEXPR_NUM_THREADS='1', RAYON_NUM_THREADS='1')
    verify()


def prepare(task):
    k, body = task
    verify()
    if not active(): return {'task': task, 'skipped': 'owner ended before reservation'}
    sys.path.insert(0, str(R / 'tools'))
    import cpu_slots
    import run_batched
    import cambc_env
    held = cpu_slots.acquire(1)
    try:
        if not active(): return {'task': task, 'skipped': 'owner ended while waiting'}
        begin = time.time()
        spec = importlib.util.spec_from_file_location('ahead_fgate', PLAN['gate_source'])
        fg = importlib.util.module_from_spec(spec); spec.loader.exec_module(fg)
        fg.BODY = dict(zip('FM', PLAN['bodies']))
        fg.build_version(k)  # Existing per-seed/body locks serialize source construction with the gate.
        bot = R / 'bots/variants' / f'spar-dvn{k}-{body}'
        before = {str(p.relative_to(bot / 'src')): sha(p) for p in (bot / 'src').rglob('*') if p.is_file()}
        frozen = run_batched.freeze(bot)
        generated = time.time()
        log = D / 'logs' / f'{k}-{body}.log'; log.parent.mkdir(exist_ok=True)
        with cpu_slots.exclusive(frozen.parent / 'build.lock'):
            locked = time.time()
            if not active(): return {'task': task, 'skipped': 'owner ended before compile'}
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
                  'owner_alive_at_end': active(), 'log_sha256': sha(log)}
        write(D / 'ready' / f'{k}-{body}.json', result)
        return result
    finally:
        cpu_slots.release(held)


@contextmanager
def scope(directory, manifest, blocks, gate_source, bodies, first=1, last=1000,
          owner_pid=None, workers=DEFAULT_WORKERS, lookahead=DEFAULT_LOOKAHEAD, enabled=True):
    """Resource-only lifetime for an in-process gate phase or an explicitly supplied child."""
    directory=Path(directory); stop=directory/'stop'; helper=None; stream=None
    status={'helper_started':False,'workers':workers,'lookahead':lookahead}
    try:
        try:
            directory.mkdir(parents=True,exist_ok=True)
            assert not stop.exists(),'Stopped helper phase requires explicit recovery review'
            if enabled and os.environ.get('CAMBC_COMPILE_AHEAD','1')!='0':
                owner=identity(owner_pid or os.getpid())
                if owner and owner['state']!='Z':
                    plan={'owner':owner,'directory':str(directory),'stop_file':str(stop),'manifest':str(manifest),
                          'manifest_sha256':sha(manifest),'blocks':str(blocks),'gate_source':str(gate_source),
                          'first':first,'last':last,'bodies':list(bodies),'workers':workers,'lookahead':lookahead,
                          'group':'compile-ahead-'+str(owner['pid'])}
                    write(directory/'plan.json',plan);stream=(directory/'helper.log').open('a')
                    helper=subprocess.Popen([sys.executable,str(Path(__file__).resolve()),'--plan',str(directory/'plan.json')],cwd=R,stdout=stream,stderr=subprocess.STDOUT)
                    status.update(helper_started=True,helper_pid=helper.pid,owner=owner)
        except Exception as exc:
            status['helper_setup_error']=repr(exc)
        try:
            yield status
        except KeyboardInterrupt:
            status['interrupted']=True
            owner=identity(owner_pid or os.getpid())
            if owner is not None:
                if owner_pid and owner_pid!=os.getpid():
                    status['interrupted_tree']=interrupt_owned_tree(owner)
                else:
                    status['interrupted_tree']=interrupt_scored_children(owner,helper.pid if helper else None)
            raise
    finally:
        try:
            stop.write_text('gate phase ended; stop dispatch and drain compiles\n')
        except OSError as exc:
            status['stop_marker_error']=repr(exc)
            if helper is not None and helper.poll() is None:helper.send_signal(signal.SIGINT)
        finally:
            if helper is not None:status['helper_exit']=wait_drained(helper)
            if stream is not None:stream.close()
        try:write(directory/'lifecycle.json',status)
        except OSError as exc:print('compile-ahead lifecycle record failed:',exc,file=sys.stderr)


def snapshot_manifest(path, bots, gate_source):
    """Seal current inputs for the standard future-gate entry point before any games."""
    paths={Path(gate_source),Path(__file__).resolve(),R/'tools/fgate.py',R/'tools/run_batched.py',R/'tools/ab.py',R/'tools/cpu_slots.py',
           R/'tools/cambc_env.py',R/'copybot',CLI}
    for directory in ('sdk/cpp','research/notes/ideas-2026-11-08/diverse-tools','research/notes/ideas-2026-11-08/spar-tools',
                      'research/notes/ideas-2026-11-09/freshgate-tools','research/notes/ideas-2026-11-09/oppfidelity-tools',
                      'research/notes/ideas-2026-11-09/fishfid','research/notes/ideas-2026-11-10/opporder'):
        paths.update(p for p in (R/directory).iterdir() if p.is_file() and p.suffix in ('.py','.sh','.h','.json'))
    sources={}
    for bot in (*bots,'variants/oc-tune3'):
        root=(R/'bots'/bot/'src').resolve()
        assert root.is_dir(),root
        sources[bot]={str(p.relative_to(root)):sha(p) for p in root.rglob('*') if p.is_file()}
    write(path,{'files':{str(p):sha(p) for p in sorted(paths)},'sources':sources})


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--plan', required=True); ap.add_argument('--check', action='store_true'); args = ap.parse_args()
    initialize(args.plan)
    def stop_dispatch(*_):
        global STOP_REQUESTED
        STOP_REQUESTED=True
    signal.signal(signal.SIGINT,stop_dispatch);signal.signal(signal.SIGTERM,stop_dispatch)
    first, last = PLAN['first'], PLAN['last']; blocks = Path(PLAN['blocks'])
    completed = lambda: max([first-1, *(int(p.stem) for p in blocks.glob('*.json'))])
    if args.check:
        print(json.dumps({'owner_alive': active(), 'window': window(completed(), first, last)})); return
    assert os.environ.get('CAMBC_SLOTS') == '86' and not os.environ.get('CAMBC_SLOT_DIR')
    assert os.environ.get('FASTRUNNER_MODE') == 'native'
    os.chdir(R); (D / 'ready').mkdir(parents=True, exist_ok=True)
    with (D / 'run.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        write(D / 'started.json', {'pid': os.getpid(), 'at': time.time(), 'plan_sha256': sha(args.plan)})
        pending = {}; finished = set(); failed = None
        with ProcessPoolExecutor(max_workers=PLAN['workers'], initializer=initialize, initargs=(args.plan,)) as pool:
            while active() and failed is None:
                verify()
                for task, future in list(pending.items()):
                    if not future.done(): continue
                    try:
                        result = future.result(); print(json.dumps(result), flush=True); finished.add(task)
                    except Exception as exc:
                        failed = repr(exc); print(f'PREPARE FAILED {task}: {failed}', flush=True)
                    del pending[task]
                if failed: break
                for task in window(completed(), first, last):
                    if len(pending) >= PLAN['workers']: break
                    if task in finished or task in pending: continue
                    marker = D / 'ready' / f'{task[0]}-{task[1]}.json'
                    if marker.exists(): finished.add(task); continue
                    pending[task] = pool.submit(prepare, task)
                time.sleep(2)
            # No submissions after owner exit/stop/error. Already-started locked compiles drain.
        write(D / 'exit.json', {'at': time.time(), 'owner_alive': same_owner(PLAN['owner']), 'error': failed,
                                'completed_tasks': sorted(finished), 'pending_at_dispatch_stop': list(pending)})


if __name__ == '__main__': main()
