"""Campaign recovery and exact evidence scope, without remote calls or builds."""
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import live_sched as sched
from live_r6_campaign import Campaign, REQUIRED, SOURCES, sha


class CampaignTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.h = Path(self.tmp.name)
        self.s = SimpleNamespace(H=self.h, save=Mock(), log=Mock(), wake=Mock(), hold=Mock(),
                                 now=lambda: 'now', submissions_json=Mock(), sh=Mock(return_value=(0, 'ok')),
                                 ls=SimpleNamespace(TEAMS=sched.ls.TEAMS, CambcError=sched.ls.CambcError), plan_gate=Mock())
        self.c = Campaign(self.s, Mock())
        self.plan = {'id': 'bridge113-r6-main506', 'submission_note': 'unique506'}
        self.path = self.h / 'r6-campaign.json'
        self.path.write_text(json.dumps(self.plan))
        self.st = {'history': [], 'reported': [], 'r6_campaign': {
            'phase': 'activate113', 'plan_sha256': sha(self.path)}}
        self.valid = patch.object(self.c, 'validate', return_value=({}, {'workspace': str(self.h)}))
        self.valid.start()
        self.addCleanup(self.valid.stop)

    def platform(self, live, selected=None, rows=()):
        self.s.submissions_json.return_value = {'active': {'version': live},
            'selected': {'version': live if selected is None else selected}, 'submissions': list(rows)}

    def test_absent_plan_keeps_ordinary_scheduler(self):
        self.path.unlink()
        self.assertFalse(self.c.tick({}))
        self.s.sh.assert_not_called()

    def test_activation_reuses113_and_waits_without_upload(self):
        self.platform(114)
        self.c.tick(self.st)
        self.assertEqual(self.s.sh.call_args.args[0], ['cambc', 'submissions', 'activate', '113'])
        self.platform(114, 113)
        self.s.sh.reset_mock()
        self.c.tick(self.st)
        self.s.sh.assert_not_called()
        self.platform(113)
        self.c.tick(self.st)
        self.assertEqual(self.st['r6_campaign']['phase'], 'bridge')

    def test_outside_selection_fails_closed(self):
        self.platform(115)
        self.c.tick(self.st)
        self.s.hold.assert_called_once()
        self.s.sh.assert_not_called()

    def test_read_only_rate_limit_waits_without_hold(self):
        self.s.submissions_json.side_effect = sched.ls.CambcError('HTTP429')
        self.c.tick(self.st)
        self.s.hold.assert_not_called()
        self.s.sh.assert_not_called()

    def test_bridge_only_plans_mite_r6_and_ignores_reported113(self):
        self.st['r6_campaign']['phase'] = 'bridge'
        self.st['reported'] = [113]
        self.platform(113)
        with patch.object(self.c, 'progress', return_value=True):
            self.c.tick(self.st)
        self.s.plan_gate.assert_called_once_with(113, {'mite': 'r6'})
        self.assertEqual(self.st['r6_campaign']['phase'], 'upload506')
        self.assertEqual(self.s.wake.call_args.args[0]['groups'], 52)

    def test_interrupted_upload_never_reuploads(self):
        self.st['r6_campaign'].update(phase='upload_intent', upload_note='unique506')
        self.platform(113)
        self.c.tick(self.st)
        self.s.hold.assert_called_once()
        self.s.sh.assert_not_called()

    def test_uploaded_inactive_version_recovered_by_exact_note(self):
        self.st['r6_campaign'].update(phase='upload_intent', upload_note='unique506')
        self.platform(113, rows=[{'version': 115, 'note': 'unique506', 'status': 'inactive'}])
        self.c.tick(self.st)
        self.assertEqual(self.st['r6_campaign']['phase'], 'activate506')
        self.assertEqual(self.st['r6_campaign']['version506'], 115)
        self.s.sh.assert_not_called()

    def test_slow_build_waits_failed_build_holds(self):
        self.st['r6_campaign'].update(phase='wait506', upload_note='unique506')
        for status in ('queued', 'building'):
            self.platform(113, rows=[{'version': 115, 'note': 'unique506', 'status': status}])
            self.c.tick(self.st)
            self.assertEqual(self.st['r6_campaign']['phase'], 'wait506')
            self.s.hold.assert_not_called()
        self.platform(113, rows=[{'version': 115, 'note': 'unique506', 'status': 'failed'}])
        self.c.tick(self.st)
        self.s.hold.assert_called_once()

    def test_full_collection_exact_scope_and_context(self):
        tid = sched.ls.TEAMS['mite'][0]
        tasks, created, finished, rows = [], {}, {}, []
        (self.h / 'replay.zip').touch()
        for i in range(52):
            t = {'id': str(i), 'version': 113, 'purpose': 'set', 'part': 'core', 'pin': 'ref',
                 'refset': 'r6', 'opp_id': tid}
            tasks.append(t)
            created[str(i)] = {'group': str(i), 'live': 113, 'selected': 113, 'source_group': SOURCES['mite']}
            finished[str(i)] = {}
            for j in range(5):
                n = 5*i+j
                rows.append({'group': str(i), 'position': j+1, 'status': 'finished', 'result': 'win',
                             'replay': 'replay.zip', 'opp_id': tid, 'map': str(n//2),
                             'side': 'ab'[n%2], 'filler': n >= 256})
        tasks.append(dict(tasks[0], id='old', refset='r5'))
        self.s.ls.state = Mock(return_value=(tasks, created, finished, set(), {}))
        self.s.ls.DATA = self.s.ls.ROOT = self.h
        self.s.ls.read_jsonl = Mock(return_value=rows)
        self.s.ls.suspect_groups = Mock(return_value=set())
        self.assertTrue(self.c.progress(113, {'mite': 'r6'}))
        created['0']['source_group'] = 'old-r5'
        with self.assertRaisesRegex(ValueError, 'snapshot'):
            self.c.progress(113, {'mite': 'r6'})

    def test_required_r6_blocks_before_any_api_or_fallback(self):
        candidate = {'required_refsets': REQUIRED, 'required_sources': SOURCES, 'opponents': ['mite']}
        with patch.object(sched, 'refsets', return_value={'fish': 'r2', 'mite': 'r5'}), \
                patch.object(sched.ls, 'state') as state:
            with self.assertRaises(ValueError):
                sched.gate_refsets(candidate)
            state.assert_not_called()


if __name__ == '__main__':
    unittest.main()
