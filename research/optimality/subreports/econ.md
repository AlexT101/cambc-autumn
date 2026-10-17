# Camp economics, items and draft (econ subagent; saved by the main investigator)

Code and data in this folder (clear.cpp/exe exact DP solver; costs.py; t2*.py; siege.py; t3_numbers.py; t4*.py; t5.py;
fronts_*.json; t1_table.md, t1_groups.md, t2_threshold.md, ratio_surplus.md, t5_marginal.md). Most two-member group costs
are upper bounds (the exact 2D group DP mostly timed out).

## Summary
1. T1 exact clears: C++ DP over (position, cooldowns, sleep state, shield, member hp, damage) gives the Pareto front of
   rounds T vs damage taken D per champion vs wolf, elk, gem cluster, Monolith (exact cooldowns, stuns, Varg shield/splash,
   Ren reflection, dashes, sleep/wake). 1D ring model matched the 2D map version exactly for 5 champions. morgana's
   averaged formulas (output, min_camp_damage, spell_clear_rounds) misprice the clear cost (T + λD) by 0-68%, almost always
   too high on clears that take hits: wolf Ren +51%, Varg +39%, Tavi +27%, Stellar +25%; elk Varg +68%, Ren +67%,
   Cassi/Tavi +28%. Smith's rule (σ/hp descending) is optimal in 173/176 ladder groups (3 failures: Varg splash). No
   champion face-tanks a solo elk in one bout.
2. T3 health: camps never regenerate and an abandoned group sleeps after 2 phases, so a clear can be paused at the floor,
   healed and resumed for free. Pricing health at λ = heal-trip rounds / usable hp is exact to first order (Dinkelbach:
   max_j [r_j - ρ(τ_j + λD_j)] = 0); morgana's proration has the right form but wrong inputs: (a) the 0.35·H floor should be an
   absolute enemy-burst floor; (b) heal cost should be the marginal detour recall + d(spawn,next) - d(here,next), not recall +
   walk out (overstates λ ~1.4x); (c) `owed = damage + deficit` double-counts the deficit; (d) the face-to-face guard
   (dps·3 < recall line) and `affordable()` forbid exactly the big clears pausing makes cheap. Fixing them: modelled solo farm
   rate +15-31% for melee (Varg +14.8, Ryth +21.1, Ren +17.8, Issac +31.2), +3-6% for casters. Recall threshold: recall at an
   absolute floor h0 = burst that can reach you before you escape (Stellar ~375, C&I ~250, Ryth 200, Ren 165, two enemies
   400-600), hazard-weighted; without enemies just the hits taken leaving (σ ranged, 2σ melee).
3. Banking (EOQ): B* = ρ·sqrt(2·c_b/h) (c_b altar detour, h death hazard/round): 218/116/81/57 gems at hazard tenths
   1/3/5/7 (ρ = 0.5, c_b = 40) vs chain_bag_limit = 50. Team LP: bank size 50 -> 150 lifts team rate +18% on average (+41-53%
   on contest, stampede).
4. Ratio vs surplus: r/τ and r - ρ*τ choose different next groups in 27-43% of decisions at ρ* = 0.3 and 4-21% at 0.45;
   each differing decision loses 4-30 gems of surplus. E.g. collision: Stellar takes a lone wolf (ratio .68) over EEE (108 gems,
   .58), losing 16-22 gems; swirl: EGGWWW over EEEEGG, losing 12-28.
