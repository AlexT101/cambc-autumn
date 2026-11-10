from pathlib import Path
import subprocess
root=Path(__file__).resolve().parents[3]
maps=[]
for seed in range(1462610,1462618):
 d=root/f'maps/suites/fuel-fourth/final-{seed}'
 log=root/f'replays/fuel/oc-fourth/mapgen/mapgen-{seed}.log'
 log.parent.mkdir(parents=True,exist_ok=True)
 with log.open('w') as f:subprocess.run(['node','tools/mapgen/mapgen.mjs','suite','--out',str(d),'--seed',str(seed),'--mix','ladder-v2'],cwd=root,stdout=f,stderr=f,check=True)
 paths=sorted(d.glob('*.map26a'));assert len(paths)==256,len(paths)
 maps.extend(str(p.relative_to(root)) for p in paths)
(root/'research/fuel-2026-11-10-fourth/tools/maps-final.txt').write_text('\n'.join(maps)+'\n')
