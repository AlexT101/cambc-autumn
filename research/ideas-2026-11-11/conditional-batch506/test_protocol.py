import unittest
from run import config_for, CONFIGS, batch_jobs, BASE, verify_runtime
from unittest.mock import patch


class ProtocolTests(unittest.TestCase):
    def test_assignment_is_balanced_and_independent_of_input_order(self):
        rows = [{'name': str(i), 'sha256': format(i, '064x')} for i in range(10240)]
        a = config_for(rows)
        self.assertEqual(a, config_for(list(reversed(rows))))
        self.assertEqual(a['opponent_index'], 1)
        for c in CONFIGS:
            self.assertEqual(sum(v == c for v in a['maps'].values()), 1280)

    def test_batch_design_is_four_large_ab_calls_not_noise_specific_bodies(self):
        jobs = batch_jobs('chanM', 'p0', '/maps', '/config')
        self.assertEqual(len(jobs), 4)
        self.assertEqual(len({x[2] for x in jobs}), 2)
        self.assertEqual(sum(x[1] == BASE for x in jobs), 2)
        self.assertEqual(len({x[0] for x in jobs}), 4)

    def test_only_exact_reference_jobs_have_shared_names(self):
        first = batch_jobs('chanM', 'p0', '/maps', '/config')
        second = batch_jobs('bagfF', 'p0', '/maps', '/config')
        shared = {x[0] for x in first} & {x[0] for x in second}
        self.assertEqual(shared, {x[0] for x in first if x[1] == BASE})

    def test_ambient_own_fuel_override_is_rejected(self):
        manifest = {'runtime': {'environment': {'FASTRUNNER_MODE': 'native'}}}
        with patch.dict('os.environ', {'FASTRUNNER_MODE': 'native'}, clear=True):
            verify_runtime(manifest)
            with patch.dict('os.environ', {'FASTRUNNER_BOT_FUEL': 'oc-dfuel-506:99999999'}):
                with self.assertRaises(AssertionError):
                    verify_runtime(manifest)


if __name__ == '__main__':
    unittest.main()
