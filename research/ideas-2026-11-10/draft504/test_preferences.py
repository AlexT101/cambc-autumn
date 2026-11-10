import json
from pathlib import Path
import unittest
import numpy as np
from preferences import weights, targets, flat, slope, normalize, direction_value, standardized, calibrate, CHAMPS, DISPLAY, fold
from oof import generated


class PreferencesTest(unittest.TestCase):
    def rows(self):
        return [{'team':t,'map_hash':str(m),'side':s,'picks':DISPLAY[:p]} for t in ['Fish','Mite']
                for m,p in [(0,3),(1,5)] for s in ['a','b']]

    def test_repeat_invariance_and_team_map_balance(self):
        rows=self.rows(); w=weights(rows)
        repeated=rows+[dict(rows[0])]*9; wr=weights(repeated)
        np.testing.assert_allclose(flat(targets(rows),w)[1],flat(targets(repeated),wr)[1])
        self.assertAlmostEqual(w.sum(),4)
        self.assertAlmostEqual(wr[[i for i,r in enumerate(repeated) if r['team']=='Fish']].sum(),2)

    def test_flat_is_overall_and_smoothed(self):
        rows=self.rows(); eta,q=flat(targets(rows),weights(rows))
        self.assertTrue(np.isfinite(eta).all()); self.assertAlmostEqual(q[3],.5)
        self.assertGreater(q[0],q[3]); self.assertGreater(q[3],q[10])

    def test_signed_nonnegative_calibration_and_duplication(self):
        eta=np.zeros(4); d=np.array([1,-1,1,-1]); keys=['m0','m0','m1','m1']
        y=np.array([1,0,1,0]); value=slope(eta,d,y,keys)
        self.assertGreater(value,0); self.assertEqual(slope(eta,d,1-y,keys),0)
        self.assertAlmostEqual(value,slope(np.tile(eta,3),np.tile(d,3),np.tile(y,3),keys*3))
        self.assertAlmostEqual(value,slope(eta,-d,1-y,keys))

    def test_common_clipping_and_missing_values_match_model(self):
        model={'features':['f'+str(k) for k in range(25)],'transforms':[None]*25,'mean':[1]*25,'sd':[2]*25}
        f={x:100 for x in model['features']};f['f1']=None
        z=standardized(f,model);self.assertEqual(z[0],4);self.assertEqual(z[1],0)

    def test_direction_and_normalization(self):
        a=np.zeros((12,26));a[:,0]=np.arange(12)-5.5
        direction={str(p):a.tolist() for p in (3,4,5)};pool=[{'picks':3,'z':[0]*25},{'picks':5,'z':[0]*25}]
        result,scale=normalize(direction,pool);self.assertGreater(scale,0)
        row={'picks':3,'z':[0]*25,'A':[9,10,11],'B':[0,1,2],'oursA':True,'oursB':True}
        self.assertGreater(direction_value(result,row),0)
        self.assertAlmostEqual(direction_value(result,row),-direction_value(result,{**row,'A':row['B'],'B':row['A']}))

    def test_opponent_values_are_fixed_and_our_side_flips(self):
        a=np.zeros((12,26));a[:,0]=np.arange(12)
        direction={'3':a.tolist()}
        row={'picks':3,'z':[0]*25,'A':[2,3,4],'B':[8,9,10],'oursA':True,'oursB':False}
        self.assertEqual(direction_value(direction,row),9)
        self.assertEqual(direction_value(direction,{**row,'B':[0,1,2]}),9)
        self.assertEqual(direction_value(direction,{**row,'A':row['B'],'B':row['A'],'oursA':False,'oursB':True}),-9)

    def test_oof_injection_keeps_original_body(self):
        original='prefix const commands = { fit: fitCommand, other: other }; suffix'
        result=generated(original,'function draft17OOF() {}')
        self.assertIn('"draft17-oof": draft17OOF, fit: fitCommand, other: other',result)
        with self.assertRaises(AssertionError):generated('changed marker','')
        self.assertEqual(fold('same-map'),fold('same-map'))

    def test_export_only_changes_declared_coefficients_and_zero_is_identity(self):
        model={'layout':{'B':0,'W':12,'K':92},'picks':{str(p):{'theta':[0.]*1300,'chol':[42]} for p in (3,4,5)}}
        a=np.zeros((12,26));a[:,0]=np.arange(12)-5.5;a[:,1]=a[:,0]*.1
        pref={'directions':{'flat':{str(p):a.tolist() for p in (3,4,5)}}}
        keys={}
        for i in range(100):keys.setdefault(fold(str(i)),str(i))
        rows=[]
        for f,k in keys.items():
            rows.append({'key':k,'fold':f,'picks':3,'z':[0]*25,'A':[9,10,11],'B':[0,1,2],
                         'oursA':True,'oursB':False,'eta':0,'y':1})
        pool=[{'picks':p,'z':[0]*25} for p in (3,4,5)]
        result=calibrate(pref,rows,pool,model)['arms']['flat']
        self.assertGreater(result['lambda'],0)
        allowed=set(range(12))|{12+c*92+k for c in range(12) for k in range(25)}
        for p in ('3','4','5'):
            th=result['model']['picks'][p]['theta']
            self.assertTrue(any(th));self.assertTrue(all(v==0 for i,v in enumerate(th) if i not in allowed))
            self.assertEqual(result['model']['picks'][p]['chol'],[42])
        zero=calibrate(pref,[{**r,'y':0} for r in rows],pool,model)['arms']['flat']
        self.assertEqual(zero['lambda'],0);self.assertEqual(zero['model'],model)

if __name__=='__main__':unittest.main()
