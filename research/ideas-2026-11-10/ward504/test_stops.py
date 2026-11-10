"""Exercise the actual width-stop expression without running or importing a gate."""
import ast
from pathlib import Path
from types import SimpleNamespace
import unittest

ROOT = Path(__file__).resolve().parents[3]


class StopTests(unittest.TestCase):
    def setUp(self):
        tree = ast.parse((ROOT / 'research/ideas-2026-11-09/freshgate-tools/fgate.py').read_text())
        conditions = [node.test for node in ast.walk(tree) if isinstance(node, ast.If)
                      and '196 * se' in ast.unparse(node.test)]
        self.assertEqual(len(conditions), 1)
        self.code = compile(ast.Expression(conditions[0]), '<actual-width-condition>', 'eval')

    def stop(self, ci, se, block=8, screened=False):
        return eval(self.code, {}, {'a': SimpleNamespace(ci=ci, min_blocks=8),
                                   'se': se, 'k': block, 'screen_at': 1 if screened else None})

    def test_zero_disables_even_exact_zero_width(self):
        self.assertFalse(self.stop(0, 0))
        self.assertFalse(self.stop(0, .001))

    def test_default_threshold_and_minimum_unchanged(self):
        self.assertTrue(self.stop(.25, .001))
        self.assertFalse(self.stop(.25, .002))
        self.assertFalse(self.stop(.25, .001, block=7))
        self.assertFalse(self.stop(.25, .001, screened=True))


if __name__ == '__main__':
    unittest.main()
