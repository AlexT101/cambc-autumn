"""Publish one verified partial loss book using the existing upload/queue helper.

Commands (run from repo root; replace WORK):
  py research/ideas-2026-11-13/rbook/loss_live.py --work WORK prepare --expected-rest 126
  py research/ideas-2026-11-13/rbook/loss_live.py --work WORK upload
  py research/ideas-2026-11-13/rbook/loss_live.py --work WORK reconcile
  py research/ideas-2026-11-13/rbook/loss_live.py --work WORK validate
  py research/ideas-2026-11-13/rbook/loss_live.py --work WORK promote
  py research/ideas-2026-11-13/rbook/loss_live.py --work WORK confirm

prepare/reconcile/validate do not call the API or change scheduler state. upload invokes
live_test.sh ONCE (it uploads, makes the latest book REST and queues checks). An interrupted upload is
never retried: reconcile history and queue; repair missing queue steps separately.
promote writes REST after revalidation; reconcile checks the scheduler configuration.
confirm reads platform live/selected versions before marking published. No polling
daemon. Existing control markers are respected at entry, never cleared by this driver;
the reused helper temporarily stops/restarts the scheduler, so the coordinator must
serialize it with other users of rbook-mask/prepared.json.
"""
import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess

import loss_live_plan as plan
import oppwatch
from refresh_build import ROOT, ls, sched, validate_stage
from refresh_queue import write

HELPER = Path(__file__).with_name('live_test.sh')
STATE = 'loss-live-state.json'


def read(path):
    return json.loads(path.read_text())


def ensure(ok, why):
    if not ok:
        raise RuntimeError(why)


def artifacts(work):
    build = read(work/'build-state.json')
    ensure(build['phase'] == 'ready_for_live_checks', 'Local build is not ready')
    entries = read(work/'book_cells.json')
    keys = {c['key'] for c in entries}
    verified = read(work/'verify.json')
    ensure(keys and len(keys) == len(entries) and set(verified) == keys and not any(verified.values()),
           'Incomplete exact verification')
    ensure((work/'stage.DONE').exists(), 'Missing stage.DONE')
    validate_stage((work/'stage.out').read_text(), work)
    ensure(0 < (work/'bundle.zip').stat().st_size <= 4900000, 'Invalid bundle size')
    forced = set((work/'force.txt').read_text().splitlines())
    ensure(forced <= keys, 'Forced keys outside the shipped book')
    if forced:
        ensure(re.search(rf'{len(forced)} forced cells, 0 bad,', (work/'forcecheck.out').read_text()),
               'Forced-draft fallback verification missing')
    pins = build['pins']
    baseline = {(r['opp_name'].split()[-1].lower(), r['map'], r['side']):r
                for r in ls.games(build['host_version']) if r.get('purpose') == 'set'
                and r.get('pin') == 'ref'
                and pins.get(r['opp_name'].split()[-1].lower()) == r.get('refset')}
    sources = plan.source_rows(work, pins)
    needed = plan.coverage(entries, forced, baseline, sources, pins)
    steps, expected = read(work/'live-steps.json'), read(work/'live-expectations.json')
    ensure(steps and expected, 'Missing live checks')
    specs = {}
    for cf, sid, opp, rs, host, pin in steps:
        ensure(sid not in specs and opp in pins and rs == pins[opp]
               and host == build['host_version'] and pin in ('ref', 'none'), 'Invalid/duplicate step')
        cells = read(Path(cf))
        ensure(cells and len(cells) == len({tuple(c) for c in cells}), 'Empty/duplicate step cells')
        specs[sid] = dict(id=sid,kind='cells',lost_by=host,opp=opp,refset=rs,pin=pin,cells=cells)
    wanted = {(sid,s['opp'],m,side,s['pin'],s['refset'] if s['pin']=='ref' else None)
              for sid,s in specs.items() for m,side in s['cells']}
    actual = {(e['step'],e['opponent'],e['map'],e['side'],e['pin'],e['refset']) for e in expected}
    ensure(len(actual) == len(expected) and actual == wanted and all(e['require_win'] for e in expected),
           'Expectations disagree with step cells or weaken required wins')
    pinned = {(e['opponent'],e['map'],e['side']) for e in expected if e['pin']=='ref'}
    ensure(set(needed) <= pinned, 'Missing provisional source or collateral pin checks')
    # Snapshot actual pinned source groups; named refsets alone are not proof of the opponent version.
    refs = ls.state()[4]
    pin_groups = {opp:refs[(pin,ls.TEAMS[opp][0])] for opp,pin in pins.items()}
    suspect = ls.suspect_groups()
    for entry in entries:
        source = sources[entry['key'].rsplit('-',1)[1]]
        cell = (entry['opp'],entry['map'],entry['side'])
        if cell not in pinned:
            ensure(source.get('group') not in suspect
                   and (source.get('source_group') or source.get('group')) == pin_groups[entry['opp']],
                   'Source win lacks clean target-pin provenance')
    for opp in pins:
        candidates = sorted((c for c in entries if c['opp']==opp),
                            key=lambda c:(c['key'] not in forced,c['map'],c['side']))
        required = {(opp,c['map'],c['side']) for c in candidates[:20 if opp=='mite' else 10]}
        current = {(e['opponent'],e['map'],e['side']) for e in expected if e['pin']=='none'}
        ensure(required <= current, 'Missing current-opponent sample')
    files = [work/n for n in ('build-state.json','book_cells.json','verify.json','force.txt','stage.out',
                              'stage.DONE','bundle.zip','live-steps.json','live-expectations.json')]
    if forced:
        files.append(work/'forcecheck.out')
    files += [Path(s[0]) for s in steps]
    bot = Path(build['bot']).resolve()
    ensure((bot/'src').is_dir(), 'Bot source directory missing')
    files += sorted((bot/'src').rglob('*'))
    digest = hashlib.sha256()
    for path in sorted(set(files)):
        if path.is_file():
            digest.update(str(path).encode()+b'\0'+path.read_bytes())
    return dict(build=build,entries=entries,expected=expected,specs=specs,
                pin_groups=pin_groups,digest=digest.hexdigest(),bot=str(bot))


