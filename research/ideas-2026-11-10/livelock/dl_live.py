import json, subprocess, os, sys, time
OUT = os.path.expanduser('~/tmp-offload/livelock/live')
since = sys.argv[1]  # ISO
cur = None; got = []
while True:
    cmd = ['cambc', 'matches', 'list', '--team', 'me', '--limit', '100', '--json'] + (['--cursor', cur] if cur else [])
    d = json.loads(subprocess.run(cmd, capture_output=True, text=True).stdout)
    stop = False
    for m in d['matches']:
        if m['createdAt'] < since: stop = True; break
        if m['status'] == 'finished': got.append(m)
    cur = d.get('nextCursor') or d.get('cursor')
    if stop or not cur: break
json.dump(got, open(f'{OUT}/list.json', 'w'))
print(len(got), 'finished', flush=True)
for m in got:
    f = f"{OUT}/{m['matchId']}.zip"
    if os.path.exists(f): continue
    for t in range(5):
        r = subprocess.run(['cambc', 'matches', 'download', m['matchId'], '-o', f], capture_output=True, text=True)
        if 'Saved' in r.stdout + r.stderr: break
        time.sleep(3)
    time.sleep(0.7)
    if len(os.listdir(OUT)) > 700: break
print('done', flush=True)
