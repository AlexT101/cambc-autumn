# Ocean fuel, after 496 (2026-11-10)

Worked alone. Baseline is `variants/oc-fuel2-base`, identical in source to `variants/oc-fuel-496`
and ocean at `6a1b127ae`. The goal is at least 10% fewer exhausted turns, also reducing shortcuts;
mean fuel is secondary. All measurements use cambc 5.0.1 and the native fast runner.

Shipped in `bots/ocean`, frozen as **`variants/oc-fuel-497`**. Final fresh confirmation clears the goal:
**13.42% fewer exhausted turns and 6.50% fewer shortcuts**; release builds show **10.98% fewer exhausted turns**.

## Changes

1. **Compile strike formulas.** Kit, ready-slot mask and movement determine the coefficients and
   reach at each distance. Compile these into a table; evaluate the changing Strength/Focus with
   SIMD. A compile-time assertion checks that a combined spell/basic term dominates the pure spell
   term wherever that simplification is used. Float multiplication and addition order are preserved.
2. **Compile derived champion metadata.** Ability-slot lookup, dash kind, casting/stunning ranges
   and the tracking model's action range are properties of the kit. The champion aggregate derives
   them at compile time rather than repeatedly inspecting its two abilities.
3. **Rank small teams in parallel.** Compare cyclic offsets of four/eight priorities with SIMD,
   retaining the original lower-index tie break. Padded entries rank below real entries even at
   `INT32_MIN`. Larger teams keep the scalar fallback.
4. **Compile Reach attack patterns.** Movement/ability geometry, insertion order and equal-key
   merges depend only on the kit and readiness combination. Compile them once; evaluate damage
   and retain the original stable damage ordering at runtime. The basic-attack index is retained:
   it determines whether the second basic attack counts.
5. **Use window masks for ward visibility.** Replace square-building loops in support and turn
   order with the existing square table. For a ward's actual board, reuse the existing validated
   chunk-window reader, with a positions-within fallback. No sight rule changes.
6. **Stop a settled Reach query.** Ways are in descending damage order. Once a single-turn hit
   reaches the current damage, later walked hits cannot improve the result. Stop only after the
   basic follow-up is accounted for when needed and every possible stun is settled. A precompiled
   per-pattern stun flag avoids a suffix scan or runtime suffix table.

No search budget, fuel gate, combat threshold or draft is changed. The tables require no draft-time
initialisation. These changes are additional to 495's record cache/ring queue/tail reserves and 496's
support-risk queries/output coefficients/strike cache.

## Measurement method

Real-budget bench runs are debug builds, so shortcut traces are present. OOF counts come from the
runner's **`Out of fuel: A ... B ...`**, not stdout's recovery markers or the bench JSON's inferred
count: those miss consecutive exhausted turns. Shortcuts exclude `out-of-fuel` and malformed `SLOT`
lines. Release A/Bs are separate, with both bots on their own drafts (`--no-test-draft`).

The 1,024-game screen uses previously tested maps and is not independent confirmation. The first
fresh suite has 2,048 ladder-v2 maps, seeds **1461310–1461317**, both sides. The final confirmation
suite has another 2,048 maps, seeds **1461410–1461417**. Each seed makes 256 maps. Manifests are in
`tools/`; runner logs and full per-turn bench JSONs are under `replays/fuel/oc-third/`.

### Final bundle

| Test | Baseline OOF | Candidate OOF | Change | Shortcuts, baseline → candidate |
|---|---:|---:|---:|---:|
| Final fresh bench, 4,096 paired games | 40,183 | 34,789 | **-13.42%** | 1,419,556 → 1,327,255 (**-6.50%**) |
| Standard release A/B, 1,280 games | 11,565 | 10,624 | -8.14% | no release trace |
| Final fresh release A/B, 4,096 games | 37,031 | 32,964 | **-10.98%** | no release trace |

