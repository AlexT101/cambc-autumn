# A current-Mite body, and tuning against it (2026-11-12)

The user (verbatim, 2026-11-12): "now battlecats is becoming somewhat competent at fish level. however mite is the
biggest threat. i wonder how to optimise vs mite. maybe something like use our bot but tune its constants to match
with what mite played? ..." This programme covers that part: a body fitted to current Mite (live pin r7), its
calibration against our live results, and a Mite-only constant tune of our best bot. mitere
(`../mitere/`) reverse-engineered Mite's rules; forkcomp (`../forkcomp/`) built the live-position fork used as
a second fidelity check.

## Summary

- **New body `variants/mf-c1`, and `mf-c2` with Mite's retreat rule:** c520-ps playing Mite r7's draft, with 0.2
  noise on the 19 lab knobs. Seed and salt come from the runner, as for the rt-* bodies. It calibrates far better
  than Mt3q:
  - Full games: we beat c1 / c2 by 64.3 / 68.5% against 66.2% live (v116); Mt3q gives 77.4%.
  - From live positions (livefork): body − live is −0.8 / +0.2 points (±2.6), Mt3q +4.7.
  - Behaviour: c1 matches Mite's tribute volume, bag sizes, big bags, kills and deaths; Mt3q misses most of them.
- **fgate takes it:** `--mite-body mf-c2` (any ready run-time body dir under `bots/variants/`).
- **Mite's rules on top of it make the body easier, not closer.**
  - Locks, the opening pack and Vesper's holds/build each move their own statistic toward live. Cohesion is
    matched exactly at c7.
  - But they cost the body early gold where Mite earns more: r100 gold 347-399 against live 469.
  - Our win rate rises to 71-74% (live 66).
  - Mite's opening is efficient in a way our farm valuation under a pack discount is not.
- **Tune:** see "Mite-only tune" below.

## Bodies (mkbody.py layers)

`py mkbody.py NAME [--set K=V] [--mul K=F] [--py RULE.py] [--noise SD] [--static K] [--draft table|model]`, built on
`variants/c520-ps`:
1. Draft:
   - Mite r7's exact picks per (ladder map, side) (`spar_draft.h`, via spar-tools' hashes). Mite's draft is
     deterministic per cell: 65 of 65 repeated cells agree.
   - Elsewhere, an r7 pick logit (`fitgen_r7.py`; held-out champion overlap 0.75 / 0.81 / 0.92 at 3 / 4 / 5
     picks), sampled with the draft salt.
2. Run time: `experiment_config(0/1)` is the member seed and the draft salt, as runtime_body.py does. `--static K`
   bakes them in for tune.py.
3. Constants: params.h literals.
4. Noise: the 19 lab knobs (localq mktune.sh) are tunified and redrawn every 100 rounds as value × exp(0.2 N(0,1)),
   seeded by member, team and map (`dvp_noise.h`, as the dvn bodies).
5. Rules: `rule_*.py`.

| body | adds |
|---|---|
| mf-c0 | draft only, no noise |
| mf-c1 | + noise |
| mf-c2 | + retreat (mitere 1), as constants: hurt line 0.40, brake_bag 11, hurt_retreat_ratio 0.01 (hurt or carrying: never stay against any pack), home_retreat_ratio 1000 (numbers never send a healthy body home) |
| mf-c3 | + locks (`rule_locks.py`): none before r350, then half the bodies |
| mf-c4 | + opening pack (`rule_pack.py`): before r200, a group no ally is nearer to is worth 0.5x |
| mf-c5 | + Vesper (`rule_vesper.py`): she takes single-holder captures (value x4) and builds Greed-Str, Bruiser-Health, Greed-Health |
| mf-c6 / c7 | c5 with the pack led by Vesper (`rule_packv.py`, 0.5x / 0.2x unless Vesper is nearer) |

Not built: Mite's targeting (lowest absolute health for basic attacks, nearest for spells). It sits inside the
strike search. Mite's priority writer is not built either: our packed priority carries comms and the turn order.

