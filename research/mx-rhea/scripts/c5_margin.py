"""Race arithmetic on endgame races, from the replay's exact positions: at each winning tribute's start, the earliest turn an
enemy could stop it (a stunner within its stun reach of the channeller with the stun ready; a lock carrier within 2 of the
altar; straight Chebyshev walks, dead enemies from their spawn after respawn), against its channel length: margin =
stop - dur (>= 0: no stop arrives in time). How attempts end by margin, and whether another altar had a better margin from
the holder's tile (walk + dur). Usage: py c5_margin.py ANALYSIS_DIR [TEAM_NAME]"""
import gzip, json, sys
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from endrace import game as race
from c5_cancel import STUN, cheb

ONLY = sys.argv[2] if len(sys.argv) > 2 else None


def stop_eta(R, i, team, name, t, pos, alt, spawn):
    best = 999
    for c in R['champions']:
        j = int(c['id'])
        if team[j] == t: continue
        nm = name[j]
        if c['alive'][i] and c['x'][i] is not None:
            ep, wait, cd = (c['x'][i], c['y'][i]), 0, None
        else:
            ep, wait = spawn[1 - t], c['respawn'][i] or 0
        reach = STUN.get(nm, (None, None))[1]
        if reach is not None:
            cd = c[f"cd{STUN[nm][0]}"][i] or 0 if c['alive'][i] else 0
            best = min(best, max(wait + max(0, cheb(ep, pos) - reach), cd))
        cons = c['cons'][i] or [0, 0]
        if c['alive'][i] and len(cons) > 2 and cons[2] > 0:
            best = min(best, wait + max(0, cheb(ep, alt) - 2))
    return best


def game(d):
    r = race(d)
    if not r: return None
    meta = json.loads((d/'meta.json').read_text())
    R = json.load(gzip.open(d/'rounds.json.gz'))
    ev = [json.loads(l) for l in gzip.open(d/'events.jsonl.gz', 'rt')]
    team = {c['id']: c['team'] for c in meta['champions']}
    name = {c['id']: c['name'] for c in meta['champions']}
    tnames = [t['name'] for t in meta['teams']]
    rix = {x: i for i, x in enumerate(R['round'])}
    # spawn centres: champion positions at round 1
    spawn = [None, None]
    for c in R['champions']:
        if spawn[c['team']] is None: spawn[c['team']] = (c['x'][0], c['y'][0])
    alts = sorted({tuple(e['altar']) for e in ev if e['k'] == 'tribute_start'})
    w = r['w']
    open_, rows = {}, []
    for e in ev:
        k = e['k']
        if k == 'tribute_start':
            t = team[e['a']]
            if e['gems'] + R['gems'][t][max(0, e['r'] - 2)] < 1000: continue
            if ONLY and tnames[t] != ONLY: continue
            i = rix.get(e['r'])
            if i is None: continue
            pos = tuple(e['at']); alt = tuple(e['altar'])
            m = stop_eta(R, i, team, name, t, pos, alt, spawn) - e['dur']
            # other altars: walk from here to within 1, then the channel (standing tile approximated by the altar)
            other = max((stop_eta(R, i, team, name, t, a, a, spawn) - max(0, cheb(pos, a) - 1) - e['dur'] for a in alts if a != alt), default=None)
            open_[e['a']] = dict(side='winner' if t == w else 'loser', m=m, other=other, dur=e['dur'])
        elif k in ('tribute_end', 'tribute_cancel', 'death') and e.get('a', e.get('v')) in open_:
            a = open_.pop(e.get('a', e.get('v')))
            a['end'] = 'end' if k == 'tribute_end' else ('death' if k == 'death' else e.get('cause', '?'))
            rows.append(a)
    return rows


if __name__ == '__main__':
    dirs = [p for p in Path(sys.argv[1]).iterdir() if (p/'meta.json').exists()]
    rows = []
    with ProcessPoolExecutor(32) as ex:
        for o in ex.map(game, dirs, chunksize=8):
            if o: rows.extend(o)
    print(f'{len(rows)} winning tribute attempts in races')
    B = lambda m: '<-40' if m < -40 else '-40..-11' if m < -10 else '-10..-1' if m < 0 else '>=0'
    for side in ('winner', 'loser', None):
        S = [x for x in rows if side is None or x['side'] == side]
        print(f'== {side or "all"} {len(S)}')
        by = defaultdict(Counter)
        for x in S: by[B(x['m'])][x['end']] += 1
        for b in ('<-40', '-40..-11', '-10..-1', '>=0'):
            print(f'  margin {b:9s} n={sum(by[b].values()):4d}', by[b].most_common())
        neg = [x for x in S if x['m'] < 0]
        print(f'  of {len(neg)} negative-margin starts, another altar had margin >= 0 in {sum(1 for x in neg if x["other"] is not None and x["other"] >= 0)},'
              f' a better margin in {sum(1 for x in neg if x["other"] is not None and x["other"] > x["m"])}')
