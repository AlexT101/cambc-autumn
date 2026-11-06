# Pooled level changes, round 2 (ocean, 2026-11-06)

Round 1 (pool.md) pooled the 50.1-50.8% tier and shipped as CHANGES 441 (`variants/oc-base10`, +3.3 held out). This
round repeats it one tier down: changes that read about 49.9-50.1% and were cut. A second, mildly negative tier
(non-significant losses, roughly 49.0+) goes only into the constant soup (`variants/oc-soup`) for a joint tune.

Base: `variants/oc-base10` (= `bots/ocean`).

## 1. Candidates

Bar for the plain arms (level tier, **L**): best held-out or largest reading ≥ 49.9%, no reading lost significantly,
no loss on varied or the panel, not in oc-base10. Soup-only tier (**M**): best reading roughly ≥ 49.0, a
non-significant loss, nothing broken. Where two candidates are alternatives for the same code, the better-measured
one is taken. The obese-bag line is excluded (another agent is retesting it).

Readings are own drafts against the source's base (oc-retest-clean unless noted); "2x" = 200k fuel a turn.

| # | Tag | Tier | Source (knobs) | What it does | Readings |
|---|---|---|---|---|---|
| 1 | np | L | fixc-dev (`nuke_price` 0.6) | the strike search prices an end tile in a single foe's lethal nuke zone at 0.6 x (health + life + bag) | real 50.1, 2x 49.9 (20,480 each) |
| 2 | ngd | L | fixc-dev (`nuke_guard`) | step and work guards refuse steps into a nuke zone from outside | real 50.1, 2x 49.9; OOF +4% |
| 3 | o05 | L | fixc-dev (`open_ratio` 0.5) | no opening hit while our EHP within 8 is under half theirs | 2x 50.1, real 49.6 |
| 4 | kr0h | L | kill-dev (`race_on`, Y 0, no ally needed) | a big-bag carrier refuses the killing blow when the race model says the kill delays our win | 50.0 and 50.0 (2x, two full suites); OOF +40-54% |
| 5 | c1r | L | kill-dev (`c1` 3) | a 5+ turn channel is cancelled only for a kill within the restart-cost window | 49.9 (2x, 20,480) |
| 6 | c3w | L | kill-dev (`c3_turns` 20, no switch) | a 20+ turn channel starts only with no enemy in sight (the body waits) | 49.9 (2x, 20,480) |
| 7 | c4p | L | kill-dev (`c4_cap` 300, `c4_round` 1200) | Prism keeps no bag of 300+ from round 1200 | 49.9 (2x, 20,480) |
| 8 | cbi | L | comeback-dev (items bit, fight x2, econ x0.5) | cooked: fight emblems x2, economy emblems x0.5, no learned-emblem override | deny+items 50.3, deny+snipe+items 50.4 held out (2x) |
| 9 | cbg2 | L | comeback-dev (`enemy_min` 200, `gap` 75, `gap_off` 50) | the cook trigger earlier (base: 400 / 150 / 100) | deny+items at g2 50.6 of 20,480 (2x); g3 51.6 early H1 |
| 10 | fin | L | fixm-dev (`finish_wait` 20) | a winning bag that has waited 20 rounds at an altar starts its tribute when unhurt and not threatened | real 50.0, 2x 50.0, 10M 50.0 |
| 11 | escw | L | fixm-dev (`escort_multi`) | multi-altar maps escort a winning bag at the home altar too | real 49.9, 2x 49.5 |
| 12 | b2w | L | fixm-dev (`cover_n` 2) | while escorting, the first 2 guards stand as the carrier's cover (within 5) | 50.1 (2,005, H1 no-harm), 2x 49.9 |
| 13 | rbank | M† | fixm-dev (`race_bank_k` 100) | Prism stops holding its bag for Focus once the race model's danger(100) holds | 2x 50.0 (2,097, no-harm H1) |
| 14 | elv | L | fixm-dev (`ender_leave`) | a game-ender stop with no hard stop and no kill in 3 hits leaves the channel alone (iw2 = iw + this) | 2x 50.1 (H0) |
| 15 | gwin | L | lock-dev (perma-lock, gate winbank) | one-site maps: keep our lock while their tributed + bags would win | real 49.9 (20,480), 2x 50.0, 10M 50.2; ladder vs astraeus 53.5 (base 56.2, ±6) |
| 16 | sp4 | L | fb-dev (`stale_rounds` 8, 0.8, sp3 notes) | the farm loop prunes groups recently far below the best | 49.9 of 20,480 |
| 17 | lp90 | L | fb-dev (`loop_pct` 90) | non-banking loops keep 90% of their walk reserve | with r1: 50.3 (= r1's 50.3); loop_pct 80 49.9 |
| 18 | shr | L | astport-dev (`shield_ready`) | camp damage with the shield's cooldown after the trip (astraeus 410) | 50.2 (3,599, H0) |
| 19 | rfin | L | astport-dev (`reset_finish`) | Willow's camp finish needs a ready reset | 49.9 (1,498, H0) |
| 20 | dct | L | astport-dev (`dead_camp_tiles`) | support and heal stations on dead camp tiles | 49.9 (2,515, H0) |
| 21 | lvh | L | astport-dev (`leaving_holders`) | capture_taken leaves out allies that go before payout | 49.9 (1,800, H0) |
| 22 | lka | L | astport-dev (`lock_arrival`) | melee arrival hit on a lock; tribute after a breaking hit | 50.1 (7,912, H0) |
| 23 | drs | L | astport-dev (`draft_reserve`) | draft usable health by recall_health_fraction (412) | 49.9 (1,640, H0) |
| 24 | bnv | L | astport-dev (`beaten_near_via`) | beaten_near's banking bound by the recall out | 50.1 (1,678, H0) |
| 25 | rlag | L | gemfight3-dev, on oc-base3 (`recall_lag` 1) | a visible enemy in a real recall joins fight sims a turn late | 50.1, 49.9 (confirm), 49.9 (base3) |
| 26 | ramp | L | gemfight3-dev (`bag_ramp_from` 10, power 0) | our bag in the strike search's death cost, a step at 10 | 50.1, 49.9 (confirm), 49.9 (base3) |
| 27 | obw | L | gemfight3-dev (`own_bag_weight` 1) | our bag in the death cost, weight 1 | 49.9, 49.8 (base3) |
| 28 | rint | L | gemfight3-dev (`recall_intercept`, factor 0.5) | recall interception valued by the bag | 49.9, 49.9 |
| 29 | bls | L | gemfight3-dev (`bag_line_slope` -0.15) | drawn_home's recall line scaled down by our bag | 49.9 |
| 30 | ssp | L | retest-dev, on oc-base4 (`spawn_spells` 1) | spells from spawn on mend turns | 49.9 (retest); 50.6 / 49.3 / 50.2 pooled (spawncamp) |
| 31 | w1 | L | oc-dev, on oc-r0 (`route::w1` 0) | an empty-handed walk to spawn for the turn-end heal when it beats the other routes | 50.19, 49.92 confirm; +0.26 on R1+F1 |
| 32 | ac | L | ac-dev, on oc-combo2 (`area::guard`, radius 4, reach 6) | a free ally guards an ally's hold when an enemy nears | 49.96 of 20,480 |
| 33 | ne | M | fixc-dev (`nuke_escape`) | turn-start walk out of every nuke zone | real 50.0, 2x 49.4 |
| 34 | lwar | M | fixm-dev (`lock_break`, `lock_seek` 8) | break enemy locks within 8 | real 49.6, 2x 49.5, 10M 49.2 |
| 35 | sfun | M | fixm-dev (`funnel_power` 2, `sep_chain_bag` 45) | separate-altar funnel | real 49.8, 2x 48.8 (5,120) |
| 36 | p2 | M* | fb-dev (`prey_after_dup`, `prey_walk` 8000) | prey's check after the repeat-fight skip; 8k for the walk | 50.1 (10,542, H0) |
| 37 | g1 | M* | fb-dev (`guard_reserve` 12000) | the step guard keeps 12k, not 20k | 49.9 (8,229, H0) |
| 38 | sfl | M* | fb-dev (`strike_floor` 40000) | anytime strike search below 40k left | 50.1 (9,933, H0), OOF -8% |
| 39 | f20 | M | fb-dev (`farm_floor` 20000) | farm_turn below 20k keeps last turn's group | 49.7 (4,357, H0) |
| 40 | sfc | M | astport-dev (`shop_forecast`) | the learned emblem in every forecast | 49.7 (9,770, H0) |
| 41 | pk | M | astport-dev (`price_keep`) | prices keep their emblem until the share moves a tenth | 49.7 (7,660, H0) |
| 42 | sff | M | astport-dev (`spawn_field_first`) | the spawn field on turn 1 | 49.1 (3,132, H0) |
| 43 | sl | M | proteus-dev (`seats`, `ledger`) | proteus's seat ledger in comms | alone 49.5 (2x), 49.6 (10M); with windows 50.7 vs 50.8 (2x) |
| 44 | cah | M | proteus-dev (`cheap_after_heavy`, 70k) | after a heavy turn, next round's order read as the base does | real 49.7 (40,960) vs wn's 50.3 |
| 45 | ah85 | - | lock-dev round 2 (all hands from round 1850) | the whole team holds the site late while ahead | 49.8-50.0 (one-site screens, 3,204); dropped: its plock settings conflict with gwin's |
| 46 | amb | M | comeback-dev (`ambush` bit) | cooked: the bush ambush gambit | in the comeback z-tiers, 47.0-49.5 with hunt / hop; soup only, as the coordinator asked (to take draftcond's precomputed map facts later) |
| 47 | hop | M | comeback-dev (`hop` bit) | cooked: the crystal hop gambit | as amb |

\* p2, g1 and sfl are level alone, but their combination (fuelbud c1 = p2 + g1 + sfl) lost: 49.3 (48.6-49.9) of
20,480. They go to the soup only. The same check for fixc: n1 (np + ngd + ne) read 49.3 (48.6-50.0) at 2x, but ng
(ngd + ne) read the same and ne alone 49.4, while np and ngd alone read 49.9: the escape is the weak part, so np and
ngd stay in the plain arms and ne goes to the soup.

† rbank's original test was a no-op (the port found its branch could not fire as tested), so its 50.0 measured
nothing; it goes to the soup only.

On the 100M bench (16 default games, 52 wide) `finish_wait` and `ender_leave` never fire, nor do `draft_reserve`
and `beaten_near_via`; they are kept as ported.

**Excluded:**
- *Lost significantly:* fixc b1-b4/b6 (bag_bank), cm1, o15 / or1 (49.2); kill C1 strict (48.8), C2 (49.1, 49.2), C4
  any-risk to 30 (49.3, 48.6-50.0); comeback hunt, ambush, crystal hop and hunters' items (47.0-49.5 and comeback
  rate down 3-6 points); fuelbud r1b, s2, light loop, watchdog; gemfight `bag_line_slope` +0.25 / +0.5; farm-route R4
  on R1+F1 (49.41, 48.85-49.97), B1, R3; bankfin3 (level, but -0.21 against fish_farm, CI -0.40 to -0.03).
- *Alternatives:* kill's fixed / dynamic / routing / funnel refusals (kr0h is the measured one); T2b / T3b (T1b is in
  base10); fixc o1 / o075 (o05), bt1 / bt2 / bt4 (bt3 is in base10), b7 / b8 (b5 is in base10); comeback z-tier1-3
  (a different mask per level; items + the trigger are the measured parts), g3 (g2 has the full run); gemfight's
  other settings; astport loop_reserve (an alternative to r1, in base10); perma-lock g2b500 (gwin), n8l50 (lost
  49.7 / 48.2 at 10M); area control a2-a4 (a1); interrupt variants iw / iw12 / dw (iw8 is in base10).
