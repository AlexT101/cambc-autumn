"""Run a command holding CPU slots from the machine-wide pool (tools/cpu_slots.py), so a fit's threads take cores
from games instead of crowding them: py tools/emblab/with_slots.py N CMD...  ({slots} in CMD is the number held).
CAMBC_SLOT_WEIGHT scales the share, as for games."""
import subprocess, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import cpu_slots  # noqa: E402

want = int(sys.argv[1])
held = cpu_slots.acquire(want, least=want, poll=0.05)  # waits for all of them: games hand slots over as they end
try:
    sys.exit(subprocess.run([a.replace("{slots}", str(len(held))) for a in sys.argv[2:]]).returncode)
finally:
    cpu_slots.release(held)
