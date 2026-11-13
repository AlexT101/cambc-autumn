"""endrace.py by team name: in games where both sides held a winning bag at once, each named team's race wins, its winning
tribute attempts and how they ended, and its winning-bag deaths. Usage: py c5_side.py ANALYSIS_DIR"""
import gzip, json, sys
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from endrace import game as race


def game(d):
    r = race(d)
    meta = json.loads((d/'meta.json').read_text())
    names = [t['name'] for t in meta['teams']]
    if not r: return dict(race=False, names=names, w=meta['result']['winner'])
    R = json.load(gzip.open(d/'rounds.json.gz'))
    team = {c['id']: c['team'] for c in meta['champions']}
    deaths = Counter()
    for l in gzip.open(d/'events.jsonl.gz', 'rt'):
        e = json.loads(l)
        if e['k'] == 'death':
            t = team[e['v']]
            if e['gems'] + R['gems'][t][max(0, e['r'] - 2)] >= 1000: deaths[names[t]] += 1
    return dict(race=True, names=names, w=r['w'], att={names[t]: [a['end'] for a in r['att'][t]] for t in (0, 1)}, deaths=deaths)


if __name__ == '__main__':
    dirs = [p for p in Path(sys.argv[1]).iterdir() if (p/'meta.json').exists()]
    with ProcessPoolExecutor(32) as ex:
        rows = [o for o in ex.map(game, dirs, chunksize=8) if o]
    teams = sorted({n for r in rows for n in r['names']})
    print(f'{len(rows)} games, {sum(r["race"] for r in rows)} races')
    for n in teams:
        allg = [r for r in rows if n in r['names']]
        R = [r for r in allg if r['race']]
        won = sum(1 for r in R if r['names'][r['w']] == n)
        ends = Counter(e for r in R for e in r['att'][n])
        none = sum(1 for r in R if not r['att'][n])
        print(f'{n}: all games won {sum(1 for r in allg if r["names"][r["w"]] == n)}/{len(allg)}; races won {won}/{len(R)}; '
              f'winning attempts {sum(ends.values())} ({sum(ends.values())/max(1, len(R)):.1f}/race) ends {ends.most_common()}; '
              f'no attempt in {none}; winning-bag deaths {sum(r["deaths"][n] for r in R)}')
