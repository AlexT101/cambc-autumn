# Ally seat commitment (`bots/variants/ast-seat`, 2026-11-02)

Built from astraeus e9c37971; judged against `bots/variants/astraeus-e9c3797`, both on their own drafts
(`--no-test-draft`), with fastrunner native. Suites: fresh-85100..85119 (main), fresh-85120..85139 (confirm).

## Result

| Variant | Win % | 95% CI | OOF cand / ref |
|---|---|---|---|
| seat-v1: commitments + seat planned at the top + soft seat holds | 46.6 | 45.6-47.6 | 81,883 / 77,739 (+5.3%) |
| v1 without seat planning (holds kept) | 48.8 | 47.9-49.8 | 78,291 / 77,727 |
| v1 without soft holds (top-seat planning kept) | 48.4 | 47.4-49.4 | 79,964 / 77,796 |
| v1 without either: hard commitments + deadline-first placement | 49.5 | 48.5-50.4 | 76,735 / 78,966 |
| "before": deadline offers, value placement, old pricing, nothing respected | 50.0 | 49.0-50.9 | 78,708 / 78,171 |
| **seat-v2 (shipped in the copy)**, main suites | **49.8** | 48.8-50.8 | 81,518 / 76,825 (+6.1%) |
| seat-v2, confirm suites | 49.1 | 48.1-50.0 | 77,321 / 75,387 (+2.6%) |

10,240 games each; the first five rows use the same main suites. v2 is level to slightly negative (49.45% over
20,480 games). It does what it was built to do: commitments now hold (below). It does not win games. Out-of-fuel
counts swing by thousands between runs of the same reference, so the +3-6% is not conclusive. The added work is
small: a mates list read once a turn, ranks of up to 5 allies, and a plain priority on band turns.

## Commitments hold (traces)

Each champion prints `PRI round handle priority` (what the engine orders next round by) and
`SEAT round handle planned natural chosen top top_without_assumed deadline committed hard seen_mask` in a
`debug_block`. A script rebuilds each team's real order for round R+1 from every ally's PRI lines and checks every
committed deadline. 48 games per variant, maps/gen 24 maps x both sides, against the baseline:

| Variant | Commitments | Broken (rank next round > deadline) |
|---|---|---|
| before (value placement, commitments only logged) | 7,222 (731 hard) | 973, 13.5% (hard 14, 1.9%) |
| v1 with the first packing (inserted values only) | 11,537 | 1,570, 13.6% |
| v1 with the commit band | 11,777 (702 hard) | 45, 0.38% (hard 3) |
| **v2** | 788 hard | **2, 0.25%** |

- The first v1 build inserted the committer between its neighbours' values. That holds between allies that see
  each other. It broke as often as no protocol, because an ally out of sight still ranks by value, against a
  priority it last read. Fix: committed priorities sit in their own band above every uncommitted one (below).
- With the band, the breaks left are visibility: of the allies above a broken committer in v1, 17 had acted
  earlier unseen by it, 11 acted later blind to it, and 18 saw it. The 18 are hard needs overriding soft holds, which
  the design allows. In v2, both breaks are visibility.
- Allies out of sight: `assumed` commitments (an ally last read last round, with that round's tag, is assumed to
  renew) set the top rank in 379 of 210,852 turns in v1 and 36 of 212,134 in v2. Each of those turns placed us
  lower than we would otherwise have gone.

## Why v1 lost: low-need allies moved earlier

The coordinator's hypothesis, from ast-measure's dead-last A/B (48.2%): a champion with nothing urgent gains by
acting late, since it sees enemy moves first. v1's traces fit it.

- **Soft holds**: in 5% of turns (11,246 of 210,852), a champion with no band need committed its seat because an
  enemy's two turns reached its end tile. In 69% of those (7,709), it took an earlier rank than its plain priority's.
  Removing holds alone gave 48.4, removing planning alone 48.8, and both 49.5, against v1's 46.6. Each costs about
  2 points.
- **Top-seat planning**: with an enemy in sight, the move was priced at the best rank the commitments allowed. In 18%
  of turns (35,886) that was earlier than the rank it then released to. The move was priced as acting earlier than
  it did.
