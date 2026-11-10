from pathlib import Path
import os, subprocess
from concurrent.futures import ThreadPoolExecutor
root=Path(__file__).resolve().parents[3]
out=root/'replays/fuel/oc-fourth/prof'
env=os.environ | {'FASTRUNNER_FUELPROF':str(out),'FASTRUNNER_MODE':'native'}
runner=root/'tools/fastengine/runner-prof/fastrunner'
bot=root/'bots/variants/oc-f4x-prof'
maps=(root/'research/fuel-2026-11-10-fourth/tools/maps-id.txt').read_text().split()
def run(i):
 with (out/f'game-{i}.log').open('w') as log:
  subprocess.run([str(runner),'run','--release',str(bot),str(bot),'--map',maps[i],'-o',str(out/f'game-{i}')],env=env,stdout=log,stderr=log,check=True)
run(0)
with ThreadPoolExecutor(max_workers=12) as pool:list(pool.map(run,range(1,len(maps))))
for name,d in [('all',out),('heavy',out/'heavy'),('oof',out/'oof')]:
 subprocess.run(['python3',str(Path(__file__).with_name('symbolise.py')),str(bot),str(out/f'{name}.json'),str(d)],check=True)
