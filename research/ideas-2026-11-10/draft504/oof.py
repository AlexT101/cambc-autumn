"""Run five genuine held-map fits without editing the shared draftlab module."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile

R = Path(__file__).resolve().parents[3]
T = Path(__file__).resolve().parent
sys.path.insert(0, str(R / 'tools'))
import cpu_slots


def generated(source, fragment):
    marker = 'const commands = { fit: fitCommand,'
    assert source.count(marker) == 1
    return fragment + '\n' + source.replace(marker, 'const commands = { "draft17-oof": draft17OOF, fit: fitCommand,')


def main():
    lab, fixed, out = sys.argv[1:]
    original = R / 'tools/draftlab/model.mjs'
    data = generated(original.read_text(), (T / 'oof_fragment.mjs').read_text())
    held = cpu_slots.acquire(24, least=8)
    path = None
    try:
        with tempfile.NamedTemporaryFile(mode='w', suffix='.mjs', prefix='.draft17-oof-', dir=original.parent, delete=False) as f:
            f.write(data); path = Path(f.name)
        env = dict(os.environ, OMP_NUM_THREADS=str(len(held)), OPENBLAS_NUM_THREADS=str(len(held)), MKL_NUM_THREADS=str(len(held)))
        subprocess.run(['node', path, 'draft17-oof', '--lab', lab, '--fixed-model', fixed, '--out', out,
                        '--threads', str(len(held))], cwd=R, env=env, check=True)
    finally:
        if path is not None: path.unlink(missing_ok=True)
        cpu_slots.release(held)


if __name__ == '__main__': main()
