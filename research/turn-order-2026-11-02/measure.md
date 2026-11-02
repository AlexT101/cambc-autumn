# Turn-order measurements (2026-11-02)

Where turn-order coordination loses games in astraeus at e9c37971, to steer `ast-wc` (worst-case enemy order) and
`ast-seat` (ally seat commitment). The enemy order is assumed adversarial throughout, as the user directs.

## Method

- **Bot.** `bots/variants/ast-measure` is astraeus at e9c37971 plus `debug_block` trace lines, in a debug build.
  None of them changes a decision. To fit under the 1 MiB stdout cap, the `SLOT` line and `debug_search` are off.
  The lines are:
  - `TO` at the end of `set_turn_order`. It gives the winning bid and its kind (K kill, X/T/R/P cancel an enemy
    channel, C our channel, E escape, H heal), the rank and slot we assumed for next round, the target and its
    assumed slot, the enemies the bid must precede with their assumed slots, and each ally's code as read (with
    read-this-round, acted and visible flags).
  - `TB` at `act()` start. It gives `world.slot` for us and for each visible enemy within 8 next round, and
    `turns_before_ours`.
  - `KL` in `offer_kills`. For each enemy we can hit, it gives side damage at the worst-case and the read enemy
    slot.
  - `PL` in `Search::read`. It lists foes that a walk or dash could hit only from a tile an ally holds
    (`free_n_at` / `land_here_at` with the ally tiles opened).
  - `MW` in `make_way`.
- **Games.** ast-measure played the frozen `variants/astraeus-e9c3797` (both bots on their own drafts, test_draft
  off) on the ladder maps (172 games) and on fresh suites `maps/fresh-85220` to `85227` (4096 games). That makes
  4268 games, both sides, on the fastrunner (native). ast-measure won 50.5%, so the tracing changes nothing that
  matters. Batches are `replays/meas-{ladder,85220..85227}`, extracted to `replays/meas-ex`.
- **Ladder.** 9510 distinct ladder replays from 2026-10-29 to 2026-10-31 (all teams), extracted to
  `replays/meas-ladder-ex`.
- **Real order.** The real order comes from the replays' `prio`: round r's order sorts each team by the `prio` at
  the end of round r-1, then id. This reproduced all 110,222 actor-event `t` indices checked. The stdout cap cut
  the last rounds of 33 games, so trace metrics use only the rounds before the last printed line (99.8% of rounds).
- **Scripts** (in `scripts/`):
  - `tolib.py`: loaders and order.
  - `traced.py`: metrics 1, 2b, 4 and 5 from the traces.
  - `replay_only.py`: metrics 2, 3 and 6 from replays.
  - `summarize.py`: the tables.
- **Running them:**
  `python3 scripts/traced.py replays/meas-ex T.pkl; python3 scripts/replay_only.py replays/meas-ex O.pkl;
  python3 scripts/replay_only.py replays/meas-ladder-ex L.pkl; python3 scripts/summarize.py T.pkl O.pkl L.pkl`.
- **Definitions.** "In contact" means within 4 (Chebyshev) of a live enemy at the end of the round. Rates are
  per event. Games are clustered (map pairs), so treat small differences (under ~1 point on samples this size)
  as noise.

## 1. Bid outcomes (traced, 15.4 band bids a game)

| kind | bids | per game | assumed first | acted first | goal met | met if first | met if not |
|---|---|---|---|---|---|---|---|
| E escape | 40266 | 9.4 | 35.5% | 58.6% | 56.9% (alive end of r+1) | 66.1% | 43.8% |
| K kill | 23976 | 5.6 | 100% | 96.2% | 52.7% (target died in r+1) | 52.0% | 69.6% |
| R cancel recall | 903 | 0.2 | 100% | 99.3% | 60.2% | 60.2% | - |
| C own channel | 367 | 0.1 | 100% | 98.9% | 99.7% | 100% | - |
| T cancel tribute | 198 | 0.05 | 100% | 97.5% | 60.1% | 60.6% | - |
| H heal | 157 | 0.04 | 80.3% | 75.2% | 84.7% | 84.7% | 84.6% |

