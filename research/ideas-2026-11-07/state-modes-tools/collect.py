"""Per game, samples every 10 rounds: leads, the next 100 rounds' lead change split by source, deaths, and
each team's behaviour (bags, enemy-half share, spacing). usage: collect.py ANALYSIS_DIR SET OUT.json
SET: ladder (us = 'stellar best girl'), oa (us = ocean vs astraeus), oo (self-play, one side by hash)."""
import gzip, json, os, sys
from concurrent.futures import ProcessPoolExecutor

STEP, W = 10, 100
SET = sys.argv[2]


def cheb(a, b):
    return max(abs(a[0] - b[0]), abs(a[1] - b[1]))


def one(d):
    try:
        m = json.load(open(os.path.join(d, 'meta.json')))
        if not m.get('validation', {}).get('ok', True):
            return None
        names = [t.get('name') for t in m['teams']]
        if SET == 'ladder':
            if 'stellar best girl' not in names:
                return None
            us = names.index('stellar best girl')
        elif SET == 'oa':
            if sorted(names) != ['astraeus', 'ocean']:
                return None
            us = names.index('ocean')
        else:
            if names != ['ocean', 'ocean']:
                return None
            us = int(os.path.basename(d)[-1], 16) % 2
        r = json.load(gzip.open(os.path.join(d, 'rounds.json.gz')))
        rounds, last = r['round'], m['result']['rounds']
        ch = r['champions']
        team = {c['id']: c['team'] for c in ch}
        n = len(rounds)
        idx = {rd: i for i, rd in enumerate(rounds)}
        spawn = []
        for t in (0, 1):
            ps = [(c['x'][0], c['y'][0]) for c in ch if c['team'] == t]
            spawn.append((sum(p[0] for p in ps) / len(ps), sum(p[1] for p in ps) / len(ps)))
        us_ = us
        tot = [list(r['gems'][t]) for t in (0, 1)]
        earned = [[0.0] * n, [0.0] * n]
        for c in ch:
            for i in range(n):
                tot[c['team']][i] += c['gems'][i]
                earned[c['team']][i] += c['earned'][i]
        # Events by round: farm gems, bags taken by kills, bags lost to camps, deaths.
        farm = [{}, {}]; took = [{}, {}]; camp_loss = [{}, {}]; deaths = [{}, {}]; bag_deaths = [{}, {}]
        drec = []
        for line in gzip.open(os.path.join(d, 'events.jsonl.gz'), 'rt'):
            e = json.loads(line)
            k = e.get('k')
            if k == 'capture':
                for cid, gems, gold in e['shares']:
                    t = team[cid]
                    farm[t][e['r']] = farm[t].get(e['r'], 0) + gems
            elif k == 'death':
                vt = team[e['v']]
                if not e.get('linked') or e['v'] < e['linked']:
                    i0 = idx.get(e['r'], 0)
                    at = e['at']
                    home = cheb(at, spawn[vt]) <= cheb(at, spawn[1 - vt])
                    near = 0
                    for c in ch:
                        if c['team'] == vt and c['id'] != e['v'] and c['alive'][i0] and cheb((c['x'][i0], c['y'][i0]), at) <= 4:
                            near += 1
                    drec.append({'r': e['r'], 'us': int(vt == us_), 'gems': e.get('gems', 0), 'home': int(home), 'camp': int(not (e.get('by') in team and team.get(e.get('by')) != vt)),
                                 'lead': tot[us_][i0] - tot[1 - us_][i0], 'near': near})
                deaths[vt][e['r']] = deaths[vt].get(e['r'], 0) + 1
                g = e.get('gems', 0)
                if g >= 20:
                    bag_deaths[vt][e['r']] = bag_deaths[vt].get(e['r'], 0) + 1
                by = e.get('by')
                if by is not None and by in team and team[by] != vt:
                    took[1 - vt][e['r']] = took[1 - vt].get(e['r'], 0) + e.get('gemsTo', g)
                else:
                    camp_loss[vt][e['r']] = camp_loss[vt].get(e['r'], 0) + g

        def ssum(dct, a, b):
            return sum(v for rd, v in dct.items() if a < rd <= b)

        them = 1 - us
        out = []
        for i, rd in enumerate(rounds):
            if rd % STEP or rd >= last or rd == 0:
                continue
            end = min(rd + W, last)
            j = idx.get(end, n - 1)
            s = {'r': rd, 'lead': tot[us][i] - tot[them][i], 'trib': r['gems'][us][i] - r['gems'][them][i],
                 'gold': earned[us][i] - earned[them][i], 'tus': r['gems'][us][i], 'tthem': r['gems'][them][i],
                 'dl': (tot[us][j] - tot[them][j]) if end < last else None, 'full': end - rd == W}
            s['cum'] = [ssum(farm[us], 0, rd), ssum(farm[them], 0, rd), ssum(took[us], 0, rd), ssum(took[them], 0, rd),
                        ssum(camp_loss[us], 0, rd), ssum(camp_loss[them], 0, rd)]
            if end < last:
                s['src'] = [ssum(farm[us], rd, end), ssum(farm[them], rd, end), ssum(took[us], rd, end),
                            ssum(took[them], rd, end), ssum(camp_loss[us], rd, end), ssum(camp_loss[them], rd, end)]
                s['dth'] = [ssum(deaths[us], rd, end), ssum(deaths[them], rd, end)]
                s['bagd'] = [ssum(bag_deaths[us], rd, end), ssum(bag_deaths[them], rd, end)]
            beh = []
            for t in (us, them):
                alive = [c for c in ch if c['team'] == t and c['alive'][i]]
                if not alive:
                    beh.append(None)
                    continue
                pos = [(c['x'][i], c['y'][i]) for c in alive]
                bags = [c['gems'][i] for c in alive]
                far = sum(1 for p in pos if cheb(p, spawn[t]) > cheb(p, spawn[1 - t]))
                if len(pos) > 1:
                    nn = sum(min(cheb(p, q) for q in pos if q is not p) for p in pos) / len(pos)
                else:
                    nn = None
                beh.append({'alive': len(alive), 'bag': sum(bags), 'maxbag': max(bags), 'far': far / len(alive), 'nn': nn,
                            'hp': sum(c['hp'][i] / c['maxHp'][i] for c in alive) / len(alive)})
            s['beh'] = beh
            out.append(s)
        return {'dir': os.path.basename(d), 'opp': names[them], 'win': int(m['result']['winner'] == us), 'last': last,
                'map': m['map']['name'], 'n': len(ch) // 2, 'samples': out, 'deaths': drec,
                'final_cum': [ssum(farm[us], 0, last), ssum(farm[them], 0, last), ssum(took[us], 0, last), ssum(took[them], 0, last),
                              ssum(camp_loss[us], 0, last), ssum(camp_loss[them], 0, last)]}
    except Exception as e:
        print('skip', d, repr(e), file=sys.stderr)
        return None


if __name__ == '__main__':
    root, out = sys.argv[1], sys.argv[3]
    dirs = [os.path.join(root, x) for x in os.listdir(root) if os.path.exists(os.path.join(root, x, 'meta.json'))]
    with ProcessPoolExecutor(16) as p:
        games = [g for g in p.map(one, dirs, chunksize=4) if g]
    json.dump(games, open(out, 'w'))
    print(SET, len(dirs), 'dirs,', len(games), 'games')
