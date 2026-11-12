"""Batch live tests (2026-11-12, user): the rest version (v115) stays active on the ladder; a candidate is active only
while one quota-sized batch of its groups is created and played, then the rest version is activated again (an
existing submission, never a re-upload). With no candidate, the rest version is active.

Per candidate (live queue / ocean line, built and smoked by live_sched.prepare): the full gate is core + ext of set v1
against every opponent in refsets.json (52 groups each), the same cells the rest version plays as control, so each
candidate pairs against the rest version cell by cell. The first group under a new refset captures that opponent's
current bot as the pin.

Control runs at the end (user, 2026-11-12): while any candidate is waiting, the quota goes to candidate batches and
the rest version's control groups are held (data/HOLD-TASKS.json: pending, not dropped). They are created only once
no candidate is waiting, while the rest version sits active; a candidate's gate is reported when its own groups are
in, and again with the full pairing once the control has played.

Batch cycle: rest version active, nothing in flight, and quota room for a full batch (or, once, whatever fits when
sched/BATCH-NOW exists) -> upload (first batch) or activate the candidate, append the next `room` gate tasks and write
data/BATCH (the runner pauses replay collection and raises its in-flight cap) -> once those tasks are created and every
group has played (or the quota is spent), activate the rest version. Hourly while resting: Fish/Mite/BattleCats opponent-change observations
(logged + wake only; testing pins never change automatically).

State: state.json 'batches'. Report: py tools/live_batches.py report
"""
import json
import math
import sys
import time
from pathlib import Path

from ladder_opp_check import Evidence, InvalidComparison

REST = 115
RESERVE = 10          # the runner's --reserve: quota kept free for teammates
PARTS = (('core', 99), ('ext', 90))
OBS_EVERY = 3600
RETRY = 90            # seconds between repeated activation requests


def specs(ls, version, rsets, now):
    """Gate tasks with plan's ids (`ladder_scrims.py plan`), so the rest version's planned control matches them."""
    maps = ls.load_set('v1')
    out = []
    for part, prio in PARTS:
        for k, (opp, rs) in enumerate(rsets.items()):
            oid, name = ls.TEAMS[opp]
            for i, g in enumerate(ls.set_groups(maps[part], maps['core']), 1):
                out.append({'id': f'v{version}-v1{part}-{rs}-{opp}-{i:02d}', 'version': version, 'set': 'v1',
                            'part': part, 'purpose': 'set', 'opp_id': oid, 'opp_name': name, 'pin': 'ref',
                            'refset': rs, 'games': g, 'priority': prio, 'order': i, 'planned': now,
                            'campaign': 'batches', '_k': k})
    # Interleave opponents, so a partial batch stays balanced.
    out.sort(key=lambda t: (-t['priority'], t['order'], t.pop('_k')))
    return out


def paired(ls, cand, rest, rsets):
    """Candidate against the rest version on the cells both played, per opponent (same refset, map, side)."""
    out = {}
    for opp, rs in rsets.items():
        oid = ls.TEAMS[opp][0]
        side = lambda v: {(r['map'], r['side']): r['result'] == 'win' for r in ls.games(v)
                          if r['opp_id'] == oid and r.get('refset') == rs and r.get('purpose') == 'set'}
        a, b = side(cand), side(rest)
        both = a.keys() & b.keys()
        wa, wb = sum(a[k] for k in both), sum(b[k] for k in both)
        fa, fb = sum(a[k] and not b[k] for k in both), sum(b[k] and not a[k] for k in both)
        out[opp] = dict(refset=rs, cells=len(both), cand_wins=wa, rest_wins=wb, net=wa - wb, flips_for=fa,
                        flips_against=fb, z=round((fa - fb) / math.sqrt(fa + fb), 2) if fa + fb else 0.0)
    return out


def minutes(B, until):
    """Minutes each version was live since batch mode began, from the confirmed-live switch log."""
    out, sw = {}, B.get('switches', [])
    for i, x in enumerate(sw):
        end = sw[i + 1]['t'] if i + 1 < len(sw) else until
        out[x['live']] = out.get(x['live'], 0) + (end - x['t']) / 60
    return {v: round(m, 1) for v, m in out.items()}


