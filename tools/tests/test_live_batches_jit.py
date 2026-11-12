"""Just-in-time candidate activation (user 2026-11-12): the scheduler selects the candidate only while the runner creates
its groups, then the rest version again without waiting for them to play; the runner marks suspect only groups created
since its last live/selected read. python -m unittest discover -s tools/tests -p test_live_batches_jit.py -v"""
import json
import sys
import tempfile
import threading
import time
import types
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import ladder_scrims as ls  # noqa: E402
import live_batches as lb  # noqa: E402
import test_ladder_scrims_run as base  # noqa: E402
from test_ladder_scrims_run import FakeApi, task  # noqa: E402


class SwitchApi(FakeApi):
    """live and selected apart; `switch_after` creates later, selected (and live) become `to`."""

    def __init__(self, switch_after=None, to=None, **kw):
        super().__init__(**kw)
        self.selected, self.switch_after, self.to = self.live, switch_after, to

    def run(self, cmd, **kw):
        a = cmd[1:]
        if a[:2] == ["submissions", "list"]:
            self.calls.append((time.monotonic(), "submissions", "list", threading.current_thread().name))
            return types.SimpleNamespace(returncode=0, stdout=f"Live: {self.live}  Selected: {self.selected}\n",
                                         stderr="")
        r = super().run(cmd, **kw)
        if a[:2] == ["match-groups", "create"] and r.returncode == 0 and self.switch_after is not None:
            self.switch_after -= 1
            if self.switch_after == 0:
                self.live = self.selected = self.to
        return r


class RunnerSuspect(base.RunTest):
    # The base class's own tests run in their module.
    test_burst_then_refill = test_calls_are_spaced_and_creates_go_first = None
    test_bucket = test_reserve_and_other_versions_wait = None

    def events(self, kind):
        return [e for e in ls.read_jsonl(ls.DATA / "events.jsonl") if e["ev"] == kind]

    def test_switch_between_passes_marks_nothing(self):
        # The scheduler's switch: v118's groups still playing when v117 is selected; they stay valid.
        api = SwitchApi(play=30)
        self.start(api, [task(i, pin="none") for i in range(5)], exit_when_done=False)
        self.wait(lambda: len(self.created()) == 5)
        with ls.live_lock(ls.DATA):   # as the scheduler switches: never inside a create pass
            api.live = api.selected = 117
        for i in range(5, 8):
            ls.append_jsonl(ls.DATA / "tasks.jsonl", task(i, version=117, pin="none"))
        self.wait(lambda: len(self.created()) == 8)
        self.assertEqual([e["live"] for e in self.created()], [118] * 5 + [117] * 3)
        self.assertEqual(len(self.events("live_change")), 1)
        self.assertEqual(self.events("suspect"), [])

    def test_switch_inside_a_pass_marks_groups_since_last_read(self):
        # An outside switch after the 4th create, seen at the re-read after the 6th: 4-6 may have bound to it; 1-3
        # were confirmed by the re-read after the 3rd.
        api = SwitchApi(play=30, switch_after=4, to=117)
        self.start(api, [task(i, pin="none") for i in range(9)], recheck=3, exit_when_done=False)
        self.wait(lambda: len(self.events("suspect")) == 3)
        time.sleep(0.3)
        ids = [e["task"] for e in self.created()]
        self.assertEqual(ids, [f"t{i:03d}" for i in range(6)])   # the pass stopped at the switch
        self.assertEqual([e["task"] for e in self.events("suspect")], ids[3:])


class FakeSched:
    def __init__(self, home):
        self.ls, self.H, self.logs = ls, home, []

    def now(self):
        return ls.now()

    def log(self, m):
        self.logs.append(m)

    def save(self, st):
        pass


def ctask(i, version=117, purpose="set"):
    return dict(task(i, version=version, pin="none"), id=f"v{version}-{purpose}-{i:02d}", purpose=purpose,
                campaign="batches")


