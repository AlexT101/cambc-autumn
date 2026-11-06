"""Fights beside awake camps (MICRO.md section 5), from micro_rows.

    python3 tools/fish/micro_camps.py OUT.json [--splits fit held seventh]

For each visible enemy that the actor can damage this turn (one-turn reach > 0) on a completed,
unstunned turn off spawn: is the enemy inside an awake visible camp's range, is the actor, and
does the actor hit that enemy. Also: Fish kills whose victim stood in camp fire, and contested
camp fights (actor and an enemy both inside the same awake group's range).
"""
import argparse

from micro_common import NAMES, Tally, cohorts, dist, ehp, rows, write

CAMP_RANGE = {0: 3, 1: 4, 4: 5, 5: 4}


def in_fire(p, camps):
    return [c for c in camps if c['awake'] and c['type'] in CAMP_RANGE and dist(p, (c['x'], c['y'])) <= CAMP_RANGE[c['type']]]


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('out')
    p.add_argument('--splits', nargs='+', default=['fit', 'held'])
    a = p.parse_args()
    cs = cohorts(a.splits)
    T = Tally()
    for r in rows(cs):
        if not r['done'] or r['stunned'] or r['at_home']:
            continue
        camps = r['camps']
        me_f = in_fire(r['pos'], camps)
        hit_ids = {c['id'] for x in r['y']['eff'] for c in x['champs'] if c['foe'] and (c['dmg'] > 0 or c['stun'])}
        dead = {c['id'] for x in r['y']['eff'] for c in x['champs'] if c['foe'] and c['dead']}
        for e in r['enemies']:
            if e['mine'] <= 0:
                continue
            e_f = in_fire((e['x'], e['y']), camps)
            shared = bool({c['group'] for c in e_f} & {c['group'] for c in me_f})
            key = ('self in fire' if me_f else 'self clear', 'enemy in fire' if e_f else 'enemy clear')
            T.add(r, key + ('opportunities',))
            T.add(r, key + ('hit',), e['id'] in hit_ids)
            if me_f and e_f:
                T.add(r, ('both in fire', 'same group' if shared else 'different groups', 'opportunities'))
                T.add(r, ('both in fire', 'same group' if shared else 'different groups', 'hit'), e['id'] in hit_ids)
            if e['mine'] >= ehp(e):
                T.add(r, ('killable', 'enemy in fire' if e_f else 'enemy clear', 'opportunities'))
                T.add(r, ('killable', 'enemy in fire' if e_f else 'enemy clear', 'killed'), e['id'] in dead)
            if e['id'] in dead:
                T.add(r, ('fish kill', 'victim in camp fire', bool(e_f)))
    out = dict(tallies=T.report(), cohorts=cs)
    for s, c in out['tallies'].items():
        print(s)
        for k, v in c.items():
            print('  ', k, v)
    write(a.out, out)


if __name__ == '__main__':
    main()
