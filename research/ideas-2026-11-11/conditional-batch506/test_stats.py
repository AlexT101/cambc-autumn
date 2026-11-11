import unittest
from stats import cells, paired, interval, decision


class FixedMapTests(unittest.TestCase):
    def test_winner_is_logical_bot_index_and_sides_are_one_unit(self):
        a = cells([{'map': 'm.map26a', 'order': [0, 1], 'winner': 0},
                   {'map': 'm.map26a', 'order': [1, 0], 'winner': 0}], ['m'])
        b = cells([{'map': 'm.map26a', 'order': [0, 1], 'winner': 0},
                   {'map': 'm.map26a', 'order': [1, 0], 'winner': 1}], ['m'])
        self.assertEqual(paired(a, b), {'m': .5})

    def test_duplicate_and_missing_side_fail_closed(self):
        r = {'map': 'm.map26a', 'order': [0, 1], 'winner': 0}
        for rows in ([r], [r, r]):
            with self.assertRaises(AssertionError):
                cells(rows, ['m'])

    def test_fixed_decision_needs_target_and_safety(self):
        positive = {'normal_95': [.001, .003]}
        safe = {'normal_95': [-.002, .001]}
        uncertain = {'normal_95': [-.003, .001]}
        self.assertTrue(decision(positive, safe).startswith('POSITIVE'))
        self.assertTrue(decision(positive, uncertain).startswith('UNRESOLVED'))
        self.assertTrue(decision(uncertain, safe).startswith('UNRESOLVED'))

    def test_degenerate_sample_is_not_claimed_exact(self):
        result = interval([0] * 100)
        self.assertEqual(result['normal_95'], [0, 0])
        self.assertLess(result['bounded_95'][0], 0)
        self.assertGreater(result['bounded_95'][1], 0)


if __name__ == '__main__':
    unittest.main()
