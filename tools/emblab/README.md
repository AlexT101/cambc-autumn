# Emblem lab

Learns which emblems astraeus should buy, and with them which champions to draft, from self-play games whose
drafts and emblem choices are randomised. The target is winning (and the wealth margin, tributed + carried at the
end, if cross-validation on wins says it helps), so combat value counts as fully as farming. Python 3 and Node 22+,
no other dependencies. It reuses the draft lab's vehicles, batch runner and outcomes (tools/draftlab/README.md).

```
py tools/emblab/lab.py init --lab NAME [--source REF]   # freeze REF's bots/astraeus, the map table (replays/emblab/feat/), the prior
py tools/emblab/lab.py run --lab NAME --games 12000 [--vehicles 6] [--batches N]
py tools/emblab/lab.py status --lab NAME
py tools/emblab/pilot.py --lab NAME                     # logs, pairs against independent games, effect sizes
node tools/emblab/fit.mjs --labs main,pilot [--search] [--boot 20]   # the model (model.json, model.md in the first lab)
node tools/emblab/ladder_emblems.mjs [replays/ladder]    # top teams' emblem orders (ladder_emblems.jsonl)
py tools/emblab/policy.py [model.policy.json] [--min-p10 0]   # astraeus's learned table (src/economy/emblem_table.h)
```

Map features (`replays/emblab/feat/<set>.jsonl`) come from `node tools/draftlab/features.mjs maps/<set> --out ...`;
`init` reads every file there (ladder maps first) and leaves out `maps/fall-holdout`, `maps/fresh-2918` and
`maps/fresh-2934` (kept for confirming what the lab deploys).

## How it works

- **Batches overlap:** batch b plays while b - 1 finishes and b + 1 is planned and built, so even and odd
  batches have their own vehicles (`el-<lab>-v<k>`, `el-<lab>-v<k>-odd`). A resumed batch rebuilds its vehicles
  from its plan first. A 40k batch played in ~49 min before the WASM cache and per-game run-batches (2026-10-29);
  3,000 of its games replayed at 82 games/s, about 8 min for a batch.
- **Vehicles** (`evehicle.py`): a draft lab vehicle whose `trainer_table.h` also holds, per (map key, team), each
  champion's arm (family x 3 + stat, or the model's choice) for its first 8 new emblems. Row i is pick i (Cassi for
  Cassi and Issac), row 5 Issac. Patches to the copy's `shop.cc`:
  - `best_emblem` becomes `model_emblem`. A new `best_emblem` gives the table's arm at a new emblem that
    `buy_shards` starts, priced by pinning it in `begun_emblem`. Prices, `affordable_prefix` and shopping trips
    keep the model's choice until the arm's first shard is bought.
  - An arm whose passive is already owned falls back to the model (logged as arm -2). Power and Bruiser may repeat.
  - `begun_emblem` finishes any begun emblem, not only those the model's list names.
  - `prices().per_gold` is scaled by `trainer::gold_price_scale` (1.5: we earn less gold than top teams).
  - The `SLOT` and `D` debug lines are dropped: the engine caps each team's stdout at 1 MiB whatever
    `--log-limit` says, and they would crowd out late `EMB` lines.
- **Logs:** every new-emblem decision prints, inside `debug_block` (no fuel in local builds):
  `EMB round type ordinal arm chosen model gold strength focus max_health v0..v41`. `v` is the model's value
  (`saved`) of every arm, x for Greed's. `finish` reads them from each bundle's `team-<a|b>.stdout` before
  `outcome.mjs` deletes the replay, into `decisions.jsonl`. The workers write each game's rows; the batch keeps
  them in `emb.dec` and per-game counts and offsets in `emb.jsonl`, for a resumed finish.
- **Plan** (`lab.py plan`): ladder maps every batch, then other maps shuffled, one game per vehicle per map.
  - Each team is drafted by `draft_mix`:
    - `explore`: at random, without `explore_exclude` (Stellar: the weakest in night1 and the pilot);
    - `ladder`: from the night1 ladder prior, compositions by frequency;
    - `night1`: one of night1's Thompson teams on this map, falling back to `ladder` on maps night1 never played.
  - Each (row, ordinal) is forced to a uniformly random arm with probability `p_force`.
  - Vehicles come in pairs. On `pair_share` of maps (0 since the pilot) the second game is the first with one (side, row, ordinal)
    flipped (`flip`, at ordinal 0/1/2 by `flip_ordinals`). Games are deterministic, so a pair is identical up to
    that decision. On the other maps the two games are drawn independently.

## Model (`fit.mjs`)

P(A wins) = sigmoid(side + team A's terms - team B's), where a team's terms are:

- **Draft:** per champion b_c + w_c . z, with z the draft lab's 19 standardised map features.
- **Emblems:** per decision, phi(chosen) - phi(model). So only decisions where the arm differed from the
  model's choice add anything, and emblem terms are learned from the randomised decisions alone. phi(arm) for
  champion type t at its k-th new emblem (kb = min(k, 3)):
  - ET[t, family] + ST[t, stat] + EK[kb, family] + SK[kb, stat];
  - (DV + DVT[t]) x the model's logged value of that arm;
  - MZ[family] . z;
  - MD[kb] + MDT[t] if the arm is the model's choice: what its state-dependent pick is worth beyond the rest.
    Without it, any noise in the static terms beats the model's choice.

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
`games.jsonl` (drafts, sources, arms, pair and flip, winner, wealth, checkpoints, per-champion statistics,
out-of-fuel lines and stdout bytes per team), `decisions.jsonl`, `lab.log`, `batches/bNNN/` (plan, manifest,
results, emb, outcomes, run log).
