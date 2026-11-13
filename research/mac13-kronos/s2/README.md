# s2: why does our Prism convert so few of its kill chances?

A measurement study with no bot change kept. `bots/variants/s2-trace` is chy-ref (charybdis 525) plus debug-only `PK`
lines ([pk-trace.patch](pk-trace.patch)). It also drops the per-observation `SLOT` debug line, to keep each team's
stdout under the 1 MiB cap (max 932 KB, no game at the cap). The release build is the same size as chy-ref's, with
one 51-byte block reordered inside one function.

**Run:** a debug mirror against chy-ref on `maps/suites/mac13/study512` (1,024 games, fuel 200k, fast runner). It went
50.1% (513-511), with 0 failures and 83 out-of-fuel turns on each side. Every chance turn got its end line. The replays
are deleted. The 41k joined rows are kept in `replays/mac13-kronos-s2-pk.jsonl.gz`.

- `pk_join.py BATCH`: joins each PK line with the replay over the next 8 rounds: death and killer, our damage and
  casts on the target, heals and shields it got, what it did before our next turn, and the distance at our next
  turn. The target's turns before our next turn come from the engine order, rebuilt from the recorded priorities.
  That model matched the events' turn index on every event except channel cancels, which are logged on the
  canceller's turn.
- `report.py [rows] [--sizing | --windows]`: writes every table in [tables.md](tables.md).

**PK lines.** `PK S` is printed at our Prism's turn start, once for each visible enemy non-Prism within 6 whose
`effective_hp` ((health + shield) / taken) is under 2.5x our Focus. It gives the distance, both cooldowns, our
channel, bag and health, the nearest enemy Prism, the bot's two turn-window answers for the target, and bushes.
`PK E` is printed at the turn end. It gives decide's exit point and the branch, the strike search's result (ran,
chose, attacked, moved), `chase_aim`'s target, our casts, and two chase-gate verdicts on each chance target:
- the real one, from the last `prey()` call this turn;
- a shadow one, from `prey()` called at decide's start, inside the debug block.

A verdict is one of: chosen, preyable's refusal (near spawn, teleport, healthy off our ground, pack covers), fight
sim lost, escapes, fuel cut, or another target chosen first.

**Units.** An *episode* is the chances on one target, deduplicated per 10 rounds. It is *converted* if the target
(or its linked body) dies within 8 rounds of the episode's first chance. Rates are per traced team-game (1,024).

## Findings

1. **The baseline reproduces.** There are 11.2 episodes a team-game (40 chance turns). 2.62 are converted (23%),
   2.10 of them by our Prism. That matches k2's 2.6 / 2.1. k2's 14.6 used a looser dedupe; the kills match.

2. **Distance decides, and 72% of chances are at distance 6.** A Prism kill from 6 needs two steps (a walk excludes
   casting; stun range 4, ground reach 5, no dash) while the target keeps its turns.

   | onset | per tg | converted |
   |---|---|---|
   | d6 (stun ready, no enemy Prism / enemy Prism within 8) | 3.35 / 2.81 | 23% / 11% |
   | d6, stun down | 1.84 | 7-16% |
   | d5 | 1.66 | 15-51% |
   | d4 | 0.87 | 18-74% |
   | d<=3 | 0.65 | 29-77% |

   Of the 8.56 missed episodes a team-game, 6.7 start at d6. At our next turn, the missed targets were:
   - at 6: 3.2;
   - at 7-9: 3.2;
   - at 5 or closer: 1.9.

   Our Prism never damaged the target in 7.30 of the 8.56. The target was healed in 1.37, shielded in 0.36, and
   our Prism died within 8 rounds in 0.51.

3. **Real lethal windows convert well.** In these, the burst (stun + ground, raw) beats the target's effective hp:

   | window | per tg | converted | main misses |
   |---|---|---|---|
   | d<=4, stun ready | 1.28 | 82% | 0.23/tg: tribute kept 0.11, stopping a game-ender 0.04, retreats 0.03 |
   | d5, stun ready | 1.99 | 54% | farm turns that neither cast nor stepped: 0.09/tg at 20%; the search casts ground at d5 in most turns (65%) |
   | d6, stun ready | 7.30 | 17% | farm without a step: 1.22 at 6%; retreat: 0.83 at 5% |

   At d6, a chase step converts 29% and a farm step-in 17%.

