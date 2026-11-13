"""Host identity and partial-baseline gates, without engine/API calls."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

import loss_host
import loss_refresh as refresh


class LatestHost(unittest.TestCase):
    def test_profile_requires_exact_unmasked_submission_and_unchanged_sources(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            for name in ('base','template'):
                path=root/'bots/variants'/name/'src';path.mkdir(parents=True)
                (path/'main.cc').write_text(name)
            p=dict(version=132,label='chy-531',commit='c451e3387',reference='variants/base',template='variants/template')
            for name in ('reference','template'):
                p[name+'_hashes']=loss_host.hashes(root/'bots'/p[name]/'src')
            h=dict(version=132,label='chy-531',commit='c451e3387',masked=False)
            with mock.patch.object(loss_host,'ROOT',root):
                self.assertEqual(loss_host.validate(p,132,h),p)
                for bad in (dict(h,masked=True),dict(h,label='chy-525f'),dict(h,commit='other')):
                    with self.assertRaisesRegex(RuntimeError,'submission'):
                        loss_host.validate(p,132,bad)
                with self.assertRaisesRegex(RuntimeError,'submission'):
                    loss_host.validate(p,128,h)
                (root/'bots/variants/template/src/main.cc').write_text('drift')
                with self.assertRaisesRegex(RuntimeError,'template changed'):
                    loss_host.validate(p,132,h)

    def test_partial_mite_does_not_gate_complete_fish_but_needs_clean_collected_cells(self):
        pins=dict(fish='r9',mite='r13')
        tasks=[dict(id=opp+str(i),version=132,purpose='set',opp_name=opp.title(),refset=pins[opp],
                    games=[dict(map=str(i),side='a')]) for opp in pins for i in range(2)]
        tasks += [dict(id='source',version=131,part='wins',purpose='set',opp_name='Fish',refset='r9')]
        created={t['id']:dict(group=t['id']) for t in tasks if t['id']!='mite1'}
        finished=set(created)
        rows=[dict(opp_name=t['opp_name'],map=t['games'][0]['map'],side='a')
              for t in tasks if t['id'] in created and t['version']==132]
        with mock.patch.object(refresh.sched,'load',return_value={'batches':{'after_done':['wins']}}), \
             mock.patch.object(refresh.ls,'state',return_value=(tasks,created,finished,set(),{})), \
             mock.patch.object(refresh.ls,'suspect_groups',return_value=set()), \
             mock.patch.object(refresh,'baseline_rows',return_value=rows):
            self.assertFalse(refresh.ready(132,pins,['wins']))
            self.assertTrue(refresh.ready(132,pins,['wins'],partial_baseline=['mite']))
            self.assertTrue(refresh.ready(132,pins,['wins'],partial_baseline=['fish','mite'],minimum_baseline_fraction=.5))
            self.assertFalse(refresh.ready(132,pins,['wins'],partial_baseline=['fish','mite'],minimum_baseline_fraction=.6))
            with mock.patch.object(refresh.ls,'suspect_groups',return_value={'mite0'}):
                with self.assertRaisesRegex(RuntimeError,'suspect'):
                    refresh.ready(132,pins,['wins'],partial_baseline=['mite'])
            finished.remove('fish1')
            self.assertFalse(refresh.ready(132,pins,['wins'],partial_baseline=['mite']))
        with self.assertRaises(ValueError):
            refresh.ready(132,pins,['wins'],partial_baseline=['fish','mite'])

    def test_unknown_collateral_is_deferred_natural_target_win_rejected(self):
        candidates=[dict(key='known',opp='fish',map='known',side='a'),
                    dict(key='unknown',opp='fish',map='unknown',side='a')]
        baseline={('fish',m,'a'):dict(result='loss') for m in ('known','unknown')}
        baseline['mite','known','a']=dict(result='win')
        kept,deferred=refresh.eligible_candidates(candidates,baseline,{'fish':'r9','mite':'r13'})
        self.assertEqual([c['key'] for c in kept],['known'])
        self.assertEqual(deferred[0]['unknown_opponents'],['mite'])
        baseline['fish','known','a']['result']='win'
        with self.assertRaisesRegex(RuntimeError,'confirmed host loss'):
            refresh.eligible_candidates(candidates,baseline,{'fish':'r9','mite':'r13'})

    def test_resume_rejects_different_host_profile(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);work=root/'work';work.mkdir()
            host=root/'bots/variants/rbook-loss-v132';host.mkdir(parents=True)
            frozen=dict(host_version=132,pins={'fish':'r9'},forced_keys=[],candidates=[],host_profile={'old':True})
            (work/'selection.json').write_text(json.dumps(frozen))
            (work/'build-started.json').write_text(json.dumps(dict(bot=str(host))))
            profile=dict(reference='variants/base',template='variants/template')
            (work/'profile.json').write_text(json.dumps(profile))
            with mock.patch.object(refresh,'ROOT',root),mock.patch.object(refresh,'baseline_rows',return_value=[]), \
                 mock.patch.object(refresh.sched,'load',return_value={'history':[dict(version=132)]}), \
                 mock.patch.object(loss_host,'validate',return_value=profile):
                with self.assertRaisesRegex(RuntimeError,'artifacts do not match'):
                    refresh.build(work,132,{'fish':'r9'},resume=True,host_profile=work/'profile.json')

class OutcomeOnlyHost(unittest.TestCase):
    def test_outcome_only_baseline_selects_full_sources_without_host_replays(self):
        import types
        import rbuild
        with tempfile.TemporaryDirectory() as tmp:
            work=Path(tmp);replay=work/'source.zip';replay.touch()
            common=dict(group='clean',status='finished',opp_name='Mite',refset='r13',side='a')
            rows=[dict(common,version=131,map=m,result='win',rounds=20,replay=str(replay),match=m)
                  for m in ('loss','win','unknown')]
            rows += [dict(common,version=132,map=m,result=m,replay=None,collection='outcome_only')
                     for m in ('loss','win')]
            games=work/'games.jsonl';games.write_text(''.join(json.dumps(r)+'\n' for r in rows))
            args=types.SimpleNamespace(versions='131',host_version=132,host_losses_only=True,extra=None)
            with mock.patch.object(rbuild,'GAMES',games),mock.patch.object(rbuild.ls,'suspect_groups',return_value=set()):
                self.assertEqual([c['map'] for c in rbuild.select(args,'Mite','r13','mite')],['loss'])

    def test_late_sources_are_conditional_on_latest_host_outcomes(self):
        import loss_cycle
        with tempfile.TemporaryDirectory() as tmp:
            work=Path(tmp);late=work/'late.json'
            late.write_text(json.dumps([dict(map=m,side='a') for m in ('win','loss','unknown','uncovered')]))
            (work/'book_cells.json').write_text(json.dumps([dict(opp='mite',map='loss',side='a')]))
            rows=[dict(opp_name='Mite',map=m,side='a',result='win' if m=='win' else 'loss')
                  for m in ('win','loss','uncovered')]
            with mock.patch.object(refresh,'baseline_rows',return_value=rows):
                result=loss_cycle.late_coverage(work,dict(host_version=132,pins={'mite':'r13'},late_source_cells=str(late)))
            self.assertEqual([r['status'] for r in result],['natural_host_win','booked','unknown_host_deferred','confirmed_loss_uncovered'])

    def test_source_proposal_defers_unknown_collateral_without_queue_writes(self):
        import loss_cycle
        with tempfile.TemporaryDirectory() as tmp:
            work=Path(tmp)
            rows=[dict(opp_name='Fish',map=m,side='a',result='loss') for m in ('safe','unknown')]
            rows += [dict(opp_name='Mite',map='safe',side='a',result='win'),
                     dict(opp_name='Fish',map='natural',side='a',result='win')]
            with mock.patch.object(refresh,'baseline_rows',return_value=rows),mock.patch.object(loss_cycle.sched,'save') as save:
                loss_cycle.source_opportunity(work,dict(host_version=132,pins={'fish':'r9','mite':'r13'}))
                save.assert_not_called()
            self.assertEqual(json.loads((work/'first-source-fish-known-losses.json').read_text()),[['safe','a'],['unknown','a']])
            self.assertEqual(json.loads((work/'first-source-fish-actionable-losses.json').read_text()),[['safe','a']])

    def test_local_resume_refuses_any_prior_upload_attempt(self):
        import loss_cycle
        with tempfile.TemporaryDirectory() as tmp:
            work=Path(tmp)
            (work/'refresh-plan.json').write_text('{}')
            (work/'cycle-state.json').write_text('{"phase":"held"}')
            (work/'build-state.json').write_text('{"phase":"ready_for_live_checks"}')
            (work/loss_cycle.release.STATE).write_text('{"phase":"upload_attempt"}')
            with mock.patch.object(loss_cycle.release,'upload') as upload:
                with self.assertRaisesRegex(RuntimeError,'no upload attempt'):
                    loss_cycle.run(work,resume_local=True)
                upload.assert_not_called()

    def test_existing_cycle_never_restarts_upload(self):
        import loss_cycle
        with tempfile.TemporaryDirectory() as tmp:
            work=Path(tmp);(work/'refresh-plan.json').write_text('{}')
            (work/'cycle-state.json').write_text('{"phase":"uploading_once"}')
            with mock.patch.object(loss_cycle.release,'upload') as upload:
                with self.assertRaisesRegex(RuntimeError,'reconciliation'):
                    loss_cycle.run(work)
                upload.assert_not_called()


if __name__=='__main__':
    unittest.main()
