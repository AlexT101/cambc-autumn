"""Lightweight source and scheduling invariants; no builds, native games or datasets."""
import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

T = Path(__file__).resolve().parent

def module(name):
    spec = importlib.util.spec_from_file_location('tune8_test_'+name,T/(name+'.py'))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m

v = module('vehicle')
r = module('run')

class Controls(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        root = v.R/'bots'/v.SPEC['base']/'src'
        cls.original = {str(p.relative_to(root)):p.read_text() for p in root.rglob('*') if p.is_file()}

    def test_default_plain_export_exact(self):
        values = {p['name']:p['default'] for p in v.SPEC['parameters']}
        self.assertEqual(v.transform(self.original,values),self.original)

    def test_all_ranges_only_declared_sites(self):
        sites = {p['file'] for p in v.SPEC['parameters']}
        for end in (0,1):
            values = {p['name']:p['range'][end] for p in v.SPEC['parameters']}
            out = v.transform(self.original,values)
            self.assertEqual(set(out),set(self.original))
            self.assertEqual({p for p in out if out[p]!=self.original[p]},sites)
            self.assertEqual(out['draft/draft_model.h'],self.original['draft/draft_model.h'])
            self.assertEqual(out['economy/emblem_table.h'],self.original['economy/emblem_table.h'])

    def test_vehicle_mutability_and_spec(self):
        out = v.transform(self.original)
        self.assertEqual(len(json.loads(out['tune.json'])['floats']),27)
        for name in ('gold_price_scale','recall_health_fraction'):
            self.assertIn('inline float& '+name+' = diana_tune.f[',out['params.h'])
        self.assertEqual(out['model/safety.cc'],self.original['model/safety.cc'])
        self.assertEqual(out['draft/draft.cc'],self.original['draft/draft.cc'])

    def test_drift_and_invalid_values_fail(self):
        broken = dict(self.original)
        broken['economy/farm.cc'] = broken['economy/farm.cc'].replace('constexpr float stickiness = 1.2f;','constexpr float stickiness = 1.3f;')
        with self.assertRaises(AssertionError):v.transform(broken)
        values = {p['name']:p['default'] for p in v.SPEC['parameters']}
        for x in (float('nan'),1000):
            bad = dict(values,shop_gain_scale=x)
            with self.assertRaises(AssertionError):v.transform(self.original,bad)

    def test_base_policy_and_committed_both_required(self):
        sealed = {'a':'x'}
        digest = r.hashlib.sha256(json.dumps(sorted(sealed.items()),separators=(',',':')).encode()).hexdigest()
        policy = {'base':r.BASE,'base_source_sha256':digest}
        self.assertTrue(r.start_base_check(policy,sealed,sealed))
        self.assertFalse(r.start_base_check(policy,{'a':'y'},sealed))
        self.assertFalse(r.start_base_check(dict(policy,base='new'),sealed,sealed))

    def test_first_heavy_hold_and_started_preservation(self):
        with tempfile.TemporaryDirectory() as d, patch.object(r,'D',Path(d)), patch.object(r.subprocess,'check_output',return_value='cambc 5.0.1'):
            (Path(d)/'manifest.json').write_text(json.dumps({'engine':'cambc 5.0.1'}))
            with patch.object(r,'preflight',return_value={'ready':False}):
                with self.assertRaises(SystemExit):r.first_start()
                self.assertFalse((Path(d)/'first-heavy-start.json').exists())
            with patch.object(r,'preflight',return_value={'ready':True}):r.first_start()
            with patch.object(r,'preflight',side_effect=AssertionError('Started work must not retarget')):r.first_start()

if __name__=='__main__':unittest.main()
