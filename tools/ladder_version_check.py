"""Scheduler-owned hourly v1 probes. Never creates or changes opponent pins.

The runner shares live-switch.lock and stops creating groups while the durable
marker exists. It keeps collecting existing groups, so the scheduler can drain.
An ambiguous create is not retried: reconcile its group ID before resuming.
"""
import hashlib
import json
import os
import time
from pathlib import Path
from ladder_coordination import live_lock


PROBE_VERSION = 1
PROBE_ID = 'cd7eedca-dfbf-4832-aab1-b75ca30e7704'
INTERVAL = 3600


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix('.tmp')
    with tmp.open('w') as f:
        json.dump(value, f, indent=2)
        f.flush()
        os.fsync(f.fileno())
    tmp.replace(path)


def selection(d):
    return {'active': d['active']['version'], 'selected': d['selected']['version'],
            'pinned': d['pinned'], 'newest': max(x['version'] for x in d['submissions'])}


def fingerprint(d):
    # Exclude diagnostics/runtime metadata and priority obfuscation. Full game
    # trajectories are stronger evidence than the final winner or score alone.
    fields = ('roster', 'teams', 'championTimelines', 'teamTimelines', 'events', 'heatmaps')
    body = {k: d[k] for k in fields}
    body['match'] = {k: v for k, v in d['match'].items()
                     if k not in ('engineBuildHash', 'engineVersion', 'seed')}
    return hashlib.sha256(json.dumps(body, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


class VersionCheck:
    def __init__(self, ls, home, log, wake):
        self.ls, self.home, self.log, self.wake = ls, Path(home), log, wake
        self.file = self.home / 'version-check.json'
        self.marker = ls.DATA / 'version-check-active.json'
        self.records = self.home / 'version-check-events.jsonl'
        self.evidence = self.home / 'version-check-evidence'

    def save(self, st):
        write_json(self.file, st)

    def event(self, kind, **data):
        rec = dict(event=kind, at=self.ls.now(), **data)
        self.ls.append_jsonl(self.records, rec)
        self.log('version-check ' + json.dumps(rec))
        if kind in ('opponent-change-evidence', 'version-check-needs-review', 'incomplete'):
            self.ls.append_jsonl(self.home / 'version-check.ready', rec)
        return rec

    def block(self, st, why):
        if st.get('phase') != 'blocked':
            st['blocked_phase'] = st['phase']
            st['phase'], st['error'] = 'blocked', why
            self.save(st)
            self.wake(self.event('version-check-needs-review', reason=why, cycle=st.get('cycle')))
        return True

    def snapshot(self):
        return json.loads(self.ls.cambc('submissions', 'list', '--json'))

    def tick(self, scheduler_state):
        """True means this tick owns live selection; skip ordinary scheduler work."""
        with live_lock(self.ls.DATA):
            return self._tick(scheduler_state)

    def _tick(self, scheduler_state):
        if not self.file.exists():
            return False
        st = json.loads(self.file.read_text())
        phase = st.get('phase', 'idle')
        if phase == 'idle':
            if not st.get('enabled') or time.time() < st.get('next_due', 0):
                return False
            if any((self.home / x).exists() for x in ('HOLD', 'PAUSE', 'STOP')):
                return False
            d = self.snapshot()
            snap = selection(d)
            expected = max(h['version'] for h in scheduler_state['history'])
            if snap['active'] != expected or snap['selected'] != expected:
                return False
            q = self.ls.quota().get('quota', {})
            if (q.get('limit') or 100) - q.get('used', 0) < 2:
                return False
            if st.get('probe_id') != PROBE_ID or st.get('probe_version') != PROBE_VERSION:
                raise ValueError('version-check must use the verified original v1')
            fixture = st['fixture']
            if len(fixture) != 5 or len({g['map_id'] for g in fixture}) != 5:
                raise ValueError('version-check needs exactly five distinct frozen maps')
            st.update(phase='drain', cycle=str(time.time_ns()), started=time.time(),
                      resume=snap, groups={}, attempting=None, abort_reason=None)
            self.save(st)
            write_json(self.marker, {'owner': str(self.file), 'cycle': st['cycle']})
            self.event('draining', cycle=st['cycle'], restore=snap)
            return True
        if phase == 'blocked':
            return True
        # Recreate the exclusion after a crash between state and marker writes.
        if phase != 'analyze' and not self.marker.exists():
            write_json(self.marker, {'owner': str(self.file), 'cycle': st['cycle']})
        d = self.snapshot()
        cur, prior = selection(d), st['resume']
        if cur['newest'] != prior['newest']:
            return self.block(st, 'outside submission appeared; preserve its selection and reconcile manually')
        original = (prior['active'], prior['selected'], prior['pinned'])
        actual = (cur['active'], cur['selected'], cur['pinned'])
        if phase == 'drain':
            if actual != original:
                return self.block(st, 'outside selection changed while draining; no activation performed')
            _, created, finished, _, _ = self.ls.state()
            if any(e['group'] not in finished for e in created.values()):
                return True
            # Persist before the mutation: restart reconciles both pre/post-call states.
            st['phase'] = 'activating'
            self.save(st)
            phase = 'activating'
        if phase == 'activating':
            status = str(d['selected'].get('status', '')).lower()
            if cur['selected'] == PROBE_VERSION and ('fail' in status or 'error' in status):
                st.update(phase='restoring', abort_reason='v1 build failed: ' + status)
                self.save(st)
                return True
            if actual == original:
                self.ls.cambc('submissions', 'activate', PROBE_ID, '--json', retries=0)
                return True
            if cur['selected'] != PROBE_VERSION or not cur['pinned'] or cur['active'] not in (prior['active'], PROBE_VERSION):
                return self.block(st, 'outside selection changed during v1 activation')
            if cur['active'] != PROBE_VERSION:
                return True
            if d['active']['id'] != PROBE_ID:
                return self.block(st, 'live v1 identity mismatch')
            st['phase'] = 'probing'
            self.save(st)
            self.event('v1-active', cycle=st['cycle'])
            return True
        if phase == 'probing':
            if actual != (PROBE_VERSION, PROBE_VERSION, True):
                return self.block(st, 'outside selection changed during probe; do not restore over it')
            if st.get('attempting'):
                return self.block(st, 'ambiguous group creation for ' + st['attempting'] + '; do not retry or spend more quota')
            for opp in ('mite', 'fish'):
                if opp in st['groups']:
                    continue
                q = self.ls.quota()
                if not q.get('ready', True) or (q.get('quota', {}).get('limit') or 100) - q.get('quota', {}).get('used', 0) < 1:
                    return True
                st['attempting'] = opp
                self.save(st)
                task = {'opp_id': self.ls.TEAMS[opp][0], 'games': st['fixture']}
                # Single create attempt, deliberately no --source-group.
                gid, output = self.ls.create(task, None, retries=0)
                st['groups'][opp] = {'id': gid, 'created': self.ls.now(), 'created_time': time.time(), 'response': output}
                st['attempting'] = None
                self.save(st)
                self.event('created', cycle=st['cycle'], opponent=opp, group=gid, pin=None)
                return True
            complete = True
            for opp, group in st['groups'].items():
                detail = self.ls.group_detail(group['id'])
                write_json(self.evidence / st['cycle'] / f'{opp}-group.json', detail)
                if not self.ls.group_done(detail):
                    complete = False
            if complete:
                st['phase'] = 'restoring'
                self.save(st)
            return True
        if phase == 'restoring':
            if actual == original:
                st['phase'] = 'analyze'
                self.save(st)
                self.marker.unlink(missing_ok=True)
                self.event('restored', cycle=st['cycle'], selection=prior)
                return True
            target = str(prior['selected']) if prior['pinned'] else 'latest'
            status = str(d['selected'].get('status', '')).lower()
            if cur['selected'] == prior['selected'] and ('fail' in status or 'error' in status):
                return self.block(st, 'saved submission failed to build during restoration: ' + status)
            if cur['active'] in (PROBE_VERSION, prior['active']) and cur['selected'] == PROBE_VERSION and cur['pinned']:
                self.ls.cambc('submissions', 'activate', target, '--json', retries=0)
                return True
            if cur['selected'] == prior['selected'] and cur['pinned'] == prior['pinned'] and cur['active'] == PROBE_VERSION:
                return True
            return self.block(st, 'outside selection changed during restoration; no overwrite')
        if phase == 'analyze':
            if actual != original:
                return self.block(st, 'outside selection changed after restoration')
            self.marker.unlink(missing_ok=True)
            self.analyze(st)
            return True
        raise ValueError('unknown version-check phase ' + phase)

    def analyze(self, st):
        if st.get('abort_reason'):
            self.wake(self.event('incomplete', reason=st['abort_reason'], cycle=st['cycle']))
        for opp, group in st['groups'].items():
            path = self.evidence / st['cycle']
            detail = json.loads((path / f'{opp}-group.json').read_text())
            rows = []
            for m in sorted(detail['matches'], key=lambda x: x['position']):
                if m['status'] != 'finished':
                    break
                fixture = st['fixture'][m['position'] - 1]
                us = next(x for x in m['teams'] if x['teamId'] == self.ls.MY_TEAM)
                if fixture['map_id'] != m['mapId'] or fixture['side'] != us['side']:
                    raise ValueError('probe fixture differs from returned game')
                raw = path / f"{opp}-{m['position']}.summary.bin"
                decoded = path / f"{opp}-{m['position']}.summary.json"
                if not raw.exists():
                    self.ls.cambc('matches', 'summary', m['matchId'], '-o', str(raw))
                if not decoded.exists():
                    write_json(decoded, json.loads(self.ls.cambc('summary', str(raw), '-o', '-')))
                d = json.loads(decoded.read_text())
                meta = {k: d['match'].get(k) for k in ('seed', 'engineVersion', 'engineBuildHash', 'mapHash')}
                rows.append({'map': m['map'], 'side': us['side'], 'hash': fingerprint(d), 'context': meta})
            if len(rows) != 5:
                self.wake(self.event('incomplete', opponent=opp, group=group['id'], cycle=st['cycle']))
                continue
            baseline = st.setdefault('baselines', {}).get(opp)
            record = {'group': group['id'], 'cycle': st['cycle'], 'games': rows}
            if baseline is None:
                self.event('calibrated', opponent=opp, **record)
            elif baseline['games'] != rows:
                changed = [r['map'] for a, r in zip(baseline['games'], rows) if a != r]
                context_changed = any(a['context'] != r['context'] for a, r in zip(baseline['games'], rows))
                self.wake(self.event('opponent-change-evidence', opponent=opp, previous=baseline['group'],
                                    changed_maps=changed, context_changed=context_changed,
                                    caveat='Behaviour change evidence, not proof of a submission version; engine, seed or nondeterminism can also differ. No repin queued.',
                                    **record))
            else:
                self.event('unchanged', opponent=opp, group=group['id'], cycle=st['cycle'])
            st['baselines'][opp] = record
            self.save(st)
        st.update(phase='idle', next_due=max(max((g['created_time'] for g in st['groups'].values()), default=st['started']) + INTERVAL, time.time()), last_completed=self.ls.now())
        self.save(st)
