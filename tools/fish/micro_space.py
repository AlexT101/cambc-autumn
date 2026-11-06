"""Spacing in contact: the walked end tile, by structured hypotheses (MICRO.md section 3), plus
bush, wall and camp-fire tile use (sections 4 and 5).

    python3 tools/fish/micro_space.py OUT.json [--splits fit held seventh]

Population: micro_rows turns, completed, not stunned, off spawn, no tribute/teleport channel,
no dash, teleport or tribute this turn, a visible enemy within 5 at turn start, end tile among
the candidates (start tile and its walkable neighbours; walls, holes, altars, the enemy spawn and
visible units block). Each hypothesis scores "the end tile is in the hypothesis's best set" on a
class of turns, against the expected hit rate of a uniformly random candidate of the same class
(sum of |best| / |class tiles|). Classes use the turn's own outcome (engage / decline / walked),
so these are tile choices given the class, not class predictions.
"""
import argparse
import collections

from combat_common import one_turn_damage
from micro_common import MELEE_T, NAMES, RANGED, SPLITS, Tally, cohorts, dist, ehp, rows, split_of, write


def as_champ(e):
    return dict(type=e['type'], cd=e['cd'], strength=e['str'], focus=e['focus'], hp=e['hp'], maxHp=e['maxhp'])