def unchanged(work, state):
    a = artifacts(work)
    ensure(a['digest'] == state['digest'] and a['pin_groups'] == state['pin_groups'],
           'Artifacts or source pins changed since prepare; reconcile manually')
    return a


def guards(work, rest, idle=True):
    ensure(not any((work/n).exists() for n in ('STOP','HOLD-PUBLISH','HOLD-LIVE-CHECK')), 'Work held')
    ensure(not any((sched.H/n).exists() for n in ('STOP','PAUSE','HOLD'))
           and not (ls.DATA/'STOP').exists(), 'Scheduler/runner control marker present')
    st = sched.load()
    ensure(st['batches']['rest'] == rest and not sched.queue_lines(), 'REST or queue ownership changed')
    current = st['batches']['cur']
    ensure(not idle or current is None or current['phase']=='rest',
           'Batch in progress; retry at a resting boundary')
    rest_file = sched.H/'REST'
    ensure(not rest_file.exists() or int(rest_file.read_text()) == rest, 'Another REST request is pending')
    return st


def prepare(work, rest):
    ensure(not (work/STATE).exists(), 'Already prepared; use reconcile, never overwrite upload intent')
    a = artifacts(work)
    st = guards(work, rest)
    ids = set(a['specs'])
    queued = read(sched.H/'after-queue.json')
    ensure(not ids.intersection(s['id'] for s in queued)
           and not ids.intersection(st['batches'].get('after_done',[]))
           and not any(t.get('part') in ids for t in ls.state()[0]), 'Step IDs already used')
    state = dict(phase='prepared',at=ls.now(),expected_rest=rest,bot=a['bot'],digest=a['digest'],
                 pin_groups=a['pin_groups'],history_before=[h['version'] for h in st['history']])
    write(work/STATE,state)
    return state


