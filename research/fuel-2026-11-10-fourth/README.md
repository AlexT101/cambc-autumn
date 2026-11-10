# Ocean fuel 501 (2026-11-10)

Worked alone. The initial reference is `variants/oc-fuel4-base`, source-identical to
CHANGES 498. The objective is at least 10% fewer exhausted turns and fewer shortcuts;
average fuel is secondary. All games use cambc 5.0.1 with the native fast runner.

Shipped in `bots/ocean`, frozen as **`variants/oc-fuel-501`**. CHANGES 499 (Skirmish table)
and 500 (heal before waking a lethal camp) were independently merged during this work and
are preserved. `oc-f4x-currentbase` equals frozen 500; the tested final source is
`oc-f4x-combo6`/`oc-f4x-release6` (the shipped copy only corrects two cache-version comments).

**Final independent release confirmation: 11.30% fewer exhausted turns**, 30,156 → 26,749,
on 4,096 games; wins 51.15% (49.62–52.68). Standard release: 9,663 → 8,506 (-11.97%),
49.84% wins. No failed games, early losses or broken/capped drafts. On the same fresh maps,
the final real-budget debug bench reduces exhausted turns **13.67%** (32,202 → 27,799) and
shortcuts **6.31%** (1,313,304 → 1,230,497). Mean fuel falls 0.37%.

## Changes

- **Answer settled threat queries before building movement geometry.** Every movement
  set contains the enemy's current tile. If all attack patterns can reach and see the
  target from there, their maximum damage, basic follow-up and stun result are already
  known. The compiled pattern stores the minimum applicable range and the recipe stores
  the result. Other queries build the original geometry on demand. Stationary patterns
  need only the origin; Varg retains its splash-unit calculations.
- **Reuse camp geometry until occupancy changes.** Damage that leaves a monster alive
  does not change movement blockers. A separate version tracks occupied/empty changes,
  captures and respawns. Pathing and non-Varg Reach reuse their boards against this version;
  health-based decisions retain their original versions and dirty groups. The final version
  tracks occupancy both globally and per group; Pathing's group masks and the large-group
  combat lane masks also survive nonlethal damage.
- **Index camp members once per group.** Economy and Reach share a tile-to-member table.
  Its 16-bit entries also fix the old Reach cache silently ignoring members numbered 255
  and above. Large groups are explicitly included in the coverage suite.
- **Index static enemy walks by origin and movement kind.** Replace the 24-entry scan/LRU
  with a direct index and a bounded 256-entry FIFO. Boards are still filled only when needed.
- **Check cached clear ordering in linear time.** With an unchanged living set, adjacent
  updated keys establish whether the order still sorts. New ties rebuild the geometry
  tie-break. This avoids comparing every changed member with every other member.
- **Small SIMD operations.** Test four allies' fight squares together, copy the fixed
  search node representation with explicit vector loads/stores, and test whether a
  two-word window is nonempty with `v128.any_true`. Large-group combat compares sixteen
  camp members at a time using signed byte lanes, retaining the original member order.
  Published map coordinates/differences fit; padding is masked out. Scalar/constant-evaluation fallbacks
  remain. No search budget, reserve or strategic threshold is changed.

## Measurement

True exhaustion counts come from the runner's `Out of fuel: A ... B ...` lines. The
bench's inferred count and stdout recovery markers miss consecutive exhausted turns.
Shortcuts exclude exhaustion and malformed `SLOT` lines. Debug bench measures shortcuts;
release A/B measures platform-like play separately. Both bots use their own drafts except
the explicitly forced champion-coverage copies.

The development screen has 512 maps/1,024 games. Independent confirmation uses 2,048
fresh ladder-v2 maps, seeds **1462510–1462517**, both sides. Each seed creates 256 maps.
After preserving 499/500 and selecting the final camp changes, independent confirmation
uses another 2,048 ladder-v2 maps, seeds **1462610–1462617**. The first confirmation suite
is development evidence for that last selection. Manifests and diagnostic scripts are in
`tools/`; compact evidence is in `results/`.
Full bench JSONs and logs are under `replays/fuel/oc-fourth/`. Early runs used
`replays/fuel/games/<stem>`; later runs explicitly use `oc-fourth/games/<stem>`.

