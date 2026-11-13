"""Offline checks for refresh gates; no engine games or platform calls."""
import json
from pathlib import Path
import tempfile
import types
import unittest
from unittest import mock

import oppwatch
import rbuild
import refresh_build
import refresh_live
import loss_refresh
import loss_live_plan


class RefreshGates(unittest.TestCase):
    def test_live_step_prefix_preserves_first_book_and_distinguishes_increment(self):
        first=dict(host_version=128,bot='/repo/bots/variants/rbook-loss-v128')
        increment=dict(first,bot='/repo/bots/variants/rbook-loss-v128-r13-increment2')
        self.assertEqual(loss_live_plan.step_prefix(first),'loss-v128')
        self.assertEqual(loss_live_plan.step_prefix(dict(host_version=128)),'loss-v128')
        self.assertEqual(loss_live_plan.step_prefix(increment),'loss-v128-r13-increment2')

    def test_increment_live_plan_namespaces_pinned_and_current_expectations(self):
        with tempfile.TemporaryDirectory() as tmp:
            work=Path(tmp)
            state=dict(phase='ready_for_live_checks',host_version=128,pins=dict(mite='r13'),
                       bot='/repo/bots/variants/rbook-loss-v128-r13-increment2')
            entry=dict(key='map-a-v901-src',opp='mite',map='map',side='a')
            (work/'build-state.json').write_text(json.dumps(state))
            (work/'book_cells.json').write_text(json.dumps([entry]))
            (work/'force.txt').write_text('')
            baseline=dict(opp_name='Mite',map='map',side='a',purpose='set',pin='ref',refset='r13',
                          result='loss',opp_id='mite-id',our_picks=[],opp_picks=[])
            with mock.patch.object(loss_live_plan.ls,'games',return_value=[baseline]), \
                 mock.patch.object(loss_live_plan,'source_rows',return_value={'src':dict(result='win')}):
                loss_live_plan.plan(work)
            steps=json.loads((work/'live-steps.json').read_text())
            expected=json.loads((work/'live-expectations.json').read_text())
            ids={s[1] for s in steps}
            self.assertEqual(ids,{'loss-v128-r13-increment2-mite-r13','loss-v128-r13-increment2-mite-current'})
            self.assertEqual({e['step'] for e in expected},ids)
            self.assertEqual({e['pin'] for e in expected},{'ref','none'})

    def test_variant_name_defaults_and_rejects_paths(self):
        self.assertEqual(loss_refresh.variant_name(128),'rbook-loss-v128')
        self.assertEqual(loss_refresh.variant_name(128,'rbook-loss-v128-r13-increment2'),
                         'rbook-loss-v128-r13-increment2')
        for name in ('', '.', '..', '../first', '/absolute', 'variants/new', 'new name'):
            with self.subTest(name=name),self.assertRaises(ValueError):
                loss_refresh.variant_name(128,name)

    def test_named_increment_resume_cannot_reuse_first_variant(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);work=root/'work';work.mkdir()
            name='rbook-loss-v128-r13-increment2'
            host=root/'bots/variants'/name;host.mkdir(parents=True)
            frozen=dict(host_version=128,pins=dict(mite='r13'),forced_keys=[],candidates=[])
            (work/'selection.json').write_text(json.dumps(frozen))
            (work/'build-started.json').write_text(json.dumps(dict(bot=str(host))))
            with mock.patch.object(loss_refresh,'ROOT',root), \
                 mock.patch.object(loss_refresh.sched,'load',return_value={'history':[dict(version=128,label='chy-525f',masked=False)]}), \
                 mock.patch.object(loss_refresh,'baseline_rows',return_value=[]), \
                 mock.patch.object(loss_refresh.rbuild,'select') as select, \
                 mock.patch.object(loss_refresh,'run',side_effect=RuntimeError('sizing reached')) as run:
                with self.assertRaisesRegex(RuntimeError,'sizing reached'):
                    loss_refresh.build(work,128,dict(mite='r13'),resume=True,bot_name=name)
                select.assert_not_called()
                self.assertEqual(run.call_count,1)
                self.assertIn('variants/'+name,run.call_args.args[0])
                with self.assertRaisesRegex(RuntimeError,'artifacts do not match'):
                    loss_refresh.build(work,128,dict(mite='r13'),resume=True)
                self.assertEqual(json.loads((work/'selection.json').read_text()),frozen)

    def test_foreign_candidates_must_match_planned_pin(self):
        with tempfile.TemporaryDirectory() as tmp, mock.patch.object(loss_live_plan.ls,'read_jsonl',return_value=[]):
            work=Path(tmp)
            meta={'map-a-v901-source':dict(opp='fish',target_refset='r8',qualification='local_exact_live_pending')}
            (work/'foreign-metadata.json').write_text(json.dumps(meta))
            self.assertIn('source',loss_live_plan.source_rows(work,{'fish':'r8'}))
            with self.assertRaisesRegex(RuntimeError,'another pin'):
                loss_live_plan.source_rows(work,{'fish':'r9'})

    def test_live_plan_preserves_other_opponent_wins_on_forced_or_shared_drafts(self):
        entry=dict(key='map-a-v125-source',map='map',side='a',opp='fish')
        sources={'source':dict(our_picks=[1],opp_picks=[2])}
        baseline={('fish','map','a'):dict(result='loss',our_picks=[1],opp_picks=[2]),
                  ('mite','map','a'):dict(result='win',our_picks=[3],opp_picks=[4])}
        checks=loss_live_plan.coverage([entry],{entry['key']},baseline,sources,['fish','mite'])
        self.assertTrue(checks[('mite','map','a')]['require_win'])
        checks=loss_live_plan.coverage([entry],set(),baseline,sources,['fish','mite'])
        self.assertNotIn(('mite','map','a'),checks)
        baseline[('mite','map','a')].update(our_picks=[1],opp_picks=[2])
        checks=loss_live_plan.coverage([entry],set(),baseline,sources,['fish','mite'])
        self.assertTrue(checks[('mite','map','a')]['require_win'])
        baseline[('fish','map','a')]['result']='win'
        with self.assertRaisesRegex(RuntimeError,'host loss'):
            loss_live_plan.coverage([entry],set(),baseline,sources,['fish','mite'])

    def test_live_plan_reuses_known_pin_win_but_checks_other_pin_source(self):
        entry=dict(key='map-a-v125-source',map='map',side='a',opp='fish')
        base=dict(result='loss',our_picks=[1],opp_picks=[2],opp_id='fish-id',refset='r8')
        source=dict(base,result='win',pin='ref')
        self.assertEqual(loss_live_plan.coverage([entry],set(),{('fish','map','a'):base},
                                                {'source':source},['fish']),{})
        source['refset']='r7'
        checks=loss_live_plan.coverage([entry],set(),{('fish','map','a'):base},{'source':source},['fish'])
        self.assertTrue(checks[('fish','map','a')]['require_win'])

    def test_loss_refresh_requires_complete_clean_host_coverage(self):
        pins=dict(fish='r8',mite='r12')
        tasks=[dict(id=opp,version=128,purpose='set',opp_name=name,refset=pins[opp],
                    games=[dict(map='map',side='a')])
               for opp,name in [('fish','Intercontinental Fish'),('mite','Mite')]]
        tasks.append(dict(id='source',version=126,purpose='set',part='wins',opp_name='Mite',refset='r12'))
        created={t['id']:dict(group=t['id']) for t in tasks}
        rows=[dict(version=128,opp_name=t['opp_name'],map='map',side='a',result='loss') for t in tasks[:2]]
        with mock.patch.object(loss_refresh.sched,'load',return_value={'batches':{'after_done':['wins']}}), \
             mock.patch.object(loss_refresh.ls,'state',return_value=(tasks,created,set(created),set(),{})), \
             mock.patch.object(loss_refresh.ls,'suspect_groups',return_value=set()), \
             mock.patch.object(loss_refresh,'baseline_rows',return_value=rows):
            self.assertTrue(loss_refresh.ready(128,pins,['wins']))
            with mock.patch.object(loss_refresh,'baseline_rows',return_value=rows[:1]):
                with self.assertRaisesRegex(RuntimeError,'missing cells'):
                    loss_refresh.ready(128,pins,['wins'])
            with mock.patch.object(loss_refresh.ls,'suspect_groups',return_value={'source'}):
                with self.assertRaisesRegex(RuntimeError,'suspect'):
                    loss_refresh.ready(128,pins,['wins'])

    def test_resume_preserves_frozen_selection_and_does_not_copy_host(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);work=root/'work';work.mkdir()
            host=root/'bots/variants/rbook-loss-v128';host.mkdir(parents=True)
            frozen=dict(host_version=128,pins=dict(mite='r13'),forced_keys=['forced'],candidates=[])
            (work/'selection.json').write_text(json.dumps(frozen))
            (work/'build-started.json').write_text(json.dumps(dict(bot=str(host))))
            with mock.patch.object(loss_refresh,'ROOT',root), \
                 mock.patch.object(loss_refresh.sched,'load',return_value={'history':[dict(version=128,label='chy-525f',masked=False)]}), \
                 mock.patch.object(loss_refresh,'baseline_rows',return_value=[]), \
                 mock.patch.object(loss_refresh.rbuild,'select') as select, \
                 mock.patch.object(loss_refresh,'run',side_effect=RuntimeError('sizing reached')) as run:
                with self.assertRaisesRegex(RuntimeError,'sizing reached'):
                    loss_refresh.build(work,128,dict(mite='r13'),resume=True)
                select.assert_not_called()
                self.assertEqual(run.call_count,1)
                self.assertIn('--selection',run.call_args.args[0])
                self.assertEqual(json.loads((work/'selection.json').read_text()),frozen)
                with self.assertRaisesRegex(RuntimeError,'artifacts do not match'):
                    loss_refresh.build(work,128,dict(mite='r14'),resume=True)
                versions=loss_refresh.DEFAULT_SOURCE_VERSIONS+',131'
                with self.assertRaisesRegex(RuntimeError,'source versions'):
                    loss_refresh.build(work,128,dict(mite='r13'),resume=True,versions=versions)
                self.assertEqual(run.call_count,1)
                frozen['source_versions']=versions
                (work/'selection.json').write_text(json.dumps(frozen))
                with self.assertRaisesRegex(RuntimeError,'sizing reached'):
                    loss_refresh.build(work,128,dict(mite='r13'),resume=True,versions=versions)
                args=run.call_args.args[0]
                self.assertEqual(args[args.index('--versions')+1],versions)
                select.assert_not_called()
                self.assertEqual(json.loads((work/'selection.json').read_text()),frozen)

    def test_source_versions_reject_invalid_or_duplicate_uploads(self):
        for value in ('', '0', '-1', '126,,131', '126,126', '126,unknown'):
            with self.subTest(value=value),self.assertRaises(ValueError):
                loss_refresh.source_versions(value)

    def test_partial_sources_still_require_complete_host_baseline(self):
        pins=dict(mite='r13')
        tasks=[dict(id='base',version=128,purpose='set',opp_name='Mite',refset='r13',
                    games=[dict(map='map',side='a')])]
        tasks += [dict(id=str(i),version=126,purpose='set',part='wins',opp_name='Mite',refset='r13')
                  for i in range(4)]
        created={t['id']:dict(group=t['id']) for t in tasks[:-1]}
        finished=set(created)
        with mock.patch.object(loss_refresh.sched,'load',return_value={'batches':{'after_done':[]}}), \
             mock.patch.object(loss_refresh.ls,'state',return_value=(tasks,created,finished,set(),{})), \
             mock.patch.object(loss_refresh.ls,'suspect_groups',return_value=set()), \
             mock.patch.object(loss_refresh,'baseline_rows',return_value=[dict(opp_name='Mite',map='map',side='a')]):
            self.assertTrue(loss_refresh.ready(128,pins,['wins'],.7))
            self.assertFalse(loss_refresh.ready(128,pins,['wins'],.8))
            self.assertFalse(loss_refresh.ready(128,pins,['wins']))
            finished.remove('base')
            self.assertFalse(loss_refresh.ready(128,pins,['wins'],.7))

    def test_live_win_after_divergence_counts_but_loss_does_not(self):
        outcome = refresh_live.validate_live_results([dict(result='win',diff=-1),dict(result='win',diff=700)])
        self.assertEqual(outcome, dict(wins=2,exact_wins=1,wins_after_divergence=1))
        with self.assertRaisesRegex(RuntimeError,'lost'):
            refresh_live.validate_live_results([dict(result='loss',diff=700)])
        with self.assertRaisesRegex(RuntimeError,'evidence'):
            refresh_live.validate_live_results([dict(result='win',diff=None)])

    def test_loss_policy_separates_opponent_pin_and_unknown_cells(self):
        with tempfile.TemporaryDirectory() as tmp:
            work=Path(tmp); replay=work/'replay.zip';replay.touch()
            common=dict(status='finished',map='shared',side='a',rounds=10,replay=str(replay),group='clean')
            rows=[dict(common,version=117,opp_name=opp,refset=pin,result='win',match=opp)
                  for opp,pin in [('Mite','r12'),('Intercontinental Fish','r8')]]
            rows += [dict(common,version=128,opp_name='Mite',refset='r12',result='loss',match='base-mite'),
                     dict(common,version=128,opp_name='Intercontinental Fish',refset='r8',result='win',match='base-fish'),
                     dict(common,version=117,opp_name='Mite',refset='r12',result='win',match='unknown',map='unknown'),
                     dict(common,version=117,opp_name='Mite',refset='r13',result='win',match='newpin')]
            games=work/'games.jsonl';games.write_text(''.join(json.dumps(row)+'\n' for row in rows))
            args=types.SimpleNamespace(versions='117',host_version=128,host_losses_only=True,extra=None)
            with mock.patch.object(rbuild,'GAMES',games), mock.patch.object(rbuild.ls,'suspect_groups',return_value=set()):
                self.assertEqual(len(rbuild.select(args,'Mite','r12','mite')),1)
                self.assertEqual(rbuild.select(args,'Intercontinental Fish','r8','fish'),[])
                self.assertEqual(rbuild.select(args,'Mite','r13','mite'),[])
                extra=work/'extra.tsv'
                extra.write_text(f'{replay} a shared-a-v901-foreign shared mite\n')
                args.extra=extra
                args.extra_uncovered_only=True
                self.assertEqual(rbuild.select(args,'Mite','r12','mite')[0]['version'],117)
                args.extra_uncovered_only=False
                self.assertEqual(rbuild.select(args,'Mite','r12','mite')[0]['version'],901)

    def test_stage_rejects_successful_command_with_different_replays(self):
        text = 'plain: 24 games, 5 bodies handed over, invalid 0\n== 100M\nidentical replays: 51/52\n'
        with self.assertRaisesRegex(RuntimeError, '52 replays'):
            refresh_build.validate_stage(text)
        refresh_build.validate_stage(text.replace('51/52', '52/52'))

    def test_small_partial_requires_every_available_long_fallback_case(self):
        with tempfile.TemporaryDirectory() as tmp:
            work=Path(tmp)
            cells=[dict(key=str(i)) for i in range(20)]
            (work/'book_cells.json').write_text(json.dumps(cells))
            (work/'book.jsonl').write_text(''.join(json.dumps(dict(key=str(i),rounds=600 if i<19 else 400))+'\n' for i in range(20)))
            stage='plain: 19 games, 5 bodies handed over, invalid 0\n== 100M\nidentical replays: 52/52\n'
            refresh_build.validate_stage(stage,work)
            for bad in (stage.replace('19 games','18 games'),stage.replace('invalid 0','invalid 1'),stage.replace('5 bodies','0 bodies')):
                with self.assertRaisesRegex(RuntimeError,'Fallback'):
                    refresh_build.validate_stage(bad,work)

    def test_fresh_result_cannot_substitute_for_missing_wide_bench(self):
        text = 'plain: 24 games, 5 bodies handed over, invalid 0\n== 100M\n== fresh real fuel\nidentical replays: 52/52\n'
        with self.assertRaisesRegex(RuntimeError, '52 replays'):
            refresh_build.validate_stage(text)

    def test_only_declared_forced_cells_may_differ_in_wide_bench(self):
        with tempfile.TemporaryDirectory() as tmp:
            work=Path(tmp)
            (work/'force.txt').write_text('forced\n')
            (work/'book_cells.json').write_text(json.dumps([dict(key='forced',map='map',side='a')]))
            text="plain: 24 games, 5 bodies handed over, invalid 0\n== 100M\nidentical replays: 51/52; differ: [('map', 'a')]\n"
            refresh_build.validate_stage(text,work)
            with self.assertRaisesRegex(RuntimeError,'outside'):
                refresh_build.validate_stage(text.replace("('map', 'a')","('other', 'a')"),work)

    def test_suspect_shorter_win_cannot_enter_book(self):
        with tempfile.TemporaryDirectory() as tmp:
            work = Path(tmp)
            replay = work/'replay.zip'
            replay.touch()
            common = dict(status='finished', opp_name='Mite', refset='r11', map='map',
                          side='a', version=119, result='win', replay=str(replay))
            rows = [dict(common, group='bad', rounds=10, match='suspect'),
                    dict(common, group='good', rounds=20, match='clean')]
            games = work/'games.jsonl'
            games.write_text(''.join(json.dumps(r)+'\n' for r in rows))
            args = types.SimpleNamespace(versions='119', host_version=None, extra=None)
            with mock.patch.object(rbuild, 'GAMES', games), mock.patch.object(
                    rbuild.ls, 'suspect_groups', return_value={'bad'}):
                selected = rbuild.select(args, 'Mite', 'r11', 'mite')
            self.assertEqual([c['key'] for c in selected], ['map-a-v119-clean'])

    def test_shared_cell_accepts_either_exact_draft_entry(self):
        with mock.patch.object(oppwatch, 'book_divergence', side_effect=[-1, 0]):
            self.assertEqual(oppwatch.cell_divergence({}, ['fish', 'mite']), -1)

    def test_missing_replay_is_not_a_match(self):
        with mock.patch.object(oppwatch, 'book_divergence', return_value=None):
            self.assertIsNone(oppwatch.cell_divergence({}, ['fish']))

    def test_failed_entry_stops_build(self):
        with tempfile.TemporaryDirectory() as tmp, mock.patch.object(
                rbuild, 'verify_one', return_value=[('entry', 'differs')]):
            with self.assertRaises(SystemExit):
                rbuild.verify([{'key':'entry', 'opp':'fish'}], None, Path(tmp), None)
            self.assertEqual(json.loads((Path(tmp)/'verify.json').read_text()), {'entry':'differs'})

    def test_held_full_control_does_not_block_refresh_build(self):
        prefix = 'book-refresh-r11-mite'
        tasks = [dict(id='sweep', version=119, purpose='set', refset='r11', opp_name='Mite'),
                 dict(id='control', version=118, purpose='set', refset='r11', opp_name='Mite', part='core'),
                 dict(id='losses', version=118, purpose='set', refset='r11', opp_name='Mite', part=prefix+'-v118')]
        state = {'batches': {'after_done':[prefix,prefix+'-v118',prefix+'-v117']}}
        created = {'sweep': {'group':'a'},'losses':{'group':'b'}}
        with mock.patch.object(refresh_build.sched,'load',return_value=state), mock.patch.object(
                refresh_build.ls,'state',return_value=(tasks,created,{'a','b'},set(),{})):
            self.assertTrue(refresh_build.ready(None,'r11'))
        with mock.patch.object(refresh_build.sched,'load',return_value=state), mock.patch.object(
                refresh_build.ls,'state',return_value=(tasks,created,{'a'},set(),{})):
            self.assertFalse(refresh_build.ready(None,'r11'))

    def test_existing_destination_never_rebuilt(self):
        with tempfile.TemporaryDirectory() as tmp:
            work=Path(tmp)
            (work/'build-started.json').write_text('{}')
            with self.assertRaisesRegex(RuntimeError,'already started'):
                refresh_build.build(work,'r999999',False)


if __name__ == '__main__':
    unittest.main()