- *No-op or superseded:* fixc ry (cannot fire); value round 2's ally_gold_weight and retest tw / w20 / e1p1 (code
  rewritten by CHANGES 419-420); draftfeat (draft6 drafts now); oc-tuned3 (oc4).
- *Not ocean:* astraeus CHANGES 439 / 440 fix 1, campdmg2 (astraeus only).
- *Obese bags* (V0 / V1): another agent's retest.
- *Lost on older bases and not retried:* invade B2 (50.0 confirm on oc-base1, later variants lost), the ungated
  mirror pull, spawncamp home bonus, cooked mirror (comebacks fall).

## 2. Arms

One tree, `variants/oc-pool2-dev`: oc-pool1t (= oc-base10) plus four ported change sets (fixm/perma-lock,
fuelbud/astport, gemfight/spawn spells/route, area control), each member behind a constant in a `SOUP` block at the
top of `params.h` that the knobs read. The arms differ only in that block (`tmp-offload/pool2/mkarm.py`).

| Arm | Members | Block |
|---|---|---|
| `variants/oc-pool2-dev` | none | literals at base10 values |
| `variants/oc-pool2-1` | the 31 L rows | `namespace pool2` flags; each soup constant `pool2::tag ? tested : base` |
| `variants/oc-pool2-2` | the better half (≥ 50.0): np ngd o05 kr0h cbi cbg2 fin b2w elv shr lka bnv lp90 ssp | as pool2-1 |
| `variants/oc-soup` | all 46 (L + M) | literals at the tested settings, for `tunify.py` |

