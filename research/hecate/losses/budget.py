"""Time budget per champion-round, us vs the opponent, in our losses (and wins).

Each alive champion-round is one of: dead, channel (tribute / real recall), fight (hit a champion),
camp-gem (hit a group with gems), camp-gold (hit a gold-only group), capture (standing on a cleared
group's tiles), walk (moved), still (none of these). The first that applies wins.
py research/hecate/losses/budget.py [--upto 300]
"""
import argparse
import collections
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from common import our_games  # noqa

KINDS = ['dead', 'tribute', 'recall', 'fight', 'camp-gem', 'camp-gold', 'capture', 'walk', 'still']


def budget(g, upto):
    cg = {c['id']: c['group'] for c in g.map.raw['camps']}
    gems = {gr['id']: gr['gems'] for gr in g.map.raw['groups']}
    tiles = {}
    for gr in g.map.raw['groups']:
        for t in gr['tiles']:
            tiles[tuple(t)] = gr['id']
    acts = collections.defaultdict(set)  # (cid, r) -> kinds
    for e in g.events:
        if e['r'] > upto or 'a' not in e:
            continue
        k = e['k']
        key = (e['a'], e['r'])
        if k in ('attack', 'cast'):
            if e.get('camp') is not None or e.get('cdmg'):
                camp = e.get('camp') if e.get('camp') is not None else e['cdmg'][0][0]
                acts[key].add('camp-gem' if gems[cg[camp]] > 0 else 'camp-gold')
            if any(v in g.team_of and g.team_of[v] != g.team_of[e['a']] for v, _ in e.get('dmg', [])):
                acts[key].add('fight')
        elif k == 'move':
            acts[key].add('walk')
    # cleared groups by round from the change rows
    cols = g.rounds['groupCols']
    state = {}
    cleared_at = collections.defaultdict(set)
    rows = sorted(g.rounds['groups'], key=lambda x: x[0])
    j = 0
    for r in range(1, min(upto, len(g.rounds['round'])) + 1):
        while j < len(rows) and rows[j][0] <= r:
            state[rows[j][1]] = rows[j][2]
            j += 1
        cleared_at[r] = {gid for gid, s in state.items() if s == 2}
    out = {0: collections.Counter(), 1: collections.Counter()}
    for c in g.champs:
        cid, team = c['id'], c['team']
        ch = g.ch(cid)
        for r in range(1, min(upto, len(ch['alive'])) + 1):
            i = r - 1
            if not ch['alive'][i] or ch['turn'][i] == 4:
                out[team]['dead'] += 1
                continue
            if ch['chan'][i] == 2:
                out[team]['tribute'] += 1
                continue
            if ch['chan'][i] == 1 and ch['chanT'][i] is not None and ch['chanT'][i] < 4:
                out[team]['recall'] += 1
                continue
            a = acts.get((cid, r), set())
            p = (ch['x'][i], ch['y'][i])
            for k in ('fight', 'camp-gem', 'camp-gold'):
                if k in a:
                    out[team][k] += 1
                    break
            else:
                if p in tiles and tiles[p] in cleared_at[r]:
                    out[team]['capture'] += 1
                elif 'walk' in a:
                    out[team]['walk'] += 1
                else:
                    out[team]['still'] += 1
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--upto', type=int, default=300)
    a = ap.parse_args()
    agg = {'L': [collections.Counter(), collections.Counter()], 'W': [collections.Counter(), collections.Counter()]}
    for g in our_games():
        b = budget(g, a.upto)
        res = 'W' if g.winner == g.us else 'L'
        agg[res][0].update(b[g.us])
        agg[res][1].update(b[g.them])
    for res, (us, them) in agg.items():
        for name, c in (('us', us), ('them', them)):
            tot = sum(c.values())
            print(res, name.ljust(5), ' '.join(f"{k} {100 * c[k] / tot:4.1f}%" for k in KINDS))


if __name__ == '__main__':
    main()
