# Camp destinations with astraeus-style farm terms (farm2)

Continuation of [CHOICE.md](CHOICE.md), November 5, 2026. No bot, cache, manifest, earlier
script or earlier result changed. New scripts are `tools/fish/farm2_*`. New derived files are in
`replays/fish-farm2/<cohort>/` and `replays/fish-confirm-farm2/`. Results are the `farm2-*.json`
files next to this report.

**Result.** Adding astraeus's reward-rate terms to the conditional logit moves held-out accuracy
from 61.6% to **65.9%** on the fifth cohort: **75.7%** after payout (was 69.2%) and **59.8%**
after spawn (was 56.8%). On the 96-game confirmation cohort, which no destination model had used,
it moves from 58.0% to **62.1%**. The gain over the frozen logit is positive in every
match-group bootstrap except fourth-cohort post-spawn. Post-spawn choice is still the weak half.
Four further distinct ideas left it flat, and so did a per-move heading diagnostic.

## Data and splits

- **Episodes and labels**, unchanged from CHOICE.md (`choice-v1`):
  - starts: post-payout and spawn-exit starts with no visible enemy;
  - label: the first camp-directed hit, or occupation of a different empty group, within 40 rounds;
  - candidates: reachable groups other than the group just paid out;
  - denominator: every non-opening episode with status `hit`. Rows whose label is not a candidate
    count as errors.
- **Cohorts**: model (124 games), third (43), fourth (46), fifth (94), and confirm (96). The
  confirm cohort's `decisions-v2`/`routes-v3`/`choice-v1` files were built for this pass with the
  unchanged scripts into `replays/fish-confirm-farm2/`, from the existing `replays/fish-confirm`
  caches and `confirmation-manifest.json`.
- **Splits**, fitted on whole cohorts:
  - **A**: fit on model+third+fourth, test on fifth and confirm.
  - **B**: fit on fifth, test on model, third, fourth and confirm.
- **Comparisons**: the wait baseline (`routes_model.route(x,'ready')`) and the frozen
  `choice-fit.json` logit. That logit was fitted on model+third+fourth, so in split B it is
  in-sample on those three cohorts while farm2 is not.
- **Bootstrap**: farm2 minus frozen-logit accuracy, 10,000 resamples of match groups. The
  confirmation manifest lacks group ids, so match ids are used there (95 units).

## Causal extras (`farm2_data.py`)

Per episode, this rebuilds the actor's own memory from its recorded perspectives up to and
including the decision turn's start, and nothing later:

- **Remembered live health** of each group:
  - each camp tile's last seen hp, used only if seen after the group was last seen empty or
    respawning;
  - members missing from a visible living group within 6 tiles of the actor count as dead;
  - otherwise full public hp.
- **Per group**: awake members, last capture state and timer, and the raw respawn countdown.
- **Static walks** (8-neighbour BFS; terrain, camp tiles and the other spawn blocked):
  - from our spawn and from the enemy spawn to the group's adjacent tiles;
  - from the group to a tile within 1 of an altar.
- **Visible allies' stats** at the start.
- **History**: ally sightings (last and previous position), allies seen at the last recall start,
  and the last recall, death and off-spawn position.

Labels never enter. The static group naming uses all frames to map live ids to map groups, as in
`decision_data.py`, but no dynamic state is copied from them.

## The model (`farm2_features.py`, sets `base+hp+rate+home+stale+crew+size`)

Score `w · f(c)`; argmax, ties to the lower group id. There are separate weights after payout and
after spawn. `base` is the frozen logit's feature list (CHOICE.md table). Added:

