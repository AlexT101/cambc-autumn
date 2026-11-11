# T9: Prism bag duels (candidate `bots/variants/macro2-duel`)

Read /home/ubuntu/wt/macro2/research/macro-2026-11-11/briefs/common.md first and follow it. Base: copy
`variants/ocean-ref-b7c87cf` to `variants/macro2-duel`.

## Rules (cambc-rules.yaml)
- Prism: +1.5 Focus per carried gem.
  - Ability 0: a 1.5 x Focus unit-target stun.
  - Ability 1: a 1 x Focus ground spell.
  - Both are `exclusive` (a cast turn has no walk; check the rules' wording for `exclusive`).
- Ability range is 4. A ground spell hits the 3x3 around its target tile, so it reaches enemies 5 tiles away.
  A slot cast in round t is ready again in round t+8.
- A stun removes the target's next turn and cancels its recall or tribute.
- Turn order alternates one champion at a time. Each team's champions go by priority, team A first in odd rounds,
  team B in even rounds. So a given enemy may get 0, 1 or 2 turns between two of ours (ocean's `turn_order.cc`
  computes this).
- Ocean's Prism keeps its gems until its bag wins (`retaining_gems`). That makes its Focus, and its bag, the
  largest on the map.

## Evidence (256 distinct ref-vs-ref mirror games; replay-watcher report)
- There were 45 Prism-on-Prism kills of bags of 100+, and the victim's team lost 41 of those games. In 71 of the
  201 Prism games, the loser lost a 100+ bag.
- In 33 of the 45, the victim could see its killer at the start of the turn before. The killer had the larger bag
  in 32 and its stun ready in 31. The victim's stun was cooling down in 28 (both spells in 18).
- Examples (debug replays with D lines in
  /home/ubuntu/wt/macro2/replays/batch-20261111-033927-ab-macro2-dbg-s-200001, team A = macro2-base, which equals
  ref; narrations in
  /tmp/claude-1000/-home-ubuntu-cambc-autumn/b6215605-83f5-4219-85ac-eb40528dec74/scratchpad/watch/narr/games/):
  - game 185 (gen-ladder-20000100048, map in /home/ubuntu/wt/macro2-maps/s-200001): at r356-360, B's Prism (347
    gems, Focus 610) was holding a capture (branch P) while A's Prism (476 gems, Focus 804) was in view.
    - B's Prism stepped back one tile a turn (R at r361-362) as A's Prism closed one tile a turn.
    - At r363, A acted first and cast its area spell from 5 tiles for 700, killing B's Prism (361 gems).
  - game 307 (gen-ladder-20000100109): B's Prism (400/700 hp, 322 gems, branch F) farmed toward A's group. It never
    saw A's Prism behind a wall block and ended its turn 4 tiles from it. A's stun did 1002.
  - game 249 (gen-ladder-20000100080): B's Prism (224 gems) spent its stun on a 120-hp gem camp while A's Prism was
    in view. At r326 it took a "chase Cassi" step to 4 tiles from A's Prism, which had both spells ready.
    Stun 544 plus area 350 killed it.
  - mut-yin-yang game (s-200001 `mut-yin-yang-20000117018`): A's Prism (228 gems) spent both spells on a camp.
    B's Prism walked 9 tiles in unseen and hit for 568. A's retreat step then moved it closer (5 to 3 tiles), and
    it died.

## Principle
Each bag duel is decided by one burst. Two things decide it: who acts first while the other stands inside its
reach, and whether the burst covers the target's hp. No walk is needed to cast, so the danger zone is the caster's
reach from where it starts its turn, which is where it ended its last one. With two turns before ours it can walk
first and then cast. A big bag raises a Prism's own Focus, but it also makes that Prism the biggest prize on the
map, and its stun is its only defence. Spending that stun on a camp leaves it unable to answer for 8 rounds.

## What to build (bounded)
1. **Diagnose first.** Reproduce game 185 (both seats run ref; `cambc run` with the same seats, map and `--fuel
   200000`, debug build, deterministic). Find why ref's safety let B's Prism end r361 and r362 inside A's Prism's
   reach. Check each in turn:
   - The step guard / lethal tiles (`model/safety.*`, `Safety::lethal`, strike computation).
   - Whether the capture-hold and retreat branches consult it.
   - Whether the enemy Prism's burst damage is Focus-scaled with its bag (1.5 per carried gem, read from the
     visible enemy's Focus).
   - Whether the area spell's 3x3 (reach 5) is modelled.
   - Whether the retreat step picks a tile still inside reach when one outside exists.
   Do the same quickly for game 249 or the yin-yang game. Write down what you find in your report. It is the main
   deliverable if the fix turns out large.
2. **Fix the model where it is wrong.** For example, burst reach or damage, a branch that skips the guard, or a
   retreat choosing the wrong tile. These are rule-derived corrections, not tuning.
3. **Stun reserve.** While an enemy Prism (seen, or possible from ocean's unseen-enemy model) could get within
   ability range of our Prism before our stun is ready again (8 rounds, at its walk speed), our Prism doesn't spend
   ability 0 on camps. Ability 1 may still be used on camps only if ability 0 is ready. Keep both for champions.
   Apply this to any of our champions whose stun is its defence against a burst that covers its hp, if it falls out
   naturally. Otherwise keep it to Prism.
4. **Keep:** the draft, emblems, `retaining_gems` (don't change when the Prism banks), the farm, and all other
   champions' behaviour except what the model fix in step 2 touches.
5. **No new tuned constants.** Use rule values: Focus multipliers, range 4, the 3x3 area, cooldown 8 and speeds.

## Check
Trace `DUEL round handle enemy_dist burst our_hp stun_ready verdict` (debug_block) on turns where an enemy Prism is
within 8 of our Prism. Rerun game 185 with the candidate as team B and ref as team A, and report whether B's Prism
survives r363. Then play 2 more local games and audit, as common.md says.