**Identity (100M, fast runner):** oc-pool2-dev vs oc-base10 identical 16/16 default, 52/52 wide (+0.3% fuel).
oc-soup with all 46 off and tunified (110 params) identical 16/16 and 52/52 (+1.4% fuel).

## 3. The soup

111 tunables: 87 soup rows plus 24 oc5 constants recentred on their current values (half to double, fractions to
0.95, ints at least +-2). The soup rows are:
- R1: the round-1 members already in base10.
- const: the scan constants from soup-constants.md.
- L / M: this round's members.

Gates are floats, on above 0.5. The L gates start at 0.6 (on), and the M gates at 0.4: off, but one SPSA perturbation
from on. Every R1, const and oc5 row starts at its base10 value, and the L rows at their tested settings.
- Config: `/home/ubuntu/tmp-offload/pool2/soup-config.json` (`params` in tune.py's `[lo, hi, kind]` form, plus
  `start` and `base10`).
- Names: `soup_table.TUNE`.
- `soup_c4p_cap` is 0 in base10 (off). In the soup, the member is disabled at `soup_c4p_round` 2001.
- `safety.cc`'s `static_assert(hit_given_reach >= recall_risk)` is gone, because both are now tunable.
- The tunified build at the start point matches the constexpr build except through `cah`, which reads last turn's
  measured fuel. Tunify adds about 1.4% fuel.

