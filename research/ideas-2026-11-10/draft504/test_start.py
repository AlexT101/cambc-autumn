"""A queued lab must hold if either approved or committed main advances before it starts."""
import hashlib
import json
import unittest
from run import BASE, start_base_check

class StartBaseTests(unittest.TestCase):
    def setUp(self):
        self.sealed = {'bot.cc': 'aaa', 'draft/draft_model.h': 'bbb'}
        self.policy = {'base': BASE, 'base_source_sha256': hashlib.sha256(
            json.dumps(sorted(self.sealed.items()), separators=(',', ':')).encode()).hexdigest()}

    def test_exact_source_and_approval(self):
        self.assertTrue(start_base_check(self.policy, dict(self.sealed), self.sealed))

    def test_new_approved_base_holds_even_if_main_not_updated(self):
        self.assertFalse(start_base_check({**self.policy, 'base': 'variants/oc-fuel-505'}, self.sealed, self.sealed))

    def test_new_main_holds_even_if_policy_not_updated(self):
        self.assertFalse(start_base_check(self.policy, {**self.sealed, 'bot.cc': 'new'}, self.sealed))

    def test_same_label_changed_approved_source_holds(self):
        self.assertFalse(start_base_check({**self.policy, 'base_source_sha256': 'changed'}, self.sealed, self.sealed))

if __name__ == '__main__':
    unittest.main()
