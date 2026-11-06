# Draft6 lab: current player, mixed opponents, ladder-mix pool (ocean, 2026-11-06)

Goal: a draft model that drafts better than draft5 in head-to-head play, not only in CV. Background:
[draftfeat.md](draftfeat.md) section 6: F92 fitted 53 (1e-4) better than draft5 but read 49.9% of 20,480 games; on the
12,576 games where the teams differed both models were worse than a coin, and each rated its own top pick ~3.5
points above the other's. Causes taken as working hypotheses: the optimizer's curse (argmax over ~800 noisy team
scores), stale lab data (draft5's player `variants/ocean-base`, 3b3a57a0, predates CHANGES 405-433) and
pseudoreplication (the opponent was always the same bot). Large files: `/home/ubuntu/tmp-offload/draft6/`.

## 1. Design

**Player.** `bots/variants/oc-base6` (READY: bots/ocean after CHANGES 433, = `oc-fuel8`), frozen. Its draft is
draft5's, so draft5 is the lab's `current_lab` (the "current" team source = what the base drafts).

**Opponents, mixed.** Each lab game picks the bot that plays the other side:
- `self`: oc-base6 itself (both sides are ocean, as in every earlier lab), 1/3 of games;
- `astraeus`: `bots/variants/astraeus-now-1106` (ocean reads ~53% against it), 1/3;
- `proteus`: `bots/variants/panel-proteus` (frozen copy of bots/proteus; ocean ~63%), 1/3.

Left out: `bots/fish`. It read 23.6% against astraeus 37e1eb6, so games against it are mostly decided by play,
not draft (little information per game), and its Fish-like draft would need its own non-table draft path
through the lab (the opponent's team known only after the game). Every opponent drafts from the lab's table
(vehicles of each bot), so its team source is the same as before: half ladder compositions, else Thompson or
random.

**Model.** draft5's form, plus opponent terms: for a team played by opponent bot o, an offset u_o (its strength;
penalty `opp`, light) and per-champion deviations d_o,c (how o plays champion c differently from ocean; penalty
`dev`, searched, a random effect shrunk to 0). Ocean's own values (b, w, syn, ctr) are what the bot deploys;
u and d are nuisance terms and never reach the C++. Self-play games carry no u or d. Fitted per pick count,
pooled as before. Checks:
- the usual 5-fold CV over maps;
- **leave-one-opponent-out CV**: fit without any game against opponent o, then predict o's games with d_o = 0
  and u_o (one number) fitted on half of o's maps and scored on the other half (and swapped). This asks
  whether ocean's champion values transfer to an opponent the fit never saw, the nearest offline stand-in for
  the ladder.

Forms fitted on the same games: the 25 features (draft5's), F92 (`derived.mjs`, draftfeat section 4), each with
counters on with the counter penalty re-searched (pinned at 1e9 since draft3).

**Map pool.** Ladder-mix, so one-altar maps are ~25% as on the ladder (draft5's pool: 4.9%):
- the 128 ladder maps (every batch) and `fresh-548000..548099` (100 ladder-mix suites, 25,600 maps). No
  `fall-custom` (edge cases, not ladder-like).
- Held out (never in the pool): `d6-e` = fresh-548200..548239 (dev A/B), `d6-c` = fresh-548300..548339 (confirm),
  `d6-v` = fresh-548400..548409 (`--mix varied`), and draftfeat's unused `df-c` (545100-545139).

**Sampling.** Unchanged from draft5: 2 exploring batches (60 random / 40 current), then explore 35, current 15,
Thompson 35, probe 15; half the games against a ladder composition (prior: top 15 teams, ladder-archive days
2026-11-02, 04, 05 refreshed from big-arm (11-05 now 1,143 games against 481 for draft5), half-life 24 h, as
draft5). Probes keep the previous game's opponent bot as well as its team and side, so pairs stay paired. No team
lock (as draft5). The change I considered and did not make: more probes (paired near-best teams). They help the
near-best comparisons directly, but the judging below is by head-to-head play anyway, and keeping the mix keeps
the lab comparable with draft5.

**Against the optimizer's curse.** The deployed team is not the argmax of the posterior mean alone:
- `lcb`: rank the teams by the posterior mean, keep the top 64, and score each by mean - kappa x sd, where sd is
  over D = 32 posterior draws (baked into `draft_model.h`) of the team's score less the 64 teams' mean score in
  the same draw (so the common-mode noise cancels). kappa = 0 is draft5's rule.
- kappa (and an optional penalty multiplier, i.e. more shrinkage) are chosen by a **split-half selection check**:
  fit on half of the games (by game id), choose teams from that half's posterior, value them under the other
  half's posterior mean against the base's own team (draft5's), both ways round. This is an honest estimate of
  the switch's worth against noise (not against misspecification the halves share), and its self-assessed
  counterpart shows the size of the curse.
- Final judgement only by head-to-head A/B (below); model-predicted gains are reported but not trusted.

**Judging.** Candidate `bots/variants/oc-draft6` = oc-base6 with the new `draft_model.h` (and `map_features`/
`model_team` changes if F92 or lcb). JS/C++ parity (`native.mjs`) 0 team mismatches on the 128 ladder maps and a
fresh suite; first draft turn fuel (`firstturn.py`) within the 10M first turn. A/B against oc-base6, own drafts
(`--no-test-draft`), fast runner:
1. 2x fuel (`--fuel 200000`): `d6-e` (20,480 games), SPRT 0.50/0.51 with its own `--sprt-seed` if more than one
   candidate, then the held-out confirm `d6-c` (20,480).
2. If it holds: real budget on `d6-c` or `df-c`, `d6-v` (`--mix varied`, 5,120), the panel (PANEL.md:
   5 x 5,120 on panel-check-514510), and a split of every run by one-altar against multi-altar maps.

## 2. Scale and wall time (planned before launch)

| Item | Games | Wall (estimate) |
|---|---|---|
| Lab, 10 batches of ~100k | 1,000,000 | draft5 played 1.09M in 75 min on a quiet box (~200 games/s); ocean is heavier and the box is shared with the SPSA tuner and a fuel port: ~100-130 games/s, **2-3 h**, plus fits (25-feature lab fits ~1-2 min; final search ~15 min) |
| Offline fits: 25 / F92 / counters, LOOO CV, split-half | 0 | ~1-1.5 h of 32 threads (F92 CV ~7 min a penalty set on a loaded box) |
| Parity, first-turn fuel | ~2,000 one-round games | ~10 min |
| A/B 2x: d6-e for up to 2 candidates, d6-c confirm | 40,960-61,440 | ~10-20 min each |
| Real budget, varied, panel (5 x 5,120 + 2 x 5,120 more for astraeus and proteus), ladder | ~62,000 | ~1 h |
| **Total** | **~1.12-1.15M** | **~6-8 h** |

Below the 1.5M games at which I would report first, so it launches without waiting.

## 3. Log

**Setup (13:00-13:25).**
- Suites generated (`mapgen.mjs suite --seed ... --out 'maps/suites/fresh/fresh-{seed}'`): pool 548000-548099, `d6-e`,
  `d6-c`, `d6-v` (merged symlink dirs under `maps/suites/merged/`). 21% of the judging maps have one altar.
- Prior: `ladder_prior.py --engine 3.0.0 --top 15 --half-life 24 --days 2026-11-02,2026-11-04,2026-11-05` on the
  archive with 11-04 and 11-05 re-synced from big-arm (`/home/ubuntu/tmp-offload/draft6/ladder-archive`): 910 games
  (draft5's: 497), team-games 255 / 334 / 961 for 3 / 4 / 5 picks.
- Tools (additive; labs without `opponents` behave as before):
  - `lab.py`: `opponents`, `opponent_bots`, `max_games`; per-opponent vehicles `dl-<lab>-<bot>-v<k>`; a game's
    manifest line names each side's vehicle; rows carry `botA`, `botB`.
  - `model.mjs`: layout groups `opp` and `dev` (`layoutOf(k, n)`); plan picks each game's bot by share, probes
    keep the paired game's bot; `oppcv` (leave-one-opponent-out), `selcheck` (split-half selection check),
    `lcbTeam`, and a config `deploy` {kappa, draws, top, seed} that `cpp`, `teams` and `native.mjs` follow
    (draws baked into `draft_model.h`).
  - `draft6-tools/lcb_patch.py`: the C++ side of `lcbTeam` in `map_features.cc` (`lcb_pick`); with draws 0 it
    compiles away.
- Smoke lab `replays/draftlab/draft6-smoke` (2,664 games, ladder + 2 suites): 0 errors, 0 draft mismatches with the
  three bots; `oppcv`, `selcheck` ran. LCB parity on it (kappa 1.5, which changed 155 of its 633 maps' teams):
  `native.mjs` on the 128 ladder maps 0 key, feature, team mismatches, 0 C++ failures; the patched bot builds.
- Coordinator: ocean is now `variants/oc-base7` (= oc-fuel9, identical at 100M to oc-base6, fewer out-of-fuel
  turns). The main lab had not played, so its player is oc-base7 (`source`), and the A/B base is oc-base7.
- Main lab launched 13:24 (`lab.py run --lab draft6 --hours 12`, `max_games` 1,000,000). The pool's 3- and 4-pick
  maps are fewer than a 100k batch wants, so batches are ~67k games (~15 batches). ~130 games/s while shared.

**Lab (13:24-15:02).** 1,000,000 games (999,946 usable: 3 / 4 / 5 picks 222,080 / 279,500 / 498,366), 16 batches,
0 errors, 3-7 draft mismatches a 67k batch; ~130-190 games/s while shared. Opponents 1/3 each; with the lab's
mixed (largely random) drafts ocean won 61.1% against astraeus-now-1106 and 67.3% against panel-proteus (batch 0),
self-play side A 49.9%. Replays deleted as read; `batches/` keeps plans and logs (3.9 GB).
- Final search (25 features): lam b 4, w 5120, syn 320, dev 1024, opp 1, ctr off; **CV 0.5698** (no map 0.5900,
  no pairs 0.5712, intercepts 0.5954). (draft5's 0.5988 is on other games; not comparable.)
- Counters (`draft6-ctr`, ctr searched from 320): ctr 1280, CV 0.56943 against 0.5698 without: -3.7 (1e-4), as
  draftfeat's -2.9. Not deployed (draft2's counters lost an A/B; the gain is tiny).
- F92 (`draft6-f92`, w and dev searched from draftfeat's w 320): w stays 320, dev 256; **CV 0.56582**, -39 (1e-4)
  against the 25 features (draftfeat: -53).
- Leave-one-opponent-out (`oppcv`, 25 features): an opponent the fit never saw costs little against the in-sample
  map-fold CV on the same games: astraeus 0.57481 against 0.57434 (+4.7), proteus 0.54839 against 0.54677 (+16).
  The deviation terms help in-sample (proteus -10, astraeus -2.7) and not held out (+1.3, +1.6 with them): ocean's
  champion values transfer across these bots; the per-bot part is small.
- Split-half selection check (`selcheck`, 25 features, 2,000 pool maps + 126 ladder maps; gain in win-% points
  against the ladder prior's top 40, of the chosen team over the base's draft5 team, valued under the other
  half's fit):

| w, syn penalty | kappa 0 | kappa 1 | kappa 2 | kappa 3 | self-assessed (kappa 0) | teams changed |
|---|---|---|---|---|---|---|
| x0.25, pool | 1.62 ±0.04 | 1.66 | 1.66 | 1.66 | 2.09 | 69% |
| x1 (CV's), pool | 1.67 ±0.04 | 1.69 | 1.69 | 1.69 | 2.03 | 68% |
| x4, pool | 1.95 ±0.04 | 1.95 | 1.95 | 1.95 | 2.16 | 68% |
| x1, ladder | 2.21 ±0.18 | 2.20 | 2.20 | 2.21 | 2.59 | 77% |
| x4, ladder | 2.56 ±0.19 | 2.58 | 2.58 | 2.57 | 2.79 | 75% |

  The LCB (kappa) changes almost nothing: among the top 64 teams the posterior sd hardly differs, so the curse is
  not about a few uncertain teams. More shrinkage (x4) narrows the self-assessed excess (0.36 to 0.21 on the pool)
  and raises the honest gain by ~0.3 points. Both halves share the lab's misspecification, so this is an upper
  bound on honesty, not a measurement of play.

**Candidates** (`draft6-tools/make_candidate.sh`; oc-base7 plus the header; parity `native.mjs` on the 128
ladder maps + fresh-548200: 384 maps, 0 key, feature and team mismatches, 0 C++ failures each):
- `variants/oc-draft6` (C1): draft6, 25 features, posterior mean (kappa 0: lcb_patch not applied). Its team differs
  from draft5's on 17,045 of the 25,265 pool maps (67%).
- `variants/oc-draft6-s4` (C2): w and syn penalties x4 (`replays/draftlab/draft6-s4`); differs from C1 on 3,977
  maps (16%).
- First draft turn (`firstturn.py --sample draft6/maps.jsonl --heavy 100 --random 300`, 674 maps, 1,348
  team-drafts): oc-draft6 median 4.00M, p99 6.84M, max 9.17M, 0 out of fuel; oc-base7 on the same maps median
  4.00M, p99 6.84M, max 9.17M (the two maps over 8.5M are the base's own cost: 100x100 `gen-huge` and
  `gen-ladder`). The header names the same 25 features as the base's, so the draft turn costs the same.

**A/B, both on own drafts, fast runner, against `variants/oc-base7`** (`draft6-tools/ab.sh`; split by
`draft6-tools/split.py`, CIs by map pair):

| Run | Games | Candidate | 95% CI | one-altar maps | multi-altar maps | OOF cand / base |
|---|---|---|---|---|---|---|
| C1, d6-e, 2x fuel | 20,480 | **51.8%** | 51.1-52.5 | 52.8% of 4,434 | 51.5% of 16,046 | 1,046 / 1,068 |
| C1, d6-c (held-out confirm), 2x | 20,480 | **51.9%** | 51.2-52.6 | 52.8% of 4,502 | 51.7% of 15,978 | 1,069 / 959 |
| C2, d6-e, 2x | 20,480 | 51.9% | 51.3-52.6 | 53.5% of 4,434 | 51.5% of 16,046 | |
| C2 against C1, d6-e, 2x | 20,480 | 49.9% | 49.3-50.6 | 50.2% | 49.9% | |
| C1, df-c, real fuel | 20,480 | **52.1%** | 51.4-52.8 | 53.0% of 4,596 | 51.8% of 15,884 | 122.3k / 117.3k |
| C1, d6-v (`--mix varied`), real fuel | 5,120 | 49.5% | 48.1-50.8 | 52.1% of 754 | 49.0% of 4,366 | 32.6k / 31.3k |

C2's extra shrinkage is level with C1 in play (49.9%), so the split-half's +0.3 did not show; C1 (the CV's
penalties) stays the candidate.

**C3, `variants/oc-draft6-f92`**: oc-base7 with draft6's F92 model (`replays/draftlab/draft6-f92`: w 320, dev 256,
b 64, syn 320) and draftfeat's F92 `map_features.{h,cc}` (from `oc-draftfeat2`; oc-base7's own map_features are
oc-retest-clean's, so they drop in). Parity on the 384 maps: 0 key and 0 team mismatches, 0 C++ failures; 66 maps
with sq_/pr_ values differing in the last bit (libm against V8 `log`, as in draftfeat). Differs from C1 on 12,104
pool maps (48%). First draft turn on the same 674 maps: median 4.06M (+55k), p99 6.90M, max 9.23M (base 9.17M),
0 of 1,348 out of fuel.

| Run | Games | C3 | 95% CI | one-altar maps | multi-altar maps | OOF C3 / other |
|---|---|---|---|---|---|---|
| against oc-base7, d6-e, 2x | 20,480 | **52.9%** | 52.3-53.6 | 54.2% of 4,434 | 52.6% of 16,046 | 1,018 / 1,019 |
| against C1, d6-e, 2x | 20,480 | 50.9% | 50.2-51.6 | 51.4% | 50.8% | |
| against oc-base7, d6-c (held out), 2x | 20,480 | **53.4%** | 52.7-54.1 | 52.6% of 4,502 | 53.6% of 15,978 | 1,042 / 946 |
| against C1, d6-c, 2x | 20,480 | 51.3% | 50.6-52.0 | 50.5% | 51.5% | |
| against oc-base7, df-c, real fuel | 20,480 | **52.9%** | 52.2-53.6 | 54.2% of 4,596 | 52.5% of 15,884 | 118.1k / 113.8k |
| against C1, df-c, real fuel | 20,480 | 51.1% | 50.4-51.8 | 51.0% | 51.1% | |
| against oc-base7, d6-v (`--mix varied`), real | 5,120 | 51.0% | 49.6-52.4 | 53.4% of 754 | 50.6% of 4,366 | 31.8k / 31.1k |

**Panel** (PANEL.md; real fuel; `panel-check-514510`, 5,120 games each; base rates re-measured for oc-base7; second
set `d6-p2` = fresh-548500..548509 for astraeus and proteus). Logs `replays/ab/pchk-{base7,c1,c3}-vs-*`,
`p2-*`.

| Member | oc-base7 | C1 | C1 - base | C3 | C3 - base | fail if below |
|---|---|---|---|---|---|---|
| astraeus-now-1106 | 54.9 | 56.6 | +1.7 | 57.6 | **+2.7** | 53.0 |
| panel-proteus | 63.6 | 65.5 | +1.9 | 66.3 | **+2.7** | 61.7 |
| panel-demeter | 66.6 | 68.1 | +1.5 | 69.0 | **+2.4** | 64.8 |
| panel-ocean-td | 82.3 | 82.8 | +0.5 | 83.5 | **+1.2** | 80.8 |
| baselines/v67 | 78.1 | 79.6 | +1.5 | 79.6 | **+1.5** | 76.5 |
| mean | 69.1 | | +1.42 | | **+2.10** | |
| d6-p2: astraeus-now-1106 | 55.1 | 57.1 | +2.0 | 56.5 | +1.4 | |
| d6-p2: panel-proteus | 64.2 | 65.7 | +1.5 | 66.3 | +2.1 | |

Both pass (no member down, mean up). Caveat: astraeus-now-1106 and panel-proteus were lab opponents; the three
members that were not (demeter, ocean-td, v67) gain too (+2.4, +1.2, +1.5 for C3).

**Ladder teams** (126 ladder maps of the published sizes): C3 differs from draft5 on 101. Champion shares
draft5 / C1 / C3: Cassi 92 / 98 / 96%, Prism 83 / 79 / 75%, Vesper 44 / 62 / 60%, Willow 32 / 48 / 47%,
Marcella 52 / 37 / 37%, Heart of Ruin 49 / 52 / 47%, Ryth 30 / 14 / 11%, Varg 17 / 7 / 14%, Tavi 2 / 7 / 13%,
Ren 14 / 20 / 17%, Vendetta 30 / 26 / 25%, Stellar 4 / 0 / 6%.

## 4. Conclusions

- **Draft6 drafts better in head-to-head play.** The F92 form (C3, `variants/oc-draft6-f92`) reads 52.9-53.4%
  against oc-base7 on three ladder-mix suites (61,440 games, two of them held out, one at the real budget), level
  to slightly up on varied stress maps (51.0%), and up on all five panel members (mean +2.1). The 25-feature form
  (C1) gains ~1.9 points; F92 adds ~1.1 more head-to-head (50.9 / 51.3 / 51.1% against C1). Gains are a bit larger
  on one-altar maps (+2.6 to +4.2 points against the base for C3) but present on both kinds.
- What changed against draftfeat (49.9% for F92 on draft5's data): the data. The same F92 form on games of the
  current player against mixed opponents on a ladder-mix pool drafts ~3 points better than on draft5's games.
  Stale data, not the feature set, was what kept the better fit from drafting better.
- The optimizer's curse is real but small here: split-half self-assessed gains exceed honest ones by ~0.35
  points (pool) at the CV's penalties. The LCB (kappa) changed nothing measurable offline, and extra shrinkage
  (x4), which looked +0.3 better offline, was level in play (C2 against C1, 49.9%). Deployed: the plain posterior
  mean at the CV's penalties (kappa 0; `lcb_patch.py` stays a tool).
- Mixed opponents: ocean's champion values transfer to a held-out opponent bot at a cost of 5-16 (1e-4) in log
  loss; per-bot champion deviations are small. Counters stay off (-3.7 (1e-4) in CV).
- Candidate to ship: `variants/oc-draft6-f92` (draft_model.h from `model.mjs cpp --lab replays/draftlab/draft6-f92`,
  map_features.{h,cc} from `oc-draftfeat2`). Not committed; bots/ocean untouched.

Games: lab 1,000,000 (+ 2,664 smoke); A/B 343,040 (C1 66,560, C2 40,960, C3 128,000, panels 3 x 35,840);
first-turn 3 x 1,348 draft-only team-drafts. Total ~1.35M.

**Merged** (2026-11-06, CHANGES 438):
- bots/ocean is oc-base8 plus C3's `draft/draft_model.h` and `draft/map_features.{h,cc}`, frozen as `variants/oc-base9`.
- Ladder parity gives 0 team mismatches, and the bot builds.
- At 100M it is byte-identical to oc-draft6-f92 on 68 of 68 bench games (def and wide).
- The lab's `batches/` bulk files are deleted (3.9G, already in games.jsonl); the `merged` and `ready` markers are kept for lab.py.

## Live gate: oc-base9 (draft6)

`variants/oc-base9` was submitted as **v81** at 16:05 UTC. It is the directory itself (source tree hash
1a7853603397; a scratch copy built with `cambc build --release`). It was live and pinned from 16:11. It played the
core set (priority 100) and then the ext set against Fish and Mite, pinned to refs r1: 104 groups, 16:11-19:08, with
512 paired games against each of v78 and v80. v81 stays active and pinned.

Paired flips (`ladder_scrims.py pair`, split by `gate-tools/pairsplit.py`: one-site means altar tiles within 3, at
most 2 tiles):

| | core: flips for v81 / v80 | pooled: v80 / v81 wins | pooled flips v81 / v80 | pooled flips v81 / v78 |
|---|---|---|---|---|
| Fish | 14 / 13 (+1) | 125 / 135 | 54 / 44 (+10) | 46 / 37 (+9) |
| Mite | 16 / 8 (+8) | 154 / 161 | 47 / 40 (+7) | 48 / 45 (+3) |
| one-site (188) | 9 / 8 (+1) | 105 / 114 | 34 / 25 (+9) | 38 / 30 (+8) |
| multi-site (324) | 21 / 13 (+8) | 174 / 182 | 67 / 59 (+8) | 56 / 52 (+4) |
| total | 30 / 21 (+9) | 279 / 296 | **101 / 84 (+17, z +1.25)** | **94 / 82 (+12, z +0.90)** |

By map class against v78: Fish one-site -1, multi +10; Mite one-site +9, multi -6. Against v80: Fish +5 / +5, Mite
+4 / +3. Live, v81 reads 57.8% (296 of 512) against v80's 54.5% and v78's 55.5%: positive, but not significant
alone.

### Draft forensics (v81 against v80; v78 and v80 draft identically)

`gate-tools/draftflips.py 80 81`. Fish's and Mite's drafts are the same in all 512 games (theirs are fixed per map).
Ours changed in 412 games and is identical in 100.

| | games | v80 / v81 wins | flips for v81 / v80 |
|---|---|---|---|
| draft changed, Fish | 206 | 97 / 108 | 46 / 35 |
| draft changed, Mite | 206 | 122 / 131 | 43 / 34 |
| draft identical, Fish | 50 | 28 / 27 | 8 / 9 |
| draft identical, Mite | 50 | 32 / 30 | 4 / 6 |

- **The gain is the draft.**
  - The changed drafts net +20 (89 / 69).
  - The 27 flips with an identical draft net -3. Those come from v81's other changes (fuel rounds 433/434/436),
    which alter play without changing the draft, and they are noise.
- **By pick count** (v80 / v81 wins; flips for v81 / v80):

  | | 3 picks | 4 picks | 5 picks |
  |---|---|---|---|
  | Fish | 26 / 21 (5 / 10) | **20 / 31 (14 / 3)** | 79 / 83 (35 / 31) |
  | Mite | 25 / 28 (8 / 5) | 33 / 32 (6 / 7) | 96 / 101 (33 / 28) |

  The 4-pick drafts against Fish are the clearest gain; the 3-pick drafts against Fish the one loss.
- **By opponent composition** (v80 / v81 wins):
  - Fish:
    - C&I+HoR+Marc+Vend, its 4-pick team: 16 / 24 (flips 9 / 1);
    - C&I+Marc+Vesp, 3 picks: 15 / 11 (0 / 4);
    - its two 5-pick teams: level (40 / 39 and 30 / 31).
  - Mite:
    - C&I+HoR+Tavi+Vend+Vesp (158 games): 96 / 100 (32 / 28);
    - the rest: within ±3.
- **Our picks**, the games with each champion (v80 → v81):
  - Vesper 112 → 156;
  - Willow 80 → 118;
  - Tavi 4 → 34;
  - Ren 36 → 44;
  - Marcella 134 → 92;
  - Ryth 76 → 28;
  - Prism 212 → 194;
  - Varg 44 → 36.

  This is the shift the lab predicted (Vesper, Willow and Tavi up; Marcella, Ryth and Prism down).
- **Win rates with each pick, v80 → v81:**
  - against Fish:
    - Willow 48 → 57%;
    - Vesper 46 → 51%;
    - Marcella 44 → 52%;
    - Ryth 42 → 50%;
    - Ren 47 → 61%;
    - Tavi 0/4 → 10/34 (29%);
    - Stellar 6/10 → 4/14.
  - against Mite:
    - Tavi 26/34 (76%);
    - Vesper 52 → 59%;
    - Willow 58 → 61%;
    - the rest about level.
  - So Tavi works against Mite and fails against Fish.
- **Net flips when a champion is added or removed** (games where it is, net for v81):
  - Willow added: 92 games, +11;
  - Ren added: 48, +5;
  - Ryth added: 16, +5;
  - Vendetta added: 20, +6;
  - Varg removed: 56, +9;
  - HoR removed: 80, +9;
  - Vendetta removed: 44, +5;
  - Ryth removed: 112, +3;
  - Vesper added: 100, -3;
  - Tavi added: 64, -1;
  - Prism removed: 52, -4.

  So Vesper's and Tavi's rise is about level live. Willow's rise, and dropping Varg and HoR, carry the gain.
- **Maps:**
  - most net flips over both opponents and sides: 04mountain_pass +4, 00interlock +3, 01starvation +3;
  - most lost: 00swirl -3, 02uncharted_lands -3, 03ambush_field -3.

  The rest are within ±2, with no cluster by map.

**Verdict:** v81's draft holds up live. It is +17 of 512 paired games against v80 and +12 against v78, positive
against both opponents and on both map classes, and the whole gain is in the games whose draft changed. It is not
significant alone (z +1.25), but it agrees with the local +3 points.