| Set | Features (candidate `c`) | astraeus origin |
| --- | --- | --- |
| `rate` | `worth = 3·gems + gold`. `R = max(1, wait + kill + cap)`, where `wait = max(walk, remembered respawn)`; `kill` = remembered live fighter-plus-cluster hp / (own Strength + Strength of visible off-spawn allies within 4 of the group), using full hp if respawning and 0 if empty; `cap` = 7 unless empty. `H = 100·max(1, max(W,H)/50)`. Features `logworth = ln(1+worth)`, `logR = ln R`, `lograte = logworth − ln R − ln(1+R/H)` | `rate()` (camps.cc), `cycle_horizon`, `capture_rounds`, the crew share in `crew_rate` |
| `home` | `logshare = ln max(0.05, min(1, 2·them/(us+them)))` over the two spawn walks; `enemy_near = them ≤ us` | `home_ground()` weight |
| `stale` | `empty_age` (age of an empty sighting); `resp_expired` (remembered respawning, countdown elapsed) and its age past expiry; `alive_age` (age of a living sighting) | the respawn and belief ages in `farm_turn` |
| `hp` | `hp_fight` = remembered live hp / own Strength / 100; `damaged` (live hp below full); `awake`; `part_frac` (fraction already cleared) | `live_health`, the belief health in the claimed/crew branches |
| `crew` | Strength of visible off-spawn allies within 4, over own Strength; any such ally; the kill rounds they save | `crew_work`, `plan_crew` |
| `size` | number of members / 5; living Elk; living wolves; no gems (`gold_only`) | gem vs gold pricing |

Fitted weights, all five cohorts (`farm2-fit.json`: 5,507 payout and 10,070 spawn episodes, L2
0.1, damped Newton). These are surrogate weights, not Fish constants. Correlated features must be
read together: `lograte`, `logworth` and `logR` share terms.

| Feature | After payout | After spawn |
| --- | ---: | ---: |
| **effective ln(1+worth)** (`logworth` + `lograte`) | **+2.82** | **+1.82** |
| **effective ln R** (`logR` − `lograte`) | **−1.61** | **−0.16** |
| effective ln(1+R/H) (−`lograte`) | +1.60 | −0.94 |
| `logwait` | −3.04 | −2.20 |
| `wait` | +0.05 | +0.10 |
| `respawn_part` | −0.93 | −1.46 |
| `empty` | −2.86 | −2.53 |
| `empty_age` | +0.24 | +0.27 |
| `respawning` | +0.78 | +0.91 |
| `resp_expired` / `…_age` | −0.33 / −0.08 | −0.36 / −0.17 |
| `alive_age` | −0.20 | −0.29 |
| `unknown` | −0.02 | −0.72 |
| `damaged` | +0.75 | +0.78 |
| `part_frac` | −1.87 | −0.99 |
| `hp_fight` | −0.89 | −0.52 |
| `awake` | +0.51 | +0.15 |
| `alive_fight` / `alive_dps` | −0.16 / +0.61 | +0.04 / +0.41 |
| `monolith` / `golem` | −1.87 / −0.64 | −0.15 / −0.05 |
| `has_elk` / `wolves` | +0.12 / −0.32 | +0.55 / +0.17 |
| `clusters_only` / `gold_only` | +0.42 / −0.45 | +0.98 / −0.44 |
| `gold` / `gems` (linear, /100, /10) | −0.58 / −0.06 | −0.32 / −0.01 |
| `n_types` | −0.45 | −0.01 |
| `logshare` | +2.43 | −0.03 |
| `enemy_near` | −0.93 | −1.13 |
| `terr` / `terr_neg` | −0.28 / −0.12 | −1.25 / +0.27 |
| `visited` / `route` / `last` | +0.19 / +0.67 / 0.00 | +0.42 / +0.49 / +0.37 |
| `ally_recent` | −0.87 | −0.66 |
| `ally_closer` / `allies_near` | +0.45 / −0.10 | +0.41 / +0.06 |
| `crew_frac` / `crew_any` / `crew_kill` | −0.10 / −0.10 / +0.04 | −0.09 / −0.12 / +0.03 |

How to read it:

- **Worth now matters**, on a log scale with gems at about 3 gold. The frozen logit's linear
  `gold`/`gems` had almost no weight.
- **After payout** Fish behaves like astraeus's rate: log worth against log total time
  (walk/respawn + clear + capture), and strongly prefers its own half (`logshare`).
- **After spawn** time beyond the walk/respawn wait hardly counts (effective ln R −0.16). What
  counts is worth, wait, and memory state: avoid remembered-empty, unknown and enemy-near groups;
  prefer respawning ones whose timer runs out about when it arrives.
- **Partly cleared, awake groups are preferred**, whatever their remaining hp. This is the same
  "join a fight under way" sign the frozen logit's `ally_closer` showed.

## Results (unscoreable rows count as errors)

Split A, fit on model+third+fourth ([farm2-heldout-A.json](farm2-heldout-A.json)):

