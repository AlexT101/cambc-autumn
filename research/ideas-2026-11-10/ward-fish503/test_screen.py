"""Estimator and exact coverage checks, without running any games."""
import unittest
from run_screen import estimate


class ScreenTests(unittest.TestCase):
    def test_side_pairing_cancels_side_bias(self):
        names = {'x', 'y'}
        c = {(n, s): float(s == 'a') for n in names for s in ('a', 'b')}
        b = {(n, s): float(s == 'b') for n in names for s in ('a', 'b')}
        self.assertEqual(estimate(c, b, names)['ci95_pp'], [0, 0])

    def test_missing_or_extra_cell_fails(self):
        b = {(n, s): 0 for n in ('x', 'y') for s in ('a', 'b')}
        c = dict(b)
        c.pop(('x', 'a'))
        with self.assertRaises(AssertionError):
            estimate(c, b, {'x', 'y'})
        c = dict(b)
        c['z', 'a'] = 0
        with self.assertRaises(AssertionError):
            estimate(c, b, {'x', 'y'})

    def test_uncertainty_uses_maps(self):
        b = {(n, s): 0 for n in ('x', 'y') for s in ('a', 'b')}
        c = {k: float(k[0] == 'x') for k in b}
        e = estimate(c, b, {'x', 'y'})
        self.assertEqual(e['gain_pp'], 50)
        self.assertAlmostEqual(e['ci95_pp'][0], -48)
        self.assertAlmostEqual(e['ci95_pp'][1], 148)


if __name__ == '__main__':
    unittest.main()
