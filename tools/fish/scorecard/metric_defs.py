"""The scorecard's metric table: what each statistic of metrics.py means, how it is read from the
counters, and FISH_MODEL.md's own figure for Fish where it gives one (`ref`, for checking the Fish column).

kind: 'rate' (k/n, a proportion), 'mean' (s/n), 'median' (from a histogram).
scale: 'p' proportions, compared by Cohen's h = |2 asin sqrt(a) - 2 asin sqrt(b)|;
       'l' levels, compared by |ln(a/b)| (both on an effect-size scale: 0.2 small, 0.5 medium, 0.8 large).
core: counted in the fidelity summary and the ranked gap list; the others (per champion) are listed apart.
"""

ACTS = [('dead', 8.5), ('home', 3.1), ('tribute', 2.8), ('fight', 3.0), ('clear', 20.9), ('capture', 4.7),
        ('recall', 6.7), ('wait', 7.9), ('approach', 7.0), ('travel', 34.6), ('idle', 0.8)]
ACT_LABEL = dict(dead='dead', home='on own spawn', tribute='tribute channel or attempt', fight='an action on an enemy champion',
                 clear='hitting a camp', capture='on an empty group (capture)', recall='keeping a recall channel',
                 wait='within 2 of a respawning group', approach='walking within 3 of a living camp', travel='other walking',
                 idle='idle')
CHAMPS = ['Marcella', 'Vesper', 'Vendetta', 'HoR', 'Cassi', 'Issac', 'Willow', 'Prism', 'Ren']
PAY1K_REF = dict(Vesper=22, Vendetta=17.6, Marcella=16.7, HoR=10.4, Cassi=5.8, Issac=4.8, Willow=3.1)
SPENT_REF = dict(Vesper=3866, Marcella=2318, Vendetta=1475, HoR=790, Cassi=325, Issac=260, Willow=135)
SHARDS_REF = dict(Vesper=128, Marcella=77, Vendetta=49, HoR=26, Cassi=10.5, Issac=8.3, Willow=4.3)
EMBLEM_REF = dict(Vesper=82, Marcella=88, Vendetta=140, HoR=245, Cassi=418, Issac=414, Willow=453)
BAG_REF = dict(Marcella=33, Vendetta=36, HoR=28, Cassi=20, Issac=17, Vesper=57, Willow=14)
BUDGET_REF = dict(Marcella=dict(clear=12.0, tribute=5.7), Vesper=dict(tribute=7.0, home=5.7), Willow=dict(travel=39.9))


def M(id, section, label, kind, key, scale='p', ref=None, core=True, den=None):
    return dict(id=id, section=section, label=label, kind=kind, key=key, den=den, scale=scale, ref=ref, core=core)