- **Failed "act first" is rare.** Of the 39,859 bids that assumed acting first, 1213 (3.0%, 0.28 a game) acted
  after an enemy they needed to precede. By cause (first match in this order):

  | cause | bids | share | by bid kind |
  |---|---|---|---|
  | pushed down by an ally that chose later this round | 1082 | 89.2% | K 842, E 219, H 11, T 4, R 4, C 2 |
  | pushed down by an ally out of sight (stale read) | 107 | 8.8% | K 65, E 40 |
  | an enemy reordered | 12 | 1.0% | K 4, E 4, R 2, T 1, C 1 |
  | other (ally read and acted earlier) | 12 | 1.0% | |

  The later ally's own bid was a kill in 967 of the 1082 cases, an escape in 140, and plain or danger in 33. So
  the kill band outranking everything is the whole of the commitment failure: a later kill bid pushes an earlier
  teammate's kill (842) or escape (219) below its enemy. The enemy-reorder cause is near zero. That is because
  `enemy_next_rank` already puts every unsettled enemy at rank 0 once its team has been seen changing (always,
  against astraeus).
- **The goal rate is not lower when the seat fails.** Kill bids that held their seat met the goal 52.0% of the
  time, and pushed-down ones 69.6%. Escapes: 68.4% held, 64.9% pushed. A later teammate's kill bid means the
  fight is going our way, and that confounds the comparison. **Seat commitment would fix about 0.25 bids a game,
  with no measurable outcome loss today.** It is worth doing cheaply, not as a big win.
- **Escape bids rarely know they act first.** 64.5% of escape bids (26k, 6.1 a game) already had a threatening
  enemy before us at its worst-case slot when bid. `offer_escape` never checks `can_act_before`. 37% of those
  acted first anyway. Survival is 68.3% when the bid assumed acting first and 50.6% when it did not.
- **Kill bids that act first still fail half the time.** The target died in r+1 for 52% of them, 51.9% by us. This
  is damage or plan conversion, not order: worth a separate look, since `side_damage` counts allies acting before
  the target, by the last read.
- **Assumed ranks hold.** Our assumed next rank equals the real one for 95.3% of kill bids and 91% of escape bids.
  The escape misses split 7.2% higher and 1.9% lower.

## 2. Enemy order

### Safety's `turns_before_ours` next-round term (traced: 6.5M enemy reads within 8, 1.95M within 4)

| subset | reads | wrong | fixed by our real slot | fixed by the enemy's real slot | needs both |
|---|---|---|---|---|---|
| within 8 | 6.52M | 27.1% | 11.3% | 10.7% | 5.1% |
| within 4 | 1.95M | **32.6%** | 15.3% | 11.4% | 5.9% |
| within 4, enemy yet to act | 0.97M | 36.0% | 11.4% | 17.4% | 7.1% |
| within 4, enemy acted | 0.98M | 29.2% | 19.2% | 5.4% | 4.6% |

- **The cost.** Within 4, the term says "enemy after us" but the enemy acts first in 18% of reads (352k). In
  those, the enemy hits us before our next turn 26.4% of the time, against 2.7% when "after" was right. When the
  term says "enemy first" and is right, the rate is 22.6%.
- **Why the underestimates happen** (the 352k):

  | cause | share | enemy hit first |
  |---|---|---|
  | our own slot moved | 49% (26.5% enemy yet to act, 22.5% enemy acted) | 16-22% |
  | the enemy's slot moved | 31% (26.8% yet to act, 4.1% acted) | 38% / 24% |
  | both | 20% | |

  Our own priority changed this round in 73% of the wrong reads. The move is priced at last round's rank, and
  the bid at turn end then moves it ("rank chosen after the move").
- **For `ast-wc`.** In contact, a third of Safety's next-round counts are wrong, about evenly ours and theirs.
  The enemy share sits almost all on enemies yet to act. Worst-case enemy order belongs in `turns_before_ours` for
  enemies yet to act (rank 0 next round, as `enemy_next_rank` already does), not only in the bids.
- **For `ast-seat`.** The bigger half is our own slot: the move must be priced at the rank the turn will bid.

### Enemy priorities and ranks

The read before an enemy acts differs from its final value whenever it changes priority in its turn. The table
gives the rate per live champion-round, then in contact, then the team's order changes and how in-contact
champions move. "Contact top" is the share of rounds where the team has champions both in and out of contact and
an in-contact one is rank 0 next round. Compare it with "contact share", the in-contact share of the team, which
is what a random top would give.

