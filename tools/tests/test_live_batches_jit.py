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
    test_burst_then_refill = test_successful_calls_have_no_local_wait = None
    test_server_rate_limit_is_retried = test_reserve_and_other_versions_wait = None

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

    def test_explicit_cells_can_check_current_without_changing_source_pin(self):
        oid, name = ls.TEAMS['mite']
        cells = [dict(map=f'map{i}', map_id=f'id{i}', side='a') for i in range(5)]
        source = dict(id='source', version=119, opp_id=oid, opp_name=name,
                      refset='r11', purpose='set', games=cells)
        ls.append_jsonl(ls.DATA/'tasks.jsonl', source)
        step = dict(id='book-current', lost_by=119, version=127, opp='mite', refset='r11',
                    pin='none', cells=[[c['map'], c['side']] for c in cells])
        self.B['after_done'] = []
        self.s.wake = lambda *a: None
        self.b.start_cells({}, self.B, step)
        planned = ls.read_jsonl(ls.DATA/'tasks.jsonl')
        self.assertEqual(planned[0], source)
        self.assertEqual(len(planned), 2)
        self.assertEqual(planned[1]['pin'], 'none')
        self.assertIsNone(planned[1]['refset'])
        self.assertEqual(planned[1]['games'], cells)
        self.assertEqual(self.B['cur']['task_ids'], [planned[1]['id']])
        self.assertEqual(self.B['cur']['rsets'], {'mite': None})

    def test_current_report_does_not_reuse_older_pinned_wins(self):
        common = dict(version=127, opp_id=ls.TEAMS['mite'][0], purpose='set', map='map', side='a')
        rows = [dict(common, task='old', match='old', group='old', pin='ref', refset='r11', result='win'),
                dict(common, task='now', match='now', group='now', pin='none', refset=None, result='loss'),
                dict(common, task='now', match='filler', group='now', pin='none', refset=None,
                     map='filler', filler=True, result='win')]
        for row in rows + [rows[1]]:
            ls.append_jsonl(ls.DATA/'games.jsonl', row)
        campaign = dict(version=127, rsets={'mite':'r11'}, task_ids=['now'])
        self.assertEqual(lb.observed(ls, campaign), {'mite:current':dict(cells=1,wins=0,losses=1)})
        # Legacy saved state carried r11 even for the current check; it still cannot borrow old wins.
        self.assertEqual(lb.paired(ls,127,118,campaign['rsets'],['now'])['mite']['cells'], 0)

    def test_current_cells_step_rejects_implicit_full_sweep(self):
        with self.assertRaisesRegex(ValueError, 'explicit cells'):
            self.b.start_cells({}, self.B, dict(id='bad', lost_by=119, version=127,
                                               opp='mite', refset='r11', pin='none'))

    def test_repin_can_limit_new_host_sweep_to_book_opponents(self):
        old={'fish':'r8','mite':'r11','cats':'r8'}
        (self.s.H/'refsets.json').write_text(json.dumps(old))
        (self.s.H/'HOST').write_text('/tmp/frozen-host\n')
        self.s.refsets=lambda: old
        self.s.upload_name=lambda d,given=None: given
        self.s.build=lambda c: (c,None)
        self.s.wake=lambda *args: None
        self.B['after_done']=[]
        step=dict(id='loss-book-r12',kind='repin_replay',choose='HOST',refsets={'mite':'r12'},
                  opponents=['fish','mite'],upload_name='Charybdis 525 + fuel 01-02')
        cur=self.b.start_after({},self.B,step)
        self.assertEqual(cur['rsets'],{'fish':'r8','mite':'r12'})
        self.assertEqual(cur['cand']['note'],'Charybdis 525 + fuel 01-02')
        self.assertEqual(json.loads((self.s.H/'refsets.json').read_text())['cats'],'r8')

    def test_cycle(self):
        # v118's own groups in flight (created, not played) don't hold the candidate back.
        for i in range(3):
            t = ctask(i, version=118)
            ls.append_jsonl(ls.DATA / "tasks.jsonl", t)
            self.create(t, 118)
        self.b.phase_rest({}, self.B, self.cur, 118, 118)
        self.assertEqual(self.activated, [])   # no quota room yet
        self.used = 100 - lb.RESERVE
        self.b.phase_rest({}, self.B, self.cur, 118, 118)
        self.assertEqual(self.activated, [])   # teammate reserve is not candidate quota
        self.used -= 4
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
        self.used = 100 - lb.RESERVE
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

    def test_short_quota_gap_keeps_candidate_but_long_gap_restores(self):
        ls.append_jsonl(ls.DATA/'tasks.jsonl',ctask(0))
        self.cur.update(phase='batch',batches=[dict(start=ls.now())])
        for seconds, expected in ((15,'batch'),(lb.REFILL_GRACE+60,'activate_rest')):
            reset = lb.datetime.datetime.fromtimestamp(time.time()+seconds,lb.datetime.timezone.utc).isoformat()
            with mock.patch.object(ls,'quota',return_value={'quota':dict(used=100,limit=100,resetsAt=reset)}):
                self.b.phase_batch({},self.B,self.cur,117,117)
            self.assertEqual(self.cur['phase'],expected)
        self.assertEqual(self.activated,[("submissions","activate","118")])

    def test_completed_campaign_restores_even_with_imminent_refill(self):
        t=ctask(0);ls.append_jsonl(ls.DATA/'tasks.jsonl',t);self.create(t,117)
        self.cur.update(phase='batch',task_ids=[t['id']],batches=[dict(start=ls.now())])
        with mock.patch.object(ls,'quota') as quota:
            self.b.phase_batch({},self.B,self.cur,117,117)
        quota.assert_not_called()
        self.assertEqual(self.cur['phase'],'activate_rest')

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
