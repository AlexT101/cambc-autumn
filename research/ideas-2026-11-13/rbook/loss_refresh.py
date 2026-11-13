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

DEFAULT_SOURCE_VERSIONS = '117,118,119,125,126'


def source_versions(value):
    parts = value.split(',')
    if not parts or any(not p.isdigit() or int(p) < 1 for p in parts):
        raise ValueError('Source versions must be positive comma-separated integers')
    versions = [int(p) for p in parts]
    if len(set(versions)) != len(versions):
        raise ValueError('Duplicate source version')
    return ','.join(map(str, versions))


def baseline_rows(version, pins):
    return [r for r in ls.games(version) if r.get('purpose') == 'set' and r.get('pin') == 'ref'
            and pins.get(r['opp_name'].split()[-1].lower()) == r.get('refset')]


def ready(version, pins, steps, minimum_source_fraction=1.0, partial_baseline=(), minimum_baseline_fraction=0.0):
    partial_baseline = set(partial_baseline)
    if (not partial_baseline <= pins.keys() or not 0 <= minimum_baseline_fraction <= 1
            or (partial_baseline == pins.keys() and minimum_baseline_fraction == 0)):
        raise ValueError('All-partial baselines require an explicit positive minimum coverage fraction')
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
    baselines = [t for t in required if t['version'] == version
                 and t['opp_name'].split()[-1].lower() not in partial_baseline]
    if (not baselines and partial_baseline != pins.keys()) or not all(collected(t) for t in baselines):
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
        # A collector may append rows before its collected event; freeze readiness to this event snapshot.
        if row.get('group') is not None and row['group'] not in finished:
            continue
        actual[row['opp_name'].split()[-1].lower()].add((row['map'], row['side']))
    expected = collections.defaultdict(set)
    planned = collections.defaultdict(set)
    for t in required:
        if t['version'] == version:
            planned[t['opp_name'].split()[-1].lower()].update(
                (g['map'],g['side']) for g in t['games'] if not g.get('filler'))
        if t['version'] == version and (t['opp_name'].split()[-1].lower() not in partial_baseline or collected(t)):
            expected[t['opp_name'].split()[-1].lower()].update((g['map'], g['side']) for g in t['games'] if not g.get('filler'))
    if any(not planned[opp] or len(actual[opp]) / len(planned[opp]) < minimum_baseline_fraction
           for opp in partial_baseline):
        return False
    if any((not expected[opp] and opp not in partial_baseline) or actual[opp] != expected[opp] for opp in pins):
        raise RuntimeError('Matching host baseline has missing cells')
    return True


def variant_name(version, bot_name=None):
    name = f'rbook-loss-v{version}' if bot_name is None else bot_name
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]*', name):
        raise ValueError('--bot-name must be a single variant directory name')
    return name


def eligible_candidates(chosen, baseline, pins):
    kept, deferred = [], []
    for cell in chosen:
        key = (cell['opp'],cell['map'],cell['side'])
        if baseline.get(key,{}).get('result') != 'loss':
            raise RuntimeError(f'Candidate is not a confirmed host loss: {key}')
        unknown = [opp for opp in pins if baseline.get((opp,cell['map'],cell['side']),{}).get('result') not in ('win','loss')]
        if unknown:
            deferred.append(dict(**cell,reason='unknown collateral baseline',unknown_opponents=unknown))
        else:
            kept.append(cell)
    return kept,deferred