| Cohort | Reason | farm2 | Frozen logit | Wait |
| --- | --- | ---: | ---: | ---: |
| fifth | all | **2,516/3,819 (65.88%)** | 2,351 (61.56%) | 2,002 (52.42%) |
| fifth | payout | **1,107/1,462 (75.72%)** | 1,012 (69.22%) | 925 (63.27%) |
| fifth | spawn | **1,409/2,357 (59.78%)** | 1,339 (56.81%) | 1,077 (45.69%) |
| confirm | all | **2,439/3,931 (62.05%)** | 2,278 (57.95%) | 2,004 (50.98%) |
| confirm | payout | **998/1,400 (71.29%)** | 906 (64.71%) | 854 (61.00%) |
| confirm | spawn | **1,441/2,531 (56.93%)** | 1,372 (54.21%) | 1,150 (45.44%) |

Split B, fit on fifth only ([farm2-heldout-B.json](farm2-heldout-B.json)); the frozen logit is
in-sample on model, third and fourth:

| Cohort | Reason | farm2 | Frozen logit | Wait |
| --- | --- | ---: | ---: | ---: |
| model | all / payout / spawn | **2,880/4,560 (63.16%)** / 1,150/1,580 (72.78%) / 1,730/2,980 (58.05%) | 59.01% / 66.46% / 55.07% | 49.01% / 61.08% / 42.62% |
| third | all / payout / spawn | **1,064/1,827 (58.24%)** / 390/619 (63.00%) / 674/1,208 (55.79%) | 53.86% / 59.45% / 50.99% | 46.20% / 56.87% / 40.73% |
| fourth | all / payout / spawn | **1,035/1,726 (59.97%)** / 416/608 (68.42%) / 619/1,118 (55.37%) | 57.94% / 66.61% / 53.22% | 47.68% / 61.35% / 40.25% |
| confirm | all / payout / spawn | **2,436/3,931 (61.97%)** / 1,007/1,400 (71.93%) / 1,429/2,531 (56.46%) | 57.95% / 64.71% / 54.21% | 50.98% / 61.00% / 45.44% |

Match-group bootstrap, 95% interval of farm2 minus frozen logit, in points:

| Split, cohort | All | Spawn |
| --- | --- | --- |
| A, fifth (20 groups) | +3.1 to +5.7 | +1.2 to +5.0 |
| A, confirm | +2.7 to +5.4 | +1.0 to +4.5 |
| B, model | +2.4 to +5.9 | +0.9 to +4.9 |
| B, third | +2.7 to +6.1 | +2.6 to +6.9 |
| B, fourth | +0.5 to +3.8 | **−0.5 to +4.6** |
| B, confirm | +2.5 to +5.5 | +0.6 to +4.0 |

Every miss is in the sibling `.errors.jsonl.gz` files.

Post-spawn accuracy by champion, fifth cohort, split A:

| Champion | Correct |
| --- | ---: |
| Vesper | 206/309 (66.7%) |
| Willow | 114/185 (61.6%) |
| Cassi | 252/410 (61.5%) |
| Issac | 214/352 (60.8%) |
| Marcella | 183/303 (60.4%) |
| Vendetta | 244/417 (58.5%) |
| Heart of Ruin | 183/363 (50.4%; 46.8% under the refitted base logit) |

## What helped and what did not

Held-out accuracies of every variant are in [farm2-exploration.json](farm2-exploration.json)
(gem price 3, crew Strength in `rate`). Accuracy in %; the `base` row is the refitted frozen
feature list:

