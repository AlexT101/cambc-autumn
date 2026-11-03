# Following through on our own kill bids (`bots/variants/ast-follow*`, 2026-11-02)

The starting point is [comms.md](comms.md) "Our own unkept promise". A champion that wins a kill bid on an enemy that
has already acted gets a seat before that enemy next round. Sometimes it then doesn't strike that enemy at that turn,
even though its own blow alone would kill it.

This note covers why, the wider "hit nothing near a low enemy" gap, and a fix with no message: our own kill bid kept as
a promise to ourselves.

Every A/B here is against `bots/variants/astraeus-294` (= `bots/astraeus`), both bots on their own drafts
(`--no-test-draft`), on the fastrunner (native).

## Result

| Variant | Main: fresh-85800..85819 (10,240) | Confirm: fresh-85820..85839 (10,240) | Out-of-fuel turns, main / confirm | Paired vs ast-comms v1 (same games) |
|---|---|---|---|---|
| **v1 `ast-follow`**: keep our own kill bid (no message) | **50.3%** (49.4-51.3) | **50.2%** (49.3-51.2) | +0.7% / +3.1% | -0.21 (-0.76..+0.33) / +0.00 (-0.55..+0.55) |
| v2 `ast-follow-v2`: v1 + no kill bid while a tribute or teleport runs past our next turn | 50.3% | 50.3% | +0.6% / +3.1% | -0.22 / +0.08; vs v1 -0.01 (13 games differ) / +0.08 (26 differ) |
| k `ast-follow-k`: v1 + any affordable kill before the retreat | 50.3% | 50.2% | +2.2% / +4.2% | -0.26 / -0.03; vs v1 -0.05 (-0.53..+0.43) / -0.03 (-0.51..+0.45) |
| `ast-comms` v1, rerun on these games for the pairing | 50.6% | 50.2% | +2.0% / +4.5% | |

- **v1 is 50.3% of 20,480 games (about 49.6-51.0).** It is level with ast-comms v1 on the same games: -0.11
  points paired over both sets, so the message adds nothing measurable. This agrees with comms.md's ablation:
  "without readers" was level with v1 there.
- **It does what it should.** On the traced games (section 1), the bid target dies at the bound turn 84.8% of the
  time, against 77.2% before. Bound turns that don't hit a live target fall from 12.7% to 4.9% (0.34 to 0.13 a game).
  Deaths before our next turn on leave turns go from 3.0% to 4.0%.
- **But it barely moves the game.** Kills a game rose 5.38 -> 5.43 (±0.08) on the traced 2,048, deaths 6.26 -> 6.28.
  Expect about +0.16 kills a game from the misses fixed, at about 74% conversion (section 1). That is well under the
  ±1 point an A/B of 10k games resolves.
- **v2 and k add nothing.** v2's rule is logical and touches 0.1-0.3% of games. k's kills on leave turns (0.28 a game)
  are level and cost 1.1-1.5 points more out-of-fuel turns than v1.
- **Out-of-fuel turns:** no fuel gate is added. The extra work is one strike search on leave turns that carry a bid
  (0.39 a game). The confirm set's +3.1% is within what ast-comms showed (+1.8 to +4.5%) on the same reference.

## 1. Root causes (traced)

**Traced bot.** `bots/variants/ast-follow-meas` is astraeus 294 plus `debug_block` lines (SLOT, CREW, MONO,
CHASE-AVAIL and SRCH are off, for the stdout cap):
- `KB r me target need hp`: a kill bid won at our turn end on an enemy that had acted. `need` is our modelled blow
  after its `taken`.
- `FT ...`: at the next turn, which the bid binds:
  - the branch and `want_home`'s reason;
  - the target's health at our turn's start and end, its distance and our modelled strike;
  - whether our start tile was lethal;
  - for the strike search: per-enemy masks of kills and hits offered on unguarded and on guarded end tiles; the best
    killing plan's raw value and priced total against the chosen plan's; the chosen plan's kills; node count; failure.
- `LW ...`: each visible enemy under 25% health, off its spawn, within 4 at our turn's start (section 2).

It played 2,048 games against REF on fresh-85856..85859 and won 49.8%. The traced v1, `ast-follow-v1meas`, played the
same games (49.9%).

**Scripts.**
- `scripts/follow_trace.py --ex EXTRACT_DIR RUN` makes the tables.
- `scripts/follow_leave.py` gives deaths after leave-branch bound turns.
- `scripts/follow_after.py` gives what became of targets we didn't hit.

**Read hits from the replay.** The trace's end-of-turn health read missed about 200 of our kills (the target read
unchanged), so hits and kills are read from the extracted replay. Run `extract.mjs --out DIR` on the batches, and key
replays by batch and file: two runs on the same suites share file names. Bids aren't affected: 12 of 7,319 named an
enemy already dead by our turn's end, all killed by others.

### What happens at the bound turn

