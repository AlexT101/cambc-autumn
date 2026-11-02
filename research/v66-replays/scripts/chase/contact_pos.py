# First contacts (an enemy within 8 after 5+ rounds with none): the champion's position and what follows.
import sys, json
sys.path.insert(0, 'research/v66-replays/scripts/extract')
from common import *
from concurrent.futures import ProcessPoolExecutor
def one(r):
    d = r['dir']; m = meta(d); R = rounds(d); us = r['us']; mp = mapj(m)
    F = [spawn_field(mp, 0), spawn_field(mp, 1)]; N = len(R['round']); CH = R['champions']
    NM = {c['id']: c['name'] for c in m['champions']}
    W, H = mp['width'], mp['height']
    blk = set(map(tuple, mp['walls'])) | set(map(tuple, mp['holes'])) | set(map(tuple, mp['altars']))
    bush = set(map(tuple, mp.get('bushes', [])))
    sc = []
    for t in (0, 1):
        s = mp['spawn'][t]; sc.append(((s['minX'] + s['maxX']) / 2, (s['minY'] + s['maxY']) / 2))
    rix = {rr: i for i, rr in enumerate(R['round'])}
    hit = defaultdict(float)
    for e in events(d):
        if e['k'] in ('attack', 'cast') and 'a' in e and e['r'] in rix:
            for v, x in (e.get('dmg') or []): hit[(rix[e['r']], e['a'], v)] += x
    P = lambda c, i: (c['x'][i], c['y'][i])
    out = []
    for c in CH:
        t = c['team']; f = F[t]; fo = F[1 - t]; last = -99
        for i in range(1, N - 20):
            if not c['alive'][i]: continue
            p = P(c, i)
            en = [e for e in CH if e['team'] != t and e['alive'][i]]
            if not en: continue
            near = min(en, key=lambda e: cheb(P(e, i), p)); dn = cheb(P(near, i), p)
            if dn <= 8:
                if i - last >= 5 and f.get(p) not in (None, 0):
                    al = [a for a in CH if a['team'] == t and a is not c and a['alive'][i]]
                    da = min((cheb(P(a, i), p) for a in al), default=99)
                    fh = f.get(p); fe = f.get(P(near, i))
                    opn = sum(1 for dx in range(-2, 3) for dy in range(-2, 3) if (dx or dy) and 0 <= p[0] + dx < W and 0 <= p[1] + dy < H and (p[0] + dx, p[1] + dy) not in blk)
                    cs = max(1, cheb(p, (round(sc[t][0]), round(sc[t][1]))))
                    branch = sum(1 for dx in (-1, 0, 1) for dy in (-1, 0, 1) if (dx or dy) and f.get((p[0] + dx, p[1] + dy), 999) == fh - 1)
                    # who struck first between c and any enemy in the next 10 rounds
                    first = None
                    for j in range(i, i + 10):
                        a = sum(hit[(j, c['id'], e['id'])] for e in en); b = sum(hit[(j, e['id'], c['id'])] for e in en)
                        if a or b: first = 'tie' if a and b else ('me' if a else 'them'); break
                    out.append(dict(side='us' if t == us else 'them', opp=r['opp'], me=NM[c['id']], hp=c['hp'][i] / c['maxHp'][i],
                                    home=fh, own=fh <= fo.get(p, 999), cut=(fe - fh) if fe is not None else None, dn=dn, da=da,
                                    nE=sum(1 for e in en if cheb(P(e, i), p) <= 8), nA=sum(1 for a in al if cheb(P(a, i), p) <= 8),
                                    open=opn, detour=fh / cs, branch=branch, bush=p in bush, first=first, gems=c['gems'][i],
                                    a5=sum(1 for a in al if a['alive'][i+5] and cheb(P(a, i+5), P(c, i+5) if c['alive'][i+5] else p) <= 8),
                                    e5=sum(1 for e in CH if e['team'] != t and e['alive'][i+5] and cheb(P(e, i+5), P(c, i+5) if c['alive'][i+5] else p) <= 8),
                                    a10=sum(1 for a in al if a['alive'][i+10] and cheb(P(a, i+10), P(c, i+10) if c['alive'][i+10] else p) <= 8),
                                    e10=sum(1 for e in CH if e['team'] != t and e['alive'][i+10] and cheb(P(e, i+10), P(c, i+10) if c['alive'][i+10] else p) <= 8),
                                    ad=sorted(cheb(P(a, i), p) for a in al)[:3], ed=sorted(cheb(P(e, i), p) for e in en)[:3],
                                    died20=any(not c['alive'][j] for j in range(i, min(N, i + 20)))))
                last = i
    return out
if __name__ == '__main__':
    with ProcessPoolExecutor(60) as ex: res = [x for o in ex.map(one, games()) for x in o]
    json.dump(res, open(sys.argv[1], 'w')); print(len(res))
