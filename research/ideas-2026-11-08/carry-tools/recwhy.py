"""Spar body's completed recalls: hp, gems, gold, and the RF* traces / branch letters during the channel."""
import json, gzip, os, sys, collections, zipfile, numpy as np, re
sys.path.insert(0, os.path.expanduser('~/tmp-offload/carry'))
from econ import load, H
sys.path.insert(0, '/home/ubuntu/cambc-autumn/research/ideas-2026-11-08/spar-tools'); import local
S = load(H + 'spar/ana'); RW = 600
tally = collections.Counter(); n = 0
for o in 'FM':
    for mp, side, m in local.matches(f'spar-c27-o29{o}'):
        k = os.path.basename(os.path.dirname(m['replay'])) + '/' + os.path.basename(m['replay']).split('.')[0]
        if k not in S or not os.path.exists(m['replay']): continue
        ot = 1 if side == 'a' else 0; d = H + 'spar/ana/' + S[k]; n += 1
        z = zipfile.ZipFile(m['replay']); out = z.read('team-%s.stdout' % 'ab'[ot]).decode(errors='replace')
        br = {}; rf = collections.defaultdict(set)
        for line in out.splitlines():
            t = line.split()
            if len(t) >= 4 and t[0] == 'D': br[(int(t[1]), int(t[2]))] = t[3]
            elif t and t[0] in ('RFKEEP', 'RFDROP', 'RFLAND', 'RFLOST', 'RFDEAD') and len(t) >= 3: rf[(int(t[1]), int(t[2]))].add(t[0])
        meta = json.load(open(d + '/meta.json')); ch = {c['id']: c for c in meta['champions']}
        R = json.load(gzip.open(d + '/rounds.json.gz')); ri = {r: j for j, r in enumerate(R['round'])}; C = {c['id']: c for c in R['champions']}
        st = {}
        for l in gzip.open(d + '/events.jsonl.gz'):
            e = json.loads(l)
            if e['r'] > RW: break
            a = e.get('a')
            if a is None or ch[a]['team'] != ot: continue
            if e['k'] == 'recall_start': st[a] = e['r']
            elif e['k'] == 'recall_end' and a in st:
                r0 = st[a]; j = ri.get(r0)
                if j is None: continue
                hp = C[a]['hp'][j] / max(1, C[a]['maxHp'][j])
                letters = ''.join(br.get((r, a), '?') for r in range(r0, e['r'] + 1))
                rfs = set().union(*[rf.get((r, a), set()) for r in range(r0, e['r'] + 2)])
                cls = ('healthy' if hp >= 0.6 else 'hurt') + ('+gems' if e['gems'] else '-nogems')
                why = 'RFKEEP' if 'RFKEEP' in rfs else ('Q' if 'Q' in letters else ('G' if 'G' in letters else 'K'))
                tally[(cls, why)] += 1
for k, v in sorted(tally.items()): print(k, round(v / n, 2))
