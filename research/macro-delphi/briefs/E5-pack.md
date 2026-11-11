# E5 "pack": the team farms as one pack around its Prism, and the Prism collects (bots/variants/pack)

Read /home/ubuntu/wt/macro-o4/research/macro-delphi/briefs/common.md first and follow it (note its TMPDIR rule).
Candidate dir: `bots/variants/pack` (create it: `./copybot charybdis variants/pack`). Reference: `bots/variants/charybdis-ref`.

## Why
Measured on 512 charybdis mirror games (2x fuel):
- **Kills decide.** Winners 6.9 kills / 2.2 deaths a game, losers 2.1 / 6.8. The first kill wins 69%, and the first
  Prism death loses 90%. Fights at camps are team fights: the victim usually has 3-5 enemies within 8.
- **The Prism duel is decided by Focus**, and Focus is the carried bag (+1.5 per gem). In 87% of Prism deaths the
  victim had under 0.8x the killer's Focus. Of capture gems on groups an *ally* cleared, our Prism gets only ~25%.
  The Prism collects 513-782 gems a game; each other champion collects 107-141 and walks them to altars (bag->altar
  walking is ~16% of ally turns).
- **Cohesion is the gap to the best ladder team (Fish).** Its whole pack turns on a target, and the kill rate climbs
  with attackers within 4 (Fish: 0 attackers 9%, 1 30%, 2 43%, 3+ 56%). It "travels as one group including the
  pair and Willow, takes the group to the enemy's side of the map, and when an enemy comes within sight every member
  drops the camp and closes" (research/ideas-2026-11-11/fishfight/README.md).
- **Soft nudges did not move the bot.** A farm-value bonus for allies on groups the Prism can take over (variant
  `hub`) changed only ~6% of ally picks and was level (50.1% of 10,240). Earlier "summon"/"pack mode" designs failed
  for a different reason: summoned champions walked to each other, came late, or ignored the call. So this is a
  structural rule in target selection, not a summons and not a bonus. Champions never walk to each other. They
  choose work inside a moving area.

## Design
The **anchor** is our keeping Prism: alive, `keeps_bag`, and its tile seen or posted (`recent_tile`). Its centre is
its current work: the claimed group's centre if it posted a claim, else its tile. Every non-Prism champion farms
inside the anchor's **pack radius**, R = `carry_reach()` (2 x capture_time = 12 steps). R is derived, not tuned:
it is the farthest walk from which the Prism can still come and collect a capture ('L' picks). Inside it, every
capture an ally makes can go on the Prism, and every fight has the pack within a few rounds' walk.

1. **Allies' targets (economy/farm.cc farm_turn).** For a non-Prism champion with an anchor:
   - Groups whose tiles are farther than R from the anchor centre (Chebyshev pre-check, then the walk if cheap) are
     not candidates. This covers solo, crew, kite, join and risky paths alike.
   - Exceptions: our bag's banking trip (`banks_bag`), heal/shop trips, siege/monolith operations already under way,
     and the opening plan while it runs (`open_plan_choice`).
   - If no candidate group is left, the champion walks towards the anchor centre (guarded `step_safely`) instead of
     farming far away. If the anchor is unknown or dead, behaviour is unchanged.
   - The prune bounds still hold: dropping candidates only lowers the best. Make sure the kept or memoised best is
     not a group the rule now excludes.
2. **Captures go on the Prism.** Inside the pack, a cleared gem group's capture should end in the Prism's bag:
   - `leave_for_prism` / `left_for_prism` (economy/capture.cc) and the Prism's 'G'/'L'/'Q' picks (farm.cc ~2270-2390)
     already hand captures over when the Prism's ETA fits. Within the pack, relax only the conditions that stop a
     hand-over the Prism can still make in time. Examples: the 'near' leave's `world.round - left.first >= capture_time`
     lapse when the Prism has claimed it, and `prism_dominant` (a dominant Prism still wants the gems now that
     allies do not need them). Keep the ETA-vs-payout timing checks.
   - Allies that cleared a group the Prism will take step off it to their next work. They keep off its tiles at
     payout (existing `prism_hold_tiles` / `held_step_guard`).
3. **The Prism leads.** The Prism's own choice is unchanged, except that it may prefer collection. Its existing
   'G'/'L'/'Q' picks already price that (`carried_bonus`). Do not add a new mode.
4. **Fights.** No new fight logic is needed, since everyone is within R. If it is simple, make the pack radius also
   bound an ally's walk-away targets (retreat stays as it is).
5. Without a Prism in our draft, or while ours is dead, nothing changes.
6. **Debug traces:** per turn, the anchor and the number of groups excluded; per capture, who got it (Prism or ally);
   the distance of each ally from the anchor every 50 rounds.

## Not in scope
Draft, emblems, banking thresholds (`bank_floor`), the strike search, retreat logic.

## Done when
- It builds.
- Three local games against charybdis-ref finish without bot errors, with a Prism in our draft (most maps have one).
- Traces show allies staying within R of the Prism and the Prism collecting most ally clears.

Report as common.md asks. Include: the Prism's share of our captures in your test games against the ref's, how
often an ally had no candidate in the pack, and how often captures were left uncollected.
