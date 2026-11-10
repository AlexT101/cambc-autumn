import unittest
from run import paired_scores, estimate


class Checks(unittest.TestCase):
    def test_map_pairing(self):
        rows = [{'map': 'a.map26a', 'order': [0, 1], 'winner': 0},
                {'map': 'a.map26a', 'order': [1, 0], 'winner': 1},
                {'map': 'b.map26a', 'order': [0, 1], 'winner': 0},
                {'map': 'b.map26a', 'order': [1, 0], 'winner': 0}]
        self.assertEqual(paired_scores(rows, {'a', 'b'}), {'a': .5, 'b': 1})
        with self.assertRaises(AssertionError): paired_scores(rows[:-1], {'a', 'b'})
        with self.assertRaises(AssertionError): paired_scores(rows + [rows[0]], {'a', 'b'})

    def test_uncertainty(self):
        x = estimate([.5] * 2048)
        self.assertEqual(x['win_pct'], 50)
        self.assertLess(x['map_paired_empirical_bernstein_95ci_pct'][0], 50)
        self.assertGreater(x['map_paired_empirical_bernstein_95ci_pct'][1], 50)
        self.assertAlmostEqual(estimate([0, 1] * 1024)['win_pct'], 50)


if __name__ == '__main__': unittest.main()