| Candidate / test | Reference OOF | Candidate OOF | Change | Shortcuts |
|---|---:|---:|---:|---:|
| Bundle 1, development 1,024 | 8,673 | 8,448 | -2.59% | 335,563 → 330,602 (-1.48%) |
| Bundle 2, development 1,024 | 8,673 | 7,794 | -10.13% | 335,563 → 321,725 (-4.12%) |
| Bundle 3, development 1,024 | 8,673 | 7,631 | -12.01% | 335,563 → 313,573 (-6.55%) |
| Bundle 4, fresh bench 4,096 | 34,741 | 30,558 | **-12.04%** | 1,335,902 → 1,240,232 (**-7.16%**) |
| Bundle 4, standard release 1,280 | 9,982 | 9,245 | -7.38% | release has no shortcut trace |
| Bundle 4, fresh release 4,096 | 32,655 | 29,117 | **-10.83%** | release has no shortcut trace |
| Bundle 4 on 500, first fresh bench 4,096 | 34,515 | 29,647 | **-14.10%** | 1,346,627 → 1,239,321 (**-7.97%**) |
| **Final 501, held-out bench 4,096** | **32,202** | **27,799** | **-13.67%** | **1,313,304 → 1,230,497 (-6.31%)** |
| **Final 501, held-out release 4,096** | **30,156** | **26,749** | **-11.30%** | release has no shortcut trace |
| **Final 501, standard release 1,280** | **9,663** | **8,506** | **-11.97%** | release has no shortcut trace |

Bundle 4 versus 498 fresh bench paired-game bootstrap 95% intervals: OOF -14.97 to -9.06%; shortcuts -8.93
to -5.60%. Play turns are essentially unchanged (18,654,584 → 18,649,768); per-turn OOF
-12.02%, shortcuts -7.14%. Mean fuel -0.58%. Release wins: standard 49.77% (47.03–52.50),
fresh 50.22% (48.69–51.75). No errors, early losses, broken or capped drafts.

The bundle 4 on 500 bench keeps both concurrent gameplay changes equal in candidate and reference.
It uses the same confirmation maps without tuning the fuel patch to their results. Play turns
18,708,428 → 18,727,457: OOF per turn -14.19%, shortcuts per turn -8.06%, mean fuel -0.78%.
Shortcuts' paired 95% interval is -9.77 to -6.26%. `results/current4-confirm.txt` is the full summary.
Release on that source gives fresh OOF 31,639 → 28,825 (-8.89%), wins 50.3%; standard
9,674 → 9,043 (-6.52%), wins 49.84%. This falls short of the release exhaustion target,
so development continued despite meeting it in the debug bench. `results/release-current.json`
holds all 5,376 games.

Bundle 1 combines walks, ally SIMD, the initial camp lookup and node copy. Bundle 2 adds
shared members, occupancy versions, stationary patterns and the smaller blocker radius.
Bundle 3 adds direct/deferred threat queries, linear clear ordering and window truth SIMD.
Bundle 4 shares Reach's camp lookup with economy, widens its indices and cleans up fallbacks.
The final bundle adds per-group occupancy versions and sixteen-member SIMD on top of 499/500.
The first-suite release screen improves to 28,183 / 32,037 OOF (-12.03%). Its final held-out
release result is 26,749 / 30,156 (-11.30%), 4,096 games; the standard check is 8,506 / 9,663
(-11.97%), 1,280 games. `results/release-final.json` contains all 5,376 games.

Final held-out debug bench paired-game bootstrap 95% intervals: OOF -16.72 to -10.75%,
shortcuts -7.86 to -4.81%. Play turns 19,025,552 → 19,007,323; per-turn OOF -13.59%,
shortcuts -6.22%. Mean fuel -0.37% (95% -0.66 to -0.10%).
`results/final-six.txt` contains the full summary. These paired-game intervals do not
account for the correlation between the two sides of one map.

For a fixed-opponent release comparison on the first suite, a separate 500-versus-500
mirror has 32,119 selected-side OOF. Bundle 4 against 500 has 28,825 (-10.26%); the final
bundle has 28,183 (-12.25%). This is distinct from comparing both sides within the head-to-head
A/B. No mirror rerun is counted as independent map evidence.

## Exactness and conditional coverage

