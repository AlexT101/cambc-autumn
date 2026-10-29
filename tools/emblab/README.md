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
node tools/emblab/fit.mjs --labs main,pilot [--search]   # the model (model.json, model.md in the first lab)
node tools/emblab/ladder_emblems.mjs [replays/ladder]    # top teams' emblem orders (ladder_emblems.jsonl)
```

Map features (`replays/emblab/feat/<set>.jsonl`) come from `node tools/draftlab/features.mjs maps/<set> --out ...`;
`init` reads every file there (ladder maps first) and leaves out `maps/fall-holdout`, `maps/fresh-2918` and
`maps/fresh-2934` (kept for confirming what the lab deploys).

## How it works

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
  `outcome.mjs` deletes the replay, into `decisions.jsonl`.
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

Ridge penalties per group, fitted by L-BFGS. `--search` picks the penalties and the win/margin mix (`alpha`) by
5-fold cross-validation over maps scored on wins, and compares the variants draft / emblem / analytic / map.
`model.md` ranks each type's first emblem on the static terms, and runs the learned policy (argmax over arms) on
sampled real decisions: how often it departs from the model, and its in-sample (optimistic) predicted gain.

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
