"""One owner-bound native-cache prewarmer; never contributes scored evidence."""
import argparse
import fcntl
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time

D=Path(__file__).resolve().parent
R=Path('/home/ubuntu/cambc-autumn')
P=Path('/home/ubuntu/tmp-offload/compile-ahead-ward16')
STOP=False


def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):return json.loads(Path(p).read_text())
def write(p,x):
    tmp=Path(str(p)+'.tmp');tmp.write_text(json.dumps(x,indent=2)+'\n');tmp.replace(p)
def verify():
    m=read(D/'manifest.json')
    for p,h in m['files'].items():assert sha(p)==h,('drift',p)
    ahead.verify()
    return m

def active():return not STOP and not (D/'stop').exists() and ahead.same_owner(ahead.PLAN['owner'])

def prepare(marker):
    verify();r=read(marker);frozen=Path(r['frozen']);k,body=r['task']
    if not active():return False
    held=cpu_slots.acquire(16,least=1)
    try:
        if len(held)!=16 or not active():return False
        begin=time.time()
        with cpu_slots.exclusive(frozen.parent/'build.lock'):
            if not active():return False
            actual={str(p.relative_to(frozen/'src')):sha(p) for p in (frozen/'src').rglob('*') if p.is_file()}
            assert actual==r['source'],'Frozen source differs from prepared body'
            wasm=frozen/'.cambc/build-release/bot-injected.wasm';wasm_sha=sha(wasm)
            with tempfile.TemporaryDirectory(prefix='ward-native-warm-') as td:
                td=Path(td);manifest=td/'manifest.txt'
                manifest.write_text(f'{frozen} {frozen} {R/"maps/00ambush.map26a"} {td/"warm.repl26a"}\n')
                argv=[str(ahead.CLI),'run-batch',str(manifest),'--jobs','1','--rounds','1','--log-limit','0','--release']
                env=cambc_env.env(serial=True)
                env.update(RAYON_NUM_THREADS='1',OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',FASTRUNNER_STATS='1')
                with (D/'logs'/f'{k}-{body}.log').open('w') as log:
                    done=subprocess.run(argv,cwd=R,env=env,stdout=log,stderr=subprocess.STDOUT)
            assert done.returncode==0,('warm failed',k,body,done.returncode)
            assert sha(wasm)==wasm_sha,'WASM changed during warm'
        write(D/'ready'/f'{k}-{body}.json',{'noise':k,'body':body,'begin':begin,'end':time.time(),'slots':len(held),'frozen':str(frozen),'wasm_sha256':wasm_sha,'source_marker':str(marker),'source_marker_sha256':sha(marker),'unscored_one_round_warm':True,'existing_internal_native_pgo':True,'argv':argv,'owner_alive_at_end':active()})
        return True
    finally:cpu_slots.release(held)


def main():
    global ahead,cpu_slots,cambc_env
    ap=argparse.ArgumentParser();ap.add_argument('--check',action='store_true');args=ap.parse_args()
    spec=importlib.util.spec_from_file_location('frozen_compile_ahead',P/'ahead.py');ahead=importlib.util.module_from_spec(spec);spec.loader.exec_module(ahead);ahead.initialize(P/'plan.json')
    os.environ['CAMBC_SLOT_GROUP']='ward-native-prewarm';os.environ['CAMBC_SLOT_WEIGHT']='1'
    sys.path.insert(0,str(R/'tools'));import cpu_slots;import cambc_env
    verify()
    assert os.environ.get('CAMBC_SLOTS')=='86' and not os.environ.get('CAMBC_SLOT_DIR') and os.environ.get('FASTRUNNER_MODE')=='native'
    # Cache/code-generation settings must match the already-running gate.
    raw=Path(f'/proc/{ahead.PLAN["owner"]["pid"]}/environ').read_bytes().split(b'\0')
    owner_env=dict(x.decode().split('=',1) for x in raw if b'=' in x)
    for key in ('FASTRUNNER_MODE','FASTRUNNER_PGO','FASTRUNNER_CFLAGS','FASTRUNNER_UNITS','FASTRUNNER_LIB','FASTRUNNER_TRACE_FUEL','XDG_CACHE_HOME'):
        assert os.environ.get(key)==owner_env.get(key),('engine/cache environment differs',key)
    if args.check:print(json.dumps({'owner_alive':active(),'manifest_sha256':sha(D/'manifest.json'),'slots_required':16,'serialized':True}));return
    def stopping(*_):
        global STOP
        STOP=True
    signal.signal(signal.SIGINT,stopping);signal.signal(signal.SIGTERM,stopping)
    for p in ('logs','ready'): (D/p).mkdir(exist_ok=True)
    with (D/'run.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        write(D/'started.json',{'pid':os.getpid(),'at':time.time(),'owner':ahead.PLAN['owner'],'manifest_sha256':sha(D/'manifest.json')})
        error=None
        try:
            while active():
                verify();completed=max([0,*(int(p.stem) for p in Path(ahead.PLAN['blocks']).glob('*.json'))]);prepared=False
                for k,body in ahead.window(completed,1,1000):
                    if not active():break
                    marker=P/'ready'/f'{k}-{body}.json'
                    if marker.exists() and not (D/'ready'/marker.name).exists():
                        prepared=prepare(marker);break  # Recompute current demand after each bounded warm.
                time.sleep(.1 if prepared else 1)
        except Exception as exc:
            error=repr(exc);raise
        finally:write(D/'exit.json',{'at':time.time(),'owner_alive':ahead.same_owner(ahead.PLAN['owner']),'error':error})

if __name__=='__main__':main()
