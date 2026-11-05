"""Which enemy champion Fish hits: gem carriers and channelling enemies.

Rows: tactic_rows.py `target` (each basic attack or unit spell on a visible enemy champion, with
every visible enemy in that action's range from its own before-state). Meaningful choice: >= 2
candidates. Fit (the score's constant) on FIT, scored on HELD.

- Basic attacks: the known min (HP + shield, id) rule, against gem- and channel-aware variants.
- Unit damage spells (ability type 2: Cassi slot 0, Marcella slot 1, Stellar slot 0, Tavi slot 1...):
  max (gems + a) / (HP + shield), lower id on ties; kill-first variants with damage = mult x Focus.
- Pure stuns (ability type 4, Cassi slot 1): the known Strength rule, against a channel-first variant.
"""
import argparse
import collections

from tactic_common import FIT, HELD, NAMES, Score, rows, write

MULT = {(3, 0): 2.0, (7, 1): 2.0, (5, 0): 2.0, (6, 0): 1.5, (11, 1): 1.6, (9, 0): 1.1}


def ehp(e):
    return e['hp'] + e['sh']


def dmg(r):
    return MULT.get((r['type'], int(r['act'][-1])), 0) * r['focus']


def ratio(a):
    return lambda r, cs: min(cs, key=lambda e: (-(e['gems'] + a) / ehp(e), e['id']))


def kill_then(f):
    def g(r, cs):
        k = [e for e in cs if dmg(r) >= ehp(e)]
        return f(r, k) if k else f(r, cs)
    return g


minhp = lambda r, cs: min(cs, key=lambda e: (ehp(e), e['id']))
maxgems = lambda r, cs: min(cs, key=lambda e: (-e['gems'], ehp(e), e['id']))
chan_minhp = lambda r, cs: min(cs, key=lambda e: (e['ch'] == 0, ehp(e), e['id']))
gem_minhp = lambda r, cs: min(cs, key=lambda e: (e['gems'] == 0, ehp(e), e['id']))


def stun_eligible(cs):
    return [e for e in cs if e['type'] != 7 and e['stun'] <= 0]


maxstr = lambda r, cs: min(cs, key=lambda e: (-e['str'], e['id']))
trib_maxstr = lambda r, cs: min(cs, key=lambda e: (e['ch'] != 2, -e['str'], e['id']))
chan_maxstr = lambda r, cs: min(cs, key=lambda e: (e['ch'] == 0, -e['str'], e['id']))


def evaluate(name, data, rule, base, prep=lambda cs: cs, subset=None):
    sc = Score(name)
    for r in data:
        cs = prep(r['cands'])
        if len(cs) < 2 or (subset and not subset(r, cs)):
            continue
        sc.add(r, rule(r, cs)['id'], r['chosen'], base(r, cs)['id'],
               dict(cands=[(e['id'], NAMES[e['type']], e['d'], round(ehp(e)), e['gems'], e['ch']) for e in cs]))
    print(sc.line())
    return sc.report()


def main(out):
    data = list(rows(['target']))
    basic = [r for r in data if r['act'] == 'basic']
    spell = [r for r in data if r['act'] != 'basic' and r['ability'] == 2]
    stun = [r for r in data if r['act'] != 'basic' and r['ability'] == 4]
    res = {}
    fit_spell = [r for r in spell if r['cohort'] in FIT and len(r['cands']) >= 2]
    grid = {}
    for a in [0, 0.5, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 12, 15, 20, 30, 50, 100]:
        grid[a] = (sum(ratio(a)(r, r['cands'])['id'] == r['chosen'] for r in fit_spell),
                   sum(kill_then(ratio(a))(r, r['cands'])['id'] == r['chosen'] for r in fit_spell))
    a_best = max(grid, key=lambda a: grid[a][0])
    ak_best = max(grid, key=lambda a: grid[a][1])
    res['spell_grid_fit'] = {str(a): dict(ratio=v[0], kill_first=v[1], n=len(fit_spell)) for a, v in grid.items()}
    res['spell'] = {
        f'ratio a={a_best}': evaluate(f'spell max (gems+{a_best})/EHP', spell, ratio(a_best), minhp),
        f'kill-first ratio a={ak_best}': evaluate(f'spell kill-first then (gems+{ak_best})/EHP', spell,
                                                  kill_then(ratio(ak_best)), minhp),
        'max gems then min EHP': evaluate('spell max gems', spell, maxgems, minhp),
        'min EHP': evaluate('spell min EHP', spell, minhp, minhp),
        'gems differ': evaluate(f'spell ratio a={a_best}, gem counts differ', spell, ratio(a_best), minhp,
                                subset=lambda r, cs: len({e['gems'] for e in cs}) > 1),
        'gem carrier is not min EHP': evaluate(
            f'spell ratio a={a_best}, a carrier is not the min-EHP target', spell, ratio(a_best), minhp,
            subset=lambda r, cs: any(e['gems'] for e in cs) and minhp(r, cs)['gems'] < max(e['gems'] for e in cs)),
    }
    by_type = {}
    for t in sorted({r['type'] for r in spell}):
        by_type[NAMES[t]] = evaluate(f'  spell ratio {NAMES[t]}', [r for r in spell if r['type'] == t], ratio(a_best), minhp)
    res['spell_by_caster'] = by_type
    res['basic'] = {
        'min EHP': evaluate('basic min EHP', basic, minhp, minhp),
        f'ratio a={a_best}': evaluate(f'basic (gems+{a_best})/EHP', basic, ratio(a_best), minhp),
        'carrier first': evaluate('basic carriers first, min EHP', basic, gem_minhp, minhp),
        'channel first': evaluate('basic channellers first, min EHP', basic, chan_minhp, minhp),
        'mixed channel, channel first': evaluate(
            'basic channel-first, mixed channel candidates', basic, chan_minhp, minhp,
            subset=lambda r, cs: 0 < sum(e['ch'] > 0 for e in cs) < len(cs)),
        'mixed channel, min EHP': evaluate(
            'basic min EHP, mixed channel candidates', basic, minhp, minhp,
            subset=lambda r, cs: 0 < sum(e['ch'] > 0 for e in cs) < len(cs)),
    }
    cassi = [r for r in stun if r['type'] == 3]
    res['stun'] = {
        'max Strength': evaluate('Cassi stun max Strength', cassi, maxstr, minhp, stun_eligible),
        'tribute first': evaluate('Cassi stun tributers first', cassi, trib_maxstr, maxstr, stun_eligible),
        'channel first': evaluate('Cassi stun channellers first', cassi, chan_maxstr, maxstr, stun_eligible),
        'tributer present, max Strength': evaluate(
            'Cassi stun max Strength, eligible tributer present', cassi, maxstr, trib_maxstr, stun_eligible,
            subset=lambda r, cs: any(e['ch'] == 2 for e in cs)),
    }
    write(out, res)


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('out')
    main(p.parse_args().out)
