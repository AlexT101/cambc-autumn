# Replay weaknesses of charybdis and ocean (2026-11-11)

These are the first reads from the replay tools `analyze.py --reports macro,losses`, `triage.py` and `abdiff.py`
(tools/replay/README.md, "Weaknesses"). No games were played for them: they come from replays already on disk.

## Sets
- **charybdis against ocean:** `replays/batch-20261111-183545-ab-chy-vs-ocean-d18-hold`, 240 games (charybdis-5564637
  against ocean-chybase, own drafts). charybdis won 148.
- **Against astraeus, 128 ladder games each:** charybdis in `replays/batch-20261111-190139-ab-chy-vs-ast-40k-ladder`
  (won 94), ocean in `replays/batch-20261111-190708-ab-oc-vs-ast-40k-ladder` (won 93).
- **Live:** 351 of the 520 v115 scrims (v115 = ocean 506) against Fish and Mite, taken from the ladder-scrims data.
  v115 won 235.

`reports/` holds each report as written: `losses-<focus>-<opponent>.md`, `macro-<focus>-<opponent>.md` and
`abdiff-chy-oc.md`. Their example refs (`GAME rROUND #champion`) name a game by its id, so they can be found in those
batches. The extracted analysis dirs were session scratch and are gone, so remake them with `extract.mjs` before
running `triage.py`.

## charybdis
- **Allies stand still 10+ rounds beside a tributing Prism.** This costs 11.9 [0.6..24.1] gems a game more than ocean,
  and 12.3 [1.8..30.6] against astraeus.
  - The cause is the bag: the Prism carries 200+ gems for 265 rounds a game (ocean 152), and a tribute lasts
    ceil(bag/10) turns.
  - The bag itself also dies: in `590d110dfeba742f` r754 a 1,422-gem tribute was killed in two rounds.
  - Code: `economy/bank.cc` `banks_bag` / `retaining_gems`, `combat/support.cc` `local_support`.
- **Leaving enemy-half camps it has mostly cleared, at even numbers or better:** 3.7 [0.9..6.6] a game.
  Code: `economy/capture.cc` `holding_capture` / `contest_capture`, `economy/crew.cc`.
- **Deaths at Elk camps:** 3.5 [0.4..7.0] a game. Code: `economy/camps.cc`, `combat/fight.cc` `camp_exit_way`.
- **Its losses fall behind later than ocean's** (median break round 371, against 183 for ocean), and 41% of them fall
  behind in a fight window. A Prism dying with 200+ gems starts 15 of its 92 losses against ocean.

## ocean
- **Early deaths cost it most of its losses to charybdis.** 72% of those losses fall behind on farming, with a median
  break round of 183.
  - In those windows ocean is dead on 12% of its turns (charybdis 2%).
  - In rounds 1-150 it wins 20% of the games where it loses more turns to death, and 57% of the rest.
- **Dying while walking with a small bag:** 49 [30..66] gems a game more than charybdis. The hazard is 1.36 against
  0.76 deaths per 1000 rounds of walking with gems.
  - Mostly on its own half, and not outnumbered.
  - Against Fish and Mite the hazard is level, but ocean carries gems longer (held 99.5 rounds against 66.9).
  - Code: `economy/bank.cc` `carry_bag` / `banks_bag`, `combat/fight.cc` `want_home`.
- **Not recalling a big Prism bag inside a safe window:** 45 gems a game (charybdis 19). Code: `combat/fight.cc`
  `want_home` / `recall_line`.
- **Live, starting fights 2+ down while an ally 9-16 tiles away never joins:** 24.7 against 6.8 gems a game.
  Code: `combat/plan.cc`, `combat/fight.cc` `prey`.
- **Live, waiting that Fish and Mite almost never do** (3.9% of ocean's turns against their 0.5%): beside a tributing
  ally, in standoffs, and with a farmable group in reach.
- **Against astraeus,** 37% of its own-half capture gems are stolen in its losses, against 7% in its wins. That is 35
  losses, so treat it as a pointer.

## Both bots
Only about 52% of a team's living champions are within 8 tiles when a fight starts. The absent ones are mostly walking
more than 16 tiles away (0.8 a fight).

## Caveats
- The stall detector's "farmable group in reach" context was right on 3 of 5 cases opened. Open those cases before
  acting on them.
- Excess is our cost minus the opponent's in the same games. A side that spends more time doing something can show a
  higher cost without a higher hazard, so the report also gives hazards per 1000 rounds of each activity.
