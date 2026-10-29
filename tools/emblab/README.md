# Emblem lab

Learns which emblems astraeus should buy, and with them which champions to draft, from self-play games whose
drafts and emblem choices are randomised. The target is winning (and the wealth margin, tributed + carried at the
end, if cross-validation on wins says it helps), so combat value counts as fully as farming. Python 3 and Node 22+,
no other dependencies. It reuses the draft lab's vehicles, batch runner and outcomes (tools/draftlab/README.md).

```
py tools/emblab/lab.py init --lab NAME [--source REF]   # freeze REF's bots/astraeus, the map table (replays/emblab/feat/), the prior
py tools/emblab/lab.py run --lab NAME --games 40000 [--batches N] [--vehicles 4]
py tools/emblab/lab.py status --lab NAME
node tools/emblab/dfit.mjs --labs r2 [--search] [--boot N]   # round 2: per-decision fit (dmodel.json, dmodel.md)
node tools/emblab/fit.mjs --labs main,pilot [--search] [--boot 20]   # round 1: whole-game fit (model.json, model.md)
py tools/emblab/policy.py [model.policy.json] [--min-p10 0]   # astraeus's learned table from round 1 (src/economy/emblem_table.h)
node tools/emblab/ladder_emblems.mjs [replays/ladder]    # top teams' emblem orders (ladder_emblems.jsonl)
```

Map features (`replays/emblab/feat/<set>.jsonl`) come from `node tools/draftlab/features.mjs maps/<set> --out ...`;
`init` reads every file there (ladder maps first) and leaves out `HOLDOUT`, `maps/fresh-4041` to `fresh-4044`
(kept for confirming what the lab deploys; they have no feature files). Since 2026-10-29 the pool is ~29.8k maps:
the ladder, `fall-custom`, `gen`, `gen-s1` and `fresh-4003` to `fresh-4120`. Round 1's maps' features are in
`replays/emblab/feat-r1/`.

Rounds: round 1 (`pilot`, `main`, 172k games, 1c0d627) forced uniformly random arms at k < 8 from a pre-drawn table
and was fitted whole-game (fit.mjs); its table shipped as CHANGES 232. Round 2 (`r2`, from 8fad72c) draws arms in
the game and is fitted per decision (dfit.mjs); PLAN.md has the reasoning.

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
  `explore_exclude`, Stellar), `ladder` (night1's ladder compositions by frequency) or `night1` (one of night1's
  Thompson teams on this map, else `ladder`). Each row's k-th new emblem is forced with probability `p_force[k]`
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
per-champion statistics, out-of-fuel lines and stdout bytes per team), `decisions.jsonl`, `lab.log`,
`batches/bNNN/` (plan, manifest, results, emb, outcomes, run log).
