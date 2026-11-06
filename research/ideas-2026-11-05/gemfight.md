# gemfight: gem-aware fighting (ocean, 2026-11-05)

Base `bots/variants/oc-combo2` (= `bots/ocean` at the start). Dev copy `bots/variants/oc-gemfight-dev`, knobs in
`params::gemfight::`; subvariants `bots/variants/oc-gemfight-<name>` made by
`research/ideas-2026-11-05/gemfight-tools/mkvar.sh NAME knob=value ...`. Runs are queued through
`gemfight-tools/runq.sh` (one ab.py at a time; logs in `gemfight-tools/logs/`, results in `replays/ab/gf-*`).

## How gems enter fighting now (read-only audit)

Weights are in enemy-HP units: life_value 273, gem_value 16.0, tribute_value 83.2, recall_value 66.3.
- Enemy gems are used in the kill-value formula (`kill_distance`, `hit_worth`), the strike search, best_hit, prey's
  chase order, preyable's carrier exception and game_ender.
- They are not used in engage/retreat: want_home, drawn_home, stand_lost_at, the pack zone, Safety's trade
  simulations, or the strike search's end-tile danger (raw expected damage).
- Our own gems are only thresholds: brake_bag 19 (pack retreat, pursuit), farm's pack-zone avoidance, chain_bag_limit,
  tribute_ok. The strike search prices our health lost at 1 per point whatever we carry.
- A recalling enemy gets a flat recall_value, and only from casts; intercept_steps and preyable never model a recall,
  though any damage cancels it and it lands 5 turn ends after it starts (rules recall.channel).

## Evidence

Script: `gemfight-tools/gemev.py ANALYSIS [--own]` (extracted replays; a recall counts when it completes or lasts 2+
rounds, so turn-end feints are out).

| Per game | ladder, 965 games (both sides) | ours (oc-combo2) vs astraeus, 1,873 games: us / them |
|---|---|---|
| deaths to champions with bag >= 10 / 20 / 40 | 3.38 / 2.32 / 1.11 | 1.45 / 1.10 / 0.62 vs 2.00 / 1.56 / 0.87 |
| gems lost to champion kills | 158 (tributed 1,517) | 103 (tributed 844) vs 126 (742) |
| recalls with >= 10 gems completed | 23.6 | 13.2 vs 10.4 |
| ... completed while an enemy saw it within 6 / 4 | 3.47 (178 gems) / 0.98 | them escaping us: 1.61 (80 gems) / 0.50 |
| real recalls with >= 10 gems cancelled by champion damage | 0.35 | ours cancelled by them 0.07; theirs by us 0.07 |
| carriers >= 20 seen within 5 by a healthy enemy (30-round episodes) | 21.4 | ours 11.6, theirs 11.6 |
| ... then tributed with no champion damage taken | 4.72 | them past us 1.81; us past them 2.01 |

Reading:
- Recall escapes are the biggest pool: enemy carriers recall away while we see them within 6 tiles 1.6 times a game,
  about 80 gems, and we cancel about 1 in 23 of the recalls we could plausibly reach. The ladder is the same (0.35
  cancels against 3.5 escapes a game).
- We die with a bag of 10+ 1.45 times a game, losing ~100 gems (12% of what we tribute); astraeus loses more to us.
  So pricing our bag in fights has some room, but our losses are already below the opponent's.
- Big enemy carriers walk past a healthy champion of ours to an unharmed tribute ~1.8 times a game.

## Variants (knobs; all off = oc-combo2 byte for byte at 100M, 68/68 bench replays)

1. **own_bag_weight w** (combat/plan.cc `Search::read`, `hit_unit`, `spell_unit`, `centre_value`, `land_at`,
   `add_unseen`, `plan_strikes` end-tile pricing): our health lost costs `1 + w B / (2 sqrt(H F))` of itself (B our
   bag at gem_value, both bodies for a pair via `bag_at_stake`; H health, F max health): the bag's share of
   kill_distance's slope at H. Applies to retaliation, enemy blows at the end tile, unseen threats, camp fire, and
   the shield's worth. 20 gems at full health: +16% per unit of w. Sweep w 1, 2, 4, 8.
2. **enemy_bag_slope s, enemy_bag_cap c, enemy_bag_stand** (model/safety.cc `chase_trade`, `stand_trade`, new
   `boost_side`; combat/fight.cc `prey`, `stand_lost_at`): the fight against a carrier of g gems plays out with our
   side's health x (1 + min(c, s * gem_value g / life_value)), unmemoised. prey's lost-fight memo is skipped for
   boosted targets. With enemy_bag_stand, stand_lost_at boosts by the biggest bag in the roster.
3. **bag_ramp_from b0, bag_ramp_power p** (combat/guard.cc `pack_members_of`): a bag >= b0 counts as hurt, at
   ratio hurt_retreat_ratio x (brake_bag / bag)^p (min with the home/low ratio there), replacing the step at
   brake_bag 19: smaller bags retreat from bigger packs only, bigger bags from smaller ones.
4. **recall_intercept, recall_gem_factor f** (combat/fight.cc `recall_held`, `reach_turn`, `intercept_steps`,
   `preyable`; combat/plan.cc Node `recalled`, `hit_unit`, `spell_unit`, `centre_value`, `hit_centre`;
   combat/abilities.h `recall_worth`): preyable drops a recalling enemy we cannot hit before it lands, and keeps an
   own-ground carrier we can; a cancel is worth recall_value + f * gem_value * gems, by basic attacks too, once per
   enemy a turn. Without the knob, f alone changes the cast value.

Fuel: 1 and 3 add a few multiplies; 2 adds an unmemoised fight simulation per boosted chase/stand candidate
(~2-10k each); 4 a kept_recall host read per visible recaller.

5. **recall_lag n** (model/safety.cc `make_slot`, combat/guard.cc `pack_members_of`, model/world.h
   `enemy_recall_kept`), added after the escape finding below: a visible enemy in a real recall joins the fight
   simulations n of its turns late and leaves the pack zone.
6. **bag_line_slope s, bag_line_cap c** (combat/fight.cc `drawn_home`): the threatened recall line x (1 + clamp(s bag
   / brake_bag, -c, c)), added after the bag-death finding below.

More evidence, from the sweep's own games: in 576 of 676 enemy recall escapes within 4 tiles our nearest champion was
retreating itself (decision R), and 69% of our deaths with 20+ gems come within 5 rounds of a retreat decision (26%
while stopping a game-ender). Neither knob 4 nor 5 raised the rate at which we cancel carriers' recalls (0.076 and
0.073 a game against the opponent's 0.090 and 0.081 in the same mirror games).

## Results

All rows in EXPERIMENTS.md "Gem-aware fighting (ocean, 2026-11-05)". Suites: dev `maps/suites/merged/gf-dev`
(fresh-520000..520039), confirm `gf-confirm` (520100..520139) and `gf-confirm2` (520300..520339), varied `gf-varied`
(520200..520209, unused).

- Against oc-combo2, every variant reads 48.0-50.1 at 20,480 games; the two best (bag_ramp_from 10 power 0, recall_lag
  1) read 49.9 each on unused seeds. Retreating earlier with a bag (knob 6 > 0, knob 3 from 14) loses with a
  dose-response; later is level.
- Rebased on oc-base3, enemy_bag_slope read 50.6 on dev at three slopes, but 50.4 and 49.8 on two unused 20k sets
  (pooled 50.1, 49.6-50.6) with ~2% more out-of-fuel turns. Not confirmed.
- Nothing kept; every knob stays off. No panel run: no candidate passed its confirm.
