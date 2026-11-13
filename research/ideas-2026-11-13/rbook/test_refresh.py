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


class RefreshGates(unittest.TestCase):
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

    def test_stage_rejects_successful_command_with_different_replays(self):
        text = 'plain: 24 games, 5 bodies handed over, invalid 0\n== 100M\nidentical replays: 51/52\n'
        with self.assertRaisesRegex(RuntimeError, '52 replays'):
            refresh_build.validate_stage(text)
        refresh_build.validate_stage(text.replace('51/52', '52/52'))

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
