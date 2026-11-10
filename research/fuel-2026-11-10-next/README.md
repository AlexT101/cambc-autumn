# Ocean: reduce unfinished turns, after 495 (2026-11-10)

Baseline: `variants/oc-fuel-495`. Candidate during experiments: `variants/oc-fuel-risk`;
shipped source: `bots/ocean`, frozen as `variants/oc-fuel-496`. Worked without subagents.

The target was at least 10% fewer out-of-fuel turns, prioritising these and shortcuts over mean fuel.
The fresh 4,096-game bench gives **19.3% fewer OOF turns and 4.9% fewer shortcuts**. Mean fuel falls only
0.54%: the useful savings are concentrated in expensive turns, and turn-end warming absorbs spare fuel.

## Changes

1. **Ask support safety only for what its callers use.** All but the independent Willow heal step read
   `SupportExposure.enemy` or `safe()`. Previously every station called `Safety::bound`, calculating camp
   damage, ordinary and doubled enemy damage, hits and stuns, for all nine tiles. Now it calls the existing
   `Safety::threat_at`, which computes the same threat boolean and stops on a sufficient threat. The
   independent heal step still calls the full bound, only after its cheap gates and the safe-tile check.
   No danger threshold, search budget or fuel gate changes.
2. **Reject entire harmless/dead camp groups before testing their members.** Support still treats sleeping
   monsters, monsters drawn by an ally, and groups returning by the next round as dangerous. Group Strength
   is the sum of nonnegative member Strengths. A camp check is unnecessary once an enemy already makes the
   tile unsafe; callers read the camp flag only through `safe()`.
3. **Precompute output coefficients in champion metadata.** `raw_output` used to inspect both ability kinds
   on every call. The metadata now supplies the two coefficients and whether each multiplies Strength or
   Focus. The cooldown is eight, so moving its power-of-two division into the coefficient preserves float
   multiplication rounding for gameplay stats; the additions remain in their original order.
4. **Reuse the existing strike cache for explicit ready-slot masks.** `strike_with` previously rebuilt a
   Strike for every subset considered by the turn-order model. The cache already covers champion identity,
   type, scaled Strength/Focus and all four slot masks. Its widened/standing variants are invalidated as before.
5. **Inline radius-one escape dilation.** A masked `grow()` is already the answer for radius one. Avoid the
   general, non-inlined `widen()` call in both `grow_by` and the per-turn strike loop.

## Measurements

All games use cambc 5.0.1 and the native fast runner. Both sides use their own draft except the explicitly
matched test-draft and forced-composition identity tests. Real-budget bench runs are debug builds; release
A/Bs are separate. No repeated deterministic game contributes extra evidence.

| Test | Baseline OOF | Candidate OOF | Change | Shortcuts, baseline → candidate |
|---|---:|---:|---:|---:|
| Screen, 1,024 paired games | 11,964 | 9,680 | -19.09% | 361,835 → 346,803 (-4.15%) |
| Fresh confirmation, 4,096 paired games | 47,536 | 38,362 | **-19.30%** | 1,449,627 → 1,378,828 (**-4.88%**) |
| Standard release A/B, 1,280 games | 13,659 | 11,803 | -13.59% | release has no shortcut trace |
| Fresh release A/B, 4,096 games | 43,109 | 36,087 | **-16.29%** | release has no shortcut trace |

Fresh confirmation's paired-game bootstrap 95% intervals: OOF -21.58 to -16.78%; shortcuts -6.41 to -3.38%.
There are 18,873,285 versus 18,826,369 play turns, so normalising for game length gives OOF **-19.10%** and
shortcuts **-4.65%**. After round one, mean fuel is 48,062 → 47,803 and p99 is 95,072 → 94,641.
The standard release A/B is 49.2% (46.5–52.0); fresh release is **50.8% (49.2–52.3)**. Both have no
failed matches or broken/capped drafts. The release confirmation also clears the requested 10% reduction.

The screen is every fourth map in the previous `fuelcap/p1` manifest, seeds 1370018–1370025. The confirmation
is 2,048 newly generated ladder-v2 maps, seeds 1460242–1460249 (256 each), fixed before testing the final
candidate. Manifests and compact results are in `tools/` and `results/` here.

**Counting:** use the runner's `Out of fuel: A … B …` totals, not bench.py's `out_of_fuel` field. The latter
filters play rounds using draft length, while stdout recovery messages can miss consecutive overruns.
`tools/compare.py` joins the runner totals to each map/side. Shortcuts exclude the separate `out-of-fuel`
category and malformed `SLOT` tokens. These are counts of recorded shortcuts, not distinct turns with one.

## Identity and conditional coverage

- `bench.py`, 100M: **90/96 own-draft replays identical**, **96/96 test-draft replays identical**.
  All six own-draft differences vanish in the diagnostic with both bots' turn-end
  `prepare_next_turn` call omitted: **12/12 identical** on both sides of the six maps. This is the pre-existing
  coupling documented by 495: warming next turn's walk has a real-budget floor even in a 100M game, and
  ready versus unready path fields can affect farm choice. The change leaves that behaviour alone rather
  than reproducing the old amount of wasted fuel. The first four differences change only a late claim/heal
  event, with exactly the same number of turns.
- On the 90 directly identical games, turns above 100k fall 17,408 → 16,680 (-4.2%). Baseline turns above
  95k save 1,314 fuel on average; above 100k, 1,404.
