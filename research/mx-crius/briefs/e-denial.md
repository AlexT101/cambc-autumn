# Brief E: price contested groups as a race, with the denial they carry (implementation subagent)

You implement one macro change to our Cambridge Battlecode bot charybdis, in C++, and measure it. Work only in
`/home/ubuntu/wt/mx-crius` (a git worktree on branch `mx-crius-20261113`). Do not commit, push or touch any other
worktree or `/home/ubuntu/cambc-autumn`. Do not edit `bots/variants/chy-ref` (the frozen reference), `bots/charybdis`,
or any other variant. Another subagent may be working in `bots/variants/d-stakes` (fight valuation in combat/);
stay out of combat valuation.

## Read first
- `AGENTS.md` (repo rules: fuel, debug_block tracing, testing), `cambc-rules.yaml` (engine-verified: win at 1000
  tributed gems, capture and respawn, camps), `docs/api/cpp.md` as needed.
- Source (`bots/variants/chy-ref/src`): `economy/farm.cc` farm_turn (group worth and `rate`; `exposure_of` ~line 1322
  with `params::mid_exposure` 1.361 and `mid_low_share` / `own_ground_share` / `mid_edge`; `exposure_kept`; `exposed`
  ~line 1882 with Ren's `pull.deny_scale`; the pre-facts prunes bounded by `params::max_exposure` and `exposure_most`;
  claims), `economy/camps.cc` (`rate`, `home_side`, `home_ground`: a static spawn-walk-ratio weight, at most 1),
  `economy/capture.cc` (`prism_premium`, `team_farm`), `model/enemy_reach.{h,cc}` and `model/safety.{h,cc}` (where
  enemies can be: seen, tracked, `possible` sets), `model/comms.{h,cc}` (claims, posted positions, camp respawn
  record), `bot.cc` `decide()`.
- `research/macro-2026-11-11/macro2/macro2-log.md` "macro2-race" and `research/macro-2026-11-11/macro3/macro3-log.md`
  "macro3-intent": both *discounted* contested groups (farm value x p_win; an enemy-intent contest discount) and lost
  5 and 3 points: "contesting is worth it". This brief prices the other side of the same race.

## Why (measured on 1,700 mirror games of chy-ref vs itself; scripts in research/mx-crius/scripts)
- Early bags decide games: at r150 a Prism bag lead of 20-50 gems wins 63%, 50-100 72% (median Prism bag 105).
- The economic gap is the middle: winner minus loser captured gems by r300, own / middle / enemy zone (by the
  group's share of the two spawns' distances; middle 0.4-0.6): +11.5 / +43.7 / +2.2; by r600 +18 / +110 / +8.
  Own-half farming is level; the enemy half is barely farmed by anyone.
- In the middle the team that wakes a group captures it 88% (93.5% with no enemy within 8 at the wake, 75% with one);
  winners wake 52.8% of middle groups and take 59.7% of middle gems. A middle group we leave is usually the enemy's.
- Groups sit up and asleep 60-72% of rounds even in solo games: the farm is champion-time bound, so an own-half group
  left now is mostly still there later, while a middle group left now is lost to the enemy.
- The current price of this is two static tuned weights: mid_exposure (a middle group is worth 1.36 of itself) and
  home_ground (a spawn-walk-ratio discount). Neither looks at where the enemy is or who would take the group.

## Design
In a race to 1000, a gem the enemy does not get moves the race as a gem we get does: ours shortens our clock by
1/r_us rounds, theirs lengthens theirs by 1/r_them (r the teams' collection rates, `team_farm`-style, the enemy's
from its score and seen bags). So the worth of taking group g now is
  W_us(g) + p_enemy(g) x W_them(g) x (r_us / r_them),
where W_them prices the gems as the enemy would use them (x (1 + their Prism's premium) when their Prism would take
them: its Focus compounds for them as ours does for us), and p_enemy(g) is the chance the enemy takes g if we do not
take it now: from where enemies are or can be (seen, tracked, possible sets, posted claims we saw them make), their
walk to g against its availability (respawn timer, which comms and camp records already track), and the measured
waker-captures base rate. Own-half groups the enemy cannot reach first get p near 0; contested middle groups high.
- Put it in the farm's worth where mid_exposure / home_ground act now, and replace those static weights with it
  (or show what they price that this does not, e.g. contact risk, and keep only that part). Do not discount
  contested groups for risk here (that is the lost macro2/macro3 direction; risk is another line's job).
- The prunes: any term that can raise a group's worth needs an upper bound so the pre-facts prunes stay sound
  (replace max_exposure / exposure_most with the bound of your term: p <= 1 and the premium ratio's maximum). CASTOR's
  C8 lost through fuel blow-ups when bounds were broken. At 2x fuel weaker prunes are tolerable, broken ones are not.
- Every ally must compute the same p and W from shared information (claims depend on it).
- Leave alone `draft/`, which emblems champions build (`economy/shop.cc` emblem choice), fuel optimisation (we test at
  2x fuel; a guard against runaway loops is fine), and combat valuation (combat/). No magic numbers or map-specific
  cases: quantities from the rules or measured.

## How to work
- `./copybot variants/chy-ref variants/e-denial` (never copy `.cambc/`) and work in `bots/variants/e-denial`.
- Win rate: `source ~/venv/bin/activate && cd /home/ubuntu/wt/mx-crius && CAMBC_BIN=/home/ubuntu/cambc-autumn/tools/fastengine/runner/fastrunner FASTRUNNER_MODE=native PATH=$HOME/.cargo/bin:$PATH py tools/ab.py variants/e-denial variants/chy-ref --no-test-draft --fuel 200000 --suites maps/suites/mx/train --name mx-crius-e-<tag>`
  (10,200 games, ~3-8 min; `replays/ab/<name>/summary.md`). Run long commands in the background
  (`run_in_background`), never a foreground sleep loop. Use only `train` for A/Bs and `study` for `--debug` traces
  (`debug_block({ printf(...); })`, output in replays' `team-?.stdout`); never `dev`, `hold`, `x1`, `x2`, `x3`, `scr`
  or `fin`. Delete replay batches you no longer need.
- Check it moved what it should, on extracts (`node tools/replay/extract.mjs BATCH --out DIR`): middle captures and
  wakes by bot (`research/mx-crius/scripts/zones.py`, `midcycle.py`; they orient by winner, adapt them to orient by
  team name `meta['teams'][t]['name']`), Prism bag at r150/300 by bot (`bagwin.py`), and that deaths did not rise
  much (`prismdeath.py`, `killnum.py`).
- Iterate at most ~4 full train A/Bs (fix bugs and missing companion pieces; do not sweep constants).
- Before returning: spawn a **read-only** auditor subagent (tell it explicitly not to edit anything) to check the
  change against this design and the rules for bugs (prune bounds above all, ally consistency); fix what it finds;
  make sure the bot builds; play a smoke `py tools/ab.py variants/e-denial variants/chy-ref --no-test-draft --fuel 200000`
  (256 ladder games: no failed games, no DRAFT-UNFINISHED / PLAN-CHECK).
- Stop when: built, audited and smoked with its best train A/B; or after ~4 train A/Bs; or if the premise proves wrong.

## Report back (concisely)
Variant path; what you built (files); p_enemy's distribution by zone; each train A/B (win %, CI, OOF both sides) and
what changed between them; middle wakes / captures and Prism bags before and after; the auditor's findings and
fixes; the smoke; what you would try next. Save the final diff:
`diff -ruN bots/variants/chy-ref/src bots/variants/e-denial/src > research/mx-crius/patches/e-denial.diff`.
