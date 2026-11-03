# Ally-to-ally messages: strike pledges (`bots/variants/ast-comms`, 2026-11-02)

Built from astraeus at CHANGES 294. Judged against its frozen copy `bots/variants/astraeus-294`, both on their own
drafts (`--no-test-draft`), using fastrunner native.

## Result

| Variant | Win % (10,240) | 95% CI | OOF cand / ref | Paired vs v1 |
|---|---|---|---|---|
| **v1: pledges, kept as a constraint, readers** (main, fresh-85600..85619) | **50.8** | 49.8-51.7 | 96,023 / 95,317 (+0.7%) | |
| **v1 confirm** (fresh-85620..85639) | **50.8** | 49.8-51.8 | 103,503 / 101,665 (+1.8%) | |
| v1 without readers (no follow-up credit, no side_damage change) | 50.8 | 49.8-51.7 | 96,288 / 95,517 | +0.00 (-0.19..+0.19); 102 games differ |
| v1 without keeping on the leave branch | 50.4 | 49.4-51.3 | 96,643 / 95,984 | +0.42 (+0.02..+0.82) |
| v1 without keeping at all (layout + readers only) | 50.2 | 49.3-51.2 | 97,040 / 96,175 | +0.55 (+0.08..+1.02) |
| v2: v1 + pledges on targets yet to act | 50.7 | 49.8-51.7 | 96,326 / 95,594 | -0.04 (-0.29..+0.21) |
| v3: v1 + a boundary double-seat bid | 49.2 | 48.2-50.2 | 95,756 / 94,838 | **-1.57 (-2.64..-0.50)** |

- **v1 is 50.8% of 20,480 games (~50.1-51.5).** It is small but consistent on both suite sets. Out-of-fuel turns
  are +0.7% and +1.8%.
- **The gain is the promise, not the message.** Keeping our own pledge is worth about +0.5 (paired), and most of
  that comes from the leave branch. Readers change 102 games in 10,240 and are worth nothing measurable. The
  messages are posted and read correctly, but they are too rare to matter (1.3 reads a game).
- **The payload layout costs nothing.** "v1 without keeping" carries the new layout and the readers, and it is level.
- **The double-seat bid loses.** It ranks a champion with a hittable enemy, but no kill, first next round. That
  moves low-need allies earlier, which CHANGES 293 and the seat v1 loss already showed costs points. A kill-worthy
  double is already a kill bid.

## 1. Measurement (before building)

**Traced bot.** `bots/variants/ast-comms-meas` is astraeus 294 plus two lines in `turn_order.cc`, both in
`debug_block` (SRCH lines are off):
- `SD`: in `offer_kills`, one per enemy we could hit next turn. It gives our blow, the enemy's slot, our seat, and
  each visible ally's `now` / `next` term and assumed damage.
- `TO`: the turn's band bid and the target of the winning kill offer.

It played 2,048 games against REF on fresh-85656..85659 (50.4%). The scripts are `scripts/comms_sd.py` (traced)
and `scripts/comms_replay.py` (replays only, self-play `replays/meas-ex` and 9,510 ladder games).

### How wrong `side_damage`'s ally assumption is

- **Allies counted in `side_damage`:**
  - Allies counted to hit the target later this round did so 15.6% of the time.
  - Allies counted to hit it next round did so 20.8% of the time, and acted after the target in 2.4%.
  - Over all counted ally terms, actual damage was 0.43 of the assumed.
- **Kill bids rarely rest on allies.** Of 6.6 offered kill bids a game, 5.85 kill with our own blow alone. Only 0.79
  need allies. Those convert 55.9%, and 20.1% of them fail because the allies came up short.