The tune itself (soup2, run by another agent from the 22:56 oc-soup) compiles out the M tier, kr0h, rbank, amb and
hop as base10 literals, and keeps the 30 other L members (92 params; start 50.4 at real fuel).

**Port fixes found by the soup's start (2x, `pool2-bis` = fresh-610000..610003, 2,048 games each):**

| Test | Win % |
|---|---|
| Soup start, all 46 members on | 33.7 |
| pool2-1 + every M member | 32.8 |

Adding one M member at a time to pool2-1:

| Member | Win % |
|---|---|
| ne | 51.0 |
| sfc | 50.7 |
| sl | 50.2 |
| p2, g1, sfl, f20, sff | 50.0 (no-ops at 2x) |
| lwar | 49.2 |
| sfun | 48.9 |
| pk | 48.7 |
| cah | 48.3 |
| amb | 43.5 |
| hop | 42.3 |
| rbank | 38.5 |

- **amb, hop: they interact with cbg2.** On base10 alone they read 49.4 and 47.8, their old numbers (48.8, 47.6). On
  cbg2 alone they read 45.8 and 43.1: cbg2's earlier cook (200 / 75) sends 3 hunters off the farms in many more
  games. They now keep their own measured trigger (`soup_gb_*`, 400 / 150 / 100), which brings them back to 48.7 and
  48.4 on cbg2.
