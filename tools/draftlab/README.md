# Draft lab

Learns which champions astraeus should draft from the map's features, the pick count and the opponent's picks,
from many local self-play games with varied drafts. Node 22+ and Python 3, no other dependencies.

```
py tools/draftlab/lab.py init --lab night1 [--source REF] [--top 20]   # freeze REF's bots/astraeus, map features, ladder prior
py tools/draftlab/lab.py run --lab night1 --hours 8                    # batches until the deadline, then a final fit
py tools/draftlab/lab.py status --lab night1
py tools/draftlab/lab.py fit --lab night1 [--search]                   # refit (--search: penalties by cross-validation)
py tools/draftlab/lab.py report --lab night1                           # report.md
```

Analysis (`L` = the lab directory):

```
node tools/draftlab/model.mjs gain --lab L      # predicted win % vs the ladder prior: current draft, best fixed team, best team per map
node tools/draftlab/model.mjs curve --lab L [--sizes 3000,6000,12000]   # cv log loss by exploration games, per model variant
node tools/draftlab/model.mjs compare --lab L --old OLD/model.json      # share of maps whose best team is unchanged
node tools/draftlab/model.mjs ladder --lab L    # ladder.jsonl fit with team effects, against self-play (ladder.md)
```

`run` resumes: rerun it after a crash or reboot and it finishes the unmerged batch first. Keep the laptop awake
(`powercfg /change standby-timeout-ac 0`) and plugged in.

## How it works

- **Vehicles.** The draft is compiled in, so each batch builds `--vehicles` (4) copies of the frozen bot
  (`bots/variants/dl-<lab>-v<k>`), each with a generated `trainer_table.h`: (map key, team) to a draft in pick
  order. `trainer.h` hooks `draft_order()` and lets Vesper be drafted; maps not in the table draft as the bot does.
  A game is vehicle k against itself, so a map hosts up to 4 games a batch with independent drafts for both teams.
  A build takes about 35 s.
- **Playing** (`lab.py run_batch`, shared with the emblem lab): each game is its own `cambc run-batch` holding a
  CPU slot (`tools/cpu_slots.py`), with the WASM cache (`tools/cambc_env.py`): 82 games/s on 96 cores against ~57
  for one run-batch of every game, whose parent spends ~17 ms a game serially (2026-10-29). On Windows a batch
  is still one run-batch (`--threads` jobs).
- **Map key.** `features.mjs mapKey` and `trainer.h map_key` hash the size, the terrain counts and the camps
  (summed, so handle order does not matter); change both together. Every merged game checks the replay's drafts
  against the table (`draft_ok`), and a batch with more than 2% mismatches stops the run.
- **Batches** (`model.mjs plan`): ladder maps every batch, the rest of the pool cycled in a fixed shuffle, about
  equal games per pick count (`pick_shares`). Never the same (map, team A's draft, team B's draft) twice: local
  games are deterministic. Half the games have one team on a top-20 ladder composition (`prior.json`, sampled by
  frequency). The other teams, by `mix` (night1: 15 / 70 / 15; since draft2, 2026-10-30, 50 / 35 / 15):
  - **explore** (the first `explore_batches`, then `mix.explore`): uniformly random teams in random order, without
    `explore_exclude` (draft2: Stellar).
  - **thompson**: the best team on this map against the ladder prior under one of 16 posterior draws; a
    champion good only on some map styles keeps being played there.
  - **probe**: the mean model's runner-up against the previous game's opponent, same map and side, so the
    close calls are paired.
- **Pool** (`pool`, `holdout` in `config.json`): globs of maps and suites, less the held-out suites, which are never
  measured or played. draft2: the ladder, `fall-custom`, `gen` (6001), `gen-s1` (6002) and `fresh-6003` to
  `fresh-6176` (45k maps); held out `fresh-6177` to `fresh-6196`.
- **Prior games** (`prior_games`, `prior_maps`, `prior_weight`): another lab's games (draft2: night1's, under the
  emblem logic before CHANGES 232) join every fit at `prior_weight` (0.25) and are never scored in cross-validation;
  their maps join `maps.jsonl` as set `prior:<set>` (features only, never planned). `init` fits on them at the prior
  lab's searched penalties, so Thompson has a model from batch 0. draft2 set `prior_weight` to 0 after batch 0: a different bot's
  games bias the fit once the lab's own outnumber them (at 0 they are not loaded).
  - Each team's source and its probability under that source are stored (`srcA`, `probA`, ...).
- **Outcomes** (`outcome.mjs`, ~50 ms a replay, then the replay is deleted): the winner, each team's tributed and
  carried gems at rounds 300/600/1000/1500 and the end, and every champion's engine statistics. Carried gems
  count because Prism banks late by design.
- **Model** (`model.mjs fit`): P(A wins) = sigmoid(S(A) - S(B) + sum over a in A, b in B of M[a,b] + side), with
  S(T) = sum over T of (b_c + w_c . z) + pair synergies, M antisymmetric (counters), z the 19 standardised map
  features (`FEATURES`). One fit per pick count, penalised toward a fit pooled over pick counts. The target mixes
  the win with sigmoid(5 x wealth margin) by `alpha`; the penalties and `alpha` come from 5-fold cross-validation
  over maps, scored on wins only. `--search` reruns that (minutes on tens of thousands of games), else the last
  values are reused. `cv` in `model.json` compares the model with no map terms, no pair terms and intercepts only.
- **Report** (`report.md`): map clusters (k-means on the features), and per pick count the model's best team on
  each pool map against the ladder prior (how often each champion is in it), each champion's value on every
  cluster with a mark where it is clear of the average champion, misfits (clusters where a champion's observed
  wins differ from the model, Benjamini-Hochberg at 10%) and the largest synergy and counter terms. Then play
  statistics per champion appearance and cluster: gems collected, tributed and carried, deaths, kills, raw win rate.
  These are where to look for champions that are weak because of how we play them.