| team (games) | champ-rounds changed | in contact changed | team order changes | contact top / share | in-contact jumps to top (quiet) | in-contact rank moves (up) |
|---|---|---|---|---|---|---|
| astraeus (4268, self-play) | 20.0% | 59.0% | 26.2% | 55.8% / 35.3% | 25.4% (4.1%) | 44.7% (24.1%) |
| Supaswag (1657) | 24.1% | 36.2% | 31.8% | 79.9% / 37.0% | 25.2% (3.0%) | 28.9% (16.4%) |
| T1 (1397) | 10.8% | 27.9% | 25.1% | 78.2% / 37.7% | 22.8% (2.7%) | 28.2% (17.1%) |
| Univ. of Shingtonwash (1354) | 15.8% | 38.6% | 14.5% | 58.4% / 38.7% | 18.0% (2.8%) | 33.3% (17.7%) |
| NEETCoders (1298) | 3.9% | 6.8% | 10.7% | 43.9% / 36.9% | 5.3% (0.9%) | 11.9% (7.4%) |
| print dont int (1238) | 0.1% | 0.0% | 0.0% | 31.9% / 38.4% | 0 | 0 |
| hello (1164) | 15.2% | 57.6% | 23.1% | 45.2% / 38.1% | 12.9% (3.6%) | 36.8% (21.7%) |
| Ad Astra (1124) | 27.8% | 74.3% | 8.2% | 56.4% / 38.2% | 13.1% (2.7%) | 21.9% (11.7%) |
| newer team (us, v66 era) (1072) | 27.9% | 55.3% | 24.2% | 60.2% / 36.1% | 23.7% (3.1%) | 38.1% (20.9%) |
| Intercontinental Fish (1053) | 9.1% | 32.0% | 23.1% | 36.2% / 37.6% | 12.0% (3.3%) | 36.3% (18.4%) |
| Mite (986) | 22.1% | 63.2% | 32.4% | 60.4% / 38.0% | 20.5% (5.1%) | 44.0% (25.4%) |
| prism best girl (949) | 7.6% | 27.6% | 20.8% | 36.9% / 36.4% | 11.1% (2.5%) | 32.0% (16.4%) |
| Trzy Kwaterki (896) | 22.9% | 52.6% | 14.7% | 49.7% / 37.6% | 13.3% (1.9%) | 26.2% (15.1%) |
| Sponge (792) | 1.1% | 7.0% | 4.0% | 40.9% / 37.8% | 5.5% (1.2%) | 8.7% (5.1%) |
| policy wonk (754) | 2.4% | 11.5% | 6.9% | 48.0% / 37.9% | 8.1% (1.6%) | 14.2% (8.1%) |
| Claudus Maximus (701) | 1.9% | 6.6% | 5.8% | 36.2% / 37.9% | 3.7% (1.2%) | 9.2% (5.3%) |

The full ladder table (26 teams with 50+ games) is in `summarize.py`'s output.

- **Top teams reorder in contact.** Ranks of in-contact champions move next round 28-44% of the time for every
  top-10 team, and 16-25% move up. Supaswag and T1 put an in-contact champion at rank 0 in about 80% of mixed
  rounds. Fish and PBG (the strongest records, 60% and 63%) change priority rarely (8-9% of champion-rounds), yet
  in-contact ranks still move 32-36%. The team order moves when a teammate changes.
- **A third of the field is near-static** (NEETCoders, print dont int, Sponge, policy wonk, Claudus Maximus,
  procless: under 4% changes). Against them, the current "settled until seen changing" rule is right, and worst
  case costs only bids (next item).
- **What the worst case costs today.** `KL` gives the enemies killable at their read slot that we would precede
  at that slot. In 24,782 turns (5.8 a game) the worst-case rank 0 for an unsettled enemy blocks the kill bid,
  about as many as it allows (25,209). In the blocked cases we acted first anyway 49.6% of the time, yet the
  target died next round only 15.1% of those times. In allowed cases we act first 96% of the time and the target
  dies 51.4%. The worst case already loses half the read-order kill bids against astraeus. Before `ast-wc` makes
  enemy order more adversarial, it should check that the bids it drops are not where the kills come from.

## 3. Round-boundary seats

At every boundary the team starting r+1 holds both seats, a back-to-back double: in self-play, 4.1% with one
champion in both seats. Rates below are per boundary double where a seat holder is in contact (18.6% of
boundaries in self-play).

