"""`ladder_scrims.py run` against a fake CLI: bursts to the quota, pins usable once played, unpaced calls, and server retry handling. python -m unittest discover -s tools/tests -p test_ladder_scrims_run.py -v"""
import json
import sys
import tempfile
import threading
import time
import types
import unittest
import uuid
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import ladder_scrims as ls  # noqa: E402

GAP = 0.02


class FakeApi:
    """The platform behind `cambc`: a rolling quota and groups that finish after `play` seconds."""

    def __init__(self, limit=100, used=0, play=0.5, live=118):
        self.limit, self.used, self.play, self.live = limit, used, play, live
        self.groups, self.calls, self.lock, self.last, self.limited = {}, [], threading.Lock(), 0.0, 0

    def status(self, g):
        return "finished" if time.monotonic() - g["t"] >= self.play else "running"

    def matches(self, gid):
        g = self.groups[gid]
        return [{"groupId": gid, "matchId": f"{gid}-{i}", "position": i, "status": self.status(g), "map": f"m{i}",
                 "mapId": f"id{i}", "teams": [{"teamId": ls.MY_TEAM, "side": "a", "result": "win", "draftPicks": [0]},
                                              {"teamId": "opp", "name": "Opp", "side": "b", "draftPicks": [1]}]}
                for i in range(1, 6)]

    def run(self, cmd, **kw):
        a = cmd[1:]
        if a[0] == "summary":   # converts a downloaded file: never reaches the API
            return types.SimpleNamespace(returncode=0, stdout="{}", stderr="")
        with self.lock:
            t = time.monotonic()
            self.calls.append((t, a[0], a[1] if len(a) > 1 else "", threading.current_thread().name))
            out = ""
            if a[:2] == ["match-groups", "quota"]:
                out = json.dumps({"ready": True, "quota": {"used": self.used, "limit": self.limit}})
            elif a[:2] == ["submissions", "list"]:
                out = f"Live: {self.live}  Selected: {self.live}\n"
            elif a[:2] == ["match-groups", "create"]:
                if self.used >= self.limit:
                    return types.SimpleNamespace(returncode=1, stdout="", stderr="error: quota exceeded (HTTP 403)")
                gid = str(uuid.uuid4())
                self.groups[gid] = {"t": t, "source": a[a.index("--source-group") + 1] if "--source-group" in a else None}
                self.used += 1
                out = json.dumps({"groupId": gid})
            elif a[:2] == ["matches", "list"]:
                rows = [m for gid in reversed(list(self.groups)) for m in self.matches(gid)]
                start = int(a[a.index("--cursor") + 1]) if "--cursor" in a else 0
                out = json.dumps({"matches": rows[start:start + 100],
                                  "nextCursor": str(start + 100) if start + 100 < len(rows) else None})
            elif a[:2] == ["match-groups", "show"]:
                out = json.dumps({"matches": self.matches(a[2])})
            elif a[0] == "matches" and "-o" in a:
                Path(a[a.index("-o") + 1]).write_bytes(b"x")
            return types.SimpleNamespace(returncode=0, stdout=out, stderr="")


def task(i, version=118, pin="ref", prio=90):
    return {"id": f"t{i:03d}", "version": version, "purpose": "set", "opp_id": "opp", "opp_name": "Opp", "pin": pin,
            "refset": "r8", "priority": prio, "games": [{"map": f"m{j}", "map_id": f"id{j}", "side": "a"}
                                                         for j in range(1, 6)]}


class RunTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.saved = (ls.DATA, ls.REPLAYS, ls.subprocess.run, ls.ROOT)
        self.main_thread = ls.threading.main_thread
        ls.DATA, ls.REPLAYS = Path(self.tmp.name) / "data", Path(self.tmp.name) / "replays"
        ls.ROOT = Path(self.tmp.name)
        ls.DATA.mkdir()

    def tearDown(self):
        (ls.DATA / "STOP").write_text("")
        if self.th is not threading.current_thread():
            self.th.join(30)
        time.sleep(1.5)   # the collector sees the stop within a second
        ls.threading.main_thread = self.main_thread
        ls.DATA, ls.REPLAYS, ls.subprocess.run, ls.ROOT = self.saved
        self.tmp.cleanup()

    def start(self, api, tasks, **over):
        ls.subprocess.run = api.run
        for t in tasks:
            ls.append_jsonl(ls.DATA / "tasks.jsonl", t)
        args = dict(reserve=0, inflight=0, batch_inflight=0, pace=0, recheck=15, poll=0, tick=0.05, idle=0.05,
                    max_errors=3, exit_when_done=True)
        args.update(over)
        # cmd_run treats its own thread as the creator; the collector is the only other caller.
        self.th = threading.Thread(target=self.main, args=(types.SimpleNamespace(**args),), daemon=True)
        ls.threading.main_thread = lambda th=self.th: th
        self.th.start()

    def main(self, args):
        try:
            ls.cmd_run(args)
        except SystemExit:
            pass

    def created(self):
        return [e for e in ls.read_jsonl(ls.DATA / "events.jsonl") if e["ev"] == "created"]

    def wait(self, cond, secs=20):
        end = time.monotonic() + secs
        while time.monotonic() < end and not cond():
            time.sleep(0.02)
        self.assertTrue(cond())

    def test_burst_then_refill(self):
        api = FakeApi(used=40, play=0.4)   # room for 60 of 80
        self.start(api, [task(i) for i in range(80)])
        self.wait(lambda: len(self.created()) == 60)
        ev = self.created()
        self.assertTrue(ev[0]["is_ref"] and not any(e["is_ref"] for e in ev[1:]))
        self.assertTrue(all(e["source_group"] == ev[0]["group"] for e in ev[1:]))
        self.assertTrue(all(e["results"] == "WWWWW" for e in ls.read_jsonl(ls.DATA / "events.jsonl")
                            if e["ev"] == "played"))
        # The pin group played before the rest were created; they then went out back to back.
        creates = [t for t, a, b, _ in api.calls if (a, b) == ("match-groups", "create")]
        self.assertGreaterEqual(creates[1] - creates[0], api.play)
        self.assertLess(creates[59] - creates[1], 59 * GAP * 2.5)
        time.sleep(0.5)
        self.assertEqual(len(self.created()), 60)      # quota spent: nothing more, and no refused create
        api.used -= 20                                  # the rolling hour frees 20
        self.wait(lambda: len(self.created()) == 80)
        self.th.join(90)
        self.assertFalse(self.th.is_alive())
        ev = ls.read_jsonl(ls.DATA / "events.jsonl")
        self.assertEqual(sum(e["ev"] == "finished" for e in ev), 80)
        self.assertFalse(any(e["ev"] == "dropped" for e in ev))
        self.assertEqual(len(ls.read_jsonl(ls.DATA / "games.jsonl")), 400)

    def test_successful_calls_have_no_local_wait(self):
        self.th = threading.current_thread()
        result=types.SimpleNamespace(returncode=0,stdout='ok',stderr='')
        with mock.patch.object(ls.subprocess,'run',return_value=result), mock.patch.object(ls.time,'sleep') as sleep:
            for _ in range(40):
                self.assertEqual(ls.cambc('matches','list'),'ok')
            sleep.assert_not_called()
        self.assertFalse((ls.DATA/'api.lock').exists())

    def test_batch_activation_rechecks_unchanged_tasks_promptly(self):
        api = FakeApi(live=117)
        self.start(api, [task(0, pin='none')], pace=0.05, exit_when_done=False)
        self.wait(lambda: any(a == 'submissions' for _, a, _, _ in api.calls))
        time.sleep(0.15)
        api.live = 118
        # The plan is unchanged; the scheduler's fresh batch marker wakes activation polling.
        (ls.DATA/'BATCH').touch()
        self.wait(lambda: len(self.created()) == 1, secs=2)
        self.assertEqual(self.created()[0]['live'], 118)

    def test_server_rate_limit_is_retried(self):
        self.th = threading.current_thread()
        limited=types.SimpleNamespace(returncode=1,stdout='',stderr='HTTP 429; retry after 2 seconds')
        success=types.SimpleNamespace(returncode=0,stdout='ok',stderr='')
        with mock.patch.object(ls.subprocess,'run',side_effect=[limited,limited,success]) as run, \
             mock.patch.object(ls.time,'sleep') as sleep:
            self.assertEqual(ls.cambc('matches','list'),'ok')
            self.assertEqual(run.call_count,3)
            self.assertEqual(sleep.call_args_list,[mock.call(2),mock.call(4)])

    def test_reserve_and_other_versions_wait(self):
        api = FakeApi(used=85, play=0.2)
        self.start(api, [task(i, pin="none") for i in range(10)] + [task(100, version=117, pin="none")],
                   reserve=10, exit_when_done=False)
        self.wait(lambda: len(self.created()) == 5)
        time.sleep(0.6)
        self.assertEqual(len(self.created()), 5)       # 100 - 85 - reserve 10
        self.assertTrue(all(e["live"] == 118 for e in self.created()))
        (ls.DATA / "STOP").write_text("")
        self.th.join(10)


if __name__ == "__main__":
    unittest.main()
