# A dash's escape value outside retreat (2026-11-09): stopped at the shadow run

The idea came from planner-ideas REPORT §1. Wherever ocean spends a dash outside retreat (the strike search, chase's
`dash_to_attack`, Heart of Ruin's camp landings, travel), it prices the dash only as travel. The proposal was to also
charge the escape it gives up. Reuse the escape plan. Charge a dash ending on q only for the transition from "keeping
the dash leaves a clean escape" to "q, dash spent, isn't clean", and never charge hit counts.

**Verdict: the idea doesn't hold, so nothing was built past the shadow and no A/B was played.** The brief's first
test failed: the transition does not predict danger where the price would act.
- **Strike search** (the main site, 18.2 dashes a game): the transition is rare (1.2 a game). The champion then dies
  within 10 rounds 1.1% of the time (±0.8). That is below both a search turn that kept the dash on a clean tile (2.3%)
  and a strike dash on a tile that is unclean even with the dash kept (4.2%).
- **Travel dashes** do show a gap (4.5% against 0.9%), but on 0.73 dashes a game. That is ~0.03 deaths a game, too few
  to move a win rate.

`bots/ocean` on this branch is unchanged. The instrumentation is kept as `tools/dv_shadow.patch` (against e2c735657)
and the join as `tools/dv_shadow.py`.

## The design as proposed, and the critique before building

The report's file references check out:
- `combat/plan.cc:1211` (`dash_cost = dash_range * step`) and `:1760` (charged at the dash node);
- `model/pathing.cc:1243` (`travel_dash`, withheld within `travel_dash_clearance` = 10);
- `bot.cc:335` (`search_strikes`).

Two are slightly off. Chase's call is at `combat/fight.cc:835`; `dash_to_attack` itself is at
`combat/self_abilities.cc:424`. `escape_landings` is at `self_abilities.cc:183-235`.

The design I would have built, changed from the report in three places:
- **Accessor:** `Plan::after_turn(p, kept, slack)`, the hits on turns 2..5 after a turn ending on p with the dash kept or
  spent (`Pass::after[h][kept]`). With the dash kept the set is a superset of the spent one, so the dash's escape value
  at an end tile q is the binary `q ∈ after[0][kept] \ after[0][spent]`.
- **Per-tile marginal, not the report's walk baseline.** The report charges a dash ending unclean whenever some walk
  tile is clean with the dash kept. That charges the dash for where it lands, which an unclean walk is never charged
  for. The per-tile form prices only the asset: what holding the dash would be worth at q.
- **Units:** the search's own value of a champion, `kill_distance(our health, max health, our pair's bag × gem_value)`,
  times a death-rate difference measured once. A leaf that kills a foe is not charged, since the plan's pursuer set
  includes the victim. A Vendetta kill re-readies the dash, so it is not charged either.
- **Fuel:** build in `plan_strikes` after `read()`, only with the dash ready and the cast unspent. Keep the plan's own
  50k gate, and reuse its cache (a retreat later on the same tile reuses the plan).

## Shadow run

`tools/dv_shadow.patch` is a debug-only hook at every dash cast site. It builds a separate plan from the
pre-dash tile with the gate off, refunds the build's fuel with `sdk_fuel_adjust` (a positive delta refunds;
probe-fueladjust), and prints an `EDV` line. The line holds the site, the plan's hits on the end tile with the dash
kept (K) and spent (S), the least K over our walk tiles (the report's criterion), the fuel left, the bag and the
health. The bot's own plan, its cache and its decisions are untouched.

In the strike search the line is printed at the choice, for the chosen leaf's end tile: `S` if the leaf dashes, `N` if
the dash was ready and kept. The other sites are `A` (dash_to_attack), `K` (dash_onto), `H` (Heart of Ruin camp
landing), `T` (travel), `P` (capture handoff) and `E` (escape, for reference).

- **Data:** frozen as `bots/variants/dv-shadow` (debug), against `variants/oc-esc-merge` (= e2c735657's ocean), fast
  runner. Two batches of 256 games: `maps/gen` 128 maps both sides (`replays/batch-20261109-095549-886245`) and the
  128 ladder maps both sides (`replays/batch-20261109-095704-611294`). Extracted to `replays/dv-shadow-ex`.
- **Fidelity:** 159 of the 256 map pairs played identically with the sides swapped, as two equal bots do. The rest
  diverged through small fuel shifts (static caches the shadow builds warmed). Win rate 49.2%.
- **Outcome:** a death to a champion within 10 rounds of the dash (the esc_diag join, from `events.jsonl`).
- **Classes:** *clean-spent* means S = 0. *Transition* means K = 0 and S > 0, the only class the price would charge.
  *Saturated* means K > 0. *Inactive* means no pursuer in the window or no home. *Gated* means under 30k fuel left (no
  shadow build).

```
python3 research/retreat-2026-11-09/tools/dv_shadow.py replays/dv-shadow-ex dv-shadow
```

512 team-games, 124,963 EDV lines. Deaths to champions within 10 rounds, 95% intervals:

| site | class | a game | died ≤10 | deaths a game |
|---|---|---:|---:|---:|
| S strike search, dashed | clean-spent | 0.11 | 0/58 | 0.000 |
| | **transition** | **1.23** | **1.1% ±0.8** | **0.014** |
| | saturated | 12.18 | 4.2% ±0.5 | 0.506 |
| | gated (<30k) | 4.37 | 6.2% ±1.0 | 0.270 |
| | inactive | 0.31 | 6.9% ±3.9 | 0.021 |
| N strike search, dash kept | K = 0 (clean kept) | 10.06 | 2.3% ±0.4 | 0.230 |
| | K = 1 | 1.98 | 2.4% ±0.9 | 0.047 |
| | K = 2 | 4.90 | 4.7% ±0.8 | 0.230 |
| T travel, outside stop_ender | clean-spent | 1.12 | 0.9% ±0.8 | 0.010 |
| | transition | 0.73 | 4.5% ±2.1 | 0.033 |
| | saturated | 1.63 | 3.1% ±1.2 | 0.051 |
| | inactive / gated | 166 | 0.6% | 0.94 |
| H Heart of Ruin camp landing | transition | 0.47 | 1.2% ±1.4 | 0.006 |
| | saturated | 0.95 | 19.8% ±3.6 | 0.188 |
| A dash_to_attack (chase) | all | 0.04 | 10/22 | 0.020 |
| E escape dash (reference) | clean-spent / transition / saturated | 8.9 / 4.3 / 3.1 | 4.3 / 6.2 / 18.7% | |

The intervals treat dashes as independent; they cluster by game, so the real ones are wider.

- **The transition does not predict danger in the strike search.** By (K, S):
  - dashes: (0, 2) 1.2%, (1, 2) 1.8%, (2, 2) 4.3%;
  - kept: (0, 2) 2.4%, (1, 2) 2.4%, (2, 2) 4.7%.

  A dash that gave up a clean escape dies less often than a kept dash on a clean tile. Below half health the same
  holds: 0 of 29 transitions died, against 10.9% for saturated dashes.
- **The report's criterion fares no better.** "Some walk tile is clean with the dash kept, the dash's tile is not":
  strike dashes 3.9% (11.2 a game) against 3.6% when no walk was clean.
- **What the plan does separate is location, not the dash.** A strike-dash end tile that is unclean even with the dash
  kept (saturated) dies at 4.2%, as a kept end tile with K = 2 does (4.7%). The dash had no escape value there by the
  plan's own reckoning. The other mark is fuel: dashes under 30k left die at 6.2%.
- **Where the report's pool is.** Deaths within 10 rounds of a strike dash: 0.82 a game, close to the report's 0.85
  within 3 rounds of a non-escape dash. Of those, 0.51 follow saturated dashes, 0.27 fuel-short ones, and 0.014
  transitions. A price on the transition can touch about 2% of the pool.
- **Why.** In a fight the planner's worst case saturates: 90% of active-plan strike dashes end on tiles that are "many"
  even with the dash kept. So the transition fires only on dashes made at the edge of a fight, which are the safe ones.
- **Travel dashes** are where the transition reads above clean (4.5% against 0.9%; saturated 3.1%), on 0.73 dashes a
  game. A perfect fix would save ~0.03 deaths a game out of ~10, far below what a 10k-game screen resolves (±1 point).
  The stop_ender travel dashes (forced, 0.39 a game, 47% die) are deliberate trades for a winning bag.
- **Fuel would have limited it further.** Only 26% of strike dashes (4.8 a game) had 50k left at the choice, the
  plan's own gate.

## A/Bs

None. The brief says to stop if the shadow run shows the transition does not predict danger, and it does not at the
site the idea targets. Screening it would spend 10k+ games on a price that fires 1.2 times a game on dashes that die
less often than the baseline.

## What this rules out, and what it leaves

- **Ruled out:** pricing the dash's escape value by the plan's clean-to-not-clean transition, at any of the sites
  (strike search, chase, Heart of Ruin landings, travel). Also the report's walk-baseline variant of it.
- **Not tested, and not recommended on this evidence:** charging any leaf (walk or dash) that ends where the plan sees
  no clean exit, the report's "phase 2". In the data it separates 4.2-4.7% from 2.3%. But that is location danger in
  fights, where the kills are too. The plan's pessimism (logic-audit.md: ~90% of predicted hits are phantom) would make
  it a passivity term on most fight tiles.
- **Fuel-short dashes** (6.2% die against 4.2%) point at ocean's general out-of-fuel cost, as fuel-gate.md found for
  retreats, not at the dash.
