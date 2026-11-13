"""Prepare an isolated replay template on the exact source of an unmasked submission."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

from refresh_build import ROOT, HERE, run, sched
from refresh_queue import write


def hashes(src):
    return {str(p.relative_to(src)):hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(src.rglob('*')) if p.is_file()}


def validate(profile, version, submitted):
    if (profile['version'] != version or not submitted or submitted.get('masked') is not False
            or submitted.get('label') != profile['label'] or submitted.get('commit') != profile['commit']):
        raise RuntimeError('Host profile does not match the unmasked submission')
    for key in ('reference','template'):
        path = ROOT/'bots'/profile[key]
        if hashes(path/'src') != profile[key+'_hashes']:
            raise RuntimeError(f'Frozen host {key} changed')
    return profile


def prepare(work, version, name, commit_bot):
    from loss_refresh import variant_name
    variant_name(version,name)
    submitted = next(h for h in sched.load()['history'] if h['version']==version)
    if submitted.get('masked') is not False:
        raise RuntimeError('Host submission is masked')
    source = Path(submitted['dir'])
    uploaded = Path(submitted['workspace'])/'bots/ocean/src'
    digest = hashes(source/'src')
    if not digest or digest != hashes(uploaded):
        raise RuntimeError('Source differs from actual uploaded source')
    commit = submitted['commit']
    relative = Path('bots')/commit_bot/'src'
    if relative.is_absolute() or '..' in relative.parts:
        raise ValueError('Invalid commit bot')
    files = subprocess.check_output(['git','ls-tree','-r','--name-only',commit,'--',str(relative)],cwd=ROOT,text=True).splitlines()
    committed = {str(Path(p).relative_to(relative)):hashlib.sha256(subprocess.check_output(
        ['git','show',f'{commit}:{p}'],cwd=ROOT)).hexdigest() for p in files}
    if committed != digest:
        raise RuntimeError('Source differs from frozen commit')
    reference,template = f'variants/{name}-base',f'variants/{name}-template'
    if any((ROOT/'bots'/p).exists() for p in (reference,template)) or (work/'host-profile.json').exists():
        raise RuntimeError('Host preparation already exists; reconcile instead of overwriting')
    work.mkdir(parents=True,exist_ok=True)
    run(['./copybot',str(source.relative_to(ROOT/'bots')),reference],work/'copy-reference.log')
    run(['./copybot',reference,template],work/'copy-template.log')
    target = ROOT/'bots'/template
    for patch in ('host.patch','handover-stale-read.patch'):
        with (HERE/patch).open() as inp, (work/(patch+'.log')).open('w') as out:
            subprocess.run(['patch','--batch','--fuzz=0','-p1'],cwd=target,stdin=inp,stdout=out,stderr=subprocess.STDOUT,check=True)
    (work/'empty.jsonl').write_text('')
    run([sys.executable,HERE/'build_book.py',work/'empty.jsonl',target/'src/book/book_data.h',
         '--prio','seeded'],work/'empty-header.log')
    if any(target.rglob('*.rej')):
        raise RuntimeError('Book integration has patch rejects')
    for p in target.rglob('*.orig'):
        p.unlink()
    profile = dict(version=version,label=submitted['label'],commit=commit,
                   upload_name=submitted.get('note',submitted['label']),
                   reference=reference,template=template,reference_hashes=digest,
                   template_hashes=hashes(target/'src'),uploaded_source=str(uploaded),
                   commit_source=str(relative),integration={p:hashlib.sha256((HERE/p).read_bytes()).hexdigest()
                                for p in ('host.patch','handover-stale-read.patch')})
    validate(profile,version,submitted)
    write(work/'host-profile.json',profile)
    return profile


if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--work',type=Path,required=True)
    ap.add_argument('--host-version',type=int,required=True)
    ap.add_argument('--name',required=True)
    ap.add_argument('--commit-bot',required=True,help='bot directory at the submitted commit')
    a=ap.parse_args()
    prepare(a.work,a.host_version,a.name,a.commit_bot)
