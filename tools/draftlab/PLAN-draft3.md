# Draft lab draft3 and emblem lab round 3: plan (2026-10-30)

Prepared, not launched. Both labs retrain astraeus's learned tables for the bot as it is now and for the new map
families. Read with [README.md](README.md) and [../emblab/README.md](../emblab/README.md).

## Why now

- **The bot moved.** The macro overhaul (CHANGES 235-241) beats ef8f0b8, the bot both tables were trained on, ~60%
  of the time. Champion values and emblem values are values *of how we play them* (night1's ladder cross-check:
  self-play champion values barely correlate with the ladder's), so both tables are stale.
- **The maps moved.** mapgen's new families (2316775d: topology, scenarios, quirks) are in every suite, and the
  draft2 and round-2 pools are deleted.
- **The model could not see the new axes.** draft2's 19 features have no dash-shortcut-between-spawns, corridor,
  spawn-surround, group-size, camp-by-altar or sight-against-walk term. draft3 adds six (README "Features").

## Decisions taken

- **Fuel:** both labs play at the real 100k budget (the runners' default; no `--fuel`). Out-of-fuel turns are rare
  (~4-5 a game in today's A/Bs) and the tables should be learned for the bot as deployed.
- **No counter picks.** draft2's counters lost 1.6 points (CHANGES 234; 3938c0f removed them). draft3 fits with
  `lam.ctr` 1e9 from the first batch (`initial_lam`), so Thompson, probes and the final model are counter-free and
  `model.mjs cpp` takes it as it is. Pair **synergy** stays (fitted, deployed).
- **Pick counts stay split:** one fit and one plan per pick count (3, 4, 5), each penalised toward the pooled fit
  as before, about equal games each (`pick_shares`). Nothing is extrapolated across pick counts.
- **Prior data: start from scratch** (recommended; `prior_games` null, `explore_batches` 1). Reasons:
  - Prior games would only steer batch 0's Thompson draws: with `prior_weight` 0 afterwards they leave the fit,
    and team choice depends only on the map, so the fit is unbiased either way. The gain is efficiency in one
    batch out of ~20.
  - That steering would be stale: draft2 learned 26d273e (before the macro overhaul and on the old maps), and its
    maps cannot give the six new features (deleted suites, z 0 for every new term), so batch 0 could not target
    the new axes at all.
  - Its ~55k old maps would join `maps.jsonl` as `prior:` rows and set the standardisation (mean, sd) of the old
    features for the whole lab, the old generator's maps outweighing the new pool.
  - Batch 0 as pure uniform exploration (40k games) is useful data in itself: it covers champions draft2 rarely
    played and the new families evenly, and from batch 1 Thompson uses the lab's own fit (night1's map terms
    already paid at 9k games).
  - The emblem lab likewise starts clean: `corr_model` null (round 1's corrections are from 1c0d627, two bots
    ago), the proposal is the current logic's own values plus 30% uniform. Its base policy is the current
    astraeus, whose table already holds round 2's result: departures are measured from it.
  - Kept from earlier labs: hyperparameters only (draft2's searched penalties as `initial_lam`, re-searched at
    batches 1, 4 and 9 and at the end), and the ladder prior (top-20 compositions since 2026-10-26).
- **Order:** draft3 first, deployed (or not) before emblem round 3 starts; emblem round 3 freezes that bot and
  drafts 40% of its teams with draft3's deployed team per map. Reasons: the emblem table is per (pick count,
  champion, ordinal), so it should be learned on the champions astraeus will actually draft; the draft lab's
  values are learned under the emblem table then in force, which is the one the emblem lab's base policy keeps.
  Running both at once would halve each lab's speed on the shared 94 slots and give each a moving partner.

## Source bot

- Merge this branch (the 25 features in `map_features.cc`; with today's `draft_model.h` the bot measures only the
  19 it uses, so play is unchanged) and freeze current main: `py tools/draftlab/lab.py init --lab draft3
  --source <main sha>` copies `bots/astraeus` at that commit to `bots/variants/astraeus-<sha7>`. Vehicles draft from
  the trainer table, so the bot's feature code is not exercised in lab games.
- Check before launch that `params::test_draft` is off and nothing else is running (`tmux ls`, `ps`): each lab
  takes all 94 CPU slots.

## Maps

Generated 2026-10-30 into the primary checkout's `maps/` (git-ignored; rebuild with
`node tools/mapgen/mapgen.mjs suite --seed A-B --out maps/fresh-{seed}`):

