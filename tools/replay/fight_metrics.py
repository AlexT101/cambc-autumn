"""Fight metrics of extract.mjs output, per bot (team name): deaths and kills a game (a linked pair's second body not
counted), deaths to champions and to camps, the kill share at equal numbers (champion kills where the alive champions
of each team within 8 of the victim at the round's start are equal in number: the killer's team's share), captures,
captured and tributed gems. Both teams need different names (self-play merges them).
usage: py tools/replay/fight_metrics.py EXTRACT_DIR [EXTRACT_DIR...]"""
import sys, json, gzip
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor


def cheb(a, b): return max(abs(a[0] - b[0]), abs(a[1] - b[1]))


def one(args):
    ex, g = args
    d = g['dir']
    meta = json.load(open(f'{ex}/{d}/meta.json'))
    ev = [json.loads(l) for l in gzip.open(f'{ex}/{d}/events.jsonl.gz', 'rt')]
    R = json.load(gzip.open(f'{ex}/{d}/rounds.json.gz'))
    teams = g['teams']
    idx = {r: i for i, r in enumerate(R['round'])}
    ch = {c['id']: c for c in R['champions']}
    team = {c['id']: c['team'] for c in meta['champions']}
    out = {t: Counter() for t in (0, 1)}
    for t in (0, 1):
        out[t]['games'] += 1
        out[t]['gems'] += g['gems'][t]

    def near(i, at, t):
        n = 0
        for c, a in ch.items():
            if team[c] == t and a['alive'][i] and a['x'][i] is not None and a['x'][i] >= 0 and cheb((a['x'][i], a['y'][i]), at) <= 8: n += 1
        return n
    for e in ev:
        k = e['k']
        if k == 'death' and e.get('linked') is None:
            v = e['v']; t = team[v]
            out[t]['deaths'] += 1
            by = e.get('by')
            if by is not None and by in team and team[by] != t:
                out[1 - t]['kills'] += 1
                out[t]['deaths_champion'] += 1
                i = idx.get(e['r'] - 1)
                if i is not None and e.get('at'):
                    if near(i, tuple(e['at']), t) == near(i, tuple(e['at']), 1 - t):
                        out[1 - t]['eq_kills'] += 1; out[t]['eq_deaths'] += 1
            else:
                out[t]['deaths_other'] += 1
        elif k == 'capture':
            out[e['team']]['captures'] += 1
            out[e['team']]['capture_gems'] += sum(s[1] for s in e.get('shares', []))
    return {teams[t]: dict(out[t]) for t in (0, 1)}


if __name__ == '__main__':
    tot = defaultdict(Counter)
    jobs = []
    for ex in sys.argv[1:]:
        for g in json.load(open(f'{ex}/index.json'))['games']:
            if g.get('ok'): jobs.append((ex, g))
    with ProcessPoolExecutor(24) as pool:
        for res in pool.map(one, jobs, chunksize=4):
            for name, c in res.items(): tot[name].update(c)
    for name, c in sorted(tot.items()):
        ng = c['games']
        print(f"{name}: games {ng}")
        for k in ('gems', 'captures', 'capture_gems', 'deaths', 'deaths_champion', 'deaths_other', 'kills'):
            print(f"   {k:16s} {c[k] / ng:8.2f} /game")
        print(f"   kill share at equal numbers {c['eq_kills'] / max(1, c['eq_kills'] + c['eq_deaths']):.3f} of {c['eq_kills'] + c['eq_deaths']}")