## Calibration

Our bots: v115 = oc-dfuel-506, v116 = charybdis-p3, v117 = c520-ps. Live is their r7 scrims (`calread.py`); local
is the 128 ladder maps, both sides, 8 noise members (2,048 games a bot).

Results against Mite r7, live vs bodies (our win %):

| our bot | live | Mt3q | c1 | c2 | c3 | c4 | c5 | c6 | c7 |
|---|---|---|---|---|---|---|---|---|---|
| v115 | 61.5 (49.7-73.4) of 65 | 74.0 | 57.4 | 62.7 | 59.6 | 61.5 | 65.3 | 66.7 | 70.2 |
| v116 | 66.2 (60.4-71.9) of 260 | 77.4 | 64.3 | 68.5 | 68.0 | 71.0 | 73.9 | 71.7 | 74.3 |
| v117 | 67.2 (59.0-75.4) of 125 | 78.9 | 66.7 | 69.8 | 69.3 | 72.5 | 74.5 | 74.9 | 74.8 |

Body columns are of 2,048 games, ±2.0.

- **Per map** (`permap.py`, about 3.5 live games a map): r = 0.27 for Mt3q, 0.19-0.21 for the mf bodies. All
  are significant and none is better: live noise dominates.
- **Small-map loss:** the mf bodies reproduce the 00stampede loss.
  - Live: lost 2 of 2.
  - Our win rate there: Mt3q 62.5%, c1 25%, c2 21%.
  - Clear misses the other way: 03homonoliths (live 75% of 8; c2 8%), 04comb (100% of 4; c2 19%), 04sunburst
    (87.5% of 8; c2 38%). The body is much stronger than Mite there; Mt3q is not. This is probably map-specific
    Mite play that a constant fit cannot reach.
- **Per cell** (one live game a cell): no body predicts the outcome better than a constant (Brier).
- **livefork** (forkcomp's runner; v116 registered in the harness with `versions.py`'s batch-mode lookup; 260 of
  260 games reproduce exactly). Forks at r100/300/600, two body members a fork, 696 forks.

  | | Mt3q | c1 | c2 | c4 | c5 |
  |---|---|---|---|---|---|
  | body − live, all forks (points, ±1 SE) | +4.7 ±2.6 | −0.8 ±2.6 | +0.2 ±2.6 | +1.4 ±2.5 | +1.4 ±2.5 |
  | r100 forks | +7.1 | −0.2 | +0.2 | +3.1 | +2.1 |
  | outcome agreement with live (ceiling: two seeds 75-80%) | 68.8% | 71.3% | 71.0% | 71.4% | 72.6% |

## What Mite does differently from our bot (live r7, the same 260 v116 games)

Mite side vs ours (`mstats.py`; `~/tmp-offload/mitefit/fidelity-v116-rules.md` has every statistic and body):

| | Mite | us |
|---|---|---|
| gold earned r100 / r300 / r600 | 469 / 1685 / 2915 | 407 / 1657 / 3031 |
| capture gold / gems to r300 | 1553 / 275 | 1470 / 338 |
| Vesper's share of capture gold to r100 | 0.62 | 0.44 |
| mates within 5 at r20 / r60 | 2.84 / 1.93 | 2.27 / 1.46 |
| bodies within 4 of a clear before r200 | 2.91 | 2.37 |
| gems tributed a game | 676 | 832 |
| Prism drafted / its largest bag (median, when drafted) | 22% / 207 | 81% / 444 |
| deaths / champion kills a game | 9.8 / 6.7 | 7.0 / 9.4 |
| locks / crystal hops / wards a game | 1.5 / 3.4 / 164 | 4.2 / 0.4 / 109 |

- Mite is gold-first: more gold early, fewer gems. It packs in the opening and its Vesper takes the gold.
- It dies more than we do (9.8 vs 7.0) yet converts more of its kills per body present (1.49 vs 1.21 of our
  bodies within 4 at our kills).
