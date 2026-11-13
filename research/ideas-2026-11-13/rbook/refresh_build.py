"""Finish one queued Mite refresh without agents; preserve the current Fish entries.

Wait for the book-free sweeps, record new wins, fit the source-size budget, verify,
and optionally publish through the existing REST transaction. Never modify main bots.
"""
import argparse
import ast
import collections
import fcntl
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
OLD = Path('/home/ubuntu/tmp-offload/rbook/x2')
sys.path.insert(0, str(ROOT / 'tools'))
import ladder_scrims as ls
import live_sched as sched
from refresh_queue import write


def run(args, log, env=None):
    with log.open('w') as out:
        subprocess.run([str(a) for a in args], cwd=ROOT, env=env, stdout=out,
                       stderr=subprocess.STDOUT, check=True)


def ready(work, refset):
    state = sched.load()
    prefix = f'book-refresh-{refset}-mite'
    if not all(s in state['batches'].get('after_done', []) for s in (prefix, prefix+'-v118', prefix+'-v117')):
        return False
    tasks, created, finished, dropped, _ = ls.state()
    tasks = [t for t in tasks if t.get('refset') == refset and t.get('opp_name') == 'Mite'
             and t.get('purpose') == 'set' and (t.get('version') == 119 or
             t.get('part') in (prefix+'-v118', prefix+'-v117'))]
    if any(t['id'] in dropped for t in tasks):
        raise RuntimeError('Refresh contains dropped tasks; review before building')
    return bool(tasks) and all(t['id'] in created and created[t['id']]['group'] in finished for t in tasks)


def validate_stage(stage, work=None):
    expected_fallback = 24
    if work is not None and (work/'book.jsonl').exists():
        cells = {c['key'] for c in json.loads((work/'book_cells.json').read_text())}
        entries = {e['key']:e for e in map(json.loads,(work/'book.jsonl').read_text().splitlines())}
        # Match fallbacktest's distinct long-entry sample; a small partial book cannot supply 24 cases.
        expected_fallback = min(24,sum(entries[k]['rounds'] > 450 for k in cells))
    invalid = re.findall(r'invalid\s+(\d+)', stage)
    if (not expected_fallback or not invalid or any(int(n) for n in invalid)
            or not re.search(rf'plain: {expected_fallback} games, [1-9]\d* bodies handed over', stage)):
        raise RuntimeError('Fallback verification missing, incomplete or invalid')
    wide = re.search(r'== 100M\nidentical replays: (\d+)/(\d+)([^\n]*)', stage)
    if not wide or int(wide[2]) != 52:
        raise RuntimeError('100M bench requires all 52 replays compared')
    if int(wide[1]) != 52:
        if work is None or '; differ: ' not in wide[3]:
            raise RuntimeError('100M bench requires 52 replays identical except documented forced-draft cells')
        differs = ast.literal_eval(wide[3].split('; differ: ', 1)[1])
        forced = set((work/'force.txt').read_text().splitlines())
        allowed = {(c['map'],c['side']) for c in json.loads((work/'book_cells.json').read_text())
                   if c['key'] in forced}
        if len(differs) != 52-int(wide[1]) or not set(differs) <= allowed:
            raise RuntimeError('100M bench differs outside the documented forced-draft cells')


