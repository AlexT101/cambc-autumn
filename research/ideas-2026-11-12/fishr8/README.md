# Fish r8 (2026-11-12): what changed, where the wins went, and the body fr8-g25

Intercontinental Fish changed twice on 11-12. The live pin moved from r2 to r8. v118 (`variants/lab-emb6-c520-ps`) won
195 of 340 games against r8 (57.4%). On the same 235 cells, r2 gave 181 wins and r8 gave 132: 21 cells flipped for us
and 70 against.

Data:
- Our live scrims: capture rows from big-arm, joined to the scheduler's tasks (`ours.py`). Replays are pulled by
  `sync.py` into `~/tmp-offload/fishr8/live/`.
- Fish's ranked games: `meta.py`.

## 1. What changed

**Draft.**
- Vesper is now Fish's first pick in most cells: its ranked slot 0 went from 55% Marcella to 20% Marcella.
- Across 340 cells, Vendetta was dropped from 166 and Marcella from 120. Varg was added to 94 and Tavi to 40. Ryth is
  new. The team changed in 224 cells.
- The draft is deterministic and does not depend on side.
- Fish's ranked win rate went from 57.5% (670 games) to 74.7% (75 games).

**Not only the draft.** Paired v118 cells, r2 to r8: 186 wins became 139 of 245.
- On cells where the draft changed: 112 became 85 (46 cells flipped against us, 19 for).
- On cells with the same draft: 74 became 54 (24 against, 4 for).

**A Vesper carry** (matched cells, r2 to r8):
- Her share of Fish's capture gold went from 0.57 to 0.79 by r100, and from 0.52 to 0.70 over the game.
- Fish's capture gold to r300 rose by 378 (z 6.5, about +21%).
- Her build (r8):
  - Capture-S at r60, Treasure-S r84, Jungle-S r137, Monster-S r158, Hunter-H r194, then Prospector.
  - Bruiser-S about r349.
  - Greed-S about r511 and Greed-H about r591 (Greed in 72% of games, median r454).
- At r600 her Strength went from 289 to 460 and her max HP from 3.8k to 6.7k.
- Her deaths fell from 1.41 to 0.72 a game and her kills rose from 1.82 to 2.77. She now makes 62% of our deaths
  (42% before). On same-draft cells her kills went from 1.5 to 3.6.
- She farms Fish's own half: 15 of 18 captures to r300 (`where.py`), with Vesper on 6.7 of them (r2: 2.9). Denying
  her gold would mean invading.

**Other changes.**
- Varg is a passive farmer (0.07 kills a game).
- Fish banks less often, with bigger bags: first tribute r195 became r235.

