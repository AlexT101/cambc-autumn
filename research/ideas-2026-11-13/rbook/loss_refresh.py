"""Build a loss-only book from a matching host sweep and target-pin winning recordings.

No uploads or queue mutations. The resulting book awaits live checks before publication.
"""
import argparse
import collections
import fcntl
import json
import os
from pathlib import Path
import re
import sys
import time
import types

import rbuild
from refresh_build import ROOT, HERE, run, validate_stage
from refresh_queue import write

sys.path.insert(0, str(ROOT/'tools'))
import ladder_scrims as ls
import live_sched as sched


def baseline_rows(version, pins):
    return [r for r in ls.games(version) if r.get('purpose') == 'set' and r.get('pin') == 'ref'
            and pins.get(r['opp_name'].split()[-1].lower()) == r.get('refset')]


def ready(version, pins, steps, minimum_source_fraction=1.0):
    if not 0 < minimum_source_fraction <= 1:
        raise ValueError('Source fraction must be in (0, 1]')
    state = sched.load()
    if minimum_source_fraction == 1 and not set(steps) <= set(state['batches'].get('after_done', [])):
        return False
    tasks, created, finished, dropped, _ = ls.state()
    required = [t for t in tasks if t.get('part') in steps or
                (t['version'] == version and t.get('purpose') == 'set'
                 and pins.get(t['opp_name'].split()[-1].lower()) == t.get('refset'))]
    if any(t['id'] in dropped for t in required):
        raise RuntimeError('Required source task dropped')
    def collected(t):
        return t['id'] in created and created[t['id']]['group'] in finished
    baselines = [t for t in required if t['version'] == version]
    if not baselines or not all(collected(t) for t in baselines):
        return False
    for step in steps:
        sources = [t for t in required if t.get('part') == step]
        if not sources or sum(collected(t) for t in sources) / len(sources) < minimum_source_fraction:
            return False
    suspect = ls.suspect_groups()
    if any(created[t['id']]['group'] in suspect for t in required if collected(t)):
        raise RuntimeError('Required source group is suspect; repair coverage before building')
    actual = collections.defaultdict(set)
    for row in baseline_rows(version, pins):
        actual[row['opp_name'].split()[-1].lower()].add((row['map'], row['side']))
    expected = collections.defaultdict(set)
    for t in required:
        if t['version'] == version:
            expected[t['opp_name'].split()[-1].lower()].update((g['map'], g['side']) for g in t['games'])
    if any(not expected[opp] or actual[opp] != expected[opp] for opp in pins):
        raise RuntimeError('Matching host baseline has missing cells')
    return True


