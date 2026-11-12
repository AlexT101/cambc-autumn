"""Per champion-round rows for Mite's bodies (and the opponent's), with positions, for state and movement rules.
Usage: python3 pass2.py OUT.jsonl.gz GROUPS(comma: live,ranked) [procs]
Row (one per alive body per round r >= 2, with turn context = end of r-1):
 r, cid, x0, y0, x1, y1, hp0, mhp, gems0, gems1, prio(r), dEnemy, nEn5, nAl5, dAltar0, dAltar1, dSpawn0, dSpawn1,
 dAlly0, dAlly1, hitChamp, hitCamp, tribStart, recallEnd, tpStart, cd0, cd1, enemyHpFrac(nearest), enemyGems(nearest),
 seenEn5, dmgTakenPrev, chan0, wasHitByChampPrevRound, nearestEnemyId, lockHit, dEnemyCentroid0, dEnemyCentroid1"""
import sys, json, gzip, collections
from multiprocessing import Pool
import ml
from feat import blockers, bfs

def cheb(a, b): return max(abs(a[0] - b[0]), abs(a[1] - b[1]))

def one(sd):
    try:
        g = ml.load(sd)
    except Exception:
        return None
    if g is None: return None
    m, rd, ev, mp = g['meta'], g['rd'], g['ev'], g['map']
    team = {c['id']: c['team'] for c in m['champions']}
    name = {c['id']: c['name'] for c in m['champions']}
    C = {c['id']: c for c in rd['champions']}; ids = list(C); nR = len(rd['round'])
    blk = blockers(mp)
    sp = [((s['minX'] + s['maxX']) // 2, (s['minY'] + s['maxY']) // 2) for s in mp['spawn']]
    dsp = [bfs(mp, blk - {sp[t]}, sp[t]) for t in (0, 1)]
    alt = [tuple(a) for a in mp['altars']]
    hitc = set(); hitm = set(); trib = set(); rece = set(); tps = set(); lockh = set(); dmgin = collections.defaultdict(float); hitby = set()
    for e in ev:
        k = e['k']; r = e['r']
        if k in ('attack', 'cast'):
            a = e['a']
            if e.get('lock'): lockh.add((r, a))
            for x in e.get('dmg', []):
                if x[0] in team and team[x[0]] != team[a]: hitc.add((r, a)); dmgin[(r, x[0])] += x[1]; hitby.add((r, x[0]))
            if e.get('camp') is not None or e.get('cdmg'): hitm.add((r, a))
        elif k == 'tribute_start': trib.add((r, e['a']))
        elif k == 'recall_end': rece.add((r, e['a']))
        elif k == 'teleport_start': tps.add((r, e['a']))
    def P(c, i):
        cc = C[c]
        return (cc['x'][i], cc['y'][i]) if cc['alive'][i] else None
    rows = []
    for r in range(2, nR + 1):
        i0, i1 = r - 2, r - 1
        P0 = {c: P(c, i0) for c in ids}; P1 = {c: P(c, i1) for c in ids}
        for c in ids:
            p0 = P0[c]
            if not p0: continue
            t = team[c]; cc = C[c]
            en = [x for x in ids if team[x] != t and P0[x]]
            al = [x for x in ids if team[x] == t and x != c and P0[x]]
            dE = min([cheb(p0, P0[x]) for x in en] or [99])
            if dE > 10 and cc['gems'][i0] == 0 and (r, c) not in trib: continue
            near = min(en, key=lambda x: (cheb(p0, P0[x]), x)) if en else None
            p1 = P1[c] or p0
            dA0 = min(cheb(p0, a) for a in alt); dA1 = min(cheb(p1, a) for a in alt)
            dS0 = dsp[t].get(p0); dS1 = dsp[t].get(p1)
            dL0 = min([cheb(p0, P0[x]) for x in al] or [99]); dL1 = min([cheb(p1, P1[x] or P0[x]) for x in al] or [99])
            e5 = [x for x in en if cheb(p0, P0[x]) <= 5]
            if e5:
                cx = sum(P0[x][0] for x in e5) / len(e5); cy = sum(P0[x][1] for x in e5) / len(e5)
                dc0 = max(abs(p0[0] - cx), abs(p0[1] - cy)); dc1 = max(abs(p1[0] - cx), abs(p1[1] - cy))
            else:
                dc0 = dc1 = None
            seen = set(cc['sees'][i0] or [])
            rows.append([r, c, p0[0], p0[1], p1[0], p1[1], round(cc['hp'][i0]), cc['maxHp'][i0], cc['gems'][i0], cc['gems'][i1], cc['prio'][i1], dE,
                         len(e5), sum(1 for x in al if cheb(p0, P0[x]) <= 5), dA0, dA1, dS0, dS1, dL0, dL1,
                         1 if (r, c) in hitc else 0, 1 if (r, c) in hitm else 0, 1 if (r, c) in trib else 0, 1 if (r, c) in rece else 0,
                         1 if (r, c) in tps else 0, cc['cd0'][i0], cc['cd1'][i0],
                         round(C[near]['hp'][i0] / max(1, C[near]['maxHp'][i0]), 3) if near is not None else None, C[near]['gems'][i0] if near is not None else None,
                         sum(1 for x in e5 if x in seen), round(dmgin.get((r - 1, c), 0)), cc['chan'][i0], 1 if (r - 1, c) in hitby else 0, near,
                         1 if (r, c) in lockh else 0, dc0, dc1])
    return {'mid': g['mid'], 'src': g['src'], 'ver': g['ver'], 'mite': g['mite'], 'win': g['win'], 'opp': g['opp'], 'map': g['mapname'],
            'champs': [[c['id'], c['team'], c['name']] for c in m['champions']], 'nalt': len(alt), 'rows': rows}

if __name__ == '__main__':
    outp = sys.argv[1]; srcs = sys.argv[2].split(','); procs = int(sys.argv[3]) if len(sys.argv) > 3 else 6
    ds = [d for s in srcs for d in ml.dirs(s)]
    with Pool(procs) as P, gzip.open(outp, 'wt') as f:
        n = 0
        for o in P.imap_unordered(one, ds, chunksize=2):
            if o is None: continue
            f.write(json.dumps(o) + '\n'); n += 1
    print('wrote', n)