def build(work, refset, publish):
    name = f'rbook-refresh-{refset}'
    host = ROOT / 'bots/variants' / name
    if host.exists() or (work / 'build-started.json').exists():
        raise RuntimeError('Build already started; inspect artifacts rather than overwriting or resubmitting')
    suspect = ls.suspect_groups()
    excluded = sorted({r['group'] for r in ls.read_jsonl(ls.DATA/'games.jsonl')
                       if r.get('refset') == refset and r['group'] in suspect})
    write(work/'excluded-groups.json', excluded)
    write(work/'build-started.json', {'at': ls.now(), 'host': str(host)})
    write(work/'build-state.json', {'phase':'building', 'at':ls.now(), 'bot':str(host)})
    run(['./copybot', 'variants/rbook-x2', f'variants/{name}'], work/'copy.log')
    with (HERE/'handover-stale-read.patch').open() as patch, (work/'handover-patch.log').open('w') as out:
        subprocess.run(['patch','-p1'],cwd=host,stdin=patch,stdout=out,stderr=subprocess.STDOUT,check=True)
    for directory in ('raw', 'ent'):
        (work/directory).symlink_to((OLD/directory).resolve(), target_is_directory=True)
    for filename in ('fp.json', 'bad.json'):
        if (OLD/filename).exists():
            shutil.copyfile(OLD/filename, work/filename)
    # Old forced Mite recordings belong to r9/r10, not this refreshed opponent.
    extra = [l for l in (OLD/'extra.tsv').read_text().splitlines()
             if l.strip() and (len(l.split()) < 5 or l.split()[4] == 'fish')]
    (work/'extra.tsv').write_text('\n'.join(extra)+'\n')
    args = ['--host', f'variants/{name}', '--work', work, '--prio', 'seeded', '--jobs', '8',
            '--opp', 'Intercontinental Fish:r8', '--opp', f'Mite:{refset}',
            '--extra', work/'extra.tsv', '--force-versions', '901']
    run([sys.executable, HERE/'rbuild.py', *args, '--no-build'], work/'sizes.out')
    old = json.loads((OLD/'book_cells.json').read_text())
    fish = {c['key'] for c in old if c['opp'] == 'fish'}
    cells = {c['key']: c for c in json.loads((work/'book_cells.json').read_text())}
    if not fish <= cells.keys():
        raise RuntimeError('Refresh would lose existing Fish entries')
    forced_cells = {(c['map'], c['side']) for c in old if c['key'] in fish and c['version'] == 901}
    fps = json.loads((work/'fp_book.json').read_text())
    sizes = {}
    for line in (work/'sizes.out').read_text().splitlines():
        p = line.split()
        if len(p) == 5 and p[0] == 'cell' and p[3] in cells:
            sizes[p[3]] = int(p[4]) + sum((len(n)+1)//2 for n in fps[p[3]])
    used = sum(sizes[k] for k in fish)
    records = collections.defaultdict(dict)
    for r in ls.games():
        if r.get('refset') == refset and r['version'] in (117, 118, 119):
            records[(r['map'],r['side'])][r['version']] = r['result'] == 'win'
    candidates = []
    for key, cell in cells.items():
        pair = (cell['map'], cell['side'])
        if cell['opp'] != 'mite' or pair in forced_cells:
            continue
        results = records[pair]
        worth = 1-(sum(results.values())+1)/(len(results)+2)
        candidates.append((worth/sizes[key], key))
    kept = set(fish)
    for _, key in sorted(candidates, reverse=True):
        if used + sizes[key] <= 4130000:
            kept.add(key)
            used += sizes[key]
    mite = len(kept-fish)
    if mite < 170:
        raise RuntimeError(f'Only {mite} new Mite entries fit; review balance instead of auto-publishing')
    (work/'keys.txt').write_text('\n'.join(sorted(kept))+'\n')
    write(work/'selection.json', {'fish_preserved':len(fish), 'new_mite':mite, 'estimated_blob':used,
                                'forced_fish_cells_excluded_from_mite':sorted(forced_cells)})
    env = dict(os.environ, PRIO='seeded', REF='chy-525f',
               CAMBC_BIN=str(ROOT/'tools/fastengine/runner/fastrunner'), FASTRUNNER_MODE='native')
    # stage.sh performs exact verification, fallback, fresh-map checks, and both benches.
    stage_args = ['--opp','Intercontinental Fish:r8','--opp',f'Mite:{refset}',
                  '--extra',work/'extra.tsv','--force-versions','901','--jobs','8']
    run(['bash', HERE/'stage.sh', name, work, work/'keys.txt', *stage_args], work/'stage-driver.log', env)
    verified = json.loads((work/'verify.json').read_text())
    if set(verified) != kept or any(verified.values()):
        raise RuntimeError('Entry verification incomplete or failed')
    stage = (work/'stage.out').read_text()
    validate_stage(stage, work)
    if (work/'bundle.zip').stat().st_size > 4900000:
        raise RuntimeError('Bundle exceeds conservative size ceiling')
    run([sys.executable,HERE/'forcecheck.py','--host',f'variants/{name}',
         '--opp','variants/chy-525f','--work',work],work/'forcecheck.out',env)
    force = (work/'forcecheck.out').read_text()
    if not re.search(r'bad\s*[:=]?\s*0|0 bad',force):
        raise RuntimeError('Forced draft check needs review; see forcecheck.out')
    result = {'phase':'ready','at':ls.now(),'bot':str(host),'fish':len(fish),'mite':mite,
              'refset':refset,'book_free_sources':[117,118,119]}
    write(work/'build-state.json',result)
    if not publish:
        return
    if (work/'HOLD-PUBLISH').exists():
        result.update(phase='ready_publication_held', reason=(work/'HOLD-PUBLISH').read_text().strip())
        write(work/'build-state.json', result)
        return
    current = sched.load()
    if current['batches']['rest'] != 126 or sched.queue_lines() or (work/'STOP').exists():
        raise RuntimeError('REST/queue ownership changed; ready book preserved for coordinator')
    if any((sched.H/f).exists() for f in ('STOP','PAUSE','HOLD')):
        raise RuntimeError('Scheduler has a control marker; do not clear it')
    # One persisted upload attempt: a failure must be reconciled, never blindly retried.
    write(work/'publish-attempt.json',{'at':ls.now(),'expected_rest':126,'bot':str(host)})
    note = f'Charybdis 525 + fuel 01-02 + Fish r8/Mite {refset} exact book ({len(kept)})'
    run(['bash','/home/ubuntu/tmp-offload/rbook-mask/new_rest.sh',host,note],work/'publish.log',env)
    current = sched.load()
    history = current['history'][-1]
    if current['batches']['rest'] != history['version'] or history.get('label') != name:
        raise RuntimeError('Upload result requires reconciliation')
    result.update(phase='published',version=history['version'],at=ls.now())
    write(work/'build-state.json',result)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--work',type=Path,required=True)
    ap.add_argument('--refset',required=True)
    ap.add_argument('--publish',action='store_true')
    a=ap.parse_args()
    if not re.fullmatch(r'r[0-9]+', a.refset):
        raise ValueError('Expected a named refset such as r11')
    a.work.mkdir(parents=True,exist_ok=True)
    with (a.work/'build.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        write(a.work/'build-state.json',{'phase':'waiting_for_book_free_sweeps','at':ls.now()})
        while not ready(a.work,a.refset):
            if (a.work/'STOP').exists():
                return
            q=a.work/'queue-state.json'
            if q.exists() and json.loads(q.read_text())['phase']=='held':
                raise RuntimeError('Stability check held; no build')
            time.sleep(30)
        try:
            build(a.work,a.refset,a.publish)
        except Exception as error:
            write(a.work/'build-state.json', {'phase':'held', 'at':ls.now(), 'error':repr(error)})
            raise


if __name__=='__main__':
    try:
        main()
    except Exception as error:
        print('REFRESH HELD:',repr(error),file=sys.stderr,flush=True)
        raise
