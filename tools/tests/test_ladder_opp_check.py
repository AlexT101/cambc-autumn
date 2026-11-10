"""No API calls or live mutations: rolling detector, recovery and report isolation."""
import copy
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import ladder_opp_check as oc
import ladder_scrims as ls
import live_sched as sched


class Fake:
    TEAMS = {'fish': ('F', 'Fish'), 'mite': ('M', 'Mite')}
    DATA = Path('/fixture')

    def __init__(self):
        self.tasks = []; self.created = {}; self.finished = {'pin-F': {}, 'pin-M': {}}
        self.dropped = set(); self.bad = set(); self.rows = []
        self.refs = {('r2', 'F'): 'pin-F', ('r5', 'M'): 'pin-M'}

    def state(self):
        return self.tasks, self.created, self.finished, self.dropped, self.refs

    def suspect_groups(self): return self.bad
    def read_jsonl(self, path): return self.rows
    def append_jsonl(self, path, task): self.tasks.append(copy.deepcopy(task))

    def core(self, version):
        for opp, ref in [('fish', 'r2'), ('mite', 'r5')]:
            oid, name = self.TEAMS[opp]
            self.tasks.append({'id': f'v{version}-{opp}-01', 'version': version, 'opp_id': oid, 'opp_name': name,
                'purpose': 'set', 'part': 'core', 'pin': 'ref', 'refset': ref, 'order': 1,
                'games': [{'map': f'm{i}', 'map_id': f'id{i}', 'side': 'ab'[i % 2]} for i in range(5)]})

    def complete(self, tid, score=100, engine='engine-a'):
        t = next(t for t in self.tasks if t['id'] == tid); group = 'group-' + tid
        source = self.refs[(t['refset'], t['opp_id'])] if t['pin'] == 'ref' else None if t['pin'] == 'none' else t['pin']
        self.created[tid] = {'group': group, 'live': t['version'], 'selected': t['version'], 'source_group': source,
                             'opp_id': t['opp_id'], 'at': '2026-11-10T22:00:00Z'}
        self.finished[group] = {}
        for i, g in enumerate(t['games'], 1):
            self.rows.append(dict(g, task=tid, group=group, version=t['version'], opp_id=t['opp_id'], opp_name=t['opp_name'],
                purpose=t['purpose'], refset=t['refset'], pin=t['pin'], source_group=source, position=i,
                match=f'{group}-{i}', status='finished', result='win', rounds=200, our_gems=score, opp_gems=50,
                our_kills=1, opp_kills=0, our_picks=['Ryth'], opp_picks=['Prism'], engine='3.0.0', engine_hash=engine, seed=f'seed-{i}'))
        return group


