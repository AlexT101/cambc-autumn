import importlib.util
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch
import run

spec=importlib.util.spec_from_file_location('tested_ahead',run.R/'tools/gate_compile_ahead.py')
ahead=importlib.util.module_from_spec(spec);spec.loader.exec_module(ahead)


class Controls(unittest.TestCase):
    def test_window_is_conditional_range_and_current_first(self):
        with patch.object(ahead,'PLAN',{'bodies':['Flp4','Mt3qro'],'lookahead':8}):
            self.assertEqual(ahead.window(0,1004,2003),[(k,b) for k in range(1004,1013) for b in ('Flp4','Mt3qro')])
            self.assertEqual(ahead.window(2002,1004,2003),[(2003,'Flp4'),(2003,'Mt3qro')])
            self.assertEqual(ahead.window(2003,1004,2003),[])

    def test_stop_marker_overrides_live_owner(self):
        with tempfile.TemporaryDirectory() as td:
            stop=Path(td)/'stop'
            with patch.object(ahead,'PLAN',{'stop_file':str(stop),'owner':{}}),patch.object(ahead,'same_owner',return_value=True):
                self.assertTrue(ahead.active());stop.touch();self.assertFalse(ahead.active())

    def lifecycle(self, gate_rc=0, helper_start_error=False, identity_error=False, stop_write_error=False, interrupted=False):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);(root/'chanM').mkdir();(root/'manifest.json').write_text('{}')
            stop=root/'chanM/compile-ahead/stop';events=[]
            class Gate:
                pid=111;done=False;was_interrupted=False
                def poll(self):return gate_rc if self.done else None
                def wait(self):
                    events.append('gate wait')
                    if interrupted and not self.was_interrupted:
                        self.was_interrupted=True;raise KeyboardInterrupt()
                    self.done=True;return gate_rc
            class Helper:
                pid=222
                def wait(self):
                    assert stop.exists() or (stop_write_error and events==['gate wait'])
                    events.append('helper drain after stop');return 0
            calls=[]
            def popen(argv,**kwargs):
                calls.append(argv)
                if len(calls)==1:return Gate()
                if helper_start_error:raise OSError('fixture start failure')
                return Helper()
            original_write=Path.write_text
            def write_text(path,*args,**kwargs):
                if stop_write_error and path==stop:raise OSError('fixture stop marker failure')
                return original_write(path,*args,**kwargs)
            # The real identity helper can read a valid process; no child or build is created.
            with patch.object(run,'D',root),patch.object(run.subprocess,'Popen',side_effect=popen),patch.object(run.importlib.util,'module_from_spec') as make,patch.object(Path,'write_text',new=write_text):
                module=make.return_value;module.wait_drained.side_effect=lambda process:process.wait();module.interrupt_owned_tree.return_value={};module.identity.return_value={'pid':111,'start':'fixture','cmdline':'gate','state':'S'}
                if identity_error:module.identity.side_effect=OSError('fixture identity read failure')
                with patch.object(run.importlib.util,'spec_from_file_location') as make_spec:
                    make_spec.return_value.loader.exec_module.return_value=None
                    if interrupted:
                        with self.assertRaises(KeyboardInterrupt):run.gate_phase('chanM')
                        module.interrupt_owned_tree.assert_called_once_with(module.identity.return_value)
                    elif gate_rc:
                        with self.assertRaises(subprocess.CalledProcessError):run.gate_phase('chanM')
                    else:run.gate_phase('chanM')
            self.assertEqual(len(calls),1 if identity_error else 2)  # Never restart the scored gate.
            self.assertEqual(stop.exists(),not stop_write_error)
            self.assertEqual(events,['gate wait','gate wait','helper drain after stop'] if interrupted else ['gate wait'] if helper_start_error or identity_error else ['gate wait','helper drain after stop'])

    def test_interrupt_waits_original_gate_and_drains_helper(self):self.lifecycle(interrupted=True)

    def test_gate_success_drains_helper_before_return(self):self.lifecycle()
    def test_gate_failure_still_drains_helper(self):self.lifecycle(gate_rc=1)
    def test_helper_start_failure_does_not_restart_gate(self):self.lifecycle(helper_start_error=True)
    def test_identity_failure_still_waits_original_gate(self):self.lifecycle(identity_error=True)
    def test_stop_marker_failure_still_drains_helper(self):self.lifecycle(stop_write_error=True)


if __name__=='__main__':unittest.main()
