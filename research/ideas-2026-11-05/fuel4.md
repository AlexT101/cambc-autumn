# Fuel round 4: exact fuel savings in ocean (ocean, 2026-11-05)

Goal: fewer out-of-fuel (OOF) turns in ocean with exact savings: the same decisions, made more cheaply. Base
`variants/oc-base3` (= `bots/ocean`); dev copy `variants/oc-fuel4-dev`. Over 20,480 games against
`variants/astraeus-now-1105`, oc-base3 had 197.5k OOF turns and astraeus 141.8k.

Exactness check: `tools/fuel/bench.py` at 100M against oc-base3, replays byte-identical to oc-base3's on the
default (16), wide (52) and pool (128: the first 64 maps of fresh-519039) sets. Script:
`replays/fuel/ocfuel4/bench.sh`. A/Bs: `replays/fuel/ocfuel4/ab.sh`, fresh ladder-mix suites 525000-525039 (dev,
`maps/suites/merged/oc-fuel4-dev`) and 525100-525139 (confirm, `maps/suites/merged/oc-fuel4-conf`). Profiles ran on
fresh-525200, which no A/B uses.

## Where the fuel goes (oc-base3, real budget)

**Census** (`tools/fuel/census/instrument.py --fine --trace --lenient` on a copy, `variants/oc-fuel4-cen`, against
oc-base3; 64 fresh-525200 maps, both sides, 128 games): 912 OOF turns that began on time, 311 late, 10,643 heavy
finished turns (65k+ before the turn-end queue).

- 53% of OOF-first turns have no enemy within 6; 38% see none. Economy turns are the larger half, fights the rest.
- Where the fuel ran out (decide-level scope): farm 33%, carry_bag 16%, act_end 14%, turn_order 9%, retreat 6%,
  strike_search 5%, strike_after 4%, publish_order 4%.
- Inclusive fuel on OOF-first turns, where present: World::update 13.8k (100%), the channels 15.4k (74%: the recall
  kept or cancelled, with CHANGES 404's farm re-pick, `farm_reprice`, and `want_home`), farm 45.7k (56%; loop 29.6k,
  after the loop 18.2k), carry_bag 52.0k (23%), want_home 21.5k (17%), strike_search 36.6k (32%), retreat 48.0k (7%),
  chase 16.9k (22%), the fight sims `s.fight_of` 11.7k (26%).
- Self fuel summed over OOF turns: farm.loop 7%, strike_search 7%, farm 4%, wh.stand_lost 4%, route 3%,
  s.new_fight 3%, siege_kite 3%, camp 3%; the rest is spread thin.
- Signatures of OOF turns (components of 15k+): world+farm 20%, farm 13%, want_home+strike_search 8%, carry_bag 7%,
  channels+strike_search 6%.

**Flat profile** (`siteprof`-style, fastrunner site traces, 48 self-play games on fresh-525200): charging the fuel
between host calls to the next caller, `TurnEndQueue::run` and `sight` look large, but that is the attribution:
long call-free stretches land on the next function to make a host call. Not used for decisions.

**Fight value and funnel (CHANGES 413-414).** CHANGES 414's EXPERIMENTS entry found caching the funnel factor
changed nothing: the extra OOF turns come from the games they play (more fights), not from their arithmetic. The
census agrees: `current_emblem`/`prices` are ~2% of OOF-turn self fuel.

## The lever: astraeus's exact farm-turn campaign, which ocean lacks

ocean is astraeus 5b66bde0 plus its own changes. astraeus has since had a fuel campaign ocean never got
(3076ffa9: pre-facts bounds, crew pricing tables, the turn-end queue's clear warm-ups, live_camps by dirty group,
exact travel-plan windows; 7950979e: altar access without floods, the unseen-enemy box). On astraeus it read OOF
-15% (51.6% over 40,960 games) and -11% (49.9%, pre-loop). Its logic parts are left out: the prices tolerance
(d737bcf6), the spawn field on turn 1 (4a16bebf), the state-sized reserve (9dba3ed8, 1310d649) and its refit, and
CHANGES 409's beaten_near fix (ocean's own bound is kept).