- It banks less: fewer gems tributed, and a smaller Prism bag.
- Compared with what our code does when made to pack, Mite's opening gives the same cohesion with more gold, not
  less. That efficiency (which groups, what route, every body hitting at once) is the gap no constant closes.

## Mite-only tune (tune1.sh)

SPSA setup:
- Knobs: c520-ps's 19 lab knobs.
- Opponents: only six static mf-c1 members (`mf-s951..956`).
- Maps: 40 fresh ladder-v2 suites (mapgen seeds 7930000-7930039).
- 600 iterations of 16 maps × 6 opponents × 8 candidates, scored win .75 / gems .25.
- The candidate is the second-half mean, ported into `variants/mft1-c520`.
- The labs filler was paused for the SPSA.

The gates are in `gate1.sh`: fgate fixed reads from pool batch 30, against the Fish body with mf-c2, mf-c1 and
Mt3q, plus a head-to-head against c520-ps on a fresh suite (seed 7931000).

Results against c520-ps (mft1-c520; fgate v2 pool from batch 30, 2 batches; Flp4 with each Mite body, unmetered;
100k fuel):

| read | win% (95% CI) | maps | games |
|---|---|---|---|
| fresh, with mf-c2 | 50.02% (49.33-50.70) | 5,120 | 40,960 |
| fresh Mite, mf-c2 | 50.09% (49.01-51.16) | 5,120 | 20,480 |
| fresh Mite, mf-c1 (the training body) | 49.48% (48.38-50.58) | 5,120 | 20,480 |
| fresh Mite, Mt3q | 49.45% (48.54-50.37) | 5,120 | 20,480 |
| fresh Fish, Flp4 | 49.94% (49.10-50.79) | 5,120 | 20,480 |
| ladder side read, with mf-c2 | 50.68% (47.57-53.80) | 256 | 2,048 |
| h2h, fresh ladder-v2 suite 7931000 | 51.2% (46.8-55.5) | 256 | 512 |

- Null everywhere, the training body included.
- The SPSA never learned: training win against the static members was flat at 71% in every 100 iterations.
- No Mite-specific constant set beats our constants, in line with forkcomp's finding from past SPSA logs that
  splitting constants by opponent buys at most 0.07 points.

tune2 was the same SPSA against mf-c2 members on 40 fresh ladder-v3 suites (`tune2.sh`). It stopped at iteration 21
and was not resumed, because tune1 never learned and the best bot had moved on (lab-emb6-c520-ps).

## Vesper carry (rule_vcarry.py), mitere's rule 1

The Prism carry macro, generalised to Vesper for groups with gold.

Paired results on the 128 ladder maps against mf-c2, 8 members, 2,048 games each:

| bot | our win% | paired difference | Vesper share by r100 | Prism max bag |
|---|---|---|---|---|
| c520-ps | 69.8 | | 0.41 | 441 |
| vc-c520, Vesper takes every gold group | 67.3 | −2.4 ±2.2 | 0.57 | 334 |
| vc2-c520, Prism keeps every gem group | 70.3 | +0.5 ±1.9 | 0.43 | 456 |

