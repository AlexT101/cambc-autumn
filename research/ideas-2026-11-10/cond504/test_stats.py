import unittest
from stats import BOUND, decision

class Stops(unittest.TestCase):
    def test_noninferiority_alone_is_not_gain(self):
        self.assertIsNone(decision(0,BOUND+.1,0)[0])
    def test_gain_h0_alone_is_not_rejection(self):
        self.assertIsNone(decision(-BOUND-.1,0,0)[0])
    def test_joint_small_is_not_positive(self):
        self.assertEqual(decision(-BOUND-.1,BOUND+.1,0)[0],'SMALL/UNRESOLVED: judgement review')
    def test_positive_target(self):
        self.assertEqual(decision(BOUND+.1,0,0)[0],'POSITIVE SCREEN: target gain H1')
    def test_gain_first_lower_cross_is_not_reset(self):
        self.assertIsNone(decision(BOUND+.1,0,0,gain_h0=True)[0])
    def test_target_harm(self):
        self.assertEqual(decision(0,-BOUND-.1,0)[0],'REJECT: target harm H0')
    def test_later_harm_reversal_is_review_not_formal_reject(self):
        self.assertEqual(decision(0,-BOUND-.1,0,harm_h1=True)[0],'TARGET REGRESSION REVIEW: later safety alarm')
    def test_offtarget_harm_blocks_positive_admission(self):
        self.assertEqual(decision(BOUND+.1,0,-BOUND-.1)[0],'OFF-TARGET HARM: review')

if __name__ == '__main__': unittest.main()
