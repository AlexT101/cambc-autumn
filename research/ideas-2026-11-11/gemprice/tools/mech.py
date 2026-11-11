"""Mechanism read on an extracted badmaps batch: per body and map class (wheel / other), our and their gem flow.

usage: python3 mech.py EXTDIR [EXTDIR ...]   (extract.mjs output of gp-mech-* runs; bot 0 is ours)
"""
import collections, gzip, json, os, statistics, sys


def games(ext):
    for g in json.load(open(ext + '/index.json'))['games']:
        base = os.path.basename(g['source'])
        yield g, (0 if base.endswith('-12.repl26a') else 1), ('Mt3q' if 'Mt3q' in g['source'] else 'Flp4')


def one(ext, g, us):
    d = ext + '/' + g['dir']
    meta = json.load(open(d + '/meta.json'))
    R = json.load(gzip.open(d + '/rounds.json.gz'))
    ev = [json.loads(l) for l in gzip.open(d + '/events.jsonl.gz', 'rt')]
    mp = json.load(open(os.path.join(ext, 'maps', os.path.basename(meta['mapFile']))))
    team = {c['id']: c['team'] for c in meta['champions']}
    typ = {c['id']: c['name'] for c in meta['champions']}
    groups = {G['id']: G for G in mp['groups']}
    score = R['gems']  # [team][round index]
    rounds = R['round']
    ri = {r: i for i, r in enumerate(rounds)}
    a = collections.Counter()
    side = lambda t: 'us' if t == us else 'them'
    for e in ev:
        k = e['k']
        if k == 'capture':
            t = side(e['team'])
            G = groups.get(e['g'], {})
            gems = sum(s[1] for s in e['shares'])
            i = ri.get(e['r'], len(rounds) - 1)
            enemy = score[1 - e['team']][i]
            a[t + '_cap'] += 1
            a[t + '_cap_gems'] += gems
            if enemy >= 600:
                a[t + '_late_cap'] += 1
                if G.get('gems', 0) == 0: a[t + '_late_gold_cap'] += 1
                elif G.get('gold', 0) > 10 * G.get('gems', 0): a[t + '_late_goldish_cap'] += 1
        elif k == 'death':
            t = side(team[e['v']])
            gems = e.get('gems', 0)
            a[t + '_deaths'] += 1
            a[t + '_died_gems'] += gems
            if typ[e['v']] == 'Prism': a[t + '_prism_died_gems'] += gems
            if gems >= 40: a[t + '_big_deaths'] += 1
        elif k == 'tribute_end':
            t = side(team[e['a']])
            a[t + '_trib'] += 1
            a[t + '_trib_gems'] += e['gems']
        elif k == 'teleport_start':
            a[side(team[e['a']]) + '_tele'] += 1
        elif k == 'lock_place':
            a[side(e['team']) + '_locks'] += 1
    # Bag-weighted carry: the team's carried gems summed over rounds (exposure), and the largest bag.
    for c in R['champions']:
        t = side(c['team'])
        gm = c['gems']
        a[t + '_carry_rounds'] += sum(gm)
        a[t + '_max_bag'] = max(a[t + '_max_bag'], max(gm))
    a['win'] = int(meta['result']['winner'] == us)
    a['rounds'] = meta['result']['rounds']
    a['by_gems'] = int(max(meta['result']['gems']) >= 1000)
    # Round the enemy first reaches 600.
    e600 = next((rounds[i] for i, s in enumerate(score[1 - us]) if s >= 600), None)
    a['enemy600'] = int(e600 is not None)
    return a


def main():
    agg = collections.defaultdict(collections.Counter)
    n = collections.Counter()
    for ext in sys.argv[1:]:
        for g, us, body in games(ext):
            cls = 'wheel' if 'wheel' in g['map'] else 'other'
            a = one(ext, g, us)
            for key in ((body, cls), (body, 'all'), ('both', cls)):
                agg[key].update(a)
                n[key] += 1
    cols = [('win', 'win%'), ('rounds', 'rounds'), ('us_cap_gems', 'cap us'), ('them_cap_gems', 'cap them'),
            ('us_died_gems', 'died us'), ('us_prism_died_gems', 'Prism'), ('them_died_gems', 'died them'),
            ('us_big_deaths', 'big d'), ('us_trib', 'trib us'), ('them_trib', 'trib them'), ('us_tele', 'tele us'),
            ('them_tele', 'tele them'), ('us_late_cap', 'late cap'), ('us_late_gold_cap', 'late gold'),
            ('us_late_goldish_cap', 'late goldish'), ('them_late_cap', 'their late'), ('them_late_gold_cap', 'their late gold'),
            ('us_carry_rounds', 'carry us/rd'), ('them_carry_rounds', 'carry them/rd')]
    print('| body | maps | n | ' + ' | '.join(c[1] for c in cols) + ' |')
    print('|' + '---|' * (3 + len(cols)))
    for key in sorted(agg):
        a, k = agg[key], n[key]
        vals = []
        for c, _ in cols:
            if c == 'win': vals.append(f'{100 * a[c] / k:.1f}')
            elif c.endswith('carry_rounds'): vals.append(f'{a[c] / max(1, a["rounds"]):.0f}')
            else: vals.append(f'{a[c] / k:.1f}')
        print(f'| {key[0]} | {key[1]} | {k} | ' + ' | '.join(vals) + ' |')


if __name__ == '__main__':
    main()