4. **Causes of the misses** (missed episodes a team-game, by the onset branch, then the gate):

   | cause | missed/tg | conv | what our Prism did / why | what the target did |
   |---|---|---|---|---|
   | chase gate refused: healthy (>=45% of max) on its side, no bag or hold (`preyable`) | 1.85 | 12% | farmed (1.48/tg at onset) | mostly walked on; 6 -> 6/7 |
   | want_home retreat | 1.81 | 9% | retreated; 77% with an enemy Prism within 8, mostly at 90-100% health. Gate behind it: healthy-off-ground 0.71, fight lost 0.64, pack 0.23 | stayed out of reach |
   | tribute channel kept | 1.27 | 41% | kept the channel; at d<=5 with stun ready only 0.19/tg missed | often came to us; killed after the channel |
   | chased, no kill | 0.72 | 30% | stepped in; no hit in 0.54/tg | stepped away (6 -> 6/7); healed in 0.18 |
   | gate refused: escapes (chase verdict) | 0.64 | 11% | farmed | walked home |
   | gate refused: fight sim lost | 0.63 | 11% | farmed | |
   | carry_bag (winning or closing bag), gate refuses too | 0.45 | 25% | banked | |
   | we were stunned | 0.42 | 27% | nothing (stun) | |
   | other (pack covers, game-ender stop, holds, altar guard, ...) | 0.77 | | | |

   At the onset, the gate verdict across all episodes was:

   | verdict | per tg | converted |
   |---|---|---|
   | refused, healthy off our ground | 4.55 | 20% |
   | refused, fight sim lost | 1.64 | 13% |
   | refused, escapes | 1.14 | 16% |
   | chosen (any kind) | 2.14 | 41-62% |

   The healthy-off-ground clause compares a health share with 0.45. These targets are burst-killable at 90-100%
   health: 6.0 of the 11.2 episodes are at 90%+ health share.

5. **Sizing.** I compared each cause's non-acting onset turns with acting turns (a chase, a cast or a step in) in the
   same stratum: distance, stun ready, enemy Prism within 8. This is an upper bound, because the acting turns were
   picked for looking good.

   | cause (onset did not act) | per tg | conv now | at the acting rate | added kills/tg (upper bound) |
   |---|---|---|---|---|
   | want_home retreat | 1.52 | 6% | 20% | +0.21 |
   | gate: healthy off our ground | 1.10 | 7% | 20% | +0.14 |
   | gate: escapes | 0.43 | 8% | 20% | +0.05 |
   | gate: fight sim lost | 0.39 | 7% | 21% | +0.05 |
   | tribute kept | 2.15 | 41% | 30% | -0.23 (not a cause) |
   | all non-acting | 6.93 | 20% | 25% | +0.31 |

   So at most about 0.3 kills a team-game is recoverable from decisions, against the 2.1 our Prism makes. A
   realistic share is 0.1-0.15, about +5-7% Prism kills. The rest is reach: targets at 6 that keep walking.

6. **Turn windows are not the lever.** Conversion by the target's turns before our next turn (engine order) is 28%
   for 0 turns, 23% for 1 and 20% for 2. `enemy_may_act_after_us` was exact on every chance turn. The other window,
   `enemy_turn_before_ours_next` (`model/turn_window.cc:237`), differed from the engine's next-round order on 36% of
   chance turns:
   - it said "does not act" 6,272 times, and the target did act 3,004 times (48%);
   - it said "acts" 34,711 times, and the target did not 11,954 times.

   Both teams re-set priority every round, so this window is information-limited by design. It doesn't drive the
   misses above.

## The 2-3 most promising fixes

1. **A healthy-off-ground test that knows our burst.** In `preyable()` (`combat/fight.cc:747`, the clause at
   lines 756-759), "hurt" could mean `effective_hp(e) <` our two-turn burst (stun + ground, with the hits it leaves),
   not `health < 0.4533 x max`. The rule's logic is that a beaten enemy escapes a step across the line, but a
   burst-lethal one dies before it gets two steps. This affects 1.81/tg farm or chase turns, 1.56 of them at d6.
   - Upper bound: +0.14 kills/tg.
   - Weighted by how often the later fight and escape checks pass (22% at d6, 56% at d5, 74% at d4): about +0.07/tg.

   Cheapest to try, and the most logical.

2. **A lethal stun before a retreat.** In decide's `leave` branch (`bot.cc:469-478`), the strike search runs only
   under `follow::binding`. `want_home` (`combat/fight.cc:597`, via `drawn_home` :501 / `stand_lost_at` :512) doesn't
   price that our stun takes the target's next turn. Non-acting retreat episodes: 1.52/tg at 6%.
   - Upper bound: +0.21/tg. But 77% of these have an enemy Prism within 8, and the Prism war decides games, so a
     broad version likely loses.
   - A narrow version: only a d<=4 stun-ready lethal window on one of the threats themselves, about 0.1/tg at
     48-70% conversion. About +0.03-0.05/tg.

3. **The d6 chase verdicts** (`escapes()` `combat/fight.cc:817`, `Safety::chase_trade` `model/safety.cc:3450`): at
   most +0.05/tg each. Tune only together with fix 1, since that fix sends more targets to these checks.

Not worth changing:
- `continue_tribute` (`economy/bank.cc:1457`): tribute-kept chances convert 41%, better than acting ones.
- `carry_bag`'s chase gate (`economy/bank.cc:1566`): 0.08/tg.
- The d5 strike search (`combat/plan.cc:1992`): it already casts ground at d5 in most turns, 65% converted.