| Bound turns, our blow alone enough (2,048 games) | astraeus 294 (6,061) | v1 (5,885) |
|---|---|---|
| killed the target | **77.2%** | **84.8%** |
| hit it, short | 1.0% | 0.6% |
| **did not hit it** | **11.6%** (12.7% of live targets; 0.34 a game) | **4.5%** (4.9%; 0.13 a game) |
| target dead before our turn | 8.2% | 8.4% |
| we were stunned | 1.4% | 1.3% |
| the target acted before us (seat lost) | 0.4% | 0.3% |

**Turn order, stuns and movement are not the cause.**
- The seat holds 99.6% of the time.
- A stun takes 1.4% of bound turns.
- The target already acted, so it hasn't moved since the bid.

The misses split into four causes plus small branches.

| Not hit (704 in base) | share | what happened |
|---|---|---|
| Leave branch: `want_home` -> `retreat()` | 33.5% | low (recall line) 78, stand lost while pursued 70, stand lost 42, linked pair 19, pack zone 17, lethal tile 7, Willow 3 |
| Strike search chose another plan | 28.0% | a kill of the target offered on an allowed tile in 197 of them |
| Tribute kept (branch T) | 18.9% | Prism 113, Marcella 15 |
| Search found no plan reaching it | 8.2% | walls, sight or range |
| Other branches: recall kept to bank or shop (k) 41, hold (P) 13, game-ender stop (E) 12, capture recall (Q) 8, rest 6 | 11.4% | |

**Leave branch.**
- The kill was possible by distance in 99% of cases. Our start tile was lethal in 13%.
- Our health averaged 0.53 of max, with the recall line at 0.35: "low" is a minority. Most leaves come from
  `Safety::stand` losing.
- The target was 4 away in 46% and 2 away in 35%.
- **Why retreat misses it:** `retreat()` takes only `sure_kill` (one basic attack from here) and `step_to_kill` (a
  step or dash, then one basic attack, where only the victim reaches us). The bid's blow is the whole turn's Strike: a
  walk, a reset and a second attack, a cast. Of all leave-branch bound turns, retreat's own kills took 63%.
