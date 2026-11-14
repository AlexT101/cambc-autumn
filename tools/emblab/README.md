# Emblem lab

Learns which emblems our bot should buy (ocean from round 4; astraeus before), and with them which champions to
draft, from games whose drafts and emblem choices are randomised. The target is winning (and the wealth margin,
tributed + carried at the end, if cross-validation on wins says it helps), so combat value counts as fully as
farming. Python 3 and Node 22+, no other dependencies. It reuses the draft lab's vehicles, batch runner and outcomes
(tools/draftlab/README.md). [RUNBOOK.md](RUNBOOK.md) is the step-by-step for a run;
[PLAN-round5.md](PLAN-round5.md) is the audit of round 4 and the plan round 5 follows ("Round 5" below).

```
py tools/emblab/lab.py init --lab NAME [--source REF]   # freeze REF's bot (config "bot", default ocean), the map table, the prior
py tools/emblab/lab.py run --lab NAME --games 80000 [--batches N | --hours H] [--vehicles 4]   # `touch <lab>/stop` ends it after the batch in play
py tools/emblab/lab.py status --lab NAME
node tools/emblab/dfit.mjs --labs r2 [--search [--rounds 2]] [--boot N]   # round 2: per-decision fit (dmodel.json, dmodel.md); --rounds 0 scores only the variants
node tools/emblab/dfit.mjs --labs r2 --variant static --dr --out replays/emblab/r2/dmodel-dr.json   # + cross-fitted DR selection (*.policy2.json)
node tools/emblab/dfit.mjs --labs r3 --mapdr --out replays/emblab/r3/dmodel-mapdr.json   # + map-keyed policies, nested (mapdr.mjs; *.mappolicy.json)
node tools/emblab/dfit.mjs --labs r4 --mapdr --mapsplits area,gems_side --mapcuts 2,4,6   # the map-keyed search over named splits only
py tools/emblab/candidate.py SELECTION --key 0-2 [--flat] --source BOT --out bots/variants/NAME   # a candidate bot from a selection
node tools/emblab/fit.mjs --labs main,pilot [--search] [--boot 20]   # round 1: whole-game fit (model.json, model.md)
py tools/emblab/policy.py [model.policy.json] [--min-p10 0]   # astraeus's learned table from round 1 (src/economy/emblem_table.h)
node tools/emblab/ladder_emblems.mjs [replays/ladder]    # top teams' emblem orders (ladder_emblems.jsonl)
```