- **Stellar is absent from the usual identity compositions.** A separate forced draft puts Stellar, Willow
  and Prism in every team, adding Cassi/Issac and Ren on larger teams. It uses all 48 identity maps plus six
  existing large-group stress maps (40/64/100 squares, 3/5 picks, central groups up to 352 members).
  **94/108 replays are directly identical.** Among those games, baseline turns above 95k save 4,515 fuel;
  turns above 100k fall 6.1%. Disabling the same turn-end preparation in both bots restores **22/22 byte
  identities** on both sides of all eleven differing maps, including the large-group cases. Thus every
  differing own/forced-draft replay is resolved by the same pre-existing cache-preparation coupling.
- An instrumented forced-composition copy checks the new enemy/safe booleans against the old full bound and
  member loop on the same state. Across **108 games and at least 397,312 checks: zero mismatches**. Its block
  is in `tools/risk-oracle-block.txt`; the instrumented variant is `oc-next-risk-oracle`. An earlier camp-only
  oracle also has zero mismatches in eight games on the first differing maps.
- `tools/check_output.py` compiles the actual champion header and compares old/new arithmetic bitwise on
  **1,300,000 inputs across all 13 champion bodies**, including zero and random stats up to one million:
  all identical. The tiny SDK stub supplies metadata types only; no engine calls are involved.

Raw bench JSON/logs: `replays/fuel/oc-next/`; replay bundles and runner logs:
`replays/fuel/games/<result-stem>/`. Exception: the early escape identity and strike real-budget runs use
`replays/fuel/oc-next/escape-id-games` and `strike-real-games`. Release results:
`replays/ab/oc-next-standard` and `oc-next-holdout`.

## What was tried and dropped

Learned from fuel campaigns 5–7, 12–13, campaign 16, fuelgap's lane A and the preceding fuel-2026-11-10 pass:
the hot profile is flat; sim unrolling and generic caches often cost more than they save; cross-turn sim
reuse is rare; warm-up dominates mean/p90; high-budget identity can still couple to cache preparation.
The existing record cache, radius reduction and tail reserves were retained, not rediscovered as gains.

All names below are under `bots/variants/`. Identity tests use the same 96 games; comparisons of fuel by
turn use only byte-identical games. A positive saving means less fuel.

| Variant / idea | Result and decision |
|---|---|
| `oc-fuel-strike`, explicit-mask strike cache | 96/96 identical; saves 19 mean, 195 on turns ≥95k. Kept. |
| `oc-fuel-escape`, radius-one dilation | 96/96 identical; small further saving. Kept. |
| `oc-fuel-pair`, closed form for allocating two spells across turns | 96/96 identical, slightly dearer than the cache alone. Dropped. |
| `oc-fuel-wake`, eight hashed search wake-cache buckets | 96/96 identical, +1 mean/+4 heavy fuel. Dropped. |
| `oc-fuel-stale`, earlier stale checks in escape/sim/retreat/search | 1,024 real games: stdout OOF 11,311 versus 11,253 baseline. No gain; dropped. |
| `oc-fuel-output`, precomputed output coefficients | 96/96 own and test identities; saves 836 on ≥95k turns versus baseline. Screen engine OOF -7.39%, shortcuts -3.13%. Kept. |
| `oc-fuel-reads`, cache gold/cooldowns/items between actions | 96/96 identical but +55 mean/+74 heavy versus escape. Dropped. |
| `oc-fuel-centre`, single-foe ground-cast centre shortcut | 96/96 identical; about one mean fuel saved, none on heavy turns. Dropped. |
| `oc-fuel-touch`, omit already-awake/harmless groups from search wake masks | 95/96 identical, only 4 mean/23 heavy saved versus escape. Dropped. |
| `oc-fuel-support`, filter camp groups first | 92/96 directly identical; about 34 mean/134 heavy saved versus output. Same-state oracle passes. Kept. |
| `oc-fuel-retreat`, select retreat options on demand instead of sorting | 96/96 identical, about two mean fuel saved. Dropped. |
| `oc-fuel-reachstop`, stop Reach after a hit when no later stun can improve it | 96/96 identical, about three mean/58 heavy saved. Dropped. |
| `oc-fuel-stations`, build only requested station entries | 90/96 identical against support, 75 mean/135 heavy saved on matching games. Small gain and more cache complexity; dropped. |
| `oc-fuel-risk`, compute booleans in support and full bound only in quiet heal check | The final bundle above. Screen and fresh confirmation both reduce OOF about 19%. Kept. |

The useful follow-up lesson is to trace which fields a result's callers actually consume. Avoiding whole
damage calculations paid much more than memoising another small inner loop. Short-circuiting by group
state also avoids work proportional to large camp membership without inventing a new approximation.

## Reproduce

```sh
py tools/fuel/bench.py run variants/oc-fuel-496 --opp variants/oc-fuel-495 \
  --maps $(cat research/fuel-2026-11-10-next/tools/maps-id.txt) --jobs 32 --out replays/fuel/oc-next/final-id.json
# Default bench fuel is 100M. Add --fuel 0 for real-budget measurements; use the held-out manifest.
py research/fuel-2026-11-10-next/tools/compare.py \
  replays/fuel/oc-next/base-holdout.json replays/fuel/oc-next/risk-holdout.json \
  replays/fuel/games/base-holdout/run-batch.log replays/fuel/games/risk-holdout/run-batch.log
py research/fuel-2026-11-10-next/tools/check_output.py
CAMBC_BIN=$PWD/tools/fastengine/runner/fastrunner FASTRUNNER_MODE=native \
  py tools/ab.py variants/oc-fuel-496 variants/oc-fuel-495 --no-test-draft --threads 32
```

For a custom `bench.py --games` path, pass an absolute path. A relative path is duplicated by the fast
runner's output-directory handling and causes missing statistics and slow stock retries.
