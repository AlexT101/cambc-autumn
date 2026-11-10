"""Reserve slots for a bounded raw-engine diagnostic; substitute the actual job count."""
import os
from pathlib import Path
import subprocess
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / 'tools'))
import cpu_slots
held = cpu_slots.acquire(int(sys.argv[1]))
try:
    n = str(len(held))
    env = dict(os.environ, OMP_NUM_THREADS=n, OPENBLAS_NUM_THREADS=n, MKL_NUM_THREADS=n)
    raise SystemExit(subprocess.run([arg.replace('{n}', n) for arg in sys.argv[2:]], env=env).returncode)
finally:
    cpu_slots.release(held)
