"""Final F92 fit, with each worker backed by a shared CPU slot."""
import os
from pathlib import Path
import subprocess
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / 'tools'))
import cpu_slots
held = cpu_slots.acquire(24, least=8)
try:
    n = str(len(held))
    env = dict(os.environ, OMP_NUM_THREADS=n, OPENBLAS_NUM_THREADS=n, MKL_NUM_THREADS=n)
    raise SystemExit(subprocess.run(['node', 'tools/draftlab/model.mjs', 'fit', '--lab', sys.argv[1],
                                    '--search', '--groups', 'w,dev', '--passes', '1', '--threads', n], env=env).returncode)
finally:
    cpu_slots.release(held)
