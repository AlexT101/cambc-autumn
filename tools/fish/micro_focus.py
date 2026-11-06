"""Team focus fire, sequencing, stun follow-up, holding and kill securing (MICRO.md sections 1 and 6).

    python3 tools/fish/micro_focus.py OUT.json [--splits fit held seventh]

Target rules are scored on each attack's or unit cast's own before-state (the actor's view at the
moment it acts, which already shows what earlier allies did to visible enemies). The alternative
rules add one observer-derived but causal input each (micro_rows `ctx`): which enemies earlier
Fish actors hit or stunned this round, the actor's own previous targets, the enemies that hurt
Fish since the actor's last turn. Meaningful subset: two or more candidates, and the alternative
picks differently from the baseline.
"""
import argparse
import collections
import random

from micro_common import NAMES, RANGED, SPLITS, Score, Tally, by_round, cohorts, dist, ehp, write

UNIT_DMG = 2      # ability_kind::damage
CC = 4            # ability_kind::cc (unit stuns for Fish's kits)
MARCELLA = 7


def cands_of(b, rng):
    return [dict(id=e[0], x=e[1], y=e[2], hp=e[3], sh=e[4], stun=e[5], gems=e[6], type=e[7], str=e[8], maxhp=e[9])
            for e in b['en'] if dist(b['pos'], (e[1], e[2])) <= rng]


def min_ehp(cs, pref=()):
    return min(cs, key=lambda c: (c['id'] not in pref, ehp(c), c['id']))['id']


def ratio(cs, pref=()):
    return max(cs, key=lambda c: (c['id'] in pref, (c['gems'] + 8) / max(ehp(c), 1e-6), -c['id']))['id']


