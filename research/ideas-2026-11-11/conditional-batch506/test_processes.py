from pathlib import Path
import os
import subprocess
import sys
import tempfile
import time
import unittest
from processes import drain, live_group


class OwnedGroupTests(unittest.TestCase):
    def test_exited_parent_cannot_leave_a_grandchild_in_next_phase(self):
        with tempfile.TemporaryDirectory() as tmp:
            ready = Path(tmp) / 'ready'
            code = "import subprocess,sys,pathlib;subprocess.Popen([sys.executable,'-c','import time;time.sleep(60)']);pathlib.Path(sys.argv[1]).write_text('ready')"
            process = subprocess.Popen([sys.executable, '-c', code, str(ready)], start_new_session=True,
                                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            try:
                process.wait(timeout=5)
                self.assertTrue(ready.exists())
                self.assertTrue(live_group(process.pid))
                drain(process, interrupt=True)
                self.assertFalse(live_group(process.pid))
            finally:
                drain(process, interrupt=True)

    def test_nested_phase_command_stays_in_outer_owned_session(self):
        with tempfile.TemporaryDirectory() as tmp:
            ready = Path(tmp) / 'nested'
            helper = "import subprocess,sys,pathlib,time;p=subprocess.Popen([sys.executable,'-c','import time;time.sleep(60)']);pathlib.Path(sys.argv[1]).write_text(str(p.pid));time.sleep(60)"
            code = "import sys;from run import command;command([sys.executable,'-c',sys.argv[1],sys.argv[2]],sys.argv[3])"
            env = dict(os.environ, PYTHONPATH=str(Path(__file__).parent), COND_RUNTIME_SESSION='1')
            process = subprocess.Popen([sys.executable, '-c', code, helper, str(ready), str(Path(tmp) / 'log')],
                                       start_new_session=True, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            try:
                deadline = time.monotonic() + 5
                while not ready.exists() and time.monotonic() < deadline:
                    time.sleep(.01)
                self.assertTrue(ready.exists())
                grandchild = int(ready.read_text())
                stat = Path('/proc') / str(grandchild) / 'stat'
                self.assertEqual(int(stat.read_text().split(') ', 1)[1].split()[2]), process.pid)
                drain(process, interrupt=True)
                self.assertFalse(live_group(process.pid))
                if stat.exists():
                    self.assertEqual(stat.read_text().split(') ', 1)[1].split()[0], 'Z')
            finally:
                drain(process, interrupt=True)


if __name__ == '__main__':
    unittest.main()
