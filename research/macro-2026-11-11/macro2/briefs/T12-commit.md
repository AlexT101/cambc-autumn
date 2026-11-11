# T12: farm targets change only on new information (candidate `bots/variants/macro2-commit`)

Read /home/ubuntu/wt/macro2/research/macro-2026-11-11/briefs/common.md first and follow it. Base: copy
`variants/ocean-ref-b7c87cf` to `variants/macro2-commit`.

## Evidence (256 debug ref-vs-ref games, 512 team-games; farm-waste analyst)
- 58% of turns are farm (F) turns, 2744 a team-game. About 40% of them end without our team capturing the group
  farmed. The biggest class is walks abandoned before arrival: 537 turns a team-game (19.6% of F).
- About 236 of those 537 are net waste. The other 301 still stepped toward the group reached next.
- What triggered the retargets, by first match on true information, per team-game:
  - another team or an ally cleared or damaged our target first: 90;
  - **the target respawned on schedule and we then dropped it: 73;**
  - the new target changed state: 108;
  - an enemy within 8 of the old target: 74;
  - ally claim changes: 93;
  - **no event at all: 88**, including 14 A→B→A flips.
- Example: game dir `29b4845f36f2cb4b` in /home/ubuntu/wt/macro2-an/dbg (gen-ladder-20000100070), Cassi id 7.
  - r947-973: she walks 42→5 toward a respawning group g5 (17 rounds left).
  - r974: she switches to g6, 55 away. Allies take both.
  - She then flips g6→g4→g7→g6 through r1040: about 95 F turns and no capture.
- Ocean's farm (economy/farm.cc) re-scores every turn: rate(worth, rounds), mid_exposure, claims, and the
  ordering kept from last turn. It already has near-tie hysteresis of some kind; find it.

## Principle
A plan should change only when the information behind it changes. Value a group's arrival as
max(walk, respawn left). While we walk toward the target, its arrival improves by one round per round, and every
other group's improves by at most one. So with no new information the ranking cannot turn against the target, and a
switch after a scheduled respawn or with no event is the model contradicting its own earlier choice. That happens
when the valuation isn't time-consistent: for example, a respawning group priced differently from a live one at the
same arrival time, or a term that jumps as the walk shrinks. Each such switch throws away the walk already made.

## What to build (bounded)
1. **Measure first.** Trace every farm-target change: `RETARGET round handle old new old_value new_value reason`,
   where reason names which input differed from the previous turn. Use the input classes the evidence lists, plus
   anything you find: group state, enemy seen near either group, an ally claim, our health or bag, fuel-gated
   ordering, and "none". Play 2-3 local games and count.
2. **Find why the no-event and scheduled-respawn switches happen.** The causes to look for are a time-inconsistent
   value term (respawning vs live priced differently at equal arrival, a discount that jumps, a reach or exposure
   term that changes with distance in a way the target's doesn't), or fuel-dependent ordering. Fix the root cause in
   the valuation if it is a clear inconsistency.
3. **Otherwise add commitment.** Keep the current target unless one of these happened since last turn:
   - a group's state changed (woken, cleared, captured, respawned early or late against its schedule);
   - an enemy was newly seen within reach of the target or of our path to it;
   - an ally's claim changed;
   - our health or bag crossed a threshold the code already uses (recall, bank or hurt);
   - the target became unreachable or invalid.
   Without one of these, keep it. Don't add a margin constant: the rule is "no new information, no change".
4. **Keep:** every branch other than the farm's target choice, the claims protocol, the draft, emblems and safety.
5. **No new tuned constants.**

## Check
Report the retarget counts by reason in base and candidate games (same maps and seats), and farm captures per game.
Audit and report as common.md says.