- **rbank: broken.** On base10 alone it reads 38.7. `danger(k)` is margin < k, which holds whenever we are behind.
  Before our first tributes are projected (`never`), Prism banked every bag from round ~44 (self-play trace,
  gen-classic-61000001002). A close-race version (|margin| < k, both wins before round 2000) still reads 44.3. It is
  off in the soup and not tuned.
- With rbank off and amb/hop fixed, the soup with every M member on still read 44.0 (2x) and 43.7 (real budget,
  `pool2-diag` = fresh-610400..610409, 5,120 games): the small losses add up. With the M gates at 0.4 the start reads
  48.9 (2x, 2,048) and 48.7 (real, 5,120).

| Param | Tier / member | Range | Start | base10 | Disables at | Note |
|---|---|---|---|---|---|---|
| `soup_cb_enemy_min` | L cbg2 | 150..800 | 200 | 400 |  | cbdp: cook trigger, enemy tributed |
| `soup_cb_gap` | L cbg2 | 50..300 | 75 | 150 |  | cbdp: cook trigger, their lead |
| `soup_cb_gap_off` | L cbg2 | 25..200 | 50 | 100 |  | cbdp: cook off below this lead |
| `soup_cb_deny_w` | R1 | 0..1 | 0.5 | 0.5 | lo | cbdp: enemy-side camps x (1 + w); 0 off |
| `soup_cb_bar` | R1 | 0..4 | 2 | 2 | lo | cbdp snipe: turns we must last; 0 off |
| `soup_cb_bar_bag` | R1 | 20..100 | 40 | 40 |  | cbdp snipe: least carrier bag |
| `soup_ptw` | R1 | 0..1 | 0.6 | 0.6 | lo | ptw gate (turn windows + after_nearest); <0.5 off |
| `soup_b3w_leash` | R1 | 4..12 | 8 | 8 |  | b3w: escort clear leash |
| `soup_bt3_threat` | R1 | 0..4 | 2 | 2 | lo | bt3: bush rank under a ready strike, reach + this; 0 off |
| `soup_bt3_margin` | R1 | 0..0.3 | 0.1 | 0.1 |  | bt3: bush retreat step damage let off |
| `soup_t1b_bag` | R1 | 50..300 | 100 | 100 |  | t1b: reactive Tribute emblem from this bag |
| `soup_r1_pct` | R1 | 30..100 | 60 | 60 | hi | r1: banking loop walk reserve %; 100 off |
| `soup_b5_bag` | R1 | 50..200 | 100 | 100 |  | b5: big bag at stake |
| `soup_b5_ratio` | R1 | 1.2..3.4 | 2 | 2 | hi (away from home) | b5: outmatch ratio (>= hurt_retreat_ratio: off away from home) |
| `soup_b1_bag` | R1 | 80..300 | 150 | 150 |  | b1: safe altar from this bag |
| `soup_b1_turns` | R1 | 5..20 | 10 | 10 |  | b1: and this channel length |
| `soup_cm2` | R1 | 0..1 | 0.6 | 0.6 | lo | cm2 gate (strict commit); <0.5 off |
| `soup_cm2_radius` | R1 | 4..12 | 8 | 8 |  | cm2: at most one visible enemy within this |
| `soup_gf_slope` | R1 | 0..2 | 1 | 1 | lo | gf: chase boost per bag value; 0 off |
| `soup_gf_cap` | R1 | 0.1..0.6 | 0.3 | 0.3 |  | gf: chase boost cap |
| `soup_c1_nodes` | R1 | 8..24 | 12 | 12 | hi (pre-c1) | c1: strike search nodes (24 = before c1) |
| `soup_c1_queries` | R1 | 4..10 | 6 | 6 | hi (pre-c1) | c1: exact reach queries (10 = before c1) |
| `soup_stickiness` | const | 1..1.8 | 1.2 | 1.2 |  | farm: last turn's group weight |
| `soup_cycle_base` | const | 50..200 | 100 | 100 |  | rate(): cycle horizon base |
| `soup_escape_step_value` | const | 105..420 | 210 | 210 |  | fight: a retreat walk's value |
| `soup_cast_cost` | const | 20..80 | 40 | 40 |  | least worth of a hitting cast |
| `soup_chase_health` | const | 0.2..0.7 | 0.4 | 0.4 |  | dash_to_attack chase health |
| `soup_min_landing_value` | const | 125..500 | 250 | 250 |  | least value of a dash landing |
| `soup_endgame_margin` | const | 8..40 | 20 | 20 |  | rounds spared on the last altar trip |
| `soup_deny_stake` | const | 20..80 | 40 | 40 |  | channel_to_deny's bag-at-stake floor |
| `stun_tribute_horizon` | const | 5..20 | 10 | 10 |  | stun_worth's tribute delay (already params.h) |
| `mapcond_q` | const | 0..0.6 | 0.25 | 0.25 |  | mapcond-q shrink (was double mapcond_shrink) |
| `soup_recall_health_fraction` | const | 0.1577..0.631 | 0.315491 | 0.315491 |  | oc5 recall_health_fraction (map-shifted at turn 1) |
| `soup_gold_price_scale` | const | 0.6605..2.642 | 1.32098 | 1.32098 |  | oc5 gold_price_scale (map-shifted at turn 1) |
| `soup_np` | L np | 0..1.2 | 0.6 | 0 | lo | nuke zone price; 0 off |
| `soup_ngd` | L ngd | 0..1 | 0.6 | 0 | lo | nuke guard gate |
| `soup_o05` | L o05 | 0..1 | 0.5 | 0 | lo | open_ratio; 0 off |
| `soup_kr0h` | L kr0h | 0..1 | 0.6 | 0 | lo | race kill refusal gate |
| `soup_kr0h_y` | L kr0h | 0..40 | 0 | 0 | (gate) | race refusal margin (rounds) |
| `soup_c1r` | L c1r | 0..1 | 0.6 | 0 | lo | C1 restart-cost cancel gate |
| `soup_c3w` | L c3w | 0..1 | 0.6 | 0 | lo | C3 unseen start gate (wait) |
| `soup_c3w_turns` | L c3w | 10..40 | 20 | 20 | (gate) | C3: least channel turns |
| `soup_c4p_cap` | L c4p | 150..600 | 300 | 0 | (round hi) | C4 Prism bag cap (0 = off in the off build) |
| `soup_c4p_round` | L c4p | 800..2001 | 1200 | 2000 |  | C4 from this round; 2001 off |
| `soup_cbi_fight` | L cbi | 1..3 | 2 | 1 | lo | cooked items: fight emblems x; <= 1 off |
| `soup_cbi_econ` | L cbi | 0.25..1 | 0.5 | 1 | (fight lo) | cooked items: economy emblems x |
| `soup_fin` | L fin | 0..40 | 20 | 0 | lo | finish_wait rounds; 0 off |
| `soup_escw` | L escw | 0..1 | 0.6 | 0 | lo | escort_multi gate |
| `soup_b2w` | L b2w | 0..3 | 2 | 0 | lo | cover_n; 0 off |
| `soup_elv` | L elv | 0..1 | 0.6 | 0 | lo | ender_leave gate |
| `soup_gwin` | L gwin | 0..1 | 0.6 | 0 | lo | perma-lock gwin gate |
| `soup_sp4_rounds` | L sp4 | 0..16 | 8 | 0 | lo | stale prune rounds; 0 off |
| `soup_sp4_margin` | L sp4 | 0.5..0.95 | 0.8 | 0.7 | (gate) | stale prune margin |
| `soup_lp` | L lp90 | 60..100 | 90 | 100 | hi | non-banking loop reserve %; 100 off |
| `soup_shr` | L shr | 0..1 | 0.6 | 0 | lo | astport shield_ready |
| `soup_rfin` | L rfin | 0..1 | 0.6 | 0 | lo | astport reset_finish |
| `soup_dct` | L dct | 0..1 | 0.6 | 0 | lo | astport dead_camp_tiles |
| `soup_lvh` | L lvh | 0..1 | 0.6 | 0 | lo | astport leaving_holders |
| `soup_lka` | L lka | 0..1 | 0.6 | 0 | lo | astport lock_arrival |
| `soup_drs` | L drs | 0..1 | 0.6 | 0 | lo | astport draft_reserve |
| `soup_bnv` | L bnv | 0..1 | 0.6 | 0 | lo | astport beaten_near_via |
| `soup_rlag` | L rlag | 0..2 | 1 | 0 | lo | gemfight recall_lag; 0 off |
| `soup_ramp_from` | L ramp | 0..30 | 10 | 0 | lo | gemfight bag_ramp_from (power 0); 0 off |
| `soup_obw` | L obw | 0..2 | 1 | 0 | lo | gemfight own_bag_weight; 0 off |
| `soup_rint` | L rint | 0..1 | 0.6 | 0 | lo | gemfight recall_intercept gate |
| `soup_rint_factor` | L rint | 0..1 | 0.5 | 0.5 | (gate) | recall_gem_factor when on |
| `soup_bls` | L bls | -0.3..0 | -0.15 | 0 | hi | gemfight bag_line_slope (cap 0.3); 0 off |
| `soup_ssp` | L ssp | 0..1 | 0.6 | 0 | lo | spawn spells gate |
| `soup_w1` | L w1 | -1..6 | 0 | -1 | lo | route W1 margin; -1 off |
| `soup_ac` | L ac | 0..1 | 0.6 | 0 | lo | area-control hold guard gate |
| `soup_ne` | M ne | 0..1 | 0.4 | 0 | lo | nuke escape gate |
| `soup_lwar` | M lwar | 0..1 | 0.4 | 0 | lo | lock war gate (lock_seek 8) |
| `soup_sfun` | M sfun | 0..1 | 0.4 | 0 | lo | separate-altar funnel gate |
| `soup_p2` | M p2 | 0..1 | 0.4 | 0 | lo | prey after dup + 8k walk gate |
| `soup_g1` | M g1 | 0..1 | 0.4 | 0 | lo | step guard reserve 12k gate |
| `soup_sfl` | M sfl | 0..1 | 0.4 | 0 | lo | strike floor 40k gate |
| `soup_f20` | M f20 | 0..1 | 0.4 | 0 | lo | farm floor 20k gate |
| `soup_sfc` | M sfc | 0..1 | 0.4 | 0 | lo | astport shop_forecast |
| `soup_pk` | M pk | 0..1 | 0.4 | 0 | lo | astport price_keep |
| `soup_sff` | M sff | 0..1 | 0.4 | 0 | lo | astport spawn_field_first |
| `soup_sl` | M sl | 0..1 | 0.4 | 0 | lo | ptw seats + ledger |
| `soup_cah` | M cah | 0..1 | 0.4 | 0 | lo | ptw cheap_after_heavy (70k) |
| `soup_amb` | M amb | 0..1 | 0.4 | 0 | lo | cooked ambush bush gambit |
| `soup_hop` | M hop | 0..1 | 0.4 | 0 | lo | cooked crystal hop gambit |
| `soup_gb_min` | M amb | 200..800 | 400 | 400 |  | ambush / hop trigger: enemy tributed |
| `soup_gb_gap` | M amb | 75..300 | 150 | 150 |  | ambush / hop trigger: their lead |
| `soup_gb_gap_off` | M amb | 50..200 | 100 | 100 |  | ambush / hop off below this lead |
| `fight_weight` | oc5 | 0.3441..1.3764 | 0.688214 | = | | |
| `fight_camp_prior` | oc5 | 245.061..980.245 | 490.123 | = | | |
| `shop_gain_scale` | oc5 | 0.3755..1.5021 | 0.751062 | = | | |
| `heal_trip_fraction` | oc5 | 0.2681..0.95 | 0.536285 | = | | |
| `pair_hold_share` | oc5 | 0.2749..0.95 | 0.549802 | = | | |
| `life_value` | oc5 | 138.3..553.2 | 276.6 | = | | |
| `gem_value` | oc5 | 8.7607..35.0428 | 17.5214 | = | | |
| `chip_value` | oc5 | 0.1233..0.4934 | 0.246691 | = | | |
| `hurt_health_fraction` | oc5 | 0.2266..0.9065 | 0.453251 | = | | |
| `hurt_retreat_ratio` | oc5 | 1.6675..6.6701 | 3.33505 | = | | |
| `home_retreat_ratio` | oc5 | 1.087..4.3482 | 2.17409 | = | | |
| `hit_given_reach` | oc5 | 0.1169..0.4678 | 0.233893 | = | | |
| `recall_risk` | oc5 | 0.1035..0.4141 | 0.207039 | = | | |
| `reveal_mass` | oc5 | 0.1171..0.4684 | 0.234208 | = | | |
| `reveal_prior` | oc5 | 0.825..3.2998 | 1.64992 | = | | |
| `efficiency_power` | oc5 | 0..2.5 | 1.46538 | = | | |
| `pick_up_radius` | oc5 | 4..14 | 7 | = | | |
| `chain_bag_limit` | oc5 | 13..52 | 26 | = | | |
| `brake_bag` | oc5 | 10..38 | 19 | = | | |
| `threat_radius` | oc5 | 4..16 | 8 | = | | |
| `track_horizon` | oc5 | 1..6 | 3 | = | | |
| `tribute_window` | oc5 | 6..22 | 11 | = | | |
| `lock_stage_steps` | oc5 | 4..16 | 8 | = | | |
| `deny_gems` | oc5 | 56..224 | 112 | = | | |


