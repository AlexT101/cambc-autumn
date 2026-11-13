"""Why bystanders don't join: joins.py's engagements, joined with the debug bot's JN/JL/JP/D lines (variants/join-dbg).
For each bystander on the logging team (within 8 of the target at the first hit), its first JN line in rounds r..r+2
gives prey's verdict on the relevant enemy (the target if we attack, the attacker if we defend), and its D line that
turn the branch that took it. usage: joindiag.py EXTRACT_DIR [TEAMNAME]"""
import gzip, json, sys, collections, zipfile
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor

def cheb(a, b): return max(abs(a[0]-b[0]), abs(a[1]-b[1]))
WANT = sys.argv[2] if len(sys.argv) > 2 else 'join-dbg'

def g(d):
    meta = json.loads((d/'meta.json').read_text())
    tnames = [t['name'] for t in meta['teams']]
    if WANT not in tnames: return []
    us = tnames.index(WANT)
    R = json.load(gzip.open(d/'rounds.json.gz'))
    import os
    mp = json.load(open(os.path.join(d, meta['mapFile'])))
    bushes = set(map(tuple, mp['bushes']))
    team = {int(c['id']): int(c['team']) for c in meta['champions']}
    names = {int(c['id']): c['name'] for c in meta['champions']}
    ch = {int(c['id']): c for c in R['champions']}
    jn, br, jl, jp, ja = {}, {}, {}, {}, {}
    def parse(p, line):
        if p[0] == 'D' and len(p) >= 4: br[(int(p[1]), int(p[2]))] = p[3]
        elif p[0] == 'JN':
            head, _, rest = line.partition('|')
            h = head.split()
            ent = {}
            for tok in rest.split():
                base, _, plus = tok.partition('+')
                f = base.split(':')
                code = f[2]
                if plus: code += '>' + plus.split(':')[0]
                ent[int(f[0])] = (int(f[1]), code, f[3:])
            jn[(int(h[1]), int(h[2]))] = (dict(hp=int(h[3]), own=int(h[4]), linked=int(h[5]), heals=int(h[6]), eb=int(h[7]), pr=int(h[8]), tp=int(h[9])), ent)
        elif p[0] == 'JL': jl[(int(p[1]), int(p[2]))] = (int(p[3]), int(p[4]))
        elif p[0] == 'JP': jp[(int(p[1]), int(p[2]))] = int(p[3])
        elif p[0] == 'JA': ja[(int(p[1]), int(p[2]))] = int(p[3]) >= 0
    try:
        z = zipfile.ZipFile(meta['source'])
        for line in z.read('team-a.stdout' if us == 0 else 'team-b.stdout').decode(errors='replace').splitlines():
            p = line.split()
            if not p: continue
            try:
                parse(p, line)
            except (IndexError, ValueError):
                pass
    except Exception as ex:
        return []
    n = len(next(iter(ch.values()))['x'])
    def pos(c, r):
        i = min(max(0, r-1), n-1)
        x = ch[c]['x'][i]
        return None if x is None or not ch[c]['alive'][i] else (x, ch[c]['y'][i])
    hits = collections.defaultdict(set)
    chits = []
    for l in gzip.open(d/'events.jsonl.gz', 'rt'):
        e = json.loads(l)
        if e['k'] in ('attack', 'cast'):
            a = e.get('a')
            if a is None: continue
            if e.get('dmg'):
                for v, dm in e['dmg']:
                    if v in team and team[v] != team[a] and dm > 0: hits[(e['r'], a)].add('champ'); chits.append((e['r'], a, v))
            if e.get('stun'):
                for v in e['stun']:
                    if v in team and team[v] != team[a]: hits[(e['r'], a)].add('champ'); chits.append((e['r'], a, v))
            if e.get('cdmg') or e.get('camp') is not None: hits[(e['r'], a)].add('camp')
    out = []
    last = []
    for (r, a, v) in chits:
        pv = pos(v, r)
        if pv is None: continue
        if any(r - rr <= 6 and rr < r and cheb(pp, pv) <= 10 for rr, pp in last):
            last.append((r, pv)); continue
        last.append((r, pv))
        if r > 900: continue
        for c in ch:
            if c in (a, v) or team[c] != us: continue
            pc = pos(c, r)
            if pc is None or cheb(pc, pv) > 8: continue
            side = 'att' if team[a] == us else 'dfn'
            enemy = v if side == 'att' else a
            did = set()
            for rr in range(r, r+3): did |= hits.get((rr, c), set())
            kind = 'champ' if 'champ' in did else 'camp' if 'camp' in did else 'none'
            # first JN at or after r
            row = None
            for rr in (r+1, r+2, r):
                if (rr, c) in br:
                    row = rr; break
            code, extra, info, b, leave, asked, aimed = 'noturn', None, None, '?', None, None, None
            if row is not None:
                b = br.get((row, c), '?')
                leave = jl.get((row, c))
                asked = jp.get((row, c))
                aimed = ja.get((row, c))
                if (row, c) in jn:
                    info, ent = jn[(row, c)]
                    if enemy in ent:
                        dd, code, extra = ent[enemy]
                    else: code = 'unseen'
                else: code = 'unseen'
            pa = pos(a, row or r); pv2 = pos(v, row or r); pc2 = pos(c, row or r)
            geo = (cheb(pa, pv2) if pa and pv2 else -1, cheb(pc2, pa) if pc2 and pa else -1, cheb(pc2, pv2) if pc2 and pv2 else -1)
            pe = pos(enemy, row or r)
            ebush = pe in bushes if pe else None
            edist = cheb(pc2, pe) if pc2 and pe else -1
            out.append(dict(ebush=ebush, edist=edist, geo=geo, side=side, kind=kind, code=code, extra=extra, info=info, br=b, leave=leave, asked=asked, aimed=aimed,
                            name=names[c], d=cheb(pc, pv), tname=names[enemy]))
    return out

