import math
from pathlib import Path
import sys
import unittest

TOOLS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TOOLS))
import ab  # noqa: E402
import fgate_batch as fb  # noqa: E402


def units(mean, n=2560, sd=0.26):
    """n map units with exactly this mean and spread (half at mean + sd, half at mean - sd)."""
    return [0.5 + mean + sd, 0.5 + mean - sd] * (n // 2)


class SequentialTests(unittest.TestCase):
    def gate(self, **kw): return fb.Sequential(ab.llr, **kw)

    def play(self, seq, mean, batches):
        for _ in range(batches):
            if out := seq.add(units(mean), flips=1000): return out

    def test_identical_bots_stop_at_once(self):
        self.assertTrue(self.gate().add([0.5] * 2560, flips=0).startswith('IDENTICAL'))

    def test_a_loss_rejects_and_a_null_is_never_accepted(self):
        self.assertEqual(self.play(self.gate(ci=0), -0.01, 16), 'REJECT')
        seq = self.gate(ci=0)
        self.assertIsNone(self.play(seq, 0.0, 16))
        self.assertIsNone(seq.screen_at); self.assertIsNotNone(seq.high_h0_at)

    def test_zone_needs_both_crossings(self):
        seq = self.gate(ci=0, zone_stop=True)
        self.assertEqual(self.play(seq, 0.0025, 16), 'ZONE')
        self.assertTrue(seq.low_at and seq.high_h0_at)

    def test_live_bar_is_read_after_the_screen_batch(self):
        seq = self.gate(ci=0)
        # One batch at +6 points passes ln 99 by itself: still only a screen pass.
        self.assertIsNone(seq.add(units(0.06), flips=1000))
        self.assertEqual(seq.screen_at, 2560); self.assertGreater(seq.hl, fb.LIVE)
        self.assertEqual(seq.add(units(0.06), flips=1000), 'LIVE BAR H1')
        seq = self.gate(ci=0)
        seq.add(units(0.12), flips=1000)
        self.assertTrue(seq.add(units(-0.005), flips=1000).startswith('H1 but'))
        self.assertEqual(self.gate(ci=0, screen=True).add(units(0.06), flips=1000), 'ACCEPT (screen H1)')

    def test_narrowed_at_the_width(self):
        seq = self.gate(ci=0.25)
        out = self.play(seq, 0.004, 40)
        self.assertTrue(out.startswith('NARROWED')); self.assertLessEqual(seq.half, 0.25)
        self.assertEqual(seq.batches, math.ceil((196 * 0.26 / 0.25) ** 2 / 2560))


if __name__ == '__main__':
    unittest.main()
