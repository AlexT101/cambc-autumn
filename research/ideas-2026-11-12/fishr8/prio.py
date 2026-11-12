"""Fish r8's priority encoding: decode v -> ceil(v / 2^SHIFT) and test it against the 11-09 rank code (det3.fish_token)
with rank offsets 0 / -1; also the low bits.   py prio.py EXT ROWS.json"""
import json, gzip, sys, collections, math
sys.path.insert(0, '/home/ubuntu/cambc-autumn/research/ideas-2026-11-12/bcexploit'); import det3
ext, rf = sys.argv[1:3]; rows = json.load(open(rf)); idx = json.load(open(ext + '/index.json'))['games']
S = int(sys.argv[3]) if len(sys.argv) > 3 else 20
tot = collections.Counter(); lowcorr = []
def dec(v): return -((-v) >> S) if v < 0 else -((-v) >> S)  # floor(v / 2^S) ... tested both below
for g in idx:
    mid = g['source'].split('/')[-1][:-8]
    if mid not in rows: continue
    fish = 1 if rows[mid]['side'] == 'a' else 0
    d = ext + '/' + g['dir']; m = json.load(open(d + '/meta.json')); R = json.load(gzip.open(d + '/rounds.json.gz'))
    names = {c['id']: c['name'] for c in m['champions']}
    roster = [names[c['id']] for c in R['champions'] if c['team'] == fish]; lo, rank = det3.setup(roster)
    j = 0
    for c in R['champions']:
        if c['team'] != fish: continue
        last = None
        for i, v in enumerate(c['prio']):
            if v == last or v == 0: last = v; continue
            last = v; tot['n'] += 1
            ce = -((-v) // (1 << S))   # ceil(v / 2^S)
            fl = v // (1 << S)         # floor
            for lab, x in (('ceil', ce), ('floor', fl)):
                for off in (0, -1, 1):
                    t = det3.fish_token(x, len(roster), rank[j] + off, c['hp'][i], c['maxHp'][i] or 1, c['shield'][i] or 0, c['gems'][i])
                    tot[f'{lab} off{off} fit'] += t > 0; tot[f'{lab} off{off} core'] += t == 2
        j += 1
n = tot.pop('n'); print(n, 'distinct writes')
for k, v in sorted(tot.items()): print(f'{k:22s} {v / n:.3f}')
