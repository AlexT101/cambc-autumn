# Emblem lab round 5: plan and handoff (written 2026-11-10, not started)

For an agent picking this up cold. Read first: `AGENTS.md`, `cambc-rules.yaml` (`economy.emblems`, `economy.shards`),
[README.md](README.md) ("Round 4", "What round 4 found"), [RUNBOOK.md](RUNBOOK.md) (section 9: what went wrong),
and research/EXPERIMENTS.md "Emblem lab round 4 on ocean" (every number below comes from there).

**Status of this document.** The audit (section 2) and the plan (sections 3-8) come from a read-only review of round 4:
nothing in them has been run. "Verified" means read in the code or the records. Two amendments from the round-4
session are marked **[amended]**. The user has not yet said to start.

## 1. Where things stand

- **The bot.** `bots/ocean` is at CHANGES 499 (frozen `variants/oc-skirm-499`): round 2's learned table plus Skirmish
  as every champion's fifth emblem. That copy is the base and the A/B reference for round 5.
- **How ocean chooses an emblem** (`bots/ocean/src/economy/shop.cc`): `best_emblem` takes
  `learned_arm[picks - 3][type][ordinal]` (`emblem_table.h`; 255 = no entry) where set and its passive is not owned,
  else the bot's own pricing (`current_emblem`), then a reactive Tribute rule. Ordinals from 12 on are pricing only.
- **Round 4** played 1,840,000 games (1.28M dense: 35-50% of every decision below ordinal 12 drawn; 560k sparse) and
  fitted per-decision doubly robust sums (`dfit.mjs`, `select.py`). Every table built from the fit lost head to head
  (47.9-48.4% of 20,480 for full selections; level for their early-ordinal parts).
- **What clean A/Bs established** (20,480 games each on held-out maps, ±0.7 at 95%, against ocean 496 unless noted):

  | change | A/B |
  |---|---|
  | no learned table | 47.0% (-3.0) |
  | no table at the purchase only | 47.4% |
  | no table from ordinal 3 on | 48.1% (-1.9) |
  | no table at ordinals 0-2 | 50.3% of 61,440 |
  | late cells without Collectors (39 cells) | 48.3% (-1.7) |
  | late cells without Home / Tribute / Monster / Durability | 49.8 / 50.0 / 49.7 / 49.9% |
  | Collectors as everyone's k-th emblem, k 1 / 2 / 3 / 4 / 6 / 8 | 48.7 / 49.4 / 49.8 / 50.2 / 49.9 / 50.4% |
  | family F as the fifth emblem: Skirmish / Durability / Monster / Prospector / Jungle / Capture / Treasure / Hunter / Home / Tribute | 50.7 / 50.1 / 50.1 / 50.1 / 50.0 / 49.8 / 49.7 / 49.7 / 49.7 / 49.1% |
  | Skirmish fifth, the looks that did not choose it (holdouts, fresh maps, gate) | +0.42 ± 0.13 (1 se): merged, CHANGES 499 |
  | on top of Skirmish: Prospector 3rd / Collectors 6th / Monster 9th / Durability 10th / Home 12th / all five | 50.0 / 50.1 / 50.1 / 49.9 / 50.0 / 50.1% of 61,440 |

- **Data and tools left by round 4:** `replays/emblab/{r4,r4b,r4c,r4d}` (games, compressed decisions),
  `replays/emblab/r4/dmodel-*.{json,md,drsums.bin}`, `research/ideas-2026-11-10/emblab4/` (scripts, `collectors.py`
  for family-at-ordinal bots, `scripts/abwave.sh` for a wave of A/Bs under one kept slot weight).