- **100M own drafts:** bundle 4 has 93/96 byte-identical replays. The three differences
  are continent `144001002812` A, ladder `144000000022` B and monolith `144000008003` B.
  Bundle 3 diagnostic copies omitting only next-turn walk preparation are 6/6 identical
  on these maps: the previously documented cache-readiness coupling. That diagnostic
  omission is not part of the candidate.
- **100M forced compositions:** bundle 4 has 106/108 byte-identical replays. The suite
  covers all 13 champion bodies, 3/4/5-pick teams, and 112/208/352-member central groups
  on 40/64/100-sized maps. `groups-100-3` A changes with the intentional wide-member fix.
  `01corridors` A is a ward-cache timing exception, traced below.
- **Same-state Reach oracle:** the original full calculation, with an independently
  widened linear member lookup, passes at least **82,427** comparisons in 108 games.
  Damage is compared bitwise; hit and stun flags must match exactly. No mismatches.
  The oracle is diagnostic: its cache warming is excluded from performance results.
- On identical own-draft games, turns whose baseline cost is at least 100k save **2,918
  fuel/turn**; turns over 100k fall 17,576 → 16,313 (-7.2%). On matching conditional games,
  the corresponding saving is **5,033 fuel/turn**. These are unlimited-budget cost checks,
  not the actual exhaustion metric.

### Ward-cache timing exception

On `01corridors` A, with next-turn preparation omitted in both diagnostic copies, all
actual actions agree until Heart of Ruin's round 83. The old code queries a target at
(13,26) from (8,22) and unnecessarily reads enemy wards while settling that threat. Its
round-cached ward mask is 24. After moving to (9,23), it reuses that mask, predicts 120
damage and casts a shield. The optimized query already knows the same 180-damage result
at (13,26) from terrain/range, so needs no ward read. Its first ward read happens at (9,23),
where those enemy wards are no longer visible; it predicts zero damage and leaves the shield.
Both games finish in round 1,258 with the same 1,005–709 score.

The result formula is not the cause: same-state old/new queries agree. Reverting node copies,
walk caching or linear camp ordering does not resolve the difference; removing the direct
query exit does. Adding only the old ward-cache warming to the direct exit restores **2/2
byte-identical replays**. Traces and the identity check are in `results/wardtrace*.txt` and
`results/wardwarm-identity.txt`. This is the existing unintended dependence on the first
query's observation timing, analogous to the next-turn preparation cache coupling. The
user explicitly permits arbitrary ordering and asks not to preserve unintended quirks;
the artificial warming is diagnostic only and is not shipped. No claim that this shield
difference itself improves gameplay is made.

On the final source with 499/500 preserved, the own-draft 100M test is **95/96 identical**;
only continent `144001002812` A differs. Omitting next-turn preparation in both diagnostic
copies restores **2/2 byte-identical replays** (`results/current-noprep-identity.txt`). The final per-group/SIMD additions alone are **96/96 byte-identical** to bundle 4,
so they introduce no new own-draft differences. Final forced coverage remains **106/108**,
with exactly the same ward-timing and wide-member exceptions. On matching own-draft games,
≥100k turns save **2,990 fuel/turn**, with >100k turns 16,316 → 14,985 (-8.2%). These explicit
exceptions prevent claiming universal byte identity while retaining the full bench and
same-state evidence.

## Lessons used and rejected attempts

Read the previous 495–497 fuel work, campaigns 3–7 and 12–13, retreat/fuel-gap research,
and the historical `FUEL-GATES.md`. Their useful lessons were to measure the heavy tail,
count actual exhausted turns, cover uncommon bodies and large groups, avoid float
reassociation, and distrust cache-size/average-fuel wins until measured at the real budget.

The isolated 100M screen (96 own-draft games) rejected several tempting changes:

| Attempt | Result / reason |
|---|---|
| Heart of Ruin factor / distance early exit | Essentially no saving. |
| Share Pathing's live-camp board directly with Reach | Cost ~35 average and 171 fuel on heavy turns. |
| Insertion sort retreat steps | Slightly more fuel. |
| Incremental clear bookkeeping | More average and heavy-turn fuel. |
| Cache square windows | More average fuel and first-turn work. |
| Separate geometry by movement kind | Extra pointer/cache overhead outweighed reuse. |
| SIMD window AND/OR | Better average, worse heavy turns; retain only truth testing. |
| Walk FIFO 1,024 rather than 256 | No additional play-turn saving. |
| Larger allocation arena | Negligible benefit. |
| Special-case every stationary query | Worse than handling stationary geometry once. |