Maps: with `pool` in `config.json` (round 3 on, [PLAN-draft3.md](../draftlab/PLAN-draft3.md)), `init` measures
the pool's maps as the draft lab does (globs less `holdout`), writes the ladder compositions of the `top` (10)
best-rated other teams since `patch_since` (the draft lab's `ladder_data`, ours left out), and takes for the `model`
draft source the deployed team per map (`model.mjs teams`) of `draft_lab`: a draft lab, or `shipped`, the lab named
in the source bot's `draft_model.h` (its `model.json` must be the one the header was made from). Without `pool`
(rounds 1-2), map features (`replays/emblab/feat/<set>.jsonl`) come from `node tools/draftlab/features.mjs maps/<set>
--out ...`; `init` reads every file there (ladder maps first) and leaves out `holdout` (default `maps/suites/fresh/fresh-4041` to
`fresh-4044`), and the prior and per-map teams come from night1. The fits' map features are the draft lab's
`FEATURES` (all of them). Round 2's pool (2026-10-29; those maps were deleted 2026-10-30, see tools/README.md) was ~29.8k maps:
the ladder, `fall-custom`, `gen`, `gen-s1` and `fresh-4003` to `fresh-4120`. Round 1's maps' features are in
`replays/emblab/feat-r1/`.

Rounds: round 1 (`pilot`, `main`, 172k games, 1c0d627) forced uniformly random arms at k < 8 from a pre-drawn table
and was fitted whole-game (fit.mjs); its table shipped as CHANGES 232. Round 2 (`r2`, from 8fad72c) draws arms in
the game and is fitted per decision (dfit.mjs); PLAN.md has the reasoning.

## Round 5: the edit lab (ocean, 2026-11-10)

Many policy-level A/Bs in one run ([PLAN-round5.md](PLAN-round5.md) sections 3-7; results in research/EXPERIMENTS.md
"Emblem lab round 5"). Rounds 1-4 randomised single decisions inside a shared build; round 5 randomises whole
policies per team-game, so what it scores is what a candidate bot plays.

```
py tools/emblab/edits.py build --base bots/variants/BOT --out replays/emblab/LAB/edits.json [--r4] [--structural]   # the library; prints its hash
py tools/emblab/edits.py table --registry edits.json --base bots/variants/BOT --out bots/variants/NAME EDIT...   # a candidate bot with those edits
py tools/emblab/elab.py init | drafts | run | status | check --lab LAB    # the lab (config.json first)
py tools/emblab/efit.py fit --lab LAB [--gate] [--by opp|picks] [--from B --to B]   # estimates; --gate: the calibration report
py tools/emblab/efit.py step --lab LAB                                    # the screen's allocation (elab.py run calls it when config has "auto": [])
```

- **Edit** (`edits.py`): a list of `learned_arm` cells, lab flags (`structural.py`; hooks in `evehicle.py FLAG_PATCHES`),
  or nothing (a placebo). Tiers: anchors (changes an A/B has measured), placebos, pooled (a passive family as
  everyone's k-th emblem, overwriting or inserted), typed rows and typed cells (`typed_r4.py`: per type, round 4's
  best-ranked and random controls), structural. Two edits conflict when they touch one cell or flag. The registry is
  append-only and hashed.
- **Vehicle** (`evehicle.make_edit`): the base bot with only `shop.cc` patched. At the first emblem choice it copies
  `learned_arm`, applies this map and side's edit ids (`trainer_table.h`, `Entry.force`) and sets the flags. Release
  builds, no logging. The draft is the bot's own and sees neither the opponent nor the edits, so `elab.py drafts`
  plays a draft-only game a map and the plan knows every team beforehand: a typed edit goes only to teams that draft
  its pick. `elab.py check --fuel 100000000` shows the vehicle playing exactly as plain bots do (unedited, and with
  the edits written into the table); at the real budget about half the games differ, by fuel timing alone (the
  zero-edit vehicle against the base: 49.98% of 20,480).
- **Games** (`elab.py`): a lab team is the base plus up to 3 non-conflicting edits (`none_share` none, `solo_share`
  one). Opponents: `self` (a second lab team with its own edits) or a sparring body. The outcome is the result
  line; replays are deleted as games end, but for the first `check_drafts` of a batch, which confirm the drafts.
- **Estimates** (`efit.py`): a Bradley-Terry logistic over games on edit indicators, with intercepts per opponent
  kind, pick count, lab side, body and drafted pick. Points = 25 beta. A typed edit's `pts` is its effect on
  carrying teams x the share of teams drafting the pick; `n_eff = (50 / se)^2` is the screen's unit.
- **Screen** (`efit.py step`, `stage.json`): successive halving on cumulative estimates, six steps (n_eff 6k / 12k /
  20k / 32k / 48k / 80k an edit; 250 / 180 / 120 / 75 / 45 / 20 of 330 stay). Each batch's quotas bring every edit
  alive to the stage's target, counting what is planned and not merged.

What round 5 measured about the method:

- **Throughput:** 80,000 games in ~4 minutes at slot weight 35 (1.2M an hour; round 4's logging vehicles: 0.7M).
- **Information a game:** 3.8 edit appearances a game in the screen, 0.78 n_eff an appearance: the lab beats the
  bodies 76-79% of the time, so a body game carries about a third of a mirror game's information.
- **Blocking (not used):** the map and side fix 18% of a mirror game's outcome variance and about 30% of a body
  game's, so a fit with map effects would gain roughly 17%.
- **Rank halving beats confidence bounds:** dropping edits whose upper bound falls under the 20th best's lower
  bound cost more games than the plan's halving at equal power; six rank cuts on cumulative estimates cost 22% fewer
  appearances than the plan's three (`research/notes/ideas-2026-11-10/emblab5/simsched2.py`).

## Round 4 (ocean, 2026-11-10)

What changed from rounds 2-3, whose design the sections below describe:

- **The bot is ocean** (`config.json` `bot`). Its `best_emblem` also prices forecasts, so the vehicle draws only
  inside `buy_shards` (`lab_shopping`); a forecast before the first shard still prices the base's emblem.
- **Opponents** (`opponents`, `opponent_bots`): a share of games put the lab team against a sparring body (the
  Fish and Mite bodies of the gates, other noise seeds), which drafts and shops for itself and logs nothing. The
  game row has `opp` (the kind), `us` (the lab's sides) and the body's own draft; the fit has an intercept per
  opponent kind and pick count (`OPP`), and `--dr` prints every selection's gain against each kind. A table whose
  gain is only against `self` is a mirror artefact.
- **Logs:** `EMB3` lines carry `qb`, the proposal's probability of the base, for every decision, and the entry's
  mode for unforced ones. With `q` (the chosen arm's, forced rows) the logging probability of each row is
  P(base) = 1 - p + p qb, P(arm) = p q, with nothing recomputed, so `corr_model` may change between batches
  (`prepare` reads it from `config.json` per batch and the plan records it): round 4 started on round 3's static
  gains and moved to its own interim fit.
- **Quiet vehicles** (`evehicle.quiet`): every `debug_block` of the source but `main.cc`'s OOF line is compiled out
  (`lab_off`), in the bodies too. A team's stdout is ~10 KB, far from the 1 MiB cap, and games play faster.
- **Decisions** are written per batch, compressed (`decisions/bNNN.jsonl.zst`); `zstd -dc` them into
  `decisions.jsonl` for a fit and delete it after.
- **Maps:** the pool is walked in one fixed shuffle, a slice a batch. The fit's map features are the draft lab's
  first 30 (its base features); the squares and products added for draft7 would put ~370 entries in every row.
- **Checks** (any batch, rows with k < 12): the mean of 1 / P(base) over rows that took the base is 1 (1.0004 on
  the smoke lab), and the sum of 1 / P(chosen) over rows that left it, per row, is the mean number of other
  drawable arms (28.400 against 28.406).

### What round 4 found about the method (read before running another)

Numbers and tables: research/EXPERIMENTS.md "Emblem lab round 4 on ocean".

- **A table is a joint change; the lab measures single cells.** 1.28M games scored "no learned table at all" as
  level (+0.25 ± 0.77 points a team) where a clean A/B reads 47.0%, and scored its own selections 2 to 4 points
  above what they play (47.9-48.4%). Checked on the lab's data (`research/notes/ideas-2026-11-10/emblab4/selfheal.py`,
  `pooled_edits.py`):
  - The base heals one deviation: a champion drawn away from a passive the base wanted owns it within three more
    emblems 60% of the time. Every cell is scored with the rest of the build as the base has it, so a selection's
    cells are scored with the purchases they jointly delete still in place (Collectors cells: -0.49 ± 0.24 in the
    lab, -1.7 when all are dropped).
  - A fixed policy is resolved to ±0.5-0.8 points; a selection is the best of 43 candidates in each of 468 cells,
    and a noise pick costs (a drawn arm is ~0.25 points worse than the base).
  - For one changed cell a champion, pooled over types and stated beforehand (family F as everyone's k-th
    emblem: `pooled_edits.py`), the sums agree with 19 A/Bs: correlation +0.42, rms gap 0.51 points.
  So: use the data for few, pooled, one-cell-a-champion edits, take the best, A/B it, re-base and repeat; or
  evaluate whole rows (a fit over what a champion owns at each decision, backed up along its build); or randomise
  whole rows per champion-game next time.
- **A cross-fitted gain is not a result until it replicates.** The mid-run fit (720k games) read one arm per
  (type, ordinal bucket) at +0.149 ± 0.050 a decision (`select.py` `tb-z2`; all five map folds positive, per-cell
  selection at zero). The same selection scored on the next 240k games (`select.py --on`): -0.02 ± 0.09.
- **Calibrate the lab on something an A/B already knows.** `select.py`'s sums hold a candidate "the current logic"
  for every cell: the lab's estimate of dropping the shipped table. If that disagrees with the A/B of dropping it
  (10 minutes), the lab's other numbers are off by as much.
- **A/B a mid-run candidate.** That costs 15 minutes and showed two hours before the final fit that the lab's
  numbers were not turning into wins.
- **Deploy what the vehicle did** (`candidate.py --buy`): arms at the purchase only. Writing them into the table
  ocean's forecasts read measured 47.9% against the purchase-only build's 48.1%: not the cause here, but a second
  difference between the lab and the bot that an A/B then cannot tell apart.
- **Sparse forcing** (`r4d`: `p_force` [0.1, 0.1, 0.1, 0, ...], `uniform_share` 0; fit it alone, with `--fitall`)
  keeps later purchases, teammates and opponents on the base policy (71% of teams hold at most one drawn decision),
  but 560k games gave a few hundred draws per arm at a main champion's first emblem: it needs 10M+ games, or draws
  limited to a handful of arms.
- **What measured correctly was the clean A/B of a policy-level change** (a whole table, a family at an ordinal:
  `research/notes/ideas-2026-11-10/emblab4/collectors.py`), 20,480 games for ±0.7 points. The next lab should randomise
  whole tables or build orders per team-game, not single decisions inside a shared build.

## How it works (round 2)

- **Batches overlap:** batch b plays while b - 1 finishes and b + 1 is planned and built, so even and odd
  batches have their own vehicles (`el-<lab>-v<k>`, `el-<lab>-v<k>-odd`). A resumed batch rebuilds its vehicles
  from its plan first. A 40k batch plays in ~8 min (2026-10-29).
- **Vehicles** (`evehicle.py`, `trainer.h`): a draft lab vehicle whose `trainer_table.h` also holds, per (map key,
  team), a mode, a seed and, per arm row, which of the first 12 new emblems are drawn (bitmasks). Row i is pick i
  (Cassi for Cassi and Issac), row 5 Issac. Patches to the copy's `shop.cc`: the bot's own `best_emblem` (learned
  table, else the current logic) becomes `base_emblem`; a new `best_emblem`, at a new emblem `buy_shards` starts
  that the table forces, draws an arm among those whose passive is not owned (Power and Bruiser repeat):
  - mode 0: eps / n uniform + (1 - eps) softmax((v[a] - v[base]) / tau + corr[a] / corr_tau), eps 0.3, tau and
    corr_tau 0.04; v the current logic's value (`saved`) of the arm, corr round 1's static gain (`corr_model`);
  - mode 1 (`uniform_share` 10% of team-games, at `p_uniform` 0.2): uniform, as an unbiased check.
  The draw is fixed by the entry's seed, the row and the ordinal, and priced by pinning it in `begun_emblem`.
  The `SLOT`, `D`, `SHORTCUT` and `SRCH` debug lines are dropped: the engine caps each team's stdout at 1 MiB
  whatever `--log-limit` says, and in 2000-round games they reached ~0.9 MiB.
- **Logs:** every new-emblem decision prints, inside `debug_block` (no fuel in local builds), `EMB2 round type k
  forced mode chosen base current q gold strength focus max_health own_gems enemy_gems carried allies_alive picks
  v0..v41` (`evehicle.py`'s docstring has the fields). `finish` reads them from each bundle's stdout before
  `outcome.mjs` deletes the replay, into `decisions.jsonl` (~1.5 GB a 40k batch).
- **Plan** (`lab.py plan`): ladder maps every batch, then other maps shuffled, one game per vehicle per map (4
  vehicles: a 40k batch plays ~10k maps). Each team is drafted by `draft_mix`: `explore` (at random, without
  `explore_exclude`, Stellar), `ladder` (the ladder compositions by frequency) or the per-map source: `model` (the
  `draft_lab` model's team on this map: what the source bot drafts there) or `night1` (one of night1's Thompson
  teams on this map), else `ladder`. Each row's k-th new emblem is forced with probability `p_force[k]`
  (0.35 at k0, 0.5 after).

## Model, round 2 (`dfit.mjs`)

One row per forced decision (k < 12); the outcome is whether that team won. Given the state at the decision, which
the proposal depends on through v, the drawn arm is as good as random, so the fit conditions on that state:
logit = baseline + phi(chosen) - phi(base). The baseline holds the side, the draft per pick count, the state per
ordinal bucket (score difference and total, round, gold, allies alive, carried gems) and intercepts per ordinal;
phi(arm) holds per (type, ordinal, arm) terms shared through coarser (type, bucket, family / stat), (ordinal,
family / stat) and per pick count ones, the value gap v[arm] - v[base], whether the arm is the current logic's pick
or its family, family x score difference and round, and family / stat x map features. Each worker parses a byte
range of `decisions.jsonl` and keeps its rows; L-BFGS runs in the main thread. `--search` picks penalties by 5-fold
CV over maps and compares baseline / static / state / full variants. `dmodel.md` reports, on held-out folds, per pick
count, type and ordinal, how often the model would leave the base, its mean predicted gain and best arms, with a
single-decision inverse-propensity estimate (noisy). Whole policies are judged by A/B, not off-policy: a team makes
~28 decisions below k12, and importance weights over all of them collapse.

`--dr` scores every reached decision (forced or not, loaded with the forced ones but not fitted on) doubly robustly:
Gamma(a) = mu(a) + 1[chosen = a] (y - mu(chosen)) / P(chosen), mu the cross-fitted model, P the logging probability
(1 - p_force + p_force q for the base, p_force q otherwise; q recomputed from the logged values, matching the logged q
to 0.02%). Per policy class (one choice per pick count, type and ordinal; or also per the current logic's pick
family) and z, each fold's cells take the candidate (a fixed arm, falling back to the current logic where not
drawable, or the current logic) whose mean D = Gamma(candidate) - Gamma(base) on the other folds clears z standard
errors, scored on the fold. Selection on all folds goes to `*.policy2.json`. On 44M decisions (2026-10-30): z 2,
class 0, +0.08 +- 0.03 win points per decision, 53.0% and 52.3% in A/Bs: CHANGES 233. Truncated EMB2 lines (fewer than
42 values) are skipped; one shifted every later row of a worker before.

## Model, round 1 (`fit.mjs`)

P(A wins) = sigmoid(side + team A's terms - team B's), where a team's terms are:

- **Draft:** per champion b_c + w_c . z, with z the draft lab's 19 standardised map features.
- **Emblems:** per assigned arm in the table (intention to treat: whether or not the game reached it),
  ET[t, family] + ST[t, stat] + EK[kb, family] + SK[kb, stat] + MZ[family] . z - (MD[kb] + MDT[t]), for champion
  type t at its k-th new emblem (kb = min(k, 3)); MD + MDT is what the old chooser's state-dependent pick is worth.

Every block but MZ also has a copy per pick count (3, 4, 5) with its own penalty, so each pick count's model is
the shared one plus a deviation, as the draft lab fits each pick count toward the pooled fit.

Ridge penalties per group, fitted by L-BFGS on worker threads sharing the data (`--threads`). `--search` picks the
penalties and the win/margin mix (`alpha`) by 5-fold cross-validation over maps scored on wins, and compares the
variants draft / draft_sized / emblem / sized / map. On 172k games (2026-10-29), CV log loss: draft 0.6549,
draft_sized 0.6515, emblem 0.6465, sized 0.6429, map 0.6432; alpha 0 (wins only). Pick count changes champion
strength and what the model's own choice is worth (k0: 3.5 / 2.8 / 2.0 win points at 3 / 4 / 5 picks); the search
shrinks the per-size arm terms to nearly nothing, so which arm beats the model is the same at every pick count.
`model.md` gives champion strength per pick count and, per pick count, type and decision, the best arms against the
model's choice, with bootstrap agreement and the 10th percentile of the gain.

Pilot findings (2026-10-29, 12k games), which set the design:
- Pairs gave 0.24x (wins) and 1.0x (margin) the information per game of independent games: dropped.
- Wins carried more signal than the margin.
- A random first emblem in place of the model's costs ~2.6 win points; the second ~1.7, the third ~0.7.
- Pooled over champions, families barely differ (between-family sd ~0.4 points). Gains have to come from
  champion x emblem x stat structure.

## Files

Under `replays/emblab/<lab>/`: `config.json` (defaults in `lab.py DEFAULTS`), `maps.jsonl`, `prior.json`,
`games.jsonl` (drafts, sources, modes, seeds and force masks (round 1: arms), winner, wealth, checkpoints,
per-champion statistics, out-of-fuel lines and stdout bytes per team), `decisions.jsonl` (round 4:
`decisions/bNNN.jsonl.zst`), `lab.log`,
`batches/bNNN/` (plan, manifest, results, emb, outcomes, run log). Rounds 2 and 3 keep `decisions.jsonl` and the
batches' `emb.dec` zstd-compressed (2026-10-31, for disk): `zstd -d` them before `dfit.mjs` (it reads plain JSONL).
