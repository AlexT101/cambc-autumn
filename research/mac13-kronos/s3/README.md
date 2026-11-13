# s3: the Prism war, turn by turn

This is a measurement study over the 1,024 debug mirror games in `replays/batch-20261113-034628-ab-mac13-kronos-bel-study512`
(`kr-beliefs` against `chy-ref`, which play the same game). No bot was changed. The full tables are in [tables.md](tables.md).

**Sample.** In 494 of the 512 map pairs, the two sides played the identical game. So there are about 530 independent
games, and every count below is over all 1,024 (doubled).

## Scripts

Every script reads `replays/.s3cache` and runs 16 processes.

- `extract.py` builds the cache: one compact pickle per game. It holds the extracted rounds and events, the D lines
  (branch, farm group, claim) and CV lines from both stdouts, and kr-beliefs' `BD` records of the enemy Prism.
- `lib.py` loads the games and holds the geometry. It also computes `own_ground`, from walking steps from each
  spawn, as `combat/guard.cc:29` does.
- `study.py` writes `rows.pkl`, with these row types:
  - encounters;
  - Prism deaths, each with its sight window;
  - dominant-Prism rounds and engagement episodes;
  - per-game dominance onset and loss inputs.
- `endrace.py` writes `endrace.pkl`: the loser's and winner's bags and channels at the end, and every Prism
  tribute's start, cancel and completion.
- `firststrike.py` writes `firststrike.pkl`: for each Prism duel, who stepped into cast reach (4) and who hit first.
- `report.py > tables.md` writes the tables.

**Definitions:**
- **Power:** Focus × health.
- **Encounter:** both Prisms alive within 6 tiles. A new episode starts after 20 rounds apart.
- **Weak:** power ratio ≥ 1.5.
- **"Closed":** a Prism's own steps against the other's last tile sum to ≤ -2 over the 10 rounds before.
- **Hits:** damage events from the replay. The D branch never shows `A`, because the goal step overwrites it.
- **Burst over two turns:** 1.5F + 1.0F for the ready spells, plus two basic attacks.

## Findings

### Q1. How encounters start (2,218 with ratio ≥ 1.5; 2.4 a both-Prism game)

- **The weak Prism closes the distance, not the strong one.** It closed in 50% of encounters and died within 20
  rounds in 57% of those. The strong one closed in 22% (weak died 22%); both closed in 24%.
- **The biggest single kind is the endgame stall (627, 28%).** The weak Prism is in `stop_ender` (E,
  `stop_game_ender`, fight.cc ~1260, forced from bot.cc:425 by `holds_hard_stop`). It walks at the strong Prism,
  which is channelling a winning tribute in 98% of these (median bag 1,214). In 92% of the resulting deaths the weak
  one stepped into reach itself; it dies 86% of the time.
- **Farming (947, 43%).** The weak one dies in only 18% of these encounters.
  - Its farm target was within 4 of the strong Prism in 54% and within 8 in 79%.
  - The target was on its own side 36%, the middle 31%, the strong side 34%. The weak one stood on its own ground in
    93%.
  - It saw the strong one in 59% (64% within the last 10 rounds).
  - The strong one was farming in 63%, tributing 13%, chasing 11%.
- **Retreating (257).** The strong one closed in 55% of these, chasing 26% or farming 57%. The weak one saw it 93%
  of the time and died 28%.
- Overall, the weak one saw the strong one at the encounter 75% of the time (78% within 10 rounds). Sight is not
  the problem.

### Q2. Weak Prism deaths

There were 1,109 Prism deaths by the enemy Prism, of 1,477 Prism deaths in all. The first Prism death in a
both-Prism game happened in 532 games, and the victim's team lost 485 of them. 389 of those first deaths were by the
enemy Prism.

| first death by the Prism | n | victim team won | sight → death (q1/med/q3) | victim branches | fought back | could 2-turn-burst the killer at sight | killer could burst victim |
|---|---|---|---|---|---|---|---|
| retreat, weak | 144 | 8% | 4 / 9 / 15 | R 61 F 25 B 9 | 71% (median 475 dmg) | 7% | 44% |
| retreat, not weak | 95 | 11% | 5 / 12 / 23 | R 45 F 34 T 9 | 69% | 25% | 34% |
| stop_ender, weak | 61 | 7% | 8 / 17 / 39 | R 39 E 27 B 26 | 77% | 13% | 69% |
| stop_ender, not weak (bag ~595) | 43 | 0% | 16 / 35 / 98 | B 34 R 30 T 14 E 9 | 49% (median 0) | 72% | 84% |
| other (mostly unseen, ~5 rounds) | 40 | 0% | 5 | F / T / B | 5% | | |