- **Maps used up:** fresh-3100000..3100399 (round 4's pool), 3110000..3110119 (`merged/emb4-h1..h3`, about 45 A/Bs),
  3120000..3120119 (`merged/emb4-c1..c3`). Round 5 needs new ones (section 6).

## 2. Audit of round 4 (read-only; ranked)

1. **The selections were scored as a policy the candidate bots do not play** (verified in code). `select.py`'s
   pooled rules (`tb`, `tk`) pick one arm X for several consecutive ordinals and `candidate.py` writes X into each
   cell. `drStats` scores each of those cells as "X against the base" on logged rows, where X is almost always still
   unowned. Deployed, X is bought once; the later cells fall back to the current logic and the table's own arms there
   disappear. So the fit counts X's gain 3-6 times and never counts the deleted cells. Self-healing only shrinks
   effects towards zero; this can flip the sign.
2. **No mechanical asymmetry between base and non-base arms was found**, and the numbers do not need one.
   Propensities are right (`pc` in `drStats`; the 1.0004 and 28.400 checks). Ruled out: Tavi selling (ocean never
   sells), Cassi and Issac (separate rows, types and draws), repeated calls at one ordinal (the draw is frozen at
   the first call), row-level errors (split-half z sd 1.04). Immaterial: the reactive Tribute rule
   (`trib_min_bag` is 100 gems). **Not ruled out: debug against release builds** (ocean has about 12 out-of-fuel
   turns a side-game, so lab and A/B builds differ in fuel behaviour). The accounting that suffices: a whole table
   is resolved to ±0.04 x 28 = ±1.1 points; "+0.149" was the best of several rules; its replication, -0.02 ± 0.09
   a decision, agrees with the A/B.
3. **"The lab agrees with A/Bs on pooled edits" is not supported.** The 19 A/B values have sd 0.45 around their
   mean and the lab's rms gap is 0.51: no better than predicting a constant. r = +0.42 at n = 19 rests on two
   large negatives. Prospectively the lab was 0 for 5, and it read Skirmish, the one real gain, at +0.08 ± 0.41.
4. **"No signal left in the data" is a power statement.** At ±1 point a type per half and true effects up to 0.5,
   the expected split-half correlation is about +0.04; the observed +0.02 cannot tell nothing from several +0.5 edits.
5. **Self-healing is real but shown only for deletions.** The table is redundant by construction (Ryth at 3 picks
   has Collectors at ordinals 3, 5 and 6). A chain calculation at ~30% effective deviation a cell gives about 0.3 of
   the true effect, matching -0.49 against -1.7. Direct test on `games.jsonl` alone: regress wins on the force
   masks, with a term for "all of a row's Collectors cells forced".
6. **The A/Bs are sound; the "level" verdicts are wide and the edit class is narrow.** Each "family at k" edit
   overwrote a cell (it measures +F minus the displaced arm); insert-and-shift was never tried. No-table (-3.0) is
   not late (-1.9) plus early (+0.3): a 1.4-point interaction, unexplained. Every A/B is the mirror on own drafts.
7. **"One edit is worth at most 0.5 points" covers only: one passive family, the type's usual stat, all types,
   overwriting one ordinal.** Never tested at policy level:
   - Greed (excluded from the lab's arms and from `current_emblem`'s choices);
   - the stat mix across a whole build;
   - Collectors keyed to families owned rather than ordinal, and diversifying families after it;
   - type-specific rows;
   - ordinals from 12 on (one peeked Vesper earned 2,294 gold, about 15 emblems);
   - the pricing behind the ~58% of emblems the table does not decide. `or_passive` cannot choose Collectors, Home
     or Greed at all: the table's 1.7 points is a pricing hole patched by ordinal.
8. **External validity is the largest unexamined risk.** The repository's shop study has Vesper's `fight_share` at
   0.008-0.03 locally against about 50% champion damage live: every local result, bodies included, may underprice
   Health, Durability and Skirmish. (From the records; check the source before relying on it.)

## 3. Decision: a new run, no whole-build fit on the old data

- For a pre-stated table the old data resolves ±0.8-1.1 points. A fitted-Q evaluation would chain regressions over
  owned sets with teammates still on the 50%-random policy (more variance), with support only near the base, the
  current logic and the steered arms. A 20,480-game A/B gives ±0.35 (1 se) in minutes.
- **Reuse** from round 4: the force-mask regression (audit 5), priors for the type-specific edits
  (`research/ideas-2026-11-10/emblab4/rank_edits.py`), a Collectors-by-families-owned slice to set thresholds, and
  the plumbing (`lab.py` plan and finish, the trainer table, the bodies, suites).
- **Retire** `dfit.mjs`, `select.py` and `candidate.py` as decision tools.
- **[amended] First, one A/B that checks audit 1:** round 4's final selection
  (`replays/emblab/r4/sel/dense-tb-z2.json`) as an overlay on the first cell of each bucket only, keeping the old
  arm wherever X is owned. If that reads level or better where the full selection read 48.4%, the fit was misapplied
  rather than wrong.

## 4. Design: an "edit lab" (many policy-level A/Bs in one run)

- **Unit:** the team-game. A lab team plays the base table plus up to 3 non-conflicting edits from a library fixed
  before play, all game, all champions. 15% of teams get none.
- **Builds:** release, no in-game logging. The outcome is the win and the assignment is the plan, so the
  debug/release question goes away.
- **Opponents:** 50% a second lab team with its own edits, 25% the Fish body, 25% the Mite body.
  **[amended]** Use the Mite body the gates use now (`Mt3qro`), and noise seeds no gate plays.
- **Drafts:** ocean's own, which is what a deployed table meets.
- **Estimator:** per edit, a Bradley-Terry logistic on edit indicators with side, opponent-kind and pick-count
  intercepts. No propensities, no state.
- **Precision:** se = 50 / sqrt(n) points, n the team-games carrying the edit, about 3.8 edit-appearances a game.
  This assumes binomial variance and additivity between co-assigned edits; the gate checks the second.
- **Deployable by construction:** a table edit is a list of `learned_arm` cells; a structural edit is a flag that
  becomes a constant in `shop.cc`.

**Library, about 330 edits, hashed before play:**

| tier | count | contents |
|---|---|---|
| anchors | 12 | no-table, late only, early only, no late Collectors, the four family groups, Collectors at k1 and k2, the Skirmish cell removed, Power -> Bruiser |
| placebos | 8 | edits that change nothing |
| structural | ~55 | Greed as the stat sink from ordinal 6 / 8 / 10 and beyond 12; Collectors at >= 2 / 3 / 4 / 5 families owned; diversify after Collectors; stat -> Health or main by ordinal bucket; price multipliers (`fight_weight`, Skirmish, Treasure, Prospector, Capture, Hunter, Tribute); Collectors priced for champion damage in `or_passive`; each type's row back to the current logic (13) |
| pooled | ~130 | family x ordinal, as overwrite and as insert-and-shift |
| type-specific | ~126 | the 7 most drafted types x 12 edits ranked by round 4's sums, plus 6 random controls each (tests whether that ranking is worth anything) |

**Rounds (successive halving):**

| round | edits | new n each | se | games |
|---|---|---|---|---|
| CAL | 28 | 30k | 0.29 | 0.25M |
| A | 330 | 12k | 0.46 | 1.05M |
| B | 165 | 24k | 0.26 cumulative | 1.05M |
| C | 60 | 60k | 0.20, new data only | 0.95M |
| D (replication) | 20 | 150k | 0.13, unbiased | 0.8M |
| E (2^S factorial of survivors) | <= 8 | | main ±0.1, pairs ±0.2 | 0.9M |

- About 5.5M games with confirmations (round 4 played ~0.7M an hour at slot weight 35).
- A true +0.5 edit survives to D about 70% of the time and reads z of about 3.8 there; +1.0 about 99%; +0.3 about 35%.
- If throughput is under 0.6M an hour at hour 3, cut the library to 200.

**Heterogeneity.** Type and ordinal are in the library; shrink towards the pooled edit only for ranking in A-C. In
D, nine contrasts stated beforehand per edit: opponent kind, pick count, and median splits of gold_side, spawn_dist
and cluster_share. Act only on |z| >= 3.5 that repeats in E.

## 5. Calibration gate (after CAL, before any estimate is trusted)

Re-measure three anchors on the current base by plain A/B in hour 0. Pass needs all of:
- no-table within 0.8 points of its A/B (about -3.0 on 496);
- no late Collectors within 0.8 (about -1.7);
- Collectors at k1 within 0.8 (about -1.3);
- the placebos' mean within ±0.15 and none with |z| > 3;
- rms gap over all anchors <= 0.45;
- an anchor's effect alone against its effect with two co-edits: within 2 se.

## 6. Schedule (about 12 hours)

| hour | work | decision |
|---|---|---|
| 0-1 | Generate suites (a lab pool, e.g. fresh-3130000..3130399, and held out fresh-3140000..3140119, 3150000..3150119; `--mix ladder-v2`, at most ~30k maps a mapgen command). Anchor A/Bs at 20k and an A/A. The audit-1 A/B (section 3). Write the code. Run the force-mask regression. | The zero-edit vehicle must replay identically to release ocean on 64 maps, else fix first. |
| 1-2 | CAL. Write the structural flags. | Gate fails on placebos: debug, 1 hour cap. Anchors attenuated below 60%: one edit a team, rerun. Still failing at 3:30: drop the lab and A/B the structural tier directly (40 x 40k). |
| 2-5 | Rounds A and B. | Any edit >= +1.5: fork a 20k A/B at once. |
| 5-7 | Round C. | Top-20 mean <= +0.1 on C-only data: stop the search and record the bound. |
| 7-8.5 | Round D. | Survivors are >= +0.25 at z >= 2.5. None: stop. One: straight to the A/B. Two or more: round E. |
| 8.5-10 | Round E, with 10% all-on and 10% all-off teams. | Keep main effects >= 2 se with no pair <= -2 se. |
| 10-12 | Release A/B against current ocean on the held-out suites, 61,440 games (se 0.2). Start the fresh gate with its own seed. Write up. | The merge rule below. |

**Merge rule.**
- A/B >= +0.5 with all three suites above 50, and the fresh gate's SPRT H1 at 50.5 / 50.75: queue the live pair.
- +0.3 to +0.5, consistent across D, E and the A/B (pooled z >= 3): the Skirmish precedent (CHANGES 499), the live
  pair still required.
- Below +0.3: not merged.
- Fight-family edits get a live pair even on a local null (audit 8).
- Merging and queuing for live are the user's calls: report, do not do them unasked.

## 7. Code changes, in order

1. `tools/emblab/edits.py` (new): the library -> cell lists and flag ids, `edit_defs.h`, a hashed registry;
   `--table` exports a candidate bot.
2. `tools/emblab/evehicle.py`: a second wrapper of about 25 lines. A mutable copy of `learned_arm` is patched at
   first use from `Entry.force[0..5]` read as edit ids. `trainer.h` is unchanged; no `debug_block`.
3. `tools/emblab/lab.py`: a `"design": "edits"` config: `draw_edits` in place of `draw_force`, release builds, no
   decision parsing, edit ids in `games.jsonl`.
4. `tools/emblab/efit.py` (new): estimates, bootstrap, the placebo and gate report, the halving allocation.
5. Flag hooks as vehicle patches on `shop.cc` (`best_emblem`, `current_emblem`, `passive_saved`): these join at
   round A or B.

Steps 1-4 are data only, so CAL can start within the hour.

## 8. Risks and how each shows early

- **An edit applied wrongly:** the identity replay, the placebos and the anchors, all by hour 2.
- **Multiplicity:** D uses only new games; placebos in the top 20 measure the false-positive rate; the final A/B is
  on untouched maps.
- **Co-edit interference:** the alone-against-with contrast in CAL.
- **Local is not live:** per-opponent-kind effects, and the champion-damage share in lab games against the live
  archive.
- **Fuel:** out-of-fuel turns per edit; Greed and the pricing flags are the ones to watch.
- **The slot pool's member-file race:** a batch over 10 minutes. Start a `slot_keeper.py` with every lab or A/B
  wave and let it die with it (RUNBOOK section 9); the schedule has about 2 hours of slack.

## 9. Practical notes from round 4

- Long runs in tmux; weight 35-40 for the lab when the box is loaded (the user asked for high weights);
  `research/ideas-2026-11-10/emblab4/scripts/abwave.sh` runs several A/Bs under one slot group with a keeper.
- Never `pkill -f` / `pgrep -f` a pattern that is in your own command line; kill by tmux session or pid.
- A killed `fgate.py` leaves lock files in `~/tmp-offload/diverse/locks/` that stall the next gate on the same
  bots: remove your own stale ones.
- `maps/SUITES.md` and `research/EXPERIMENTS.md` usually hold other agents' uncommitted edits: stage only your own
  hunks, commit on local main, then push main.
- Record results in research/EXPERIMENTS.md, and new suites in `maps/SUITES.md`.
