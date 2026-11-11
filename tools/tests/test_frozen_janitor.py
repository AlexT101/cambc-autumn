"""tools/frozen_janitor.py on a scratch replays/frozen and runner cache (never the real ones)."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

TOOLS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TOOLS))
import frozen_janitor as fj  # noqa: E402

OLD = time.time() - 30 * 86400


def old(*paths):
    for p in paths:
        os.utime(p, (OLD, OLD))


class JanitorTests(unittest.TestCase):
    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        base = Path(self.td.name)
        self.frozen, self.cache = base / "replays" / "frozen", base / "cache"
        for name in ("aaaaaaaaaaaa", "bbbbbbbbbbbb", "cccccccccccc"):
            wasm = self.frozen / name / "bot" / ".cambc" / "build-release" / "bot.wasm"
            wasm.parent.mkdir(parents=True)
            wasm.write_bytes(b"w")
            (self.frozen / name / "build.lock").touch()
        (self.cache / "native").mkdir(parents=True)
        (self.cache / "modules").mkdir()
        self.lib_old = self.cache / "native" / f"{'1' * 32}-4dff7d93.so"
        self.lib_open = self.cache / "native" / f"{'2' * 32}-4dff7d93.so"
        self.lib_new = self.cache / "native" / f"{'3' * 32}-4dff7d93.so"
        self.work = self.cache / "native" / f".{'4' * 32}-4dff7d93.999999999"
        self.work.mkdir()
        for f in (self.lib_old, self.lib_open, self.lib_new):
            f.write_bytes(b"so")
        old(self.lib_old, self.lib_open, self.work)
        for name in ("aaaaaaaaaaaa", "bbbbbbbbbbbb"):  # c stays recent
            d = self.frozen / name
            old(d / "bot" / ".cambc" / "build-release" / "bot.wasm", d / "bot", d)
        # b is in use: a process works in it; the old library is open in another.
        self.procs = [subprocess.Popen(["sleep", "30"], cwd=self.frozen / "bbbbbbbbbbbb" / "bot"),
                      subprocess.Popen(["sh", "-c", "exec 3<\"$0\"; sleep 30", str(self.lib_open)])]
        time.sleep(0.3)
        self.patches = [patch.object(fj, "FROZEN", self.frozen), patch.object(fj, "CACHE", self.cache)]
        for p in self.patches:
            p.start()

    def tearDown(self):
        for p in self.procs:
            p.kill()
            p.wait()
        for p in self.patches:
            p.stop()
        self.td.cleanup()

    def run_main(self, *argv):
        with patch.object(sys, "argv", ["frozen_janitor.py", *argv]):
            self.assertEqual(fj.main(), 0)

    def test_dry_run_deletes_nothing(self):
        self.run_main()
        self.assertTrue(all((self.frozen / n).is_dir() for n in ("aaaaaaaaaaaa", "bbbbbbbbbbbb", "cccccccccccc")))
        self.assertTrue(self.lib_old.exists() and self.work.exists())

    def test_delete_keeps_recent_and_referenced_entries(self):
        self.run_main("--delete")
        self.assertFalse((self.frozen / "aaaaaaaaaaaa").exists())
        self.assertTrue((self.frozen / "bbbbbbbbbbbb").is_dir())  # a process's cwd is inside it
        self.assertTrue((self.frozen / "cccccccccccc").is_dir())  # used recently
        self.assertFalse(self.lib_old.exists())
        self.assertTrue(self.lib_open.exists())  # open in a process
        self.assertTrue(self.lib_new.exists())
        self.assertFalse(self.work.exists())  # a dead builder's work dir
        self.assertEqual([p.name for p in self.frozen.iterdir() if p.name.startswith(".")], [])

    def test_a_held_build_lock_keeps_a_copy(self):
        import fcntl
        with open(self.frozen / "aaaaaaaaaaaa" / "build.lock", "a+b") as f:
            fcntl.flock(f, fcntl.LOCK_EX)
            self.run_main("--delete", "--only", "frozen")
        self.assertTrue((self.frozen / "aaaaaaaaaaaa").is_dir())

    def test_keep_days_has_a_floor(self):
        with patch.object(sys, "argv", ["frozen_janitor.py", "--keep-days", "1"]), self.assertRaises(SystemExit):
            fj.main()


if __name__ == "__main__":
    unittest.main()
