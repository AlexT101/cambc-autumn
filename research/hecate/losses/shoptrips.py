"""Trips home with an empty bag: rounds walked homeward empty-handed before arriving on spawn, and
whether the arrival shopped. Per 100 game rounds, us vs them.

py research/hecate/losses/shoptrips.py [GAME_DIR ...]   (default: every game, split W/L)
"""
import collections
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from common import our_games, Game, US  # noqa


def cheb(a, b):
    return max(abs(a[0] - b[0]), abs(a[1] - b[1]))


def trips(g, team):
    sp = g.map.raw['spawn'][team]
    on = lambda p: p and sp['minX'] <= p[0] <= sp['maxX'] and sp['minY'] <= p[1] <= sp['maxY']
    shops = collections.defaultdict(set)
    recall_end = set()
    for e in g.events:
        if e['k'] == 'shop' and g.team_of.get(e['a']) == team and e.get('gold', 0) < 0:
            shops[e['a']].add(e['r'])
        if e['k'] == 'recall_end' and g.team_of.get(e['a']) == team:
            recall_end.add((e['a'], e['r']))
    sc = g.map.spawn_center(team)
    out = collections.Counter()
    for cid in g.team_ids[team]:
        ch = g.ch(cid)
        run = 0
        for r in range(2, len(ch['x']) + 1):
            i = r - 1
            p0, p1 = g.pos(cid, i - 1), g.pos(cid, i)
            if not p1:
                run = 0
                continue
            if on(p1) and not on(p0) and (cid, r) not in recall_end:
                if run >= 3:
                    shopped = any(r <= s <= r + 2 for s in shops[cid])
                    hurt = (ch['hp'][i - 1] or 0) < 0.6 * (ch['maxHp'][i - 1] or 1)
                    k = 'shop' if shopped else 'heal' if hurt else 'other'
                    out['trips:' + k] += 1
                    out['rounds:' + k] += run
                run = 0
                continue
            if p0 and ch['gems'][i - 1] == 0 and cheb(p1, sc) < cheb(p0, sc):
                run += 1
            elif p0 and p0 != p1:
                run = 0
    return out


def main():
    if len(sys.argv) > 1:
        sets = {'given': [Game(d) for d in sys.argv[1:]]}
    else:
        gs = our_games()
        sets = {'L': [g for g in gs if g.winner != g.us], 'W': [g for g in gs if g.winner == g.us]}
    for name, games in sets.items():
        tot = {'us': collections.Counter(), 'them': collections.Counter()}
        rounds = 0
        for g in games:
            us = g.names.index(US)
            tot['us'].update(trips(g, us))
            tot['them'].update(trips(g, 1 - us))
            rounds += g.n_rounds
        for k, c in tot.items():
            print(name, k, {x: round(100 * v / rounds, 1) for x, v in sorted(c.items())}, '(per 100 game rounds)')


if __name__ == '__main__':
    main()
