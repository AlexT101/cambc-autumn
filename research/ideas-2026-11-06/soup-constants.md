# Constant soup: untuned decision constants in ocean (2026-11-06)

A read-only scan of `bots/variants/oc-base10/src` (= `bots/ocean`) for the soup tune (`variants/oc-soup`, pool2.md).
It looks for hard-coded numbers that change what the bot decides, beyond params.h's SPSA set (oc1-oc5's names) and
pool2's soup knobs. No A/Bs or builds were run.

Most of ocean's decision numbers already sit in params.h. Outside it, the decision constants are mostly named
`constexpr`s in the .cc files, so this list is close to complete for named ones. Bare literals in decision code are rare.
The scan grepped every literal of 3 or more and every decimal in the files below, then read each hit's context.

## Porting notes (for the soup agent)

- `tunify.py` matches only `inline constexpr (float|int) NAME = V;` in params.h. Each constant in section A must
  first be moved there under a unique name, at its current value, with a check that replays are identical.
- After tunify a name becomes `const T&`, so no constexpr context may read it:
  - `unknown_camp_weight`: `static_assert(unknown_camp_weight >= recall_risk ...)` at safety.cc:2689. Drop the
    assert or keep the range at or above 0.21.
  - `fight_ally_radius`: `constexpr unsigned side = 2 * fight_ally_radius` at safety.cc:773. Make it `const`.
  - `farm.cc:13 exposure_most`: already constexpr over params. Leave it alone (no new param feeds it).
  - The `comeback::` and `fixc::` multi-declarations (`pull_c = 1.0f, pull_lam = 1.0f`): split them one per line.
    `mapcond_shrink` is a `double`: make it a float.
  - `lock_stage_steps` (already tuned) is read through `constexpr int lo = ...` at fight.cc:933. oc5 coped with this,
    so copy whatever it did.
- `rate()` caches `cycle_horizon` in a function static (camps.cc:181), and `income_prior` is computed once
  (shop.cc:283). That is fine under tunify, since the values are patched before the game starts.
- **astraeus dup**: "yes" means astraeus has the same constant at the same value (for a later port). Lines are
  oc-base10's.

## A. Hard-coded decision constants (not in params.h)

Ranges follow tune.py's defaults (half to double, fractions below 0.95, ints at least ±2), adjusted where the
semantics bound them.