def defs():
    out = []
    for a, ref in ACTS:
        out.append(M(f'budget:{a}', '6 turn budget', f'share of turns: {ACT_LABEL[a]}', 'share', f'act:all:{a}', 'p', ref / 100,
                     den='act:all'))
    for c in CHAMPS:
        for a, _ in ACTS:
            out.append(M(f'budget:{a}:{c}', '6 turn budget by champion', f'{c}: {ACT_LABEL[a]}', 'share', f'act:{c}:{a}', 'p',
                         BUDGET_REF.get(c, {}).get(a, None) and BUDGET_REF[c][a] / 100, core=False, den=f'act:{c}'))
    S = '7.1 grouping and space'
    out += [
        M('nearest_ally', S, 'nearest alive off-spawn ally, median Chebyshev tiles', 'median', 'nearest_ally', 'l', 2),
        M('ally_within4', S, 'nearest ally within 4 (off-spawn turns with another ally off spawn)', 'rate', 'ally_within4', 'p', 0.67),
        M('centroid_spread', S, 'mean Chebyshev distance of off-spawn bodies to the team centroid (rounds with 2+)', 'mean', 'centroid_spread', 'l'),
        M('pair_dist', S, 'mean pairwise Chebyshev distance of off-spawn bodies', 'mean', 'pair_dist', 'l'),
        M('team_within8', S, 'every off-spawn body within 8 of the centroid', 'rate', 'team_within8', 'p'),
        M('side_own', S, 'off-spawn turns on own half (walk-distance territory)', 'rate', 'side_own', 'p', 0.69),
        M('side_mid', S, 'off-spawn turns in the middle', 'rate', 'side_mid', 'p', 0.22),
        M('side_enemy', S, 'off-spawn turns on the enemy half', 'rate', 'side_enemy', 'p', 0.09),
        M('pay_own', S, 'payouts on own side', 'rate', 'pay_own', 'p', 0.77),
        M('pay_middle', S, 'payouts in the middle', 'rate', 'pay_middle', 'p', 0.16),
        M('pay_enemy', S, 'payouts on the enemy side', 'rate', 'pay_enemy', 'p', 0.07),
    ]
    S = '7.1/7.5 farming'
    out += [
        M('pay1k', S, 'payouts per 1,000 rounds per champion-game, median', 'median', 'pay1k:all', 'l'),
        M('pay1k_mean', S, 'payouts per 1,000 rounds per champion-game, mean', 'mean', 'pay1k_mean:all', 'l'),
        M('pay_single', S, 'payouts with a single recipient', 'rate', 'pay_single', 'p', 0.92),
        M('pay_groups', S, 'distinct payout groups per champion-game', 'mean', 'pay_groups:all', 'l'),
        M('solo_clear:Wolf', S, 'Fish-only Wolf-led clears done solo', 'rate', 'solo_clear:Wolf', 'p'),
        M('solo_clear:Elk', S, 'Fish-only Elk-led clears done solo', 'rate', 'solo_clear:Elk', 'p', 457 / 5598),
        M('solo_clear:Golem', S, 'Fish-only Golem clears done solo', 'rate', 'solo_clear:Golem', 'p', 5 / 345),
        M('solo_clear:Monolith', S, 'Fish-only Monolith clears done solo', 'rate', 'solo_clear:Monolith', 'p', 7 / 116),
        M('wake_alone', S, 'waker of a fully asleep group has no other body within 4 of the group', 'rate', 'wake_alone', 'p'),
        M('wake_alone:Elk', S, 'waker alone: Elk groups', 'rate', 'wake_alone:Elk', 'p', 0.51),
        M('wake_alone:Golem', S, 'waker alone: Golem groups', 'rate', 'wake_alone:Golem', 'p', 0.53),
        M('wake_alone:Wolf', S, 'waker alone: Wolf groups', 'rate', 'wake_alone:Wolf', 'p', 0.55),
    ]
    for c in CHAMPS:
        out.append(M(f'pay1k:{c}', '7.1 farming by champion', f'{c}: payouts per 1,000 rounds, median', 'median', f'pay1k:{c}', 'l',
                     PAY1K_REF.get(c), core=False))
        out.append(M(f'pay_groups:{c}', '7.1 farming by champion', f'{c}: distinct payout groups per game', 'mean', f'pay_groups:{c}', 'l',
                     core=False))
    S = '8 economy'
    out += [
        M('spent', S, 'gold spent per champion-game (engine statistics)', 'mean', 'spent:all', 'l'),
        M('shards', S, 'shards bought per champion-game', 'mean', 'shards:all', 'l'),
        M('has_emblem', S, 'champion-games with an emblem', 'rate', 'has_emblem:all', 'p'),
        M('first_emblem', S, 'round of the first emblem, median (champions with one; 10-round bins)', 'median', 'first_emblem:all', 'l'),
        M('trib_bag', S, 'gems carried at a tribute start, median', 'median', 'trib_bag:all', 'l'),
        M('tribute_start', S, 'tribute starts per free off-spawn turn', 'rate', 'tribute_start', 'p'),
        M('recall_start', S, 'recall started on free turns ending off spawn with no channel running (prepared recall)', 'rate', 'recall_start', 'p', 1.0),
        M('recall_survive', S, 'a recall started on a free turn still running after the next turn', 'rate', 'recall_survive', 'p', 0.038),
        M('keep_rate', S, 'recall kept at timer 1 (the last chance to cancel)', 'rate', 'keep_rate', 'p'),
        M('keep_rule', S, 'timer-1 keep rule agreement (capturing: h<=0.40; payout round: h<=0.63; else h<=0.63 or gold>=30)', 'rate', 'keep_rule', 'p', 0.906),
        M('home_gate', S, 'home gate (h<=0.63 or gold>=30) holds at a completed recall', 'rate', 'home_gate', 'p', 0.986),
        M('home_reason_hurt', S, 'completed recalls with h<=0.63', 'rate', 'home_reason_hurt', 'p', 2906 / 5643),
    ]
    for c in CHAMPS:
        S2 = '8 economy by champion'
        out += [M(f'spent:{c}', S2, f'{c}: gold spent per game', 'mean', f'spent:{c}', 'l', SPENT_REF.get(c), core=False),
                M(f'shards:{c}', S2, f'{c}: shards per game', 'mean', f'shards:{c}', 'l', SHARDS_REF.get(c), core=False),
                M(f'first_emblem:{c}', S2, f'{c}: first emblem round, median', 'median', f'first_emblem:{c}', 'l', EMBLEM_REF.get(c), core=False),
                M(f'trib_bag:{c}', S2, f'{c}: tributed bag, median', 'median', f'trib_bag:{c}', 'l', BAG_REF.get(c), core=False)]
    S = '5 priority'
    out += [
        M('prio_rank_ok', S, "alive turns whose priority has Fish's rank residue ((-p) mod (N+1) = base-health rank)", 'rate', 'prio_rank_ok', 'p', 1.0),
        M('prio_mode_agree', S, 'priority mode agrees with the selector (dead / late / contact / quiet), alive unstunned', 'rate', 'prio_mode_agree', 'p'),
        M('prio_quiet_exact', S, 'quiet-predicted turns with the exact quiet value -rank-(N+1)*band', 'rate', 'prio_quiet_exact', 'p'),
        M('prio_dead_ok', S, 'dead turns with the dead level (L = -1)', 'rate', 'prio_dead_ok', 'p', 1.0),
        M('prio_write_repeat', S, 'priority writes that repeat the current value', 'rate', 'prio_write_repeat', 'p', 0.0),
    ]
    for md in ('quiet', 'late', 'contact', 'early', 'other', 'unset'):
        out.append(M(f'prio_mode:{md}', S, f'alive turns in priority mode {md}', 'hshare', f'prio_mode@{md}', 'p', den='prio_mode'))
    S = '9-10 combat'
    out += [
        M('kills', S, 'champion kills per game (bodies)', 'mean', 'kills', 'l'),
        M('deaths', S, 'deaths per game (bodies; Cassi and Issac die together)', 'mean', 'deaths', 'l'),
        M('camp_deaths', S, 'deaths to camps per game', 'mean', 'camp_deaths', 'l'),
        M('camp_death_share', S, 'share of deaths dealt by camps', 'rate', 'camp_death_share', 'p'),
        M('enemy_in_sight', S, 'alive turns with an enemy champion in sight at turn start', 'rate', 'enemy_in_sight', 'p'),
        M('contact_hit', S, 'free turns with an enemy within 3 that hit an enemy champion', 'rate', 'contact_hit', 'p'),
        M('engage_rule', S, 'positioning rule agreement (10.1: kill available, or h>0.49 and danger<=0.28)', 'rate', 'engage_rule', 'p', 0.736),
        M('engage_rule:m2', S, 'positioning rule, melee at 2', 'rate', 'engage_rule:m2', 'p', 0.735),
        M('engage_rule:m1', S, 'positioning rule, melee adjacent', 'rate', 'engage_rule:m1', 'p', 0.742),
        M('engage_rule:r', S, 'positioning rule, ranged within 3', 'rate', 'engage_rule:r', 'p', 0.729),
        M('engage_rate:m2', S, 'engages: melee at 2 (ends adjacent or spell-hits)', 'rate', 'engage_rate:m2', 'p'),
        M('engage_rate:m1', S, 'engages: melee adjacent (stays adjacent)', 'rate', 'engage_rate:m1', 'p'),
        M('engage_rate:r', S, 'engages: ranged within 3 (does not back off)', 'rate', 'engage_rate:r', 'p'),
        M('kill_override', S, 'engages when a kill is available from an engage tile', 'rate', 'kill_override', 'p', 0.987),
        M('chase_rule', S, 'chase rule agreement (10.3)', 'rate', 'chase_rule', 'p', 0.734),
        M('chase_rate', S, 'chases last turn\'s target, now nearest and out of basic range', 'rate', 'chase_rate', 'p', 0.612),
        M('basic_minehp', S, 'basic attack target = min EHP (2+ enemy champions in range)', 'rate', 'basic_minehp', 'p', 0.936),
        M('basic_champ_first', S, 'basic attacks hit a champion when one is in range', 'rate', 'basic_champ_first', 'p', 0.999),
        M('reset_use', S, 'melee reset after a surviving basic, cast unused', 'rate', 'reset_use', 'p', 0.946),
        M('spell_when_still', S, 'exclusive damage spell cast when standing, ready, cast unused', 'rate', 'spell_when_still', 'p', 0.954),
        M('stand_to_cast', S, 'stands still when its exclusive damage spell is ready with an enemy within 4', 'rate', 'stand_to_cast', 'p'),
        M('hor_shield_rule', S, 'HoR shield iff a visible unstunned enemy threatens it', 'rate', 'hor_shield_rule', 'p', 0.931),
        M('cassi_stun_on_cd', S, 'Cassi stuns when her damage spell is on cooldown', 'rate', 'cassi_stun_on_cd', 'p', 0.989),
        M('momentum', S, 'range 4-8: closes iff the previous step continued would close (9)', 'rate', 'momentum', 'p', 0.708),
        M('range_close', S, 'range 4-8 free turns that close on the nearest enemy', 'rate', 'range_close', 'p', 0.455),
        M('campcont_rule', S, 'keeps hitting camps iff nearest enemy > 4 (agreement, enemy in sight)', 'rate', 'campcont_rule', 'p', 0.808),
    ]
    for b, ref in (('none', 0.96), ('far', 0.891), ('d8', 0.853), ('d7', 0.855), ('d6', 0.791), ('d5', 0.676), ('d4', 0.448), ('d1-3', 0.182)):
        out.append(M(f'campcont:{b}', S, f'keeps hitting camps, nearest enemy {b}', 'rate', f'campcont:{b}', 'p', ref))
    S = '12 wards and bushes'
    out += [
        M('ward_rate:contact', S, 'ward placed, ward ready, enemy within 5', 'rate', 'ward_rate:contact', 'p', 0.08),
        M('ward_rate:enemy', S, 'ward placed, ward ready, enemy visible farther', 'rate', 'ward_rate:enemy', 'p', 0.05),
        M('ward_rate:none', S, 'ward placed, ward ready, no enemy visible', 'rate', 'ward_rate:none', 'p', 0.029),
        M('ward_per_turn', S, 'ward placements per alive turn', 'rate', 'ward_per_turn', 'p'),
        M('ward_bush', S, 'ward placements on a bush', 'rate', 'ward_bush', 'p', 0.788),
        M('ward_d2', S, 'ward placements at distance 2 from the placer', 'rate', 'ward_d2', 'p', 0.887),
        M('bush_tie:contact', S, 'steps onto a bush among equal-progress steps, enemy within 5', 'rate', 'bush_tie:contact', 'p', 0.731),
        M('bush_tie:enemy', S, 'steps onto a bush among equal-progress steps, enemy visible farther', 'rate', 'bush_tie:enemy', 'p', 0.783),
        M('bush_tie:none', S, 'steps onto a bush among equal-progress steps, no enemy', 'rate', 'bush_tie:none', 'p', 0.711),
    ]
    S = 'outcome'
    out += [
        M('win', S, 'win rate', 'rate', 'win', 'p', 352 / 456),
        M('final_round', S, 'round the game ends, mean', 'mean', 'final_round', 'l'),
        M('reach_2000', S, 'games reaching round 2000', 'rate', 'reach_2000', 'p', 9 / 456),
        M('gems300', S, 'tributed gems by round 300', 'mean', 'gems300', 'l'),
        M('gems600', S, 'tributed gems by round 600', 'mean', 'gems600', 'l'),
        M('gold300', S, 'team gold earned by round 300', 'mean', 'gold300', 'l'),
        M('gold600', S, 'team gold earned by round 600', 'mean', 'gold600', 'l'),
    ]
    for c in CHAMPS:
        out.append(M(f'contact_hit:{c}', '9-10 combat by champion', f'{c}: contact turns hitting', 'rate', f'contact_hit:{c}', 'p',
                     dict(Marcella=0.528, Vesper=0.674, Willow=0.483).get(c), core=False))
        out.append(M(f'enemy_in_sight:{c}', '9-10 combat by champion', f'{c}: enemy in sight', 'rate', f'enemy_in_sight:{c}', 'p',
                     dict(Marcella=0.385, Vesper=0.246, Willow=0.23).get(c), core=False))
    return out
