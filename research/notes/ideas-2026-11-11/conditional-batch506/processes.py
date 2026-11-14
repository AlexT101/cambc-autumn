"""Owned subprocess sessions must drain before another queue phase can begin."""
import os
from pathlib import Path
import signal
import time


def live_group(pgid):
    for path in Path('/proc').glob('[0-9]*/stat'):
        try:
            fields = path.read_text().split(') ', 1)[1].split()
            if fields[0] != 'Z' and int(fields[2]) == pgid:
                return True
        except (OSError, ValueError, IndexError):
            pass
    return False


def signal_group(process, sig):
    # Each caller creates a fresh session whose process-group ID is the original child PID.
    if not getattr(process, 'owns_group', True):
        if process.poll() is None:
            try:
                process.send_signal(sig)
            except ProcessLookupError:
                pass
        return
    if live_group(process.pid):
        try:
            os.killpg(process.pid, sig)
        except ProcessLookupError:
            pass


def drain(process, interrupt=False):
    began = time.monotonic()
    if interrupt:
        signal_group(process, signal.SIGINT)
    sent_term = sent_kill = False
    while process.poll() is None or (getattr(process, 'owns_group', True) and live_group(process.pid)):
        try:
            elapsed = time.monotonic() - began
            if interrupt and elapsed >= 5 and not sent_term:
                signal_group(process, signal.SIGTERM)
                sent_term = True
            if interrupt and elapsed >= 10 and not sent_kill:
                signal_group(process, signal.SIGKILL)
                sent_kill = True
            time.sleep(.05)
        except KeyboardInterrupt:
            if not interrupt:
                began = time.monotonic()
            interrupt = True
            signal_group(process, signal.SIGINT)
    return process.wait()