- **Retreat deaths (239, 61% of the first Prism-on-Prism deaths).** This is the earlier study's pattern.
  - The victim saw the killer 93% of the time, from 5-7 tiles away.
  - Its steps went away 29-35% of the time, toward 22-25%, and stood still 42-47%.
  - It was 26-31 walking steps from its own spawn, with an ally at a median distance of 4 and an altar at 7-8.
  - A recall that had been kept going was cut by damage in 15-29%.
  - The killer stepped into reach in 39-46% of the non-stop_ender deaths and hit first in 63-72%. It ended with a
    median 60-77% of its health.
  - **Prism spells exclude walking.** In 34-36% of these deaths, the victim's retreat walked within the killer's
    reach with a spell ready. In 27 of 239, the casts it walked past (cooldowns simulated) exceeded the killer's
    remaining health.
- **Did fighting back from the start win?** Rarely, for the weak ones: their 2-turn burst covered the killer's
  health at first sight in 7-13% (25% for the not-weak).
- **The "stop_ender, not weak" deaths are different.** These are Prisms carrying 540-715 gems.
  - Both sides hold big bags near the altars and oscillate between bank and retreat (the B/R strings, as in the live
    case at EXPERIMENTS.md:17233).
  - When the enemy starts a winning tribute, ours walks in under the forced stop and dies, often without dealing
    damage, although its burst covered the killer's health in 72%. It hands the killer a ~595-gem bag, and its
    team won none of these.