Paired-game bootstrap 95% intervals on the final fresh bench: OOF **-16.43 to -10.07%**, shortcuts
**-8.08 to -5.00%**. Normalised for the 18,751,747 → 18,652,031 play turns: OOF **-12.96%**, shortcuts
**-6.00%**. After round one, mean fuel is 48,200 → 47,770 (-0.89%), p99 94,857 → 94,387. The final
release win rate is **51.0% (49.4–52.5)** on fresh maps; standard is 47.8% (45.1–50.6). Neither run has
failed games, broken/capped drafts or losses by round five. Compact outputs are in `results/`;
release bundles are `replays/ab/oc-third-shipped-{standard,confirm}`.

Across both 4,096-game real-budget suites, this exact final source has OOF **79,778 → 70,658 (-11.43%)**.
The first suite was reused during development; only the second is the final independent confirmation.

### Earlier bundles

Before the Reach early exit, the combined five changes (`oc-fuel2-plus`, code-equivalent to the
provisional `oc-fuel-497`) measured:

| Test | Baseline OOF | Candidate OOF | Change | Shortcuts, baseline → candidate |
|---|---:|---:|---:|---:|
| Screen, 1,024 paired games | 10,069 | 8,618 | -14.41% | 339,877 → 334,457 (-1.59%) |
| First fresh bench, 4,096 paired games | 39,595 | 35,926 | -9.27% | 1,369,565 → 1,330,951 (-2.82%) |
| Standard release A/B, 1,280 games | 11,493 | 10,590 | -7.86% | no release trace |
| First fresh release A/B, 4,096 games | 37,591 | 33,927 | -9.75% | no release trace |

Standard release win rate was 49.5% (46.7–52.2), fresh 50.7% (49.2–52.2), with no failed games or
broken/capped drafts. The independent results fell just short of the target, so work continued.

The early exit alone, added to that bundle, saved 295 fuel per ≥100k turn on identical games.
It gave OOF 8,671 and shortcuts 332,303 on the screen; on the first fresh maps, now used as a development
suite, OOF **35,869 (-9.41%)**, shortcuts **1,333,871 (-2.61%)**. Per-turn reductions there were 9.86%
and 3.08%; the candidate played 18,865,234 turns versus 18,772,533. These reruns do not provide a second
independent confirmation.

## Exactness and conditional coverage

- **Own drafts, 100M:** 93/96 replays directly byte-identical. The three differences are
  `00monolith` side A, `gen-continent-144001002812` side B, and `gen-shared-gems-144000014002` side B.
  As in 495/496, next-turn walk preparation has a real-budget cap even under the 100M bench. Changing
  earlier fuel changes which cache entries it prepares, and cache readiness can change path selection.
  Omitting only `prepare_next_turn` in both diagnostic copies resolves all three maps: **6/6 identical**.
  That omission is not shipped. The early exit itself was **96/96 identical** to the five-change bundle.
- **Forced compositions, 100M:** **108/108 byte-identical**, including all 13 champion bodies, 3/4/5-pick
  teams, and large camp groups on 40/64/100-sized stress maps (up to 352 central members). The selected
  side drafted Stellar 56 times, Varg 54, Willow 55, Heart of Ruin 44, Prism 41, Tavi 38, Ryth 37,
  Vesper Vale 35, Cassi & Issac 35, Ren 35, Vendetta 31 and Marcella 31. This covers spells, resets,
  stuns, dash landings, Varg splash, linked bodies and the ward/heal paths.
- **Actual-source arithmetic checks:** 2,080,000 strike inputs in both scalar and SIMD builds;
  3,380,000 ordered Reach patterns; 1,700,000 priority rankings; every derived metadata property.
  Zero bitwise/result differences. Stats include zero and random nonnegative values up to one million;
  ranks cover sizes 0–16, ties and both int32 extremes.
