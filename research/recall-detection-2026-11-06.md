# Telling real recalls from feints (2026-11-06)

Question: astraeus treats a champion's recall as real once it has lasted more than one turn end (`kept_recall`,
`bots/astraeus/src/model/world.h`: remaining `< full - 1`, full 5, or 3 with Home). Would a health condition, or
reading the first window, separate real recalls from feints better? Data only; no bot changes.

Scripts and full tables: [recall-detection-2026-11-06/](recall-detection-2026-11-06/) (`collect.py` gives `counts.json`,
`report.py` gives [tables.md](recall-detection-2026-11-06/tables.md), every rule at every X; `kept.py` gives `kept.txt`).

## Data

| team | games | dates | source |
| --- | ---: | --- | --- |
| Fish | 529 | 2026-11-06 | our ladder scrims against Fish (cambc 5.0.0), Fish's side |
| Mite | 520 | 2026-11-06 | scrims against Mite, Mite's side |
| ocean (ours) | 1049 | 2026-11-06 | the same scrims, our side: v78 (512), v80 (417), v81 (120), all `bots/ocean` variants |
| astraeus self-play | 300 | 2026-11-06 | random 300 of `batch-20261106-160915-ab-gf2-gf2-741` (astraeus-gf2 vs astraeus-0305953), both sides pooled |
| Fish / Mite ladder | 231 / 227 | 2026-10-30 | pre-5.0.0 ladder: the newest Fish/Mite replays we hold (later ladder folders have only `group.json`) |

Replays are deduplicated by sha256 (1925 files, 1777 distinct). They are extracted with `tools/replay/extract.mjs --out replays/.analysis-recall`, with the scrim bundles' `replay.repl26a` copied to `replays/.recall-detection/`.

## Ground truth and the confounder

`extract.mjs` gives each recall's end: `recall_end` (arrival), or `recall_cancel` with the step that removed the channel. The cause is `manual` for the champion's own Cancel step; otherwise `damage` (shield-absorbed included), `stun` or `death`. So voluntary and forced cancels are cleanly separated.

The rule "interrupted = real" does not hold. Every team starts a recall at nearly every turn end, so a champion in a fight carries a fresh feint that the next hit cancels. 13.5-15.5% of all recalls are interrupted before the recaller has had a turn to keep or cancel them. That is about 550 a game per team, against about 45 real ones. Intent is decided at the recaller's next own turn: a turn taken channelling (rounds `turn` code 3) means it chose to keep the recall. So:

- **real** = completed, or kept through at least one own turn and then damaged, stunned or killed;
- **feint** = cancelled by hand at its first own turn;
- **abandoned** = kept through a turn or more, then cancelled by hand. These count with feints, since they never go home. Mite's out-of-fuel turns also carry about 3 feints a game into a 2nd window; they count as feints;
- **undecided** = interrupted before its first own turn. Intent is unknowable. These are left out of precision and recall, and their share among flagged recalls is shown.

The undecided ones are almost all feints. When a champion starts another recall within 2 rounds of the interruption, it keeps that one only 0.8-3.0% of the time. If they were counted as real (the literal definition), first-window rules would look 2-3x more precise than they are (tables.md, last column).

Observation: round-end snapshots. Window k has `chanT = full - k`, which is what a champion acting before the recaller's next turn reads. Recalls interrupted in their own start round have no window (about 1.5%, all undecided). The 2s tables in tables.md repeat everything using only windows an enemy saw.

## 1. Counts (per game)

| team | started | real | (completed / kept, then interrupted) | feint | abandoned | undecided |
| --- | ---: | ---: | --- | ---: | ---: | ---: |
| Fish | 3942 | 44.7 | 38.7 / 6.0 | 3226 | **110.9** | 560 |
| Mite | 3721 | 44.6 | 43.2 / 1.5 | 3112 | 1.1 | 563 |
| ocean (scrims) | 3878 | 48.9 | 48.0 / 0.9 | 3272 | 8.9 | 547 |
| astraeus (self-play) | 7726 | 96.0 | 94.2 / 1.8 | 6574 | 15.9 | 1040 |
| Fish 10-30 | 3355 | 42.1 | 40.9 / 1.2 | 2822 | 2.2 | 488 |
| Mite 10-30 | 3616 | 42.2 | 41.4 / 0.8 | 3013 | 2.1 | 559 |

