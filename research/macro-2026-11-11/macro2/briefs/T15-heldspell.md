# T15: a ready spell stays ready (candidate `bots/variants/macro2-held`)

Read /home/ubuntu/wt/macro2/research/macro-2026-11-11/briefs/common.md first and follow it. Base: copy
`variants/macro2-combo` (`./copybot variants/macro2-combo variants/macro2-held`). Another implementer works on
`macro2-exits` (hold_outlasts and keep_bid). Don't touch those functions.

## Evidence
- The T9 implementer found a gap while diagnosing Prism duels: "the escape plan counts a held spell only on its
  first two ready turns (`model/escape.cc`), although a ready slot stays ready until cast."
- Rules: a slot cast in round t can be cast again in round t+8. A slot that is ready and not cast stays ready.
- macro2-duelm fixed a similar rule gap (two casts on a double turn) and was level over 25,600 games. It is part of
  the combo, our best at 50.53% of 51,200.

## Principle
The escape model should price an enemy's ready spell on every enemy turn of the window until it is cast, not only on
its first two ready turns. Either of two errors is wrong:
- treating a held spell as gone, which makes the model too optimistic about escapes;
- counting one spell twice, which makes it too pessimistic.
Each enemy turn allows one cast across both slots, and a slot once cast is gone for 8 rounds.

## What to build (bounded)
1. Read `model/escape.cc` (and whatever it calls for enemy damage per turn). Find exactly how a ready slot is
   counted over the turns of the escape window. Write down the current rule and the correct one in your report.
2. If the current rule is wrong, fix it to: each enemy turn in the window may cast one ready slot (the best one for
   damage, or the stun if it stops our escape). A cast slot is unavailable for 8 rounds after.
3. If the rule is right, or the gap is only in a case that can't happen within the window length, say so and stop.
   That is a valid result.
4. No new tuned constants. Leave everything else alone.

## Check
Trace `HELD round handle old_verdict new_verdict` when the escape verdict changes. Build, play 2-3 local games,
audit, and report as common.md says.
