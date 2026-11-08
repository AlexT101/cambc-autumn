"""Spar body's capture recalls (Q): bag at landing, rounds to next camp hit / tribute, shop on landing."""
import json, gzip, os, sys, collections, zipfile, numpy as np
sys.path.insert(0, os.path.expanduser('~/tmp-offload/carry'))
from econ import load, H
sys.path.insert(0, '/home/ubuntu/cambc-autumn/research/ideas-2026-11-08/spar-tools'); import local
S = load(H + 'spar/ana'); RW = 600; rows = []; n = 0
for o in 'FM':
    for mp, side, m in local.matches(f'spar-c27-o29{o}'):
        k = os.path.basename(os.path.dirname(m['replay'])) + '/' + os.path.basename(m['replay']).split('.')[0]
        if k not in S or not os.path.exists(m['replay']): continue
        ot = 1 if side == 'a' else 0; d = H + 'spar/ana/' + S[k]; n += 1
        out = zipfile.ZipFile(m['replay']).read('team-%s.stdout' % 'ab'[ot]).decode(errors='replace')
        br = {}
        for line in out.splitlines():
            t = line.split()
            if len(t) >= 4 and t[0] == 'D': br[(int(t[1]), int(t[2]))] = t[3]
        meta = json.load(open(d + '/meta.json')); ch = {c['id']: c for c in meta['champions']}
        R = json.load(gzip.open(d + '/rounds.json.gz')); ri = {r: j for j, r in enumerate(R['round'])}; C = {c['id']: c for c in R['champions']}
        ev = [json.loads(l) for l in gzip.open(d + '/events.jsonl.gz')]; st = {}
        for i, e in enumerate(ev):
            if e['r'] > RW: break
            a = e.get('a')
            if a is None or ch[a]['team'] != ot: continue
            if e['k'] == 'recall_start': st[a] = e['r']
            elif e['k'] == 'recall_end' and a in st:
                r0 = st[a]; j = ri.get(r0)
                if j is None: continue
                if 'Q' not in ''.join(br.get((r, a), '?') for r in range(r0, e['r'] + 1)): continue
                hp = C[a]['hp'][j] / max(1, C[a]['maxHp'][j])
                hit = trib = None; shop = 0
                for e2 in ev[i + 1:]:
                    if e2['r'] > e['r'] + 80: break
                    if e2.get('a') != a: continue
                    if e2['k'] == 'shop' and e2['r'] <= e['r'] + 1: shop = 1
                    if hit is None and e2['k'] in ('attack', 'cast') and 'cdmg' in e2: hit = e2['r'] - e['r']
                    if trib is None and e2['k'] == 'tribute_start': trib = e2['r'] - e['r']
                    if hit is not None and trib is not None: break
                first = 'trib' if trib is not None and (hit is None or trib < hit) else ('farm' if hit is not None else 'none')
                rows.append((e['gems'], hp, shop, first, hit if hit is not None else -1, trib if trib is not None else -1))
print(n, 'games', len(rows) / n, 'Q recalls/game')
for lo, hi in ((0, 0), (1, 24), (25, 39), (40, 999)):
    s = [r for r in rows if lo <= r[0] <= hi]
    if not s: continue
    c = collections.Counter(r[3] for r in s)
    print(f'bag {lo}-{hi}: {len(s)/n:.1f}/g  shop {np.mean([r[2] for r in s]):.2f} hp {np.mean([r[1] for r in s]):.2f} first: ' + ' '.join(f'{k} {v/len(s):.2f}' for k, v in c.items()),
          f'rounds to camp hit (farm-first) {np.median([r[4] for r in s if r[3]=="farm"]) if c["farm"] else -1}, to tribute (trib-first) {np.median([r[5] for r in s if r[3]=="trib"]) if c["trib"] else -1}')
