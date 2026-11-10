"""Force a fairness scan between member creation and its lifetime lock."""
import importlib.util
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

SOURCE = Path(os.environ.get('CPU_SLOTS_TEST_SOURCE', Path(__file__).resolve().parents[1] / 'cpu_slots.py'))
SCAN = """import importlib.util,sys
s=importlib.util.spec_from_file_location('slots',sys.argv[1]);m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
h=m.acquire(1);m.release(h)
"""


@unittest.skipIf(sys.platform == "win32", "fair-share membership uses flock")
class MemberPublication(unittest.TestCase):
    def test_scan_before_lock_preserves_live_weight_and_prunes_dead_member(self):
        with tempfile.TemporaryDirectory() as pool, mock.patch.dict(os.environ, {
            'CAMBC_SLOT_DIR': pool, 'CAMBC_SLOTS': '2', 'CAMBC_SLOT_GROUP': 'weighted-owner', 'CAMBC_SLOT_WEIGHT': '35',
        }):
            spec = importlib.util.spec_from_file_location('slots_under_test', SOURCE)
            slots = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(slots)
            scanner_env = dict(os.environ, CAMBC_SLOT_GROUP='scanner', CAMBC_SLOT_WEIGHT='1')

            def scan():
                subprocess.run([sys.executable, '-c', SCAN, str(SOURCE)], env=scanner_env, check=True, timeout=10)

            real_flock = slots.fcntl.flock
            scanned = False

            def before_lock(fd, op):
                nonlocal scanned
                if op == slots.fcntl.LOCK_EX and not scanned:
                    scanned = True
                    scan()
                return real_flock(fd, op)

            with mock.patch.object(slots.fcntl, 'flock', before_lock):
                slots._set_waiting(1)
            try:
                self.assertTrue(scanned)
                self.assertEqual(os.fstat(slots._member.fileno()).st_nlink, 1, 'scanner unlinked a live registration')
                scan()
                members = [p for p in (Path(pool) / 'members').iterdir() if p.read_text().startswith('weighted-owner\t')]
                self.assertEqual(len(members), 1)
                member = members[0]
                self.assertEqual(member.read_text(), 'weighted-owner\t35.0\t1\n')
                self.assertEqual(member.stat().st_ino, os.fstat(slots._member.fileno()).st_ino)
            finally:
                slots._member.close()
            scan()
            self.assertFalse(member.exists(), 'dead registrations must still be reclaimed')


if __name__ == '__main__':
    unittest.main()