| team | in contact | one champion in both seats (of in-contact) | hit, either seat | kill | one-champion double: hit / kill / hits in both | control: in-contact single turn hit / kill |
|---|---|---|---|---|---|---|
| astraeus (ours, self-play) | 18.6% | 14.5% | 48.6% | 2.9% | 61.3% / 2.6% / 20.1% | 35.1% / 1.3% |
| astraeus (theirs on us) | 18.6% | 14.5% | 48.4% | 2.9% | 61.1% / 2.5% / 19.9% | 35.1% / 1.3% |
| Supaswag | 27.7% | 2.8% | 39.7% | 2.5% | 43.2% / 2.2% / 12.7% | 30.9% / 1.6% |
| T1 | 29.7% | 7.0% | 41.6% | 1.7% | 51.4% / 1.4% / 20.6% | 34.0% / 1.2% |
| Intercontinental Fish | 23.1% | 13.0% | 41.7% | 3.3% | 68.8% / 8.1% / 28.5% | 31.7% / 1.5% |
| prism best girl | 20.2% | 7.7% | 40.1% | 3.4% | 64.6% / 7.3% / 22.6% | 31.5% / 1.7% |
| Mite | 25.5% | 10.1% | 38.5% | 1.9% | 46.6% / 2.7% / 18.6% | 33.5% / 1.4% |

- **A double is worth about two turns.** A boundary double in contact lands a hit 48.6% of the time and a kill
  2.9%, against 35.1% and 1.3% for an ordinary in-contact turn. The enemy's doubles on us read the same: 48.4%
  hit, 2.9% kill.
- **The two seats rarely go to one in-contact champion** (14.5% for astraeus). No ladder team does it
  deliberately either: the highest share is 13%, Fish's. When one champion does hold both seats, kill rates reach
  7-8% for Fish and PBG.
- **For `ast-seat`.** "The in-contact champion that can use two turns takes the last seat in a round they start
  and the first in the next" is a cheap rule the rules guarantee, whatever the enemy order. Today it happens by
  accident 14.5% of the time.

## 4. Fork opportunities (traced)

A fork is two or more enemies killable by us with allies (at their read slots), none of which our seat guarantees
preceding at its worst-case slot. We found 1060 such turns, 0.25 a game, out of 1.05M turns with an enemy in our
reach.

- In 1033 of them, rank counting guarantees that at least one acts after us: more killable enemies than enemy
  slots before ours. In those we acted before at least one of them 96.1% of the time, and one died next round
  40.1%. Our bid there was no band (989), escape (41) or kill (3), so the bot never claims the fork.
