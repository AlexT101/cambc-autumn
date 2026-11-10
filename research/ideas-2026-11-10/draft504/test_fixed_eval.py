import unittest
from fixed_eval import choose, compare, estimate


class FixedEvaluationTest(unittest.TestCase):
    def test_selection_requires_positive_lower_bound_and_tie_is_flat(self):
        self.assertEqual(choose({'flat':{'lower':0,'delta':.04},'conditional':{'lower':-.01,'delta':.05}}),'control')
        both={k:{'lower':.001,'delta':.02} for k in ['flat','conditional']}
        self.assertEqual(choose(both),'flat')
        both['conditional']['delta']=.021
        self.assertEqual(choose(both),'conditional')

    def test_repeated_noises_do_not_multiply_map_sample_size(self):
        picks={f'm{i}':3+i%3 for i in range(12)}
        scores={b:{m:{o:{(1,s):0 for s in 'ab'} for o in 'FM'} for m in picks} for b in ['cand','ref']}
        for i,m in enumerate(picks):
            for o in 'FM':
                for s in 'ab':scores['cand'][m][o][1,s]=i%2
        first=compare(scores,'cand','ref',picks)
        for b in scores:
            for m in picks:
                for o in 'FM':
                    for k in range(2,17):
                        for s in 'ab':scores[b][m][o][k,s]=scores[b][m][o][1,s]
        second=compare(scores,'cand','ref',picks)
        self.assertEqual(first,second);self.assertEqual(second['all']['maps'],12)
        del scores['ref']['m0']['F'][1,'a']
        with self.assertRaises(AssertionError):compare(scores,'cand','ref',picks)

    def test_effect_sign_and_diagnostic_groups(self):
        x=estimate([-.1,-.2,-.1]);self.assertLess(x['upper'],0)
        self.assertEqual(x['maps'],3)
        with self.assertRaises(AssertionError):estimate([1])

if __name__=='__main__':unittest.main()