5. Stuns: a stun cast at turn t cancels the camp-phase t+1 attack. k staggered stunners prevent exactly k/8 of a monster's
   attacks (simulated .874/.745/.621/.478/.375 hit share for k = 1..5). Meta comp has 3 stunners: hit share .625 (.594 with
   Varg's shield), not rival's siege_hit_share .75. Level-0 meta Monolith siege: 57 rounds, 6,650 tank damage > team's 5,450 hp
   (needs rotation or a mid-siege heal); spells only from 4: 225 rounds; level-0 siege ≈ 0.33 gems/body-round (below wolf/elk).
6. T2 crews: the tank stands at 1, partners at 3 take nothing (equal distance: higher id loses, so Issac tanks for Cassi).
   Best pairs (wolf T, tank D / elk T, tank D): varg+stellar 9,60 / 17,460; varg+ryth 10,60 / 18,360; varg+ren 12,60 / 21,360;
   varg+cassi 13,60 / 23,420; ren+ryth 9,120 / 17,720; issac+cassi 15,240 / 25,1260. Varg is by far the best tank (elk crew
   25-31 champion-rounds per member vs 85-107 solo). Crew beats splitting iff walk to the next camp d < mean solo cost -
   2·T_team - λ·D_tank: elk 17-36, EE 26-93, $E 20-39, wolf 4-15 steps. Team LP: crews +0-25% (lanes +25, elkring +14).
7. T4 items: whole-emblem greedy on marginal rate = exhaustive optimum for all 9 champions tested (per-shard greedy is not safe:
   passives arrive with the 5th shard). Best: stellar jungle_f, jungle_f, monster_f (bot -10%); cassi same (bot -14%); prism
   jungle_f, power_f, monster_f (-13%); tavi power_f, power_f, monster_f (bot builds Strength, -14.9%; main_stat picks
   Strength since 10·2.2 < 5·5); varg jungle_s, power_s, monster_s (-6.4%); ryth jungle_s, dur_s, monster_s (-2.6%); ren
   jungle_s, dur_h, monster_s (-3%); issac -7.1%. Monster emblems (missing from the bot) rank 1st-2nd for almost everyone.
   Treasure beats Power only with > ~107 rounds left and never beats Jungle/Monster. Gold value ≈ 0.001·R gems per gold (R =
   rounds left) in this all-farming model. Durability's fight value not modelled.
8. T5 draft (farm-only LP: visit-rate variables for solo/crew/siege jobs, group visits ≤ 1/(respawn + 16), body time ≤ 1):
   morgana's fixed order is within 2.0% of the best composition on the ladder maps on average (ambush 3.7, collision 3.0,
   contest 6.1, eight 4.1, expanse 3.7, stampede 10.3, pilgrimage 1.9, else 0-0.5%); 132 generated maps: mean gap 0.8%, zero on
   86. A 5th pick of Tavi or Prism farms slightly better than Ren (Ren's value is in fights, not modelled). Marginal value of
   the last pick: +0.09 contest, +0.19 fragment, +0.24 stampede, +0.35-0.74 gems/round elsewhere. A per-body plan fits the
   draft: ~1M fuel (330k distance fields, 260k costs, greedy pick per round), ~470 bytes.
9. Against the procless head-to-head: the theory predicts mispricing pushes us onto zero-damage gem clusters and off
   wolves/elk, and that the right policy spends more health, recalls more and carries bigger bags: every observed sign
   matches (+53% camp damage taken, wolf 285 vs 176, elk 87 vs 43, clusters 193 vs 230, recalls 23 vs 14.5, carried
   gem-rounds 2.27x). Model sizes: bigger bags +18%, health pricing +15-30% for the melee half, crews +5-14%: roughly the
   observed +35%, not decomposed empirically. Every DP-optimal plan casts on the first legal round; casting before walking
   when a target is in reach is worth 1.45-2.6 rounds of output per cast.

## Implications (file:function -> computed replacement)
1. bot.cpp output / min_camp_damage / spell_clear_rounds / spell_output / basic_output -> exact front tables
   cost = min_k (T_k + λ·D_k) per champion × camp type × shard level (constexpr data, ~5k numbers); groups as staged
   virtual monsters + AoE-kite term.
2. farm() heal_rounds -> λ = c_h/U, c_h = marginal detour (0 when the trip also banks or shops); drop `+ deficit`.
3. recall_health_fraction / want_home / safety -> absolute hazard-weighted burst floor; recall at it and resume the camp.
4. finishing_camp -> pausing loses nothing; fix logic and comment.
5. farm() face-to-face guard and affordable() -> delete; let the priced cost decide.
6. farm() value -> surplus r - ρ̂τ with ρ̂ an EWMA of realised rate.
7. chain_bag_limit -> B* = ρ̂·sqrt(2·c_b/h(p)) with h from death_hazard.
8. cast_at_camp order in farm/spell_clear -> cast a ready damage spell before walking whenever a target is in reach.
9. main_stat / buy_shards -> per-champion emblem tables above (Tavi Focus; add Monster).
10. rival siege_hit_share -> 1 - k/8 (stunners within 4, staggered) minus shield: .594 for the meta comp.
11. Crews -> Varg tanks at range 1, partners at 3; crew only below the distance thresholds.
12. Smith sort -> keep; for Varg target the member with most live attacker neighbours.
13. Draft -> keep the order; optionally Tavi/Prism 5th on contest/stampede (+6-10% farm); write per-body assignments.

Limitations: enemies only through the floor and banking hazard; static crew formations; group costs mostly upper bounds;
steady-state LP with approximate travel; Prism's gem Focus and Willow's heal not modelled.
