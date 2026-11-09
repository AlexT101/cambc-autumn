"""Outcome after traced decisions: usage trcout.py TRACE.json ANA_DIR W [flipcol=val]. Lines 'TAG r me tgt ...'.
Per line: target died within W rounds (by our team), we died within W; first line per (game, me, tgt) within W only."""
import json, sys, os, gzip, collections, beh
T, A, W = sys.argv[1], sys.argv[2], int(sys.argv[3])
cond = sys.argv[4] if len(sys.argv) > 4 else None
tr = json.load(open(T)); idx = json.load(open(A + '/index.json'))['games']
res = collections.Counter(); chk = collections.Counter()
for g in idx:
    stem = os.path.basename(g['source']).split('-', 1)[1].rsplit('.', 1)[0]
    lines = tr.get(stem)
    if not lines: continue
    meta, rd, ev = beh.load(A + '/' + g['dir'])
    Tm = 0 if stem.endswith('-12') else 1
    team = {c['id']: c['team'] for c in meta['champions']}
    pos = {c['id']: c for c in rd['champions']}; R = rd['round']
    deaths = collections.defaultdict(list)
    for e in ev:
        if e['k'] == 'death': deaths[e['v']].append((e['r'], e.get('by'), e.get('gems', 0)))
    seen = {}
    for l in lines:
        x = l.split()
        if cond:
            c, v = cond.split('='); 
            if x[int(c)] != v: continue
        r, me, tg = int(x[1]), int(x[2]), int(x[3])
        if (me, tg) in seen and r - seen[(me, tg)] <= W: continue
        seen[(me, tg)] = r
        chk['team_ok'] += team.get(me) == Tm; chk['tgt_enemy'] += team.get(tg) == 1 - Tm; chk['n'] += 1
        tk = [d for d in deaths[tg] if r <= d[0] <= r + W and team.get(d[1]) == Tm]
        md = [d for d in deaths[me] if r <= d[0] <= r + W]
        res['n'] += 1; res['tk'] += bool(tk); res['md'] += bool(md); res['tkgems'] += sum(d[2] for d in tk); res['mdgems'] += sum(d[2] for d in md)
print('id check', dict(chk))
n = res['n']; print(f"episodes {n}: target killed by us {res['tk']/n:.3f} (gems {res['tkgems']/n:.1f}/ep), we died {res['md']/n:.3f} (gems {res['mdgems']/n:.1f}/ep)")