def reconcile(work, state):
    a = unchanged(work,state)
    if state['phase'] == 'prepared':
        return state
    st = sched.load()
    candidates = [h for h in st['history'] if h['version'] not in state['history_before']
                  and h.get('label') == Path(state['bot']).name
                  and Path(h.get('dir','')).resolve() == Path(state['bot'])]
    ensure(len(candidates) == 1 and candidates[0].get('masked') is False,
           'Upload ambiguous/missing: inspect platform, prepared.json and helper log; DO NOT upload again')
    version = candidates[0]['version']
    ensure(state.get('version',version) == version, 'Uploaded version changed')
    state['version'] = version
    write(work/STATE,state)
    queued = read(sched.H/'after-queue.json')
    for sid,spec in a['specs'].items():
        found = [s for s in queued if s['id'] == sid]
        ensure(len(found)==1 and all(found[0].get(k)==v for k,v in dict(spec,version=version).items()),
               f'Queue step {sid} missing/conflicting: repair queue only, DO NOT upload again')
    if state['phase'] in ('upload_attempt','waiting_for_live_checks'):
        state['phase'] = 'waiting_for_live_checks'
    if state['phase'] == 'promotion_requested' and st['batches']['rest'] == version:
        # Scheduler state records desired REST, not necessarily completed platform activation.
        state['phase'] = 'promotion_configured'
    write(work/STATE,state)
    return state


def upload(work,state):
    ensure(state['phase']=='prepared', 'Upload already attempted; reconcile instead')
    a = unchanged(work,state)
    st = guards(work,state['expected_rest'])
    ensure([h['version'] for h in st['history']] == state['history_before'], 'History changed since prepare')
    ensure(not any(s['id'] in a['specs'] for s in read(sched.H/'after-queue.json')), 'Steps already queued')
    ensure(sched.MASK_UPLOADS is False, 'Upload masking enabled')
    pins = a['build']['pins']
    note = f"Charybdis 525 + fuel 01-02 + Fish {pins['fish']}/Mite {pins['mite']} loss book ({len(a['entries'])})"
    ensure(len(note)<=80, 'Upload note too long')
    state.update(phase='upload_attempt',at=ls.now(),note=note,rest_on_upload=True)
    write(work/STATE,state)
    with (work/'loss-live-upload.log').open('w') as out:
        result = subprocess.run(['bash',str(HELPER),state['bot'],note,'',str(work/'live-steps.json'),'--rest'],
                                cwd=ROOT,stdout=out,stderr=subprocess.STDOUT,
                                env=dict(os.environ,CAMBC_SLOT_WEIGHT='0.25'))
    state['helper_exit'] = result.returncode
    write(work/STATE,state)
    return reconcile(work,state)


def select_results(expected, specs, version, pin_groups, tasks, created, finished, dropped, suspect, rows):
    selected = []
    for sid,spec in specs.items():
        group_tasks = [t for t in tasks if t.get('part') == sid]
        ensure(group_tasks, f'Waiting for step {sid} to be planned')
        task_cells = []
        for task in group_tasks:
            tid = task['id']
            ensure(task['version']==version and task['purpose']=='set'
                   and task['opp_id']==ls.TEAMS[spec['opp']][0] and task['pin']==spec['pin']
                   and task.get('refset')==(spec['refset'] if spec['pin']=='ref' else None), 'Task provenance mismatch')
            ensure(tid not in dropped, f'Dropped task {tid}')
            ensure(tid in created and created[tid]['group'] in finished, f'Waiting for collection: {tid}')
            ev = created[tid]
            ensure(ev['live']==version and ev['group'] not in suspect, 'Wrong/suspect created group')
            source = pin_groups[spec['opp']] if spec['pin']=='ref' else None
            ensure(ev.get('source_group') == source, 'Created group source pin mismatch')
            wanted = {(g['map'],g['side']) for g in task['games'] if not g.get('filler')}
            task_cells += list(wanted)
            for cell in wanted:
                matches = [r for r in rows if r.get('task')==tid and r.get('group')==ev['group']
                           and (r.get('map'),r.get('side'))==cell and not r.get('filler')]
                # A retry can append the same observation, but conflicting observations must never be hidden.
                unique = {json.dumps(r,sort_keys=True):r for r in matches}
                ensure(len(unique)==1, f'Missing/conflicting collected row: {tid} {cell}')
                row = next(iter(unique.values()))
                ensure(row['version']==version and row['purpose']=='set' and row['opp_id']==task['opp_id']
                       and row.get('pin')==task['pin'] and row.get('refset')==task.get('refset')
                       and row.get('source_group')==source and row['status']=='finished', 'Row provenance mismatch')
                selected.append((sid,row))
        ensure(len(task_cells)==len(set(task_cells)) and set(task_cells)=={tuple(c) for c in spec['cells']},
               'Task cells disagree with frozen plan')
    ensure(len(selected)==len(expected), 'Incomplete requested coverage')
    return selected