Undecided recalls are mostly damage (about 95%), then stun and death. Real recalls interrupted after being kept are 2-13% of real ones: Fish 13.5%, the others 1.8-3.3%. Self-play has two astraeus teams per game, hence the doubled rates.

## 2. Rules: precision / recall, %

Per recall: precision = real / (real + feint + abandoned) among flagged recalls; recall = flagged real / all real.

| rule | Fish | Mite | ocean | astraeus | Fish 10-30 | Mite 10-30 |
| --- | --- | --- | --- | --- | --- | --- |
| (a) any recall | 1.3 / 100 | 1.4 / 100 | 1.5 / 100 | 1.4 / 100 | 1.5 / 100 | 1.4 / 100 |
| (b) first window | 1.3 / 100 | 1.4 / 100 | 1.5 / 100 | 1.4 / 100 | 1.5 / 100 | 1.4 / 100 |
| **(c) 2nd+ window (current)** | **28.0 / 96.5** | **91.3 / 99.5** | **84.5 / 99.8** | **85.7 / 99.8** | **94.9 / 99.9** | **92.4 / 99.6** |
| (d) first window, hp<25% | 17.9 / 14.7 | 18.4 / 15.2 | 15.1 / 12.6 | 12.0 / 12.9 | 23.7 / 15.9 | 16.1 / 13.5 |
| (d) hp<33% | 17.8 / 25.2 | 18.0 / 28.2 | 12.0 / 18.3 | 10.0 / 19.1 | 23.4 / 28.3 | 14.8 / 20.1 |
| (d) hp<50% | 10.8 / 45.6 | 11.2 / 48.2 | 8.0 / 29.7 | 6.6 / 30.0 | 12.1 / 50.5 | 10.3 / 36.8 |
| (d) hp<66% | 6.5 / 57.1 | 8.2 / 64.0 | 5.9 / 41.0 | 4.9 / 40.8 | 7.3 / 61.0 | 7.5 / 52.0 |
| (d) hp<75% | 4.6 / 61.3 | 5.8 / 69.0 | 5.1 / 48.0 | 4.2 / 47.3 | 5.3 / 65.2 | 6.0 / 61.1 |
| (d) hp<100% | 2.8 / 81.7 | 2.9 / 87.8 | 3.3 / 71.4 | 2.8 / 70.6 | 3.0 / 84.8 | 2.8 / 85.6 |
| (e) 2nd+ window, hp<25% | 81.5 / 14.3 | 97.3 / 15.1 | 86.5 / 12.5 | 84.9 / 12.9 | 91.2 / 15.8 | 95.5 / 13.4 |
| (e) hp<33% | 83.5 / 24.5 | 97.9 / 28.1 | 84.7 / 18.2 | 83.4 / 19.0 | 92.5 / 28.1 | 95.1 / 20.0 |
| **(e) hp<50%** (the proposed rule) | **76.0 / 44.3** | 97.4 / 48.0 | 85.0 / 29.6 | 83.1 / 29.8 | 92.7 / 50.2 | 93.7 / 36.5 |
| (e) hp<66% | 65.1 / 55.4 | 96.7 / 63.7 | 84.9 / 40.8 | 83.3 / 40.7 | 92.9 / 60.9 | 94.2 / 51.6 |
| (e) hp<75% | 56.7 / 59.4 | 95.9 / 68.6 | 85.1 / 47.8 | 83.4 / 47.2 | 93.2 / 65.1 | 94.6 / 60.8 |
| (e) hp<100% | 40.8 / 78.8 | 94.3 / 87.3 | 84.9 / 71.2 | 84.6 / 70.4 | 94.3 / 84.6 | 94.1 / 85.2 |
| (c) or (d) hp<33% | 21.2 / 97.0 | 42.0 / 99.6 | 40.2 / 99.8 | 35.1 / 99.9 | 51.1 / 100 | 44.8 / 99.7 |
| (c) or (d) hp<50% | 13.8 / 97.4 | 20.4 / 99.8 | 21.9 / 99.9 | 18.6 / 99.9 | 21.4 / 100 | 23.5 / 99.8 |

The (d) rows at 25/66/75% and every (f) row are in tables.md. Restricted to windows an enemy saw (tables.md, 2s), precision is within a few points; recall drops to 27-48%, because most recalls are never seen.