## 4. Results

All runs are against oc-base10 with `--no-test-draft` on the fast runner.

| Arm | 2x screen (dev suite, SPRT 0.50/0.51, 20,480) | Held out, real budget (pool2-held, 20,480) | OOF turns, cand / ref (held) |
|---|---|---|---|
| pool2-1 (31 L) | 50.5 (49.8-51.2), undecided, seed 610001 | **49.1 (48.4-49.8)** | 385k / 207k |
| pool2-2 (14) | 50.6 (49.9-51.3), undecided, seed 610002 | **48.5 (47.8-49.2)** | 340k / 208k |

Neither arm passes: the small 2x gain reverses at the real budget. The fuel is mostly **kr0h's**, through the race
model (its OOF was +40-54% when measured alone). On `pool2-diag`, 5,120 games each at the real budget:

| Arm | Win % |
|---|---|
| pool2-2 | 47.8 |
| pool2-2 without kr0h | 50.1 |
| pool2-1 without kr0h | 50.3 |

Without kr0h both arms are level, not a pass. Varied, panel and LOO were not run, because no arm passed held out.

**Verdict: null.** The level tier pooled reads level-to-negative at the real budget. kr0h's refusal is worth nothing
it can pay for in fuel. Removing it leaves +0.1-0.3 (±1.4), which is not worth a confirm on its own. The soup carries
every member as a gate for the joint tune.

Suites: pool2-dev = fresh-610000..610039 (10,240 maps); pool2-held = fresh-610100..610139 (10,240); pool2-varied =
fresh-610200..610209 (`--mix varied`, 2,560, unused); pool2-panel2 = fresh-610300..610309 (2,560, unused); pool2-bis
= fresh-610000..610003 (a slice of dev, used for diagnosis); pool2-diag = fresh-610400..610409 (2,560).
