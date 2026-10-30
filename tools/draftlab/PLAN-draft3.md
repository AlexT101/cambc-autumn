# Emblem lab round 3, then draft lab draft3: plan (2026-10-30)

Prepared, not launched. Both labs retrain astraeus's learned tables for the bot as it is now and for the new map
families. Read with [README.md](README.md) and [../emblab/README.md](../emblab/README.md).

## Why now

- **The bot moved.** The macro overhaul (CHANGES 235-241) beats ef8f0b8, the bot both tables were trained on, ~60%
  of the time. Champion and emblem values are values *of how we play them* (night1's ladder cross-check: self-play
  champion values barely correlate with the ladder's), so both tables are stale.
- **The maps moved.** mapgen's new families (2316775d: topology, scenarios, quirks) are in every suite, and the
  draft2 and round-2 pools are deleted.
- **The model could not see the new axes.** draft2's 19 features have no dash-shortcut-between-spawns, corridor,
  spawn-surround, group-size, camp-by-altar or sight-against-walk term. draft3 can use six more (README "Features").

## Decisions

- **Order: emblem round 3 first, then draft3**, as the last cycle (CHANGES 232/233, then 234). Emblem values are
  fitted per decision and per champion, and that lab already randomises drafts; draft values depend on what each
  champion buys, so the draft is trained last, under the final emblem policy. Never run the two at once: each takes
  all 94 slots, and each needs the other's policy fixed.
- **Fuel:** both labs play at the real 100k budget (the runners' default; no `--fuel`). Out-of-fuel turns are rare
  (~4-5 a game in today's A/Bs) and the tables should be learned for the bot as deployed.
- **No counter picks.** draft2's counters lost 1.6 points (CHANGES 234; 3938c0f removed them). draft3 starts with
  `lam.ctr` 1e9 (`initial_lam`); a ctr penalty of 1e8 or more is never searched, so Thompson, probes and the final
  model are counter-free by construction and `model.mjs cpp` takes the model as it is. Pair **synergy** stays.
- **Pick counts: draft2's partial pooling, kept.** `fitAll` fits a model pooled over 3, 4 and 5 picks, then one model
  per pick count penalised toward it (the per-count terms are deviations from the pooled ones, at the searched
  penalty). Planning (`pick_shares`, about a third of games each, Thompson and probes per pick count) and the
  shipped header stay separate per pick count; nothing is extrapolated across pick counts.
- **Ladder prior: the top 10 other teams.** `init --top 10` (the default now) ranks teams by latest rating since
  `patch_since` (2026-10-26) with ours (`fetch_replays.MY_TEAM`, "newer team", #5) left out, and takes the 10 best:
  their compositions are `prior.json`, the opponents half the games face. Run `init` after `replays/ladder` has
  been refreshed (every ranked group since 2026-10-26 of the current top 11). Our drafts never enter `prior.json`;
  `ladder.jsonl` keeps our games against those teams only for `model.mjs ladder`'s team-effects cross-check.
- **Split maps** (spawns joined only by dash or crystal; ~6% of generated maps, none on the ladder): the user's
  decision is that the model drafts them. That is its own bot commit, on top of the rest, because it does not yet
  pass the fuel bar: the features there need a crystal travel field (one, mirrored for team B, exact), and on 34 of
  the 4,023 split maps of the pool and holdouts the first draft turn still ran out inside the model draft (dash and
  wall lattices, topo-split, topo-island): a random draft. Merge it once the crystal field is cheaper, or accept
  that. Either way the labs play and fit split maps like any other (their features are exact in JS), and the emblem
  lab's `model` teams there are the model's team (lab vehicles draft from their table, so this changes nothing in
  the lab whether or not the source drafts split maps by the model).
- **Features ship on performance and fuel** (below): a feature goes into the shipped header only if an A/B says it
  helps and the first draft turn never runs out of fuel with it.
- **Prior data: start from scratch** (`prior_games` null, `explore_batches` 1; emblem `corr_model` null). Reasons:
  - Prior games only steer batch 0's choices: at `prior_weight` 0 afterwards they leave the fit, and team (or arm)
    choice depends only on the map (or the logged state), so the fits are unbiased either way. The gain is
    efficiency in one batch of ~20.
  - That steering would be stale: draft2 learned 26d273e (before the macro overhaul, on the old maps), and its
    maps cannot give the six new features (deleted suites: z 0 for every new term). Round 1's emblem corrections
    are from 1c0d627, two bots ago.
  - draft2's ~55k old maps would join `maps.jsonl` as `prior:` rows and set the standardisation (mean, sd) of the
    old features for the whole lab.
  - Batch 0 as uniform exploration (40k games) is good data in itself: it covers champions draft2 rarely played
    and the new families evenly; from batch 1 Thompson uses the lab's own fit (night1's map terms paid at 9k games).
  - Kept: hyperparameters (draft2's searched penalties as `initial_lam`, re-searched in the run) and the emblem
    lab's base policy, the current astraeus, whose table already holds round 2's result.

## Maps

In the primary checkout's `maps/` (git-ignored; rebuild with `node tools/mapgen/mapgen.mjs suite --seed A-B --out
maps/fresh-{seed}`). The pool has only suites no A/B has used: `gen`, `gen-s1` and `fresh-6003`..`6040` were, so
they are out. Never use `fresh-9001`..`9004` or `9501`..`9520` (others' A/B suites).

| Use | Suites | Maps |
|---|---|---|
| Pool (both labs; `lab.py POOL`) | ladder (`maps/*.map26a`), `fall-custom`, `fresh-9100`..`9280` | 171 + 46,336 |
| emblem r3: judge | `fresh-9340`..`9359` | 5,120 (10,240 games) |
| emblem r3: confirm | `fresh-9360`..`9379` | 5,120 |
| draft3: judge | `fresh-9300`..`9319` | 5,120 |
| draft3: feature A/B | `fresh-9320`..`9339` | 5,120 |
| draft3: confirm; both together | `fresh-9400`..`9419`; `fresh-9420`..`9439` (generate when needed) | 5,120 each |

All of 9300-9379 is in draft3's `holdout` (lab.py DEFAULTS) and the emblem lab's; `parity.py` refuses them.

## Emblem lab round 3 (first)

- **Source:** current main with this branch merged (draft2-noctr's header; split maps model-drafted only if their
  commit is merged). Check `params::test_draft` is off and nothing else runs (`tmux ls`, `ps`).
- **Config** (before `init`; `draft_lab` "shipped" is the lab named in the source's `draft_model.h`, today
  `replays/draftlab/draft2-noctr`, checked against its `model.json`):

```
mkdir -p replays/emblab/r3 && python3 -c "import json; json.dump({'pool': ['maps/*.map26a', 'maps/fall-custom',
  'maps/fresh-91[0-9][0-9]', 'maps/fresh-92[0-7][0-9]', 'maps/fresh-9280'],
  'holdout': [f'maps/fresh-{s}' for s in range(9300, 9380)], 'draft_lab': 'shipped', 'top': 10,
  'corr_model': None, 'draft_mix': {'explore': 0.4, 'ladder': 0.3, 'model': 0.3}}, open('replays/emblab/r3/config.json', 'w'))"
py tools/emblab/lab.py init --lab r3 --source <main sha>      # after the ladder refresh; ~10 min of features
tmux new -s r3 'py tools/emblab/lab.py run --lab r3 --games 40000 --batches 20 2>&1 | tee replays/emblab/r3-run.log'
```

- **Games:** 800k (20 batches of 40k), as round 2: ~44M reached decisions, ~16M forced. `p_force` 0.35 at k0, 0.5
  to k11; 10% of team-games uniform at 0.2. Drafts: 40% random (Stellar out), 30% top-10 ladder compositions, 30%
  the shipped model's team on that map (round 2's shares, the model's teams in night1's place).
- **Hours:** round 2 played a batch in 12-15 min with the next built alongside: ~5 h. Then `dfit.mjs --search` and
  `--dr` (~1-2 h), `candidate.py`, two A/Bs: ~8 h in all. `decisions.jsonl` grows ~1.5 GB a batch (~30 GB; 187 GB
  free on 2026-10-30; round 2's 63 GB can be compressed first).
- **Features:** the fits' map terms use all 25 (`FEATURES`); they reduce variance and test map x emblem effects.
  The shipped table stays per (pick count, type, ordinal); map-conditioned emblems are an open question below.
- **Ship:** doubly robust selection (z 2, class 0, as CHANGES 233) into `emblem_table.h` (`candidate.py`); A/B on
  9340-9359, confirm on 9360-9379. Per-decision gains did not add up when three quarters of decisions changed
  (round 2's pooled table, 50.0%): prefer the conservative selection.

## draft3 (second)

- **Source:** the bot that ships emblem round 3 (or current main if it ships nothing). `lab.py DEFAULTS` as
  committed: pool `POOL`, holdout 9300-9379, mix explore 0.5 / Thompson 0.35 / probe 0.15, half the games with one
  team on a top-10 ladder composition, Stellar out of random teams, 4 vehicles, 40k batches, searches at batches 1, 4
  and 9, `features` all 25 (written into `config.json` at `init`).

```
py tools/draftlab/lab.py init --lab draft3 --source <sha>        # after the ladder refresh; ~10 min of features
tmux new -s draft3 'py tools/draftlab/lab.py run --lab draft3 --hours 4.5 2>&1 | tee replays/draftlab/draft3-run.log'
```

- **Games and hours:** a 40k batch plays in ~10 min (draft2 on 94 slots; the smoke tests ran ~9 games/s on 8), but
  the searches after batches 4 and 9 block the next batch (fits run on one core), so 4.5 h gives ~650-750k games.
  The final fit with search then takes ~2 h (draft2's took 71 min on 590k games with 19 features; 445 parameters a
  pick count now against 373). About 6.5 h in all; fits keep every game in memory, so node runs with a 64 GB heap.
- **Vehicles** draft from the trainer table, but their draft bot still runs `measure()` (with the source's header),
  so lab games pay the same first-turn fuel as the source bot.

## Features: what ships

The model is fitted on all 25. `sight_gap` and `narrow` (and any new feature) ship only if **both** hold:

1. **Performance, by A/B** (not cv loss): refit draft3 without them and A/B the two headers head to head on
   9320-9339 (own drafts). The cheaper header ships unless the full one wins clearly (lower end of the 95% interval
   above 50%). If the full one wins, a second A/B can split them (without `sight_gap` only) on 9400-9419.
2. **Fuel:** the first draft turn never runs out before the pick. Checked at ship time, only for a candidate header
   that names `sight_gap` or `narrow`, and not before the labs launch: `py tools/draftlab/firstturn.py --sample
   replays/draftlab/draft3/maps.jsonl --bot <candidate>` (release, draft only) on the heaviest few hundred maps by
   area, camps, bush tiles and walkable tiles plus ~2,500 random pool maps. Bar: no team-draft without its `FT`
   line, and start-up plus the model draft (map read, engine fields, `compute`, team ranking) at most **8.5M of the
   10M** (1.5M of headroom; the analysis' 500k reserve comes after it); report how often `analyse()` spills to
   later draft turns (2.0% of team-drafts with today's header).

With all 25 features some of the heaviest maps ran the first turn out (`sight_gap` up to 2.2M, `narrow` 0.73M on
top of the 19's 6.9M), so a header naming both is unlikely to pass without making them cheaper.

**Refit recipe** (as `draft2-noctr`): a new lab directory with links to draft3's `games.jsonl`, `maps.jsonl`,
`prior.json` and `ladder.jsonl`, a **copy of draft3's `config.json`** with `features` set to the subset (a fresh
config would fall back to model.mjs's built-in penalties, `ctr` 20, and refit counters), then
`node tools/draftlab/model.mjs fit --search --lab <dir>` and `model.mjs cpp --lab <dir> --out <candidate>/src/draft/draft_model.h`.

## Judging and deploying

Every A/B: `py tools/ab.py bots/astraeus bots/variants/astraeus-<ref sha7> --no-test-draft --suites <20 holdout
dirs, comma-separated>` (astraeus's `test_draft` is off: both bots draft their own), 10,240 games, ~±1 point. The
reference is a frozen copy (`git archive <sha> bots/astraeus`, AGENTS.md).

1. **Emblem r3:** candidate table against the source on 9340-9359; ship if the 95% interval's lower end is above
   50%; confirm on 9360-9379 (not below 50%).
2. **draft3:** `model.mjs cpp`, then `native.mjs` on the pool and holdouts (0 differences in key, features, team),
   `parity.py` on ~200 maps sampled from the pool only (it refuses holdouts): 0 differences, `FEATFUEL`, `DRAFTTURN`
   spills against the current header's. A/B against the source on 9300-9319 (draft2 shipped at 51.9%, 50.9-52.9);
   the feature A/B above on 9320-9339; confirm the chosen header on 9400-9419.
3. **Together:** the final bot against the pre-lab astraeus on 9420-9439. Record everything in EXPERIMENTS and
   CHANGES.

## Draft memory

Not full: per [DRAFT-COMPUTE.md](../../research/hyperion/DRAFT-COMPUTE.md), 747-984 of the 1024 bytes are free on
the bench maps and the tightest known map (gen-dense-camps) leaves 82; everything in it is an optional fuel cache,
and the v8 index only fills leftover room. A few bits of map information for the emblem chooser (a map class, or
two or three quantised features) would fit ahead of the index. Champions could also measure features themselves in
play (round 1 has a double budget).

## Risks

- **Draft fuel.** A missed first pick makes the whole draft random. The analysis' cost estimates ran short near
  the end of the first turn (fixed by its 500k reserve; later draft turns keep 40k of 100k and are unmeasured).
  `firstturn.py` before any header naming `sight_gap` or `narrow` ships; on a new map family, re-measure.
- **Split maps** are drafted by the model only with their own commit, which still runs the first turn out on 34
  of 4,023 such maps; the ladder has none, so the A/Bs see them only in generated suites.
- **Feature drift.** The features come from mapgen's `metrics`; if mapgen changes them, the bot and the labs
  disagree silently. `native.mjs` over the pool before every deployment catches it.
- **Self-play bias.** Self-play values measure how our bot plays a champion against itself. Half the games give one
  team a top-10 composition; still, judge only by A/B.
- **Vehicle patches.** Both labs patch the frozen source (`trainer.h` hooks `draft_order()`; the emblem vehicle
  patches `shop.cc` and some prints). The smoke tests built and played both on 6cf6c0f7; re-run one short batch
  whenever the source moves.
- **Winner's curse** on per-map teams and per-cell emblems: held-out A/Bs are the only judge; never pick among
  candidates on the suite that then confirms.

## Checks done (2026-10-30, at most 8 games at once)

- **First draft turn** (release, draft only, every pool and holdout map; the one all-maps pass, before the
  ship-time check above replaced it): with today's header and split maps model-drafted, 144 of 133,830 team-drafts
  ran the turn out before the pick: 68 on 34 split maps (inside the model draft), 76 on 40 other maps (inside
  `analyse()`, whose estimates ran short once the cheaper features left it more fuel; main's bot finished 73 of
  those 74 maps). With the 500k first-turn reserve and split maps declined (the commits' base), 1,624 of the 1,625
  heaviest and failing maps finish (the one left, fall-custom `giant`, fails on main too); before the analysis max
  6.6M, after it max 9.7M. Non-split maps: start-up plus model draft max 6.9M over all 62,964.
- **Feature parity, JS against C++** (`native.mjs`, all 25 features, key and team): all 66,987 pool and holdout
  maps, 0 differences (split maps included, with the mirrored crystal field). Also with headers from a smoke model:
  all 25 features (939 maps) and a 23-feature subset (683 maps), the model's team equal.
- **In game** (`parity.py`, debug build): 133 maps (61 ladder, 71 of the heavy new families) with today's header,
  0 feature differences; 110 maps with the 23-feature header, 0 differences.
- **Bot unchanged where it should be:** `tools/fuel/bench.py --set wide` (26 maps, 52 games, 100M fuel), main
  (52c07ae) against the base commit: 52/52 replays identical (none of the 26 maps is split). The split-maps commit
  against the base on two split archipelagos (fresh-9101): 0/4 identical, as meant (the model drafts there).
- **draft lab smoke** (`smoke-d3`: ladder + `fresh-9100`, 400-game batches, 8 slots): `init` 5 s for 326 maps;
  8 batches, 3,456 games, batch 0 explore then Thompson and probes, 0 errors, 0 draft mismatches, ~48 s a 432-game
  batch; fits with `ctr` 1e9 throughout; final search 64 s; `report.md` clusters on the new features.
- **emblem lab smoke** (`smoke-e3`): one 400-game batch in 42 s, 0 errors, 0 draft mismatches, 26,643 decisions
  (~67 a game, as round 2); sources explore 316, model 329, ladder 155; `dfit.mjs` ran on it. After the pool,
  `top` and `shipped` changes, both `init`s again on the refreshed ladder: the top 10 other teams (ours out),
  6,046 / 8,121 / 21,250 team-games at 3 / 4 / 5 picks; `shipped` found draft2-noctr and its team on all 326 maps.

## Open questions

- Split maps: merge their commit as it is (34 of 4,023 split maps then draft at random), or first make the crystal
  field cheaper (its Dial loop is 2.5-3.8M on lattices; a bit-parallel layer version was no cheaper in WASM)?
- fall-custom `giant` runs the first turn out on main too: not investigated.
- Later draft turns keep a 40k reserve of 100k; nobody has measured whether their analysis steps overrun it.
- Map-conditioned emblems: worth a few bytes of the draft plan (or champion-side features), if round 3's map x
  emblem terms beat the static table by a clear margin?
