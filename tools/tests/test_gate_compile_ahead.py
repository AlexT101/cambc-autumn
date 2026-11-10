import importlib.util
import json
from pathlib import Path
import signal
import subprocess
import sys
import time
import tempfile
import unittest
from unittest.mock import patch

spec=importlib.util.spec_from_file_location('resource_ahead',Path(__file__).resolve().parents[1]/'gate_compile_ahead.py')
ahead=importlib.util.module_from_spec(spec);spec.loader.exec_module(ahead)


class ScopeTests(unittest.TestCase):
    def test_default_window(self):
        with patch.object(ahead,'PLAN',{'bodies':['Flp4','Mt3q']}):
            tasks=ahead.window(99,1,1000)
            self.assertEqual(len(tasks),18)
            self.assertEqual(tasks[0],(100,'Flp4'))
            self.assertEqual(tasks[-1],(108,'Mt3q'))
            self.assertEqual(ahead.DEFAULT_WORKERS,16)

    def test_interrupt_drains_exact_tree_and_preserves_unrelated_process(self):
        with tempfile.TemporaryDirectory() as td:
            ready=Path(td)/'ready'
            child_code="import signal,time; signal.signal(signal.SIGINT,lambda *_:exit(0)); time.sleep(60)"
            parent_code=("import subprocess,sys,time,signal; from pathlib import Path; "
                         "signal.signal(signal.SIGINT,lambda *_:exit(0)); "
                         "p=subprocess.Popen([sys.executable,'-c',sys.argv[2]]); "
                         "Path(sys.argv[1]).write_text(str(p.pid)); time.sleep(60)")
            unrelated=subprocess.Popen([sys.executable,'-c',child_code])
            parent=subprocess.Popen([sys.executable,'-c',parent_code,str(ready),child_code])
            child=None
            try:
                deadline=time.monotonic()+5
                while not ready.exists() and time.monotonic()<deadline:time.sleep(.01)
                self.assertTrue(ready.exists());child=int(ready.read_text())
                owner=ahead.identity(parent.pid)
                tracked=ahead.interrupt_owned_tree(owner)
                parent.wait(timeout=5)
                self.assertIn(child,tracked)
                self.assertFalse(ahead.same_owner(owner))
                actual=ahead.identity(child)
                self.assertTrue(actual is None or actual['state']=='Z')
                self.assertIsNone(unrelated.poll())
                # A reused PID identity must never signal an unrelated live process.
                forged=ahead.identity(unrelated.pid);forged['start']='not-the-live-start'
                ahead.interrupt_owned_tree(forged)
                self.assertIsNone(unrelated.poll())
            finally:
                for proc in (parent,unrelated):
                    if proc.poll() is None:proc.kill()
                    proc.wait()
                if child:
                    actual=ahead.identity(child)
                    if actual and actual['state']!='Z':
                        import os
                        os.kill(child,signal.SIGKILL)

    def test_inprocess_interrupt_drains_scored_child_without_signaling_self(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);manifest=root/'manifest.json';manifest.write_text('{}')
            directory=root/'helper';real_popen=subprocess.Popen;child=None;events=[]
            helper_code="import sys,time;from pathlib import Path; p=Path(sys.argv[1]);\nwhile not p.exists():time.sleep(.01)"
            real_helper=real_popen([sys.executable,'-c',helper_code,str(directory/'stop')])
            class Helper:
                pid=real_helper.pid;waits=0
                def wait(self):
                    self.waits+=1
                    if self.waits==1:raise KeyboardInterrupt()
                    events.append('helper drained');return real_helper.wait(timeout=5)
            helper=Helper()
            try:
                with patch.object(ahead.subprocess,'Popen',return_value=helper):
                    with self.assertRaises(KeyboardInterrupt):
                        with ahead.scope(directory,manifest,root/'blocks',root/'fgate.py',['Flp4','Mt3q']):
                            child=real_popen([sys.executable,'-c','import time;time.sleep(60)'])
                            raise KeyboardInterrupt()
                self.assertIsNotNone(child.poll())
                self.assertEqual(events,['helper drained'])
                status=json.loads((directory/'lifecycle.json').read_text())
                self.assertTrue(status['interrupted'])
                self.assertEqual(status['helper_exit'],0)
                self.assertNotIn(str(real_helper.pid),status['interrupted_tree'])
                self.assertIn(str(child.pid),status['interrupted_tree'])
            finally:
                if real_helper.poll() is None:real_helper.kill()
                real_helper.wait()
                if child is not None:
                    if child.poll() is None:child.kill()
                    child.wait()

    def scoped(self, phase_error=False, stop_failure=False, disabled=False):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);manifest=root/'manifest.json';manifest.write_text('{}')
            directory=root/'helper';events=[];owner={'pid':1,'start':'fixture','cmdline':'owner','state':'S'}
            class Helper:
                pid=2
                def poll(self):return None
                def send_signal(self,sig):self_signal=sig;events.append(('signal',self_signal))
                def wait(self):
                    assert (directory/'stop').exists() or events[-1]==('signal',signal.SIGINT)
                    events.append('drained');return 0
            original=Path.write_text
            def writing(path,*args,**kwargs):
                if stop_failure and path==directory/'stop':raise OSError('fixture marker failure')
                return original(path,*args,**kwargs)
            with patch.object(ahead,'identity',return_value=owner),patch.object(ahead.subprocess,'Popen',return_value=Helper()) as launched,patch.object(Path,'write_text',new=writing):
                try:
                    with ahead.scope(directory,manifest,root/'blocks',root/'fgate.py',['Flp4','Mt3q'],enabled=not disabled):
                        events.append('phase')
                        if phase_error:raise ValueError('fixture gate error')
                except ValueError:
                    self.assertTrue(phase_error)
                self.assertEqual(launched.call_count,0 if disabled else 1)
            self.assertEqual(events,['phase'] if disabled else ['phase',('signal',signal.SIGINT),'drained'] if stop_failure else ['phase','drained'])
            if not disabled:
                plan=json.loads((directory/'plan.json').read_text())
                self.assertEqual((plan['workers'],plan['lookahead']),(16,8))

    def test_inprocess_phase_drains_before_return(self):self.scoped()
    def test_phase_exception_drains(self):self.scoped(phase_error=True)
    def test_stop_write_failure_signals_only_helper_and_drains(self):self.scoped(stop_failure=True)
    def test_optout_starts_no_helper(self):self.scoped(disabled=True)


if __name__=='__main__':unittest.main()