def validate(work,state):
    ensure(state['phase'] in ('waiting_for_live_checks','validated','promotion_requested','promotion_configured'),
           'Reconcile upload and queue before validation')
    a = unchanged(work,state)
    tasks,created,finished,dropped,_ = ls.state()
    selected = select_results(a['expected'],a['specs'],state['version'],state['pin_groups'],
                              tasks,created,finished,dropped,ls.suspect_groups(),
                              ls.read_jsonl(ls.DATA/'games.jsonl'))
    results = []
    for sid,row in selected:
        ensure(row['result']=='win', f"Required win failed: {sid} {row['map']} {row['side']}")
        ensure(oppwatch.rhash(row) is not None, 'Full replay evidence missing')
        opp = a['specs'][sid]['opp']
        recordings = [work/'raw'/f"{c['key']}.repl26a" for c in a['entries']
                      if (c['opp'],c['map'],c['side'])==(opp,row['map'],row['side'])]
        diff = oppwatch.cell_divergence(row,recordings) if recordings else None
        ensure(not recordings or diff is not None, 'Book replay comparison unreadable')
        results.append(dict(step=sid,map=row['map'],side=row['side'],match=row['match'],result='win',diff=diff))
    write(work/'loss-live-results.json',results)
    state.update(phase='validated',at=ls.now(),wins=len(results),
                 wins_after_divergence=sum(r['diff'] is not None and r['diff']>=0 for r in results))
    write(work/STATE,state)
    return state


def promote(work,state):
    ensure(state['phase'] in ('validated','promotion_requested','promotion_configured'), 'Validate before promotion')
    if state['phase'] in ('promotion_requested','promotion_configured'):
        return reconcile(work,state)
    state = validate(work,state)
    if state.get('rest_on_upload'):
        return confirm(work,state)
    guards(work,state['expected_rest'])
    state.update(phase='promotion_requested',at=ls.now())
    write(work/STATE,state)
    # REST is the scheduler's existing publication interface; do not activate directly.
    target = sched.H/'REST'
    tmp = target.with_name('REST.loss-live.tmp')
    tmp.write_text(f"{state['version']}\n"); tmp.replace(target)
    return state


def confirm(work,state):
    ensure(state['phase'] in ('promotion_requested','promotion_configured','published')
           or (state['phase']=='validated' and state.get('rest_on_upload')), 'No promotion requested')
    state = reconcile(work,state)
    ensure(sched.load()['batches']['rest']==state['version'], 'Scheduler has not adopted REST yet')
    live,selected = ls.live_version()
    ensure(live==selected==state['version'], 'Platform activation pending or ownership changed')
    state.update(phase='published',at=ls.now())
    write(work/STATE,state)
    return state


def main():
    ap = argparse.ArgumentParser(description=__doc__,formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--work',type=Path,required=True)
    sub = ap.add_subparsers(dest='command',required=True)
    p = sub.add_parser('prepare'); p.add_argument('--expected-rest',type=int,required=True)
    for cmd in ('upload','reconcile','validate','promote','confirm'):
        sub.add_parser(cmd)
    args = ap.parse_args(); work = args.work.resolve()
    with (work/'loss-live.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        if args.command=='prepare':
            state = prepare(work,args.expected_rest)
        else:
            state = globals()[args.command](work,read(work/STATE))
        print(json.dumps(state,indent=2))


if __name__=='__main__':
    main()