Ported three-way, commit by commit on the first-parent line (`git merge-file` per file): 682d6dc8, 0afaebf8,
eaf6639d (501e32e0, 2a2ee15f and the camp_moved merge), 9d274454, 53add725 (bd30ed16, 5ffd89be), 65b6d496,
532ec6fd, 28cc1105, 2107c44d, 311d1ec7, c74930d8, b0e437ab; f1c93ff0's BagKey only (ocean's 406 memos already
cover the rest). CHANGES 409's adaptations to the recall out while carrying (CHANGES 404): PreLanes' banking trip
and claim_most take the recall-out trip.

Two things made the port inexact on ocean; both are fixed:
1. **Exposure.** CHANGES 405's SPSA tuned `max_exposure` (1.215) below `mid_exposure` (1.361); in astraeus they
   are equal. The pre-facts bounds scale worth by `max_exposure` as the most `exposure()` gives, which ocean's
   middle band exceeds, so they pruned groups that would win. The new bounds take `exposure_most`
   (max(1, mid_exposure, max_exposure)), and ocean's own pre-facts prunes, at `max_exposure` without clears or
   weights, are kept beside them (`pre_old`, `pre_old_alt`), so a group either pruned is pruned.
2. **Path dependence.** The weighted value bound against the best (`pre_value`) and `claim_most` skipped groups
   that ocean walks as far as `live_steps` before rejecting them, and `live_steps` keeps each approach's camp
   labels (`same_labels`), which later turns read. Those two bounds now run just after `live_steps`; the bounds
   against the bar stay before facts (they stand in for prunes that come before it).

## Plan

1. The port above (done: exact on 196/196). Frozen as `bots/variants/oc-fuel4` (CHANGES 415), **shipped** into `bots/ocean`.
2. Open: the channels (`continue_recall`'s want_home and farm re-pick each turn of a recall).
3. Open: the strike search (`plan_strikes` is `[[gnu::flatten]]`, so its 9% self fuel on OOF turns is spread over
   inlined code that the census cannot split), `stand_lost_at` and the fight sims, on turns with enemies near; and
   `update_camps` (6.3k on 82% of OOF-first turns).
4. Each step: exact at 100M on all three sets, the real-budget wide bench, then an A/B against oc-base3.

## Results

**Exactness** (bench.py at 100M against oc-base3): default 16/16, wide 52/52, pool 128/128 identical replays. Along
the way: the plain port 7/16, 23/52, 66/128; with `exposure_most` and the old lanes 16/16, 50/52, 118/128; with
`pre_value` and `claim_most` after `live_steps` 16/16, 52/52, 128/128.

**Fuel at 100M** (same games, so a pure cost cut): total -2.32% default, -2.63% wide, -2.57% pool; p50 -2.5/-3.1/-3.7%,
p99 -3.8/-3.9/-4.7%.

**Real budget.** Wide bench (52 games): mean fuel a turn 51,569 -> 50,047, OOF turns 929 -> 693 (-25%), farm's
partial evaluations 11,308 -> 9,625, turn-order 1,639 -> 1,320. Census (128 games, fresh-525200): OOF turns 981 -> 780,
OOF-first 912 -> 711, farm partial evaluations 32,977 -> 28,366. What is left is fight-heavy: strike_search in 41% of
OOF-first turns at 38k, want_home 23k, the channels 17.7k, farm 42.6k on 54%.

**A/Bs** (own drafts, fast runner, 20,480 games each):

| CAND | REF | Suite | Win % | 95% CI | OOF cand / ref |
|---|---|---|---|---|---|
| `oc-fuel4-a` (= oc-fuel4) | oc-base3 | oc-fuel4-dev (525000-525039), SPRT 0.50/0.51 ran to completion, LLR 2.29 | **50.8** | 50.1-51.4 | 159.1k / 203.4k |
| `oc-fuel4` | oc-base3 | oc-fuel4-conf (525100-525139) | **50.7** | 50.1-51.4 | 159.2k / 202.1k |
| `oc-fuel4` | `astraeus-now-1105` | oc-fuel4-conf | **55.8** | 55.1-56.5 | 152.0k / 140.1k |

OOF turns -21.7% and -21.3% against oc-base3. Against astraeus, ocean's excess out-of-fuel turns fall from +39%
(oc-base3, 197.5k / 141.8k on fresh-524000..524039, 55.6%) to +8.5%. That 55.8% is on another suite, so it is
not a measured gain over 55.6. Sources: `replays/ab/oc4-a-dev/`, `replays/ab/oc4-conf/`, `replays/ab/oc4-ast/`.
