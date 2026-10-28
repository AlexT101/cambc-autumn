# Audit: comms (`bots/astraeus/src/model/comms.cc`, `comms.h`)

## Changed

Commit `f1860021` "astraeus audit (comms): cleanup". Bench replays are **byte-identical** (8/8 on 00ambush, 00lanes, 01hooks, 00interlock with `--test-draft`). Total fuel 2,211,802,776 -> 2,210,495,400 (-0.06%); mean turn 50161 -> 50131.

- `expect()` and `receive()` decoded the two sighting slots with duplicated code. They now share `each_fresh_sighting(L, bits, fresh, f)`, which calls `f(slot, sighting, round)` for each changed slot, first slot first, so the precedence of `note_sighting` stays the same.
- Added `health_share(sevenths)`, which replaces the health decode that was written out twice.
- Added `decode_capture(L, record)`, which pulls the residue arithmetic for the camp record out of `receive()`.
- `receive()` now resets the urgencies (round, known, count, first, second) at its start. The defensive reset in `send()` is gone: `send()` returns unless `receive()` ran this round, and `receive()` now resets before anything that could throw.
- Merged the second-slot conditions in `send()`. `second_free`, its mid-loop mutation and `second_replaceable` became one condition: `L.second && camp_free && !posted_camp`, then `!second_taken || replaces(...)`. This is equivalent, and the observe gate keeps its own pre-camp condition.
- `send()` uses `L.team` for the team size (the same value).
- `urgency_of` and `urgency` use the `U` alias throughout.
- Removed the redundant null check in `receive_support()` (the early return already covers it).
- Comments:
  - Dropped the write-count note that was duplicated in the layout block.
  - Fixed the order of the bit-budget comment (claim comes before camp) and noted that the bag's 10 bits assume 6 allies.
  - Dropped "static storage starts zeroed for free".
  - The header now says what `support_request` and `support_available` mean (the other endpoint's intent, posted within two rounds and read while it was seen) instead of "Dated local intent only".
  - `bag_of` now documents the 508 cap.

## Considered, not changed

- **Caching `expect()`'s shared-memory read for `receive()`.** It would save one raw host call (tens of fuel) a turn. It would need a round guard for the stale-resume path. Not worth the extra state.
- **The `[[gnu::noinline]] lay_out` and the lazy `layout()`.** These are fine as they are: the layout is built once a game.
- **Skipping the second slot's enemy when choosing the first slot.** If a teammate's this-round second sighting holds enemy A, our first-slot choice can post A again, which wastes a slot. But our sighting of A may be fresher (an enemy turn can fall between). It's a judgement call, so it's under Suggestions.
- **`urgency()` ignores teammates' wards and walls.** It overestimates urgency, which is conservative. The comment already explains the fuel reason.

## Suggestions

1. **The priority payload (claim plus support intent) is lost whenever an ally's raw turn rank is 0.** `turn_order.cc:97` `packed_priority` returns 0 for raw 0, and `comms.cc` `payload_of` reads priority 0 as "no payload".
   - Raw 0 is a normal value. `idle_priority` is `role + 8 - 8*bucket`, so a champion with role 0 and 10-20% health missing, or role 8 and 20-30% missing, publishes no claim and no support intent.
   - For Willow/Prism pairs, `support_mailbox` then sees no payload and the intent lapses after two rounds.
   - Fix (turn_order.cc): encode raw 0 as `(7 - index) << 16 | payload`. Ordering looks preserved: rank_code(0) - rank_code(0) = 0 gives a rank of 7 - index, which is below raw 1's (rank_code(1) - rank_code(0)) * 8 + ... ≥ 8, and above every negative raw.
   - Check why raw 0 was pinned to 0 ("bots read a champion they have not seen as priority 0") before changing it. Turn order changes, so it needs an A/B.
   - Severity: medium. Effort: small.
2. **A capture record can be overwritten before a teammate reads it when turn order changes.** `send()` treats only records that are fresh *to us* as protected (`camp_free`).
   - Say P posts in round r and teammate T acted before P in round r. If P (or someone who read it) acts before T in round r+1, the slot can be reused for another capture or a second sighting.
   - T then never learns of the capture, because `told_respawn` stops anyone re-posting it.
   - Claims and bags have reminders for this; captures don't.
   - Exact fix: keep a record you wrote, or read, in round r-1 protected in round r while some teammate's `prev_rank` was before the writer's and its `rank` is after ours. Cheaper alternative: let the poster re-post once in its next turn.
   - Severity: low-medium (only when priorities reorder). Effort: small.
3. **The second sighting slot disappears on large maps with big teams.** Examples: 100x100 with 5 enemies and ~60 groups needs 42 + 24 = 66 bits, which is over 64, so `L.second` is false.
   - Options:
     - Drop the second slot's own 3-bit write count. Its parity plus a rotated enemy usually changes the bits anyway.
     - Quantise health to quarters (2 bits).
     - Share one write count across both slots.
   - Each option saves 1-3 bits, which is enough for 100x100 with 5 enemies at moderate group counts.
   - Severity: low-medium (big ladder maps are where scouting matters most). Effort: small, but the layout is a wire format, so every instance must change together, which is automatic since all run the same bot.
4. **Sightings carry no channel state and no shield.**
   - `sight_value` posts health without the shield (Varg, Heart of Ruin), so receivers underestimate effective health.
   - No bit says the enemy is tributing or recalling, though a tributing enemy at an altar is the highest-value interrupt. On maps with spare bits, a 1-bit "channelling" flag would fit.
   - Severity: low-medium. Effort: small for the bit, more for the receivers to use it.
5. **A same-enemy sighting is never replaced within a round** (`send()` `replaces`: `index != e.index`). An enemy turn can fall between the teammate's turn and ours. If our position for that enemy differs, ours is strictly newer, but receivers date both "from the round's start" (`World::note_sighting`), and the first written wins.
   - Allow replacement when the position differs and our urgency is no worse. Related: the first-slot choice could skip an enemy already in this round's second slot when the positions match.
   - Severity: low. Effort: small.
6. **The mates cache is from the turn start.** `urgency()` builds `U.mates`, including `visible`, at `receive()`. After `send()`'s observe, we may see a mate we didn't before, so urgency stays slightly high (conservative). Low severity.
7. **`refresh` in `main.cc` is an existing fuel gate.** It reads `moved && fuel_ok(end_reserve)` and otherwise notes `comms-stale-vision`.
   - The observe is needed only to post sightings of enemies our move revealed.
   - A bounded alternative: read only the enemy champions' raw `in_sight` and `champion info` (~12-20 fuel each, ≤6 enemies) instead of a full `observe()`. That makes it cheap enough to drop the gate.
   - Severity: low. Effort: medium (World API).
8. **`endpoints()` duplicates `combat/support.cc:123`'s search for the healer and protected mate.** A shared `support_pair(world)` in world.h or map_economy.h would keep them from diverging. Low severity, small effort.
9. **Bags are clamped at 127 fours (508 gems).** Receivers then underestimate an ally carrying more, for example after a monolith (200 gems) plus kills. This is rare, and one more bit fixes it where there's room. Low severity.
