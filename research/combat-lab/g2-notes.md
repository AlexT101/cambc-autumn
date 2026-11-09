# G2: safety judged after the action (notes, 2026-11-08)

Variant `bots/variants/cl2-g2` (from `variants/oc-cl2-base`). Reference for every A/B: `variants/oc-cl2-base`,
`--no-test-draft`, suite `maps/suites/merged/cl2-dev`.

## How the turn-start judgement worked

- **Step guard** (`combat/guard.cc` `step_guard`, set by `guard_steps` before the strike search and keep_bid): a
  tile within the step/dash radius (1-2) is guarded when it is more exposed than ours and the fight there (fight
  key = visible foes whose Reach hits it, unseen threats, lost-turn enemies, allies near it) is lost, or we fall
  there and are linked or `lethal(q)`. All read from the turn-start roster.
- **Strike search** (`combat/plan.cc`): `Search::offer` did `ends &= ~guarded` before the candidate's kills and stuns
  were known to matter; the pricing loop dropped a tile whose guard a deferred cover resolved; the grid-edge tiles
  (distance 3) were dropped on `safety.lethal(p)`. The danger sum itself was already post-action (`removed`:
  drop_kill incl. the Cassi/Issac partner, drop_stun for enemies with one turn before ours).
- **Leave decision** (`bot.cc` `decide`): `want_home` on the turn-start state; `retreat()` makes a sure kill first
  (from here, or `step_to_kill`'s step/dash where only the victim reaches) and then keeps running home.
- `only_threat` (retreat's sure-kill test) excluded the victim but not a Cassi/Issac partner that dies with it.
- After the search, the goal's guards (guard_steps again, guard_work) are rebuilt after `see_stuns` + `refresh`, so
  they already read the post-action state. strike_after does not move.

## What changed

- `Pathing` remembers the guard's source (`guard_source()`), so only step_guard's tiles are re-judged (not
  Willow's station guard, not the tiles off a held capture, `held_out`).
- `Search::offer`: a plan that kills a foe or stuns one of its one turn before ours may end on a step-guarded tile.
  Each leaf records its kills (enemy bits, partner included), counted stuns, Ren retaliation taken and slots cast.
- Pricing loop: a guarded tile keeps only the candidates for which `still_guarded` (guard.cc) is false: step_guard's
  one-tile test with the killed out of the fight key, the stunned joining a turn late (`late` = 1), our health less
  the retaliation and our spent slots on cooldown (`Safety::fight_hurt`), and `lethal_without` for the falls case.
  At most 12 simulations a search; skipped for candidates that could not win anyway; short of fuel: still guarded.
- Grid-edge lethal tiles keep the candidates whose `removed` set makes `lethal_without` false.
- The query-capped path drops every guarded tile (before, one resolved mid-loop could be chosen at its Strike price).
- `stand_won_back` (fight.cc): after retreat's own sure kill, or keep_bid's attack, `see_kills` and ask `want_home`
  again; if it no longer sends us home, the retreat is abandoned (claim and branch restored) and the turn goes on
  as a stay (captures, strike search with what is left, the goal).
- `only_threat` also excludes the victim's linked partner.

## How often it fires (debug builds, 200 cl2-dev maps, 400 candidate games, 46k searches)

- Search: a guarded tile with a killing/stunning candidate reached pricing in 23 searches; 3 cleared. Grid-edge
  lethal tiles in 78 searches, 10 with a candidate that removes a threat. Chosen plans on a re-judged tile: 9
  (3 guard, 6 lethal edge). About 0.02 a game.
- Leave: 109 retreat turns with a kill of ours; 24 won the stand back (0.06 a game).
- An audit (read-only subagent) found an out-of-bounds cache read and our spent cooldowns counted as ready in the
  re-judged fight; both fixed before the A/B.

## Results (cl2-dev, 20,480 games each, release builds, `--no-test-draft`)

| Round | Change | Win % (95% CI) | OOF turns CAND / REF | Paired OOF a game |
|---|---|---|---|---|
| v1 (`cl2-g2-v1`) | search re-judge + leave re-judge + only_threat partner | 49.8 (49.2-50.5) | 214,631 / 207,326 | +0.36 (SE 0.055) |
| v2 (`cl2-g2-v2`) | v1, fuel overhead made lazy, + goal guard re-placed after a kill or stun | 49.9 (49.3-50.6) | 212,013 / 207,963 | +0.20 (SE 0.055) |

`fight_metrics.py` on each run's 1000 kept replays (a game, CAND vs REF):
- v1: kills 9.02 vs 9.09, deaths 9.42 vs 9.36, kill share at equal numbers 0.496.
- v2: kills 10.12 vs 10.19, deaths 10.63 vs 10.56, kill share 0.501.

All level.

**Fuel.** On identical searches (same map, team A's searches matched until the games diverged), v1's strike
search cost +490 fuel. Per-leaf bookkeeping in `offer` (kill, stun and spent-slot loops for every new leaf) cost
~90 a node in `grow`, plus `root()` and the guard-source test. Made lazy in v2, it is +66 on a typical search.
The rest of v2's OOF excess is most likely `see_kills`' vision re-read on kill turns, now also after the strike
search, and `want_home` re-asked on retreat kills.

## What was learned

- The gap is real but rare in games. A plan whose kills or stuns clear a guarded or lethal end tile was chosen ~0.02
  times a game; a retreat kill won the stand back ~0.06 times a game. The danger pricing was already post-action
  (`removed`). The step guard rarely guards a tile that a single kill or stun clears: mostly the fight is still lost
  to the other enemies and unseen threats (3 of 23 cleared).
- At these rates no A/B can resolve the effect (±0.7 points). Two rounds of 20k read level, and so did kills and
  deaths.
- Next, if anything: the bigger before-acting judgements are the leave decision on states no sure kill changes
  (`want_home` once a ready stun takes the only threat's turn, or once a ranged kill is weighed against the walk it
  spends), and G3's commitment. Both need the lab's counterfactuals before a full A/B.