| Use | Suites | Maps |
|---|---|---|
| Pool (both labs) | ladder (`maps/*.map26a`), `fall-custom`, `gen`, `gen-s1`, `fresh-6003`..`6040` | ~10.4k |
| Pool (both labs) | `fresh-9100`..`9240`, without `9210` (mapgen's dungeon designer throws on that seed) | 35,840 |
| draft3: judge | `fresh-9300`..`9319` | 5,120 (10,240 games) |
| draft3: confirm | `fresh-9320`..`9339` | 5,120 |
| emblem r3: judge | `fresh-9340`..`9359` | 5,120 |
| emblem r3: confirm | `fresh-9360`..`9379` | 5,120 |

- `fresh-9001`..`9004` are someone else's (not in either pool). `gen`, `gen-s1` and `fresh-6003`..`6040` are the
  team's A/B suites: training on them is fine (draft2 did), but judge lab output only on the 93xx holdouts.
- The four holdouts are in draft3's `holdout`; the emblem lab drops its own and the draft lab's.
- Of the generated maps ~7% have spawns joined only by dash or crystal (topo-split, topo-island, dash-lattice,
  atoll, archipelago, continent). They are trained on (their features are exact in JS), but the bot declines them
  (table draft): a crystal travel field costs up to ~8.6M fuel there.

## draft3 (draft lab)

Config: `lab.py DEFAULTS` as committed (pool, holdout, mix explore 0.5 / Thompson 0.35 / probe 0.15, half the games
with one team on a top-20 ladder composition, Stellar out of random teams, 4 vehicles, 40k-game batches,
searches at batches 1, 4, 9, `features` null = all 25).

```
py tools/draftlab/lab.py init --lab draft3 --source <main sha>          # ~10 min: features of ~46k maps
tmux new -s draft3 'py tools/draftlab/lab.py run --lab draft3 --hours 4.5 2>&1 | tee replays/draftlab/draft3-run.log'
```

- **Games:** ~800k (about 20 batches of 40k, a third per pick count). draft2's 590k fitted 373 parameters a pick
  count; draft3 has 445 and more varied maps. Smoke pace (8 slots, this bot): 432 games in ~48 s; draft2 played a
  40k batch in ~10 min on 94 slots.
- **Hours:** ~4.5 h of batches, then the final fit with search: draft2's took 71 min on 590k games with 19
  features; expect ~2 h. About 6.5 h in all. Fits run on one core beside the games.
- **Memory:** fits keep every game in memory; `lab.py` now runs node with a 64 GB heap (the box has 185 GB).

**Features** (README "Features"): the 19 of draft2 plus `dash_gain`, `narrow`, `spawn_ring`, `max_group`,
`camp_altar`, `sight_gap`. The bot measures only what the deployed model names, so a feature's fuel matters only if
it ships. `sight_gap` is the dear one (release, in game: median 1.1M, max 1.8M, on top of the 19's median 1.6M, max
6.0M, in a first draft turn of 10M). After the final fit:

1. Refit without `sight_gap` (a lab dir linking draft3's `games.jsonl`, `maps.jsonl`, `prior.json`, `ladder.jsonl`,
   with `"features"` = the other 24, as `draft2-noctr` was made): `node tools/draftlab/model.mjs fit --search --lab ...`.
2. Ship `sight_gap` only if it is worth its fuel: cv log loss better by more than ~0.0005 *and* the deployed team
   changes on more than ~2% of pool maps. Otherwise ship the 24-feature model. The same test can drop any other
   new feature whose weights are negligible (`report.md`).

## Emblem lab round 3

After draft3's deployment decision. Config (`replays/emblab/r3/config.json`, before `init`):

```
mkdir -p replays/emblab/r3 && python3 -c "import json; json.dump({'draft_lab': 'replays/draftlab/draft3',
  'holdout': [f'maps/fresh-{s}' for s in range(9340, 9380)], 'corr_model': None,
  'draft_mix': {'explore': 0.4, 'ladder': 0.2, 'model': 0.4}}, open('replays/emblab/r3/config.json', 'w'))"
py tools/emblab/lab.py init --lab r3 --source <main sha with draft3>
tmux new -s r3 'py tools/emblab/lab.py run --lab r3 --games 40000 --batches 20 2>&1 | tee replays/emblab/r3-run.log'
```

- **Games:** 800k (20 batches of 40k), as round 2; ~44M reached decisions, ~16M forced. `p_force` 0.35 at k0,
  0.5 to k11; 10% of team-games uniform at 0.2.
- **Hours:** round 2 played a batch in 12-15 min with the next one built alongside: ~5 h. Then `dfit.mjs --search`
  and `--dr` (~1-2 h), `candidate.py`, A/Bs: ~8 h in all. `decisions.jsonl` is ~1.5 GB a batch (~30 GB; 187 GB
  free on 2026-10-30; round 2's 63 GB can be compressed or deleted first).
- **Features:** the fits' map terms use all 25 (`FEATURES`); they reduce variance and test map x emblem effects.
  The deployed table stays per (pick count, type, ordinal): map-conditioned emblems would need map information in
  play, and the draft's 1024-byte plan is full (open question below).

## Judging and deploying

Every A/B: `py tools/ab.py bots/astraeus bots/variants/astraeus-<ref sha7> --no-test-draft --suites <20 holdout
dirs, comma-separated>` (astraeus's `test_draft` is off: both bots draft their own), 10,240 games, ~±1 point.
The reference is a frozen copy of current astraeus (`git archive <sha> bots/astraeus`, AGENTS.md).

- **draft3:** `model.mjs cpp --lab replays/draftlab/draft3` (or the 24-feature refit), then
  1. `native.mjs` on the pool and all holdouts (0 differences in key, features and team);
  2. `parity.py` on the ladder and ~200 sampled maps: 0 differences, `FEATFUEL`, and draft-analysis spills
     (`DRAFTTURN`) against the current header's;
  3. A/B on `fresh-9300`..`9319`: deploy if the lower end of the 95% interval is above 50% (draft2 shipped at
     51.9%, 50.9-52.9);
  4. confirm on `fresh-9320`..`9339`: not below 50%. Record both in EXPERIMENTS and CHANGES.
- **Emblem r3:** doubly robust selection (z 2, class 0, as CHANGES 233) into `emblem_table.h` (`candidate.py`); A/B
  on `fresh-9340`..`9359`, confirm on `9360`..`9379`, same bars. Per-decision gains did not add up when three
  quarters of decisions changed (round 2's pooled table, 50.0%): prefer the conservative selection.
- **Together:** the final bot against the frozen pre-lab astraeus on a fresh suite neither lab nor A/B used
  (generate `fresh-9400`..`9419`).

## Risks

- **Draft fuel.** Shipping `sight_gap` adds ~1.1M median, 1.8M max to the first draft turn; on the heaviest maps
  (fuel-stress, big topologies) the 19 already take up to 6M. Before its rewrite (2.85M median) the debug parity
  build ran out before picking on two such maps, and a missed pick makes the rest of the draft random; after it,
  the debug build's worst was 8.5M of 10M. Gate it by the refit test above and check `parity.py` spills before
  shipping.
- **Walk-split maps** (~7% of the generated pool, none on the ladder) are trained on but drafted by the table.
  If the ladder ever gets such maps, the model is not used there.
- **Feature drift.** The new features' values come from mapgen's `metrics`; if mapgen changes them, the bot and the
  lab disagree silently. `native.mjs` over the pool before every deployment catches it.
- **Self-play bias.** Self-play values measure how our bot plays a champion against itself (night1's ladder
  cross-check). Half the games give one team a ladder composition; still, judge only by A/B.
- **Moving partner.** The emblem lab's base policy and the draft lab's emblem table are the same table only if the
  emblem lab waits for draft3. Don't overlap them.
- **Vehicle patches.** Both labs patch the frozen bot's source (`trainer.h` hooks `draft_order()`; the emblem
  vehicle patches `shop.cc` and some prints). The smoke tests below built and played both on 6cf6c0f7; re-run one
  short batch whenever the source moves.
- **Winner's curse** on per-map teams and per-cell emblems: the held-out A/B is the only judge; don't select
  among several candidates on the same holdout (use the confirming suite).

## Checks and smoke tests done (2026-10-30, source 6cf6c0f7, at most 8 games at once)

- **Feature parity, JS against C++** (`native.mjs`, all 25 features, key and team): every map of the pool and the
  holdouts, 0 differences: the ladder, `fall-custom`, `gen`, `gen-s1`, `fresh-6003`..`6040` (20,651 maps with
  `fresh-9100`..`9139`) and `fresh-9100`..`9240` and `9300`..`9379` (56,320). Also with headers from a smoke model:
  all 25 features (939 maps) and a 23-feature subset (683 maps), the model's team equal.
- **In game** (`parity.py`, debug build): 133 maps (61 ladder, 71 of the heavy new families) with today's header,
  0 feature differences; 110 maps with the 23-feature header, 0 differences.
- **Bot unchanged in play:** `tools/fuel/bench.py` (16 games against hecate, 100M fuel), HEAD against this branch:
  16/16 replays identical, total fuel +262 of 4.0B.
- **draft lab** (`smoke-d3`: ladder + `fresh-9100`, 400-game batches, 8 slots): `init` 5 s for 326 maps; 8 batches,
  3,456 games, batch 0 explore then Thompson and probes, 0 errors, 0 draft mismatches, ~48 s a 432-game batch
  (~9 games/s on 8 slots); fits with `ctr` 1e9 throughout; final search 64 s; `report.md` clusters on the new
  features (a `dash_gain` +4 sd cluster).
- **emblem lab** (`smoke-e3`, `draft_lab` smoke-d3): `init` took the maps, prior and the model's team on all 326
  maps; one 400-game batch in 42 s, 0 errors, 0 draft mismatches, 26,643 decisions (~67 a game, as round 2);
  sources explore 316, model 329, ladder 155; `dfit.mjs` ran on it.

## Open questions

- Map-conditioned emblems: worth carving a few bytes of the draft plan for a map class? Only if round 3's map x
  emblem terms beat the static table by a clear cv margin.
- Should walk-split maps get a model draft (crystal travel within the first turn's fuel), or be left to the table?
- mapgen's dungeon designer throws on seed 9210 (`design.mjs:564`, reduce of an empty array): a generator bug
  for whoever owns mapgen.
