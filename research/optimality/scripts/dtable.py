# D_m(champion, d): max damage a champion (base stats, both slots ready) can deal to a stationary target
# at Chebyshev distance d within m of its own turns, open ground. Brute force over legal per-turn plans.
import itertools
C = {  # name: (ranged, str, focus, [slot0, slot1]); slot = (kind, mult, range, excl_walk)
    'Ryth': (False, 50, 100, [('ground', 1.0, 4, True), ('reset',)]),
    'Varg': (False, 50, 100, [('reset',), ('shield',)]),
    'Ren': (False, 40, 100, [('unit', 1.25, 4, True), ('dash',)]),
    'Issac': (False, 40, 100, [('reset',), ('dash',)]),
    'Vendetta': (False, 70, 100, [('reset',), ('dash',)]),
    'Marcella': (False, 45, 50, [('reset',), ('unit', 2.0, 4, True)]),
    'Cassi': (True, 30, 70, [('unit', 2.0, 4, True), ('stun',)]),
    'Stellar': (True, 35, 100, [('unit', 2.0, 4, True), ('ground', 1.4, 4, True)]),
    'Prism': (True, 35, 80, [('unit', 1.5, 4, True), ('ground', 1.0, 4, True)]),
    'Tavi': (True, 35, 100, [('reset',), ('unit', 2.2, 4, True)]),
    'Willow': (True, 45, 105, [('heal',), ('reset',)]),
    'Vesper': (True, 45, 100, [('reset',), ('dash',)]),
}


def turn_options(name, d, ready):
    """Yield (new_d, damage, slot_used) for one turn from distance d with slots ready (tuple of bools)."""
    ranged, s, f, slots = C[name]
    rng = 3 if ranged else 1
    casts = [None] + [i for i in (0, 1) if ready[i] and slots[i][0] in ('ground', 'unit', 'reset', 'dash')]
    for cast in casts:
        k = slots[cast] if cast is not None else None
        excl = k is not None and len(k) > 3 and k[3]
        walks = [0] if excl else [0, 1]
        dashes = [0, 1, 2] if k is not None and k[0] == 'dash' else [0]
        for w in walks:
            for dsh in dashes:
                # order: movement can be split around attacks; for a stationary target, moving first then
                # acting is optimal except ranged walk which spends the attack (reset restores it)
                nd = max(1, d - w - dsh)
                dmg = 0.0
                attacks = 0
                if ranged:
                    attack_ok = (w == 0)
                    if k is not None and k[0] == 'reset' and w == 1:
                        attack_ok = True  # walk, reset, attack
                    if attack_ok and nd <= rng: attacks = 1
                    if k is not None and k[0] == 'reset' and w == 0 and nd <= rng: attacks = 2  # attack, reset, attack
                else:
                    if nd <= rng: attacks = 2 if (k is not None and k[0] == 'reset') else 1
                dmg += attacks * s
                if k is not None and k[0] in ('unit', 'ground'):
                    reach = k[2] + (1 if k[0] == 'ground' else 0)
                    if nd <= reach: dmg += k[1] * f
                yield nd, dmg, cast


def D(name, d, m):
    best = 0.0
    def rec(d, t, ready, acc):
        nonlocal best
        best = max(best, acc)
        if t == m: return
        for nd, dmg, cast in turn_options(name, d, ready):
            r2 = list(ready)
            if cast is not None: r2[cast] = False
            rec(nd, t + 1, tuple(r2), acc + dmg)
    rec(d, 0, (True, True), 0.0)
    return best


if __name__ == '__main__':
    for m in (1, 2):
        print(f'D_{m}(d): max damage within {m} own turn(s), both slots ready, base stats')
        print('champion  ' + ' '.join(f'd={d:<4d}' for d in range(1, 8)))
        for name in C:
            print(f'{name:9s} ' + ' '.join(f'{D(name, d, m):6.0f}' for d in range(1, 8)))
        print()
