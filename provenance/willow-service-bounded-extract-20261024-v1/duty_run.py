#!/usr/bin/env python3
"""Run one child process in an isolated process group with a coarse duty cycle."""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path


def utc() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cwd", required=True)
    ap.add_argument("--stdout", required=True)
    ap.add_argument("--stderr", required=True)
    ap.add_argument("--receipt", required=True)
    ap.add_argument("--run-seconds", type=float, default=0.1)
    ap.add_argument("--stop-seconds", type=float, default=0.9)
    ap.add_argument("command", nargs=argparse.REMAINDER)
    args = ap.parse_args()
    command = args.command[1:] if args.command[:1] == ["--"] else args.command
    if not command or args.run_seconds <= 0 or args.stop_seconds < 0:
        ap.error("provide a command and positive run / nonnegative stop intervals")

    cwd = Path(args.cwd).resolve()
    stdout_path, stderr_path = Path(args.stdout).resolve(), Path(args.stderr).resolve()
    receipt_path = Path(args.receipt).resolve()
    for path in (stdout_path, stderr_path, receipt_path):
        if path.exists():
            raise SystemExit(f"refusing to overwrite existing evidence: {path}")
        path.parent.mkdir(parents=True, exist_ok=True)

    interrupted: int | None = None

    def request_stop(signum: int, _frame: object) -> None:
        nonlocal interrupted
        interrupted = signum

    for sig in (signal.SIGINT, signal.SIGTERM, signal.SIGHUP):
        signal.signal(sig, request_stop)

    receipt: dict[str, object] = {
        "schema": "bounded-duty-run/v1",
        "started_utc": utc(),
        "cwd": str(cwd),
        "argv": command,
        "run_window_seconds": args.run_seconds,
        "stop_window_seconds": args.stop_seconds,
        "approximate_active_fraction": args.run_seconds / (args.run_seconds + args.stop_seconds),
        "nice": 19,
        "process_group_isolated": True,
        "stdout": str(stdout_path),
        "stderr": str(stderr_path),
        "duty_intervals": [],
    }
    proc: subprocess.Popen[bytes] | None = None
    aborted = False
    with stdout_path.open("xb") as stdout, stderr_path.open("xb") as stderr:
        try:
            proc = subprocess.Popen(
                ["nice", "-n", "19", *command], cwd=cwd, stdout=stdout, stderr=stderr,
                start_new_session=True,
            )
            receipt["pid"] = proc.pid
            receipt["process_group_id"] = proc.pid
            while proc.poll() is None and interrupted is None:
                active_start = time.monotonic()
                time.sleep(args.run_seconds)
                active_end = time.monotonic()
                receipt["duty_intervals"].append({"run_start_monotonic": active_start, "run_end_monotonic": active_end})
                if proc.poll() is not None or interrupted is not None:
                    break
                os.killpg(proc.pid, signal.SIGSTOP)
                try:
                    time.sleep(args.stop_seconds)
                finally:
                    # This group is the new session created above, never the caller's group.
                    try:
                        os.killpg(proc.pid, signal.SIGCONT)
                    except ProcessLookupError:
                        pass
            if interrupted is not None and proc.poll() is None:
                aborted = True
                try:
                    os.killpg(proc.pid, signal.SIGCONT)
                except ProcessLookupError:
                    pass
                try:
                    os.killpg(proc.pid, signal.SIGTERM)
                except ProcessLookupError:
                    pass
                try:
                    proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    try:
                        os.killpg(proc.pid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass
                    proc.wait()
        except BaseException:
            if proc is not None and proc.poll() is None:
                try:
                    os.killpg(proc.pid, signal.SIGCONT)
                except ProcessLookupError:
                    pass
                try:
                    os.killpg(proc.pid, signal.SIGTERM)
                except ProcessLookupError:
                    pass
                try:
                    proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    try:
                        os.killpg(proc.pid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass
                    proc.wait()
            raise
        finally:
            if proc is not None:
                # Ensure a normally finishing child is not left stopped on any path.
                if proc.poll() is None:
                    try:
                        os.killpg(proc.pid, signal.SIGCONT)
                    except ProcessLookupError:
                        pass
                    proc.wait()
                receipt["exit_code"] = proc.returncode
            receipt["interrupted_by_signal"] = interrupted
            receipt["aborted"] = aborted
            receipt["ended_utc"] = utc()
            receipt_path.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")

    return 128 + interrupted if interrupted is not None else int(receipt.get("exit_code", 1))


if __name__ == "__main__":
    sys.exit(main())
