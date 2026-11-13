"""Smaller-bag Prism deaths in Prism encounters: was the bigger seen, who closed in, what branch, did it flee."""
import gzip, json, sys, collections, zipfile
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
RANGE = 6

def cheb(c, d, i):
    if c['x'][i] is None or d['x'][i] is None: return 99
    return max(abs(c['x'][i]-d['x'][i]), abs(c['y'][i]-d['y'][i]))

def g(d):
    meta = json.loads((d/'meta.json').read_text()); R = json.load(gzip.open(d/'rounds.json.gz'))
    names = {int(c['id']): c['name'] for c in meta['champions']}; team = {int(c['id']): int(c['team']) for c in meta['champions']}
    ch = {int(c['id']): c for c in R['champions']}
    pr = [i for i in ch if names[i] == 'Prism']
    if len(pr) != 2: return []
    try: z = zipfile.ZipFile(meta['source'])
    except Exception: z = None
    br = {}
    if z:
        for f in ('team-a.stdout', 'team-b.stdout'):
            try: txt = z.read(f).decode(errors='replace')
            except KeyError: continue
            for line in txt.splitlines():
                if line.startswith('D '):
                    p = line.split(); br[(int(p[1]), int(p[2]))] = p[3]
    deaths = {}
    for l in gzip.open(d/'events.jsonl.gz', 'rt'):
        e = json.loads(l)
        if e['k'] == 'death' and e['v'] in pr: deaths.setdefault(e['v'], []).append((e['r'], names.get(e.get('by'), 'camp') if e.get('by') is not None else 'camp'))
    a, b = pr; A, B = ch[a], ch[b]; n = len(A['x'])
    out = []; i = 0
    while i < n:
        if A['alive'][i] and B['alive'][i] and cheb(A, B, i) <= RANGE:
            r0 = i
            big, sm = (a, b) if A['gems'][i] >= B['gems'][i] else (b, a)
            j = i
            while j < n and ch[a]['alive'][j] and ch[b]['alive'][j] and cheb(A, B, j) <= RANGE+3: j += 1
            smdead = any(r0 <= r <= j+2 for r, _ in deaths.get(sm, []))
            bigdead = any(r0 <= r <= j+2 for r, _ in deaths.get(big, []))
            S, Bg = ch[sm], ch[big]
            # first round within 8 before r0 and who moved closer
            k = r0
            while k > 0 and S['alive'][k-1] and Bg['alive'][k-1] and cheb(S, Bg, k-1) <= 9: k -= 1
            seen = any(big == x for x in (S['sees'][r0] or [])) if S['sees'][r0] is not None else None
            seen_prev = any(big == x for x in (S['sees'][max(0, r0-1)] or []))
            # who closed the last step: compare distances with one side frozen
            sm_in = big_in = 0
            for t in range(max(1, k), r0+1):
                d_now = cheb(S, Bg, t)
                # distance if sm had stayed
                ds = max(abs(S['x'][t-1]-Bg['x'][t]), abs(S['y'][t-1]-Bg['y'][t])) if S['x'][t-1] is not None and Bg['x'][t] is not None else d_now
                db = max(abs(S['x'][t]-Bg['x'][t-1]), abs(S['y'][t]-Bg['y'][t-1])) if S['x'][t] is not None and Bg['x'][t-1] is not None else d_now
                if d_now < ds: sm_in += 1
                if d_now < db: big_in += 1
            allies_s = sum(1 for c in ch if team[c] == team[sm] and c != sm and ch[c]['alive'][r0] and cheb(ch[c], S, r0) <= 8)
            allies_b = sum(1 for c in ch if team[c] == team[big] and c != big and ch[c]['alive'][r0] and cheb(ch[c], Bg, r0) <= 8)
            out.append(dict(r0=r0, gs=S['gems'][r0], gb=Bg['gems'][r0], fs=S['foc'][r0], fb=Bg['foc'][r0], hs=S['hp'][r0]/S['maxHp'][r0], hb=Bg['hp'][r0]/Bg['maxHp'][r0],
                            smdead=smdead, bigdead=bigdead, seen=seen, seen_prev=seen_prev, sm_in=sm_in, big_in=big_in, brs=br.get((r0, sm), '?'), brs_prev=br.get((max(1, r0-2), sm), '?'),
                            as_=allies_s, ab=allies_b, dmin=min(cheb(S, Bg, t) for t in range(r0, j)) if j > r0 else 99))
            i = j + 1
        else:
            i += 1
    return out

if __name__ == '__main__':
    dirs = [d for d in Path(sys.argv[1]).iterdir() if (d/'meta.json').exists()]
    with ProcessPoolExecutor(32) as ex: E = [x for r in ex.map(g, dirs, chunksize=8) for x in r]
    print('encounters', len(E))
    for lab, sel in (('smaller dies', lambda e: e['smdead'] and not e['bigdead']), ('no death', lambda e: not e['smdead'] and not e['bigdead'])):
        S = [e for e in E if sel(e)]
        if not S: continue
        m = lambda f: round(sum(f(e) for e in S)/len(S), 3)
        print(f'== {lab}: n {len(S)}')
        print('  round median', sorted(e['r0'] for e in S)[len(S)//2], ' gems small/big median', sorted(e['gs'] for e in S)[len(S)//2], sorted(e['gb'] for e in S)[len(S)//2])
        print('  focus ratio big/small mean', m(lambda e: e['fb']/max(1, e['fs'])), ' hp small', m(lambda e: e['hs']), 'hp big', m(lambda e: e['hb']))
        print('  small saw big at r0', m(lambda e: bool(e['seen'])), ' at r0-1', m(lambda e: e['seen_prev']))
        print('  small stepped in (steps)', m(lambda e: e['sm_in']), ' big stepped in', m(lambda e: e['big_in']), ' small stepped in >=1', m(lambda e: e['sm_in'] > 0))
        print('  allies near small', m(lambda e: e['as_']), ' near big', m(lambda e: e['ab']), ' min dist', m(lambda e: e['dmin']))
        print('  small branch at r0', collections.Counter(e['brs'] for e in S).most_common(8))
        print('  small branch at r0-2', collections.Counter(e['brs_prev'] for e in S).most_common(8))
    # death rate of smaller by focus ratio and small-steps-in
    print('-- smaller death rate by focus ratio (big/small) x small stepped in')
    bins = collections.defaultdict(lambda: [0, 0])
    for e in E:
        fr = e['fb']/max(1, e['fs'])
        k = ('<1.15' if fr < 1.15 else '1.15-1.4' if fr < 1.4 else '1.4-2' if fr < 2 else '2+', e['sm_in'] > 0)
        bins[k][0] += 1; bins[k][1] += e['smdead'] and not e['bigdead']
    for k in sorted(bins): print('  ', k, bins[k][0], round(bins[k][1]/bins[k][0], 3))
