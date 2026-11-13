"""Live-switch exclusion and expiring control priority over background API traffic."""
from contextlib import contextmanager
import fcntl
import os
import threading
import time


CONTROL_LEASE_SECONDS = 90  # exceeds one server backoff (capped at 60s), but expires if an owner stops
_OWNERS = threading.local()


@contextmanager
def control_priority(data):
    # Shared owners: a rate-limited reader must never exclude a waiting activation.
    with (data / 'api-control.lock').open('a') as owner:
        fcntl.flock(owner, fcntl.LOCK_SH)
        def renew():
            os.utime(owner.fileno(), None)
        renew()
        if not hasattr(_OWNERS, 'stack'):
            _OWNERS.stack = []
        _OWNERS.stack.append((data.resolve(), renew))
        try:
            yield renew
        finally:
            _OWNERS.stack.pop()


def wait_for_control(data):
    """Yield only while a live control owner has renewed its lease; never hold up that owner.

    The probe is released before the request. One already-started background call may overlap control.
    A crash releases the advisory lock; a stopped owner cannot renew beyond the lease expiry.
    """
    for directory, renew in reversed(getattr(_OWNERS, 'stack', ())):
        if directory == data.resolve():
            renew()  # e.g. a version check reads its group's summary under live_lock
            return
    with (data / 'api-control.lock').open('a') as probe:
        while True:
            try:
                fcntl.flock(probe, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                age = time.time() - os.fstat(probe.fileno()).st_mtime
                if not 0 <= age < CONTROL_LEASE_SECONDS:
                    return
                time.sleep(min(0.1, CONTROL_LEASE_SECONDS - age))
            else:
                return


@contextmanager
def live_lock(data):
    # Lock order is always priority (shared), then switch (exclusive). Background callers only probe priority.
    with control_priority(data), (data / 'live-switch.lock').open('a') as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        yield


def probe_active(data):
    return (data / 'version-check-active.json').exists()
