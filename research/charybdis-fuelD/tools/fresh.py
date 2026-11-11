"""Generate independent ladder-v2 maps, saving exact manifests before testing."""
from pathlib import Path
import subprocess
import sys

root = Path(__file__).resolve().parents[3]
name, start, count = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
paths = []
for seed in range(start, start + count):
    directory = root / f'maps/suites/fuelD/fresh-{seed}'
    log = root / f'replays/fuel/fuelD/mapgen-{seed}.log'
    with log.open('w') as f:
        subprocess.run(['node', 'tools/mapgen/mapgen.mjs', 'suite', '--out', str(directory),
                        '--seed', str(seed), '--mix', 'ladder-v2'], cwd=root, stdout=f, stderr=f, check=True)
    maps = sorted(directory.glob('*.map26a'))
    assert len(maps) == 256
    paths.extend(str(p.relative_to(root)) for p in maps)
(root / f'research/charybdis-fuelD/tools/maps-{name}.txt').write_text('\n'.join(paths) + '\n')
