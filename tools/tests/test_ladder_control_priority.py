"""Control priority, crash/lease recovery, and pre/post-create 429 exclusion guarantees."""
import multiprocessing
import os
from pathlib import Path
import signal
import sys
import tempfile
import threading
import time
import types
import unittest
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import ladder_coordination as coordination
import ladder_scrims as ls
import test_ladder_scrims_run as runner_tests
from test_ladder_scrims_run import FakeApi, task


def hold_priority(data, ready):
    with coordination.control_priority(Path(data)):
        ready.send(True)
        ready.close()
        time.sleep(60)


class PriorityCalls(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.data = Path(self.tmp.name)
        self.patch = mock.patch.object(ls, 'DATA', self.data)
        self.patch.start()

    def tearDown(self):
        self.patch.stop()
        self.tmp.cleanup()

    def test_preflight_reads_defer_without_sleep_but_mutations_do_not(self):
        limited = types.SimpleNamespace(returncode=1, stdout='', stderr='HTTP 429; retry after 2 seconds')
        ok = types.SimpleNamespace(returncode=0, stdout='ok', stderr='')
        for command in (('submissions', 'list'), ('match-groups', 'quota')):
            with self.subTest(command=command), mock.patch.object(ls.subprocess, 'run', return_value=limited), \
                    mock.patch.object(ls.time, 'sleep') as sleep, ls.defer_control_reads(True):
                with self.assertRaises(ls.ControlReadLimited) as error:
                    ls.cambc(*command)
                self.assertEqual(error.exception.retry_after, 2)
                sleep.assert_not_called()
        with mock.patch.object(ls.subprocess, 'run', side_effect=[limited, ok]) as run, \
                mock.patch.object(ls.time, 'sleep') as sleep, ls.defer_control_reads(True):
            self.assertEqual(ls.cambc('match-groups', 'create', 'opp'), 'ok')
            self.assertEqual(run.call_count, 2)
            sleep.assert_called_once_with(2)

    def test_background_retries_recheck_priority_and_local_summary_does_not_wait(self):
        limited = types.SimpleNamespace(returncode=1, stdout='', stderr='HTTP 429; retry after 1 seconds')
        ok = types.SimpleNamespace(returncode=0, stdout='ok', stderr='')
        with mock.patch.object(ls.subprocess, 'run', side_effect=[limited, ok]), \
                mock.patch.object(ls.time, 'sleep'), mock.patch.object(ls, 'wait_for_control') as wait:
            ls.cambc('matches', 'download', 'match')
            self.assertEqual(wait.call_count, 2)
        with coordination.control_priority(self.data), mock.patch.object(ls.subprocess, 'run', return_value=ok), \
                mock.patch.object(ls, 'wait_for_control') as wait:
            ls.cambc('summary', 'local-file', '-o', '-')
            wait.assert_not_called()

    def test_fresh_timestamp_without_owner_does_not_hold_collection(self):
        (self.data/'api-control.lock').touch()
        with mock.patch.object(coordination.time, 'sleep') as sleep:
            coordination.wait_for_control(self.data)
            sleep.assert_not_called()

    def test_control_thread_background_calls_do_not_wait_on_their_own_lease(self):
        main, real_sleep = threading.current_thread(), time.sleep
        downloaded = threading.Event()
        calls = []
        def sleep(seconds):
            if threading.current_thread() is main:
                raise AssertionError('Control thread waited on its own lease')
            real_sleep(seconds)
        def run(cmd, **kwargs):
            calls.append((cmd[1:3], threading.current_thread()))
            return types.SimpleNamespace(returncode=0, stdout='{"matches":[]}', stderr='')
        def collect():
            ls.cambc('matches', 'download', 'match')
            downloaded.set()
        collector = threading.Thread(target=collect)
        with mock.patch.object(ls.subprocess, 'run', side_effect=run), \
                mock.patch.object(coordination.time, 'sleep', side_effect=sleep):
            try:
                with ls.live_lock(self.data):
                    collector.start()
                    self.assertFalse(downloaded.wait(0.15))
                    with coordination.control_priority(self.data):
                        self.assertEqual(ls.group_detail('group'), {'matches':[]})
                    # The inner owner is gone; the outer owner must still bypass its own lease.
                    ls.cambc('matches', 'summary', 'match')
                    self.assertFalse(downloaded.is_set())
                    self.assertEqual([cmd for cmd,thread in calls if thread is main],
                                     [['match-groups','show'],['matches','summary']])
                self.assertTrue(downloaded.wait(2))
            finally:
                if collector.ident is not None: collector.join(3)

    def owner_recovery(self, expired):
        ctx = multiprocessing.get_context('spawn')
        receive, send = ctx.Pipe(duplex=False)
        owner = ctx.Process(target=hold_priority, args=(str(self.data), send))
        owner.start(); send.close()
        finished = threading.Event()
        background = threading.Thread(target=lambda: (coordination.wait_for_control(self.data), finished.set()))
        try:
            self.assertTrue(receive.poll(5))
            self.assertTrue(receive.recv())
            background.start()
            self.assertFalse(finished.wait(0.15))
            if expired:
                os.kill(owner.pid, signal.SIGSTOP)
                old = time.time() - coordination.CONTROL_LEASE_SECONDS - 1
                os.utime(self.data/'api-control.lock', (old, old))
                self.assertTrue(owner.is_alive())
            else:
                owner.kill(); owner.join(5)
                # mtime is still fresh: the kernel ownership, not a timestamp alone, determines priority.
                self.assertLess(time.time()-(self.data/'api-control.lock').stat().st_mtime,
                                coordination.CONTROL_LEASE_SECONDS)
            self.assertTrue(finished.wait(2))
        finally:
            if owner.is_alive(): owner.kill()
            owner.join(5); receive.close()
            if background.ident is not None: background.join(3)

    def test_crashed_owner_releases_collection_immediately(self):
        self.owner_recovery(expired=False)

    def test_stopped_owner_cannot_hold_collection_past_lease(self):
        self.owner_recovery(expired=True)


class RateLimitedApi(FakeApi):
    def __init__(self, read_number):
        super().__init__(play=30)
        self.read_number, self.reads = read_number, 0
        self.at_read, self.respond = threading.Event(), threading.Event()

    def run(self, cmd, **kwargs):
        if cmd[1:3] == ['submissions', 'list']:
            self.reads += 1
            if self.reads == self.read_number:
                self.at_read.set()
                if not self.respond.wait(5): raise RuntimeError('Test did not release API response')
                return types.SimpleNamespace(returncode=1, stdout='', stderr='HTTP 429; retry after 2 seconds')
        return super().run(cmd, **kwargs)


class RunnerPriority(runner_tests.RunTest):
    # Reuse only the runner fixture; the ordinary runner cases run in their own module.
    test_burst_then_refill = test_successful_calls_have_no_local_wait = None
    test_batch_activation_rechecks_unchanged_tasks_promptly = None
    test_server_rate_limit_is_retried = test_reserve_and_other_versions_wait = None

    def concurrent_retry(self, after_create):
        api = RateLimitedApi(read_number=2 if after_create else 1)
        backoff, resume = threading.Event(), threading.Event()
        scheduler_started, activated, downloaded = threading.Event(), threading.Event(), threading.Event()
        real_sleep = time.sleep
        def sleep(seconds):
            if threading.current_thread() is self.th and seconds == 2:
                backoff.set()
                if not resume.wait(5): raise RuntimeError('Test did not release backoff')
            else:
                real_sleep(seconds)
        def activate():
            scheduler_started.set()
            with ls.live_lock(ls.DATA):
                ls.cambc('submissions', 'activate', '117')
                api.live = 117
                activated.set()
        def download():
            ls.cambc('matches', 'download', 'match', '-o', str(ls.DATA/'download'))
            downloaded.set()
        scheduler = threading.Thread(target=activate)
        collector = threading.Thread(target=download)
        with mock.patch.object(ls.time, 'sleep', side_effect=sleep):
            try:
                self.start(api, [task(0, pin='none')], recheck=1, pace=20, exit_when_done=False)
                self.assertTrue(api.at_read.wait(3))
                scheduler.start(); collector.start()
                self.assertTrue(scheduler_started.wait(1))
                self.assertFalse(activated.wait(0.1))
                self.assertFalse(downloaded.is_set())
                api.respond.set()
                self.assertTrue(backoff.wait(3))
                if after_create:
                    self.assertFalse(activated.wait(0.15))
                    self.assertEqual(len(self.created()), 1)
                    # An outside switch still has to mark the unconfirmed group suspect after the retry.
                    api.live = 117
                else:
                    self.assertTrue(activated.wait(2))
                    self.assertEqual(self.created(), [])
                self.assertFalse(downloaded.is_set())
                resume.set()
                self.assertTrue(activated.wait(3))
                self.assertTrue(downloaded.wait(3))
                if after_create:
                    suspect = [e for e in ls.read_jsonl(ls.DATA/'events.jsonl') if e['ev']=='suspect']
                    self.assertEqual([e['task'] for e in suspect], ['t000'])
            finally:
                (ls.DATA/'STOP').touch()
                api.respond.set(); resume.set()
                self.th.join(5)
                if scheduler.ident is not None: scheduler.join(5)
                if collector.ident is not None: collector.join(5)
        self.assertFalse(scheduler.is_alive())
        self.assertFalse(collector.is_alive())

    def test_precreate_429_yields_switch_to_scheduler_while_collector_stays_quiet(self):
        self.concurrent_retry(after_create=False)

    def test_postcreate_429_retains_lock_and_marks_unconfirmed_switch(self):
        self.concurrent_retry(after_create=True)


if __name__ == '__main__':
    unittest.main()
