import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
from types import SimpleNamespace
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import experiment_config as ec
import run_batched as rb

class ConfigTests(unittest.TestCase):
 def test_side_swap_and_exact_candidate(self):
  c={'map':{'seed':2**64-1,'salt':17,'unmetered':True}}
  self.assertEqual(ec.teams(c,'map.map26a',(0,1)),{'a':None,'b':c['map']})
  self.assertEqual(ec.teams(c,'map.map26a',(1,0)),{'a':c['map'],'b':None})
  self.assertEqual(ec.suffix(None,'map.map26a',(0,1)),'')
 def test_missing_invalid_and_recorded_hash(self):
  with tempfile.TemporaryDirectory() as td:
   p=Path(td)/'c.json';d={'schema':1,'opponent_index':1,'maps':{'map':{'seed':1,'salt':2,'unmetered':True}}};p.write_text(json.dumps(d))
   c,proof=ec.load(p,['map.map26a']);self.assertEqual(len(proof['sha256']),64)
   with self.assertRaises(ValueError):ec.load(p,['missing.map26a'])
   for key,val in [('seed',-1),('salt',True),('unmetered',1)]:
    bad=json.loads(json.dumps(d));bad['maps']['map'][key]=val;p.write_text(json.dumps(bad))
    with self.assertRaises(ValueError):ec.load(p,['map.map26a'])
 def test_prepare_reservation_partial_release_and_failure_cleanup(self):
  for code in [0,1]:
   with self.subTest(code=code),tempfile.TemporaryDirectory() as td:
    events=[];partial=list(range(4));full=list(range(16));env={}
    def run(argv,**kwargs):
     self.assertEqual(events,[('release',4)]);self.assertIn('--prepare-only',argv)
     events.append(('prepare',16));return SimpleNamespace(returncode=code)
    with patch.object(rb.cpu_slots,'acquire',side_effect=[partial,full]),patch.object(rb.cpu_slots,'release',side_effect=lambda h:events.append(('release',len(h)))),patch.object(rb,'sleep'),patch.object(rb.subprocess,'run',side_effect=run):
     if code:
      with self.assertRaises(RuntimeError):rb.prepare_experiment_cache('runner',Path(td)/'manifest',[],env,Path(td)/'log')
     else:rb.prepare_experiment_cache('runner',Path(td)/'manifest',[],env,Path(td)/'log')
    self.assertEqual(events,[('release',4),('prepare',16),('release',16)])
    self.assertEqual(env['FASTRUNNER_BUILT'],'1')
if __name__=='__main__':unittest.main()