- **Same-state engine oracle:** the forced-composition 108 games compare the actual `Reach::at`
  result to the original full loop, using recalculated bounds. At least **325,072 checks**, no mismatch.
  The ward-board path was checked against all 81 old tile tests on three calls; every square-mask use
  was also compared with the original nested loop. `tools/make_oracle.py` builds the diagnostic copy.

Oracle work is inside `debug_block`. Its fuel/codegen and cache warming are not used for performance
claims. The ordinary replay comparisons use uninstrumented bots.
On the 93 matching own-draft games, total fuel falls 0.81%; turns over 100k fall 18,506 → 17,532 (-5.26%).
Those ≥100k turns save 1,645 fuel on average. The final source matches `oc-third-earlyreach` exactly;
`results/source-hashes.json` records baseline/candidate fingerprints.

## Lessons and rejected experiments

Read the preceding two fuel passes and campaigns 4–7, 12–13, fuelgap lane A, retreat fuel work and
FUEL-GATES before changing code. Their main warnings held: the hot profile is flat; generic caches
and smaller structs often cost more; repeated simulations mostly have different inputs; warm-up
absorbs spare fuel; and a high-budget game can still depend on measured fuel/cache readiness.

A fresh fine census on the 96-game manifest found 1,177 first and 433 subsequent exhausted turns.
Strike search appeared in 53% of exhausted turns (~36k inclusive), but world updates, fight setup,
retreat and farming were also substantial. HoR, Vesper, Willow, Ren, Issac and Prism were the most
frequent exhausted bodies. `replays/fuel/oc-third/census-summary.txt` holds the full breakdown.

The table below reports savings on byte-identical games, positive meaning cheaper. `oc-fuel2-*`
experiments are isolated against the original baseline unless noted; `oc-third-*` follow-ups are
against the combined bundle or its early-exit version. Full comparisons are in `results/experiments.txt`.

| Experiment | Result / decision |
|---|---|
| Quiet-pair simulation | +4 mean, +35 heavy fuel used; dropped. |
| Strike formulas | 96/96 identical; saves 115 mean, 490 on ≥100k turns; kept. |
| Derived metadata | 96/96; saves 73 mean, 171 heavy; kept. |
| SIMD ranks | 96/96; saves 123 mean, 392 heavy; kept. |
| Lazy hidden-enemy fields / hits-only queries | 96/96; saves 11 mean; too much extra cache machinery for the gain. |
| Compact Fighter fields | 96/96; +6 mean, +53 heavy; dropped. |
| Closed-form search squares | 96/96; saves 3 mean, 18 heavy; dropped. |
| Complete threat-strike memo | 96/96; +22 mean, +44 heavy; dropped. |
| Batched exact-sixteenth quiet damage | 96/96; +11 mean, +85 heavy; dropped. |
| Additional boolean safety queries | 96/96; saves 5 mean; dropped. |
| Relative-order rank cache | Worse by 37 mean versus the original baseline; dropped. |
| Compiled Reach patterns | 96/96; saves 30 mean, 205 heavy; kept. |
| Capped damage bounds / camp-only lethal precheck | 96/96; +1 mean; dropped. |
| Ward masks | 94/96 directly identical; saves 46 mean, 106 heavy on matching games; kept. |
| Shared HealGate cache | 96/96; saves 10 mean; not enough for another cache. |
| 64-entry camp-damage memo | 96/96; +81 mean; dropped. |
| Runtime dominated-way pruning | 96/96 versus bundle; +33 mean; dropped. |
| Compile-time dominated-way pruning | 96/96; saves 6 mean, 45 heavy; dropped. |
| Reuse unchanged Reach bounds | 96/96; less than one mean, 3 heavy saved; dropped. |
| Reach early exit | 96/96; saves 23 mean, 295 heavy; kept. Prior passes' suffix-table version cost more to build; this uses a static flag and also handles two-turn queries. |
| Store maximum reach during bounds build | 96/96; saves 3 mean but costs 13 heavy; dropped. |
| Skip impossible repeated camp-stun reads | 96/96; costs 10 mean, 11 heavy including the new guards; dropped. |
| Share champion stun/shield buff read | More expensive; dropped. |
| Reuse the last attack-range box | 96/96; costs 7 mean, 74 heavy; dropped. |
| Heap of unpriced strike tiles | 96/96; costs 7 mean, 32 heavy; dropped. |
| Scalar ranking, each unordered pair once | Costs 40 mean versus SIMD ranks; dropped. |
| Pass champion index directly into strike formulas | Exactly the same fuel on every turn; compiler already removes the pointer arithmetic. No additional change needed. |