- **Safe and possible, by our own Safety:**
  - v1 runs the strike search behind the step guard, offering only plans that keep the bid. It found one in 95.7% of
    3,999 such turns (0.39 a game, v1's main run).
  - On the traced games, leave-branch bound turns killed the target 95.0% of the time (base 63.3%).
  - Deaths before our next turn went 3.0% -> 4.0%: 5 more deaths (20 -> 25) for 176 more kills (417 -> 593), over
    2,048 games.

**The search preferred another plan.**
- The best kill of the target was worth 729 raw against the chosen plan's 1,090, and 705 priced against 1,043.
- The chosen plan hit another enemy in 73% of cases and killed another in 22.5%.
- By champion: Marcella 122 (her reset's stunning attack and her cast), Vesper 58, Heart of Ruin 34.
- **The mechanism is `hit_worth`.** It is the fall in `kill_distance`, by design the same summed in any order, so
  killing a target left at h is worth only `kill_distance(h)`. A large chunk (or a stun) on a healthier enemy
  out-values it. The value ignores that damage short of a kill decays: the target we held a seat to kill acts next,
  and 74% of targets left alive are still alive three rounds later (below).

**Tribute kept.**
- Prism tributes big bags: channels 36-105 turns.
- `continue_tribute` keeps a safe tribute, so the turn the bid took a seat for is the channel's.
- A cancel would throw away tens of turns of channel, so the bid is the error. v2 drops kill bids while a tribute or
  teleport runs past our next turn's start. That is rule-derived but changes almost no games.

**No plan reaches it.** `offer_kills` bids on Strike, which is crow-flies by distance. Walls, bushes and sight make 8%
of the misses unplayable. These are wasted seats, not lost kills.

**By champion** (misses / bound turns with the target alive at our turn):

| | Marcella | Prism | Heart of Ruin | Vesper | Vendetta | Cassi | Issac |
|---|---|---|---|---|---|---|---|
| base | 12% of 1,858 | 32% of 403 | 15% of 786 | 12% of 879 | 8% of 839 | 8% of 332 | 10% of 223 |
| v1 | 2% | 20% | 6% | 5% | 3% | 1% | 6% |

Marcella is 32% of base misses, Prism 18% (tributes), Heart of Ruin 16%, Vesper 15%.

**By round:** 1-300 9%, 301-800 44%, 801-1400 31%, 1401+ 16%. That is the mid game, where most fights are.

**What became of targets we didn't hit** (base, 695):
- 73.7% were alive three rounds later.
- 14.6% were killed later by the same champion.
- 11.2% were killed by an ally.

So an unkept bid mostly loses the kill rather than delaying it.

**After v1** (263 misses left):
- Tribute kept: 86 (Prism 66).
- No plan reaches it: 72.
- Recall kept to bank or shop: 39.
- Leave with no keeping plan: 26.
- Hold: 14.

## 2. The wider gap: our champions near a low enemy (LW lines, base, 61,466 champion-turns, 30 a game)

Each record is one of our champion's turns starting within 4 of a visible enemy under 25% health, off its spawn.
Hits are read from the replay. The same episode spans several turns.

| Class | share | our modelled strike kills it |
|---|---|---|
| hit it | 40.3% | 7,263 |
| **couldn't reach** (modelled one-turn strike 0 at that distance) | **29.6%** | 37 |
| couldn't reach (no legal plan: walls, sight) | 3.7% | 612 |
| hit another (2,550 of 3,046 could not reach it) | 5.0% | 267 |
| **retreated** | **19.8%** | 676 |
| reachable, chose no hit on it | 0.6% | 109 |
| channel (tribute, recall) | 0.9% | 95 |

- **"Hit nothing at all" is 52% of these turns.** The replay measure (36% of hunters within 4 at a round's end) counts
  differently; the split is what matters.
- **About two-thirds of the non-hitting is reach.** That is 37% of all records (29.6 + 3.7 + 4.1 another-target with
  no plan): the low enemy is beyond this turn's walk, dash and attack. Fixing it is approach and positioning, not the
  turn's choice.
- **Retreats are 20%, and our own Safety ordered every one.** By reason:
  - low (recall line) 39%;
  - stand lost 42% (pursued 2,039, plain 1,744, linked pair 997, lethal tile 265);
  - a linked pair's body falling 10% (1,203), or ours on a lethal tile (28);
  - pack zone 8% (918);
  - Willow 214;
  - camps 53.

  The start tile was lethal in 9%. Only 676 of the retreats (5.6%) had our modelled strike kill the low enemy. That
  is the part a kill-before-retreat could take. Variant k takes it (0.28 kill plans a game on leave turns), and it is
  level.
- **Fixable at the turn by a choice:** about 1,150 records (1.9%; ~0.56 a game). Those are retreats with a modelled
  kill, reachable non-hits with one, and channels with one. v1 takes the bid-target subset.
- **The rest is approach or Safety's verdict.** The rest of the gap to Fish and PBG lies in reaching low enemies
  (approach and cohesion, TODO "Chase persistence") and in how often `Safety::stand` loses. It is not in the turn's
  choice of target.

## 3. The fix (`bots/variants/ast-follow`, v1)

**Files:**
- `model/follow.h` (new);
- `model/turn_order.cc` (`Wish` carries the kill offer's target and blow; `set_turn_order` keeps the winning one on an
  acted enemy as `follow::own`);
- `combat/plan.{h,cc}`;
- `bot.cc`.

**The rule.** A kill bid on an enemy that has acted holds a seat before it, so that our next turn strikes it:
- **The strike search:** a plan that leaves the bound target above `health at the turn's first search - 0.9 x our
  blow` loses `break_penalty` (1e5). That ranks every keeping plan first. With none, the choice is as before.
  "Impossible or fatal" stays with the search:
  - the step guard's tiles;
  - `lethal` far tiles;
  - retaliation that kills us.
- **The leave branch:** `keep_bid` runs the search behind the step guard with only keeping plans, then `retreat()`
  takes what is left.
- **No message and no payload change.** This is ast-comms v1's keeping without the pledge in the priority.

**v2** adds one rule in `bid()` (`turn_order.cc`): no kill bid while a tribute or teleport channel runs past our next
turn's start. That turn is the channel's.

**k** adds this to the leave branch, when no bid binds and a visible enemy off its spawn is within our Strike's kill:
- a kill-only search (any foe killed);
- each end tile must be one no surviving enemy or camp reaches, unless the walk is still unspent for the retreat.

That is retreat's own rule for a ranged kill.

## Verdict and next

- **Ship candidate:** v1 (`bots/variants/ast-follow`), if the promise is wanted without ast-comms's payload layout.
  - It is the simplest form of comms.md's finding.
  - It is level with ast-comms on the same 20,480 games, and ~50.3% against 294.
  - It is logical, and the trace shows it keeps the promise (unkept bound turns 12.7% -> 4.9%).
  - Within noise, it is not a measurable win.
- **v2's rule** can ride along. It is logical, touches ~0.2% of games and is level.
- **Don't retry without a new mechanism:**
  - kills before every retreat (k, level, more fuel);
  - cancelling a tribute for a bid (the tributes are Prism's long channels).
- **Where a gain would be:**
  - **Reach (37% of non-hitting turns near a low enemy):** approach and cohesion, not the turn.
  - **`hit_worth`'s order-free value:** it values chip damage on a healthier enemy at par with a kill now, though
    74% of targets left alive escape. A kill-now term derived from that escape rate would change every search, not
    only bound turns. It needs its own A/B.
  - **Bids on Strike's crow-flies reach:** 8% of misses had no legal plan. Checking `legal` at bid time would stop
    wasted seats.