def build(work, version, pins, resume=False, bot_name=None, versions=DEFAULT_SOURCE_VERSIONS, host_profile=None):
    versions = source_versions(versions)
    submitted = next((h for h in sched.load()['history'] if h['version'] == version), None)
    if host_profile is not None:
        from loss_host import validate
        profile = validate(json.loads(Path(host_profile).read_text()),version,submitted)
        reference,template = profile['reference'],profile['template']
    else:
        profile = None
        reference,template = 'variants/chy-525f','variants/rbook-refresh-r11'
        if not submitted or submitted.get('label') != 'chy-525f' or submitted.get('masked') is not False:
            raise RuntimeError('This builder requires the matching unmasked chy-525f baseline')
    if profile is not None and not resume and any((work/n).exists() for n in ('fp.json','bad.json')):
        raise RuntimeError('New host requires freshly recorded fingerprints, not prior-host caches')
    name = variant_name(version, bot_name)
    host = ROOT/'bots/variants'/name
    if not resume and (host.exists() or (work/'build-started.json').exists()):
        raise RuntimeError('Build already started; reconcile artifacts instead of overwriting')
    baseline = {(r['opp_name'].split()[-1].lower(),r['map'],r['side']):r
                for r in baseline_rows(version,pins)}
    extra = work/'foreign-extra.tsv'
    selection = types.SimpleNamespace(versions=versions, host_version=version,
                                      host_losses_only=True, extra_uncovered_only=True,
                                      extra=extra if extra.exists() else None)
    if resume:
        started = json.loads((work/'build-started.json').read_text())
        frozen = json.loads((work/'selection.json').read_text())
        if (not host.is_dir() or started.get('bot') != str(host)
                or frozen['host_version'] != version or frozen['pins'] != pins
                or frozen.get('source_versions', DEFAULT_SOURCE_VERSIONS) != versions
                or frozen.get('host_profile') != profile):
            raise RuntimeError('Resume artifacts do not match this host, pins or source versions')
        (work/'forced-candidates.txt').write_text(''.join(k+'\n' for k in frozen['forced_keys']))
    else:
        chosen = []
        for opp, pin in pins.items():
            chosen += rbuild.select(selection,ls.TEAMS[opp][1],pin,opp)
        chosen,deferred = eligible_candidates(chosen,baseline,pins)
        write(work/'deferred-candidates.json',deferred)
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
        write(work/'selection.json',dict(host_version=version,pins=pins,source_versions=versions,host_profile=profile,
              policy='confirmed host losses only',
              baseline={opp:dict(cells=sum(k[0]==opp for k in baseline),
                                 losses=sum(k[0]==opp and r['result']=='loss' for k,r in baseline.items()))
                        for opp in pins},candidates=chosen,forced_keys=forced))
        (work/'forced-candidates.txt').write_text(''.join(k+'\n' for k in forced))
        write(work/'build-started.json',dict(at=ls.now(),bot=str(host)))
        # This frozen copy includes the verified stale-round handover guard; main bots stay untouched.
        run(['./copybot',template,f'variants/{name}'],work/'copy.log')
    write(work/'build-state.json',dict(phase='building',at=ls.now(),bot=str(host),resumed=resume))
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
    exclusion_file = work/'excluded-keys.json'
    excluded = json.loads(exclusion_file.read_text()) if exclusion_file.exists() else {}
    if not isinstance(excluded,dict) or not set(excluded) <= cells.keys():
        raise RuntimeError('Excluded entries do not match this frozen candidate book')
    kept,used=[],0
    # Every entry repairs a confirmed loss: maximize coverage within the source-size budget.
    for key in sorted(sizes,key=lambda k:(sizes[k],k)):
        if key in excluded:
            continue
        if used+sizes[key]<=4130000:
            kept.append(key);used+=sizes[key]
    if not kept:
        raise RuntimeError('No verified entries fit')
    (work/'keys.txt').write_text(''.join(k+'\n' for k in kept))
    env=dict(os.environ,PRIO='seeded',REF=Path(reference).name,BOOK_JOBS='8',CAMBC_SLOT_WEIGHT='0.25',
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
             '--opp',reference,'--work',work,'--jobs','8'],work/'forcecheck.out',env)
        if not re.search(rf'{len(force_keys)} forced cells, 0 bad,', (work/'forcecheck.out').read_text()):
            raise RuntimeError('Forced-draft fallback check failed')
    write(work/'build-state.json',dict(phase='ready_for_live_checks',at=ls.now(),bot=str(host),
          host_version=version,pins=pins,entries=len(actual),host_profile=profile,
          host_name=profile['upload_name'] if profile else 'Charybdis 525 + fuel 01-02',
          opponents=dict(collections.Counter(c['opp'] for c in actual)),
          forced_entries=len(force_keys),publication='held until target-pin and forced collateral checks'))
    from loss_live_plan import plan
    plan(work)


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--work',type=Path,required=True)
    ap.add_argument('--host-version',type=int,required=True)
    ap.add_argument('--bot-name',help='distinct directory name under bots/variants (default rbook-loss-vHOST_VERSION)')
    ap.add_argument('--source-versions',type=source_versions,default=DEFAULT_SOURCE_VERSIONS,
                    help='winning recording versions; frozen at selection and checked on resume')
    ap.add_argument('--host-profile',type=Path,help='verified exact-source baseline and replay template')
    ap.add_argument('--partial-baseline',action='append',default=[],choices=['fish','mite'])
    ap.add_argument('--minimum-baseline-fraction',type=float,default=0.0,
                    help='minimum known fraction for each partial opponent; required when all are partial')
    ap.add_argument('--mite-pin',required=True)
    ap.add_argument('--fish-pin',default='r8')
    ap.add_argument('--after-step',action='append',required=True)
    ap.add_argument('--resume',action='store_true',help='resume reconciled local artifacts using their frozen selection')
    ap.add_argument('--minimum-source-fraction',type=float,default=1.0,
                    help='allow a partial source sweep; baseline complete except explicit --partial-baseline')
    a=ap.parse_args();variant_name(a.host_version,a.bot_name)
    a.work.mkdir(parents=True,exist_ok=True)
    pins=dict(fish=a.fish_pin,mite=a.mite_pin)
    with (a.work/'build.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        if (a.work/'build-started.json').exists() and not a.resume:
            raise RuntimeError('Existing build requires reconciliation')
        write(a.work/'build-state.json',dict(phase='waiting_for_sweeps',at=ls.now(),host_version=a.host_version,pins=pins))
        try:
            while not a.resume and not ready(a.host_version,pins,a.after_step,a.minimum_source_fraction,a.partial_baseline,a.minimum_baseline_fraction):
                if (a.work/'STOP').exists():
                    return
                time.sleep(30)
            if (a.work/'STOP').exists():
                return
            build(a.work,a.host_version,pins,resume=a.resume,bot_name=a.bot_name,versions=a.source_versions,host_profile=a.host_profile)
        except Exception as error:
            write(a.work/'build-state.json',dict(phase='held',at=ls.now(),error=repr(error)))
            raise


if __name__=='__main__':
    main()
