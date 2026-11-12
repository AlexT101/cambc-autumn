"""Our Fish scrims for refset REF (default r8): refresh capture rows from big-arm, pull the replays not yet local, unzip
them beside live_ds.py's, and write rows-REF-all.json (games.jsonl rows plus capture rows; match id -> row).
    py sync.py [REF] [--no-pull]"""
import json, os, subprocess, sys, zipfile, glob
H = os.path.expanduser('~/tmp-offload/fishr8'); F = os.path.dirname(os.path.abspath(__file__))
ref = next((a for a in sys.argv[1:] if not a.startswith('-')), 'r8')
if '--no-pull' not in sys.argv:
    subprocess.run(f'timeout 900 ssh big-arm "bash -s" < {H}/pull_ours_remote.sh > {H}/rows_recent.tsv.gz.tmp && mv {H}/rows_recent.tsv.gz.tmp {H}/rows_recent.tsv.gz', shell=True, check=True)
subprocess.run([sys.executable, f'{F}/ours.py'], check=True, cwd=F, capture_output=True)
subprocess.run([sys.executable, f'{F}/live_ds.py', ref], check=True, cwd=F, capture_output=True)
ours = json.load(open(f'{H}/ours.json')); rows = json.load(open(f'{H}/live/rows-{ref}.json'))
want = [v['replay'] for k, v in ours.items() if v['refset'] == ref and v['replay'] and k not in rows and not os.path.exists(f'{H}/live/raw/{k}.repl26a')]
if want and '--no-pull' not in sys.argv:
    open(f'{H}/want.txt', 'w').write('\n'.join(want) + '\n')
    subprocess.run(f"cd {H}/bigarm && ssh big-arm 'cd ~/cambc-autumn/.oarena/capture && nice tar cf - -T -' < {H}/want.txt | tar xf -", shell=True, check=True)
for k, v in ours.items():
    if v['refset'] != ref or k in rows: continue
    dst = f'{H}/live/raw/{k}.repl26a'
    z = f'{H}/bigarm/{v["replay"]}'
    if not os.path.exists(dst) and v['replay'] and os.path.exists(z):
        with zipfile.ZipFile(z) as zf:
            n = [x for x in zf.namelist() if x.endswith('.repl26a')][0]; open(dst, 'wb').write(zf.read(n))
    if os.path.exists(dst):
        rows[k] = {x: v.get(x) for x in ('version', 'map', 'side', 'result', 'our_picks', 'opp_picks', 'created', 'group', 'task')}
json.dump(rows, open(f'{H}/live/rows-{ref}-all.json', 'w'))
print(len(rows), 'games with replays for', ref, '; results known', sum(1 for v in ours.values() if v['refset'] == ref))
