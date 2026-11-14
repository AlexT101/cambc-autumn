# Running an emblem lab, step by step

How to run the emblem lab from scratch, as round 4 was run on ocean (2026-11-10, the 96-core box).
[README.md](README.md) explains how the lab works; this file is the order of operations. It follows the draft
lab's [RUNBOOK](../draftlab/RUNBOOK.md), which has more on disk, ladder data and maps. Commands run from the
repository root, `py` = `python3`.

## 1. Settle the decisions first

Write the answers into the lab's `config.json` (step 5) before `init`; it holds only what differs from
`lab.py DEFAULTS`.

- **Which bot** (`bot`, default `ocean`; `init --source REF`, default HEAD): the commit whose bot the vehicles
  copy. Its own emblem choice (`best_emblem`: the learned table, else the current logic) is the base every arm is
  measured against, so the lab's result is a change to that bot and nothing older.
- **Games:** at least 1M (round 2 and 3 had 800k each and resolved about ±0.03 win points a decision, ±0.8 points a
  policy). Round 4 played 80k-game batches at `CAMBC_SLOT_WEIGHT=35` (an A/B has weight 1, the draft lab 2), about
  7 minutes a batch with other jobs on the box.
- **Draft mix** (`draft_mix`): which teams the lab side plays: `explore` (random, without `explore_exclude`;
  `explore_require_share` of them hold `explore_require`, the draft's team lock), `ladder` (the top `top` other
  teams' compositions since `patch_since`, by frequency) and `model` (the shipped draft model's team on that map:
  what the bot drafts there). Rounds 3 and 4: 40 / 30 / 30.
- **Opponents** (`opponents`, round 4 on): `self` is a second lab team on the same vehicle (both sides draw
  emblems and log); any other kind is a sparring body from `opponent_bots` (bot directories), which drafts and
  shops for itself. Round 4: 40% self, 30% the Fish body, 30% the Mite body (`spar-dvn952/953-Flp4`, `-Mt3q`:
  noise seeds no gate plays). A body game logs one team, so it carries half a mirror game's decisions.
- **Ladder window** (`patch_since`): as the draft lab's; round 4 used the last four days.
- **Forcing** (`p_force`, `uniform_share`, `p_uniform`, `corr_model`): leave at round 2's values unless there is a
  reason. `corr_model` is the fit whose static arm gains steer the proposal: the previous round's per-decision
  model (`dmodel*.json`), or this round's interim fit from a later batch on (every row logs its own probabilities,
  so the proposal may change between batches).

## 2. Check the box and the disk

```
uptime; ps -eo pid,etime,args | grep -E "[a]b.py|[r]un_batched|[l]ab.py|[c]ambc run-batch" | cut -c1-160; tmux ls
df -h /; free -g
```

A million games need about 4.5 GB of compressed decisions (`decisions/bNNN.jsonl.zst`, which the fit streams:
never decompress them to disk, ~25 GB a million games), 3.7 GB of `games.jsonl` and 7 GB of replays per 80k-game
batch while it is merged (two batches at once). Keep 40 GB free. The fit holds every row in memory (~30 GB a
million games, up to twice that while loading): run it after the games, or with few threads on a part of them.

## 3. Ladder data

```
py tools/fetch_replays.py --list
py tools/fetch_replays.py --top 11 --since 2026-11-06 --kind ranked --max-groups 0 --no-replays --threads 8
```

## 4. Maps: a pool no lab or A/B has played, and held-out suites to judge on

At most ~30k maps a mapgen command. Round 4: 400 suites for the pool (102,400 maps) and 120 held out, `--mix
ladder-v2`, about a minute per 100 suites:

```
for r in 3100000-3100099 3100100-3100199 3100200-3100299 3100300-3100399 3110000-3110059 3110060-3110119; do
  node tools/mapgen/mapgen.mjs suite --seed $r --mix ladder-v2 --jobs 24 --out 'maps/suites/fresh/fresh-{seed}'; done
```

Record the seeds in `maps/SUITES.md`. The fits cross-validate by map, so a selection is never scored on a map it
was chosen on; the held-out suites are for the A/Bs only.

## 5. Create the lab and start it

```
mkdir -p replays/emblab/r5
cat > replays/emblab/r5/config.json <<'EOF'
{"seed": 5, "bot": "ocean",
 "pool": ["maps/*.map26a", "maps/suites/fresh/fresh-31000[0-9][0-9]", "maps/suites/fresh/fresh-31001[0-9][0-9]"],
 "holdout": [], "draft_lab": "shipped", "top": 10, "patch_since": "2026-11-06T00:00",
 "draft_mix": {"explore": 0.4, "ladder": 0.3, "model": 0.3}, "explore_exclude": ["stellar"],
 "explore_require": ["cassi_and_issac"], "explore_require_share": 0.5,
 "opponents": {"self": 0.4, "fish": 0.3, "mite": 0.3},
 "opponent_bots": {"fish": ["bots/variants/spar-dvn952-Flp4", "bots/variants/spar-dvn953-Flp4"],
                   "mite": ["bots/variants/spar-dvn952-Mt3q", "bots/variants/spar-dvn953-Mt3q"]},
 "corr_model": "replays/emblab/r4/dmodel-dr.json"}
EOF
tmux new -d -s el-r5 "cd $PWD && source ~/venv/bin/activate && export CAMBC_SLOTS=86 CAMBC_SLOT_WEIGHT=35 && \
  python3 tools/emblab/lab.py init --lab r5 2>&1 | tee replays/emblab/r5-init.log && \
  python3 tools/emblab/lab.py run --lab r5 --games 80000 --hours 3 2>&1 | tee -a replays/emblab/r5-run.log; exec bash"
```