def build(work, version, pins):
    submitted = next((h for h in sched.load()['history'] if h['version'] == version), None)
    if not submitted or submitted.get('label') != 'chy-525f' or submitted.get('masked') is not False:
        raise RuntimeError('This builder requires the matching unmasked chy-525f baseline')
    name = f'rbook-loss-v{version}'
    host = ROOT/'bots/variants'/name
    if host.exists() or (work/'build-started.json').exists():
        raise RuntimeError('Build already started; reconcile artifacts instead of overwriting')
    baseline = {(r['opp_name'].split()[-1].lower(),r['map'],r['side']):r
                for r in baseline_rows(version,pins)}
    extra = work/'foreign-extra.tsv'
    selection = types.SimpleNamespace(versions='117,118,119,125,126', host_version=version,
                                      host_losses_only=True, extra_uncovered_only=True,
                                      extra=extra if extra.exists() else None)
    chosen = []
    for opp, pin in pins.items():
        chosen += rbuild.select(selection,ls.TEAMS[opp][1],pin,opp)
    if not chosen:
        raise RuntimeError('No target-pin wins on host losses yet')
    # select() names an exact recording; a per-cell deduplicated view can hide that match.
    from loss_live_plan import source_rows
    rows = source_rows(work,pins)
    forced = []
    for cell in chosen:
        source = rows[cell['key'].rsplit('-',1)[1]]
        base = baseline[(cell['opp'],cell['map'],cell['side'])]
        if source['our_picks'] != base['our_picks']:
            forced.append(cell['key'])
    write(work/'selection.json',dict(host_version=version,pins=pins,policy='confirmed host losses only',
          baseline={opp:dict(cells=sum(k[0]==opp for k in baseline),
                             losses=sum(k[0]==opp and r['result']=='loss' for k,r in baseline.items()))
                    for opp in pins},candidates=chosen,forced_keys=forced))
    (work/'forced-candidates.txt').write_text(''.join(k+'\n' for k in forced))
    write(work/'build-started.json',dict(at=ls.now(),bot=str(host)))
    write(work/'build-state.json',dict(phase='building',at=ls.now(),bot=str(host)))
    # This frozen copy includes the verified stale-round handover guard; main bots stay untouched.
    run(['./copybot','variants/rbook-refresh-r11',f'variants/{name}'],work/'copy.log')
    args = ['--versions',selection.versions,'--host-version',str(version),'--host-losses-only',
            '--selection',work/'selection.json','--extra-uncovered-only',
            '--force-keys',work/'forced-candidates.txt','--jobs','8']
    if selection.extra:
        args += ['--extra',selection.extra]
    for opp,pin in pins.items():
        args += ['--opp',f'{ls.TEAMS[opp][1]}:{pin}']
    run([sys.executable,HERE/'rbuild.py','--host',f'variants/{name}','--work',work,
         '--prio','seeded','--no-build',*args],work/'sizes.out')
    cells = {c['key']:c for c in json.loads((work/'book_cells.json').read_text())}
    fps = json.loads((work/'fp_book.json').read_text())
    sizes = {}
    for line in (work/'sizes.out').read_text().splitlines():
        p = line.split()
        if len(p)==5 and p[0]=='cell' and p[3] in cells:
            sizes[p[3]]=int(p[4])+sum((len(n)+1)//2 for n in fps[p[3]])
    if sizes.keys()!=cells.keys():
        raise RuntimeError('Missing entry size evidence')
    kept,used=[],0
    # Every entry repairs a confirmed loss: maximize coverage within the source-size budget.
    for key in sorted(sizes,key=lambda k:(sizes[k],k)):
        if used+sizes[key]<=4130000:
            kept.append(key);used+=sizes[key]
    if not kept:
        raise RuntimeError('No verified entries fit')
    (work/'keys.txt').write_text(''.join(k+'\n' for k in kept))
    env=dict(os.environ,PRIO='seeded',REF='chy-525f',CAMBC_SLOT_WEIGHT='0.25',
             CAMBC_BIN=str(ROOT/'tools/fastengine/runner/fastrunner'),FASTRUNNER_MODE='native')
    run(['bash',HERE/'stage.sh',name,work,work/'keys.txt',*args],work/'stage-driver.log',env)
    verified=json.loads((work/'verify.json').read_text())
    actual=json.loads((work/'book_cells.json').read_text())
    if not verified or set(verified)!={c['key'] for c in actual} or any(verified.values()):
        raise RuntimeError('Incomplete exact verification')
    validate_stage((work/'stage.out').read_text(),work)
    if (work/'bundle.zip').stat().st_size>4900000:
        raise RuntimeError('Bundle exceeds conservative platform size limit')
    force_keys=set((work/'force.txt').read_text().splitlines()) & set(verified)
    # build_book may discard conflicting keys; check only the entries actually shipped.
    (work/'force.txt').write_text(''.join(k+'\n' for k in sorted(force_keys)))
    if force_keys:
        run([sys.executable,HERE/'forcecheck.py','--host',f'variants/{name}',
             '--opp','variants/chy-525f','--work',work,'--jobs','8'],work/'forcecheck.out',env)
        if not re.search(rf'{len(force_keys)} forced cells, 0 bad,', (work/'forcecheck.out').read_text()):
            raise RuntimeError('Forced-draft fallback check failed')
    write(work/'build-state.json',dict(phase='ready_for_live_checks',at=ls.now(),bot=str(host),
          host_version=version,pins=pins,entries=len(actual),
          opponents=dict(collections.Counter(c['opp'] for c in actual)),
          forced_entries=len(force_keys),publication='held until target-pin and forced collateral checks'))
    from loss_live_plan import plan
    plan(work)


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--work',type=Path,required=True)
    ap.add_argument('--host-version',type=int,required=True)
    ap.add_argument('--mite-pin',required=True)
    ap.add_argument('--fish-pin',default='r8')
    ap.add_argument('--after-step',action='append',required=True)
    ap.add_argument('--minimum-source-fraction',type=float,default=1.0,
                    help='allow a partial source sweep; the host baseline must still be complete')
    a=ap.parse_args();a.work.mkdir(parents=True,exist_ok=True)
    pins=dict(fish=a.fish_pin,mite=a.mite_pin)
    with (a.work/'build.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        if (a.work/'build-started.json').exists():
            raise RuntimeError('Existing build requires reconciliation')
        write(a.work/'build-state.json',dict(phase='waiting_for_sweeps',at=ls.now(),host_version=a.host_version,pins=pins))
        try:
            while not ready(a.host_version,pins,a.after_step,a.minimum_source_fraction):
                if (a.work/'STOP').exists():
                    return
                time.sleep(30)
            if (a.work/'STOP').exists():
                return
            build(a.work,a.host_version,pins)
        except Exception as error:
            write(a.work/'build-state.json',dict(phase='held',at=ls.now(),error=repr(error)))
            raise


if __name__=='__main__':
    main()
