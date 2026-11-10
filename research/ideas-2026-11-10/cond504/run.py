"""Queue-owned sequential200k exploiter evaluations; builds and diagnostics start only inside the queue."""
import argparse
import fcntl
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tarfile
import time

R=Path('/home/ubuntu/cambc-autumn');D=Path('/home/ubuntu/tmp-offload/cond504');T=Path(__file__).resolve().parent
BASE='variants/oc-emb5-504';CAND={'chanM':'variants/oc504-chanM','bagfF':'variants/oc504-bagfF'}


def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def write(p,x):Path(p).write_text(json.dumps(x,indent=2)+'\n')
def source(bot):
    root=R/'bots'/bot/'src'
    return {str(p.relative_to(root)):sha(p) for p in sorted(root.rglob('*')) if p.is_file()}


def verify():
    m=json.loads((D/'manifest.json').read_text())
    for p,h in m['files'].items():assert sha(p)==h,('Input/tool drift',p)
    for bot,files in m['sources'].items():assert source(bot)==files,('Source drift',bot)
    for p,h in m['smoke_maps'].items():assert sha(p)==h,p
    if (D/'maps-seal.json').exists():
        for p,h in json.loads((D/'maps-seal.json').read_text()).items():assert sha(p)==h,p
    if (D/'maps.json').exists():
        for row in json.loads((D/'maps.json').read_text())['selected']:assert sha(row['path'])==row['sha256'],row['path']
    if (D/'mirror/maps-seal.json').exists():
        for path,h in json.loads((D/'mirror/maps-seal.json').read_text()).items():assert sha(path)==h,path
        for row in json.loads((D/'mirror/maps.json').read_text())['selected']:assert sha(row['path'])==row['sha256'],row['path']
    return m


def body_seal(k):
    directory=D/'bodies';directory.mkdir(exist_ok=True)
    path=directory/f'{k}.json'
    current={f'variants/spar-dvn{k}-{v}':source(f'variants/spar-dvn{k}-{v}') for v in ('Flp4','Mt3q')}
    assert all(current.values()), 'Missing opponent source'
    if path.exists():assert json.loads(path.read_text())==current, ('Cached opponent source drift',k)
    else:write(path,current)
    return current


def preflight(arm):
    policy=json.loads(Path('/home/ubuntu/tmp-offload/localq/base-policy.json').read_text())
    head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=R,text=True).strip()
    raw=subprocess.check_output(['git','archive',head,'bots/ocean/src'],cwd=R)
    with tarfile.open(fileobj=io.BytesIO(raw)) as archive:
        committed={x.name.removeprefix('bots/ocean/src/'):hashlib.sha256(archive.extractfile(x).read()).hexdigest() for x in archive.getmembers() if x.isfile()}
    sealed=json.loads((D/'manifest.json').read_text())['sources'][BASE]
    digest=hashlib.sha256(json.dumps(sorted(sealed.items()),separators=(',',':')).encode()).hexdigest()
    token=Path('/home/ubuntu/tmp-offload/localq/state/exploit504-chanM-reviewdone/done')
    reviewed=arm=='chanM' or (token.exists() and token.read_text().strip()=='0')
    engine=subprocess.check_output(['cambc','--version'],cwd=R,text=True).strip()
    return {'ready':policy.get('base')==BASE and policy.get('base_source_sha256')==digest and committed==sealed and reviewed and engine.endswith('5.0.1'),
            'head':head,'approved_base':policy.get('base'),'committed_main_matches':committed==sealed,'previous_review':reviewed,'engine':engine}


def command(argv,log):
    with Path(log).open('a') as out:
        out.write('\n'+json.dumps([str(a) for a in argv])+'\n');out.flush()
        subprocess.run([str(a) for a in argv],cwd=R,stdout=out,stderr=subprocess.STDOUT,check=True)


def pooled(argv,log):command([sys.executable,R/'tools/pooled.py','1','--',*argv],log)