| Sets | A fifth all / spawn | A confirm all / spawn | B model / third / fourth spawn |
| --- | --- | --- | --- |
| `base` | 61.6 / 56.9 | 57.9 / 54.2 | 53.9 / 51.4 / 52.6 |
| `base+hp` | 62.1 / 56.7 | 58.5 / 54.4 | 54.6 / 51.6 / 52.7 |
| `base+rate` | 64.4 / 59.0 | 60.3 / 55.2 | 56.5 / 54.6 / 54.0 |
| `base+home` | 61.7 / 56.7 | 57.9 / 53.9 | 54.5 / 51.2 / 53.3 |
| `base+stale` | 62.4 / 57.9 | 58.3 / 54.7 | 54.6 / 53.5 / 52.9 |
| `base+size` | 62.3 / 57.1 | 58.6 / 54.5 | 55.0 / 53.6 / 54.1 |
| `base+altar` | 61.5 / 56.6 | 57.8 / 54.0 | 53.9 / 51.5 / 52.6 |
| `base+recall` | 61.4 / 56.6 | 57.8 / 54.5 | 53.9 / 52.3 / 53.2 |
| `base+danger` | 62.2 / 57.4 | 58.6 / 54.9 | 54.4 / 52.3 / 52.7 |
| `base+mates` | 61.6 / 56.9 | 57.9 / 54.2 | 54.2 / 52.2 / 52.3 |
| `base+allymem` | 61.9 / 57.1 | 57.7 / 53.9 | 53.7 / 52.6 / 53.2 |
| `core` | 63.2 / 58.1 | 60.6 / 56.4 | 54.5 / 53.4 / 52.1 |
| `base+hp+rate+home+stale+crew+size` | 65.9 / 59.8 | 62.0 / 56.9 | 58.1 / 55.8 / 55.4 |
| `base+hp+rate+home+stale+crew+size+habit` | 66.1 / 60.2 | 61.8 / 56.5 | 58.4 / 57.0 / 56.9 |
| `base+hp+rate+home+stale+crew+size+follow` | 66.1 / 59.8 | 61.9 / 56.8 | 58.0 / 56.2 / 55.0 |
| `base+hp+rate+home+stale+crew+size+altar2` | 65.7 / 59.9 | 62.1 / 57.3 | 58.4 / 56.9 / 55.7 |
| `base+hp+rate+home+stale+crew+size+emptyworth` | 65.9 / 60.1 | 62.1 / 57.0 | 58.6 / 56.4 / 55.5 |
| `base+hp+rate+home+stale+crew+size+allymem+recall+altar+danger+mates` | 65.8 / 59.8 | 62.1 / 57.3 | 58.1 / 56.5 / 55.6 |


- **Helped:**
  - **reward rate (`rate`)**, by far the most. In leave-one-out runs of the same driver (all 12 sets, not saved), removing it costs 1.3-2.3 points
    overall and 0.4-1.4 after spawn.
  - **Pricing gems at 3-5 gold.** Over {1, 3, 5, 10, 30, 100}, 3 and 5 are best: at 100 (gems
    only) post-payout loses about 4 points.
  - **The home-ground weight (`home`)**, mostly after payout.
  - **Stale-memory ages (`stale`)**, mostly after spawn: +0.4 to +1.7 there.
  - **Adding visible allies' Strength to the clear time** (`crew=1`): +0.0 to +1.1 overall.
- **Small or neutral:** remembered live hp instead of full hp in the clear time (`live_hp=0` costs
  ≤0.4), group size, and the `hp`/`crew` sets.
- **No gain, retained as negative results:**
  - camp damage taken relative to own hp (`danger`);
  - altar distance when carrying (`altar`);
  - spawn-mates and big camps (`mates`);
  - distance to the recall-start and last off-spawn positions (`recall`);
  - allies remembered within 3 of a group in the last 10/40 rounds, or seen there at recall start
    (`allymem`). This is the "decide at recall start" test.
  - visit counts and recency instead of binary `visited` (`habit`: +0.4 fifth, −0.5 confirm);
  - allies seen walking toward a group in the last 3 rounds (`follow`, the "follow the leader" test);
  - L2 1.0 instead of 0.1.
- **Small but consistent after spawn; not in the frozen model:**
  - the carrier detour (`altar2`: walk plus group-to-altar walk for gem carriers, and its log):
    +0.2 to +1.1 on spawn in all six tests, payout −0.7 to +0.2;
  - an empty group's log worth and capture-state code (`emptyworth`): +0.1 to +0.6 on spawn in all
    six;
  - both together ([farm2-exploration-altar2-emptyworth.json](farm2-exploration-altar2-emptyworth.json)):
    spawn 59.91% fifth and 57.80% confirm (split A), 58.76/56.62/55.90/56.82% (split B). That is
    +0.1 to +0.9 on spawn, but overall −0.3 on fifth. Freeze it as a candidate for the sixth
    cohort, not as a result.
- **A compact 17-feature `core` model** gets fifth 63.24% (spawn 58.12%) and confirm 60.65%
  (56.38%). Most of the post-spawn gain comes from `lograte`, `logshare` and the stale terms.

