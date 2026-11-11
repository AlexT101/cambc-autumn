"""The fresh-map gate's cache check (fgate_batch.check_source) and worktree body adoption, on temporary trees."""
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest.mock import patch

TOOLS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TOOLS))
import fgate_batch as fb  # noqa: E402

LOG = "Running 2 matches\nBot 1: /x/bots/variants/c\n  as /x/replays/frozen/{}/c\nBot 2: /x/bots/variants/r\n  as /x/replays/frozen/eeeeeeeeeeee/r\n"


class SourceTests(unittest.TestCase):
    def setUp(self):
        self.td = tempfile.TemporaryDirectory(); self.root = Path(self.td.name)
        self.patches = [patch.object(fb, 'ROOT', self.root), patch.dict(fb._now, {'variants/c': 'aaaaaaaaaaaa'}, clear=True),
                        patch.dict(fb._played, clear=True)]
        for p in self.patches: p.start()

    def tearDown(self):
        for p in self.patches: p.stop()
        self.td.cleanup()

    def summary(self, frozen=None, log_hash=None, started='1'):
        log = self.root / 'replays/ab/n/ladder.log'; log.parent.mkdir(parents=True, exist_ok=True)
        if log_hash: log.write_text(LOG.format(log_hash))
        return {'started': started, 'cand': {'path': 'bots/variants/c', **({'frozen': frozen} if frozen else {})},
                'suites': [{'log': 'replays/ab/n/ladder.log'}]}

    def test_recorded_source_is_used_and_checked(self):
        fb.check_source('n', self.summary(frozen=['aaaaaaaaaaaa']), 'variants/c')
        with self.assertRaises(SystemExit):
            fb.check_source('n', self.summary(frozen=['bbbbbbbbbbbb']), 'variants/c')

    def test_a_legacy_run_is_checked_from_its_logs(self):
        x = self.summary(log_hash='aaaaaaaaaaaa')
        self.assertEqual(fb.played('n', x), {'aaaaaaaaaaaa'})
        fb.check_source('n', x, 'variants/c')
        with self.assertRaises(SystemExit):
            fb.check_source('n', self.summary(log_hash='bbbbbbbbbbbb', started='2'), 'variants/c')

    def test_a_run_mixing_sources_is_refused(self):
        with self.assertRaises(SystemExit):
            fb.check_source('n', self.summary(frozen=['aaaaaaaaaaaa', 'bbbbbbbbbbbb']), 'variants/c')

    def test_an_unrecorded_run_is_reused(self):
        fb.check_source('n', self.summary(), 'variants/c')


class AdoptTests(unittest.TestCase):
    def test_a_worktree_copies_a_body_without_its_build(self):
        with tempfile.TemporaryDirectory() as td:
            primary, tree = Path(td, 'primary'), Path(td, 'tree')
            body = primary / 'bots/variants/rt-X'
            (body / 'src').mkdir(parents=True); (body / 'src/bot.cc').write_text('x')
            (body / '.cambc/build').mkdir(parents=True); (body / '.cambc/build/bot.wasm').write_text('w')
            (tree / 'bots/variants').mkdir(parents=True)
            fg = types.SimpleNamespace(dgate=types.SimpleNamespace(R=f'{primary}/'))
            with patch.object(fb, 'ROOT', tree):
                fb.adopt(fg, 'variants/rt-X')
                fb.adopt(fg, 'variants/missing')
            self.assertEqual((tree / 'bots/variants/rt-X/src/bot.cc').read_text(), 'x')
            self.assertFalse((tree / 'bots/variants/rt-X/.cambc').exists())
            self.assertFalse((tree / 'bots/variants/missing').exists())


if __name__ == '__main__':
    unittest.main()