class DetectorTests(unittest.TestCase):
    def setUp(self):
        self.fake = Fake(); self.st = {'opp_checks': {}}; self.saved = []; self.logs = []; self.wakes = []
        self.detector = oc.OpponentDetector(self.fake, lambda s: self.saved.append(copy.deepcopy(s)), self.logs.append,
                                           self.wakes.append, lambda: '2026-11-10T23:00:00Z')
        self.rsets = {'fish': 'r2', 'mite': 'r5'}

    def tick(self, v): return self.detector.tick(self.st, v, self.rsets)

    def first_change(self):
        self.fake.core(1); self.tick(1)
        for opp in ('fish', 'mite'):
            self.fake.complete(f'v1-{opp}-01')
            self.fake.complete(f'v1-{opp}-01-cur', 101 if opp == 'mite' else 100)
        self.tick(1)

    def test_successive_changes_advance_snapshot_unchanged_keeps_it(self):
        self.first_change()
        first = self.st['opp_detector']['snapshots']['mite']['source_group']
        self.assertEqual(first, 'group-v1-mite-01-cur'); self.assertEqual(len(self.wakes), 1)
        self.fake.core(2); self.tick(2)
        m = self.st['opp_detector']['runs']['2-mite']; f = self.st['opp_detector']['runs']['2-fish']
        self.assertEqual(m['snapshot_group'], first); self.assertEqual(m['baseline_task'], 'v2-mite-01-observed')
        self.assertEqual(f['baseline_task'], 'v2-fish-01')
        for opp, score in [('fish', 350), ('mite', 490)]:
            run = self.st['opp_detector']['runs'][f'2-{opp}']
            self.fake.complete(run['baseline_task'], score); self.fake.complete(run['current_task'], score)
        self.tick(2)
        self.assertEqual(self.st['opp_detector']['snapshots']['mite']['source_group'], first)
        self.assertEqual(len(self.wakes), 1)  # Changed own bot did not create a false opponent change.
        self.fake.core(3); self.tick(3)
        run = self.st['opp_detector']['runs']['3-mite']
        self.fake.complete(run['baseline_task'], 600); self.fake.complete(run['current_task'], 601); self.tick(3)
        self.assertEqual(self.st['opp_detector']['snapshots']['mite']['generation'], 2)
        self.assertEqual(self.st['opp_detector']['snapshots']['mite']['source_group'], 'group-v3-mite-01-cur')
        self.assertEqual(len(self.wakes), 2); self.tick(3); self.assertEqual(len(self.wakes), 2)
        self.assertEqual(self.fake.refs, {('r2', 'F'): 'pin-F', ('r5', 'M'): 'pin-M'})
        for t in self.fake.tasks:
            if t['purpose'] == 'oppcheck':
                self.assertIsNone(t['refset']); self.assertFalse(t['is_ref'])

    def test_bootstrap_latest_valid_legacy_is_not_new_change(self):
        for version in (110, 112):
            self.fake.core(version)
            for opp in ('fish', 'mite'):
                base = next(t for t in self.fake.tasks if t['id'] == f'v{version}-{opp}-01')
                cur = dict(base, id=base['id'] + '-cur', purpose='oppcheck', pin='none', refset=None)
                self.fake.tasks.append(cur); self.fake.complete(base['id']); self.fake.complete(cur['id'], 101 if opp == 'mite' else 100)
                self.st['opp_checks'][cur['id']] = {'changed': opp == 'mite'}
        before = len(self.fake.tasks); self.tick(112)
        self.assertEqual(len(self.fake.tasks), before); self.assertFalse(self.wakes)
        self.assertEqual(self.st['opp_detector']['snapshots']['mite']['source_group'], 'group-v112-mite-01-cur')
        self.assertEqual(self.st['opp_detector']['snapshots']['fish']['source_group'], 'pin-F')
        self.assertFalse(self.st['opp_detector']['runs'])

    def test_partial_planning_recovers_without_duplicate_tasks(self):
        self.fake.core(1)
        real = self.fake.append_jsonl
        def interrupted(path, task):
            real(path, task)
            raise OSError('crash after append')
        with patch.object(self.fake, 'append_jsonl', side_effect=interrupted):
            with self.assertRaises(OSError): self.tick(1)
        self.tick(1); self.tick(1)
        ids = [t['id'] for t in self.fake.tasks]
        self.assertEqual(len(ids), len(set(ids))); self.assertEqual(len(ids), 4)

    def test_historical_arm_core_does_not_reset_rolling_snapshot(self):
        self.first_change()
        snapshot = copy.deepcopy(self.st['opp_detector']['snapshots']['mite'])
        self.fake.refs['r3', 'M'] = 'historical-r3'
        self.fake.finished['historical-r3'] = {}
        self.fake.core(2)
        core = next(t for t in self.fake.tasks if t['id'] == 'v2-mite-01')
        core['refset'] = 'r3'
        self.tick(2)  # Global defaults still say r5.
        run = self.st['opp_detector']['runs']['2-mite']
        self.assertEqual(run['testing_refset'], 'r3')
        self.assertEqual(run['testing_source'], 'historical-r3')
        self.assertEqual(run['snapshot_group'], snapshot['source_group'])
        self.assertEqual(run['baseline_task'], 'v2-mite-01-observed')
        self.assertEqual(run['task_specs'][0]['pin'], snapshot['source_group'])
        self.assertTrue(all(t['purpose'] == 'oppcheck' and t['refset'] is None for t in run['task_specs']))
        self.fake.complete(run['baseline_task'], 700)
        self.fake.complete(run['current_task'], 700)
        self.tick(2)
        self.assertEqual(self.st['opp_detector']['snapshots']['mite'], snapshot)
        self.assertEqual(self.rsets['mite'], 'r5')
        self.assertEqual(core['refset'], 'r3')

    def test_ambiguous_core_refs_hold_and_dropped_cores_are_excluded(self):
        for dropped in (False, True):
            with self.subTest(dropped=dropped):
                self.setUp(); self.fake.core(1)
                old = next(t for t in self.fake.tasks if t['id'] == 'v1-mite-01')
                self.fake.tasks.append(dict(old, id='v1-mite-r3-01', refset='r3'))
                self.fake.refs['r3', 'M'] = 'historical-r3'; self.fake.finished['historical-r3'] = {}
                if dropped: self.fake.dropped.add(old['id'])
                self.tick(1)
                run = self.st['opp_detector']['runs']['1-mite']
                if dropped:
                    self.assertEqual(run['status'], 'pending')
                    self.assertEqual(run['testing_refset'], 'r3')
                else:
                    self.assertEqual(run['status'], 'held')
                    self.assertEqual(run['refsets'], ['r3', 'r5'])
                    self.assertFalse(any(t['purpose'] == 'oppcheck' and t['opp_id'] == 'M' for t in self.fake.tasks))
                    self.fake.complete('v1-fish-01'); self.fake.complete('v1-fish-01-cur')
                    self.assertTrue(self.tick(1))  # Keep the scheduler from switching away from the held comparison.

    def test_invalid_context_never_advances(self):
        for mode in ('suspect', 'engine', 'source', 'version', 'side', 'metric', 'duplicate', 'duplicate-match', 'seed', 'missing-seed', 'failed'):
            with self.subTest(mode=mode):
                self.setUp(); self.fake.core(1); self.tick(1)
                self.fake.complete('v1-mite-01'); group = self.fake.complete('v1-mite-01-cur', 999)
                row = self.fake.rows[-1]
                if mode == 'suspect': self.fake.bad.add(group)
                if mode == 'engine': row['engine_hash'] = 'different'
                if mode == 'source': row['source_group'] = 'other'
                if mode == 'version': row['version'] = 2
                if mode == 'side': row['side'] = 'b' if row['side'] == 'a' else 'a'
                if mode == 'metric': row.pop('rounds')
                if mode == 'duplicate': self.fake.rows.append(dict(row, our_gems=42))
                if mode == 'duplicate-match': self.fake.rows.append(dict(row, match='another-match'))
                if mode == 'seed': row['seed'] = 'different-seed'
                if mode == 'missing-seed': row.pop('seed')
                if mode == 'failed': row['status'] = 'failed'
                self.tick(1)
                self.assertEqual(self.st['opp_detector']['runs']['1-mite']['status'], 'invalid')
                self.assertNotIn('mite', self.st['opp_detector']['snapshots']); self.assertFalse(self.wakes)

    def test_partial_rows_wait_and_exact_duplicate_is_harmless(self):
        self.fake.core(1); self.tick(1); self.fake.complete('v1-mite-01'); self.fake.complete('v1-mite-01-cur', 101)
        last = self.fake.rows.pop(); self.tick(1)
        self.assertEqual(self.st['opp_detector']['runs']['1-mite']['status'], 'pending'); self.assertFalse(self.wakes)
        self.fake.rows.extend([last, dict(last)]); self.tick(1); self.assertEqual(len(self.wakes), 1)

    def test_notification_failure_keeps_durable_outbox(self):
        self.fake.core(1); self.tick(1); self.fake.complete('v1-mite-01'); self.fake.complete('v1-mite-01-cur', 101)
        with patch.object(self.detector, 'wake', side_effect=OSError('notification unavailable')):
            with self.assertRaises(OSError): self.tick(1)
        event = next(iter(self.st['opp_detector']['outbox'].values()))
        self.assertFalse(event['delivered']); self.assertEqual(self.st['opp_detector']['snapshots']['mite']['generation'], 1)
        self.tick(1); self.assertTrue(event['delivered']); self.assertEqual(len(self.wakes), 1)


class IntegrationTests(unittest.TestCase):
    def test_wake_journal_recovery_deduplicates_event_id(self):
        with tempfile.TemporaryDirectory() as td, patch.object(sched, 'HAND', Path(td)):
            rec = {'event_id': 'opp-observation-113-mite', 'changed': True}
            sched.wake(rec); sched.wake(rec)
            self.assertEqual(len(ls.read_jsonl(Path(td) / 'parked/live-gate.ready')), 1)

    def test_pair_report_excludes_both_detector_arms(self):
        base = {'opp_id': 'M', 'opp_name': 'Mite', 'map': 'm', 'side': 'a', 'result': 'win', 'refset': 'r5', 'purpose': 'set'}
        rows = [base, dict(base, refset=None, purpose='oppcheck')]
        with patch.object(ls, 'games', return_value=rows), patch('sys.stdout', new_callable=io.StringIO) as out:
            ls.cmd_pair(type('Args', (), {'versions': [1, 2]})())
        self.assertIn('1 paired games', out.getvalue())


if __name__ == '__main__': unittest.main()
