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


class RefreshGates(unittest.TestCase):
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