- vc-c520 copies Mite's gold split. But in games with both Vesper and Prism the Prism loses about half its gems,
  and those games lose about 10 points (mitere's paired read).
- vc2-c520 barely moves anything: pure-gold groups are rare.
- As a body layer, mf-c8 (mf-c2 + vcarry) calibrates the same as mf-c2: our win% 63.2 / 68.5 / 70.6 for
  v115 / v116 / v117. It does not close the body's r100 gold gap either.
- Not pursued.

## Fight fidelity, and the fight body mf-f9

**Statistics.** `fstats.py` gives per-game fight statistics:
- kills and deaths by Vesper and Prism, and deaths carrying 11+ gems;
- engagements: champion damage clustered with a gap of 6 rounds; kills per engagement, overall and for the side
  that hit first;
- retreat after a hit, binned by health and bag.

`vstats.py` and `vacts.py` cover Mite's Vesper: gold, Strength, items, attacks and damage. `fcmp.py` prints the
table, live against bodies, on the same cells.

**What mf-c2 misses** (v116 live against 2 noise members, 512 games):

| | live | mf-c2 | mf-f9 |
|---|---|---|---|
| Mite kills a game | 6.73 | 5.48 | 6.24 |
| Mite kills / engagement | 0.319 | 0.251 | 0.275 |
| Mite kills / engagement it started | 0.464 | 0.351 | 0.394 |
| share of engagements Mite started | 0.345 | 0.429 | 0.409 |
| Mite Vesper kills (games with her) | 2.90 | 2.14 | 2.35 |
| Mite Prism deaths (games with Prism) | 2.21 | 1.67 | 1.88 |
| our deaths | 7.03 | 5.80 | 6.58 |
| our losses / engagement we started | 0.243 | 0.175 | 0.193 |
| Mite Vesper's gold by r150 | 484 | 376 | 366 |
| Mite Vesper's champion damage | 8,192 | 5,938 | 5,983 |

- Real Mite starts fewer fights, and the ones it starts kill more. It punishes the fights we start.
- Its Vesper is fed and fights more: 26% more attacks on champions and 21% more damage an attack.
- Both sides deal more champion damage live than in local games.

**Layers and constants tried** (2 members unless noted):
- **Targeting rule** (`rule_target.py`, basic attacks on the lowest-health foe in reach), as mf-c10: changes
  nothing (kills / engagement 0.256).
- **Vesper carry** feeds Vesper (her r150 gold 404-410) but removes the fight gains: mf-f7 0.249, mf-f10 0.254.
- **Kill-seeking constants** (`chip_value`, how much chip damage is worth against a kill; `life_value`, the
  worth of our own life): a sweep of 9 bodies on one member, then the best two on a second.
- **mf-f9** = mf-c2 + chip_value 0.03 + life_value x0.35 is the best fit. Mite values kills over chip damage and
  its own lives cheaply.

**mf-f9 calibration.** Our win % on the ladder, 8 members:
- v115 61.8 (live 61.5), v116 67.4 (live 66.2), v117 69.9 (live 68.8). That is the closest yet; mf-c2 gave
  62.7 / 68.5 / 69.8.
- livefork, body − live: +0.3 ±2.6 (mf-c2 +0.2).

**Not reproduced:** the fed Vesper. Her gold, damage and kills stay those of mf-c2.

Late-game Strength is the next thing to check: mitere's live median is 465 at r600-900 and 705 after r900. Avoiding
her loses on our side (mitere 97f1cf220: REJECT, 46.90%).

**Opponent classification.** opp_detect reads every mf body as unknown: 256 of 256 games against mf-c2
(`oppd_read.py`). The bodies write our packed turn order, not Mite's priorities. Exploit gates against them use a
forced test copy and read the fresh-Mite row.

## Files

- `live_ds.py`: our live scrims against a Mite pin, unzipped (`~/tmp-offload/mitefit/live/`).
- `mstats.py`, `runstats.sh`, `cmpstats.py`: per-game behaviour statistics for live and local runs, and the
  fidelity table.
- `calib.sh`, `calread.py`, `permap.py`: ladder calibration runs and reads.
- `mkbody.py`, `fitgen_r7.py`, `rule_*.py`: the bodies.
- `mf_livefork.py`: forkcomp's livefork with another body.
- `tune1.sh`, `gate1.sh`: the tune and its gates.
- `tune2.sh`: the same SPSA against mf-c2 members (mf-s961..966) on 40 fresh ladder-v3 suites.
- Map seeds used:
  - 7930000-7930039: tune1, ladder-v2.
  - 7931000: the h2h suite, ladder-v2.
  - 7932000-7932039: tune2, ladder-v3.
  - All are in `~/tmp-offload/mitefit/`, not under `maps/`.
- Data: `~/tmp-offload/mitefit/` (live decode and stats, local stats, fork runs, the tune's maps and logs).
