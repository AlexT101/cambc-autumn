# Per block: the frozen hash of the opponent body each run played (base vs cands). A mismatch = different opponents.
import json, re, sys, collections
R = '/home/ubuntu/cambc-autumn/'
def h(n):
    try: b = json.load(open(f'{R}replays/ab/{n}/summary.json'))['suites'][0]['batch']
    except Exception: return None
    m = re.search(r'frozen/([0-9a-f]+)/spar-', open(R + b + '/manifest.txt').readline()); return m.group(1) if m else None
cands = sys.argv[1:]; bad = collections.Counter(); tot = 0
for k in range(1, 400):
    for o in 'FM':
        base = h(f'spar-cbase25-dvn{k}{o}2')
        if base is None: continue
        for c in cands:
            x = h(f'spar-c{c}-dvn{k}{o}2')
            if x is None: continue
            tot += 1
            if x != base: bad[c] += 1; print('mismatch', k, o, c, base, x)
print('pairs', tot, dict(bad))