- **Exact pledges in the bids** (oracle: allies' actual damage in place of the assumed):
  - 0.36 bids a game would not have been made. Their target died 18.5% of the time.
  - 0.01 bids a game would have been added.
  - Upper bound on kills from exact ally damage in bids: **~0.16 a game** (the "allies short" bids, all
    converted).

### Why kill bids that win the seat convert only ~59%

The split is by whether the target had acted that round. The other column means it acts after us this round.

| Winning K bids (6.2 a game) | target acted (7,926) | target yet to act (4,802) |
|---|---|---|
| target died before its next turn | **79.9%** | 24.7% |
| we acted first but did not hit it | 9.6% | **65.6%** |
| no turn (dead, stunned) | 4.7% | 5.6% |
| we hit short | 4.9% | 3.3% |

- **A target that has yet to act walks away before our next turn.** That accounts for most of the 48% "acted first,
  still failed" in measure.md. A pledge can't fix it (v2: level).
- **Our own unkept promise.** On targets that had acted, the bidder still did not hit its target 9.6% of the time,
  0.37 a game, with its blow alone enough to kill.
  - 42% of these were the leave branch: `want_home` sends the turn to `retreat()`, which never runs the strike
    search.
  - Most of the rest ran the search and hit another enemy (46% hit another).
  - Marcella is 36% of the cases, Vesper 17%, Heart of Ruin 17%.
  - This is the largest addressable gap, and it is a promise to ourselves.

### What the replays say (`comms_replay.py`, 4,268 self-play games, ladder for comparison)

- **Hunters not hitting is the main loss.** In intervals where an enemy at or under 25% health, off its spawn, has a
  hunter of ours within 4:
  - 36% of our engaged hunters hit nothing; Fish and PBG 26-27%.
  - Damage on the target is 27 an interval against their 47-49.
  - Our hunters walk away 13% of the time against their 7%.
- **Split focus is small.** Missed focus kills (another hunter's damage on Y would have killed X, and Y also
  survived) are 0.23 a game, about 4% of kills (ladder 0.19). We split hitters less than the ladder (33% vs 38%).
- **Unneeded hits almost never cost a kill.** 0.012 a kill had another target in range.
- **Stuns are not wasted.** 1.3% of stun targets were already stunned (ladder 1.3%). Cassi wastes none. Two hunters
  stunning the same target before its turn: 1.6% of stun windows. **Stun claims have no upside.**
- **Doubles.** With a hunter holding two turns in a row, we kill 36% against Fish's 56% and PBG's 58%. Single turns
  are level (22%). The gap is in what the double does, not in who holds it (v3 below).

### Upper bound before building

- Pledges read by allies: at most ~0.16 kills a game in bids, plus some of the 0.23 missed-focus kills a game.
- Keeping our own kill bids on acted targets: up to 0.37 kills a game.
- Against ~5.2-6 kills a game, that is a ceiling of roughly 5-10% more kills, mostly from the sender's own promise.

## 2. Payload layout

The priority's low 22 bits (was 16). Above them sit the order code and `7 - index`.

| Bits | Content |
|---|---|
| 0-7 | claim + 1 (comms.cc, unchanged) |
| 8 | support intent (support_mailbox.h, unchanged) |
| 9-10 | round mod 4 of the turn end that set it. Written by the support pair and by a pledger, the same value. |
| 11-15 | seat commitment, reserved with seat.md's layout: commit, deadline x3, hard |
| 16-18 | pledge: the enemy's index + 1 (0 for none) |
| 19 | the pledge stuns (reserved: no reader, since duplicate stuns are 1.3%) |
| 20 | boundary double seat (v3 writes it; v1 leaves it 0) |
| 21 | reserved |

**The order code.** It is 10 bits with the sign (-88..351).
- Idle, dead and danger keep exact codes, so allies with no band need order exactly as today.
- Each band's value is quantized to 10 levels, with bounds 100, 150, 225, 300, 450, 600, 900, 1350 and 2000. Band
  bids still outrank everything else, and protect stays below kill.
- Only the order among band bidders with close values changes: they tie by index instead.
- 160 codes are left above the kill band for seat.md's commit band. That needs the band repacked as
  ((7 - deadline) x 2 + hard) x 8 + 7 - index, which is 128 values.
- "v1 without keeping" (layout + readers) is level, so the quantization costs nothing measurable.

**Reading a pledge** (`pledge::of`). A pledge is read from an ally in sight, from a priority read this round. Which
turn it binds depends on its round tag:
- Tag = this round: the ally has acted, so the pledge binds its turn next round.
- Tag = last round and the ally has not acted: it binds the ally's turn this round.
- Anything else is ignored. The tag is needed because a priority set at our turn end is read the same round by
  allies after us and next round by allies before us.

## 3. Implementation (`bots/variants/ast-comms`)

Files: `model/pledge.h` (new), `model/turn_order.{h,cc}`, `combat/plan.{h,cc}`, `bot.cc`.

**Sender** (`set_turn_order` / `publish_turn_order`)
- When the winning bid is a kill offer on an enemy that has acted this round, we post `{target, round, need}`.
  `need` is our blow after the target's `taken`.
- It binds our turn next round, where we act before the target.

**Keeping it** (`plan.cc`). A pledge binds the next turn's strike search.
- Plans that leave the target above `health at the first search - 0.9 x need` lose `pledge_penalty` (1e5). That
  ranks every keeping plan first.
- "Impossible or fatal" stays with the search: tiles the step guard excludes or `safety.lethal` refuses, and blows
  whose retaliation kills us, are never offered.
- With no keeping plan, the choice is as before.
- On the leave branch (`want_home`), `keep_pledge` runs the search behind the step guard, offering only keeping
  plans. Then `retreat()` takes what is left.
- The search after the goal's walk measures from the first search's health, so a pledge is never charged twice.

**Readers**
- `side_damage`: an ally whose pledge binds the counted turn to a different enemy is not counted for this one.
- Strike search: each foe gets `follow`, the summed blows of visible allies whose pledge on it lands after our turn
  and before the enemy's next turn. A hit leaving it at no more than `follow` is worth the kill (`Search::worth`).
- Neither reader changes a measurable number of games.

**Traces** (`debug_block`)
- `PG round self target need`: a pledge posted.
- `PS round self target keepable pledge_only chosen`: a search under a pledge.
- `PR round self pledger target turn_offset before follow`: a reader used a pledge.
- `scripts/comms_pledge.py` reads them against the replay.

## 4. Traces: are pledges kept and read?

The source is v1's own A/B games, fresh-85600..85603: 2,048 games, replays in `replays/comms-v1-ex`.

| | v1 | baseline (traced 294, winning K bids on acted targets) |
|---|---|---|
| pledges / kill bids a game | 3.45 | 3.9 |
| kept: hit for >= 90% of the promise, or killed it | **92.4%** of those whose target lived to our turn | 80.9% |
| not hit at all | 2.7% | 10.1% |
| no turn (dead, stunned) | 3.8% | 4.9% |
| target dead by the end of the next round | 89.4% | 79.9% (before its next turn) |
| kills a game, CAND / REF | 5.63 / 5.47 | 5.96 / 5.92 (traced build vs REF) |

- **Searches under a pledge:** 97.8% offered a keeping plan.
- **The leave branch:** 787 pledge-only searches; 765 of them could keep the pledge.
- **Reads:** 2,596 (1.27 a game), 2,305 of them landing before the target. In those:
  - the pledger hit 83.8% of the time;
  - the reader hit the target 68.3%;
  - the target died 88.3%.
- **Breaks left:** the target dead before our turn (11.7%, not a break), no turn (3.8%), and 2.7% not hit, where
  no plan could keep the pledge.

## 5. Fuel

- No fuel gate is added.
- Extra work:
  - a pass over the allies' payloads in `Search::read` (a few hundred fuel with an ally in sight);
  - the pledged-unit check in `offer`;
  - one strike search on leave turns that carry a pledge (~0.4 a game).
- Out-of-fuel turns rose 0.7% (main) and 1.8% (confirm). Runs of the same reference swing by about that much.

## Verdict and next

- **Ship candidate:** v1, at 50.8% of 20,480 games.
- **Simpler alternative:** most of the value would come from keeping our own kill bid's promise (the penalty plus
  `keep_pledge`) with no payload at all. It was not built as its own variant: "v1 without readers" plays it with the
  messages still posted. If the layout is unwanted, that variant is the one to merge.
- **Readers stay level until pledges are common.** Pledges are posted only by kill bidders. A wider pledge, any
  champion promising its next hit on a low enemy it will reach, would also constrain non-bidders. The 36% of
  engaged hunters who hit nothing is the gap it would aim at. That is a change to engagement, not a message.
- **Don't repeat without a new mechanism:**
  - stun claims (no waste to remove);
  - pledges on targets yet to act (v2, level);
  - a boundary double-seat bid without a kill (v3, -1.6).
