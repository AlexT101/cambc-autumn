# bots/fish: a sparring partner modelled on Intercontinental Fish (2026-11-06)

Goal: `bots/fish` = astraeus (37e1eb64) rebuilt to behave like Intercontinental Fish as described in
[FISH_MODEL.md](../fish-2026-11-05/FISH_MODEL.md) and its ladder replays. Fidelity first; the end target is
**60% against astraeus** (Fish wins ~77% of its ladder games), reached by modelling Fish, not by tuning astraeus.

- Reference opponent: `bots/variants/astraeus-37e1eb6` (frozen astraeus, `test_draft` off). A/Bs: `--no-test-draft`.
- Fresh suite seeds reserved for this project: 540000-540999 (dev 540000-540019, confirm from 540100).
- Fidelity scorecard (round 1, agent B): `tools/fish/scorecard/`, results in this directory.
- Fish features are ported in grouped chunks: a single piece may lose alone; judge the whole.
- No behaviour keyed on specific ladder maps: everything must work on unseen maps (A/Bs are mostly generated maps).
  Map features are fine. The draft keeps round 1's camp-gold rule (pick count, camp gold, gold-free maps); round 1's
  128-map ladder table is removed from round 2 on.

## Rounds

1. A: copy + draft/emblems/shop/locks + priority encoding + recall/home/tribute + shared fish maths.
   B: fidelity scorecard (Fish ladder replays vs local games, astraeus as the control).
2. Farming chunk (camp-choice logit, team-union memory in the 8 bytes, camp target, holders, waking, camp micro)
   and combat chunk (positioning, kill override, chase, targets, spells, resets, dashes, spacing, range behaviour).
3. On: scorecard-driven gap fixing, A/Bs.

Each round's agent appends its section to [LOG.md](LOG.md).

## Status (2026-11-06): on hold

- Round 1 read 23.6% against astraeus-37e1eb6, with the ladder-map draft table removed afterwards.
- Round 2's chunks, `bots/fish_farm` (12.6%) and `bots/fish_combat` (11.2%), both lost to round 1. They are merged
  into `bots/fish` behind `fish::use_farm` and `fish::use_combat` (2026-11-06; the merge is unmeasured) and the copies
  deleted: set a switch to false to get round 1's farming or combat back.
  Parts that were level alone (strike target, step order, late contagion, HoR shield, Willow heal) can be kept.
- Proposed round 3, not started: rebase on round 1 with the level parts; check `fish_math`'s D and danger against
  `tools/fish/combat_common.py` on identical states (round 2's engage rate fell below Fish's: 38.5% against 58.6%);
  feed the camp-choice logit into astraeus's farm machinery instead of the new farm turn; run Fish's engage and kill
  rules before astraeus's retreat logic.
