import unittest
from unittest.mock import patch
from ahead import window, same_owner

class Controls(unittest.TestCase):
    def test_current_first_and_two_ahead_only(self):
        self.assertEqual(window(544), [(545,'Flp4'),(545,'Mt3q'),(546,'Flp4'),(546,'Mt3q'),(547,'Flp4'),(547,'Mt3q')])
        self.assertEqual(window(999), [(1000,'Flp4'),(1000,'Mt3q')])
        self.assertEqual(window(1000), [])
    def test_owner_pid_reuse_or_changed_command_stops(self):
        owner={'pid':1,'start':'100','cmdline':'ward camp'}
        for actual in [None,dict(owner,state='Z'),dict(owner,start='101',state='S'),dict(owner,cmdline='other',state='S')]:
            with patch('ahead.identity',return_value=actual):self.assertFalse(same_owner(owner))
        with patch('ahead.identity',return_value=dict(owner,state='S')):self.assertTrue(same_owner(owner))

if __name__=='__main__': unittest.main()