def prepare_maps():
    if (D/'maps.done').exists():return
    assert not (D/'maps.json').exists(),'Incomplete preparation requires review'
    history=[R/'maps',Path('/home/ubuntu/tmp-offload/diverse/fresh/pool'),Path('/home/ubuntu/tmp-offload/condarms/fresh/pool'),Path('/home/ubuntu/tmp-offload/localq/maps/dl')]
    seen=set();coverage=[]
    for root in history:
        assert root.is_dir(), ('Missing declared novelty root',str(root))
        files=root.glob('*.map26a') if root==R/'maps' else root.rglob('*.map26a')
        files=list(files);assert files, ('Empty declared novelty root',str(root))
        hashes={sha(p) for p in files};seen.update(hashes)
        coverage.append({'path':str(root),'exists':True,'map_paths':len(files),'distinct_hashes':len(hashes)})
    historical=len(seen);selected=[];generated=[]
    for seed in range(2414000,2414008):
        if len(selected)==1024:break
        out=D/'generated'/f'fresh-{seed}'
        assert not out.exists(),'Partial map generation needs review'
        pooled(['node','tools/mapgen/mapgen.mjs','suite','--jobs','1','--mix','ladder-v2','--seed',str(seed),'--out',out],D/'maps.log')
        generated.append(seed)
        for p in sorted(out.glob('*.map26a')):
            h=sha(p)
            if h in seen or len(selected)==1024:continue
            seen.add(h);j=len(selected)%8;directory=D/'pool'/f'x{j}';directory.mkdir(parents=True,exist_ok=True)
            link=directory/p.name;assert not link.exists();link.symlink_to(p)
            selected.append({'path':str(link),'sha256':h})
    assert len(selected)==1024,'Insufficient unique maps within reserved prospective cap'
    write(D/'maps.json',{'selected':selected,'generated_seeds':generated,'historical_hashes':historical,'novelty_scope':coverage,
                        'note':'Exact byte novelty in stated scope; no universal archive claim. Later noise blocks revisit these same1024 maps.'})
    pooled(['node','tools/draftlab/features.mjs',*[D/'pool'/f'x{j}' for j in range(8)],'--out',D/'features.jsonl'],D/'maps.log')
    write(D/'maps-seal.json',{str(p):sha(p) for p in (D/'maps.json',D/'features.jsonl')})
    (D/'maps.done').write_text('complete\n')


def phase(arm,name,fn):
    p=D/arm;done=p/(name+'.done')
    if done.exists():return
    verify();fn();verify();done.write_text(time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime())+'\n')


def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('arm',choices=CAND);ap.add_argument('--check',action='store_true');a=ap.parse_args()
    verify()
    if a.check:
        print(json.dumps({'arm':a.arm,'manifest_sha256':sha(D/'manifest.json'),'preflight':preflight(a.arm)}));return
    assert os.environ.get('LOCALQ_JOB')=='exploit504-'+a.arm+'-200k','Queue admission required'
    assert os.environ.get('FASTRUNNER_MODE')=='native' and os.environ.get('CAMBC_SLOTS')=='86' and not os.environ.get('CAMBC_SLOT_DIR')
    os.environ['CAMBC_SLOT_GROUP']='exploit504-'+a.arm;os.environ['CAMBC_SLOT_WEIGHT']='1'
    os.environ['OMP_NUM_THREADS']=os.environ['OPENBLAS_NUM_THREADS']='1';os.environ['NODE_OPTIONS']='--max-old-space-size=98304'
    os.chdir(R);p=D/a.arm;p.mkdir(exist_ok=True)
    with (p/'run.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        if not (p/'first-heavy-start.json').exists():
            check=preflight(a.arm)
            if not check['ready']:
                write(p/'review-required.json',{'stage':'HOLD before heavy work','evidence':check});raise SystemExit(3)
            check.update(pid=os.getpid(),manifest_sha256=sha(D/'manifest.json'));write(p/'first-heavy-start.json',check)
        phase(a.arm,'maps',prepare_maps)
        phase(a.arm,'smoke',lambda:command([sys.executable,T/'smoke.py',a.arm],p/'smoke.log'))
        phase(a.arm,'gate200k',lambda:command([sys.executable,T/'gate.py',a.arm],p/'gate.log'))
        phase(a.arm,'mirror200k',lambda:command([sys.executable,T/'mirror.py',a.arm],p/'mirror.log'))
        write(p/'review-required.json',{'stage':'target gate and mandatory mirror complete','complete':True,
              'result_sha256':sha(p/'result-200000.json'),'mirror_result_sha256':sha(p/'mirror-result-200000.json'),
              'decision':'Review target, off-target and direct Ocean mirror jointly before any normal-fuel admission or release of next job.'})

if __name__=='__main__':main()
