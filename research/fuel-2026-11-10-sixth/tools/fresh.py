"""Fresh ladder-v2 suites for the sixth fuel pass: `fresh.py NAME SEED0` makes 8 seeds of 256 maps."""
from pathlib import Path
import subprocess, sys
root = Path(__file__).resolve().parents[3]
name, seed0 = sys.argv[1], int(sys.argv[2])
maps = []
for seed in range(seed0, seed0 + 8):
    d = root / f'maps/suites/fuel-sixth/{name}-{seed}'
    log = root / f'replays/fuel/oc-sixth/mapgen/mapgen-{seed}.log'
    log.parent.mkdir(parents=True, exist_ok=True)
    with log.open('w') as f:
        subprocess.run(['node', 'tools/mapgen/mapgen.mjs', 'suite', '--out', str(d), '--seed', str(seed), '--mix', 'ladder-v2'],
                       cwd=root, stdout=f, stderr=f, check=True)
    paths = sorted(d.glob('*.map26a')); assert len(paths) == 256, len(paths)
    maps.extend(str(p.relative_to(root)) for p in paths)
(root / f'research/fuel-2026-11-10-sixth/tools/maps-{name}.txt').write_text('\n'.join(maps) + '\n')
