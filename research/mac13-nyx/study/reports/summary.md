# Summary

Set: replays/batch-20261113-020034-ab-mac13-nyx-basedbg-ladder (128 games, 127 clusters).

Extraction 7.5 s (128 games, 8 processes), reports 3.7 s. Highlights are generated from the reports and need a human check; every report cites game dirs and rounds.

Reverse causality: winner-vs-loser differences partly reflect winning (a team that is ahead dies less, banks more gold and fights on its own terms). Prefer the early-window and lead-conditioned comparisons, and treat the rest as correlations. CIs are 95% cluster bootstraps over match groups (ladder: one five-game group = one cluster; local batches: one map pair = one cluster); c = clusters.

Bots change version over time and replays carry no version information (group.json `submissionId`/`version` are null); use `--since` to restrict to recent ladder groups.

## Macro: turns, gems, cohesion, control, losses ([macro.md](macro.md))

- winner vs loser: alive turns walking (with or without gems): -5.5pt (better)
- winner vs loser: alive turns at work: hitting camps, holding captures, tributing: +3.6pt (better)
- winner vs loser: alive turns in fights (dealt or took champion damage): -0.5pt
- winner vs loser: alive turns waiting still by a respawning or live camp, or by an altar, without hitting or holding: +2.1pt
- winner vs loser: champion turns dead: -9.2pt (better)
- winner vs loser: walked steps beyond the straight (Chebyshev) line of each walk leg / steps: -4.2pt (better)
- winner vs loser: walk turns per gem earned (captures and kills): -2.8 (better)
- winner vs loser: gems earned (capture shares + kill bags) per 100 rounds: +62.6 (better)
- all games (loser's view): break window cause farm in 65/128; break round median 310; whole-game winner advantage farm 317, fight 421 gems

CSVs: `macro-paired.csv`, `macro-early.csv`, `macro-families.csv`, `macro-turns.csv`, `macro-walks.csv`, `macro-roles_focus.csv`, `macro-roles_other.csv`, `macro-gemflow.csv`, `macro-phases.csv`, `macro-absent.csv`, `macro-numbers.csv`, `macro-contests.csv`, `macro-contest_types.csv`, `macro-capacity.csv`, `macro-causes.csv`, `macro-components.csv`, `macro-window_turns.csv`, `macro-triggers.csv`, `macro-breaks.csv`

## Loss episodes: where value is lost, clustered and priced ([losses.md](losses.md))

- loser: Prism killed with 200+ gems while walking with gems: 69.9 gems a game against 4.8 for winner (0.16 a game, alone v2+ 45%, seen 6+ 50%, own half 70%, held its ground 65%, heading elsewhere 60%); look at economy/bank.cc carry_bag / banks_bag (route and when to bank); combat/fight.cc want_home; e.g. 9af6ba6844bffaa0 r985 #4 (891); 1a53508aef8b96ee r942 #2 (884)
- loser: camp invaded (own half): ours within 8: 67.2 gems a game against 23.4 for winner (2.03 a game, 1G 18%); look at economy/farm.cc farm (target choice and map coverage); economy/altar_guard.cc guard_turn; e.g. 1c9a6c8dd8810a58 r960 (192); 1c9a6c8dd8810a58 r564 (189)
- loser: camp invaded (own half): ours 9-20 away: 72.0 gems a game against 40.4 for winner (2.49 a game, 1G 29%); look at economy/farm.cc farm (target choice and map coverage); economy/altar_guard.cc guard_turn; e.g. 9b1594455a9da4c8 r486 (201); f148cc299e8ab50c r96 (137)
- loser: Prism killed with 200+ gems while fighting: 33.7 gems a game against 2.2 for winner (0.09 a game, grouped, even+ 64%, seen 6+ 64%, own half 45%, walked toward them 64%, heading toward an altar 45%); look at combat/plan.cc (strike search) and combat/fight.cc prey / chase_with_guard (who to engage); e.g. b29a405bf7050285 r613 #2 (758); 9af6ba6844bffaa0 r1655 #4 (554)
- loser: camp contested (mid half): ours left, outnumbered: 42.3 gems a game against 11.1 for winner (0.49 a game, 2G 1W 6%); look at economy/capture.cc contest_capture / yield_capture; combat/plan.cc (fight on the tiles); e.g. 7370caf6b518da93 r1573 (614); 7370caf6b518da93 r1833 (565)
- loser: Cassi killed with 0 gems while walking: 41.5 gems a game against 10.8 for winner (0.61 a game, grouped, even+ 47%, seen 6+ 42%, own half 81%, walked toward them 54%, heading toward an altar 45%); look at model/safety.cc (threat model), combat/guard.cc guard_work / step_safely (step guard); e.g. 8e562f12bb1b18dc r271 #6 (113); 3e14056889eb2885 r503 #6 (100.0)

CSVs: `losses-kinds.csv`, `losses-clusters.csv`, `losses-situations.csv`, `losses-expensive.csv`, `losses-deaths_champion.csv`, `losses-deaths_bag.csv`, `losses-deaths_doing.csv`, `losses-deaths_numbers.csv`, `losses-deaths_warning.csv`, `losses-deaths_half.csv`, `losses-cf.csv`, `losses-hazard.csv`, `losses-exposure.csv`, `losses-fights.csv`
