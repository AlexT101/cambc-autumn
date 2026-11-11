# Handoff: the rest of ATLAS's change, if it can be made cheap enough (2026-11-11)

**Goal:** ship the parts of the ATLAS programme that CHANGES 517 left out, by making them cheap enough to keep their
gain at the real 100k budget. They win at 2x fuel and lose it at 100k, where charybdis already runs out of fuel about
5.6 turns a game.

## What shipped and what is left

CHANGES 517 shipped fixes 1, 2 and 4 (stunned-enemy turn order, the fight simulation aiming at the asker, retreat
taking a survivable step over a walk-excluding cast): 50.4% of 61,440 at 100k, out-of-fuel turns +6.4%.

Left out, all in [patches/remaining-after-517.diff](patches/remaining-after-517.diff) (ATLAS's final bot minus 517;
apply it on 517, with `world.h` and `turn_window.*` the likeliest to need hand placement):

- **Fix 3, stun then cast:** `lethal()` adds the follow-up enemy turn when a stun lands before our next turn
  (`Safety` stun follow-up). 101 traced kills, 13.5k gems.
- **Fix 5, cooldown about to return:** retreat ranks steps by the enemy's reach once its lethal slot is back
  (`retreat_step`). Most of 550 no-walk-out kills, small bags.
- **Merge fixes** from combining 3 and 5 with 1, 2 and 4: `retreat_step` demotes lethal steps when fix 4 hands it the
  walk, and a double-counted stun turn in the follow-up is fixed. Take 3 and 5 from this diff, not from the earlier
  `mo1-pz35-s2` copy, which still has the double count.
- **The press:** an enemy whose damaging slots are on cooldown for 2+ turns becomes prey when our pack's damage over
  that window kills it, and retreat verdicts resting only on it are replayed without it (`press()`,
  `press_taken()`, `params::press`).
- **Fuel floors** (`params.h`): `press::min_fuel` 60k (press off below it) and `refine_fuel` 40k (fixes 2-5 fall
  back to the old code below it). Fixes 2 and 4 shipped without a floor, so on 517 the floor covers 3, 5 and the
  press only.

## Measurements (against charybdis 515, own drafts)

| Version | 2x fuel win % | 2x OOF, candidate vs ref | 100k win % | 100k OOF |
|---|---|---|---|---|
| fixes 1, 2, 4 (= 517) | 50.5 of 10,240 | 515 vs 484 (+6%) | **50.4 of 61,440** | +6.4% |
| fixes 3, 5 alone | 50.6 of 10,240 | 800 vs 476 (+68%) | not run | |
| all five (c1) | 51.0 dev; 51.2 of 19,200 pooled | 763 vs 481 (+59%) | 49.7 of 2,560 | 18,486 vs 15,230 (+21%) |
| c1 + press (press-s2) | 51.5 dev; 51.7 of 19,200 pooled | 1,071 vs 471 (+127%) | 48.2 of 2,560 | 33,052 vs 15,481 (+114%) |
| with floors (pressf, ATLAS final) | 51.4 dev; **51.8 of 19,200** pooled | 722 vs 460 | 49.7 of 7,680 | 65k vs 46k (+41%) |

The 100k cells for c1 and press-s2 are 2,560 holdout games, so they carry about ±2 points of noise. The pressf cell
is 7,680 games. Over 19,200 games at 2x, the parts beyond 517 are worth about +1.3 points.

## Where the fuel probably goes (unmeasured; check it first)

- Fix 3 makes `lethal()`, which runs for many tiles every turn, look one enemy turn further after a stun.
- Fix 5 adds another reach evaluation per candidate retreat step.
- The press replays the retreat and stand verdicts without the pressed enemy, and simulates the pack's damage over
  the disarm window.

ATLAS suggested a per-tile, per-turn memo of the lethal-tile test, and computing the stun follow-up from the reach
tables that already exist instead of a second pass.

## Suggested method

1. **Profile before optimising.** Use the fuel census (`tools/fuel/census/`, see tools/README.md "Fuel census"):
   instrument a debug copy of 517 + the remaining diff, play it at 100k, and tabulate fuel by component for
   out-of-fuel and heavy turns. Find which of fix 3, fix 5 and the press costs the most, and on which turns.
2. **Make that part cheaper, or bound it.** The saving can be exact (`tools/fuel/bench.py` identical at 100M) or
   fuel-aware (a budget, or a cheaper method on a short turn), which AGENTS.md allows when it wins by A/B.
3. **Judge every step at the real budget.** A/B against charybdis 517 at default fuel, 20k+ games on fresh
   `ladder-v2` maps no A/B has used, both on their own drafts (`--no-test-draft`). Compare out-of-fuel turns as well
   as win rate. Don't judge at 2x fuel: everything here already wins there.
4. **Add parts one at a time if the whole doesn't pay.** Fix 3 + 5 with their merge fixes is the natural first unit,
   then the press. A part that is level at 100k after optimisation isn't worth its fuel.

## Where the code is

- ATLAS's final bot: branch `macro-o1-20261111`, commit `f68b4f5fd` (local only, not pushed). The same code is
  `bots/charybdis` and `bots/variants/mo1-pressf` in `/home/ubuntu/wt/macro-o1` while that worktree exists.
- Frozen copies there (gitignored, local): `mo1-pz-s2` (= 517's change), `mo1-c1-s1`, `mo1-press-s2`, `mo1-pressf`.
- On main: [patches/final-charybdis.diff](patches/final-charybdis.diff) is the whole ATLAS change against charybdis
  515; [patches/remaining-after-517.diff](patches/remaining-after-517.diff) is what is left.
- The trace analysis that found each gap: [NOTES.md](NOTES.md), "Lethal-reach analysis".