if __name__ == '__main__':
    if len(sys.argv) > 2: WANT = sys.argv[2]
    dirs = [d for d in Path(sys.argv[1]).iterdir() if (d/'meta.json').exists()]
    with ProcessPoolExecutor(32) as ex: B = [x for r in ex.map(g, dirs, chunksize=8) for x in r]
    print('bystanders', len(B), 'games', len(dirs))
    for side in ('att', 'dfn'):
        S = [b for b in B if b['side'] == side]
        print(f'\n== {side}: {len(S)}; joined {sum(b["kind"]=="champ" for b in S)/max(1,len(S)):.3f}')
        for kind in ('champ', 'camp', 'none'):
            K = [b for b in S if b['kind'] == kind]
            if not K: continue
            c = collections.Counter(b['code'] for b in K)
            print(f' {kind:5s} n={len(K):5d} verdict:', ' '.join(f'{k}={v/len(K):.2f}' for k, v in c.most_common()))
        NJ = [b for b in S if b['kind'] != 'champ']
        print(' not joined, by verdict -> branch (top), leave share, chase asked share')
        for code, cnt in collections.Counter(b['code'] for b in NJ).most_common():
            K = [b for b in NJ if b['code'] == code]
            bc = collections.Counter(b['br'] for b in K)
            lv = sum(1 for b in K if b['leave'] and b['leave'][1]) / len(K)
            ak = sum(1 for b in K if b['asked'] is not None) / len(K)
            dist = collections.Counter(min(b['d'], 8) for b in K)
            print(f'  {code:7s} {len(K):5d} {len(K)/len(NJ):.2f} br:', ' '.join(f'{k}={v/len(K):.2f}' for k, v in bc.most_common(6)),
                  f'leave={lv:.2f} asked={ak:.2f} d:', ''.join(f'{k}:{dist[k]/len(K):.2f} ' for k in range(1, 9)))
        # W verdicts: what took the turn
        U = [b for b in NJ if b['code'] == 'unseen']
        if U:
            print('  unseen: enemy in bush', round(sum(1 for b in U if b['ebush'])/len(U), 2), 'enemy dead/gone', round(sum(1 for b in U if b['edist'] < 0)/len(U), 2),
                  'dist to enemy', sorted(collections.Counter(min(b['edist'], 10) for b in U).items()))
        W = [b for b in NJ if b['code'] == 'W']
        if W:
            c = collections.Counter((b['br'], b['asked'] is not None, bool(b['leave'] and b['leave'][1])) for b in W)
            print('  W not joined (branch, chase asked, leave):', c.most_common(10))
        L = [b for b in NJ if b['code'] == 'L']
        if L:
            print('  L geo (hitter-target, me-hitter, me-target) by allies counted:')
            for al in (1, 2, 3):
                K = [b for b in L if b['extra'] and int(b['extra'][0]) == al]
                if K: print(f'   allies={al} n={len(K)} hit-tgt', sorted(collections.Counter(min(b['geo'][0],9) for b in K).items()), ' me-hitter', sorted(collections.Counter(min(b['geo'][1],9) for b in K).items()))
        if L:
            c = collections.Counter((int(b['extra'][0]), int(b['extra'][1])) for b in L if b['extra'])
            print('  L (allies, enemies):', c.most_common(10))
        G = [b for b in NJ if b['code'] == 'G']
        if G:
            print('  G by our own ground:', collections.Counter(b['info']['own'] for b in G if b['info']).most_common())
        by = collections.Counter((b['name'], b['code']) for b in NJ)
        names = collections.Counter(b['name'] for b in NJ)
        for nm, t in names.most_common(8):
            print(f'   {nm:14s} {t:5d}', ' '.join(f'{k}={by[(nm,k)]/t:.2f}' for k in ('unseen','noturn','V','G','Z','N','L','F','E','W')))
