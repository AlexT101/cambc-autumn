# At every fight start (first cross-team champion hit with none within 12 tiles in the previous 10 rounds), for the champions of
# both teams within 8: health fraction, and camp damage taken in the previous 20 rounds (as a share of max health).
# Then: does camp damage taken beforehand predict losing the fight (kills within 15 rounds, within 12 tiles)?
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from common import *
from concurrent.futures import ProcessPoolExecutor
def one(g):
    d = g['dir']; m = meta(d); R = rounds(d); us = g['us']
    team = {c['id']: c['team'] for c in m['champions']}; CH = {c['id']: c for c in R['champions']}
    hits = []; camp = defaultdict(list); deaths = []
    for e in events(d):
        if e['k'] in ('attack', 'cast') and any(v in team and team[v] != team[e['a']] for v, a in (e.get('dmg') or [])):
            hits.append((e['r'], e['a'], tuple(e['f'])))
        elif e['k'] == 'camp_attack':
            if e.get('tgt') is not None: camp[e['tgt']].append((e['r'], e['dmg']))
            for v, a in (e.get('xdmg') or []): camp[v].append((e['r'], a))
        elif e['k'] == 'death' and e.get('linked') is None: deaths.append(e)
    out = []
    for i, h in enumerate(hits):
        if any(h[0] - 10 <= x[0] <= h[0] and j < i and cheb(x[2], h[2]) <= 12 for j, x in enumerate(hits[max(0, i - 200):i], start=max(0, i - 200))): continue
        r, a, f = h; j = r - 2
        if j < 0: continue
        side = {}
        for s, t in (('us', us), ('them', 1 - us)):
            cs = [c for c in CH if team[c] == t and CH[c]['alive'][j] and cheb((CH[c]['x'][j], CH[c]['y'][j]), f) <= 8]
            side[s] = dict(n=len(cs), hp=sum(CH[c]['hp'][j] for c in cs), mh=sum(CH[c]['maxHp'][j] for c in cs),
                           camp=sum(x for c in cs for (rr, x) in camp[c] if r - 20 <= rr <= r))
        if not side['us']['n'] or not side['them']['n']: continue
        ku = sum(1 for e in deaths if r <= e['r'] <= r + 15 and team[e['v']] != us and cheb(tuple(e['at']), f) <= 12)
        kt = sum(1 for e in deaths if r <= e['r'] <= r + 15 and team[e['v']] == us and cheb(tuple(e['at']), f) <= 12)
        out.append(dict(init='us' if team[a] == us else 'them', us=side['us'], them=side['them'], ku=ku, kt=kt, map=g['map']))
    return out
if __name__ == '__main__':
    with ProcessPoolExecutor(30) as ex: res = [x for o in ex.map(one, games()) for x in o]
    json.dump(res, open(S + '/campfight.json', 'w'))
    import statistics as st
    for s in ('us', 'them'):
        print(s, 'camp dmg in prior 20r / max hp of those present: mean %.3f; hp frac mean %.2f' % (
            st.mean(x[s]['camp'] / x[s]['mh'] for x in res), st.mean(x[s]['hp'] / x[s]['mh'] for x in res)))
    # outcome by who took more camp damage (relative), at equal counts
    c = defaultdict(lambda: [0, 0, 0])
    for x in res:
        if x['us']['n'] != x['them']['n']: continue
        du = x['us']['camp'] / x['us']['mh']; dt = x['them']['camp'] / x['them']['mh']
        k = ('we took >=10% more camp dmg' if du - dt >= 0.10 else ('they took >=10% more' if dt - du >= 0.10 else 'similar'), x['init'])
        c[k][0] += 1; c[k][1] += x['ku']; c[k][2] += x['kt']
    for k in sorted(c): n, a, b = c[k]; print('%-45s n=%5d our kills %4d theirs %4d share %.2f' % (k, n, a, b, a / max(1, a + b)))
    # who starts fights against a camp-damaged side
    c2 = Counter()
    for x in res:
        du = x['us']['camp'] / x['us']['mh']; dt = x['them']['camp'] / x['them']['mh']
        c2[(x['init'], 'target side camp-damaged>=15%' if (dt if x['init'] == 'us' else du) >= 0.15 else 'no')] += 1
    print(c2)
