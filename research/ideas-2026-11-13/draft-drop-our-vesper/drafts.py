"""Draft-only games (no rounds): REF (side a) vs CAND (side b) on map dirs; picks via drafts.mjs.
   python drafts.py OUT REFDIR CANDDIR MAPDIR... -> OUT/picks.tsv (map, ref picks, cand picks)"""
import os, sys, subprocess, glob
sys.path.insert(0, '/home/ubuntu/cambc-autumn/tools')
import cambc_env
R = '/home/ubuntu/cambc-autumn'
out, ref, cand, *dirs = sys.argv[1:]
os.makedirs(out, exist_ok=True)
for b in (ref, cand):
    r = subprocess.run(['cambc', 'build', '--release', f'{R}/bots/{b}'], cwd=R, capture_output=True, text=True)
    if r.returncode: sys.exit(r.stdout[-2000:] + r.stderr[-2000:])
maps = sorted(p for d in dirs for p in glob.glob(f'{d}/*.map26a'))
with open(f'{out}/manifest.txt', 'w') as f:
    for i, m in enumerate(maps): f.write(f'{R}/bots/{ref} {R}/bots/{cand} {os.path.realpath(m)} m{i:05d}.repl26a\n')
with open(f'{out}/run.log', 'w') as log:
    subprocess.run(['cambc', 'run-batch', 'manifest.txt', '--jobs', '8', '--rounds', '0', '--release', '--color', 'never',
                    '--timeout', '600', '--log-limit', '0'], cwd=out, env=cambc_env.env(), stdout=log, stderr=subprocess.STDOUT)
reps = [f'{out}/m{i:05d}.repl26a' for i in range(len(maps))]
with open(f'{out}/list.txt', 'w') as f: f.write('\n'.join(p for p in reps if os.path.exists(p)))
res = subprocess.run(['node', f'{R}/tools/replay/drafts.mjs', f'{out}/list.txt'], capture_output=True, text=True, check=True).stdout
idx = {p: os.path.basename(m)[:-7] for p, m in zip(reps, maps)}
with open(f'{out}/picks.tsv', 'w') as f:
    for line in res.splitlines():
        p, a, b = line.split('\t'); f.write(f'{idx[p]}\t{a}\t{b}\n')
for p in reps:
    if os.path.exists(p): os.unlink(p)
print(len(res.splitlines()), 'drafts of', len(maps))