### Heading: are post-spawn misses re-decisions on the way?

`farm2_heading.py` takes the actor's position changes after the decision, up to the labelled hit.
After move k, with s the Chebyshev distance travelled so far, a group counts as headed for if the
actor is still on a shortest walk to it, `walk_g(pos) = walk_g(start) − s`. The table counts
the 948 fifth-cohort post-spawn misses under split A ([farm2-heading-A.json](farm2-heading-A.json)):

| After move | Toward both | Label only | Prediction only | Neither | No move yet |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 582 | 208 | **43** | 111 | 4 |
| 3 | 448 | 262 | **42** | 146 | 50 |
| 6 | 274 | 324 | **33** | 185 | 132 |

Walks toward our predicted group that end at the label are rare: 33-43 of the 948 misses on
fifth, and 51-82 of 1,090 on confirm. Fish's post-spawn destination is fixed at spawn exit, and our misses
are different choices, not changes of mind as new camps come into view. The frozen CHOICE.md
finding that steps after the first are 90% on a shortest path agrees.

Two limits:

- The first move from a spawn tile is often not on any shortest path, because of spawn-tile
  shuffling.
- Payout headings are undefined: the start is a camp tile, which the fields block.

## Retained counterexamples (split A, fifth, largest score margins)

- **Cleared Monolith beside spawn.** `9d651ecb658daedc`, r547/r855, and `4d752f13a0658b81` r533,
  actor 4, Heart of Ruin: predicted g27, a cleared triple-Monolith group 1 tile from spawn and
  being held (600 gems). Fish goes to g26, a lone gold cluster 10 tiles away. A capture already
  held by others is not joined after spawn. `emptyworth` lets the fit learn this but gains little
  overall, so these remain misses.
- **Walking past a nearer group.** `825fcee16f386346` r630, actor 3 (Cassi, 21 gems): predicted
  g3, a living Elk+clusters group 4 tiles from spawn. Fish walks 67 tiles to g9, gem clusters
  remembered respawning with timer 1. The nearer group was never worth it.
- **Remembered timers on unvisited groups.** `f54302b2e536a4bc` r265, actor 4 (Issac): predicted
  g6, respawned wolf+gem group 20 away. Fish waits on g3, two gold clusters 3 tiles away still 34
  rounds from respawn, and hits it 35 rounds later.
- **Exploring far from home.** `be6f364d32fd7f32` r149, actor 4 (Issac, after payout): Fish goes
  to unknown g21, deep in enemy territory (territory +54).
- **Label noise.** `72e3972091749179` r307, actor 7 (Prism, after payout): the label is a gem
  cluster hit the same round, walk 35 but within spell reach across terrain. Walk is the wrong
  travel measure for incidental ranged hits.

## Caveats

- **Not independent of my choices.** All five cohorts were used to pick feature sets. The splits
  are held out for weights only, not for model selection. Confirm a frozen fit on a sixth cohort.
  `farm2-fit-A.json` is the one to freeze for an untouched test, since it saw neither fifth nor
  confirm.
- **Confirm-cohort caveats:**
  - Its files were extracted by the same unchanged scripts, but this is their first destination
    use.
  - Its manifest has no group ids, so the bootstrap resamples matches.
  - It overlaps earlier analyses: breadth and holders, not destinations.
- **Simplified clear time:** clear time uses Strength only (no spells, items or emblems). Walks
  ignore dashes and use static camp blocking.
- **Labels** remain first hits within 40 rounds. CHOICE.md found about 8% of labels are brief
  hits followed by another group.
- **No hidden-information check** beyond what CHOICE.md already ruled out.
- **Code hashes.** `farm2_features.py` gained the `emptyworth` and `core` sets after some of the
  fit JSONs recorded its hash. The final sets' code is unchanged: re-scoring `farm2-fit-A.json`
  with the current file reproduces every split-A count.

## Reproduction