## Files

Under `replays/draftlab/<lab>/`: `config.json` (defaults in `lab.py DEFAULTS`), `maps.jsonl` (features and keys),
`prior.json` (top-20 compositions since `patch_since`, our team excluded), `ladder.jsonl` (games between two
top-20 teams, for a fit with team effects), `games.jsonl` (one row per game, append-only), `model.json`,
`report.md`, `lab.log`, `fit.log`, `batches/bNNN/` (plan, manifest, results, outcomes, run log).

The `holdout` suites are never played: keep them for judging the drafts the model makes.

## Deployment: astraeus drafts from the model

astraeus's draft (`draft.cc model_draft`, on the first draft turn) measures the map's 19 features in C++
(`src/map_features.cc`, a step-for-step port of `features.mjs` and mapgen's `metrics`, rounding included), then
takes the best team (`model_team`, the same as `model.mjs deployedTeam`) from `src/draft_model.h`. Without counter
terms (`draft_model::counters` false, the default) the team is chosen once, in champion id order; `model.mjs cpp`
refuses a model whose counters exceed 1e-3 unless given `--counters`. With `--counters` the header carries the counter
terms and the ladder prior's pick shares `q`: round 0 takes `deployedTeam(..., counters)` (counters against `q`, picks
in `pickOrder`), and each later draft turn re-ranks the teams holding our picks against the opponent's revealed ones
(`q` spread over its hidden picks), from team scores cached in round 0 (scoring every team there cost 60-90k fuel and
ran 5-pick draft turns out before the pick, so later picks went random). Kept champions keep their pick order, so the
draft analysis's per-body leads restart only when the team changes. draft2's counters (at most ~0.012 logit) lost
1.6 points to the same model refitted without them (`draft2-noctr`, deployed), so astraeus ships without.
`draft2-noctr` links draft2's `games.jsonl`, `maps.jsonl`, `prior.json` and `ladder.jsonl`, with a copy of its
config and of its `model.json` with `lam.ctr` 1e9; `model.mjs fit --lab replays/draftlab/draft2-noctr` refits it (~1 min).
`params::map_model_draft = false` turns the model off (the old table draft
everywhere). Pick counts other than 3-5, test drafts, spawns joined only by dash or crystal (too
costly, below) and any failure fall back to the old table draft (`params::draft_three/four/five`, v61's Tavi switch
on 3 picks); off that fallback Vesper Vale may be drafted.

```
node tools/draftlab/model.mjs cpp --lab replays/draftlab/draft2-noctr    # regenerate src/draft_model.h after a refit
node tools/draftlab/model.mjs cpp --lab replays/draftlab/draft2 --counters --out DIR/src/draft/draft_model.h
node tools/draftlab/model.mjs teams --lab replays/draftlab/draft2-noctr  # the deployed team per map (or --features FILE)
node tools/draftlab/native.mjs --lab replays/draftlab/draft2-noctr maps maps/gen   # offline parity, no games (zig c++)
py tools/draftlab/parity.py --lab replays/draftlab/draft2-noctr maps --jobs 4      # in-game parity, round 0 only
py tools/draftlab/parity.py --lab replays/draftlab/draft2 --bot DIR --counters maps   # a --counters build
```

- **native.mjs** compiles `native_main.cc` with `map_features.cc` natively (`zig c++`, no FMA contraction), feeds
  it decoded maps (camps in reversed order, as the engine's need not be the file's) and compares the map key, the
  features and the team with the JS exactly. It runs our own BFS where the bot uses the engine's distance fields.
  Directories are not recursed. On 2026-10-28 all 2411 maps of the pool matched (night1's model); after the cost
  rewrite, the 70 ladder maps and 125 others across suites, pick counts and edge cases (no `altar_ratio`, no `camp_near`,
  no camps, dash and crystal access, crystal-only spawns) matched (night1's 02:14 snapshot).
- **parity.py** builds a debug copy with `params::draft_parity` on (`bots/variants/dl-parity`), plays it against
  itself with `cambc run-batch --rounds 1`, and reads the `FEAT key values`, `TEAM key picks team` and
  `FEATFUEL key fuel` lines its draft bot prints in draft round 0 from the replays' `team-a/b.stdout`. It compares
  them with `features.mjs` and `model.mjs teams` and writes `replays/draftlab/parity/<time>/report.txt`; both
  teams must print the same lines (the features are measured from team A's side, as mapgen does).
- **Cost:** 4 engine distance fields, the clearance BFS (stopped at 6), the dash travel (dashes tried only from
  tiles beside something unwalkable, then Dial's algorithm from the tiles they improve), a few passes over the map
  and at most 792 teams scored. Counted offline as WASM instructions (~1 fuel each) with the bot's compiler and
  flags, our BFS left out: ladder median 1.1M, max 4.5M (01starvation); `edge_case/gauntlet` 6.6M (dashes help
  almost everywhere); the engine fields add ~0.5-1M. The port as first written cost 14-19M on 100x100 maps, which
  would have run the first draft turn out of fuel before the first pick (a random draft). metrics' last fallback
  (spawns joined only by dash or crystal: two crystal travels, ~8.6M on a 72x72 archipelago) is declined in the
  bot (`compute(..., crystals = false)`); no ladder map needs it. `FEATFUEL` measures the cost in-game, and
  `DRAFTTURN` whether the analysis that follows still finished in round 0 (if not, it resumes on later draft turns
  at 100k each).
- **Exactness:** the only expected differences from the JS are `log`/`log1p` in the last bit (WASI libc against
  V8), which can flip a team only on a tie within 1e-15.