- Packing among allies without needs (idle, danger, dead) is unchanged in both versions. Committed priorities sit
  above every uncommitted one, as band bids did before. In v2 a plain ally lands off its packed value in 4 of 212,134
  turns, only where an ally's commitment pushes it lower. Dead allies keep `dead_priority` above idle, as in the
  baseline (ast-measure's subject).

v2 therefore drops soft holds and prices the move at the **release seat**: where our plain priority puts us. Its
turn ends in one of two ways:

- **A band need** (kill, protect, heal, channel, escape) only moves it sooner. That never adds an enemy turn before
  ours, so the move stays priced conservatively.
- **No need**: it releases to the plain value, the seat it was priced at.

## Design (v2)

**Payload** (the priority's low 16 bits):

| Bits | Content |
|---|---|
| 0-7 | claim + 1 (comms) |
| 8 | support intent (support_mailbox) |
| 9-10 | round mod 4: written by the support pair, and by any commitment |
| 11 | commit |
| 12-14 | deadline: the worst team rank (0-7) at which the need is still met. Slack = deadline - the rank a reader computes. |
| 15 | hard (a life or a kill). 0 is reserved for seat holds and move promises; none are posted in v2. |

A commitment counts when its tag equals the round it was read in. That covers an ally that acted earlier this round
and is in sight. An ally yet to act shows last round's tag and is ignored, since it re-decides after us. An ally out
of sight is read with its last-read payload: if that read was last round and carried last round's tag, it is assumed
to renew.

**Priority values** (above the payload):

- Uncommitted priorities keep the baseline packing: `rank_code * 8 + 7 - index`.
- Committed ones are `commit_base + 2 * ((((7 - deadline) * 2 + hard) * 4 + value_bucket) * 8 + 7 - index)`, above
  every uncommitted value. Among committed allies, a tighter deadline goes first (EDF), then hard, then value
  (buckets < 450, < 900, < 1800, more). An ally that can't see us therefore still ranks below our commitment.
- `band_value` decodes a hard commitment's value from the bucket, for overrides.

**Placement** (`place`, `top_rank`):

- The allies other than us are sorted by next priority (`mates`, once a turn).
- `top_rank` is the best rank we can take without pushing a committed ally past its deadline. Each ally below us
  drops one rank, so only a committed ally sitting exactly at its deadline forbids going above it.
- A hard need may override a soft hold, or a hard commitment worth at most half its own value. Such an ally already
  moved on its seat.
- `place` takes the rank in [top, deadline] nearest the value's natural rank: EDF before value within what fits.
  When the natural value doesn't land there, it inserts just above or below a neighbour (×2 spacing leaves gaps).
- A need is offered only if its deadline is at least the top rank: there is a seat to take. Before, a need was
  offered only if the value-coded priority happened to reach it.

**Seat before the move** (`plan_seat`, called at the top of `play_turn`):

- want = max(rank of our last plain priority, top). `World::plan_next_priority` writes it into our `next_priority`
  and re-ranks the allies, so `World::slot`, `turns_before_ours` and the rest price at it until the next update.
- `set_turn_order` then sets a plain priority (no commitment) or a hard bid placed at or above it, with a
  commitment.

## What changed

- `model/turn_order.h`: payload constants. `plan_seat(World&)`. `set_turn_order` now takes `World&` (it probes our
  rank).
- `model/turn_order.cc`:
  - New: `natural_upper`, `commit_upper`, `band_value`, `Mates`/`mates`, `rank_of`, `top_rank`, `upper_at`,
    `place`, `deadline_before`, `keep_after` (probes our next rank through `turns_before_ours`, for the escape
    deadline), `plan_seat`.
  - `Wish` carries a deadline.
  - `offer_kills`, `offer_channel` and `offer_heal` (the worst rank at which the heal saves the ally) offer by
    deadline rank and `top_rank` instead of `can_act_before` at the value's priority. `offer_escape`'s deadline
    keeps the enemies whose second turn it denies after us.
  - `set_turn_order` places and commits. `publish_turn_order` ORs in the commitment, and traces PRI/SEAT.
  - `can_act_before` is kept (`[[maybe_unused]]`) for the merge.
- `model/world.h`: `plan_next_priority` and `next_rank_probe`.
- `bot.cc` `play_turn`: `plan_seat(world)` first.
- Enemy side untouched. `enemy_next_rank` and `next_slot(world, false, ...)` still give `their`; deadlines read it
  through `deadline_before`. ast-wc's changes to `can_act_before`'s enemy terms belong in `deadline_before`, and in
  `turns_before_ours` for `keep_after`.

## Next

- **Seat holds earned their keep nowhere**: a move priced at an early seat, then held, cost about 2 points.
  Revisit only for hard reliance (lethal at the release seat). That case is offer_escape already.
- **Visibility**: the remaining breaks are allies that can't see each other. The team's shared bytes reach every
  ally that acts later, whatever it sees. A shared-memory commitment slot (holder index, deadline, round parity: ~7
  bits) would close this, if a slot can be spared beside the camp record.
- **Round-boundary double seat** (not built): in a round the enemy starts, our last rank acts right before our rank
  0 of the next round. A champion that commits deadline = last this round and 0 next gets two turns in a row. It
  needs a second deadline field, or reusing the soft value of bit 15 as "boundary seat".
- **Move promises** (not built): bit 15 = 0 commitments with a promise kind (hold or leave a tile) would let a later
  ally price where we will be. The commit band's value bucket could carry the kind.
- The protocol is level: it should not ship on its own. It is the base for the two items above.
