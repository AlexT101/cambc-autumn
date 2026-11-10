"""Keep a slot group's weight registered in the machine-wide CPU-slot pool (tools/cpu_slots.py) while a run lasts:

    py tools/emblab/slot_keeper.py GROUP WEIGHT [PID]     # until PID exits (default: forever; kill it after)

A member file is created and then locked; a scan by another job in between sees it unlocked, takes its process for
gone and unlinks it (cpu_slots._claim, fastrunner Slots::new). The owner then holds a lock on a file nobody can
see, and every other job counts its group at weight 1 for the rest of that process's life: on 2026-11-10 the
emblem lab at weight 35 held 19 of 86 slots against six gates. This file is locked before it is linked into
members/, and marks the group as waiting, so other groups above their share hand slots back."""
import fcntl, os, sys, time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault("CAMBC_SLOT_GROUP", "slot-keeper")
import cpu_slots  # noqa: E402

group, weight = sys.argv[1], float(sys.argv[2])
pid = int(sys.argv[3]) if len(sys.argv) > 3 else None
tmp = cpu_slots.DIR / f"keeper-{os.getpid()}.tmp"
f = open(tmp, "w+b")
fcntl.flock(f.fileno(), fcntl.LOCK_EX)
f.write(f"{group}\t{weight}\t1\n".encode())
f.flush()
(cpu_slots.DIR / "members").mkdir(exist_ok=True)
os.rename(tmp, cpu_slots.DIR / "members" / f"{os.getpid()}-keeper")
print(f"keeping {group} at weight {weight}", flush=True)
while pid is None or os.path.exists(f"/proc/{pid}"):
    time.sleep(5)
