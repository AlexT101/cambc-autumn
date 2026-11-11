# T14: holds and bids that look past the next window (candidate `bots/variants/macro2-exits`)

Read /home/ubuntu/wt/macro2/research/macro-2026-11-11/briefs/common.md first and follow it. Base: copy
`variants/macro2-combo` (`./copybot variants/macro2-combo variants/macro2-exits`). The combo is ref plus three
level fixes. It is our current best, at 50.55% of 30720 games.

## Evidence (T9 duel diagnosis, debug reruns of ref-vs-ref games)
1. **Game 185** (gen-ladder-20000100048 in /home/ubuntu/wt/macro2-maps/s-200001, seats ref A vs ref B, fuel 200000):
   - B's Prism (347 gems) held the capture on Gems5 at (16,27), in a pocket. Walls are at x=13-14, and Gems4's live
     camps sit at (15-18, 29-30).
   - A's Prism (Focus 804) closed in. At r360 `hold_outlasts` kept the hold: the payout was due at r361, and
     `turns_to_kill_idle` put an idle kill at 3 turns, beyond its 2-turn window.
   - Its horizon ends at "the payout and our turn after it". It never asks whether a way out exists after the
     payout. From (16,27), no tile within B's next two steps was out of A's walk + area reach (7+). B was dead from
     r361 and died at r363 with 361 gems.
2. **Yin-yang game** (mut-yin-yang-20000117018 in s-200001):
   - At r262, A's Prism was on branch R. `keep_bid` runs before `retreat()`, and it stepped A from distance 4 to 3
     of B's Prism on the first of A's two consecutive turns, while tiles at distance 5 were open.
   - Its burst (677) fell short of B's 765 hp, and B's stun then killed it (852 vs 632 hp).
   - Safety already prices one enemy turn, so the bid chose a lethal tile knowingly. The bid valued a kill it couldn't
     complete.
- Mirror stakes: 45 Prism-on-Prism kills of 100+ bags in 256 games. The victim's team lost 41.

## Principle
A hold or bid that keeps us inside an enemy's burst reach is worth it only if we can still leave, or the enemy dies,
before its strike lands. Both checks must look one window further:
- **Hold:** the payout is worth the bag only if, after it, a tile out of every visible enemy's next strike reach is
  reachable before that strike. The existing escape and step machinery can answer that.
- **Bid:** a kill bid on the first of our two turns should step onto a tile that safety rates lethal only if the bid
  completes the kill (its burst covers the target's hp) by the end of our second turn.

## What to build (bounded)
1. In `hold_outlasts` (find it; it's in combat or economy): when a visible enemy's burst could kill us at the hold
   tile in the window after the payout, keep holding only if an exit exists. An exit is a tile, reachable within
   our turns before that enemy's strike after payout, that lies outside its reach. Use the existing safety queries
   (lethal tiles, strike reach, escape plan); don't write a new simulator. If none exists, treat the hold as lost,
   which ref already handles (we leave now).
2. In `keep_bid` (bot.cc or combat): if the bid's step lands on a tile safety rates lethal for us, accept it only if
   the bid's own priced damage over our remaining consecutive turns kills the target. Otherwise drop the bid and let
   `retreat()` run.
3. Keep everything else. These checks only fire when a visible enemy threatens a lethal burst, so on most turns
   behaviour must be identical to the base.
4. No new tuned constants.

## Check
Trace `EXIT round handle kind(hold|bid) verdict` when either check changes the base's decision. Rerun game 185 with
the candidate as B, and the yin-yang game with the candidate as A, against ref, and report whether the Prism
survives (divergence elsewhere may change the game, so say so). Then play 1 more game. Audit and report as
common.md says.