- **For `ast-wc`.** Forks are rare (one game in four). A pigeonhole kill bid ("at least one of these acts after
  me") is correct under adversarial order and cheap, but it is worth at most a fraction of a kill per four games.
  It belongs in a worst-case rewrite only if it comes free.

## 5. Ally blocking in combat (traced)

- **An ally holding the only hitting tile is rare.** In 0.8% of strike-search turns with a hittable foe (5529, 1.3
  a game), an ally held the only walk or dash tile from which we could hit a foe. That ally left the tile later
  the same round 27.5% of the time, and by the end of next round 70.7%. We still hit someone that turn 29.6% of
  the time, and the blocked foe died that round or the next only 6.3%.
- **`make_way`** fires 1.3 times per 1000 champion-turns: declined because we carry more gems (y) 14,251, moved
  aside 5,015, move failed 3,134.
- **For `ast-seat`.** Ally blocking is not a material loss. Ordering allies so that a blocker moves first is not
  worth a turn-order change.

## 6. Kill conversion (replays)

An episode is an enemy under 25% health, off its spawn, with one of ours within 4 at the round's end. Outcome is
judged over the next 3 rounds. "Enemy first" means it acted in r+1 before every one of our champions that was
within 4.

| hunting team | episodes | killed by us | escaped (alive, no heal) | healed | recalled | reached spawn | enemy first: escapes / kills |
|---|---|---|---|---|---|---|---|
| astraeus (self-play) | 38951 | 29.6% | 63.7% | 2.6% | 1.5% | 1.1% | 42.7% / 46.3% |
| Intercontinental Fish | 14185 | 45.4% | 49.1% | 0.6% | 1.4% | 1.8% | 56.1% / 45.5% |
| prism best girl | 11910 | 45.7% | 49.2% | 0.4% | 1.5% | 1.4% | 53.7% / 44.6% |
| Univ. of Shingtonwash | 26811 | 36.4% | 57.8% | 0.9% | 1.4% | 2.1% | 52.0% / 38.4% |
| Supaswag | 22616 | 33.4% | 61.7% | 0.8% | 1.6% | 1.1% | 44.0% / 37.7% |
| newer team (us, v66) | 13270 | 28.5% | 65.3% | 0.6% | 2.6% | 1.3% | 41.9% / 36.2% |

- **Conversion is a damage problem, not an order problem.** Astraeus converts 30% of low-health enemies in reach,
  and the top teams 45%. In astraeus's games the enemy acted first in 43% of escapes and 46% of kills, which is
  no difference. Ladder teams show 8-14 points more "enemy first" in escapes than in kills, a modest order
  effect.
- The gap to Fish and PBG (16 points) is far larger than any order effect measured here.

## What this says for the two streams

- **`ast-seat`, in order of size.**
  0. Late seats are worth a lot to idle allies near enemies: 7 points between ordering them near-late and
     near-early, +1.5 to +2.3 for near-late over astraeus (see "Dead-slot loss"). The seat scheme must keep them
     at the back.
  1. Price the move at the rank the turn will bid. Our own slot moving after the move is half of Safety's wrong
     next-round counts in contact, and 49% of its underestimates.
  2. Give the two boundary seats to one in-contact champion. A double lands kills at about twice a single turn's
     rate (2.9% vs 1.3%), and it now happens to one champion only 14.5% of the time.
  3. Ally commitment against later kill bids fixes 0.25 bids a game and is cheap.
  4. Ally blocking is negligible.
- **`ast-wc`.**
  1. Apply worst-case order in Safety's `turns_before_ours` for enemies yet to act. The enemy's slot moving is
     31% of the underestimates, 38% hit-first when it happens.
  2. Weigh the bid cost. Worst case already blocks as many kill bids as it allows, and half of the blocked ones
     would have acted first.
  3. Forks are rare. The pigeonhole bid is correct under adversarial order and cheap.
  4. Every top ladder team reorders in-contact champions (28-44% of rounds), so "settled until seen changing"
     holds only against the static third of the field.
- **Not turn order.** Kill bids that act first still convert only 52%, and low-health conversion trails the top
  teams by 16 points. Both point at damage and plan estimates (`side_damage`, the strike search), not at seats.

## Dead-slot A/B

`variants/ast-deadlast` ranks dead allies below every live one. In `turn_order.cc`, `dead_priority` becomes
`idle_lowest - 1` and danger takes its own base, `idle_top + bucket`. `rank_code`'s range is widened to match.
Danger and band ordering is unchanged.

`py tools/ab.py variants/ast-deadlast variants/astraeus-e9c3797 --no-test-draft --suites maps/fresh-85200..85219
--name deadlast` (fastrunner native) gave:

- **CAND 48.2% of 10,240 (4937-5303), 95% CI 47.2-49.2.** 18 of 20 suites were under 50%.
- Out-of-fuel turns: CAND 73,678 in 7,340 games, REF 73,653 in 7,357. Equal, so this is not fuel.
- Results: `replays/ab/deadlast/summary.md`.

Moving dead allies down loses about 1.8 points. The only seats that change are those of idle (no band, no danger)
live allies, which now act one alternation earlier per dead teammate. See "Dead-slot loss" below.

## Dead-slot loss

The question is why ast-deadlast loses (48.2%). Ranking dead allies last changes only one thing: every idle live
ally (no band, no danger) acts one alternation earlier per dead teammate.

**Method.** The A/B's own 10,240 replays (9821 distinct, extracted to `replays/meas-deadlast-ex`), read with
`scripts/deadslot.py`. It compares each game's deadlast side with its baseline side and splits rounds by whether
the team started the round with a dead champion. A live ally is idle when its priority for the round decodes to
the idle range: the code above the payload is raw x 8 + 7 - index, idle raw -11..12, in both variants. "Near"
means an enemy within 8 at the round's start.

**Rounds with a dead ally, per idle champion-round:**

| | deadlast | baseline | change |
|---|---|---|---|
| idle near: slot / enemy turns before it | 3.60 / 2.05 | 6.46 / 3.48 | acts 1.4 enemy turns earlier |
| idle near: damage taken a round | 16.18 | 11.70 | **+38%** |
| idle near: deaths per 1000 | 2.728 | 2.028 | **+35%** (killer unseen the round before: 0.908 vs 0.666) |
| idle near: gems lost to death per 1000 | 25.3 | 16.2 | +56% |
| idle near: damage dealt a round / kills per 1000 | 8.85 / 0.427 | 9.05 / 0.462 | no gain |
| idle near: distance at first sight / within 4 | 6.49 / 15.6% | 6.37 / 17.2% | ~same |
| idle far (no enemy within 8): deaths per 1000 | 0.455 | 0.446 | none |
| team: capture gems per 100 rounds | 61.2 | 63.9 | -4% (more dead time: 2.43M vs 2.36M dead-ally rounds) |
| busy (danger or band) allies: deaths per 1000 | 31.6 | 29.5 | +7%, with less damage taken (76.9 vs 85.4) |
| respawned champion's next 6 rounds: damage / deaths | 11.5 / 0.33% | 11.5 / 0.30% | none (slot 7.5 vs 2.0) |

Rounds with no dead ally match within noise: idle near deaths per 1000 are 1.30 vs 1.21.

- **The whole loss is idle allies near enemies acting earlier.** Moved ahead of enemy turns, they take 38% more
  damage and die 35% more often, losing 56% more gems, and deal no more damage. Idle allies far from enemies are
  unaffected.
- **They do not see enemies sooner in any useful way.** First-sight distance is unchanged. Acting before the
  enemy only gives it the reply: it moves after us onto what we walked into.
- **(b) The respawn round is ruled out.** Damage and deaths over the first 6 rounds back are identical, though
  the respawner's slot moves from 2 to 7.5.
- **(a) Comms timing is not needed.** Shared memory is not in replays, so unread capture records could not be
  counted directly. Claim collisions among live allies are equal (19.5% vs 19.6% of claims). The -4% capture gems
  follows from the extra deaths and dead time. The decisive test below never touches dead allies' turn position,
  and so never changes their comms timing, yet it reproduces the effect in both directions.

**Direct test of the principle.** Two variants change only the order among idle allies with no camp tie hit to
order (`idle_priority`'s `hit <= 0` branch, which otherwise orders by health). They order by distance to the
nearest enemy last placed (visible, or tracked within 3 rounds), in steps of 2 tiles. Each ran 10,240 games on
fresh-85200..85219, against `astraeus-e9c3797`, with the fastrunner:

| variant | win rate | 95% CI | OOF CAND / REF |
|---|---|---|---|
| `ast-idle-nearlate`: nearer to an enemy acts later | **51.5%** | 50.5-52.5 | 75,257 / 74,292 |
| `ast-idle-nearearly`: nearer acts earlier | **44.4%** | 43.4-45.4 | 72,968 / 74,109 |
| nearlate, confirmation on unused suites (fresh-85228..85239, ladder, gen) | **52.3% of 6828** | 51.1-53.4 | 48,546 / 47,056 |

The ladder suite is 50.0% of 172 and gen 54.7% of 512. Results are in `replays/ab/idle-nearlate`,
`replays/ab/idle-nearearly` and `replays/ab/idle-nearlate-confirm`.

- **The two orders are 7 points apart.** Ordering idle allies by nearness to the enemy swings 7 points between
  them. This confirms the user's hypothesis: a champion with nothing urgent gains by acting late, and the gain
  is concentrated where the enemy is near. The baseline already gets part of it by putting idle allies below the
  dead ally, which is why moving the dead ally down lost 1.8 points.
- **`ast-idle-nearlate` is a candidate change** worth about +1.5 to +2.3 points: 51.8% over 17,068 games. The
  camp-tie order is kept whenever a camp hit is in play. It changes only `plain_priority` in `turn_order.cc`.
  Its diff against astraeus is in `bots/variants/ast-idle-nearlate`. It has not been tested against the ladder
  field, nor merged.
- **For `ast-seat`.** "As late as possible when nothing needs you early" should be a principle of the seat design,
  not a tie-break. Any scheme that commits allies to seats must keep idle allies near enemies at the back. Dead
  allies' seats are better spent above idle allies than below: they push the living later.
- **For `ast-wc`.** The value of acting late is the same effect seen from the enemy's side. Under adversarial
  order, an enemy near us that has nothing urgent will act after us.