class SchedPhases(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.saved = ls.DATA
        ls.DATA = Path(self.tmp.name)
        self.s = FakeSched(Path(self.tmp.name))
        self.b = lb.Batches(self.s, None)
        self.used, self.activated = 100, []
        self.patches = [mock.patch.object(ls, "quota", lambda: {"quota": {"used": self.used, "limit": 100}}),
                        mock.patch.object(ls, "cambc", lambda *a, **k: self.activated.append(a) or ""),
                        mock.patch.object(lb, "specs", lambda _ls, v, *a, **k: [ctask(i, version=v) for i in range(10)])]
        for p in self.patches:
            p.start()
        self.B = {"rest": 118, "cur": None, "done": [], "switches": [], "obs": {}}
        self.cur = {"cand": None, "label": "v117 test", "version": 117, "rsets": {"fish": "r8"}, "phase": "rest",
                    "batches": []}
        self.B["cur"] = self.cur

    def tearDown(self):
        for p in self.patches:
            p.stop()
        ls.DATA = self.saved
        self.tmp.cleanup()

    def create(self, t, version):
        ls.append_jsonl(ls.DATA / "events.jsonl", {"ev": "created", "task": t["id"], "group": "g-" + t["id"],
                                                   "at": ls.now(), "live": version, "selected": version})

    def test_cycle(self):
        # v118's own groups in flight (created, not played) don't hold the candidate back.
        for i in range(3):
            t = ctask(i, version=118)
            ls.append_jsonl(ls.DATA / "tasks.jsonl", t)
            self.create(t, 118)
        self.b.phase_rest({}, self.B, self.cur, 118, 118)
        self.assertEqual(self.activated, [])   # no quota room yet
        self.used = 96
        self.b.phase_rest({}, self.B, self.cur, 118, 118)
        self.assertEqual(self.cur["phase"], "activate_batch")
        self.assertEqual(self.activated, [("submissions", "activate", "117")])
        self.assertEqual(sum(t["version"] == 117 for t in ls.read_jsonl(ls.DATA / "tasks.jsonl")), 10)
        self.b.phase_activate_batch({}, self.B, self.cur, 118, 117)   # selected, not live yet
        self.assertEqual(self.cur["phase"], "activate_batch")
        self.b.phase_activate_batch({}, self.B, self.cur, 117, 117)
        self.assertEqual(self.cur["phase"], "batch")
        self.b.phase_batch({}, self.B, self.cur, 117, 117)   # the runner has not created yet: stay
        self.assertEqual(self.cur["phase"], "batch")
        for i in range(4):   # the runner fills the room; none has played
            self.create(ctask(i), 117)
        self.used = 100
        self.b.phase_batch({}, self.B, self.cur, 117, 117)
        self.assertEqual(self.cur["phase"], "activate_rest")
        self.assertEqual(self.activated[-1], ("submissions", "activate", "118"))
        self.assertEqual(self.cur["batches"][-1]["created"], 4)
        self.b.phase_activate_rest({}, self.B, self.cur, 118, 118)
        self.assertEqual(self.cur["phase"], "rest")

    def test_rest_opp_checks_hold_the_switch(self):
        ls.append_jsonl(ls.DATA / "tasks.jsonl", ctask(0, version=118, purpose="oppcheck"))
        self.used = 50
        self.b.phase_rest({}, self.B, self.cur, 118, 118)
        self.assertEqual((self.cur["phase"], self.activated), ("rest", []))

    def test_all_created_finishes_without_waiting_for_play(self):
        for i in range(10):
            t = ctask(i)
            ls.append_jsonl(ls.DATA / "tasks.jsonl", t)
            self.create(t, 117)
        self.used = 50
        self.b.phase_rest({}, self.B, self.cur, 118, 118)
        self.assertIsNone(self.B["cur"])
        self.assertEqual(self.B["done"][0]["phase"], "created")


if __name__ == "__main__":
    unittest.main()
