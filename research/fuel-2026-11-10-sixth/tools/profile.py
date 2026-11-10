"""Exact fuel profile of a bot (self-play, maps-id, release, real budget) with all/heavy/oof classes.
profile.py BOTDIR OUTDIR. Build BOTDIR first with CXXFLAGS=-g cambc build --release BOTDIR."""
from pathlib import Path
import os, subprocess, sys
from concurrent.futures import ThreadPoolExecutor
root = Path(__file__).resolve().parents[3]
bot = Path(sys.argv[1]).resolve(); out = Path(sys.argv[2]).resolve()
for p in (out, out/'heavy', out/'oof'): p.mkdir(parents=True, exist_ok=True)
env = os.environ | {'FASTRUNNER_FUELPROF': str(out), 'FASTRUNNER_MODE': 'native'}
runner = Path('/home/ubuntu/cambc-autumn/tools/fastengine/runner-prof/fastrunner')
maps = (root/'research/fuel-2026-11-10-sixth/tools/maps-id.txt').read_text().split()
def run(i):
    with (out/f'game-{i}.log').open('w') as log:
        subprocess.run([str(runner), 'run', '--release', str(bot), str(bot), '--map', maps[i], '-o', str(out/f'game-{i}')],
                       cwd=root, env=env, stdout=log, stderr=log, check=True)
run(0)
with ThreadPoolExecutor(max_workers=24) as pool: list(pool.map(run, range(1, len(maps))))
for name, d in [('all', out), ('heavy', out/'heavy'), ('oof', out/'oof')]:
    subprocess.run(['python3', str(root/'research/fuel-2026-11-10-sixth/tools/symbolise.py'), str(bot), str(out/f'{name}.json'), str(d)], check=True)
