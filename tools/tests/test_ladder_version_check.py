import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import ladder_version_check as vc
import ladder_scrims as ls
from ladder_coordination import probe_active


class Fake:
    TEAMS, MY_TEAM = ls.TEAMS, ls.MY_TEAM
    now = staticmethod(lambda: '2026-11-10T00:00:00Z')
    group_done = staticmethod(ls.group_done)
    append_jsonl = staticmethod(ls.append_jsonl)

    def __init__(self, path):
        self.DATA = path
        self.live, self.selected, self.pinned, self.newest = 106, 106, True, 106
        self.inflight = True
        self.calls, self.creates = [], []
        self.fail_create = False
        self.value = 0
        self.failed = False
        self.selected_status = "active"

    def state(self):
        return [], ({'old': {'group': 'old'}} if self.inflight else {}), {}, set(), {}

    def quota(self):
        return {'ready': True, 'quota': {'used': 80, 'limit': 100}}

    def cambc(self, *args, **kwargs):
        self.calls.append(args)
        if args[:2] == ('submissions', 'list'):
            return json.dumps({'active': {'version': self.live, 'id': vc.PROBE_ID if self.live == 1 else 'live-id'},
                               'selected': {'version': self.selected, 'status': self.selected_status}, 'pinned': self.pinned,
                               'submissions': [{'version': self.newest}]})
        if args[:2] == ('submissions', 'activate'):
            self.live = self.selected = 1 if args[2] == vc.PROBE_ID else self.newest if args[2] == 'latest' else int(args[2])
            self.pinned = args[2] != 'latest'
            self.selected_status = 'active'
            return '{}'
        if args[:2] == ('matches', 'summary'):
            Path(args[-1]).write_text('summary')
            return ''
        if args[0] == 'summary':
            return json.dumps({'match': {'seed': '1', 'engineVersion': '5', 'engineBuildHash': 'x',
                                        'mapHash': 'x', 'roundsCompleted': 30},
                               **{k: [] for k in ('roster','teams','championTimelines','teamTimelines','heatmaps')},
                               'events': [self.value]})
        raise AssertionError(args)

    def create(self, task, source, retries):
        assert source is None and retries == 0
        self.creates.append(task)
        if self.fail_create:
            raise ls.CambcError('response lost after server accepted create')
        return str(len(self.creates)), '{}'

    def group_detail(self, gid):
        fixture = self.creates[int(gid) - 1]['games']
        return {'matches': [{'position': i + 1, 'status': 'failed' if self.failed else 'finished',
                             'map': f['map'], 'mapId': f['map_id'], 'matchId': str(i),
                             'teams': [{'teamId': self.MY_TEAM, 'side': f['side']}]} for i, f in enumerate(fixture)]}


