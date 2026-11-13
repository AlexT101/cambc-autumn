"""One bounded opponent refresh: confirm stability, then queue existing book-free versions.

Uses the existing live runner and scheduler; no model calls, uploads, or direct activations.
STOP in the work directory or scheduler control markers yield without clearing anything.
"""
import argparse
import fcntl
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'tools'))
import ladder_scrims as ls
import live_sched as sched
from ladder_opp_check import Evidence, compare


def write(path, value):
    tmp = path.with_suffix(path.suffix + '.tmp')
    tmp.write_text(json.dumps(value, indent=2) + '\n')
    tmp.replace(path)


def tick(work, opponent, refset):
    state_path = work / 'queue-state.json'
    state = json.loads(state_path.read_text()) if state_path.exists() else {'phase': 'check', 'attempt': 0}
    if state['phase'] in ('queued', 'held'):
        return True
    if any(p.exists() for p in [work / 'STOP', sched.H / 'STOP', sched.H / 'PAUSE', sched.H / 'HOLD', ls.DATA / 'STOP']):
        return False
    live = sched.load()
    batches = live['batches']
    ev = Evidence(ls)
    if state.get('task'):
        if state['task'] not in ev.tasks:
            ls.append_jsonl(ls.DATA / 'tasks.jsonl', state['task_spec'])
            return False
        current = ev.group(state['task'])
        if current is None:
            return False
        baseline = ev.group(state['baseline'])
        if baseline is None:
            raise RuntimeError('Baseline evidence disappeared')
        changed = compare(baseline, current)
        state['last_comparison'] = {'at': ls.now(), 'changed_cells': changed,
                                    'baseline': state['baseline'], 'current': state['task']}
        if changed:
            state.update(baseline=state.pop('task'), next_check=time.time() + 900)
            write(state_path, state)
            print('Opponent still changing; next stability check in 15 minutes', flush=True)
            return False
        state['phase'] = 'stable'
    if state['phase'] == 'check':
        if time.time() < state.get('next_check', 0):
            return False
        if state['attempt'] >= 6:
            state.update(phase='held', reason='Six checks without a stable opponent; coordinator review')
            write(state_path, state)
            return True
        if not state.get('baseline'):
            runs = [r for r in live['opp_detector']['runs'].values()
                    if r['opponent'] == opponent and r['status'] == 'complete'
                    and r['version'] == batches['rest']]
            if not runs:
                return False
            state['baseline'] = max(runs, key=lambda r: r['completed_at'])['current_task']
        base = ev.tasks[state['baseline']]
        if base['version'] != batches['rest']:
            state.update(phase='held', reason='REST changed during stability check')
            write(state_path, state)
            return True
        state['attempt'] += 1
        tid = f'book-refresh-{refset}-{opponent}-check-{state["attempt"]}'
        task = dict(base, id=tid, purpose='book-refresh-check', pin='none', refset=None,
                    is_ref=False, priority=98, planned=ls.now(), note='Book refresh stability confirmation')
        # Persist intent before append; the same id repairs an interrupted append on restart.
        state['task'] = tid
        state['task_spec'] = task
        write(state_path, state)
        if tid not in ev.tasks:
            ls.append_jsonl(ls.DATA / 'tasks.jsonl', task)
        print('Planned', tid, 'against current', opponent, flush=True)
        return False
    if batches['cur'] is not None or sched.queue_lines():
        return False
    played = {e['group'] for e in ls.read_jsonl(ls.DATA / 'events.jsonl')
              if e['ev'] in ('played', 'finished')}
    if any(e['group'] not in played for e in ev.created.values()
           if ev.tasks.get(e['task'], {}).get('version') == batches['rest']):
        return False
    steps_path = sched.H / 'after-queue.json'
    original = steps_path.read_text()
    steps = json.loads(original)
    done = set(batches.get('after_done', []))
    pending = [s for s in steps if s['id'] not in done]
    if any(s['id'] != 'hold-control' for s in pending):
        return False
    prefix = f'book-refresh-{refset}-{opponent}'
    new = [dict(id=prefix, kind='repin_replay', refsets={opponent: refset},
                choose=f'{prefix}-BOT', ahead=True,
                note='User 2026-11-13: refresh book now; stable check, book-free v119 sweep')]
    new += [dict(id=f'{prefix}-v{v}', kind='cells', version=v, lost_by=119,
                 opp=opponent, refset=refset, ahead=True,
                 note='Existing book-free versions on v119 losses for refreshed book coverage') for v in (118, 117)]
    if any(s['id'] == prefix for s in steps):
        state['phase'] = 'queued'
        write(state_path, state)
        return True
    if any(rs == refset for _, rs in sched.refsets().items()):
        raise RuntimeError('Refset already exists without this refresh step')
    (sched.H / f'{prefix}-BOT').write_text('119\n')
    (work / 'after-queue.before.json').write_text(original)
    insert = next((i for i, s in enumerate(steps) if s['id'] not in done), len(steps))
    steps[insert:insert] = new
    if steps_path.read_text() != original:
        raise RuntimeError('Another coordinator changed the queue; retry after review')
    write(steps_path, steps)
    state.update(phase='queued', queued_at=ls.now(), steps=[s['id'] for s in new])
    write(state_path, state)
    print('Queued refresh', state['steps'], flush=True)
    return True


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--work', type=Path, required=True)
    ap.add_argument('--opp', choices=['fish', 'mite'], required=True)
    ap.add_argument('--refset', required=True)
    ap.add_argument('--once', action='store_true')
    args = ap.parse_args()
    args.work.mkdir(parents=True, exist_ok=True)
    with (args.work / 'queue.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        while True:
            try:
                done = tick(args.work, args.opp, args.refset)
            except Exception as error:
                write(args.work / 'queue-error.json', {'at': ls.now(), 'error': repr(error)})
                raise
            if done or args.once:
                return
            time.sleep(30)


if __name__ == '__main__':
    main()
