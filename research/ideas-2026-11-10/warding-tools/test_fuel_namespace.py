"""Fuel gates must neither read normal-budget caches nor omit the engine argument."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

p = Path(__file__).resolve().parents[2]/'ideas-2026-11-09/freshgate-tools/fgate.py'
spec = importlib.util.spec_from_file_location('fgate', p)
f = importlib.util.module_from_spec(spec)
spec.loader.exec_module(f)

class FuelNamespace(unittest.TestCase):
    def tearDown(self):
        f.FUEL = None

    def test_normal_names_remain_unchanged(self):
        f.FUEL = None
        self.assertEqual(f.rname('variants/oc-example', 1, 'F', 'L'), f'fg{f.ENG}-example-dvn1F{f.tag("F")}-L')
        normal = f.rname('variants/oc-example', 1, 'M', 'f0')
        f.FUEL = 200000
        self.assertEqual(f.rname('variants/oc-example', 1, 'M', 'f0'), normal+'-fuel200000')

    def test_cache_requires_matching_budget(self):
        with tempfile.TemporaryDirectory() as d, patch.object(f, 'R', d+'/'):
            p=Path(d)/'replays/ab/test/summary.json';p.parent.mkdir(parents=True)
            for cached in (None, 100000, 200000):
                p.write_text(json.dumps(dict(games=256, errors=0, release=True, cambc=f.CAMBC, fuel=cached)))
                for selected in (None, 100000, 200000):
                    f.FUEL=selected
                    self.assertEqual(f.done('test',256),cached==selected)

    def test_command_passes_budget_to_both_team_engine_run(self):
        with tempfile.TemporaryDirectory() as d, patch.object(f,'LOCKS',d), patch.object(f,'LOGS',d), patch.object(f,'done',return_value=False), patch.object(f.dgate,'running_elsewhere',return_value=False), patch.object(f.subprocess,'Popen') as popen:
            for fuel in (None,200000):
                f.FUEL=fuel
                runner=f.Runner(1)
                self.assertFalse(runner.want('variants/oc-example',1,'M','f0','suite',256))
                cmd=popen.call_args.args[0]
                self.assertIn('--no-test-draft',cmd)
                self.assertEqual('--fuel' in cmd, fuel is not None)
                if fuel is not None:self.assertEqual(cmd[cmd.index('--fuel')+1],str(fuel))
                popen.call_args.kwargs['stdout'].close()

if __name__=='__main__': unittest.main()