class Tests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.p = Path(self.tmp.name)
        self.fake = Fake(self.p)
        self.alerts = []
        self.c = vc.VersionCheck(self.fake, self.p, lambda _: None, self.alerts.append)
        self.fixture = [{'map': str(i), 'map_id': str(i), 'side': 'ab'[i % 2]} for i in range(5)]
        vc.write_json(self.c.file, {'enabled': True, 'phase': 'idle', 'next_due': 0,
                                  'probe_id': vc.PROBE_ID, 'probe_version': 1, 'fixture': self.fixture})
        self.scheduler = {'history': [{'version': 106}]}
        self.p.joinpath('refsets.json').write_text('{"fish":"r2","mite":"r5"}')

    def tearDown(self):
        self.tmp.cleanup()

    def tick(self):
        return self.c.tick(self.scheduler)

    def state(self):
        return json.loads(self.c.file.read_text())

    def finish(self):
        for _ in range(16):
            self.tick()
            if self.state()['phase'] == 'idle':
                return
        self.fail(self.state())

    def test_drain_two_groups_restore_calibrate(self):
        self.tick()
        self.assertTrue(probe_active(self.p))
        self.tick()
        self.assertEqual(self.fake.live, 106)
        self.assertFalse(self.fake.creates)
        self.fake.inflight = False
        self.finish()
        self.assertEqual((self.fake.live, self.fake.selected, self.fake.pinned), (106, 106, True))
        self.assertEqual(len(self.fake.creates), 2)
        self.assertEqual([x['games'] for x in self.fake.creates], [self.fixture] * 2)
        self.assertFalse(probe_active(self.p))
        self.assertEqual(set(self.state()['baselines']), {'fish', 'mite'})
        self.assertFalse(self.alerts)
        self.assertFalse(self.tick())
        self.assertEqual(self.p.joinpath('refsets.json').read_text(), '{"fish":"r2","mite":"r5"}')

    def test_restore_latest_mode(self):
        self.fake.pinned = False
        self.fake.inflight = False
        self.finish()
        self.assertFalse(self.fake.pinned)
        self.assertIn(('submissions', 'activate', 'latest', '--json'), self.fake.calls)

    def test_outside_selection_not_overwritten(self):
        self.fake.inflight = False
        self.tick(); self.tick(); self.tick()
        self.assertEqual(self.fake.live, 1)
        self.fake.live = self.fake.selected = self.fake.newest = 107
        n = len(self.fake.calls)
        self.tick()
        self.assertEqual(self.state()['phase'], 'blocked')
        self.assertEqual(self.fake.live, 107)
        self.assertFalse(any(c[:2] == ('submissions','activate') for c in self.fake.calls[n:]))
        self.assertEqual(len(self.alerts), 1)

    def test_restart_after_activation_reconciles(self):
        self.fake.inflight = False
        self.tick(); self.tick()
        self.assertEqual(self.state()['phase'], 'activating')
        self.assertEqual(self.fake.live, 1)
        self.c = vc.VersionCheck(self.fake, self.p, lambda _: None, self.alerts.append)
        self.finish()
        self.assertEqual(sum(x[:3] == ('submissions','activate',vc.PROBE_ID) for x in self.fake.calls), 1)

    def test_ambiguous_creation_never_retried(self):
        self.fake.inflight = False
        self.tick(); self.tick(); self.tick()
        self.fake.fail_create = True
        with self.assertRaises(ls.CambcError):
            self.tick()
        self.tick(); self.tick()
        self.assertEqual(len(self.fake.creates), 1)
        self.assertEqual(self.state()['phase'], 'blocked')
        self.assertTrue(probe_active(self.p))

    def test_unchanged_then_change_notifies_only_change(self):
        self.fake.inflight = False
        self.finish()
        for value in (0, 1):
            st = self.state(); st['next_due'] = 0; self.c.save(st)
            self.fake.value = value
            self.finish()
            self.assertEqual(len(self.alerts), value * 2)
        self.assertTrue(all(a['event'] == 'opponent-change-evidence' for a in self.alerts))
        self.assertFalse(any(a['context_changed'] for a in self.alerts))

    def test_failed_games_restore_without_baseline(self):
        self.fake.inflight = False
        self.fake.failed = True
        self.finish()
        self.assertEqual(self.fake.live, 106)
        self.assertFalse(self.state().get('baselines'))
        self.assertEqual(len(self.alerts), 2)

    def test_failed_v1_build_restores_without_groups(self):
        self.fake.inflight = False
        self.tick(); self.tick()
        self.fake.live = 106
        self.fake.selected_status = 'failed'
        self.finish()
        self.assertEqual((self.fake.live, self.fake.selected), (106, 106))
        self.assertFalse(self.fake.creates)
        self.assertFalse(probe_active(self.p))
        self.assertEqual(len(self.alerts), 1)
        self.assertEqual(self.alerts[0]['event'], 'incomplete')

    def test_slow_v1_build_is_not_failure(self):
        self.fake.inflight = False
        self.tick(); self.tick()
        self.fake.live = 106
        self.fake.selected_status = 'queued'
        self.tick(); self.tick()
        self.assertEqual(self.state()['phase'], 'activating')
        self.assertFalse(self.fake.creates)
        self.assertFalse(self.alerts)

    def test_restore_build_failure_alerts(self):
        self.fake.inflight = False
        for _ in range(10):
            self.tick()
            if self.state()['phase'] == 'restoring':
                break
        self.fake.live, self.fake.selected = 1, 106
        self.fake.selected_status = 'failed'
        self.tick()
        self.assertEqual(self.state()['phase'], 'blocked')
        self.assertEqual(len(self.alerts), 1)

    def test_disabled_midcycle_still_restores(self):
        self.fake.inflight = False
        self.tick(); self.tick(); self.tick()
        st = self.state(); st['enabled'] = False; self.c.save(st)
        self.finish()
        self.assertEqual(self.fake.live, 106)
        self.assertFalse(self.tick())

    def test_restore_crash_is_idempotent(self):
        self.fake.inflight = False
        for _ in range(10):
            self.tick()
            if self.state()['phase'] == 'restoring':
                break
        self.tick()
        self.assertEqual(self.fake.live, 106)
        self.c = vc.VersionCheck(self.fake, self.p, lambda _: None, self.alerts.append)
        self.finish()
        self.assertEqual(sum(x[:3] == ('submissions','activate','106') for x in self.fake.calls), 1)

    def test_shared_lock_excludes_other_process(self):
        import subprocess
        from ladder_coordination import live_lock
        script = "import fcntl,sys; f=open(sys.argv[1],'a'); fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB)"
        args = [sys.executable, '-c', script, str(self.p / 'live-switch.lock')]
        with live_lock(self.p):
            self.assertNotEqual(subprocess.run(args, capture_output=True).returncode, 0)
        self.assertEqual(subprocess.run(args, capture_output=True).returncode, 0)

    def test_holds_and_quota_do_not_switch(self):
        self.p.joinpath('PAUSE').touch()
        self.assertFalse(self.tick())
        self.assertFalse(probe_active(self.p))
        self.p.joinpath('PAUSE').unlink()
        self.fake.quota = lambda: {'quota': {'used': 99, 'limit': 100}}
        self.assertFalse(self.tick())
        self.assertEqual(self.fake.live, 106)


if __name__ == '__main__':
    unittest.main()