- **Repeated deaths.** Counting every death, not just the first, 611 of 925 weak deaths are stop_ender deaths in
  games already decided (the victim's team won 1%). The same Prism respawns, walks back in and dies again, up to
  4 times in one game.

### Q3. The dominant Prism (Focus ≥ 2× the enemy Prism's, both alive): 1,077 Prism-games, 136,607 rounds

- **Two phases:**
  - **Mid (65% of dominant rounds):** branches F 62, T 13, P 6, B 6, C 3, R 3.
  - **Win (35%: its bag plus its team's score reaches 1,000):** T 78, B 15. It is channelling the long winning
    tribute.
- **Sight and hits in the mid phase.**
  - It sees the weak Prism in 17% of mid-phase rounds.
  - Within 4 tiles, it hits the weak one in 28% of seen rounds, and the weak one hits it in 35%.
  - At 5-6 tiles, it hits in 4%; when it does not, it farms (F) 40% and chases (C) 14%.
- **The chase gate.** Take the rounds where it sees the weak one but neither chases nor hits it (13,139 in the mid
  phase). In 71% of them the weak Prism is healthy and on its own ground: 28% with no bag, 43% with a bag that
  `intercept_steps` calls unstoppable. `preyable` (fight.cc:747-765) refuses exactly these.
- **Engagement episodes (1,236).**
  - They last a median of 1 round.
  - 63% end at the gate: next round the dominant Prism farms or tributes while still seeing the weak one, which
    is on its own ground 97% of the time.
  - 13% end with lost sight, 10% in its own retreat (hurt in 26% of those), and 14% with the weak Prism's death.
  - The dominant Prism killed the weak one in 257 episodes (21%).
- **Whether it knows where the weak Prism is.** Sampled from the BD dumps:
  - visible 17%;
  - tracked to ≤9 possible tiles 3%, to ≤49 tiles 4%;
  - untracked 75%, because `track_horizon` is 3 rounds after the last sight.
  - It saw the weak Prism in the last 10 rounds in 27% of dominant rounds. Out of sight, it effectively does not
    know.
- **Conversion decides the game.** Take the 719 games with sustained dominance (the ratio held 10 rounds). After the
  onset:

  | what happened to the weak Prism | games | dominant team wins |
  |---|---|---|
  | killed by the dominant Prism | 258 | 96% |
  | died some other way | 55 | 89% |
  | never died | 406 | 57% |

### Q4. Dominant-team losses (340 of 894 games at the brief's onset)

- **The brief's 62% is diluted.** 339 of the 894 onsets happen at the weak Prism's own tribute: its bag leaves, so
  its Focus falls. In 108 of them the game ends that round, on that tribute.
- With a sustained onset (the ratio held 10 rounds), the dominant team wins 73% of 719 games.

| class (first that applies) | losses |
|---|---|
| 1. The weak Prism's winning tribute made the onset; the game ended that round. Our Prism was holding 594; score + bag ≥ 1,000 in 24. | 108 |
| 2. The dominant Prism was killed later (killers: Prism 30, Vesper 14, Cassi 6; a median 211 rounds after onset; bag lost 258). | 56 |
| 3. A winning tribute was stunned or locked (bag ~790; the race ran 340 rounds after onset). | 10 |
| 4. Out-tributed while holding its bag (`keeps_gems`): bag at the end 554, our score 329; the bag alone would have won in only 12, team bags in 39. 82 of these began when the weak Prism banked. | 114 |
| 6. Out-raced after banking (our score 965 at the end). | 52 |
| 5. Round limit | 0 |

**The end of every race (906 losers with a Prism):**
- In 191, the loser's score plus the gems it was carrying already reached 1,000 when the winner's tribute landed.
- In 59, the Prism's bag alone did.
- In 39, the loser's Prism was channelling a winning bag at the end. In 33, its winning bag had been stunned or
  locked.

**Prism tributes as a whole:**
- Prisms complete only 0.63 tributes a game, with a median bag of 519.
- They start 7,453 channels of median 55 turns (`ceil(bag/10)`). These are cancelled by stuns 2,639 times, by the
  Prism itself 2,363, and by locks 1,078.
- A winner's Prism takes a median 70 rounds from holding a winning bag to the win, and is stopped at least once in
  337 of 623 games.

## Levers (games per 1,000, rough; outcome splits are not causal)

1. **Converting dominance (the chase gate).**
   - The deciding code is `preyable` (combat/fight.cc:747). Off our ground, it refuses a healthy target (health ≥
     `hurt_health_fraction` 0.453) unless the target holds a cleared group or carries a bag `intercept_steps` can
     stop. `prey` and `chase` (fight.cc:906-1085) act on that.
   - It refuses 71% of the dominant Prism's seen, unengaged mid-phase rounds. Episodes last 1 round, and 63% end
     at this gate.
   - **Size:** 406 sustained-dominance games never kill the weak Prism and win 57%, against 96% when it is killed.
     Converting 1 in 5 is about +30 per 1,000. The ceiling is about 150.
   - **Risk:** "chase off own ground too" lost 2.5 points on an older bot (EXPERIMENTS.md:9181). The narrow form is
     Prism-on-Prism only, at a Focus ratio of 2 or more, with its 2-turn burst covering the target's health.
2. **The winning channel.**
   - The deciding code:
     - `keeps_gems` (economy/bank.cc:905) holds every gem until the bag wins alone, so the winning channel lasts
       `ceil(bag/10)` turns, 41-84.
     - `continue_tribute`, `can_tribute_safely` and `carry_bag`'s altar choice (bank.cc ~1440-1606) decide where it
       lands and when the channel is cancelled.
   - **Size:** up to 59 losses per 1,000 with the win already in the Prism's bag (39 mid-channel, 33 stopped).
     Winners stall a median 70 rounds. A channel that lands more often might swing about 20.
   - **Not this:** smaller or earlier banking lost repeatedly (psm50b -9.1, retain cap 150, bm-lb -2.0).
   - **Instead:** where and when it starts, and keeping the stopper off. The enemy stop_ender walks in itself 92% of
     the time.
3. **Prism retreat inside an enemy Prism's reach.**
   - The deciding code: `want_home` → `stand_lost_at` (fight.cc:512) → `retreat` (fight.cc:1579). Its
     `escape_walk` comes before `cast_at_enemies`, and a Prism's spells cannot follow a walk.
   - **Size:** 239 of 389 first Prism-on-Prism deaths end a retreat, and the victim's team wins only 8-11%. In 27,
     the casts walked past exceeded the killer's remaining health (8 of those games were won anyway). That is at
     most about 19 per 1,000, realistically 5-10.
   - **Related:** the big-bag stop_ender deaths (43 first deaths, bag ~595, none won). The forced stop in
     `decide` (bot.cc:425 → `stop_game_ender`) walks a full-bag Prism into the channeller's first strike. The
     channeller cancels and strikes, because a walker cannot cast that turn.