class Hit:
    """In-best-set agreement with a random-candidate expectation, per split."""

    def __init__(self):
        self.n = collections.Counter(); self.ok = collections.Counter(); self.rand = collections.Counter()
        self.unique = collections.Counter(); self.unique_ok = collections.Counter(); self.ex = collections.defaultdict(list)

    def add(self, r, tiles, score, end, best='min'):
        vals = [score(t) for t in tiles]
        b = min(vals) if best == 'min' else max(vals)
        if all(v == b for v in vals):
            return   # no choice under this score
        s = split_of(r['cohort'])
        bestset = [t for t, v in zip(tiles, vals) if v == b]
        self.n[s] += 1
        hit = end in bestset
        self.ok[s] += hit
        self.rand[s] += len(bestset) / len(tiles)
        if len(bestset) == 1:
            self.unique[s] += 1; self.unique_ok[s] += hit
        if not hit and len(self.ex[s]) < 8:
            self.ex[s].append(dict(game=r['game'], round=r['round'], actor=r['actor'], type=NAMES[r['type']]))

    def report(self):
        return {s: dict(n=self.n[s], ok=self.ok[s], acc=round(self.ok[s] / self.n[s], 4), random=round(self.rand[s] / self.n[s], 4),
                        unique=self.unique[s], unique_ok=self.unique_ok[s], errors=self.ex[s]) for s in self.n}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('out')
    p.add_argument('--splits', nargs='+', default=['fit', 'held'])
    a = p.parse_args()
    cs = cohorts(a.splits)
    H = collections.defaultdict(Hit)
    T = Tally()
    for r in rows(cs):
        if not r['done'] or r['stunned'] or r['at_home'] or r['ch'] not in (0, 1) or r['y']['end'] is None:
            continue
        acts = r['y']['acts']
        if any(x[0] == 'Cast ability' and x[3] == 6 for x in acts) or any(x[0] in ('Teleport channel', 'Submit gems') for x in acts):
            continue
        en = [e for e in r['enemies'] if e['d'] <= 5]
        if not en:
            continue
        end = tuple(r['y']['end'])
        tiles = [tuple(t[:2]) for t in r['tiles']]
        if end not in tiles:
            continue
        tinfo = {tuple(t[:2]): t for t in r['tiles']}
        pos = tuple(r['pos'])
        ranged = r['type'] in RANGED
        tn = NAMES[r['type']]
        my = max(ehp(r), 1)
        live = [e for e in r['enemies']]
        melee_e = [e for e in live if e['type'] in MELEE_T]
        ranged_e = [e for e in live if e['type'] in RANGED]

        def danger(q):
            return round(sum(0 if e['stun'] > 0 else one_turn_damage(as_champ(e), dist(q, (e['x'], e['y']))) for e in live) / my, 6)

        def dnear(q, es, cap=9):
            return min([dist(q, (e['x'], e['y'])) for e in es] + [cap])

        walked = end != pos
        hit = any(c['foe'] and (c['dmg'] > 0 or c['stun']) for x in r['y']['eff'] for c in x['champs'])
        d0 = dnear(pos, live)
        d1 = dnear(end, live)
        # Descriptive: distance kept at turn end to the nearest melee / ranged enemy, by own type.
        if melee_e:
            T.add(r, (tn, 'end dist to nearest melee enemy', min(dnear(end, melee_e), 7)))
        if ranged_e:
            T.add(r, (tn, 'end dist to nearest ranged enemy', min(dnear(end, ranged_e), 7)))
        T.add(r, (tn, 'turns'))
        cls = 'engage' if (d1 <= (3 if ranged else 1)) else ('decline' if d1 > d0 else 'hold')
        T.add(r, (tn, 'class', cls, 'walked', walked))
        if ranged and melee_e and dnear(pos, melee_e) <= 2:
            k_ = (tn, 'ranged, melee enemy within 2 at start')
            T.add(r, k_ + ('turns',))
            T.add(r, k_ + ('ends >= 3 from every melee enemy',), dnear(end, melee_e) >= 3)
            T.add(r, k_ + ('walked',), walked)
            T.add(r, k_ + ('hit',), hit)
            T.add(r, k_ + ('stood and hit',), hit and not walked)
            esc = [t for t in tiles if dnear(t, melee_e) >= 3]
            T.add(r, k_ + ('a tile >= 3 from every melee enemy exists',), bool(esc))
            if esc:
                T.add(r, k_ + ('escape tile exists: ends >= 3',), dnear(end, melee_e) >= 3)
        # Section 3 hypotheses.
        if ranged and walked:
            near = [t for t in tiles if dnear(t, live) <= 3]
            if near and dnear(end, live) <= 3:
                # Ranged walking but staying in range of something: farthest from melee among in-range tiles.
                H['ranged, walks, ends within 3 of an enemy: max distance to nearest melee enemy (in-range tiles)'].add(
                    r, near, lambda q: min(dnear(q, melee_e), 3), end, 'max')
                H['ranged, walks, ends within 3 of an enemy: min danger (in-range tiles)'].add(r, near, danger, end)
            if d1 > d0:
                H['ranged, walks away (decline): min danger among farther tiles'].add(
                    r, [t for t in tiles if dnear(t, live) > d0], danger, end)
                H['ranged, walks away (decline): max distance to nearest enemy among farther tiles'].add(
                    r, [t for t in tiles if dnear(t, live) > d0], lambda q: dnear(q, live), end, 'max')
            if melee_e and dnear(pos, melee_e) <= 2:
                H['ranged, walks, a melee enemy within 2: ends at distance >= 3 from every melee enemy'].add(
                    r, tiles, lambda q: dnear(q, melee_e) >= 3, end, 'max')
        if not ranged and walked:
            adj = [t for t in tiles if dnear(t, live) <= 1]
            if d1 <= 1 and len(adj) >= 2:
                weakest = min((e for e in live if any(dist(t, (e['x'], e['y'])) <= 1 for t in adj)), key=lambda e: (ehp(e), e['id']))
                H['melee, walks, ends adjacent: adjacent to the weakest reachable enemy'].add(
                    r, adj, lambda q: dist(q, (weakest['x'], weakest['y'])) <= 1, end, 'max')
                H['melee, walks, ends adjacent: min danger among adjacent tiles'].add(r, adj, danger, end)
                H['melee, walks, ends adjacent: most enemies adjacent'].add(
                    r, adj, lambda q: sum(dist(q, (e['x'], e['y'])) <= 1 for e in live), end, 'max')
                H['melee, walks, ends adjacent: fewest enemies adjacent'].add(
                    r, adj, lambda q: sum(dist(q, (e['x'], e['y'])) <= 1 for e in live), end, 'min')
                if r['type'] == 10:
                    H['Varg, walks, ends adjacent: most enemies within 2 (splash)'].add(
                        r, adj, lambda q: sum(dist(q, (e['x'], e['y'])) <= 2 for e in live), end, 'max')
            if d1 > d0:
                H['melee, walks away (decline): min danger among farther tiles'].add(
                    r, [t for t in tiles if dnear(t, live) > d0], danger, end)
                H['melee, walks away (decline): max distance to nearest enemy among farther tiles'].add(
                    r, [t for t in tiles if dnear(t, live) > d0], lambda q: dnear(q, live), end, 'max')
        if walked:
            H['any, walks: min danger over all candidates'].add(r, tiles, danger, end)
            H['any, walks: same distance class as chosen (d to nearest), min danger'].add(
                r, [t for t in tiles if dnear(t, live) == d1], danger, end)
            # Sections 4-5: bush, wall cover, camp fire, among the same distance class as the end tile.
            same = [t for t in tiles if dnear(t, live) == d1]
            H['any, walks: bush preferred (same distance class)'].add(r, same, lambda q: tinfo[q][2], end, 'max')
            H['any, walks: wall-adjacent preferred (same distance class)'].add(r, same, lambda q: tinfo[q][4] > 0, end, 'max')
            H['any, walks: least awake-camp fire (same distance class)'].add(r, same, lambda q: tinfo[q][3], end, 'min')
            H['any, walks: least awake-camp fire (all candidates)'].add(r, tiles, lambda q: tinfo[q][3], end, 'min')
        # Bush use descriptive.
        nb = sum(t[2] for t in r['tiles'])
        if nb:
            T.add(r, ('bush', 'turns with a bush candidate'))
            T.add(r, ('bush', 'ends on bush'), tinfo[end][2])
            T.add(r, ('bush', 'expected bush share x1000'), round(1000 * nb / len(r['tiles'])))
            T.add(r, ('bush', 'starts on bush'), r['in_bush'])
            T.add(r, ('bush', 'starts and ends on bush'), r['in_bush'] and tinfo[end][2])
        # Ambush: hits from a bush on an enemy not on a bush (that enemy cannot see the attacker).
        if hit:
            T.add(r, ('hit turns', 'attacker starts on bush', r['in_bush']))
    out = dict(hypotheses={k: v.report() for k, v in H.items()}, tallies=T.report(), cohorts=cs)
    for k, v in H.items():
        print(k, {s: (d['ok'], d['n'], d['acc'], d['random']) for s, d in v.report().items()})
    write(a.out, out)


if __name__ == '__main__':
    main()
