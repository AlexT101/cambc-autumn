"""Shared exclusion between live group creation and intentional submission switches."""
from contextlib import contextmanager
import fcntl


@contextmanager
def live_lock(data):
    with (data / 'live-switch.lock').open('a') as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        yield


def probe_active(data):
    return (data / 'version-check-active.json').exists()
