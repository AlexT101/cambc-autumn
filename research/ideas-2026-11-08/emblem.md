# Emblems: is ocean's shop costing games against Fish and Mite? (2026-11-08)

**No lever.** Ocean's builds match Fish's and Mite's at the family and stat level. Fish's distinctive Capture-first
build doesn't pay in Fish's own games. Live games between our versions that first diverge at a shop decision split
evenly. No arm was built. Tools are in [emblem-tools/](emblem-tools/); big files are in `~/tmp-offload/emblem/`
(the archive columns for 11-06 to 11-08, and v90/v91 decoded into `ana/`).

## Data

- **Live scrims:** v86-v91 against Fish and Mite. That is 3,215 games: the decoded set in `bigl/ana`, plus v90 and v91
  decoded here. `live_items.py` gives per-champion items, gold and earnings at checkpoints.
- **big-arm archive, 11-06 and 11-07:** about 20k Fish, 23k Mite and 23k ocean games. Each unit's emblem sequence comes
  with the round it formed. Team gold is read at checkpoints.

## What they buy, against ours

- **First emblems** (archive, 11-07, `desc.py`):

  | champion | Fish | Mite | ocean |
  |---|---|---|---|
  | Vesper | Capture-S 56%, Prospector-S 41% (by map) | Jungle 39%, Prospector 31%, Treasure 14%, Monster 10% (varies per game) | Prospector-S 85% |
  | Vendetta | Capture-H 85% | Jungle 40%, Prospector 21% | Prospector-S 64%, Treasure 21% |
  | Marcella | Prospector-F 79%, Capture by r300 62% | Jungle / Prospector | Prospector-F 74% |

- **Same families by r300-600.** All three end up with the same set of passive families (Prospector, Treasure,
  Monster, Jungle, Capture) by r300-600 (`tab.py`, live). Only the order differs.
- **Fish's late stacking.** Fish stacks Bruiser-S/H on Vesper where ocean mixes Power and Bruiser. Fish's Vesper has a
  health share of 0.29 at r400, against ocean's 0.21. Every other type's stat share is close (`stats.py`).
- **Unspent gold.** Fish's Vesper carries more of it (83-125 against our 29-36 at r150-300).
- **Why they own more.** They earn more (the carry.md gap), not because they spend differently.

## Does it turn into results in their own games?

Comparisons are within (day, map, side) cells, controlling for team and opponent gold at r50 and opponent rating.
Standard errors are clustered by cell (`fe.py`, `fe2.py`).

- **Fish: Capture-first loses to Prospector-first.** Fish's Vesper is the reverse of the lead: Prospector-first beats
  Capture-first by +170 ±52 gold at r200, +358 ±118 at r400 and +8.4 ±4.3 points of win%. Fish's Vendetta reads the
  same: Prospector-first +130 ±47 and +365 ±131 gold, +5.0 ±2.7 points.
- **Capture owned by r200/300, at a fixed emblem count:**
  - Fish's Vesper reads positive (a cell mix of Prospector maps).
  - Fish's Vendetta and Marcella read level or −70 gold.
  - Mite's champions read level or negative in gold.
  - Ocean's read level in gold.
- **Mite's per-game choice:** Jungle, Prospector and Treasure first are level in gold and win (±3 points). No emblem
  family turns into gold.
- **Caveat.** Families chosen from state (Hunter after kills, "none" when broke) show large reverse-causal gaps. They
  aren't levers.

## Live paired divergence: v89 against v90 (soup-k) and v91 (oc-base29)

`diverge2.py` takes paired r2 cells and finds the first event that differs. It then counts the flips by that event's
kind.

- **First divergence at a shop:** 39 pairs, flips 5-3 (v89-v90); 12 pairs, 0-1 (v89-v91). soup-k's emblem constants
  (fight_weight, trib_min_bag) don't explain its live result.
- **Where a cheaper cast replaced a move** (`move/cast`): flips 6-1 (v90) and 13-2 (v91) for v89, the dearer
  `cast_cost`. These are mostly Cassi's CC and Damage, and Prism's AoE. All casts first: 22-16 for v89 in v91's pairs.
- **lock_place/tribute_start** (oc-base28's deny-lock change): 9-1 for v89. lock_place/recall_start: 29-33.
- **Overall:** v91 against v89 is −14 over 470 paired games (z −1.22; Mite −10). Cast_cost 29.12 is the soup-k
  component to suspect, not its emblems.