For kept recalls only (`kept.txt`), the share real at the 2nd window, by health:

| team | hp<33% | 33-50% | 50-100% | full |
| --- | ---: | ---: | ---: | ---: |
| Fish | 83.5 | 68.4 | 25.6 | **11.7** |
| Mite | 97.9 | 96.7 | 90.9 | 74.6 |
| ocean | 84.7 | 85.5 | 84.8 | 83.6 |
| astraeus | 83.4 | 82.5 | 85.8 | 88.4 |
| Fish 10-30 | 92.5 | 92.9 | 96.8 | 98.7 |

Gems carried and distance from spawn barely separate them: kept recalls with gems are within ±3 points of those without, on every team. Fish's abandoned recalls are mostly at full health with no gems, far from spawn, cancelled with 1 or 3 turns left (27.8k and 24.4k of 58.7k). Fish did this about 2 times a game on 10-30 and 111 times a game on 11-06, against us.

## 3. Real recalls missed or read late by (c)

| team | real | (c) misses | (d) hp<50% catches of those | (c) one window late | (d) hp<50% reads a window earlier | extra feints + undecided (d) hp<50% flags |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Fish | 23643 | 828 (3.5%) | 219 | 22815 | 10556 | 85545 + 29496 |
| Mite | 23204 | 105 (0.5%) | 57 | 23099 | 11134 | 88168 + 31520 |
| ocean | 51303 | 121 (0.2%) | 57 | 51182 | 15194 | 173820 + 72584 |
| astraeus | 28801 | 54 (0.2%) | 20 | 28747 | 8608 | 121111 + 37865 |

The table at every X is in tables.md. (c) misses only recalls that were kept at the first own turn and then interrupted before the 2nd round end. Every other real recall is read at window 2, one window after it first appears. That delay is built into the feint pattern: in window 1 the recaller has not yet decided. For every real recall that (d) at hp<50% reads a window early, it also flags 11-18 feints or undecided recalls.

## Conclusion

- **Window 1 carries almost no information, for any team.** Everyone feints about 3,000+ times a game, and real recalls are 1.3-1.5% of starts. Even at hp<25%, a first-window recall is real only 12-24% of the time. Rule (d) and (c)-or-(d) are not safe for anyone: at 7-24% precision they would value 3-13 recalls that never go home for each real one.
- **How well (c) works depends on the team.** Mite (91%), our bots (84-86%) and pre-patch Fish (95%) keep only recalls they mean. Post-patch Fish keeps about 111 recalls a game that it later cancels by hand, mostly at full health. So (c) is only 28% precise against Fish.
- **The proposed rule, (c) with hp<50% (rule (e)), helps exactly where (c) fails.** Against Fish, precision goes from 28 to 76% (84% at hp<33%), while recall falls from 96.5 to 44%. Against Mite it adds 6 points of precision (91 to 97%) at half the recall. On our own bots it adds nothing (85% either way) and drops recall to 30%. Health has no signal there: our abandoned recalls are spread across all health levels.

**Recommendation.**
- **Enemies:** keep (c) as the gate, and scale the value of interrupting by health rather than cutting at a threshold. A kept recall at full health is 12% real for Fish and 75% for Mite; below a third it is 84-98% for both. If a single binary rule is wanted, (c) with hp<66% is the most uniform: Fish 65%, Mite 97%, ours 85%. With hp<50% it is Fish 76%, Mite 97%, ours 85%. The cost is about half the real recalls going unvalued. Don't value first-window recalls.
- **Allies:** keep (c). It is 84-86% precise and catches 99.8% of real ones, and neither health nor gems improve it. The one-window delay cannot be inferred away from the observable state. If it matters, the recaller would have to announce its keep in shared memory. That only helps an ally whose turn comes after the recaller's start-turn decision.

Caveats: post-patch Fish and Mite are seen only in scrims against our ocean v78-v81, one day, with the opponents pinned to the bots of their first group. Fish's abandon habit appeared between 10-30 and 11-06 and may change again. "Abandoned" lumps true changes of mind (for example, an enemy appearing) with any other hand cancel; both are cases where the champion did not go home. The self-play maps are one fresh suite (fresh-741001). Precision is per recall: a kept real recall shows up to 4 flagged windows, so counted per window, (c) and (e) look somewhat better.
