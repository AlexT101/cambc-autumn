"""Run one immutable latest-host refresh through the coordinated release helper.

Only reads live queue state until the existing release transaction. No repins,
queue rewrites or automatic retries of ambiguous uploads. Restart needs review.
"""
import argparse
import datetime
import fcntl
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

import loss_refresh as refresh
import loss_live as release
from refresh_build import ROOT, HERE

ls,sched,write = release.ls,release.sched,release.write


def late_coverage(work, plan):
    baseline={(r['map'],r['side']):r for r in refresh.baseline_rows(plan['host_version'],plan['pins'])
              if r['opp_name'].split()[-1].lower()=='mite'}
    entries={(c['map'],c['side']) for c in release.read(work/'book_cells.json') if c['opp']=='mite'}
    late=release.read(Path(plan['late_source_cells']))
    rows=[]
    for cell in late:
        key=cell['map'],cell['side'];result=baseline.get(key,{}).get('result')
        rows.append(dict(map=key[0],side=key[1],host_result=result,
                         status='natural_host_win' if result=='win' else 'booked' if key in entries else
                                'unknown_host_deferred' if result is None else 'confirmed_loss_uncovered'))
    write(work/'late-source-coverage.json',dict(host_version=plan['host_version'],cells=rows))
    return rows


def source_opportunity(work, plan):
    baseline={(r['opp_name'].split()[-1].lower(),r['map'],r['side']):r
              for r in refresh.baseline_rows(plan['host_version'],plan['pins'])}
    losses=sorted([m,s] for (opp,m,s),r in baseline.items() if opp=='fish' and r['result']=='loss')
    actionable=[[m,s] for m,s in losses if all(
        baseline.get((opp,m,s),{}).get('result') in ('win','loss') for opp in plan['pins'])]
    write(work/'first-source-fish-known-losses.json',losses)
    write(work/'first-source-fish-actionable-losses.json',actionable)
    write(work/'source-opportunity.json',dict(at=ls.now(),host_version=plan['host_version'],pins=plan['pins'],
          known={opp:sum(k[0]==opp for k in baseline) for opp in plan['pins']},
          fish_known_losses=len(losses),actionable_fish_losses=len(actionable),
          note='Read-only proposal; parent owns source queue. Unknown collateral excluded from actionable list.'))


