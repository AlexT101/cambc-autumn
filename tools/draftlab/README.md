# Draft lab

Learns which champions astraeus should draft from the map's features, the pick count and the opponent's picks,
from many local self-play games with varied drafts. Node 22+ and Python 3, no other dependencies.

```
py tools/draftlab/lab.py init --lab night1 [--source REF] [--top 10]   # freeze REF's bots/astraeus, map features, ladder prior
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
  games are deterministic. Half the games have one team on a ladder composition (`prior.json`: the top `--top`
  other teams', 10 from draft3, 20 before; sampled by frequency). The other teams, by `mix` (night1: 15 / 70 / 15; since draft2, 2026-10-30, 50 / 35 / 15):
  - **explore** (the first `explore_batches`, then `mix.explore`): uniformly random teams in random order, without
    `explore_exclude` (draft2: Stellar).
  - **thompson**: the best team on this map against the ladder prior under one of 16 posterior draws; a
    champion good only on some map styles keeps being played there.
  - **probe**: the mean model's runner-up against the previous game's opponent, same map and side, so the
    close calls are paired.
- **Pool** (`pool`, `holdout` in `config.json`): globs of maps and suites, less the held-out suites, which are never
  measured or played, and less maps outside the published sizes (`write_maps`, `PUBLISHED_SIZE` 29 to 100 a side:
  13 of `fall-custom`'s edge cases, from 2026-10-31; draft3 and emblem round 3 still had them). draft2: the ladder, `fall-custom`, `gen` (6001), `gen-s1` (6002) and `fresh-6003` to
  `fresh-6176` (45k maps); held out `fresh-6177` to `fresh-6196`. draft3's and emblem round 3's (`lab.py POOL`;
  [PLAN-draft3.md](PLAN-draft3.md)): the ladder, `fall-custom` and `fresh-9100` to `9280` (suites no A/B used); held
  out `fresh-9300` to `9379` (both labs' judging and confirming suites).
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
  S(T) = sum over T of (b_c + w_c . z) + pair synergies, M antisymmetric (counters), z the lab's standardised map
  features (`features` in `config.json`, default all of `FEATURES`). One fit per pick count, penalised toward a fit
  pooled over pick counts. The target mixes
  the win with sigmoid(5 x wealth margin) by `alpha`; the penalties and `alpha` come from 5-fold cross-validation
  over maps, scored on wins only. `--search` reruns that (minutes on tens of thousands of games), else the last
  values are reused. `cv` in `model.json` compares the model with no map terms, no pair terms and intercepts only.
- **Features** (`model.mjs FEATURES`, in astraeus's `map_features.h` order: append, never reorder): the 19 of night1
  and draft2, then from draft3 six of mapgen's quirk metrics (tools/README.md, "Quirk metrics"): `dash_gain` (log;
  dashers where a dash cuts the walk between spawns), `narrow` (1-wide corridors: body blocking, splash), `spawn_ring`
  (a walled spawn surround), `max_group` (log1p; area damage on big groups), `camp_altar` (log; camps beside
  altars hit tributes) and `sight_gap` (ranged champions where sight and walking disagree). Left out: `walk_split`
  (`dash_gain` is 10 where a dash joins the spawns), `tele_gain` (a crystal travel field on every map, too dear for
  the draft turn), `leaky`, `diag_groups`, `altar_gap` and `altar_slots` (no clear draft or emblem effect). Old labs'
  maps lack the new ones: they read as missing (z 0); set such a lab's `features` to the 19 to run its analyses.
- **Report** (`report.md`): map clusters (k-means on the features), and per pick count the model's best team on
  each pool map against the ladder prior (how often each champion is in it), each champion's value on every
  cluster with a mark where it is clear of the average champion, misfits (clusters where a champion's observed
  wins differ from the model, Benjamini-Hochberg at 10%) and the largest synergy and counter terms. Then play
  statistics per champion appearance and cluster: gems collected, tributed and carried, deaths, kills, raw win rate.
  These are where to look for champions that are weak because of how we play them.

## Files

Under `replays/draftlab/<lab>/`: `config.json` (defaults in `lab.py DEFAULTS`), `maps.jsonl` (features and keys),
`prior.json` (the top `--top` other teams' compositions since `patch_since`), `ladder.jsonl` (games between two
of them or one and us, for a fit with team effects), `games.jsonl` (one row per game, append-only), `model.json`,
`report.md`, `lab.log`, `fit.log`, `batches/bNNN/` (plan, manifest, results, outcomes, run log).

The `holdout` suites are never played: keep them for judging the drafts the model makes.

## Deployment: astraeus drafts from the model

astraeus's draft (`draft.cc model_draft`, on the first draft turn) measures the map features its `draft_model.h`
names in C++ (`src/map_features.cc`, a step-for-step port of `features.mjs` and mapgen's `metrics`, rounding
included; it measures all of `FEATURES`, the first 19 always and the others only when asked), then
takes the best team (`model_team`, the same as `model.mjs deployedTeam`) from `src/draft_model.h`. Without counter
terms (`draft_model::counters` false, the default) the team is chosen once, in champion id order; `model.mjs cpp`
refuses a model whose counters exceed 1e-3 unless given `--counters`. With `--counters` the header carries the counter
terms and the ladder prior's pick shares `q`: round 0 takes `deployedTeam(..., counters)` (counters against `q`, picks
in `pickOrder`), and each later draft turn re-ranks the teams holding our picks against the opponent's revealed ones
(`q` spread over its hidden picks), from team scores cached in round 0 (scoring every team there cost 60-90k fuel and
ran 5-pick draft turns out before the pick, so later picks went random). Kept champions keep their pick order, so the
draft analysis's per-body leads restart only when the team changes. draft2's counters (at most ~0.012 logit) lost
1.6 points to the same model refitted without them (`draft2-noctr`, deployed until CHANGES 261), so astraeus ships without.
Deployed since CHANGES 261: `draft3-cheap`, draft3 refitted on 23 features (no `sight_gap`, `narrow`), a link lab as below.
`draft2-noctr` links draft2's `games.jsonl`, `maps.jsonl`, `prior.json` and `ladder.jsonl`, with a copy of its
config and of its `model.json` with `lam.ctr` 1e9; `model.mjs fit --lab replays/draftlab/draft2-noctr` refits it (~1 min).
`params::map_model_draft = false` turns the model off (the old table draft
everywhere). Pick counts other than 3-5, test drafts and any failure fall back to the old table draft (spawns
joined only by dash or crystal did too until the split-maps commit, below) (`params::draft_three/four/five`, v61's Tavi switch
on 3 picks); off that fallback Vesper Vale may be drafted.

```
node tools/draftlab/model.mjs cpp --lab replays/draftlab/draft3-cheap    # regenerate src/draft_model.h after a refit
node tools/draftlab/model.mjs cpp --lab replays/draftlab/draft2 --counters --out DIR/src/draft/draft_model.h
node tools/draftlab/model.mjs teams --lab replays/draftlab/draft3-cheap  # the deployed team per map (or --features FILE)
node tools/draftlab/native.mjs --lab replays/draftlab/draft3-cheap maps maps/gen [--src DIR/src/draft]   # offline parity, no games (zig or c++)
py tools/draftlab/parity.py --lab replays/draftlab/draft3-cheap maps --jobs 4      # in-game parity, round 0 only
py tools/draftlab/parity.py --lab replays/draftlab/draft2 --bot DIR --counters maps   # a --counters build
```

- **native.mjs** compiles `native_main.cc` with `map_features.cc` natively (`zig c++`, else `$CXX` or `c++`; no FMA
  contraction), feeds it decoded maps (camps in reversed order, as the engine's need not be the file's) and compares
  the map key, every feature of `FEATURES` (the `--lab` model's or not) and the team with the JS exactly. It runs our
  own BFS where the bot uses the engine's distance fields.
  Directories are not recursed. On 2026-10-28 all 2411 maps of the pool matched (night1's model); after the cost
  rewrite, the 70 ladder maps and 125 others across suites, pick counts and edge cases (no `altar_ratio`, no `camp_near`,
  no camps, dash and crystal access, crystal-only spawns) matched (night1's 02:14 snapshot). On 2026-10-30, with the
  25 features (draft2-noctr's team): every map of draft3's pool and holdouts matched (PLAN-draft3.md).
- **parity.py** builds a debug copy with `params::draft_parity` on (`bots/variants/dl-parity`; it measures every
  feature), plays it against itself with `cambc run-batch --rounds 1`, and reads the `FEAT key values`,
  `TEAM key picks team` and `FEATFUEL key fuel` lines its draft bot prints in draft round 0 from the replays'
  `team-a/b.stdout`. It compares them with `features.mjs` and `model.mjs teams` and writes
  `replays/draftlab/parity/<time>/report.txt`; both teams must print the same lines (the features are measured from
  team A's side, as mapgen does). Its `FEATFUEL` is all 25 features in a debug build (2026-10-30: median 3.0M, max
  8.5M on a dash-lattice of the 10M first turn): an upper bound; the release numbers are below.
- **Cost:** 2 engine distance fields (team B's are team A's mirrored: the map is symmetric and distances exact), the clearance BFS (stopped at 6), the dash travel (dashes tried only from
  tiles beside something unwalkable, then Dial's algorithm from the tiles they improve), a few passes over the map
  and at most 792 teams scored. Counted offline as WASM instructions (~1 fuel each) with the bot's compiler and
  flags, our BFS left out: ladder median 1.1M, max 4.5M (01starvation); `edge_case/gauntlet` 6.6M (dashes help
  almost everywhere); the engine fields add ~0.5-1M. The port as first written cost 14-19M on 100x100 maps, which
  would have run the first draft turn out of fuel before the first pick (a random draft). metrics' last fallback
  (spawns joined only by dash or crystal; ~6% of generated maps, no ladder map) takes one crystal travel field
  (team B's mirrored too; metrics computes both). Its Dial loop relaxed 40 tiles for each popped tile, up to 9.2M
  on dash-lattices, and ran the first draft turn out on 34 of 4,024 split maps; tiles pop in distance order, so
  the first crystal to reach a tile is its best, and now each tile takes a crystal at most once (a byte mask read 7
  words a box). Every pass over the map is ~1 fuel a WASM instruction, so the passes work 8-16 tiles a word or SIMD
  vector (map_features.cc; the plain loops cost 40-100 fuel a tile, and the auto-vectorised ones little less).
  `FEATFUEL` measures the cost in-game, and
  `DRAFTTURN` whether the analysis that follows still finished in round 0 (if not, it resumes on later draft turns
  at 100k each).
- **First draft turn** (release, `--rounds 0`, 2026-10-30; `firstturn.py` measures it): with today's header, on all
  66,987 pool and holdout maps, start-up plus the model draft median 1.8M, max 6.9M on the maps the bot models
  (split maps declined). Two fixes made that safe: the dash table is built at compile time (~300k a map) and the leap masks by row
  dilation (up to 1.6M on lattices); and the first turn's reserve is 500k (was 40k), because the analysis' estimates
  (ward sites, the index) ran short and, with the fuel the features saved, ~40 maps ran the turn out before the
  pick (fall-custom `giant` does so on main too). Per feature on the 1,562 heaviest maps: `sight_gap` median 1.1-1.3M,
  max 2.2M (a bit-parallel BFS per sampled tile, stopped early; 2.85M before); `narrow` with its playable mask
  0.3-0.6M, max 0.73M; `camp_altar` up to 0.26M; `dash_gain`, `spawn_ring`, `max_group` next to nothing. All 25
  together ran the first turn out on some of those maps: a header naming `sight_gap` or `narrow` ships only after
  `firstturn.py` passes on it (PLAN-draft3.md). 2026-10-31, split maps model-drafted and the cheaper passes (the
  73 maps that ran out with the split-maps commit, the 200 heaviest split maps, 100 random split, 100 random others
  and giant; 880 team-drafts): none ran out; start-up plus model draft on split maps median 4.3M, max 7.0M
  (fresh-9178 dash-lattice), others median 1.7M, max 4.1M, fall-custom `giant` (256x256) 8.25M (it ran out on
  main inside `compute()`, ~20M there). `giant` was deleted the same day: 6.5x the area of the rules' largest map
  (100x100) and of any the platform publishes, it set the fuel bar alone.
- **Exactness:** the only expected differences from the JS are `log`/`log1p` in the last bit (WASI libc against
  V8), which can flip a team only on a tie within 1e-15.
