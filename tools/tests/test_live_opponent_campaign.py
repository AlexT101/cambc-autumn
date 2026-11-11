"""Lightweight fixed-panel protocol, first-capture and observation recovery tests."""
import copy
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import ladder_scrims as ls
from ladder_opp_check import OpponentDetector
from live_panel_evidence import paired, needs_discernment
from live_panel_observations import tick as observe
from live_opponent_campaign import Panel
from live_r6_campaign import sha
from test_ladder_opp_check import Fake


class PairedTests(unittest.TestCase):
    def data(self):
        tasks, created, finished, rows = [], {}, {}, []
        for v in (113, 115):
            for n in range(256):
                tid = f'{v}-{n}'; gid = 'capture' if v == 113 and n == 0 else tid
                first = gid == 'capture'
                tasks.append({'id': tid})
                created[tid] = {'group': gid, 'live': v, 'selected': v, 'opp_id': 'F',
                                'source_group': None if first else 'capture', 'is_ref': first}
                finished[gid] = {}
                rows.append({'version': v, 'opp_id': 'F', 'refset': 'panel-F', 'purpose': 'set',
                    'task': tid, 'group': gid, 'status': 'finished', 'result': 'win' if n % 3 else 'loss',
                    'engine': '5.0.1', 'engine_hash': 'same', 'seed': str(n), 'map_id': str(n//2),
                    'side': 'ab'[n%2], 'our_picks': ['different-draft' if v == 115 else 'original'],
                    'opp_picks': ['response' if v == 115 else 'original']})
        fake = SimpleNamespace(DATA=Path('/unused'), state=lambda: (tasks, created, finished, set(), {}),
                               suspect_groups=lambda: set(), read_jsonl=lambda _: rows)
        return fake, rows

    def test_draft_changes_kept_and_first_unpinned_capture_has_effective_pin(self):
        fake, _ = self.data()
        r = paired(fake, 113, 115, 'F', 'capture', 'panel-F')
        self.assertEqual(r['cells'], 256)
        self.assertEqual(r['draft_changes_descriptive_only'], {'ours': 256, 'opponent': 256})
        self.assertEqual(r['gain'], 0)
        self.assertTrue(r['zero_discordance'])
        self.assertIn('not proof of zero uncertainty', r['uncertainty'])
        self.assertTrue(needs_discernment(r,r))

    def test_wrong_seed_or_incomplete_panel_never_triggers(self):
        fake, rows = self.data()
        rows[-1]['seed'] = 'changed'
        with self.assertRaisesRegex(ValueError, 'seed'): paired(fake, 113, 115, 'F', 'capture', 'panel-F')
        rows.pop()
        with self.assertRaisesRegex(ValueError, 'complete256'): paired(fake, 113, 115, 'F', 'capture', 'panel-F')

    def test_prospective_close_condition(self):
        plus = {'gain': .05, 'ci95': [.01, .09]}
        minus = {'gain': -.05, 'ci95': [-.09, -.01]}
        unclear = {'gain': .01, 'ci95': [-.02, .04]}
        self.assertFalse(needs_discernment(plus, plus))
        self.assertFalse(needs_discernment(minus, minus))
        self.assertTrue(needs_discernment(plus, minus))
        self.assertTrue(needs_discernment(plus, unclear))


class ObservationTests(unittest.TestCase):
    def setUp(self):
        self.fake = Fake(); self.fake.core(113)
        self.st = {'opp_detector': {'snapshots': {o: {'source_group': 'pin-'+k, 'generation': 0}
                    for o, k in [('fish', 'F'), ('mite', 'M')]}, 'runs': {}, 'outbox': {}, 'migration': {'observations': []}}}
        self.det = OpponentDetector(self.fake, lambda _: None, lambda _: None, lambda _: None, lambda: 'now')
        self.refs = copy.deepcopy(self.fake.refs)
        self.st['panel_observations'] = {'next_due': 3600, 'epochs': 0, 'campaign': 'panel'}

    def tick(self, at=3600, allow=True, live=113):
        return observe(self.det, self.st, live, 'panel', allow, at, {'fish': 'r2', 'mite': 'r5'})

    def complete(self):
        for run in self.st['opp_detector']['runs'].values():
            if run['status'] == 'pending':
                self.fake.complete(run['baseline_task'])
                self.fake.complete(run['current_task'])

    def test_hourly_repeat_same_own_version_distinct_ids_no_pin_changes(self):
        self.assertTrue(self.tick())
        self.assertEqual(len(self.fake.tasks), 6)  # two existing fixtures plus four observation groups
        self.complete(); self.assertFalse(self.tick(7199))
        self.assertTrue(self.tick(7200))
        self.assertEqual(len(self.fake.tasks), 10)
        self.assertEqual(len({t['id'] for t in self.fake.tasks}), 10)
        self.assertEqual(self.fake.refs, self.refs)
        self.assertTrue(all(t['purpose']=='oppcheck' for t in self.fake.tasks[2:]))

    def test_intent_before_append_repairs_without_duplicate_epoch(self):
        real = self.fake.append_jsonl
        def interrupted(path, task):
            real(path, task); raise OSError('interrupted append')
        with patch.object(self.fake, 'append_jsonl', side_effect=interrupted):
            with self.assertRaises(OSError): self.tick()
        self.tick(); self.tick()
        self.assertEqual(self.st['panel_observations']['epochs'], 1)
        self.assertEqual(len(self.fake.tasks), 6)

    def test_cannot_switch_own_version_with_pending_observations(self):
        self.tick()
        with self.assertRaisesRegex(ValueError, 'switched'): self.tick(10, False, 115)

    def test_no_new_observation_during_phase_drain(self):
        self.assertFalse(self.tick(5000, False))
        self.assertEqual(len(self.fake.tasks), 2)

    def test_first_observation_waits_an_hour_after_panel_start(self):
        del self.st['panel_observations']
        self.assertFalse(self.tick(0))
        self.assertFalse(self.tick(3599))
        self.assertTrue(self.tick(3600))
        self.assertEqual(len(self.fake.tasks), 6)


class FirstCaptureTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.h = Path(self.tmp.name); (self.h/'rep.zip').touch()
        self.fake = Fake(); self.fake.ROOT = self.h
        maps = [{'name': str(i), 'id': str(i)} for i in range(128)]
        self.fake.load_set = lambda _: {'core': maps[:40], 'ext': maps[40:]}
        self.fake.set_groups = ls.set_groups
        self.s = SimpleNamespace(ls=self.fake, save=Mock(), now=lambda: 'now')
        self.panel = Panel(self.s, None)
        self.plan = {'id': 'panel'}
        self.entry = {'team_id': 'NEW', 'name': 'New opponent', 'refset': 'panel-new'}
        self.st = {'live_panel': {'sources': {}, 'captures': {}}}

    def test_only_first_capture_planned_before_validating_snapshot(self):
        self.assertFalse(self.panel.team(self.st, self.plan, self.entry, 113, True, {('3.0.0','engine-a')}))
        self.assertEqual(len(self.fake.tasks), 1)
        first = self.fake.tasks[0]; tid=first['id']; group='capture'
        # Model runner's first pin=ref creation: it becomes the source itself.
        self.fake.refs['panel-new', 'NEW'] = group
        self.fake.complete(tid)
        oldgroup = self.fake.created[tid]['group']
        self.fake.created[tid].update(group=group, source_group=None, is_ref=True)
        self.fake.finished[group] = {}; self.fake.finished.pop(oldgroup)
        for r in self.fake.rows:
            r.update(group=group, source_group=None, replay='rep.zip')
        self.assertFalse(self.panel.team(self.st, self.plan, self.entry, 113, True, {('3.0.0','engine-a')}))
        self.assertEqual(self.st['live_panel']['sources']['NEW'], group)
        self.assertEqual(len(self.fake.tasks), 52)
        self.assertEqual(sum(t['pin']=='ref' for t in self.fake.tasks), 1)
        self.assertTrue(all(t['pin']==group for t in self.fake.tasks[1:]))

    def test_preexisting_unrelated_reference_fails_without_extra_tasks(self):
        self.fake.refs['panel-new','NEW']='someone-elses-source'
        with self.assertRaisesRegex(ValueError,'namespace'):
            self.panel.team(self.st, self.plan, self.entry, 113, True, {('3.0.0','engine-a')})
        self.assertEqual(self.fake.tasks, [])


class PanelControlTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.h = Path(self.tmp.name)
        self.plan = {'id': 'panel', 'tranches': [[1,2,3],[4,5,6],[7,8,9],[10,11,12],[13,14]],
                     'fixed_entries': [{'team_id': str(i), 'name': str(i), 'rank_at_design': i+4,
                                        'refset': 'r'+str(i)} for i in range(14)]}
        (self.h/'live-panel.json').write_text(json.dumps(self.plan))
        self.platform_version = 115
        self.rows = [{'version': v, 'id': 'uuid'+str(v), 'status': 'inactive'} for v in (113,115)]
        self.fake = SimpleNamespace(DATA=self.h, live_lock=ls.live_lock, CambcError=ls.CambcError,
                                    state=Mock(return_value=([],{}, {}, set(), {})))
        self.s = SimpleNamespace(H=self.h, ls=self.fake, save=Mock(), hold=Mock(), log=Mock(), wake=Mock(),
            now=lambda:'now', sh=Mock(side_effect=self.activate), submissions_json=Mock(side_effect=self.platform))
        self.p = Panel(self.s, Mock())
        self.st = {'r6_campaign': {'phase':'done', 'version506':115}}
        self.result = {'gain': .01, 'ci95': [-.01,.03], 'engine_contexts': [('5.0.1','engine')]}
        self.team_calls = []
        self.validate_patch=patch.object(Panel,'validate');self.validation=self.validate_patch.start();self.addCleanup(self.validate_patch.stop)
        self.primary_patch=patch.object(Panel,'primary',return_value={'fish':self.result,'mite':self.result})
        self.primary=self.primary_patch.start();self.addCleanup(self.primary_patch.stop)
        self.team_patch=patch.object(Panel,'team',side_effect=self.team);self.team_patch.start();self.addCleanup(self.team_patch.stop)
        self.obs_patch=patch('live_opponent_campaign.observations',return_value=False)
        self.obs=self.obs_patch.start();self.addCleanup(self.obs_patch.stop)
        self.pair_patch=patch('live_opponent_campaign.paired',return_value=self.result)
        self.pair_patch.start();self.addCleanup(self.pair_patch.stop)

    def platform(self):
        return {'active':{'version':self.platform_version},'selected':{'version':self.platform_version},
                'submissions':self.rows}

    def activate(self, argv):
        self.platform_version=int(argv[-1]); return 0,'activated'

    def team(self, st, plan, entry, version, baseline, engines):
        self.team_calls.append((entry['team_id'],version,baseline))
        st['live_panel']['sources'][entry['team_id']]='capture'+entry['team_id']
        return True

    def test_clear_primary_does_not_plan_or_select(self):
        r=dict(self.result,gain=.05,ci95=[.01,.09])
        self.primary.return_value={'fish':r,'mite':r}
        self.assertFalse(self.p.tick(self.st))
        self.assertEqual(self.st['live_panel']['phase'],'not_needed')
        self.s.sh.assert_not_called();self.assertEqual(self.team_calls,[]);self.obs.assert_not_called()

    def test_full_fixed_order_finishes506_and_restart_does_not_duplicate_reports(self):
        for n in range(100):
            # Reconstruct controller every tick as a restart stress, retaining durable state.
            self.p=Panel(self.s,Mock());self.p.tick(self.st)
            if self.st.get('live_panel',{}).get('phase')=='done':break
        self.assertEqual(self.st['live_panel']['phase'],'done')
        expected=[]
        for tranche in self.plan['tranches']:
            for version in (113,115):
                expected.extend((str(i-1),version,version==113) for i in tranche)
        self.assertEqual(self.team_calls,expected)
        self.assertEqual(self.platform_version,115)
        self.assertEqual([c.args[0][-1] for c in self.s.sh.call_args_list],['113','115']*5)
        self.assertEqual(len(self.st['live_panel']['reports']),14)
        self.assertEqual(len(self.s.wake.call_args_list),15)
        self.assertFalse(self.p.tick(self.st))
        self.assertEqual(len(self.s.wake.call_args_list),15)

    def at_baseline_end(self):
        self.p.tick(self.st);self.p.tick(self.st)
        self.st['live_panel'].update(phase='baseline',index=3)
        self.s.sh.reset_mock()

    def test_observations_and_inflight_prevent_switch(self):
        self.at_baseline_end()
        self.obs.return_value=True
        self.p.tick(self.st);self.assertEqual(self.st['live_panel']['phase'],'baseline')
        self.obs.return_value=False
        self.fake.state.return_value=([],{'x':{'group':'running'}},{},set(),{})
        self.p.tick(self.st);self.assertEqual(self.st['live_panel']['phase'],'baseline')
        self.s.sh.assert_not_called()
        self.fake.state.return_value=([],{},{},set(),{})
        self.p.tick(self.st);self.assertEqual(self.st['live_panel']['phase'],'activate_candidate')
        # Final switch-lock recheck also prevents an intervening new group.
        self.fake.state.return_value=([],{'x':{'group':'raced'}},{},set(),{})
        self.p.tick(self.st);self.s.sh.assert_not_called()

    def test_outside_selection_holds_and_blocks_creation_not_collection(self):
        self.p.tick(self.st)
        self.platform_version=999
        self.p.tick(self.st)
        self.s.hold.assert_called_once()
        marker=json.loads((self.h/'version-check-active.json').read_text())
        self.assertEqual(marker['kind'],'live-panel-hold')
        self.assertNotIn('kill',str(self.s.sh.call_args_list))

    def test_changed_submission_uuid_fails_closed(self):
        self.p.tick(self.st)
        self.rows[0]['id']='different'
        self.p.tick(self.st)
        self.s.hold.assert_called_once()
        self.assertTrue((self.h/'version-check-active.json').exists())

    def test_installed_before_narrow_done_is_inert(self):
        self.st['r6_campaign']['phase']='bridge'
        self.validation.side_effect=ValueError('r6 not active')
        self.assertFalse(self.p.tick(self.st))
        self.s.sh.assert_not_called();self.assertNotIn('live_panel',self.st)
        self.validation.assert_not_called()


if __name__ == '__main__': unittest.main()
