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

RESULTS-PLACEHOLDER

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
