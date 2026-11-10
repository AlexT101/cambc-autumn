import unittest
from mirror import paired_scores

class MirrorTests(unittest.TestCase):
    def rows(self):return [{'map':'a.map26a','order':[0,1],'winner':0},{'map':'a.map26a','order':[1,0],'winner':1}]
    def test_both_sides_paired(self):self.assertEqual(paired_scores(self.rows(),{'a'}),{'a':.5})
    def test_winner_is_bot_index(self):
        rows=self.rows();rows[1]['winner']=0;self.assertEqual(paired_scores(rows,{'a'}),{'a':1})
    def test_duplicate_rejected(self):
        with self.assertRaises(AssertionError):paired_scores(self.rows()+[self.rows()[0]],{'a'})
    def test_missing_side_rejected(self):
        with self.assertRaises(AssertionError):paired_scores(self.rows()[:1],{'a'})

if __name__=='__main__':unittest.main()
