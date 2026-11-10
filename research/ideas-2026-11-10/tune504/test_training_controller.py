"""Exercise600 actual SPSA controller iterations with a fake runner; zero games/builds."""
import contextlib
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

T=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('training_under_test',T/'training.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)

class Controller(unittest.TestCase):
    def exercise(self, missing=False):
        with tempfile.TemporaryDirectory() as tmp:
            d=Path(tmp);runs=d/'runs';run=runs/m.RUN;run.mkdir(parents=True)
            maps=d/'maps';maps.mkdir()
            rows=[]
            for i in range(24):
                p=maps/f'm{i}.map26a';p.write_text(str(i));rows.append({'path':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
            cfg={'bot':'unused','opps':[f'opp{i}' for i in range(6)],'pool':[str(maps)],'params':{'x':[0,1,'float']},
                 'maps_per_iter':24,'pairs':4,'weights':{'win':.9,'gems':.1,'gold':0},'a':.2,'A':100,'alpha':.602,'c':.1,'gamma':.101,'inflight':1,'seed':24138}
            for p in (d/'config.json',run/'config.json'):p.write_text(json.dumps(cfg))
            (d/'training-inputs.json').write_text('{}');(d/'maps.json').write_text(json.dumps({'selected':rows}))
            (run/'state.json').write_text(json.dumps({'k':0,'x':{'x':.5}}))
            calls=[]
            class FakeBatch:
                def __init__(self,run,cfg,cands,games,tag,base=None):
                    self.cfg,self.cands,self.games,self.tag=cfg,cands,games,tag
                    self.n=len(cands)*len(games);self.work=run/'work'/tag;self.work.mkdir(parents=True)
                    self.proc=SimpleNamespace(returncode=0);self.wall=0
                def start(self):calls.append(self.tag);return self
                def wait(self):pass
                def finish(self):
                    return {name:[(0.0,0.0,j) for j in range(143 if missing else 144)] for name in self.cands}
            with patch.object(m,'D',d),patch.object(m.tune,'RUNS',runs),patch.object(m.tune.patch,'Base',lambda _:None),\
                 patch.object(m.tune,'Batch',FakeBatch),patch.object(m.tune.cpu_slots,'acquire',lambda *a,**k:[object()]),patch.object(m.tune.cpu_slots,'release',lambda _:None),patch.object(m.tune.cambc_env,'check_local_header',lambda:None),\
                 patch.object(m.sys,'argv',['training.py','train']),contextlib.redirect_stdout(io.StringIO()):
                if missing:
                    with self.assertRaises(AssertionError):m.main()
                    self.assertEqual(json.loads((run/'state.json').read_text())['k'],0)
                    self.assertTrue((run/'work/it0').exists())
                else:
                    m.main()
                    self.assertEqual(calls,[f'it{i}' for i in range(600)])
                    h=[json.loads(x) for x in (run/'history.jsonl').read_text().splitlines()]
                    self.assertEqual([x['k'] for x in h[300:600]],list(range(301,601)))
    def test_exact_budget(self):self.exercise()
    def test_incomplete_batch_does_not_update(self):self.exercise(missing=True)

if __name__=='__main__':unittest.main()
