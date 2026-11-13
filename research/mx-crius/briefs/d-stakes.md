# Brief D: price fight stakes with the economy's values (implementation subagent)

You implement one macro change to our Cambridge Battlecode bot charybdis, in C++, and measure it. Work only in
`/home/ubuntu/wt/mx-crius` (a git worktree on branch `mx-crius-20261113`). Do not commit, push or touch any other
worktree or `/home/ubuntu/cambc-autumn`. Do not edit `bots/variants/chy-ref` (the frozen reference), `bots/charybdis`,
or any other variant. Another subagent works in `bots/variants/c-balance` on pricing the expected contact loss into
the farm's job choice (economy/farm.cc); stay out of the farm's job pricing.

## Read first
- `AGENTS.md` (repo rules: fuel, debug_block tracing, testing), `cambc-rules.yaml` (engine-verified rules: death and
  respawn, kill gold, linked pair, capture, tribute), `docs/api/cpp.md` as needed.
- Source (`bots/variants/chy-ref/src`): `params.h` (life_value, gem_value, tribute_value, recall_value, chip_value, and
  turn_order's fixed copies), every user of them (`grep -rn "life_value\|gem_value\|tribute_value\|recall_value"`):
  `combat/plan.cc` (the fight planner), `combat/abilities.cc` (hit_worth, stun_worth), `combat/self_abilities.cc`,
  `combat/fight.cc` (stands, retreat, kill-cost turns), `combat/guard.cc`, `model/safety.cc` (side focus, fight
  sims), `model/turn_order.cc` (priority bids: rank codes need values modulo 15, see its static_assert),
  `economy/farm.cc` ~2699 (a camp-damage worth). The economy's values: `economy/capture.cc` `prism_premium`,
  `team_farm`, `holder_value`; `economy/shop.cc` `prices(world).per_gold`, `gold_income`, income rates.
- `research/hyperion/CHANGES.md` 527 (CASTOR: one consistent Prism-gem price used by every "who gets these gems"
  choice won +3 to +5 points; the gains of this programme family came from pricing consistency).

## Why (measured on 1,700 mirror games of chy-ref vs itself, `replays/an-mirror`; scripts in research/mx-crius/scripts)
- In lost games the final gem gap is mostly kill transfers (-472 gems) against captures (-206).
- 78% of Prism kills are by the enemy Prism, carrying 148 gems a kill; a team whose Prism loses a 100+ bag wins 6%.
  Prism duels are decided by bags: with a gap of 250+ the richer Prism kills in 47% of encounters, the poorer 0.9%.
- The fight code prices everything in enemy health points with tuned constants: a life = 276.6, a carried gem 17.5
  (so a life = 15.8 gems, whoever dies and whenever), a stopped tribute 83, a cancelled recall 66. The economy prices
  the same events differently and by state: a gem a Prism keeps is worth 1 + prism_premium (expm1(k rho H), up to
  ~2 and more early), gold at per_gold, a champion's round at its team's farm rate. Earlier programmes found that
  scaling these constants up or down loses (any weight +-50%: 44-50; Prism life x2 level): the average level is
  about right, so the gain, if any, is in making the value follow the state, not in moving it.

## Design
One function gives the stakes of a champion's death in gems, from the economy's own quantities and the rules, and
every fight valuation uses it instead of the fixed life_value / gem_value products:
- **Victim's loss**: its respawn (rules: 60-61 rounds) at its own farm rate (gems a round, its gold at per_gold, from
  the income model the economy already keeps or a team-level rate split by output), plus what its absence costs in
  the duel (its Prism's premium on what it would have farmed, for a Prism).
- **Killer's gain**: the victim's bag, which goes to the killer: x (1 + killer's premium) when the killer is a Prism
  that keeps it (our Prism's kill of a carrier is worth more to us than a Vesper's; an enemy Prism's kill of ours
  likewise costs us more), the kill gold (100, 150 with Hunter) at the killer team's per_gold, and for the Cassi &
  Issac pair both bodies and both bags (pair_gems already does the bags). Gems past the win are worth nothing; a
  winning bag is worth the game.
- Convert to the fight's units with one exchange rate (the current gem_value, HP per gem, keeps the planner's
  damage-to-value trade where it is), so a life = life_gems(victim, killer) x gem_value. Check what your derived
  life_gems averages over real games: if it is far from 15.8, say so and find out what the tuned constant carries
  before deciding.
- Apply it symmetrically: what our champions risk (stands, retreats, the bag at stake) and what enemy kills are worth
  (targeting, stuns, chase), including turn_order's bids if they can take it within their encoding (else leave
  them and say so). tribute_value / recall_value: express them in the same units if there is a clean derivation
  (rounds of delay x the rate), else leave them.
- Every ally must compute the same numbers where they coordinate (shared plan, bids): use only what all read alike.
- Fuel: the planner and Safety are hot; cache per round per champion. Leave alone `draft/`, which emblems champions
  build (`economy/shop.cc` emblem choice), fuel optimisation beyond keeping it sane (we test at 2x fuel), and the
  farm's job pricing (line C). No magic numbers or map-specific cases.

## How to work
- `./copybot variants/chy-ref variants/d-stakes` (never copy `.cambc/`) and work in `bots/variants/d-stakes`.
- Win rate: `source ~/venv/bin/activate && cd /home/ubuntu/wt/mx-crius && CAMBC_BIN=/home/ubuntu/cambc-autumn/tools/fastengine/runner/fastrunner FASTRUNNER_MODE=native PATH=$HOME/.cargo/bin:$PATH py tools/ab.py variants/d-stakes variants/chy-ref --no-test-draft --fuel 200000 --suites maps/suites/mx/train --name mx-crius-d-<tag>`
  (10,200 games, ~4-8 min; `replays/ab/<name>/summary.md`). Run long commands in the background
  (`run_in_background`), never a foreground sleep loop. Use only `train` for A/Bs and `study` for `--debug` traces
  (`debug_block({ printf(...); })`, output in replays' `team-?.stdout`); never `dev`, `hold`, `x1`, `x2`, `x3`, `scr`
  or `fin`. Delete replay batches you no longer need.
- Check it moved what it should: kills and deaths a game by type, gems moved by kills, Prism deaths with 100+ bags
  (`research/mx-crius/scripts/prismdeath.py`, `killnum.py`, `py tools/replay/fight_metrics.py DIR` on extracts:
  `node tools/replay/extract.mjs BATCH --out DIR`).
- Iterate at most ~4 full train A/Bs (fix bugs and missing companion pieces; do not sweep constants).
- Before returning: spawn a **read-only** auditor subagent (tell it explicitly not to edit anything) to check the
  change against this design and the rules for bugs (units, sign, symmetric use, ally consistency, turn_order
  encoding); fix what it finds; make sure the bot builds; play a smoke
  `py tools/ab.py variants/d-stakes variants/chy-ref --no-test-draft --fuel 200000` (256 ladder games: no failed
  games, no DRAFT-UNFINISHED / PLAN-CHECK).
- Stop when: built, audited and smoked with its best train A/B; or after ~4 train A/Bs; or if the premise proves wrong.

## Report back (concisely)
Variant path; what you built (files); the derived life_gems distribution against 15.8; each train A/B (win %, CI,
OOF both sides) and what changed between them; kill/death metrics before and after; the auditor's findings and
fixes; the smoke; what you would try next. Save the final diff:
`diff -ruN bots/variants/chy-ref/src bots/variants/d-stakes/src > research/mx-crius/patches/d-stakes.diff`.