`init` (~15 min for 100k maps, one core) freezes the bot, measures the pool's maps, writes the ladder prior and
the shipped draft model's team per map (`draft_lab: "shipped"` reads the lab named in the bot's `draft_model.h`).
Check its last lines: the map count, the ladder team-games per pick count, the draft lab. **Smoke first:** copy
`config.json` and `prior.json` to a second lab directory, link `maps.jsonl`, and `run --games 1600 --batches 2`
there; its two merge lines should read 0 errors and 0 draft mismatches (step 6).

`run` plays until `--batches` or `--hours` is reached; `touch replays/emblab/r5/stop` ends it after the batch in
play. It resumes: start the same command again.

## 6. Watch it

```
tail -f replays/emblab/r5/lab.log
```

Healthy merge lines: `0 errors`, a handful of draft mismatches (over 2% stops the run), `0 over by round 5` (a
resign on a broken draft handoff), few `cut log lines`, out-of-fuel lines per lab team-game near the bot's usual,
and the opponents in the configured shares. The proposal's probabilities can be checked on any batch: over rows
with k < 12, the mean of 1 / P(base) over rows that took the base is 1, and the sum of 1 / P(chosen) over rows
that left it is the mean number of other drawable arms (README, "Checks").

## 7. Fit and select

```
S=gold_side,contested_share,spawn_dist,area,gems_side,big_share,cluster_share,altar_centre,altars
cp replays/emblab/r4/dmodel-static.json replays/emblab/r5/dmodel-static.json     # the last round's searched penalties start the fit
py tools/emblab/with_slots.py 64 node tools/emblab/dfit.mjs --labs r5 --variant static --mapdr --mapsplits $S --mapcuts 2,4,6 --threads '{slots}' --out replays/emblab/r5/dmodel-static.json
py tools/emblab/select.py replays/emblab/r5/dmodel-static.json [--maps]           # selection rules on the dumped sums, cross-fitted, in seconds
node tools/emblab/dfit.mjs --labs r5 --search --rounds 1 --threads 64             # optional: penalties by 5-fold CV over maps (they barely moved in rounds 3 and 4)
```

`with_slots.py` holds CPU slots for the fit's threads, so games yield cores to it. `--labs a,b` fits several
labs of one design together (round 4's two phases). `--mapdr` implies `--dr`; both dump their sums
(`.drsums.bin`, `.mapsums.bin`) for `select.py`.

Read, in the `.md` beside each model: the cross-fitted gain per decision of each selection (class 0, z 2 is the
one that shipped twice), its gain against each opponent kind, and for `--mapdr` the nested estimates (a map-keyed
selection must beat the static one there, not in the single-level table, which is the best of many).
About 28 decisions a team-game: +0.08 points a decision was +2.3 points in round 2's A/B.

## 8. Candidates and A/Bs

```
py tools/emblab/select.py replays/emblab/r5/dmodel-static.json --write tb-z2 --out replays/emblab/r5/sel-tb-z2.json
py tools/emblab/candidate.py replays/emblab/r5/sel-tb-z2.json --key tb-z2 --buy --source bots/variants/ocean-<sha7> --out bots/variants/oc-emb5-tb2
FAST="CAMBC_BIN=$PWD/tools/fastengine/runner/fastrunner FASTRUNNER_MODE=native CAMBC_SLOTS=86"
env $FAST python3 tools/ab.py variants/oc-emb5-tb2 variants/ocean-<sha7> --no-test-draft --suites maps/suites/merged/emb5-h1
py research/notes/ideas-2026-11-09/freshgate-tools/fgate.py variants/oc-emb5-tb2 variants/ocean-<sha7> --fish-body Flp4 --mite-body Mt3qro --max-seeds 24
```

- **Build with `--buy`.** The vehicle draws an arm at the purchase only; ocean's forecasts (`prices()`,
  `affordable_prefix()`, the trip home) keep pricing the base's emblem. `--buy` deploys exactly that: a second
  table read by `buy_shards` alone. `--flat` writes the arms into `learned_arm`, which ocean's forecasts read too:
  round 4's first candidate built that way read 47.9% of 20,480 in the mirror and -2.9 points at the gate, for a
  selection the lab scored at +0.15 points a decision.
- **A candidate from the mid-run fit is worth an early A/B** (step 7's commands work while the lab plays): it showed
  the forecast problem two hours before the final fit.
- Judge on at least 20k mirror games on held-out suites and on the fresh gate (the gate's bodies are other noise
  seeds than the lab's). A table that wins the mirror and loses to the bodies is a mirror artefact: do not ship it.
- Merging into the line needs a live paired result (EXPERIMENTS "Why v90-v93 lose live"; TEST-STANDARD rule 7): the
  lab's deliverable is a gated candidate. Record the run in research/EXPERIMENTS.md; a shipped table goes to
  `bots/ocean/src/economy/` with a CHANGES entry and a frozen copy.

## 9. Things that went wrong in round 4

- **The slot pool forgot the lab's weight.** A member file is created and then locked; another job's scan in
  between unlinks it, and that process's group counts at weight 1 for the rest of its life. A batch took 25 minutes
  instead of 6.5 (19 of 86 slots). Fixed since: cpu_slots.py locks and writes member records before publishing
  them. Still check `lab.log`'s batch times.
- **`pkill -f` / `pgrep -f` match their own shell.** A watcher that started a keeper for "its own" command line
  registered a phantom waiting group, which holds every other job back: match `^python3 tools/emblab/lab.py ...`
  from a script file.
- **A fit while the lab plays takes the lab's slots** (`with_slots.py`): 720k games took 17 minutes on 36 slots.
