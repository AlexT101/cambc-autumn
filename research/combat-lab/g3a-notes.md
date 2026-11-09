# G3a: team coherence of stay/leave (2026-11-08)

Base `variants/cl2-belief` (oc-cl2-base + the belief fix). Reference for every A/B: `variants/oc-cl2-base`, suite
`maps/suites/merged/cl2-dev`, `--no-test-draft`, 20,480 games.

## Measurement (1,000 kept replays of cl2-belief-v1, cl2-belief vs oc-cl2-base; per side a game)

Scripts (scratchpad `g3a/`): `coh.py` (stand desertions), `deaths.py` (deaths by team context), `escort.py`
(flee episodes by ally cover). Rows are the two bots; they agree within noise.

**(a)/(b): a stand deserted.** A *turn* is a champion B in a fight (dealt or took champion damage in the last 3
rounds) that had not been retreating and walks home 2+ steps over the next 3 rounds (or keeps a recall). For each
ally A within 6 of B, in a fight too: *held* (A's walk home did not shrink), *followed* (A retreated too).

| | a game | A killed within 4 rounds |
|---|---|---|
| turns home from a fight | 28.5 (B at hp ≥ 0.5: 23.1) | (B itself 1.9%) |
| A held while B turned ((a) setting) | 7.8 | 1.7-1.9% |
| A followed B | 5.4 | 1.7-1.8% |
| baseline: A holds with an ally holding | 6.3-6.5 | 1.3-1.5% |
| baseline: A holds alone | 10.9 | 2.8-3.0% |
| **(a) deaths**: victim held while an ally within 6 turned in the 4 rounds before | **0.12-0.14** | |

(b) (B leaves at hp ≥ 0.5 while A held) is 6.0 a game, but A then dies 1.7-2.1% of the time against 1.3-1.5% for a
pair that holds: ~0.03 extra deaths a game. **(a) and (b) are rare as costs: 0.13 deaths a game, under the 0.3 bar.**
A desertion barely raises the stayer's death rate; ocean's lone-or-deserted stayers mostly survive.

**What is common: allies who don't cover a fleeing mate.** Deaths by context (victim's allies within 8 at k-3):

| death context | a game | share |
|---|---|---|
| stand, an ally hit an enemy in k-3..k | 1.07 | 19% |
| stand, allies near but none hit or left ("idle") | 1.22-1.28 | 21-22% |
| stand, alone | 0.61-0.65 | 11% |
| flee, an ally hit | 0.70-0.73 | 12% |
| flee, allies idle | 0.94-0.96 | 16% |
| flee, alone | 0.69 | 12% |
| allies all left (stand + flee) | 0.44 | 8% |

Flee episodes (flee.py's: below 50% health, stepping home, an enemy within 5) by a *free* ally (hp ≥ 0.5, no kept
recall or tribute, off spawn) within 5 of the pursuer:

| episode | a game | caught | home | pursuer killed within 10 |
|---|---|---|---|---|
| no free ally | 6.40 | 32.9% | 35.6% | 4.0% |
| free ally idle (no champion damage in 5 rounds) | 2.11 | 24.7% | 37.7% | 3.4% |
| free ally hit another enemy | 0.67 | 24.3% | 35.8% | 3.7% |
| free ally hit the pursuer | 3.03 | 18.3% | 42.0% | 16.0% |

The idle allies (2.7 a game): 37% walked home 2+ themselves, 50% moved away or level (farm, guard), 10% closed in
without a hit; they stood 4-5 from the pursuer in 83% of cases. Covered flights end caught 18% against 25%, and kill
the pursuer 16% against 3%. Selection inflates that (allies hit when placed to), but it is the common incoherence:
**2.1 flights a game with a healthy, free ally beside the pursuer who does nothing**, against 0.13 deaths a game
from desertion.

Why ocean's ally ignores it: `preyable` drops an enemy out of range, off our ground, at health ≥ 0.453, with no bag
or hold, and a pursuer is usually healthy. `team_pressed` joins a mate's fight only against an enemy with a smaller
health share than the mate, never the healthier pursuer of a hurt mate. And the ally counts the fleeing mate in its
own rosters as a fighter that stays (`fighting_allies`), so its stand and chase trades credit a body that is leaving.

## Mechanism: a posted leave bit, read two ways

**Post.** At the turn's end each champion posts *leaving* (its turn's branch is retreat or a kept recall) in its
priority payload, bit 11, with round & 3 in bits 12-13 (`comms::priority_payload`; claim in bits 0-7, support
mailbox 8-10). The payload is read off any ally in sight; every ally a roster counts is in sight.

**Read 1, honest rosters.** `fighting_allies` (the ally half of every fight key: stand roster, chase trade, the
planner's and guard's fights) drops an ally whose fresh bit says leaving. A champion that counted B as staying now
sees B go; it stays only if it wins without B, else it leaves with B. This is "count an ally only if it stays" and,
as its consequence, "leave together".

**Read 2, cover.** `preyable` no longer drops a healthy, out-of-range enemy off our ground when it pursues a mate
posting leaving (within its one-turn reach + 1 of the mate) and is within our range + 3. It then enters `prey`'s
candidates like any other, so a chase still needs `chase_trade` won (with read 1, without the fleeing mate).