def actions(r):
    """(action, before-state, chosen enemy id or None) for attacks and casts on a champion's tile."""
    bs = {b['step']: b for b in r['y']['b']}
    for a in r['y']['eff']:
        b = bs.get(a['step'])
        if not b:
            continue
        tgt = next((e[0] for e in b['en'] if [e[1], e[2]] == a['to']), None)
        yield a, b, tgt


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('out')
    p.add_argument('--splits', nargs='+', default=['fit', 'held'])
    a = p.parse_args()
    cs = cohorts(a.splits)
    rng_ = random.Random(0)
    S = {}

    def sc(name):
        if name not in S:
            S[name] = Score(name)
        return S[name]

    T = Tally()
    for rnd in by_round(cs):
        rnd = [r for r in rnd]
        fish_hits = []   # (k, actor, target) basic/unit hits on champions this round so far, from the observer
        for r in rnd:
            ctx = r['ctx']
            ally_hit = {c['id'] for c in ctx['before'] if c['ally'] and c['foe'] and c['dmg'] > 0}
            ally_stun = {c['id'] for c in ctx['before'] if c['ally'] and c['foe'] and c['stun']}
            prev = set(ctx['prev'])
            hurt_me = [h['by'] for h in ctx['hurt_by'] if h['on'] == r['actor']]
            last_hurt = {hurt_me[-1]} if hurt_me else set()
            hurt_team = {h['by'] for h in ctx['hurt_by']}
            rng = 3 if r['type'] in RANGED else 1
            first_basic = True
            for act, b, tgt in actions(r):
                if tgt is None:
                    continue
                kind = 'basic' if act['kind'] == 'Attack' else ('dmg' if act['ab'] == UNIT_DMG else ('cc' if act['ab'] == CC else None))
                if kind is None:
                    continue
                cs_ = cands_of(b, rng if kind == 'basic' else 4)
                if len(cs_) < 2 or tgt not in {c['id'] for c in cs_}:
                    continue
                if kind == 'basic':
                    base = min_ehp(cs_)
                    sc('basic: min (hp+shield, id)').add(r, base, tgt)
                    for nm, pref in (('ally hit earlier this round', ally_hit), ('ally stunned earlier this round', ally_stun),
                                     ('own previous turn target', prev), ('last enemy that hurt me', last_hurt),
                                     ('any enemy that hurt Fish since my last turn', hurt_team)):
                        alt = min_ehp(cs_, pref & {c['id'] for c in cs_})
                        sc(f'basic: {nm} first, then min EHP').add(r, alt, tgt, base)
                        if alt != base:
                            sc(f'basic, alternative differs: {nm} first').add(r, alt, tgt, base)
                    st = {c['id'] for c in cs_ if c['stun'] > 0}
                    if st and len(st) < len(cs_):
                        alt = min_ehp(cs_, {c['id'] for c in cs_} - st)
                        sc('basic: unstunned first, then min EHP').add(r, alt, tgt, base)
                    # Team convergence: does a later hitter join an earlier Fish target?
                    prev_t = {x[2] for x in fish_hits if x[1] != r['actor']}
                    inter = prev_t & {c['id'] for c in cs_}
                    if inter and first_basic:
                        T.add(r, 'converge_n')
                        T.add(r, 'converge_actual', tgt in inter)
                        T.add(r, 'converge_minehp', base in inter)
                        T.add(r, 'converge_random_x1000', round(1000 * len(inter) / len(cs_)))
                        if base not in inter:
                            T.add(r, 'converge_minehp_elsewhere_n')
                            T.add(r, 'converge_minehp_elsewhere_joins', tgt in inter)
                            T.add(r, 'converge_minehp_elsewhere_random_x1000', round(1000 * len(inter) / len(cs_)))
                    first_basic = False
                elif kind == 'dmg':
                    base = ratio(cs_)
                    sc('unit damage: max (gems+8)/EHP').add(r, base, tgt)
                    for nm, pref in (('ally hit earlier this round', ally_hit), ('ally stunned earlier this round', ally_stun),
                                     ('own previous turn target', prev)):
                        alt = ratio(cs_, pref & {c['id'] for c in cs_})
                        if alt != base:
                            sc(f'unit damage, alternative differs: {nm} first').add(r, alt, tgt, base)
                elif kind == 'cc' and r['type'] == 3:
                    # Cassi's pure stun.
                    el = [c for c in cs_ if c['type'] != MARCELLA and c['stun'] <= 0]
                    if len(el) >= 2 and tgt in {c['id'] for c in el}:
                        base = max(el, key=lambda c: (c['str'], -c['id']))['id']
                        sc('Cassi stun: max Strength (eligible)').add(r, base, tgt)
                        for nm, pref in (('ally hit earlier this round', ally_hit),):
                            alt = max(el, key=lambda c: (c['id'] in pref, c['str'], -c['id']))['id']
                            if alt != base:
                                sc(f'Cassi stun, alternative differs: {nm} first').add(r, alt, tgt, base)
                        alt = min_ehp(el)
                        sc('Cassi stun: min EHP (eligible)').add(r, alt, tgt, base)
                        # Sequencing: an enemy yet to act this round loses this round's turn.
                        later = set(r['order'][r['k'] + 1:])
                        yet = {c['id'] for c in el if c['id'] in later}
                        if yet and len(yet) < len(el):
                            alt = max(el, key=lambda c: (c['id'] in yet, c['str'], -c['id']))['id']
                            sc('Cassi stun: yet-to-act enemies first, then max Strength (mixed)').add(r, alt, tgt, base)
                            T.add(r, 'cassi_stun_mixed_n')
                            T.add(r, 'cassi_stun_mixed_chose_yet_to_act', tgt in yet)
                            T.add(r, 'cassi_stun_mixed_maxstr_yet_to_act', base in yet)
                            T.add(r, 'cassi_stun_mixed_random_x1000', round(1000 * len(yet) / len(el)))
            for act in r['y']['eff']:
                for c in act['champs']:
                    if c['foe'] and (c['dmg'] > 0 or c['stun']):
                        fish_hits.append((r['k'], r['actor'], c['id']))
        # Stun follow-up: after a Fish stun on E, later Fish basics this round with E among >=2 candidates.
        stunned_at = {}
        for r in rnd:
            for act, b, tgt in actions(r):
                if act['kind'] != 'Attack' or tgt is None:
                    continue
                cs_ = cands_of(b, 3 if r['type'] in RANGED else 1)
                ids = {c['id'] for c in cs_}
                inter = set(stunned_at) & ids   # stuns by earlier Fish actors this round
                if len(cs_) >= 2 and inter:
                    base = min_ehp(cs_)
                    T.add(r, 'stunfollow_n')
                    T.add(r, 'stunfollow_actual', tgt in inter)
                    T.add(r, 'stunfollow_minehp', base in inter)
                    T.add(r, 'stunfollow_random_x1000', round(1000 * len(inter) / len(cs_)))
            for act in r['y']['eff']:
                for c in act['champs']:
                    if c['foe'] and c['stun']:
                        stunned_at.setdefault(c['id'], r['k'])
        # Holding and kill securing: kill-capable actors this round (own start view) and who killed.
        killers = {}
        for r in rnd:
            for act in r['y']['eff']:
                for c in act['champs']:
                    if c['foe'] and c['dead']:
                        killers.setdefault(c['id'], (r['actor'], r['k'], NAMES[r['type']]))
        capable = collections.defaultdict(list)
        for r in rnd:
            if not r['done'] or r['stunned']:
                continue
            for e in r['enemies']:
                if e['mine'] >= ehp(e):
                    capable[e['id']].append(r)
        for e, rs in capable.items():
            first = rs[0]
            T.add(first, 'killable_n')
            k = killers.get(e)
            T.add(first, 'killable_died_this_round', k is not None)
            if k:
                T.add(first, 'killable_killer_is_first_capable', k[0] == first['actor'])
                if len(rs) >= 2:
                    T.add(first, 'killable2_n')
                    T.add(first, 'killable2_killer_first_capable', k[0] == first['actor'])
                    T.add(first, 'killable2_killer_other_capable', k[0] != first['actor'] and k[0] in {x['actor'] for x in rs})
            # The first capable actor: did it hit e, kill something else, or hold?
            mine = [c for act in first['y']['eff'] for c in act['champs'] if c['foe'] and (c['dmg'] > 0 or c['stun'])]
            killed_other = any(c['dead'] and c['id'] != e for c in mine)
            hit_e = any(c['id'] == e for c in mine)
            if not hit_e:
                T.add(first, 'first_capable_no_hit_on_e')
                T.add(first, 'first_capable_no_hit_on_e: killed another', killed_other)
                T.add(first, 'first_capable_no_hit_on_e: hit another', bool(mine) and not killed_other)
                T.add(first, 'first_capable_no_hit_on_e: no hit, later ally killed e', not mine and k is not None and k[0] != first['actor'])
                T.add(first, 'first_capable_no_hit_on_e: no hit, e survived', not mine and k is None)
        for e, k in killers.items():
            rr = next(r for r in rnd if r['actor'] == k[0])
            T.add(rr, ('kill_by_type', k[2]))
            ecap = [x['actor'] for x in capable.get(e, [])]
            T.add(rr, ('kill: killer had it in kill reach at its start', k[0] in ecap))
            T.add(rr, ('kill: earlier Fish actor had it in reach', any(x['k'] < k[1] for x in capable.get(e, []))))
    out = dict(scores={n: s.report() for n, s in S.items()}, tallies=T.report(), cohorts=cs)
    for s in S.values():
        print(s.line())
    for sp, c in T.report().items():
        print(sp, c)
    write(a.out, out)


if __name__ == '__main__':
    main()