```sh
export PYTHONPATH=tools/fish OMP_NUM_THREADS=1
# confirm cohort feature files (unchanged scripts, new directory)
python3 tools/fish/decision_data.py research/fish-2026-11-05/confirmation-manifest.json replays/fish-confirm replays/fish-confirm-farm2/decisions-v2.jsonl.gz
python3 tools/fish/routes_data.py research/fish-2026-11-05/confirmation-manifest.json replays/fish-confirm replays/fish-confirm-farm2/decisions-v2.jsonl.gz replays/fish-confirm-farm2/routes-v3.jsonl.gz
python3 tools/fish/choice_data.py replays/fish-confirm replays/fish-confirm-farm2/routes-v3.jsonl.gz replays/fish-confirm-farm2/choice-v1.jsonl.gz
# extras per cohort C (choice-v1 from replays/fish-C, or fish-confirm-farm2 for confirm)
python3 tools/fish/farm2_data.py replays/fish-C/choice-v1.jsonl.gz replays/fish-C replays/fish-farm2/C/farm2-v3.jsonl.gz
python3 tools/fish/farm2_heading.py replays/fish-C/choice-v1.jsonl.gz replays/fish-C replays/fish-farm2/C/heading-v2.jsonl.gz
# fits and held-out scores
S=base+hp+rate+home+stale+crew+size; O="--opt gem_gold=3 --opt crew=1"
python3 tools/fish/farm2_fit.py research/fish-2026-11-05/farm2-fit-A.json model,third,fourth --sets $S $O
python3 tools/fish/farm2_fit.py research/fish-2026-11-05/farm2-fit-B.json fifth --sets $S $O
python3 tools/fish/farm2_fit.py research/fish-2026-11-05/farm2-fit.json model,third,fourth,fifth,confirm --sets $S $O
python3 tools/fish/farm2_evaluate.py research/fish-2026-11-05/farm2-fit-A.json research/fish-2026-11-05/farm2-heldout-A.json fifth,confirm
python3 tools/fish/farm2_evaluate.py research/fish-2026-11-05/farm2-fit-B.json research/fish-2026-11-05/farm2-heldout-B.json model,third,fourth,confirm
python3 tools/fish/farm2_heading_report.py research/fish-2026-11-05/farm2-fit-A.json research/fish-2026-11-05/farm2-heading-A.json fifth,confirm
python3 tools/fish/farm2_explore.py SET [SET...] --opt gem_gold=3 --opt crew=1 [--out FILE]
```

`farm2_lib.load` reads the newest `farm2-v{3,2,1}` extras file. The results above used v3, a
superset of v1 and v2. To score a sixth cohort, run the decision, route and choice scripts, then
`farm2_data.py`, into `replays/fish-sixth` (or a new directory). Add it to `farm2_lib.COHORTS` if
it lives elsewhere, then run `farm2_evaluate.py` with `farm2-fit.json` or `farm2-fit-A.json`.

## Sixth-cohort confirmation (untouched)

[sixth-manifest.json](sixth-manifest.json): every downloaded Fish game outside all five earlier
manifests, **53 games / 11 groups**, 21:10–21:40 UTC November 5, 13 ranked and 40 unranked, all
`v3_0_0`. `pin_cohort.py` froze `farm2-fit-A.json`, `farm2-fit.json`, `choice-fit.json` and the
feature scripts in [sixth-freeze.json](sixth-freeze.json) before any play was decoded; all hashes
matched at scoring. [sixth-audit.json](sixth-audit.json): 637,468 inputs and 240,441 completed
turns, exact. Scored with `farm2-fit-A.json` (fitted on model, third and fourth only):

| Model | All | Payout | Spawn |
| --- | ---: | ---: | ---: |
| **farm2 (fit A)** | **1,252/2,109 (59.36%)** | 476/690 (68.99%) | 776/1,419 (54.69%) |
| choice logit (CHOICE.md) | 1,148/2,109 (54.43%) | 426/690 (61.74%) | 722/1,419 (50.88%) |
| wait baseline | 942/2,109 (44.67%) | 385/690 (55.80%) | 557/1,419 (39.25%) |

farm2 matches or beats the logit in **11/11 groups**; a bootstrap over the 11 groups (10,000
resamples) gives a gain of **+2.7 to +7.8 points**. (`farm2_evaluate.py`'s own interval says
"53 groups": it falls back to games when a manifest is unknown, so use the group figure.) Ranked
games: 299/515 (58.1%) vs 271/515 (52.6%). This cohort is harder for every model (baseline 44.7%
vs 52.4% on fifth); compare gains, not levels. Results: `farm2-sixth-A.json` (+ errors),
`choice-sixth-fit.json` (+ errors). All six cohorts are now used.
