#!/usr/bin/env python3
"""Run a CPU-heavy command (an analysis, a model fit) inside the machine-wide slot pool, as ab.py's games are.

    python3 tools/pooled.py N -- CMD [ARGS...]

Takes up to N slots that fair share allows (waiting for at least one), sets the thread count of OpenMP, BLAS and
numexpr to the number held, runs CMD and frees the slots when it exits. Without this, a numpy or scikit-learn job
starts a thread per core whatever else is running.
"""
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cpu_slots  # noqa: E402


def main():
    if len(sys.argv) < 4 or sys.argv[2] != "--":
        sys.exit(__doc__)
    want = int(sys.argv[1])
    held = cpu_slots.acquire(want)
    try:
        n = str(len(held))
        env = dict(os.environ, OMP_NUM_THREADS=n, OPENBLAS_NUM_THREADS=n, MKL_NUM_THREADS=n, NUMEXPR_NUM_THREADS=n)
        print(f"pooled: {n} of {want} slots", file=sys.stderr, flush=True)
        sys.exit(subprocess.run(sys.argv[3:], env=env).returncode)
    finally:
        cpu_slots.release(held)


if __name__ == "__main__":
    main()
