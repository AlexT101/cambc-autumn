# Exclusive spells and Marcella's gold (ocean, 2026-11-08): six arms, all H0

Two leads from [fight-execution.md](fight-execution.md): (1) Cassi and Marcella leave their exclusive damage spell unused
where Fish casts; (2) Fish's Marcella has ~146 more gold at r400 (Focus 217 vs 159).

## Arms (on `variants/oc-base25`, compile-time knobs, 1.0 = identical build)

- `excl_spell_gain` (combat/plan.cc `Search::spell_unit`): the strike search's `hit_worth` of a non-stunning exclusive
  unit spell on an enemy champion, x gain. Arms g150, g200, g300.
- `excl_retreat_gain` (combat/abilities.cc `enemy_cast`, unit branch): the same x gain on the retreat/branch-R cast
  when the walk is still available (not escaping, not stunning). Arm r200; b200 = both at 2.0.
- `marcella_gold_w` (economy/capture.cc `relative_efficiency`): Marcella's `kept_efficiency` x w, so captures route
  more gold to her. Arm m200.
- Diff kept at `~/tmp-offload/spell/logs/oc-sp-b200.diff` (+ `oc-sp-m200-vs-b200.diff`); variant dirs deleted.

## Results against oc-base25

Own drafts, fastrunner, `merged/sp-scr-1070`, `--sprt 0.50,0.5025 --sprt-min-games 20000`, own seed each:

| Arm | Games | Win % | 95% CI | SPRT |
|---|---|---|---|---|
| g150 | 20,003 | 49.76 | 49.07–50.46 | H0 |
| g200 | 24,731 | 49.86 | 49.23–50.48 | H0 |
| g300 | 33,721 | 49.93 | 49.39–50.46 | H0 |
| m200 | 25,532 | 49.57 | 48.95–50.18 | H0 |
| r200 | 30,276 | 49.50 | 48.94–50.06 | H0 |
| b200 | 33,168 | 49.53 | 48.99–50.07 | H0 |

## Why

Read from 800 kept screen replays an arm (mirror, cand side vs base side; spell-ready turns with an enemy within 4;
`bin/abcast.py`, `bin/teamgold.py`) and a 150-map debug trace (`an/trace-*.txt`).

- **The strike-search knob (g\*) barely moves casts.** 63% of Cassi's spell-ready turns at 2-4 tiles (90% adjacent)
  go to the retreat branch, which never runs the strike search. g200: Cassi 2-4 cast 31.7% vs 32.3%; Marcella
  adjacent +2.5 points (searched turns already cast 89-95%).
- **The retreat knob (r200) makes Cassi cast like Fish, and nothing follows.** Cassi at 2-4: cast 30.6% → 53.1%;
  adjacent 18.3% → 61.2%; spell damage per ready turn 83 → 135. Deaths within 2 rounds unchanged (8.3% vs 8.3% at 2-4,
  28.1% vs 29.7% adjacent). Kills: per ready turn 0.017 → 0.026, but the cooldown cuts ready turns (12,951 → 9,356),
  so Cassi's spell-turn kills are 250 vs 231 in 796 games: **+0.02 a game**. The extra casts are chip damage on
  healthy targets that walk off and heal; the forecast's "Fish's rate x our kill-per-cast" (≤ +0.29 kills, ≤ +1
  point) assumed the marginal cast converts like the average one. Cassi was forecast +0.17; she got about an eighth of it.
- **The gold weight (m200) is zero-sum inside the team, and negative.** At r400 Marcella earned 566 vs 481 (Focus 171
  vs 156), but her teammates 921 vs 1151, so team gold 1486 vs 1632 (−146, se ~82; the g200 control reads −49).
  Her kill rate did not rise (adjacent ready turns 0.086 vs 0.089). Fish's Marcella edge came with the same team gold
  (gold-rich captures: clusters, Prospector, Treasure), so it is an allocation of *which* captures, not a weight on
  how much she gets; a weight just takes captures from teammates who farm them better.

## Lesson

A cast-rate or gold-share gap to Fish is not a lever by itself: ocean already declines the casts that don't convert
(raising them doubled Cassi's casts for +0.02 kills a game) and already routes gold near-efficiently (moving more to
Marcella cost the team 146 gold at r400). Compare kills and team gold, not per-champion rates, before building an arm.