**Priority encoding.**
- r8 writes `old << 20` plus 20 random low bits, rewritten every round. `v >> 20` recovers the old `-rank - (n+1) level`.
- In the rank, Heart of Ruin comes after Varg on the base-health tie.
- opp_detect read r8 as unknown in 100% of instances.
- `oppd-r8.patch` (3 lines, against `variants/c520-mx`'s `opp_detect.cc`) fixes it. Checked with `det_r8.py`
  (bcexploit's det3 mirror) on 244 live r8 games:

| instances read as Fish | r100 | r300 | r500 |
|---|---|---|---|
| r8, current detector | 0% | 0% | 0% |
| r8, with the fix | 52% | 76% | 89% |
| r2, with the fix | 50% | 71% | 81% |

  r2 detection is unchanged. There are no false Fish reads on the Mite, BattleCats or other-team datasets.

## 2. Where the wins went

**Long games.** Over 800 rounds we now win 34-38% (r2: 68-74%). In the cells that flipped against us:
- Fish's gold lead is already there at r200 and widens.
- Fish's kills rise to about 3.2 per 200 rounds from r400, about 2 of them Vesper's.

**Prism's hoard.** Our Prism carries its gems for Focus until the bag wins or the game closes (`keeps_gems`). In the
135 live r8 games with our Prism (`prismloss.py`):
- It loses 116 gems a game to deaths, 99 of them to Fish's Vesper (r2: 69 and 21).
- In 33 games (24%) Vesper took 100 or more. We won 6% of those, against 78% of the 98 games where she took none.
- Her kills of our Prism come with a median bag of 215, at a median round of 612.

**Early exposure** (r50-450):
- Fish's Vesper is near ours about 67 rounds a game, and we hit her in 9% of those rounds (15-30% when we have the
  numbers).
- She dies 0.21 times a game early.

## 3. The body: `fr8-g25` (`fgate --fish-body fr8-g25`)

Built on `variants/c520-ps` by `mkbody.py`:
- Fish r8's draft: an exact pick table keyed by map hash for 336 cells (`hashes05.json` adds the 05-maps), and
  otherwise the r8 pick model `fitgen.py`. Held out, it gets the champions right 0.91 / 0.76 / 0.86 of the time for
  3 / 4 / 5 picks.
- `mitefit/rule_vcarry.py`.
- `mitefit/rule_vesper.py 0 --build capture-s,treasure-s,jungle-s,monster-s,hunter-h,prospector-h,bruiser-s,greed-s,greed-h`.
- `rule_gold.py 2.5`: farm's gold price x2.5.
- Noise 0.2 on 19 knobs. The run time gives the member seed and salt.

`bots/variants/` is gitignored, so rebuild the body with:

    V=research/ideas-2026-11-12/mitefit; B=capture-s,treasure-s,jungle-s,monster-s,hunter-h,prospector-h,bruiser-s,greed-s,greed-h
    py research/ideas-2026-11-12/fishr8/mkbody.py fr8-g25 --py "$PWD/$V/rule_vcarry.py" --py "$PWD/$V/rule_vesper.py 0 --build $B" \
        --py "$PWD/research/ideas-2026-11-12/fishr8/rule_gold.py 2.5"

mkbody reads `~/tmp-offload/fishr8/fm/fm_draft_F.h` (fitgen.py's output), `ours.json` and `hashes05.json`.

The other bodies:
- `fr8-c0`: draft only.
- `fr8-v1`: + vcarry and the Vesper build.
- `fr8-v1f`: v1 + `--set chip_value=0.03 --mul life_value=0.35`.
- `fr8-v2`: `rule_vesper 4`.
- `fr8-g16` / `fr8-g25f`: gold x1.6 / g25 + the v1f constants.
- `fr8-g16c`: + `fishfid/patch_coh.py 0.5`.
- `fr8-p5` / `fr8-p2` / `fr8-p5f`: g25 + `mitefit/rule_packv.py` 0.5 / 0.2 / and the v1f constants.

**Calibration**, our win % on the 168 ranked maps (`calib.sh`, `calrun.sh`, `calread.py`; 4 members × 336 games, `p*`
2 members):

| our bot | live r8 | rt-Flp4 | fr8-c0 | fr8-v1 | fr8-g25 | fr8-g25f | fr8-p5 | fr8-p2 |
|---|---|---|---|---|---|---|---|---|
| v115 oc-dfuel-506 | pending | – | 56.0 | 58.0 | 58.6 | 59.1 | – | – |
| v116 charybdis-p3 | pending | – | 68.5 | 65.9 | 64.6 | 65.3 | – | – |
| v117 c520-ps | 49.7 (42.1-57.3) of 165 | 82.9 | 69.0 | 67.6 | 67.0 | 66.5 | 69.2 | 74.4 |
| v118 lab-emb6-c520-ps | 57.4 (52.2-62.6) of 345 | 84.5 | 68.2 | 69.3 | 68.2 | 68.2 | 69.5 | 76.3 |

- The fr8 bodies account for about 16 of the 19 points the old Fish body (Flp4) misses.
- Packing on Vesper makes the body weaker.

**livefork** (`fr_livefork.py`, forkcomp's runner; 70 live v117 r8 games, 193 forks): body minus live is +9.6 ±4.1
points for fr8-g25 (r100 +12.9, r300 +10.0, r600 +4.7), and +11.4 ±4.5 for fr8-c0.

**What it misses** (`fidelity.py`; live r8 has 244 games):

| | live | fr8-g25 |
|---|---|---|
| Fish gold r100 / r300 / r600 | 569 / 2033 / 4596 | 475 / 1753 / 4058 |
| Vesper Strength r600 | 431 | 353 |
| Vesper max HP r600 | 5957 | 4115 |
| Vesper kills a game | 3.06 | 2.08 |
| Fish kills per engagement | 0.351 | 0.267 |
| Our deaths a game | 7.5 | 5.6 |
| Prism gems lost to Vesper, per Prism game | 99 | 37 |

The body is still about 10 points easier than live. The gap is mostly early economy and Fish's fights. It is as
far as the c520-ps base goes, like the Mite bodies' fed Vesper.

## 4. Counter: none built

**No candidate.** Neither lever the data points to has a cheap form left to test.
- Prism's hoard is the largest loss channel, but every form of banking or caution for it has lost locally:
  - never keep gems: 32.7;
  - cap at 150: 46.7;
  - bank at enemy score + bag: -2.0;
  - bank under threat: 42.8-49.5;
  - eight hoard-survival arms on 11-11: all level.
  Its Focus is its damage.
- Focusing or avoiding a fed Vesper doesn't pay (mitere).
- She farms her own half, so denying her gold would mean invading.

**No way to measure one locally.** A counter aimed at the fed Vesper could not be read on this body anyway: Prism loses
37 gems a game to her here, against 99 live.

**What carries over.** The opp_detect fix is ready for any Fish-specific arm. Gate such an arm on a forced copy: the
bodies write c520-ps's priorities, not Fish's.

## Files

Data:
- `meta.py`: big-arm Fish rows.
- `ours.py` and `sync.py`: our live r8 scrims and their replays.
- `live_ds.py`.

Statistics:
- live: `fishx.py`, `vesper.py`, `traj.py`, `opening.py`, `vexpo.py`, `ourdeaths.py`, `prismloss.py`, `where.py`;
- comparisons: `cmp.py`, `cmpcell.py`, `champ.py`, `builds.py`, `prio.py`;
- local runs: `fidelity.py`, `bodystats.sh`, `localrows.py`.

Body:
- `fitgen.py` (the pick model), `mkbody.py`, `rule_gold.py`.
- `calib.sh`, `calrun.sh`, `calread.py`.
- `fr_livefork.py`.

Detector: `det_r8.py`, `oppd-r8.patch`.

Working data is in `~/tmp-offload/fishr8/`.