## Farm-reserve handoff

The user handed over the paused fuel-prover programme during final confirmation. Its handoff is preserved
in `results/farm-handoff.md`; the committed notes/patches are in `research/fuelcap-2026-11-09` and
EXPERIMENTS (commits `5f77c9805`, `b0eeff17e`). These tests use the older `ocean-16d6f78`, not this baseline.

The 16k/20k/24k arms subtract that much slack from the farm-loop reserve; they do not reserve more fuel.
Their partial fresh results were +0.05 ±0.52, -0.43 ±0.56, -0.12 ±0.60 points, while exhausted turns grew.
No clear gain warrants applying them to an OOF-reduction task. The useful finding is that most cut farm
loops finish with substantial unused reserve, while half of exhausted turns miss by less than 3.9k.
This supports saving work in expensive turns, and testing any reallocation against both exhaustion and
shortcuts instead of assuming that doing more is better.

The accompanying queue-recovery guard is tested separately as `oc-third-queueguard`: it makes a resumed
warm-up stop at its next fuel check. Its global guard costs about 139 mean fuel on this source. It is not
part of the shipped six-change bundle. Against that bundle on the 1,024-game real-budget screen, OOF is
**8,671 → 8,772 (+1.16%, 95% -1.94 to +4.68)** and shortcuts **332,303 → 335,109 (+0.84%)**; mean fuel
rises 0.28%. It gives no evidence of an improvement in either target metric and was dropped. The 100M
check is 95/96 identical, with one of the already known preparation-sensitive maps differing. Results are
in `results/queueguard-{screen,identity}.txt`. No reserve reductions or queue guard are shipped.

## Reproduce

```sh
export CAMBC_BIN=$PWD/tools/fastengine/runner/fastrunner FASTRUNNER_MODE=native
py tools/fuel/bench.py run variants/oc-fuel-497 --opp variants/oc-fuel-496 \
  --maps $(cat research/fuel-2026-11-10-third/tools/maps-id.txt) --jobs 32 --out replays/fuel/check.json
# For real budgets, add --fuel 0 and use maps-confirm.txt; give each run a distinct absolute --games path.
py tools/fuel/bench.py compare BASE.json CAND.json
py research/fuel-2026-11-10-next/tools/compare.py BASE.json CAND.json BASE-run-batch.log CAND-run-batch.log
py research/fuel-2026-11-10-third/tools/check_strike.py bots/variants/oc-fuel-497
py research/fuel-2026-11-10-third/tools/check_metadata.py bots/variants/oc-fuel-497
py research/fuel-2026-11-10-third/tools/check_ranks.py bots/variants/oc-fuel-497
py research/fuel-2026-11-10-third/tools/check_ways.py bots/variants/oc-fuel-497
py tools/ab.py variants/oc-fuel-497 variants/oc-fuel-496 --no-test-draft --threads 32
```

For the conditional bench, copy both bots, generate both test-composition arrays with
`tools/draftlab/test_comps.py --prior tools/coverage-prior.json --bot BOT`, enable both copies'
`params::test_draft`, and use `tools/maps-coverage.txt`. Paths here are relative to this research directory
where applicable. The shipped bot keeps its own draft.
