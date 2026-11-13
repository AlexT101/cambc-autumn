"""One bounded current-opponent check of an already verified refresh, then promote that same version.

Uses existing upload/scheduler machinery. Never retries an upload or alters testing pins.
"""
import argparse
import concurrent.futures as cf
import json
import os
from pathlib import Path
import subprocess
import sys
import time

import oppwatch
from refresh_build import ROOT, validate_stage
from refresh_queue import write

sys.path.insert(0, str(ROOT/'tools'))
import ladder_scrims as ls
import live_sched as sched


def validate_live_results(results):
    if not results or any(r['result'] != 'win' or r['diff'] is None for r in results):
        raise RuntimeError('Live check lost or lacks replay evidence; preserve REST and inspect live-check-results.json')
    return dict(wins=len(results), exact_wins=sum(r['diff'] == -1 for r in results),
                wins_after_divergence=sum(r['diff'] != -1 for r in results))


def run(work):
    state_file = work/'live-check-state.json'
    if (work/'HOLD-LIVE-CHECK').exists():
        write(state_file, {'phase':'held_policy','at':ls.now(),
                          'reason':(work/'HOLD-LIVE-CHECK').read_text().strip()})
        return
    if state_file.exists():
        raise RuntimeError('Live check already started; reconcile its state instead of retrying')
    write(state_file, {'phase':'waiting_for_local_checks', 'at':ls.now()})
    deadline = time.monotonic()+7200
    while time.monotonic()<deadline:
        if (work/'STOP').exists():
            raise RuntimeError('Refresh STOP requested')
        state = json.loads((work/'build-state.json').read_text())
        if state['phase']=='held':
            raise RuntimeError(f'Local build held: {state}')
        if state['phase'] in ('ready', 'ready_publication_held'):
            break
        time.sleep(15)
    else:
        raise RuntimeError('Local verification timeout')
    validate_stage((work/'stage.out').read_text(), work)
    verified = json.loads((work/'verify.json').read_text())
    if len(verified)!=410 or any(verified.values()) or not (work/'stage.DONE').exists():
        raise RuntimeError('Expected complete 410-entry verification')
    if (work/'bundle.zip').stat().st_size>4900000:
        raise RuntimeError('Bundle too large')
    st=sched.load()
    if st['batches']['rest']!=126 or sched.queue_lines():
        raise RuntimeError('REST/queue ownership changed')
    if any((sched.H/f).exists() for f in ('STOP','PAUSE','HOLD')):
        raise RuntimeError('Scheduler control marker present')
    bot=Path(state['bot'])
    write(state_file, {'phase':'upload_attempt', 'at':ls.now(), 'bot':str(bot)})
    with (work/'live-upload.log').open('w') as out:
        subprocess.run(['bash','/home/ubuntu/tmp-offload/rbook-mask/multi_test.sh',str(bot),
                        'Charybdis 525 + fuel 01-02 + Fish r8/Mite r11 exact book (410)',
                        '',str(work/'live-steps.json')],cwd=ROOT,stdout=out,stderr=subprocess.STDOUT,
                       env=dict(os.environ,CAMBC_SLOT_WEIGHT='0.25'),check=True)
    matches=[h for h in sched.load()['history'] if h['label']==bot.name]
    if len(matches)!=1:
        raise RuntimeError('Cannot identify unique uploaded refresh')
    version=matches[0]['version']
    write(state_file, {'phase':'waiting_for_live_checks', 'at':ls.now(), 'version':version})
    step_ids={s[1] for s in json.loads((work/'live-steps.json').read_text())}
    deadline=time.monotonic()+3600
    while time.monotonic()<deadline:
        if (work/'STOP').exists():
            raise RuntimeError('Refresh STOP requested')
        tasks,created,finished,dropped,_=ls.state()
        tasks=[t for t in tasks if t.get('part') in step_ids and t['version']==version]
        if any(t['id'] in dropped for t in tasks):
            raise RuntimeError('Live-check task dropped')
        if len(tasks)==6 and all(t['id'] in created and created[t['id']]['group'] in finished for t in tasks):
            break
        time.sleep(15)
    else:
        raise RuntimeError('Live checks not collected within one hour')
    groups={created[t['id']]['group'] for t in tasks}
    if groups & ls.suspect_groups():
        raise RuntimeError('Live checks include suspect groups')
    rows=[r for r in ls.read_jsonl(ls.DATA/'games.jsonl') if r['group'] in groups]
    wanted={opp:{tuple(c) for c in json.loads((work/f'live-{opp}-cells.json').read_text())}
            for opp in ('mite','fish')}
    book=json.loads((work/'book_cells.json').read_text())
    selected={}
    for row in rows:
        opp=row['opp_name'].split()[-1].lower()
        cell=(row['map'],row['side'])
        if opp in wanted and cell in wanted[opp]:
            if row.get('pin')!='none' or row.get('refset') is not None or row['version']!=version:
                raise RuntimeError('Live check was not against current opponent')
            selected[(opp,*cell)]=row
    if set(selected)!={(opp,*cell) for opp,cells in wanted.items() for cell in cells}:
        raise RuntimeError('Missing requested current-opponent cells')

    def check(item):
        key,row=item
        recordings=[work/'raw'/f"{c['key']}.repl26a" for c in book
                    if (c['opp'],c['map'],c['side'])==key]
        diff=oppwatch.cell_divergence(row,recordings)
        return dict(opponent=key[0],map=key[1],side=key[2],result=row['result'],diff=diff,match=row['match'])
    with cf.ThreadPoolExecutor(8) as pool:
        results=list(pool.map(check,selected.items()))
    write(work/'live-check-results.json',results)
    outcome = validate_live_results(results)
    st=sched.load()
    if st['batches']['rest']!=126 or st['batches']['cur'] is not None or sched.queue_lines():
        raise RuntimeError('Ownership changed before promotion')
    if any((sched.H/f).exists() for f in ('STOP','PAUSE','HOLD')) or (work/'STOP').exists():
        raise RuntimeError('Control marker before promotion')
    write(state_file, {'phase':'promotion_requested','at':ls.now(),'version':version,**outcome})
    (sched.H/'REST').write_text(f'{version}\n')
    deadline=time.monotonic()+900
    while time.monotonic()<deadline:
        live,selected_version,_=sched.submissions()
        if live==selected_version==version and sched.load()['batches']['rest']==version:
            write(state_file, {'phase':'published','at':ls.now(),'version':version,**outcome})
            return
        time.sleep(30)
    raise RuntimeError('Promotion request needs reconciliation; do not resubmit')


if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--work',type=Path,required=True)
    a=ap.parse_args()
    try:
        run(a.work)
    except Exception as error:
        write(a.work/'live-check-error.json',{'at':ls.now(),'error':repr(error)})
        raise
