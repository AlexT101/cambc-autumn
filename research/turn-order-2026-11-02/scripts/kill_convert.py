"""Does damage short of a kill convert? For every champion turn that damages an enemy champion and leaves it alive
(off its spawn), what became of the victim: killed by the hitter's team before its health came back to full (a
conversion), healed to full first, killed by a camp, or still alive and hurt after H rounds. Split by the victim's
health share after the turn, and by whether the turn stunned it (kill-value.md).

usage: python3 kill_convert.py EXTRACT_DIR [--team NAME] [--jobs N] [--out PKL]
  --team: count only hits by the team of that name (e.g. astraeus-294)
"""
import argparse
import gzip
import json
import os
import pickle
import sys
from collections import Counter, defaultdict
from multiprocessing import Pool

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from tolib import G, index  # noqa: E402

H = 60  # rounds followed


def spawns(ex, g):
    m = json.load(open(os.path.join(ex, g.meta['mapFile'].replace('../', ''))))
    return m['spawn']


def on(rect, p):
    return p is not None and rect['minX'] <= p[0] <= rect['maxX'] and rect['minY'] <= p[1] <= rect['maxY']


def game(args):
    ex, d, team_name = args
    try:
        g = G(ex, d)
    except Exception:
        return []
    sp = spawns(ex, g)
    names = [t['name'] for t in g.meta['teams']]
    out = []
    for r in range(1, g.N + 1):
        evs = g.by_round[r]
        turns = defaultdict(list)  # (t, actor) -> events
        for e in evs:
            if e.get('a') is not None and e['t'] >= 0:
                turns[(e['t'], e['a'])].append(e)
        for (t, c), te in turns.items():
            us = g.team[c]
            if team_name and names[us] != team_name:
                continue
            dealt, stunned = Counter(), set()
            for e in te:
                if e['k'] in ('attack', 'cast'):
                    for v, x in e.get('dmg') or []:
                        if v in g.team and g.team[v] != us:
                            dealt[v] += x
                    for v in e.get('stun') or []:
                        if v in g.team and g.team[v] != us:
                            stunned.add(v)
            if not dealt:
                continue
            last = max(e['s'] for e in te)
            for v, x in dealt.items():
                if any(de['v'] == v and de['s'] <= last + 1 and de['t'] == t for de in g.deaths[r]):
                    continue  # killed this turn
                p = g.pos_at(v, r, last + 1)
                if p is None or on(sp[g.team[v]], p):
                    continue
                hp = g.hp(v, r - 1) if r > 1 else g.at(v, 'maxHp', 1)
                for e in evs:
                    if e['s'] > last:
                        break
                    if e['k'] in ('attack', 'cast'):
                        for w, y in e.get('dmg') or []:
                            if w == v:
                                hp -= y
                    elif e['k'] == 'camp_attack' and e.get('tgt') == v:
                        hp -= e.get('dmg', 0)
                mx = g.at(v, 'maxHp', r)
                if hp <= 0:
                    continue
                frac = min(1.0, hp / mx)
                # who acts first: did v act earlier this round?
                fv = g.first[r].get(v)
                acted = fv is not None and fv < te[0]['s']
                fate, when = 'alive', None
                for rr in range(r, min(g.N, r + H) + 1):
                    de = next((de for de in g.deaths[rr] if de['v'] == v and (rr > r or de['s'] > last)), None)
                    if de is not None:
                        fate = 'camp' if de.get('camp') else ('self' if de.get('by') == c else 'team')
                        when = rr - r
                        break
                    if rr > r and g.hp(v, rr) >= g.at(v, 'maxHp', rr) - 0.01:
                        fate, when = 'healed', rr - r
                        break
                out.append((g.type[c], g.type[v], frac, v in stunned, acted, fate, when, r))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('ex')
    ap.add_argument('--team')
    ap.add_argument('--jobs', type=int, default=16)
    ap.add_argument('--out')
    a = ap.parse_args()
    games = [(a.ex, x['dir'], a.team) for x in index(a.ex) if x['ok']]
    recs = []
    with Pool(a.jobs) as pool:
        for o in pool.imap_unordered(game, games, chunksize=4):
            recs += o
    if a.out:
        pickle.dump(recs, open(a.out, 'wb'))
    report(recs, len(games))


def report(recs, ngames):
    print(f'{len(recs)} partial hits off spawn in {ngames} games ({len(recs) / ngames:.1f} a game)')
    bins = [0, .1, .2, .3, .4, .5, .6, .7, .8, .9, 1.01]

    def row(label, rs):
        n = len(rs)
        if not n:
            return
        f = Counter(x[5] for x in rs)
        conv = (f['self'] + f['team']) / n
        within3 = sum(1 for x in rs if x[5] in ('self', 'team') and x[6] <= 3) / n
        within1 = sum(1 for x in rs if x[5] in ('self', 'team') and x[6] <= 1) / n
        print(f'{label:<18} {n:>7} conv {100 * conv:5.1f}%  <=1r {100 * within1:5.1f}%  <=3r {100 * within3:5.1f}%  '
              f'healed {100 * f["healed"] / n:5.1f}%  camp {100 * f["camp"] / n:4.1f}%  alive@{H} {100 * f["alive"] / n:4.1f}%')

    for stun in (False, True):
        print(f'-- stunned by the hit: {stun}')
        for lo, hi in zip(bins, bins[1:]):
            row(f'health {lo:.1f}-{min(hi, 1):.1f}', [x for x in recs if x[3] == stun and lo <= x[2] < hi])
        row('all', [x for x in recs if x[3] == stun])
    print('-- not stunned, by whether the victim had acted this round')
    for acted in (False, True):
        row(f'acted {acted}', [x for x in recs if not x[3] and x[4] == acted])
    print('-- not stunned, by victim')
    for k, _ in Counter(x[1] for x in recs).most_common():
        row(k, [x for x in recs if not x[3] and x[1] == k])


if __name__ == '__main__':
    main()