def run(work):
    plan=release.read(work/'refresh-plan.json')
    state_path=work/'cycle-state.json'
    if state_path.exists() or any((work/n).exists() for n in ('build-started.json',release.STATE)):
        raise RuntimeError('Existing cycle requires explicit artifact reconciliation before restart')
    def status(phase,**extra):
        value=dict(at=ls.now(),phase=phase,**extra)
        write(state_path,value);print(json.dumps(value),flush=True)
    def stopped():
        if upload_pending and deadline is not None and time.time() >= deadline:
            raise RuntimeError('Upload deadline passed; keep current REST and preserve validation margin')
        if any((work/n).exists() for n in ('STOP','HOLD-PUBLISH','HOLD-LIVE-CHECK')):
            raise RuntimeError('Refresh control marker present')
    def wait(fn):
        while True:
            stopped()
            result=fn()
            if result:return result
            time.sleep(30)
    def protected():
        manifest=release.read(Path(plan['protected_first_build']))
        if not all(hashlib.sha256(Path(p).read_bytes()).hexdigest()==h for p,h in manifest.items()):
            raise RuntimeError('Protected first book changed')
        old=Path(plan['prior_work'])
        release.unchanged(old,release.read(old/release.STATE))
    upload_pending=True
    deadline=datetime.datetime.fromisoformat(plan['upload_deadline']).timestamp() if plan.get('upload_deadline') else None
    try:
        status('waiting_for_matching_host_and_sources',host_version=plan['host_version'],pins=plan['pins'],
               partial_baseline=plan['partial_baseline'])
        def ready():
            source_opportunity(work,plan)
            return refresh.ready(plan['host_version'],plan['pins'],
                                 [] if plan.get('existing_sources_only') else [plan['source_step']],
                                 plan['minimum_source_fraction'],plan['partial_baseline'],
                                 plan.get('minimum_baseline_fraction',0))
        wait(ready)
        status('waiting_for_reference_bench')
        wait(lambda:(work/'reference-bench.DONE').exists())
        protected()
        status('building',host_version=plan['host_version'])
        cmd=[sys.executable,str(HERE/'loss_refresh.py'),'--work',str(work),
             '--host-version',str(plan['host_version']),'--host-profile',str(work/'host-profile.json'),
             '--bot-name',plan['bot_name'],'--fish-pin',plan['pins']['fish'],'--mite-pin',plan['pins']['mite'],
             '--source-versions',plan['source_versions'],'--minimum-source-fraction',str(plan['minimum_source_fraction']),
             '--minimum-baseline-fraction',str(plan.get('minimum_baseline_fraction',0))]
        if plan.get('existing_sources_only'):cmd+=['--existing-sources-only']
        else:cmd+=['--after-step',plan['source_step']]
        for opp in plan['partial_baseline']:cmd+=['--partial-baseline',opp]
        with (work/'build.out').open('w') as out:
            subprocess.run(cmd,cwd=ROOT,stdout=out,stderr=subprocess.STDOUT,check=True)
        protected()
        late=late_coverage(work,plan)
        status('locally_ready_waiting_for_release_boundary',late_source_coverage=late)
        def can_prepare():
            st=sched.load()
            if st['batches']['rest']!=plan['expected_rest']:
                raise RuntimeError('Another book became REST; reconcile before upload')
            return not sched.queue_lines() and not any((sched.H/n).exists() for n in ('STOP','HOLD','PAUSE'))
        wait(can_prepare)
        state=release.prepare(work,plan['expected_rest'])
        status('uploading_once')
        if deadline is not None:
            os.environ['BOOK_UPLOAD_DEADLINE_EPOCH']=str(int(deadline))
        state=release.upload(work,state)
        upload_pending=False
        if state['phase']!='waiting_for_live_checks':
            raise RuntimeError('Upload reconciliation did not reach live checks')
        status('uploaded_rest_waiting_for_checks',version=state['version'])
        a=release.unchanged(work,state)
        def collected():
            tasks,created,finished,dropped,_=ls.state()
            mine=[t for t in tasks if t.get('part') in a['specs']]
            if any(t['id'] in dropped for t in mine):raise RuntimeError('Book check dropped')
            return len({t['part'] for t in mine})==len(a['specs']) and all(
                t['id'] in created and created[t['id']]['group'] in finished for t in mine)
        wait(collected)
        tasks,created,finished,dropped,_=ls.state()
        rows=release.select_results(a['expected'],a['specs'],state['version'],state['pin_groups'],
                                   tasks,created,finished,dropped,ls.suspect_groups(),ls.read_jsonl(ls.DATA/'games.jsonl'))
        write(work/'live-complete-audit.json',dict(version=state['version'],provenance='clean',
              wins=sum(r['result']=='win' for _,r in rows),rows=[dict(step=s,**r) for s,r in rows]))
        state=release.validate(work,state)
        while True:
            stopped()
            try:state=release.confirm(work,state);break
            except RuntimeError as error:
                if 'Platform activation pending' not in str(error):raise
            time.sleep(30)
        protected()
        status('published',version=state['version'],wins=state['wins'])
        sched.wake(dict(event_id=plan['bot_name']+'-published',at=ls.now(),work=str(work),version=state['version']))
    except Exception as error:
        status('held',error=repr(error))
        sched.wake(dict(event_id=plan['bot_name']+'-held',at=ls.now(),work=str(work),error=repr(error)))
        raise


if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--work',type=Path,required=True)
    a=ap.parse_args();os.chdir(ROOT)
    with (a.work/'cycle.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        run(a.work)
