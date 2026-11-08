"""Local ab.py runs -> cells {(map, cand side): cand win} and drafts."""
import json, os, subprocess, collections, tempfile
R = '/home/ubuntu/cambc-autumn/'

def matches(name):
    s = json.load(open(f'{R}replays/ab/{name}/summary.json'))
    for su in s['suites']:
        for m in json.load(open(R + su['batch'] + '/results.json'))['matches']:
            if m.get('winner') is None: continue
            yield os.path.basename(m['map']).replace('.map26a', ''), ('a' if m['order'][0] == 0 else 'b'), m

def cells(name):
    return {(mp, side): float(m['winner'] == 0) for mp, side, m in matches(name)}

def drafts(name):
    """(map, cand side) -> (cand picks, opp picks), from the replays (tools/replay/drafts.mjs)."""
    ms = list(matches(name)); idx = {m['replay']: (mp, side) for mp, side, m in ms if os.path.exists(m['replay'])}
    with tempfile.NamedTemporaryFile('w', delete=False) as f: f.write('\n'.join(idx)); lst = f.name
    out = subprocess.run(['node', R + 'tools/replay/drafts.mjs', lst], capture_output=True, text=True, check=True).stdout
    d = {}
    for line in out.splitlines():
        p, a, b = line.split('\t'); mp, side = idx[p]
        d[(mp, side)] = (a, b) if side == 'a' else (b, a)
    return d