| # | file:line | value | controls | SPSA range | class | prio | astraeus dup |
|---|---|---|---|---|---|---|---|
| 1 | economy/farm.cc:9 `stickiness` | 1.2 | weight multiplier on last turn's farm group (anti flip-flop). Prunes exclude that group, so any value is safe | [1.0, 1.8] | neutral | **high** | yes |
| 2 | bot_parts.h:160 `cycle_horizon` base | 100 (x max(1, side/50)) | rate()'s horizon, worth / (r (1 + r/H)): how hard farm, crew and siege values discount long cycles. Every farm choice reads it | [50, 200] float | neutral | **high** | yes |
| 3 | combat/fight.cc:8 `escape_step_value` | 210 | the value of a retreat or intercept walk in enemy HP: the bar a cast must beat to spend the walk (5 call sites in fight.cc) | [105, 420] | neutral | **high** | yes |
| 4 | combat/abilities.h:66 `cast_cost` | 40 | least worth of an enemy-hitting cast, and the strike search's per-cast cost (plan.cc:1357, 1387) | [20, 80] | neutral | **high** | yes |
| 5 | combat/self_abilities.cc:21 `chase_health` | 0.4 | dash_to_attack chases an enemy below this health fraction (and below ours) | [0.2, 0.7] | neutral | **high** | yes |
| 6 | combat/fight.cc:757 chase boost cap | 0.3 | prey chase vs a carrier played with our HP x (1 + min(cap, gem_value*bag/life_value)) (pool1 gf). The cap is not the boost>0 memo skip, so it adds no fuel | [0.1, 0.6] | neutral | **high** | no |
| 7 | combat/abilities.cc:19 `min_landing_value` | 250 | least value of a moving cast (dash landing) | [125, 500] | neutral | **high** | yes |
| 8 | bot_parts.h:35 `endgame_margin` | 20 | rounds spared on the last altar trip: forced banking (bank.cc:772) and late capture/chain refusals (capture.cc:292-483) | [8, 40] int | neutral | **high** | yes |
| 9 | combat/fight.cc:1081 deny stake floor | 40 | channel_to_deny skips a tribute when our bag at stake ≥ max(40, their gems/3) | [20, 80] int | neutral | **high** | no |
| 10 | combat/fight.cc:1081 deny stake divisor | 3 | the gems/3 above (as a share, 1/3) | share [0.17, 0.6] | neutral | low | no |
| 11 | combat/fixc.cc:62 commit sight radius | 8 | cm2's fight-instead-of-lost-retreat needs at most one visible enemy within this | [5, 11] int | neutral | **high** | no |
| 12 | economy/altar_guard.cc:150 `clear_leash` | 8 | winning-bag escorts fight enemies within this of the altar (b3w) | [5, 12] int | neutral | **high** | no |
| 13 | economy/bank.cc:1107 `safe_walk_w` | 0.5 | safer_altar: extra walk penalty (score = eta-turns - (1+w)*walk + ...) (b1) | [0.0, 1.5] | neutral | low | no |
| 14 | economy/bank.cc:1107 `safe_cover_w` | 4.0 | safer_altar: score per visible ally within 3 of the altar | [2, 8] | neutral | low | no |
| 15 | economy/bank.cc:1106 `safe_switch` | 4 | safer_altar: least score gain over the nearest altar to switch | [1, 10] int | neutral | low | no |
| 16 | economy/bank.cc:1128 cover radius | 3 | ally-to-altar distance counted as cover | [2, 5] int | neutral | low | no |
| 17 | economy/altar_guard.cc:67 pair guard power | 0.25 | Cassi & Issac's guard_power share (one death hands over both bags) | [0.1, 0.7] | neutral | low | no |
| 18 | economy/altar_guard.cc:11 `site_link` | 3 | altars within this many steps form one held site | [2, 5] int | neutral | low | no |
| 19 | combat/self_abilities.cc:19 `heal_min_share` | 0.6 | Willow heals only when the gain is at least this share of the heal (or the target is hurt) | [0.3, 0.9] | neutral | low | yes |
| 20 | combat/support.cc:369 `support_turns` | 4 | most turns in a row Prism holds a recovery or Willow a formation | [2, 8] int | neutral | low | yes |
| 21 | economy/capture.cc:73 `holder_gold_price` | 0.3 | gems per gold in the holder choice (team-shared, so allies stay consistent at any value) | [0.15, 0.6] | neutral | low | yes |
| 22 | economy/crew.cc:77 melee tank bonus | 1.5 | crew tank score multiplier for walk+attack-independent (melee) bodies | [1.0, 2.5] | neutral | low | yes |
| 23 | economy/shop.cc:276 `income_prior_gems` | 30 | prior strength (in gems) of the shop's income rates | [15, 60] | neutral | low | yes |
| 24 | economy/shop.cc:277 `prior_rounds_per_gem` | 4.5 | prior rounds alive per gem | [2.5, 8] | neutral | low | yes |
| 25 | economy/shop.cc:278 `prior_kills_per_gem` | 0.005 | prior kills per gem (Hunter's value) | [0.0025, 0.01] | neutral | low | yes |
| 26 | economy/shop.cc:279 `prior_tribute_cut` | 0.015 | prior Tribute-emblem cut turn ends per gem | [0.0075, 0.03] | neutral | low | yes |
| 27 | economy/shop.cc:329 reactive-tribute horizon floor | 20 | reactive Tribute price: cut / max(horizon, 20) | [10, 40] | neutral | low | no |
| 28 | economy/shop.cc:343 gold-spend timing | 0.5 | passive gold valued as spent halfway through the horizon | [0.25, 0.9] | neutral | low | yes |
| 29 | bot_parts.h:163 `rounds_per_gem` | 2.3 | rounds per gem of our share still to farm (camps.cc:805 gems_share, read by the shop: emblem gain, income horizon) | [1.2, 4.6] | neutral | low | yes |
| 30 | bot_parts.h:36 `endgame_slack` | 2 | rounds spared on a last-chance tribute (bank.cc:788, capture.cc:335) | [0, 5] int | neutral | low | yes |
| 31 | model/world.cc:2788 `lock_memory` | 20 | rounds an unseen altar-lock belief is kept | [10, 40] int | neutral | low | yes |
| 32 | model/safety.h:36 `unknown_camp_weight` | 0.5 | threat weight of an awake camp unwatched for 2 rounds (static_assert ≥ recall_risk) | [0.25, 0.9] | neutral | low | yes |
| 33 | model/pathing.cc:118 `pull_radius` | 30 | allies farther than this exert no path tie-break pull | [15, 45] int | neutral | low | yes |
| 34 | model/pathing.cc:119 `pull_near` | 2.0 | allies this near exert no pull | [1, 4] | neutral | low | yes |
| 35 | combat/plan.cc:1217 follow-bid keep share | 0.9 | the strike search after the goal walk keeps 0.9 of the bid's need dealt | [0.6, 0.95] | neutral | low | yes |
| 36 | combat/plan.cc:1490 unacted-ally camp share | 0.5 | camp hits on an ally yet to act count half in a step's cost | [0.25, 0.95] | neutral | low | yes |
| 37 | economy/farm.cc:1753 Monolith side power | 2 (weight *= home) | a Monolith's enemy-side discount is squared. Needs `pow(home, p-1)` | p in [1, 3] | neutral | low | yes |
| 38 | combat/support.cc:308 finish-at basics | 2 | support counts a camp member finishable at ≤ 2 basics of health | [1, 3] | neutral | low | not checked |
| 39 | economy/siege.cc:983 kite capture gate | 2 x vision_radius (16) | a returning big group is gone for only within this distance of its centre | [10, 24] int | neutral | low | not checked |
| 40 | economy/farm.cc:844 hop refusal | 2 x ability_cooldown (16) | rounds a refused crystal hop is set aside | [8, 32] int | neutral | low | yes |
| 41 | combat/fight.cc:933 lock stage band | lo + 3 | the timed lock's waiting band width beyond lock_stage_steps | [1, 5] int | neutral | low | not checked |

## B. params.h members no SPSA run (oc1-oc5) has tuned

None of these is in pool2's knob list, though cbdp, b5 and bt3 shipped them in CHANGES 441. pool2's cbg2 already
covers comeback `enemy_min`, `gap` and `gap_off`, so those are left out here.

| # | file:line | value | controls | SPSA range | class | prio | astraeus dup |
|---|---|---|---|---|---|---|---|
| 42 | params.h:202 `stun_tribute_horizon` | 10 | stun_worth prices a tributing enemy's whole bag at this many rounds of delay (abilities.cc:118); the comment says "untuned" | [5, 20] | neutral | **high** | yes (params.h:193) |
| 43 | params.h:260 `fixc::bag_ratio` | 2.0 | pack-zone outmatch ratio with a big bag at stake (guard.cc:132, min with hurt_retreat_ratio 3.34) | [1.3, 3.3] | neutral | **high** | no |
| 44 | params.h:259 `fixc::bag_big` | 100 | the bag at stake that switches to bag_ratio | [60, 160] int | neutral | **high** | no |
| 45 | params.h:265 `fixc::bush_margin` | 0.1 | a hidden bush retreat step is let off this x our health of damage | [0.0, 0.3] | neutral | **high** | no |
| 46 | params.h:264 `fixc::bush_threat` | 2 | steps beyond a ready strike's reach where the bush rank goes first | [0, 4] int | neutral | low | no |
| 47 | params.h:268 `trib_min_bag` | 100 | the least bag the reactive Tribute emblem is priced from | [60, 160] int | neutral | low | no |
| 48 | params.h:218 `altar_stand_radius` | 2 | altar guards' stand tiles within this of the altar | [1, 3] int | neutral | low | no |
| 49 | params.h:220 `altar_farmers_min` | 1 | bodies left farming while guarding | [0, 2] int | neutral | low | no |
| 50 | params.h:251 `comeback::deny_w` | 0.5 | while cooked, enemy-side groups' worth x (1 + deny_w) | [0.2, 1.0] | neutral | low | no |
| 51 | params.h:250 `comeback::pull_lam` | 1.0 | the strength of the mirror pull while cooked | [0.4, 1.0] | neutral | low | no |
| 52 | params.h:250 `comeback::pull_c` | 1.0 | the mirror-steps multiplier of the pull | [0.7, 1.5] | neutral | low | no |
| 53 | params.h:252 `comeback::bar` | 2 | while cooked, take a lost chase if we last this many turns | [1, 4] | neutral | low | no |
| 54 | params.h:253 `comeback::bar_bag` | 40 | the least carrier bag for that | [20, 80] int | neutral | low | no |
| 55 | params.h:254 `comeback::pack_radius` | 4 | allies within this count for it | [2, 6] int | neutral | low | no |
| 56 | params.h:145 `mapcond_shrink` | 0.25 | the share of oc5's map-feature shifts applied to recall_health_fraction and gold_price_scale (double: make it a float) | [0.0, 0.6] | neutral | low | no |

## C. Fuel-sensitive decision constants (decision knobs that move fuel)

| # | file:line | value | controls / why fuel moves | SPSA range | prio | astraeus dup |
|---|---|---|---|---|---|---|
| F1 | model/safety.h:34 `credible_weight` | 0.5 | unseen enemies below this weight are left out of safety (and unseen_radius, safety.cc:1832). Lower values model more unseen threats in every damage bound and step guard | [0.3, 0.8] | **high** | yes |
| F2 | model/safety.h:37 `fight_ally_radius` | 4 | allies within this join our fight sims (bot.cc:32, safety.cc:754). Larger means more fighters per simulate() | [2, 6] int | **high** | yes |
| F3 | economy/bank.cc:1106 `safe_bag` | 150 | safer_altar runs (per altar: altar_steps field + strike_eta binary search) for bags ≥ this (b1). Mild: multi-altar maps only | [100, 250] int | **high** | no |
| F4 | economy/bank.cc:1106 `safe_min_turns` | 10 | the same, by channel length | [6, 15] int | low | no |
| F5 | model/safety.cc:1832 unseen-radius slack | 1.5 | unseen_radius = reach + 1.5 - credible_weight sqrt(tiles): a wider radius means more tiles in the unseen threat sets | [0.5, 2.5] | low | yes |
| F6 | combat/abilities.h:68 `max_unseen_tiles` | 9 | unseen enemies on more tiles are not aimed at: more aim targets, more ground-cast scoring | [5, 16] int | low | not checked |

Already-tuned members that are fuel-sensitive (excluded, noted for the soup's OOF reading): `threat_radius` (recall_line's
`may_reach_within` horizon), `recall_health_fraction`, `heal_trip_fraction` and `hurt_health_fraction` (how many turns
take want_home or recall branches), `tribute_window` (tribute_safe's lookahead), `pursuit_steps`. oc5 moved
threat_radius and tribute_window up one each, and its out-of-fuel turns rose 4-6%.

## D. Fuel-increasing (excluded: they change how much is computed)

- combat/plan.cc (the strike search): `max_nodes` 12 (:197), `max_exact_queries` 6 (:195), `max_depth` 6 (:192),
  `max_foes` 8 (:21), `max_units` 14 (:185), `max_groups` 16 (:186), `max_unseen` 24 (:191), `max_mates` 6 (:193),
  `max_sets` 8 (:305).
- economy/farm.cc: `bank_reserve_pct` 60 (:1295, pool1 r1), `pack_zone_cost_bound` 3500 (:15).
- economy/bank.cc:1106 `eta_cap` 120 and the `+ 30` slack (:1125): bounds of strike_eta's search.
- model/pathing.cc:743 `cheap_guard` 15000: a measured-fuel switch (the oc5 divergence). pathing.h:18 `max_detour` 16;
  pathing.cc:1767 `wide_cap` 6 x max_detour; attempts 3 (:1627, :1714).
- model/world.cc:245 `reach_few` 6; :1370 `most` 128 / `square` 40.
- model/turn_order.cc:640 `quiet_reserve` 6000; model/enemy_reach.cc:33 `max_steps` 16; model/turn_window.cc:13
  `window_cap` 16, `slot_cap` 32, `unseen_probe` 24.
- combat/fight.cc:48 `exit_search_steps` 4 x (reach + 1); :974 lock-plan passes 3. combat/self_abilities.cc:113 `tries`
  3.
- bot.cc:145 `reveal_fuel_floor` 60000, `reveal_grow_fuel` 15000 (fuel gates on the reveal ward).
- model/safety.cc:2390 `kept` 16; safety.h:593 `max_fights` 32; safety.cc:2977 simulation reserve; guard.cc:613 `floor +
  1000 n`; util.h reserves (`end_reserve` 10000, `small_cost_estimate`, `travel_cost_estimate`).
- pool2's fuelbud knobs (`guard_reserve`, `strike_floor`, `farm_floor`, `prey_walk`) are already soup items.

## E. Excluded as rules facts or structure

- model/world.h:403-421: emblem effects, ranges, shard prices, cluster rewards. bank.cc:142 `gems_per_tribute_turn` 10.
  shop.cc:25-26 kill gold.
- fight.cc:119 `HomeWalk::max_walk` 6: recall 5 + arrival. home.cc:40 `2 * gap`: there and back. bot.cc:166 the dash
  spread: cooldown 8.
- turn_order.cc:23-27 and params `turn_*`: rank codes fixed modulo 15 by static_assert, as is `unacted_share`.
  idle_priority.h codes; comms.cc bit widths and `camp_slack` 16.
- guard.cc:42-43 `pack_radius` (= max_reach - 1) and `pack_members`: geometry and array bounds.
- draft/: draft6's fitted F92 model, map features and fallback tables. Retune them through draftlab, not SPSA.
  self_abilities.h's learned emblem arms belong with the draft too.
- Float-rounding slacks (1.0001f, 0.01f, 1e-3f) and fallback defaults (camps.cc:626's 0.5 for unreachable sides).

## Counts

- Neutral: 56 (41 hard-coded in A, 15 params.h members in B); 14 high priority.
- Fuel-sensitive: 6 (F1-F6).
- Fuel-increasing: about 35 constants (section D), excluded.

**Top 10 high-priority neutral:** farm `stickiness`, `cycle_horizon` base, `escape_step_value`, `cast_cost`,
`stun_tribute_horizon`, `chase_health`, `min_landing_value`, `endgame_margin`, `fixc::bag_ratio` (with `bag_big`), and
the chase boost cap 0.3. Next in line: `fixc::bush_margin`, `clear_leash`, the deny stake floor 40 and the fixc_commit
radius 8.
