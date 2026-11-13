"""By bot (team name): captured gems by zone (own <0.4, middle 0.4-0.6, enemy >0.6 of the group's Chebyshev share
from the two spawn centres) by r300 / r600; middle groups' first wakes per cycle and captures (to r600); Prism bag
(mean, living Prism) at r150 / r300; deaths and Prism deaths a game. usage: py edenial.py EXTRACT"""
import json, gzip, glob, os, sys, collections
from concurrent.futures import ProcessPoolExecutor
A = sys.argv[1]
CH = json.load(open(A + '/enums.json'))['champions']
TS = (300, 600)


def one(d):
    m = json.load(open(d + '/meta.json'))
    name = {t: m['teams'][t]['name'] for t in (0, 1)}
    team = {c['id']: c['team'] for c in m['champions']}
    typ = {c['id']: CH[c['type']] for c in m['champions']}
    mp = json.load(open(os.path.join(d, m['mapFile'])))
    camps = {c['id']: c for c in mp['camps']}
    R = json.load(gzip.open(d + '/rounds.json.gz'))
    ri = {r: i for i, r in enumerate(R['round'])}
    cen = {}
    for t in (0, 1):
        xs = [(c['x'][0], c['y'][0]) for c in R['champions'] if c['team'] == t and c['x'][0] is not None]
        cen[t] = (sum(a for a, b in xs) / len(xs), sum(b for a, b in xs) / len(xs))
    gpos = {}
    for g in mp['groups']:
        ps = [(camps[c]['x'], camps[c]['y']) for c in g['camps'] if c in camps]
        if ps: gpos[g['id']] = (sum(a for a, b in ps) / len(ps), sum(b for a, b in ps) / len(ps))

    def zone(g, t):
        x, y = gpos[g]
        do = max(abs(x - cen[t][0]), abs(y - cen[t][1])); de = max(abs(x - cen[1 - t][0]), abs(y - cen[1 - t][1]))
        s = do / max(1e-9, do + de)
        return 'own' if s < 0.4 else 'mid' if s <= 0.6 else 'enemy'

    out = collections.Counter()
    out[('games', name[0])] += 1; out[('games', name[1])] += 1
    out[('wins', name[m['result']['winner']])] += 1
    woke = {}
    for l in gzip.open(d + '/events.jsonl.gz', 'rt'):
        e = json.loads(l); r = e['r']; k = e['k']; g = e.get('g')
        if k == 'death':
            v = e['v']; out[('deaths', name[team[v]])] += 1
            if typ[v] == 'Prism': out[('prism_deaths', name[team[v]])] += 1
            continue
        if g not in gpos: continue
        if k == 'group_respawn': woke.pop(g, None)
        elif k == 'group_wake' and g not in woke and r <= 600:
            woke[g] = team.get(e.get('by'), -1)
            if woke[g] >= 0 and zone(g, 0) == 'mid': out[('mid_wakes', name[woke[g]])] += 1
        elif k == 'capture':
            woke.pop(g, None)
            if r <= 600 and zone(g, 0) == 'mid': out[('mid_caps', name[e['team']])] += 1
            for cid, gm, gd in e['shares']:
                t = team[cid]
                for T in TS:
                    if r <= T: out[('gems', T, zone(g, t), name[t])] += gm
    for c in R['champions']:
        if typ[c['id']] != 'Prism': continue
        for T in (150, 300):
            i = ri.get(T)
            if i is not None and c['alive'][i]:
                out[('bag', T, name[c['team']])] += c['gems'][i] or 0; out[('bagn', T, name[c['team']])] += 1
    return out


if __name__ == '__main__':
    ds = [os.path.dirname(p) for p in glob.glob(A + '/*/meta.json')]
    tot = collections.Counter()
    with ProcessPoolExecutor(48) as ex:
        for o in ex.map(one, ds, chunksize=8): tot.update(o)
    bots = sorted({k[1] for k in tot if k[0] == 'games'})
    for b in bots:
        n = tot[('games', b)]
        print('%-10s games %d win %.1f%%' % (b, n, 100 * tot[('wins', b)] / n))
        for T in TS:
            print('  gems by r%d: %s' % (T, ' '.join('%s %.1f' % (z, tot[('gems', T, z, b)] / n) for z in ('own', 'mid', 'enemy'))))
        mw = tot[('mid_wakes', 'x')] or sum(tot[('mid_wakes', x)] for x in bots); mc = sum(tot[('mid_caps', x)] for x in bots)
        print('  middle to r600: wakes %.2f a game (%.1f%%), captures %.2f (%.1f%%)' % (
            tot[('mid_wakes', b)] / n, 100 * tot[('mid_wakes', b)] / max(1, mw), tot[('mid_caps', b)] / n, 100 * tot[('mid_caps', b)] / max(1, mc)))
        print('  Prism bag: %s' % ' '.join('r%d %.1f (n=%d)' % (T, tot[('bag', T, b)] / max(1, tot[('bagn', T, b)]), tot[('bagn', T, b)]) for T in (150, 300)))
        print('  deaths %.2f a game, Prism deaths %.2f' % (tot[('deaths', b)] / n, tot[('prism_deaths', b)] / n))