**Turn order.**
- Mate acted earlier this round: its bit and tile are this round's, post-move.
- Mate acts later this round: its bit is last round's (age 1). Retreats persist across turns (camp_fled, the recall
  line), so a stale "leaving" is usually still true; a stale "staying" errs to today's behaviour.
- Stale beyond a round (out of fuel before publish, a crash): age ≥ 2 reads as not leaving.
- Stunned mate: decide returns early but the turn end still publishes, posting not leaving; it can't walk anyway.
- Dead or out-of-sight ally: not in any roster (`fighting_allies` takes only visible allies), payload unread.
- Cassi and Issac: two bodies, two bits. Issac covering Cassi's pursuer goes through prey's linked rule (a won
  fight that drops our body is lost).
- Willow: prey returns nothing for it; it only reads the bit through rosters.
- Our own bit is never read by us.

**Second-order effects to watch.**
- Read 1 makes more stands lost (a body less), so more retreats: cascades (C drops A after A drops B). Each drop is
  honest, but ocean's verdicts were tuned with the leaving body counted, which may have stood in for the enemy's
  attention on that body. Expect deaths to fall and kills to fall a little.
- Read 2 pulls healthy allies off farms and captures into chases: fewer gems; chases into enemy groups are guarded
  by chase_trade's late joiners. Expect kills up and economy down.
- Read 1 shrinks read 2's chase trades, so read 2 alone chases more than both together.
- Fuel: a payload decode per visible ally once a round (cached in fighting_allies), and per preyable call a loop over
  allies. Negligible.

Arms (round 1): `cl2-team` (both reads), `cl2-team-h` (read 1 only, the (a)/(b) hypothesis), `cl2-team-c` (read 2
only).

## Results

### Round 1 (20,480 games each, cl2-dev, vs oc-cl2-base)

| arm | win % (95% CI) | OOF turns CAND / REF |
|---|---|---|
| cl2-team (both reads) | 49.3 (48.6-50.0) | 181,278 / 201,062 |
| cl2-team-h (honest rosters) | 49.6 (48.9-50.3) | 181,796 / 203,524 |
| cl2-team-c (cover) | 49.9 (49.2-50.6) | 210,924 / 207,205 |

All level. 1,000 kept replays each (`scratchpad g3a/kd.py`, `escort.py`): kills / deaths a game CAND 5.69 / 5.93
(team), 5.78 / 5.93 (h), 5.75 / 6.28 (c), against the base mirror's 5.81 / 5.98.
- **Cover doesn't convert.** Flights with a free ally hitting the pursuer: 3.12 a game in cl2-team-c against 3.04
  for its REF; 2.64 against 2.76 in cl2-team (honest rosters make allies leave with the mate). A debug run (30 maps,
  `CVTURN`/`CVTRADE` traces) shows why: 153 turns a game have a pursuer of a leaving mate within our range + 3, but
  on 65 of them we retreat ourselves and on 46 we farm; prey's chase trade on the cover target is lost on 41 of the
  ~53 asks a game. The sim judges the pursuit lost (its friends join), and relaxing preyable only adds asks that
  lose.
- **Honest rosters are level but cheaper:** ~10% fewer out-of-fuel turns (dropped allies shrink fights).

### Round 2: a posted chase bit (counting the mates who are coming)

Round 1 showed the stand rosters were never short of a leaving ally that mattered. The other half of the roster
question is a mate who *will* come. A champion whose branch is chase posts bit 14 (same round tag). `fighting_allies`
counts an ally posting it within 7 (`chasing_ally_radius`), not 4; `walk_allies_in` delays its arrival by its walk.
A debug run: 25 turns a game with a chasing mate 5-7 away and an enemy within 6.

| arm | win % (95% CI) | OOF turns CAND / REF |
|---|---|---|
| cl2-team2 (honest rosters + chase bit) | 49.8 (49.2-50.5) | 184,986 / 201,751 |
| cl2-team2c (chase bit only) | 50.5 (49.8-51.2) | 213,058 / 208,172 |

Both are level; cl2-belief itself was 50.2. On each run's 1,000 kept replays (the first finished, so shorter games;
a different map mix from round 1's, so compare only within a row), the bodies a game CAND - REF are +1.0 (team2) and
+0.5 (team2c). Over all 20,480 games the win rate doesn't follow.

### Conclusion

The hypothesis is not supported. A deserted stand costs 0.13 deaths a game. Honest rosters, cover chases, and
rosters that count committed chasers are each level against oc-cl2-base, at 49.3-50.5%. The common incoherence (a
free ally beside a fleeing mate's pursuer that does nothing) is blocked by the fight model, not by missing
information: once the ally is told, its chase trade is still lost 4 times in 5. Only one thing came of it: honest
rosters cut out-of-fuel turns by ~10%. Stopped after 2 rounds. Variants: `cl2-team`, `cl2-team-h`, `cl2-team-c`,
`cl2-team2`, `cl2-team2c`.
