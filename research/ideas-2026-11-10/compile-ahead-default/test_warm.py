import contextlib
import importlib.util
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
spec=importlib.util.spec_from_file_location('warm',Path(__file__).with_name('prototype_warm.py'));warm=importlib.util.module_from_spec(spec);spec.loader.exec_module(warm)

class WarmTests(unittest.TestCase):
    def exercise(self,slots,failed=False):
        with tempfile.TemporaryDirectory() as td:
            d=Path(td);bot=d/'frozen/bot';(bot/'src').mkdir(parents=True);(bot/'src/a.cc').write_text('fixture');(bot/'.cambc/build-release').mkdir(parents=True);(bot/'.cambc/build-release/bot-injected.wasm').write_bytes(b'fixture');(d/'ready').mkdir();(d/'logs').mkdir()
            marker=d/'body.json';marker.write_text(json.dumps({'task':[9,'Flp4'],'frozen':str(bot),'source':{'a.cc':warm.sha(bot/'src/a.cc')}}));held=list(range(slots));events=[]
            cpu=SimpleNamespace(acquire=lambda want,least:held,release=lambda got:events.append(('released',got)),exclusive=lambda p:contextlib.nullcontext())
            def run(argv,**kwargs):
                events.append(('run',argv));self.assertEqual(slots,16);self.assertNotIn('--slots',argv);self.assertNotIn('--slot-dir',argv);self.assertEqual(argv[argv.index('--jobs')+1],'1');self.assertEqual(kwargs['env']['RAYON_NUM_THREADS'],'1');return SimpleNamespace(returncode=1 if failed else 0)
            with patch.object(warm,'D',d),patch.object(warm,'verify'),patch.object(warm,'active',return_value=True),patch.object(warm,'cpu_slots',cpu,create=True),patch.object(warm,'ahead',SimpleNamespace(CLI=Path('/fake/runner')),create=True),patch.object(warm,'cambc_env',SimpleNamespace(env=lambda serial:{}),create=True),patch.object(warm.subprocess,'run',side_effect=run):
                if failed:
                    with self.assertRaises(AssertionError):warm.prepare(marker)
                else:self.assertEqual(warm.prepare(marker),slots==16)
            self.assertEqual(events[-1],('released',held));self.assertEqual(sum(x[0]=='run' for x in events),int(slots==16));self.assertEqual((d/'ready/9-Flp4.json').exists(),slots==16 and not failed)
    def test_partial_reservation_immediately_released_without_warm(self):self.exercise(15)
    def test_exact_sixteen_warms_once_and_releases(self):self.exercise(16)
    def test_failed_warm_releases_all_slots(self):self.exercise(16,True)

if __name__=='__main__':unittest.main()