Small individually correct savings do not necessarily reduce exhaustion: ally SIMD plus
the first camp lookup measured OOF +2.14% on the development screen. The larger bundle is
judged as a whole, with independent confirmation. No deterministic suite rerun is treated
as additional independent evidence.

The sampled profiler initially used a stale symbol-offset convention. LLVM 33 wants the
absolute WASM offsets; `tools/symbolise.py` corrects the old subtraction. Draft costs also
appear in nominal heavy/OOF profile aggregates, so those totals are not claimed as clean
play-stage attribution.


## Final incremental experiments and remaining opportunity

- A broader direct-threat settled range is 96/96 identical but costs ~10 fuel/turn; dropped.
- Per-group occupancy versions are 96/96 identical, saving 45 mean and 125 per ≥100k turn; kept.
- Sixteen-member camp SIMD is 96/96 identical, saving 6 mean and 37 per ≥100k turn; kept.
- Explicit fighter vector copies compile to effectively the same work; no gain, dropped.
- SIMD clear-health counting/division costs 4 mean and 12 per heavy turn; dropped.
- Per-Reach lists of nearby group versions add checks/storage: +24 mean and +262 per heavy
  turn versus just per-group versions; dropped.

The queue diagnostic (`oc-f4x-queueprof`, 1,024 games) labels nested precomputation stages.
Recovery markers report 5,499 decide failures, 873 own-ring fills, 265 map warm-ups, 121
visible-enemy ring fills and smaller counts elsewhere. These are diagnostic recovery
markers, not the complete exhaustion metric. Most ring failures occur after round nine;
map warm-up failures are almost all early. `results/queue-profile.json` retains the counts.
A future pass can investigate the worst-case tile precomputation cost without confusing
it with next-turn approach preparation (only three marked failures here). The shipped
patch does not change queue budgets.

## Reproduction and source provenance

`results/source-seals.json` records SHA-256 seals over each source tree (sorted relative path,
NUL, file bytes, NUL). The final frozen copy equals `bots/ocean`; the reference equals frozen 500.
The only source differences from the final tested development copy are two corrected comments.
An exact-source rebuild has **96/96 identical replays and identical fuel on every turn**
versus that copy (`results/shipped-id.txt`). The full release suite repeats all **5,376 outcomes and per-suite exhaustion totals exactly**
(`results/release-shipped.json`). This is build verification, not additional independent map evidence.

For own-draft bench tests, run each arm against `variants/oc-f4x-currentbase` with
`tools/fuel/bench.py run BOT --opp variants/oc-f4x-currentbase --maps MAPS... --out OUT.json`.
Use `tools/maps-id.txt` at the default 100M for identity; use `tools/maps-final.txt` with
`--fuel 0` for real-budget counts. Pass a distinct absolute `--games` directory for each run.
Compare identity with `bench.py compare BASE.json CAND.json`; compare real-budget counts with
`research/fuel-2026-11-10-next/tools/compare.py BASE.json CAND.json BASE-run-batch.log CAND-run-batch.log`.
The reference bench is a 500-versus-500 mirror; the candidate plays the same fixed 500 opponent.
Release A/B instead compares the two sides of their head-to-head games.

Forced coverage copies use `tools/draftlab/test_comps.py --prior
research/fuel-2026-11-10-fourth/tools/coverage-prior.json --bot BOT`, with `test_draft=true`
in both copies. Run the bench at 100M with `tools/maps-coverage.txt`; `results/coverage.json`
records the actual selected compositions. The six large-group maps are the existing `maps/suites/fresh/fc13-largegroups-v2`
stress suite; their exact paths are included in the manifest.

Release validation command (native fast runner environment set as in AGENTS.md):

```sh
py tools/ab.py variants/oc-fuel-501 variants/oc-f4x-current-ref-release --no-test-draft \
  --suites ladder,gen,maps/gen-s1,maps/suites/fuel-fourth/final-all --threads 32 --name oc-fourth-shipped
```

`tools/fresh_final.py` regenerates the final seed directories and manifest. `final-all` links
all those maps. The first-suite generator is `tools/fresh.py`. Neither deterministic reruns
nor the final build check are additional independent evidence.
