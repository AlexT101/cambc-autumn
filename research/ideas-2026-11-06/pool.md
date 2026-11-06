# Pooled level changes (ocean, 2026-11-06)

The user's idea: many variants of 2026-11-05/06 read slightly positive (50.1-50.8%) but not significantly, so none
shipped. Small real gains can each hide in ±1.5 points of noise; pooled into one variant, their sum may show.

Base: `bots/variants/oc-base9` (= `bots/ocean`: oc-retest-clean + CHANGES 429, 433, 434, 436, 438).

## 1. Inventory

Sources: research/EXPERIMENTS.md (the 2026-11-05/06 ocean sections), research/ideas-2026-11-05/*.md,
research/ladder-scrims-2026-11-06/*.md, research/hyperion/CHANGES.md.

Bar: a point estimate of at least 50.1% against its base (the held-out or largest reading where there are several),
no loss on varied or the panel where they were run, and not already in oc-base9.

### Candidates (11 behaviour changes, plus 2 constants changes for the constants arm)

Every source below is a knob copy (or frozen variant) of `variants/oc-retest-clean` unless noted, so the diff is
`diff -r oc-retest-clean/src <source>/src` with the knobs named set.

| # | Tag | Source (knobs) | What it does | Results (own drafts, against its base) | Diff |
|---|---|---|---|---|---|
| 1 | cbdp | `variants/oc-comeback-dp` (= oc-cb-w-dp-g4; `params::comeback` def 1 at g4 (enemy 400+, 150+ ahead): deny 0.5, mirror pull c 1, snipe) | When cooked: their side's camps x1.5, camps ranked by the nearer of the two sides' paths, and lost fights taken against carriers of 40+ while we last 2+ turns | 2x held out 50.6 (cb-c) and 50.4 (cb-d), 50.46 of 46,080 pooled; real 50.3 of 40,960; varied (2x) 50.2 of 5,120; comeback +1 point; panel not run | 11 files, +1,401 lines (economy/comeback.cc, model/race.{h,cc} new; bot.cc, fight.cc, farm.cc mirror pull, shop.cc) |
| 2 | ptw | `variants/oc-proteus-dev` (`ptw::windows`, `ptw::after_nearest`: "wn") | proteus's enemy turn windows: enemies' turn order as a window in threat and slot checks; this round's turns after ours go to the nearest unseen enemies | 2x 51.2 (ptw-a) and 50.2 (ptw-b), 50.7 of 40,960; real 50.4 and 50.2, 50.3 of 40,960; OOF +38% at the real budget; no varied or panel | 12 files, +967 lines (model/turn_window.{h,cc} new; safety, turn_order, comms, fight, plan) |
| 3 | b3w | `variants/oc-fixm-dev` (`fixm::clear_leash` 8, `clear_aggr` 1; its `site_guard` is already in oc-base9 by CHANGES 429) | Winning-bag escorts fight enemies within 8 of the held altar, walking at one chase() declined | real 50.3 of 20,480; 2x 50.3 of 5,120; paired against bots/fish +0.37 (s10), +0.10 held out; ladder 256 vs astraeus 53.1 (base 56.2, ±6) | altar_guard.cc escort branch (~40 lines), bank.cc leash |
| 4 | bt3 | `variants/oc-fixc-dev` (`fixc::bush_step` 2, `bush_threat` 2, `bush_margin` 0.1) | Path first steps and retreat ties prefer a hidden bush; under a ready enemy strike, the bush rank goes first | 2x 50.7 (fixc-dev), 50.3 held out (fixc-held, 20,480), SPRT H0 at 49.3 of 4,687 (fixc-sprt); ~50.4 pooled over 45,647 | pathing.{h,cc} route and closer_neighbours, guard.cc retreat_step (part of fixc-dev's 13 files, +448 lines) |
| 5 | t1b | `variants/oc-kill-dev` (`kill::trib_mode` 1, `trib_min_bag` 100) | Tribute emblem priced reactively from the bag we will tribute, from a 100-gem bag | real 50.3 of 14,422; 2x 50.1 of 8,569 (H0) | shop.cc pricing (part of kill-dev's 15 files, +1,098 lines; the rest is off) |
| 6 | r1 | `variants/oc-fb-r1` (`fuelbud::bank_pct` 60) | The banking farm loop's walk reserve at 60% (loop_reserve and ample's excess) | dev 50.3 of 20,480; confirm 50.4 of 20,480; varied 49.9 of 5,120 (level); panel mean +0.3, no member down | farm.cc, 2 lines |
| 7 | b5 | `variants/oc-fixc-dev` (`fixc::bag_big` 100, `bag_ratio` 2) | A bag at stake of 100+ makes the pack zone count us outmatched at ratio 2 (not 3.96): break off sooner, no banking | real 50.2 of 20,480; 2x 50.2 of 20,480 (b7, b8 the same at 2x); ladder 56.2 | guard.cc pack_members_of |
| 8 | b1 | `variants/oc-fixm-dev` (`fixm::safe_bag` 150, `safe_walk_w` 0.5, `safe_cover_w` 4) | A 150+ bag with a 10+ turn channel banks at the altar scoring best on arrival, channel, walk and cover | real 50.1 of 20,480; 2x 50.0 and 10M 50.1 of 5,120; paired vs fish -0.08 | bank.cc altar choice (~40 lines) |
| 9 | cm2 | `variants/oc-fixc-dev` (`fixc::commit_lost` 2) | A lost retreat from one pursuer, hit lately, with a turn to spare, fights instead when our attacks kill it first | 2x 50.1 of 20,480 (one suite) | fight.cc want_home |
| 10 | gf | `variants/oc-retest-dev` (on oc-base4; `retest::gf_bag_slope` 1, `gf_bag_cap` 0.3; removed from oc-retest-clean) | prey's chase against a carrier of g gems played with our health x (1 + min(0.3, gem_value g / life_value)) | oc-base3: dev 50.6, unused 50.4 and 49.8 (50.1 pooled of 40,960); oc-base4: 50.1 of 20,480; OOF +1-2% | fight.cc prey, safety.{h,cc} chase_trade boost (~20 lines) |
| 11 | c1 | `variants/oc-rt-c1` (on oc-base4; `retest::max_nodes` 12, `max_exact_queries` 6) | The strike search capped at 12 nodes and 6 exact queries (24 / 10) | oc-fuel4: 50.3 of 14,041 (H0), OOF -9%; oc-base4: 50.2 of 20,480, OOF -9% | plan.cc, 2 constants |
| T | tuned5 | `variants/oc-tuned5` (oc-base9 + SPSA oc5 constants) | 26 constants retuned (efficiency_power 1.465, hurt_retreat_ratio 3.34, ...) | 50.3 of 20,480 against oc-base9; varied 51.2 of 5,120; panel mean +0.9, none down; OOF +4% | params.h, fight.cc, capture.cc |
| M | mapcond-q | `variants/oc-mapcond2-q` (oc-base9; added by the coordinator) | `recall_health_fraction` and `gold_price_scale` shifted per map on each champion's first turn by a quarter of oc5's fitted feature slopes | 2x 50.3 (49.6-51.0) of 20,480 on 546400-546439; no varied or panel | draft.cc condition_on_map, main.cc, params.h (the two made non-constexpr) |

### Excluded

- **Alternatives to a candidate.** `oc-astport` (`astport::loop_reserve`, the after-loop reserve by class): held out 50.7,
  50.1, 50.0, 49.8 (~50.15 of 81,920), varied 50.0, panel +0.34. It replaces the same farm-loop reserve that r1 scales,
  so the two cannot both be ported as tested; r1 has the better held-out reading. Comeback's w-free-g4 (50.4) and
  y-di-g4 (50.3) are siblings of cbdp. ptw's w (50.1 real) and wsln (50.1) are subsets of wn.
- **Below 50.1 where judged, or mixed:** fixc np/np3 (50.1 real, 49.9 2x), ngd (50.1, 49.9), o05 (50.1 2x, 49.6
  real), ng, ne, n1-n2, b1-b4/b6 (lost), o1, or1, cm1, ry; fixm finish (50.0), bankfin3 (50.0; -0.21 against fish_farm),
  interrupt (in 429), lockwar, funnel, combos; perma-lock gwin (49.9), g2b500 (49.9), n8l50 and the round-2 grid; kill
  kr0h (50.0 held out), the fixed, dynamic, routing and funnel refusals, C1-C4, obese V0/V1, T3b (50.2 2x of 8,509
  only, a sibling of t1b); fuelbud's other re-allocations (≤50.1); gemfight's other knobs (recall_lag 1 50.1 then
  49.9, bag_ramp 10 50.1 then 49.9); spawncamp spells from spawn (49.9); draftfeat (49.9); altar escort sweeps
  (guards 4, leash 9: +0.3 on one-altar maps only, noise); area control (≤50.0); invade, mirror pull (lost);
  farm-route W1 (50.19 then 49.92) and R4 (50.12 then 49.83) on oc-r0; astraeus campdmg2 (50.4 then 50.0 of 81,920).
- **Superseded or stale:** retest tw and w20 (the wealth funnel they tune was removed by CHANGES 420), e1p1 (the same),
  value round 2's ally_gold_weight (50.2 of 14,123 on oc-combo2, SPRT H0; holder and funnel pricing rewritten since by
  CHANGES 419-420), oc-tuned3 (superseded by the oc4 retune).
- **Not decisions:** the race model (informational), the mapcond diagnostic (another agent's oc-mapcond2).
- **astraeus-only:** CHANGES 439 (goal field off spawn, 50.1 of 20,480 on astraeus) and 440 (49.9): not tested on ocean.
- **Fuel-only:** campaign 7's left-out pieces (424's centre fields, 426's siege memo) are not exact in ocean; fuel7's
  B1 is exact and level. Everything else exact is merged.

## 2. Arms

- **oc-pool1**: oc-base9 + all 11 candidates.
- **oc-pool2**: the robust half, at least 50.3 held out or at the real budget: cbdp, ptw, b3w, bt3, t1b, r1.
- **oc-pool1t**: oc-pool1 + oc-tuned5's constants + mapcond-q (the constants arm). mapcond-q's shift is added to
  tuned5's recall_health_fraction (0.315) and gold_price_scale (1.321), not oc-base9's.

Every member sits behind a flag in `params::pool` (params.h); each member's own knobs read it, so an ablation is a copy
with one flag false. oc-pool2 is oc-pool1 with b5, b1, cm2, gf and c1 false. `variants/oc-pool1-off` (every flag false)
replays identically to oc-base9 at 100M: 16/16 default, 52/52 wide with test drafts (+0.04% fuel).

## 3. Builds and reconciliation

Each knob copy's diff against oc-retest-clean was 3-way merged (`git merge-file`, base oc-retest-clean) onto a copy of
oc-base9; the rest were ported by hand. Script: `/home/ubuntu/tmp-offload/pool/merge.sh`.
- **cbdp, ptw, fixc (bt3, b5, cm2), kill (t1b):** whole knob copies merged, so their off knobs' code is in the tree
  (off). model/race.{h,cc} is shared by cbdp and kill and identical in both. main.cc runs `race::update` when either
  reads it (neither does at these settings). unity.cpp, params.h, bot.cc (fixc's turn-start hooks after CHANGES 429's
  `lock_plan_turn`), bank.cc and turn_order.cc took both sides.
- **ptw against CHANGES 433-436 in safety.cc:** four hand merges. ptw's window reads are kept, but base9's fuel forms
  are kept where ptw falls back: `world.my_slot_now()` / `my_slot_next()` in `next_turn_round`, `turns_before_ours` and
  `threat_strike`, and Reach's `last_slot` stays 0 without a dash (CHANGES 435).
- **b3w:** only its escort clearing is ported (altar_guard.cc `guard_turn`: leash 8 while `escorting`, then a walk
  at the enemy nearest the altar). Its `site_guard` is already in base9 by CHANGES 429. Its other fixm-dev knobs are
  not ported.
- **b1:** `safer_altar` and `strike_eta` ported into bank.cc with b1's constants, at fixm-dev's two call sites
  (`bank_gems`' aimed altar, `carry_bag`'s wait).
- **r1:** fuelbud's two lines in farm.cc, banking loops only (`loop_pct` was 100, so the other loop is unchanged).
- **gf:** retest-dev's `boost_side` and chase_trade `boost` in safety.{h,cc}, and fight.cc prey's call, with no
  lost-fight memo for a boosted chase, cbdp's `accept_lost` included.
- **c1:** plan.cc's two caps.
- **Overlaps.** cbdp, gf and cm2 all touch prey and chase decisions. cbdp's snipe accepts a lost chase against a 40+
  carrier when cooked; gf boosts the chase sim against any carrier; cm2 fights a lost retreat. They stack: a boosted
  lost chase can still be taken by snipe. b3w and b1 both act on winning or big bags at altars: b1 picks the altar,
  b3w clears around a guarded one (one-site maps only), so they rarely meet. r1 and astport's loop_reserve are
  alternatives for the same reserve, so loop_reserve is out.

## 4. Results

Own drafts (`--no-test-draft`; every arm's `test_draft` is off), fast runner native, against `variants/oc-base9`
unless noted. Logs: `/home/ubuntu/tmp-offload/pool/logs/`; summaries `replays/ab/pool-*`, `pchk-oc-pool*`, `p2-*`.
Suites (all fresh and unused before; maps/SUITES.md): `pool-dev` 570000-570039, `pool-held` 570100-570139,
`pool-held2` 570400-570439, `pool-varied` 570200-570209 (`--mix varied`), `pool-panel2` 570300-570309.

**2x screen** (`--fuel 200000`, SPRT 0.50/0.51, `pool-dev`, own seeds):

| Arm | SPRT seed | Stop | Win % (95% CI) | Full 20,480 at 2x | OOF cand / ref (full) |
|---|---|---|---|---|---|
| oc-pool1 | 518001 | H1 at 2,605 | 53.1 (51.2-55.0) | 52.5 (51.8-53.2) | 1,399 / 1,884 |
| oc-pool2 | 518002 | H1 at 3,116 | 52.8 (51.0-54.5) | 52.2 (51.5-52.9) | 1,223 / 1,798 |
| oc-pool1t | 518003 | H1 at 2,593 | 53.3 (51.4-55.2) | 52.6 (51.9-53.3) | 1,527 / 941 |

**Real budget, held out** (20,480 games each):

| Arm | Suite | Win % (95% CI) | OOF cand / ref |
|---|---|---|---|
| oc-pool1 | pool-held | **51.9 (51.2-52.6)** | 176.6k / 121.4k (+46%) |
| oc-pool2 | pool-held | 51.5 (50.9-52.2) | 186.2k / 121.9k (+53%) |
| oc-pool1t | pool-held | **53.3 (52.6-54.0)** | 190.1k / 120.3k (+58%) |
| oc-pool1t | pool-held2 | **53.3 (52.6-54.0)** | 186.7k / 117.3k (+59%) |
| oc-pool3t (pool1t less ptw, c1) | pool-held2 | 52.1 (51.4-52.8) | 142.0k / 116.7k (+22%) |
| oc-pool3t vs oc-pool1t | pool-held2 | 49.7 (49.0-50.3) | 144.4k / 188.7k |

**Varied** (`pool-varied`, real budget, 5,120 games): pool1 51.4 (50.0-52.8), pool2 51.7 (50.4-53.1), pool1t 52.2
(50.8-53.6). No loss.

**Panel** (panel-check-514510, real budget, 5,120 a member; oc-base9's rates from the oc5 section of EXPERIMENTS; second
set `pool-panel2` with oc-base9 measured alongside):

| Member | oc-base9 | oc-pool1 | diff | oc-pool1t | diff |
|---|---|---|---|---|---|
| astraeus-now-1106 | 57.0 | 59.5 | +2.5 | 59.7 | +2.7 |
| panel-proteus | 66.1 | 67.9 | +1.8 | 68.8 | +2.7 |
| panel-demeter | 68.9 | 70.8 | +1.9 | 71.5 | +2.6 |
| panel-ocean-td | 83.7 | 84.8 | +1.1 | 84.7 | +1.0 |
| baselines/v67 | 80.1 | 80.7 | +0.6 | 81.1 | +1.0 |
| mean | | | **+1.6** | | **+2.0** |
| astraeus, pool-panel2 | 58.0 | 60.3 | +2.3 | 61.2 | +3.2 |
| proteus, pool-panel2 | 66.6 | 69.7 | +3.1 | 69.5 | +2.9 |

Both pass: no member down, mean up; pooled over 10,240 games astraeus +2.4 / +3.0 and proteus +2.5 / +2.8.

**Leave-one-out at 2x** (`pool-dev`, full 20,480 each; CAND = the arm without the member, REF = the arm; below 50
means the member helps):

| Without | Win % (95% CI) | OOF cand / ref |
|---|---|---|
| t1b | **49.2 (48.5-49.9)** | 1,640 / 1,523 |
| tuned5 (from pool1t) | 49.5 (48.8-50.2) | 1,507 / 1,608 |
| ptw | 49.7 (49.0-50.3); real budget, pool-held: 50.1 (49.4-50.8), OOF 123.5k / 176.8k | 2,092 / 1,433 |
| cbdp | 49.8 (49.1-50.5); real budget, pool-held: 49.7 (49.1-50.4) | 1,474 / 1,361 |
| cm2 | 49.8 (49.1-50.5) | 1,439 / 1,502 |
| bt3 | 49.9 (49.2-50.5) | 1,589 / 1,459 |
| mapcond-q (from pool1t) | 49.9 (49.2-50.6) | 1,493 / 1,688 |
| b1, b3w, b5, gf, r1 | 50.0 each | level |
| c1 | 50.3 (49.6-51.0); real budget, pool-held: 50.3 (49.6-51.0) | 1,631 / 1,460 |

- Only t1b's removal is significant alone. The rest are each a few tenths, which is what the pool was built to test:
  the members' own point estimates sum to about +2.6 for pool1 (+0.6 more with the two constants changes), close to
  what the pool reads at the real budget (+1.9, +3.3 with the constants).
- c1's removal helps slightly at both budgets (n.s.). ptw's 2x gain is gone at the real budget, where it costs ~30% of
  the out-of-fuel turns. But dropping both (oc-pool3t) reads 1.2 lower against oc-base9 and 49.7 head to head, so
  neither is dropped on this evidence.
- The constants are worth more on top of the behaviour changes than alone (tuned5 +0.3 and mapcond-q +0.3 alone;
  pool1t over pool1 +1.4 on pool-held).

**Verdict.** oc-pool1t is significant on two unused suites (53.3% of 20,480 each, CI 52.6-54.0), level-or-better on
varied (52.2), and passes the panel (+2.0 mean, every member up). Its out-of-fuel turns are +58%, mostly ptw's. This
is the merge candidate. Not merged (the coordinator decides); no live scrims run.

## 5. Merge (2026-11-06)

Merged as CHANGES 441: `variants/oc-base10`, copied into `bots/ocean` (test_draft off).
- From `variants/oc-base10-dev`, a copy of oc-pool1t: `params::pool` is gone and every member is unconditional.
- The members' off knobs are gone with their code:
  - kill-dev: kill_rule.cc, model/race.{h,cc}, obese bags, C1-C4, the funnel, T2/T3, trib_forward;
  - proteus: the seat ledger in turn_order.cc and comms, w_* ablations, cheap_after_heavy;
  - fixc: nuke zones, bag_bank, fight openings, open_retreat, ryth_marcella;
  - comeback: the hunt, ambush, hop, items, the logger, triggers 2-3 and levels (all three levels had one mask, so the
    cook is on or off);
  - the ungated mirror pull (`params::late`), and the bush and INVD traces.
- Byte-identical to oc-pool1t at 100M: default 16/16, wide 52/52 (test drafts), total fuel -0.3%. No level check was
  needed. At the real budget the wide set diverges in 33 of 52 games (fuel gates), out-of-fuel turns 741 against 722
  (bench noise). Benches in `/home/ubuntu/tmp-offload/base10/`.

## 6. Live gate: oc-base10

`variants/oc-base10` was submitted as **v82** at 20:40 UTC: a scratch copy of the directory, identical by `diff -r`, also
built with `cambc build --release`. It was live from 20:51 and pinned from 20:52. It played the core and ext sets against
Fish and Mite, pinned to refs r1: 104 groups, 20:51-23:47, all queued while v82 was live. That gives 512 paired games
against each of v81 and v78. v82 stays active and pinned.

Paired flips (`ladder_scrims.py pair`, split by `gate-tools/pairsplit.py`; one-site means altar tiles within 3, at
most 2 tiles):

| | core: flips for v82 / v81 | pooled: v81 / v82 wins | pooled flips v82 / v81 | pooled flips v82 / v78 |
|---|---|---|---|---|
| Fish | 20 / 12 (+8) | 135 / 145 | 51 / 41 (+10) | 61 / 42 (+19) |
| Mite | 5 / 16 (-11) | 161 / 160 | 37 / 38 (-1) | 43 / 41 (+2) |
| one-site (188) | 9 / 11 (-2) | 114 / 114 | 28 / 28 (0) | 38 / 30 (+8) |
| multi-site (324) | 16 / 17 (-1) | 182 / 191 | 60 / 51 (+9) | 66 / 53 (+13) |
| total | 25 / 28 (-3) | 296 / 305 | **88 / 79 (+9, z +0.70)** | **104 / 83 (+21, z +1.54)** |

By map class against v81: Fish one-site +4, multi +6; Mite one-site -4, multi +3. Against v78: Fish +3 / +16, Mite
+5 / -3. Live, v82 wins 59.6% (305 of 512), against 57.8% for v81 and 55.5% for v78.
- Mite's core run was the one bad patch (5 / 16, and 0 / 7 on one-site). The ext maps made it up (32 / 22).

### Forensics (v82 against v81)

- **Drafts are identical in all 512 games**, ours and theirs (`gate-tools/draftflips.py 81 82`), so all 167 flips come
  from play.
  - By pick count (net for v82): Fish 3 / 4 / 5 picks +3 / -3 / +10; Mite -2 / 0 / +1.
  - By opponent composition: none beyond ±4. Fish's two 5-pick teams are +4 each, its C&I+Marc+Vesp +4. Mite's
    C&I+HoR+Tavi+Vend+Vesp is +2 over 158 games.
- **Win rates with each of our picks, v81 → v82:**
  - against Fish: Tavi 10 → 20 of 34, Vesper 79 → 94 of 156, Ren 27 → 31 of 44;
  - against Mite: Tavi 26 → 20 of 34, Varg 21 → 17 of 36, Stellar 9 → 6 of 14;
  - the rest within ±3.
- **Maps:** none beyond ±3 (01boss_battle and adgato_gemcombat3 -3; 00ribs and 02uncharted_lands +3). There is no
  cluster.
- **Out-of-fuel turns** (turn status 6, our champions; from the replays, `scratchpad/gate82/tools/oof.py`):
  - **3,952 → 5,479 (+39%)**: 8.6 → 11.9 per 1000 game rounds. Fish games +20%, Mite games +73%.
  - Up for every champion but Marcella (3.8 → 2.2 per 1000 turns): Willow 1.6 → 2.9, Prism 1.3 → 2.3, Tavi
    2.6 → 4.4, Issac 0.9 → 1.6.
  - Locally the rise was +58%, mostly ptw's.
- **OOF against flips:**
  - games where OOF rose by 10+ (79): net -4 (14 / 18);
  - rose by 1-9 (219): +2;
  - unchanged (88): -2;
  - fell (126): +13.

  The sign agrees with OOF costing a little, but the effect is small and confounded with game length (longer games
  run more OOF turns).
- **Replay check of the largest OOF-rise flips v82 lost:**
  - the games: 01elk_arena Mite b (OOF 42 → 122), 01starfish Mite a (15 → 49), 04keyhole Fish a (11 → 43),
    00happy_halloween Fish a (1 → 34);
  - none of the deaths in them with 20+ gems comes within 3 rounds of the dying champion's own OOF turn;
  - those games are lost to big-bag deaths instead (starfish 470 gems lost, keyhole 305, halloween 338).
- **Across all 512 games** v82's deaths are -2.4% (4,985 against 5,109), gems lost on death level (68.6k), gems
  taken +2.7% and 100+ bag deaths level (140 against 144). The bag deaths in v82's lost flips mirror v81's in v82's
  won flips, so there is no new bag-loss pattern.

**Verdict:** v82 is level-to-positive live: +9 of 512 against v81 (z +0.70) and +21 against v78 (z +1.54). That is
well clear of the -20 revert line. The gain is against Fish (+10) and on multi-site maps; Mite is level. Its OOF turns
rise 39%, but no flip cluster traces to them. v82 stays active and pinned.
