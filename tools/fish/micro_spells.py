"""Stuns and ground spells for the kits not decoded before (MICRO.md section 2).

    python3 tools/fish/micro_spells.py OUT.json [--splits fit held seventh]

Fish drafts no Ryth, Tavi or Stellar (counted from the micro rows' own types). Covered here, on
contact turns (micro_rows): Prism's unit stun (slot 0) and ground damage (slot 1), Ren's unit
stun (slot 0), Marcella's reset-stun (slot 0: the stun rides on the next basic), and every Fish
stun by source. Targets are scored on the cast's own before-state; ground centres against every
tile within 4 of the caster.
"""
import argparse
import collections

from micro_common import NAMES, RANGED, Score, Tally, cohorts, dist, ehp, rows, write

AB = {1: 'reset', 2: 'damage', 3: 'aoe', 4: 'cc', 5: 'heal', 6: 'dash', 7: 'shield'}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('out')
    p.add_argument('--splits', nargs='+', default=['fit', 'held'])
    a = p.parse_args()
    cs = cohorts(a.splits)
    S = collections.OrderedDict()

    def sc(name):
        return S.setdefault(name, Score(name))

    T = Tally()
    for r in rows(cs):
        info = {e['id']: e for e in r['enemies']}
        T.add(r, ('actor_type_rows', NAMES[r['type']]))
        bs = {b['step']: b for b in r['y']['b']}
        acts = r['y']['eff']
        for i, act in enumerate(acts):
            foes = [c for c in act['champs'] if c['foe']]
            stunned = [c['id'] for c in foes if c['stun']]
            if stunned:
                src = f"{NAMES[r['type']]} {AB.get(act['ab'], 'basic') if act['kind'] == 'Cast ability' else 'basic (Marcella reset-stun)' if r['type'] == 7 else 'basic?'}"
                T.add(r, ('stun_source', src))
                T.add(r, ('stuns_landed', src), len(stunned))
            if act['kind'] != 'Cast ability':
                continue
            b = bs.get(act['step'])
            if not b:
                continue
            en = [dict(id=e[0], x=e[1], y=e[2], hp=e[3], sh=e[4], stun=e[5], gems=e[6], type=e[7], str=e[8]) for e in b['en']]
            pos = b['pos']
            T.add(r, ('cast', NAMES[r['type']], act['slot'], AB.get(act['ab'])))
            T.add(r, ('cast hits', NAMES[r['type']], act['slot'], 'champion' if foes else ('camp' if act['camps'] else 'nothing')))
            if act['ab'] == 4 and r['type'] in (6, 9):
                tt = next((e['type'] for e in en if [e['x'], e['y']] == act['to']), None)
                res = 'kill' if any(c['dead'] for c in foes) else 'stunned' if stunned else \
                    'Marcella (immune)' if tt == 7 else 'other'
                T.add(r, ('unit cc outcome', NAMES[r['type']], res))
            if act['ab'] in (2, 4) and r['type'] in (6, 9):
                # Unit stun (Prism slot 0, Ren slot 0): which visible enemy within 4.
                cand = [e for e in en if dist(pos, (e['x'], e['y'])) <= 4]
                tgt = next((e['id'] for e in cand if [e['x'], e['y']] == act['to']), None)
                if tgt is None or len(cand) < 2:
                    continue
                nm = NAMES[r['type']]
                strength = lambda e: e['str']
                sc(f'{nm} unit stun: min EHP').add(r, min(cand, key=lambda e: (ehp(e), e['id']))['id'], tgt)
                sc(f'{nm} unit stun: max (gems+8)/EHP').add(r, max(cand, key=lambda e: ((e['gems'] + 8) / max(ehp(e), 1), -e['id']))['id'], tgt)
                el = [e for e in cand if e['type'] != 7 and e['stun'] <= 0] or cand
                sc(f'{nm} unit stun: max Strength, eligible (Cassi rule)').add(r, max(el, key=lambda e: (strength(e), -e['id']))['id'], tgt)
                sc(f'{nm} unit stun: nearest').add(r, min(cand, key=lambda e: (dist(pos, (e['x'], e['y'])), e['id']))['id'], tgt)
            if act['ab'] == 3:
                # Ground damage: centre within 4; hits enemy champions and camps within 1.
                camps = [c for c in r['camps']]
                def hits_at(q):
                    ne = sum(dist(q, (e['x'], e['y'])) <= 1 for e in en)
                    nc = sum(dist(q, (c['x'], c['y'])) <= 1 for c in camps)
                    return ne, nc
                cents = [(pos[0] + dx, pos[1] + dy) for dx in range(-4, 5) for dy in range(-4, 5)]
                best = max(hits_at(q)[0] for q in cents)
                ch = hits_at(tuple(act['to']))
                nm = NAMES[r['type']]
                T.add(r, ('ground', nm, 'enemies hit at chosen', ch[0], 'max possible', best))
                T.add(r, ('ground', nm, 'camps in area', min(ch[1], 3)))
                if best >= 2:
                    sc(f'{nm} ground: centre maximises visible enemies within 1 (max >= 2)').add(r, best, ch[0])
                if en:
                    sc(f'{nm} ground: centre maximises visible enemies within 1 (any)').add(r, best, ch[0])
        # When: Prism / Ren with a slot ready and an enemy within 4 at turn start, off spawn.
        if r['type'] in (6, 9) and r['done'] and not r['stunned'] and not r['at_home']:
            near4 = [e for e in r['enemies'] if e['d'] <= 4]
            moved = any(x[0] == 'Move' for x in r['y']['acts'])
            cast = {x[2] for x in r['y']['acts'] if x[0] == 'Cast ability'}
            nm = NAMES[r['type']]
            for slot in ((0, 1) if r['type'] == 6 else (0,)):
                if r['cd'][slot] == 0 and near4:
                    other = 1 - slot if r['type'] == 6 else None
                    if other is not None and other in cast:
                        continue
                    sc(f'{nm} slot {slot}: cast iff standing still (ready, enemy within 4, other slot unused)').add(
                        r, not moved, slot in cast, False)
            if r['type'] == 6 and near4 and (r['cd'][0] == 0 or r['cd'][1] == 0):
                pred = -1 if moved else (0 if r['cd'][0] == 0 else 1)
                act_ = min(cast & {0, 1}) if cast & {0, 1} else -1
                sc('Prism: standing -> slot 0 if ready else slot 1; walking -> none (base: never)').add(r, pred, act_, -1)
            if r['type'] == 6 and r['cd'] == [0, 0] and near4 and not moved and cast & {0, 1}:
                # Both ready, standing: which slot.
                pos = r['pos']
                cents = [(pos[0] + dx, pos[1] + dy) for dx in range(-4, 5) for dy in range(-4, 5)]
                best = max(sum(dist(q, (e['x'], e['y'])) <= 1 for e in r['enemies']) for q in cents)
                T.add(r, ('prism both ready, standing', 'max enemies in a 3x3', min(best, 3), 'cast slot', min(cast & {0, 1})))
        # Marcella's reset-stun: the next basic after slot 0 carries the stun.
        if r['type'] == 7:
            seqa = r['y']['acts']
            for i, x in enumerate(seqa):
                if x[0] == 'Cast ability' and x[2] == 0:
                    nxt = next((y for y in seqa[i + 1:] if y[0] == 'Attack'), None)
                    prv = next((y for y in reversed(seqa[:i]) if y[0] == 'Attack'), None)
                    b = bs.get(nxt[4]) if nxt else None
                    T.add(r, ('marcella reset', 'followed by attack' if nxt else 'no attack'))
                    if not b:
                        continue
                    en = [dict(id=e[0], x=e[1], y=e[2], hp=e[3], sh=e[4], stun=e[5], gems=e[6], type=e[7], str=e[8]) for e in b['en']]
                    cand = [e for e in en if dist(b['pos'], (e['x'], e['y'])) <= 1]
                    tgt = next((e['id'] for e in cand if [e['x'], e['y']] == nxt[1]), None)
                    T.add(r, ('marcella reset', 'second attack on champion' if tgt is not None else 'second attack on camp/other'))
                    if tgt is None:
                        continue
                    pb = bs.get(prv[4]) if prv else None
                    first_t = next((e[0] for e in pb['en'] if [e[1], e[2]] == prv[1]), None) if pb else None
                    T.add(r, ('marcella reset', 'same target as first basic', tgt == first_t))
                    if len(cand) >= 2:
                        strength = lambda e: e['str']
                        sc('Marcella reset-stun basic: min EHP').add(r, min(cand, key=lambda e: (ehp(e), e['id']))['id'], tgt)
                        sc('Marcella reset-stun basic: max Strength unstunned').add(
                            r, max(cand, key=lambda e: (e['stun'] <= 0, strength(e), -e['id']))['id'], tgt)
                        sc('Marcella reset-stun basic: same as first basic').add(r, first_t, tgt)
    out = dict(scores={n: s.report() for n, s in S.items()}, tallies=T.report(), cohorts=cs)
    for s in S.values():
        print(s.line())
    write(a.out, out)


if __name__ == '__main__':
    main()