class Batches:
    def __init__(self, s, detector):
        self.s, self.ls, self.det = s, s.ls, detector

    def state(self, st):
        return st.setdefault('batches', {'rest': REST, 'cur': None, 'done': [], 'switches': [],
                                         'obs': {'next_due': 0, 'epochs': 0}, 'started_at': self.s.now()})

    def note(self, B, key, msg):
        # Log a waiting reason once, not every tick.
        if B.get('_note', {}).get(key) != msg:
            B.setdefault('_note', {})[key] = msg
            self.s.log(msg)

    # ------------------------------------------------------------ platform

    def collected(self, version):
        """Every group of `version` has its games recorded (collection pauses during batches)."""
        _, created, finished, _, _ = self.ls.state()
        return all(e['group'] in finished for e in created.values() if e.get('live') == version)

    def drained(self):
        """No group whose matches may still be playing (played/finished events; collection may lag)."""
        events = self.ls.read_jsonl(self.ls.DATA / 'events.jsonl')
        done = {e['group'] for e in events if e['ev'] in ('played', 'finished')}
        return not any(e['ev'] == 'created' and e['group'] not in done for e in events)

    def activate(self, B, target, why):
        last = B.get('_activate', {})
        if last.get('target') == target and time.time() - last.get('t', 0) < RETRY:
            return
        with self.ls.live_lock(self.ls.DATA):
            if not self.drained():
                return
            rc, out = self.s.sh(['cambc', 'submissions', 'activate', str(target)])
        B['_activate'] = {'target': target, 't': time.time()}
        self.s.log(f'batches: activate existing v{target} ({why}): rc {rc} {out.strip()[-100:]}')

    def batch_file(self, on):
        f = self.ls.DATA / 'BATCH'
        if on:
            f.write_text(self.s.now() + '\n')   # refreshed every tick: the runner ignores a stale one
        else:
            f.unlink(missing_ok=True)

    def room(self):
        q = self.ls.quota().get('quota') or {}
        limit = q.get('limit') or 100
        return limit - q.get('used', 0) - RESERVE, limit - RESERVE

    # ------------------------------------------------------------ tick

    def tick(self, st):
        s, ls = self.s, self.ls
        B = self.state(st)
        if (s.H / 'PAUSE').exists() or (s.H / 'HOLD').exists():
            self.batch_file(False)
            return
        cur = B['cur']
        rest = B['rest']
        allowed = {rest} | ({cur['version']} if cur and cur.get('version') else set())
        d = s.outside_check(st, allowed)
        if not d:
            self.batch_file(False)
            return
        live, sel = d['active']['version'], d['selected']['version']
        if not B['switches'] or B['switches'][-1]['live'] != live:
            B['switches'].append({'live': live, 't': time.time(), 'at': s.now()})
            s.save(st)
        rsets_now = s.refsets()
        resting = live == sel == rest and (cur is None or cur['phase'] == 'rest')
        self.observe(st, B, rest, rsets_now, resting)
        # A queued line counts as waiting too: control must not slip in while the next candidate builds.
        self.hold_control(rest, hold=cur is not None or bool(s.queue_lines()))
        if cur is None:
            self.batch_file(False)
            self.plan_rest(B, rest, rsets_now)
            c = s.prepare(st)
            if c is None:
                if live != rest or sel != rest:
                    self.activate(B, rest, 'no candidate')
                self.final(B, rest)
                s.save(st)
                return
            self.hold_control(rest, hold=True)
            cur = B['cur'] = {'cand': c, 'label': c['label'], 'version': None, 'rsets': rsets_now, 'phase': 'rest',
                              'batches': [], 'picked_at': s.now()}
            s.log(f"batches: next candidate {c['label']} on {rsets_now}; v{rest} control held until candidates finish")
            s.save(st)
        getattr(self, 'phase_' + cur['phase'])(st, B, cur, live, sel)
        s.save(st)

    def hold_control(self, rest, hold):
        tasks, created, finished, dropped, _ = self.ls.state()
        ids = sorted(t['id'] for t in tasks if t['version'] == rest and t.get('purpose') == 'set'
                     and t['id'] not in created and t['id'] not in dropped) if hold else []
        f = self.ls.DATA / 'HOLD-TASKS.json'
        try:
            if json.loads(f.read_text()) == ids:
                return
        except (OSError, ValueError):
            pass
        tmp = f.with_suffix('.tmp')
        tmp.write_text(json.dumps(ids) + '\n')
        tmp.replace(f)
        self.s.log(f'batches: {len(ids)} v{rest} control groups held' if hold else f'batches: v{rest} control released')

    def final(self, B, rest):
        """Once the control has played, the full pairing of every candidate reported without it."""
        todo = [c for c in B['done'] if not c.get('final')]
        if not todo:
            return
        tasks, created, finished, dropped, _ = self.ls.state()
        if any(t['version'] == rest and t.get('purpose') == 'set' and t['id'] not in created and t['id'] not in dropped
               for t in tasks) or not self.drained() or not self.collected(rest):
            return
        for c in todo:
            c['final'] = paired(self.ls, c['version'], rest, c['rsets'])
            rec = {'event_id': f"batch-final-v{c['version']}", 'version': c['version'], 'label': c['label'],
                   'rest': rest, 'paired_vs_rest': c['final'], 'note': 'control complete', 'at': self.s.now()}
            self.ls.append_jsonl(self.s.H / 'gates.jsonl', rec)
            self.s.wake(rec)
            self.s.log(f"batches: final v{c['version']} ({c['label']}) vs v{rest}: {json.dumps(c['final'])}")

    def plan_rest(self, B, rest, rsets):
        tasks = {t['id'] for t in self.ls.read_jsonl(self.ls.DATA / 'tasks.jsonl')}
        new = [t for t in specs(self.ls, rest, rsets, self.s.now()) if t['id'] not in tasks]
        for t in new:
            self.ls.append_jsonl(self.ls.DATA / 'tasks.jsonl', t)
        if new:
            self.s.log(f'batches: planned {len(new)} control groups for v{rest} on {rsets}')

    def gate_tasks(self, cur):
        tasks, created, finished, dropped, _ = self.ls.state()
        ids = {t['id'] for t in tasks}
        allspec = specs(self.ls, cur['version'], cur['rsets'], self.s.now()) if cur['version'] else None
        unplanned = [t for t in allspec if t['id'] not in ids] if allspec else None
        planned_pending = [t for t in tasks if t['version'] == cur['version'] and t.get('campaign') == 'batches'
                           and t['id'] not in created and t['id'] not in dropped] if cur['version'] else []
        return unplanned, planned_pending, tasks, created, dropped

    def phase_rest(self, st, B, cur, live, sel):
        s, ls, rest = self.s, self.ls, B['rest']
        self.batch_file(False)
        if live != rest or sel != rest:
            self.activate(B, rest, 'rest')
            return
        self.plan_rest(B, rest, cur['rsets'])
        unplanned, planned_pending, tasks, created, dropped = self.gate_tasks(cur)
        # Held control groups wait for the end; only other rest-version groups (opp-checks) hold a batch back.
        rest_pending = [t for t in tasks if t['version'] == rest and t.get('purpose') != 'set'
                        and t['id'] not in created and t['id'] not in dropped]
        last = cur['batches'][-1] if cur['batches'] else None
        if last and not last.get('reported') and self.collected(cur['version']):
            last['reported'] = self.s.now()
            res = paired(ls, cur['version'], rest, cur['rsets'])
            self.s.log(f"batches: batch {len(cur['batches'])} of v{cur['version']} collected; paired {json.dumps(res)}")
            self.s.wake({'event_id': f"batch-v{cur['version']}-{len(cur['batches'])}", 'batch_done': cur['label'],
                         'version': cur['version'], 'paired_vs_rest': res, 'minutes_live': minutes(B, time.time()),
                         'at': self.s.now()})
        if rest_pending or not self.drained():
            self.note(B, 'rest', f"batches: {cur['label']} waits: v{rest} has {len(rest_pending)} groups to create "
                                 f"or groups are in flight")
            return
        todo = (len(specs(ls, 0, cur['rsets'], None)) if cur['version'] is None
                else len(unplanned) + len(planned_pending))
        if cur['version'] and todo == 0:
            if last and last.get('reported'):
                self.finish(st, B, cur)
            return
        room, cap = self.room()
        # Wait for a full batch: the rolling hour frees up, less one hourly observation per opponent.
        need = min(todo, cap - len(cur['rsets']))
        now_file = s.H / 'BATCH-NOW'
        if now_file.exists():
            need = 1   # operator: start with whatever fits
        if room < need or room <= 0:
            self.note(B, 'rest', f"batches: {cur['label']} waits for quota: room {room}, batch needs {need} "
                                 f"({todo} groups left)")
            return
        if cur['version'] is None:
            c = cur['cand']
            if not s.submit(st, c, max(h['version'] for h in st['history']), plan=False):
                return
            cur['version'] = st['history'][-1]['version']
            cur['live_at'] = s.now()
            s.log(f"batches: uploaded {cur['label']} as v{cur['version']}")
            unplanned, planned_pending, *_ = self.gate_tasks(cur)
        n = max(0, min(len(unplanned), room - len(planned_pending)))
        for t in unplanned[:n]:
            ls.append_jsonl(ls.DATA / 'tasks.jsonl', t)
        cur['batches'].append({'n': n + len(planned_pending), 'room': room, 'start': s.now()})
        now_file.unlink(missing_ok=True)
        self.batch_file(True)
        s.log(f"batches: {cur['label']} v{cur['version']} batch {len(cur['batches'])}: "
              f"{n + len(planned_pending)} groups (room {room})")
        cur['phase'] = 'activate_batch'
        B.pop('_note', None)
        if live != cur['version']:
            self.activate(B, cur['version'], 'batch')

    def phase_activate_batch(self, st, B, cur, live, sel):
        self.batch_file(True)
        if live == sel == cur['version']:
            cur['phase'] = 'batch'
            cur['batches'][-1]['live_at'] = self.s.now()
        else:
            self.activate(B, cur['version'], 'batch')

    def phase_batch(self, st, B, cur, live, sel):
        self.batch_file(True)
        if not (live == sel == cur['version']):
            self.s.log(f"batches: v{cur['version']} no longer live (live v{live} selected v{sel}); ending batch")
        else:
            with self.ls.live_lock(self.ls.DATA):
                if not self.drained():
                    return
                _, planned_pending, *_ = self.gate_tasks(cur)
                if planned_pending and self.room()[0] > 0:
                    return   # the runner creates them next
        cur['batches'][-1]['end'] = self.s.now()
        cur['phase'] = 'activate_rest'
        self.activate(B, B['rest'], 'batch played')

    def phase_activate_rest(self, st, B, cur, live, sel):
        if live == sel == B['rest']:
            self.batch_file(False)
            cur['phase'] = 'rest'
            cur['batches'][-1]['rest_at'] = self.s.now()
            self.s.log(f"batches: batch {len(cur['batches'])} of v{cur['version']} played; v{B['rest']} active again "
                       f"(minutes live {minutes(B, time.time())})")
        else:
            self.activate(B, B['rest'], 'restore')

    def finish(self, st, B, cur):
        res = paired(self.ls, cur['version'], B['rest'], cur['rsets'])
        rec = {'event_id': f"batch-gate-v{cur['version']}", 'version': cur['version'], 'label': cur['label'],
               'rest': B['rest'], 'rsets': cur['rsets'], 'batches': cur['batches'], 'paired_vs_rest': res,
               'minutes_live': minutes(B, time.time()), 'at': self.s.now()}
        self.ls.append_jsonl(self.s.H / 'gates.jsonl', rec)
        self.s.wake(rec)
        st['reported'].append(cur['version'])
        B['done'].append({k: v for k, v in cur.items() if k != 'cand'} | {'result': res, 'done_at': self.s.now()})
        B['cur'] = None
        self.s.log(f"batches: gate v{cur['version']} ({cur['label']}) done: {json.dumps(res)}")

    # ------------------------------------------------------------ hourly opponent observations (rest version only)

    def observe(self, st, B, rest, rsets, allow_new):
        det, ls = self.det, self.ls
        ev = Evidence(ls)
        det.bootstrap(st, ev)
        det.finish(st, ev)
        d, clock = st['opp_detector'], B['obs']
        ours = lambda k: k.startswith('batches-hour')
        pending = any(ours(k) and r['status'] == 'pending' for k, r in d['runs'].items())
        if allow_new and not pending and time.time() >= clock['next_due']:
            epoch, runs = clock['epochs'] + 1, {}
            for opp, rs in rsets.items():
                oid = ls.TEAMS[opp][0]
                base = next(iter(sorted((t for t in ev.tasks.values() if t['version'] == rest
                                         and t.get('purpose') == 'set' and t.get('part') == 'core'
                                         and t['opp_id'] == oid and t.get('refset') == rs
                                         and t['id'] not in ev.dropped), key=lambda t: t.get('order', 0))), None)
                test_source = ev.refs.get((rs, oid))
                if base is None or test_source not in ev.finished:
                    runs = None   # an opponent's control pin is not captured yet: start the epoch once all are
                    break
                snap = d['snapshots'].get(opp)
                source = snap['source_group'] if snap else test_source
                key = f'batches-hour{epoch}-v{rest}-{opp}'
                baseline = self.equivalent(ev, base, source)
                tasks = []
                if baseline is None:
                    baseline = key + '-observed'
                    tasks.append(dict(base, id=baseline, purpose='oppcheck', pin=source, refset=None, is_ref=False,
                                      priority=98, planned=self.s.now(), note='Hourly detector baseline'))
                tasks.append(dict(base, id=key + '-cur', purpose='oppcheck', pin='none', refset=None, is_ref=False,
                                  priority=98, planned=self.s.now(), note='Hourly current opponent, never a repin'))
                runs[key] = {'status': 'pending', 'opponent': opp, 'version': rest, 'snapshot_group': source,
                             'testing_source': test_source, 'testing_refset': rs, 'baseline_task': baseline,
                             'current_task': key + '-cur', 'task_specs': tasks, 'planned_at': self.s.now()}
            if runs is not None:
                d['runs'].update(runs)
                clock.update(epochs=epoch, next_due=time.time() + OBS_EVERY)
                self.s.save(st)   # intents before appends: a restart cannot add another epoch
        for key, run in d['runs'].items():
            if not ours(key) or run['status'] != 'pending':
                continue
            for t in run['task_specs']:
                old = ev.tasks.get(t['id'])
                if old is None:
                    ls.append_jsonl(ls.DATA / 'tasks.jsonl', t)
                    ev.tasks[t['id']] = t
        for event in d['outbox'].values():
            if not event['delivered']:
                self.s.wake(event['record'])
                event['delivered'] = True
                self.s.save(st)

    def equivalent(self, ev, base, source):
        """A finished group of the same own version, opponent and cells whose opponent bot is `source`: the
        hourly baseline without replaying it (live games are deterministic)."""
        cells = [(g['map_id'], g['side']) for g in base['games']]
        for tid, t in ev.tasks.items():
            if (t['version'] != base['version'] or t['opp_id'] != base['opp_id']
                    or [(g['map_id'], g['side']) for g in t['games']] != cells):
                continue
            try:
                g = ev.group(tid)
            except InvalidComparison:
                continue
            if g and (g['created'].get('source_group') or g['created']['group']) == source:
                return tid
        return None


def report():
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import ladder_scrims as ls
    import live_sched as s
    st = json.loads(s.STATE.read_text())
    B = st.get('batches')
    if not B:
        sys.exit('batch mode has not started')
    print(f"rest v{B['rest']}; minutes live since {B['started_at']}: {minutes(B, time.time())}")
    for c in B['done'] + ([B['cur']] if B['cur'] else []):
        print(f"\n{c['label']} v{c.get('version')} ({c['phase'] if 'result' not in c else 'done'}), "
              f"{len(c['batches'])} batches")
        if c.get('version'):
            for opp, r in paired(ls, c['version'], B['rest'], c['rsets']).items():
                print(f"  {opp:<5} {r['refset']:<4} cand {r['cand_wins']}/{r['cells']}  v{B['rest']} "
                      f"{r['rest_wins']}/{r['cells']}  net {r['net']:+d}  flips {r['flips_for']}-{r['flips_against']} "
                      f"z {r['z']:+.2f}")


if __name__ == '__main__':
    if sys.argv[1:] == ['report']:
        report()
    else:
        sys.exit('usage: py tools/live_batches.py report')
