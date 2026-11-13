# Charybdis 530 fuel pass — 2026-11-13

**Closed; modest gain retained as CHANGES 531. The 10% exhaustion target was not
met.** `bots/charybdis` equals frozen `variants/f530-final`. Further rank, cache,
medic-ranking and retreat-path changes stopped paying, so this pass closes with
the smaller confirmed reduction. All work stayed on `fuel-530-20261113`; no push.

## Final results on unused seeds

| Measurement | Games | Frozen 530 → final | Change, map-paired 95% interval |
|---|---:|---:|---|
| Release exhausted turns | 20,400 | 179,881 → 174,727 | **-2.87% [-4.57, -1.21]** |
| Debug exhausted turns | 4,080 | 38,574 → 37,313 | -3.27% [-7.58, +1.37] |
| Debug recorded shortcuts | 4,080 | 2,536,911 → 2,475,566 | **-2.42% [-4.49, -0.39]** |
| Shortcuts, uncensored maps only | 4,016 | 2,408,156 → 2,352,266 | **-2.32% [-4.20, -0.43]** |

Release win rate **50.40% [49.72, 51.09]** against frozen 530. No failed games,
broken/capped drafts or losses by round five. Debug runs also have no failed or
broken/capped drafts; their shortest game has over 190 recorded turns per body.
All intervals resample whole maps, keeping both sides together (2,000 samples,
seed 527); win interval is Wilson. Release uses 10,200 maps from ladder-v4 seeds
61496020–61496049; the debug subset uses 2,040 maps from seeds 20–25. None was
used in development. Debug mean fuel falls 0.51% [-0.86, -0.18].

Shortcuts count events excluding exhaustion and malformed SLOT labels. The
union of stdout-capped maps in either arm is 32 maps: the uncensored result drops
both sides in both arms for each. The stdout cap is 1,048,576 non-NUL bytes.
Runner exhaustion counts are complete and unaffected by that cap. The final
summary and paired observations are `results/confirmation.json`,
`results/release.json` and `results/release-pairs.json`.

Kept: one pass for the nine support tiles' camp exposure, lazy support queries
and ranking before safety, deferred medic partner checks with early heal-ranking
exit, complete ward-search proofs reused across revisits, and the enemy-near
precheck before invested-group work. The medic reads other allies' already-known
recall state, avoiding an invalid host query after movement hides an ally.
No draft, fuel gate, reserve or strategic constant changed.

100M production benches directly match **146/228** replays (36/52 own-draft wide,
110/176 forced coverage). These are **not** advertised as fully byte-identical.
After applying only the recall-query fix to the reference and disabling
`prepare_next_turn` in both diagnostic arms, **228/228 are byte-identical**.
The recall bug and preparation coupling are explained below. Conditional probes
exercise camp masks and ward-proof hits on all 176 coverage games, heal-ranking
stops on 175, and allies hidden after movement on 61; every champion occurs.

Completed replay bundles are deleted after measurement and audit. Bench JSON,
runner logs, manifests and the release results remain locally; compact evidence,
source hashes, patches and reproduction scripts are committed here. No
`fuel530-*` tmux sessions remain.

Worktree `/home/ubuntu/wt/fuel-530`, branch `fuel-530-20261113`, starting at
`705870058`; working alone. Frozen reference: `variants/chy-530`, never edited.
Target: at least 10% fewer exhausted turns, with fewer shortcuts prioritized over
mean fuel. No pushes or changes to other worktrees.

Read AGENTS, Cambridge Battlecode rules, tools guide, fuel-527, FUEL-GATES,
charybdis-fuelC/D and fuel-2026-11-13 artifacts. Prior lessons: count runner
exhaustion rather than recovery lines; profile actual exhausted turns; avoid
expensive cache bookkeeping/first-use initialization; force conditional champion
coverage; distinguish route-preparation coupling from exact replay identity;
reserve unused maps for confirmation. Broad bounds and mean-fuel wins alone have
repeatedly failed to reduce real exhaustion.

## Development history: protocol and progress

All games use cambc 5.0.1 native fast runner, CAMBC_SLOTS=86, no explicit A/B
threads, bench jobs 86. Own drafts except explicit matched coverage compositions.
Identity: bench 100M. Shortcuts: debug bench real fuel (`--fuel 0`), counting
non-OOF/non-SLOT events. Release A/B: real budget against frozen 530.
Intervals will resample whole maps, keeping both sides together.

Development maps: ladder-v4 seeds 61496000–61496001, 680 maps / 1,360 games.
No confirmation seeds have been played. Baseline and two wide census passes complete.
Replays in `replays/fuel/f530`; reproducible wrapper `tools/bench.sh`.

## Development screens

These 1,360-game results use the same development maps, fixed opponent and debug
builds. Intervals bootstrap maps with both sides together (2,000 samples,
`research/fuel-527/measure.py`). They are selection evidence only.

| Candidate | 100M wide identity | Exhausted turns | OOF change, 95% CI | Shortcuts | Shortcut change, 95% CI |
|---|---:|---:|---|---:|---|
| Frozen 530 | — | 13,705 | — | 880,033 | — |
| Lazy unseen fields | 51/52 | 13,281 | -3.09% [-9.32, +3.51] | 849,834 | -3.43% [-6.75, -0.22] |
| Enemy precheck before invested-group query | 52/52 | 13,148 | -4.06% [-10.57, +2.03] | 865,918 | -1.60% [-4.02, +0.90] |
| Stationary strike geometry | 51/52 | 13,138 | -4.14% [-8.69, +0.63] | 875,951 | -0.46% [-2.79, +1.96] |

At this stage none was retained: identical-game fuel savings are only about 0.01%, 0.02%
and 0.01%, respectively, and the OOF intervals all include no gain. Lazy fields
differ on 00fragment A; stationary geometry differs on 01hooks A. These
production identity differences have not been diagnosed and are not waived.
Patches preserve these attempts. At this stage the main bot remained frozen 530.

The census is indicative: instrumentation itself can move fuel-gated choices.
Wide census 2 puts 42% of first OOF episodes inside the goal branch and 12% in
retreat; farm evaluation, camp modeling, fight simulation and strike planning
are the substantial costs. It identifies no dominant new 530 check. See the two
compact census reports. A shared nine-station camp exposure pass is being tested.

### Runner path correction

The initial wrapper used relative `--games` paths. Fast run-batch resolved these
relative to its manifest, creating nested output directories; bench then failed
to find those bundles and started its stock fallback. The wrapper now passes an
absolute directory. Initial identity/census duplicates count only once. The
baseline development fast batch had completed all 1,360 games; the redundant
stock fallback was interrupted and `recover_bench.py` reconstructed bench JSON
from the completed native bundles, without rerunning games. Its runner log
supplies true OOF counts. This is not extra independent evidence.

## Further development before selection

| Variant | OOF | Change [95% interval] | Shortcuts | Change [95% interval] |
|---|---:|---|---:|---|
| supportmask | 12,875 | -6.06% [-13.53, +1.52] | 848,839 | -3.54% [-7.08, -0.03] |
| wardproof | 13,111 | -4.33% [-10.26, +1.18] | 860,668 | -2.20% [-4.17, -0.01] |
| conteststamp | 12,904 | -5.84% [-12.96, -0.11] | 858,308 | -2.47% [-4.84, -0.28] |
| rankorder | 13,832 | +0.93% [-7.44, +9.74] | 903,113 | +2.62% [-1.84, +7.09] |
| rankcheck | 13,639 | -0.48% [-8.10, +7.78] | 864,132 | -1.81% [-5.01, +1.64] |
| supportbatch | 13,209 | -3.62% [-12.62, +5.93] | 850,632 | -3.34% [-6.89, +0.55] |
| combo | 12,886 | -5.98% [-14.58, +2.82] | 843,127 | -4.19% [-7.87, -0.49] |
| combo2 | 12,483 | -8.92% [-16.41, -0.90] | 831,059 | -5.57% [-9.26, -1.83] |
| combo3 | 14,271 | +4.13% [-4.31, +13.65] | 846,243 | -3.84% [-7.51, +0.08] |
| combo4 | 13,180 | -3.83% [-10.83, +3.95] | 827,167 | -6.01% [-9.55, -2.43] |

Supportmask computes all nine neighbouring camp exposures in one group pass.
Wardproof extends the completed ward search's negative proof after placing its
first (globally best) candidate, when no external allied ward changes the ranking.
Conteststamp avoids clearing a 256-entry array. Rankorder/rankcheck retain or
validate previous turn ranks; both cost more fuel and are rejected. An earlier
insertion prototype was stopped because a partial exhausted write could destroy
its permutation. No results from that incomplete run are used.

Supportbatch adds lazy station queries, ranking before safety, and deferred heal
views to supportmask (the old fuelD support3 idea, excluding its unresolved guard
change). Combo adds wardproof and the enemy-near precheck. Combo2 defers medic
partner-danger queries until a healer can reach us, reads only the current
station when standing, and exits when another ally wins the heal. Combo3 moves
ranking predicates ahead of other medic work; combo4 memoizes ally camp fire by
observations, camp revision and actual positions. None is approved yet.

Supportmask is 52/52 identical in paired copies with next-turn preparation off.
Combo2 is only 47/52 under that diagnostic, so its remaining differences require
isolation. Production differences are not being called byte-identical. Full
patches preserve each attempt against frozen 530; they are research artifacts.

Stdout saturation is checked against 1,048,576 non-NUL bytes: bundle streams also
contain padding. Some development streams are capped, so raw shortcut totals
are observed counts. Final reporting will include an uncensored-map sensitivity
analysis. Runner exhaustion counts are unaffected. See audit-development.json.

Reserved final maps have been generated from seeds 61496020–61496049 (10,200
maps); no games on them have run yet. The first six seeds form the debug subset.
The forced coverage set has 92 maps (184 games), Willow in every composition and
all other champions cycled through the companion slots. It includes broad ladder
layouts and development stress geometries; manifests and draft prior are saved.

## Selected bundle and identity diagnosis

`variants/f530-final` equals `f530-medicfix`: combo2 plus the medic's use of the
already-read `recall_kept` for other allies. The allies cannot act during our
turn; their channel state is already known. Movement can take them out of sight,
so querying their live recall state again can throw error 97 and abandon the
remaining actions. The original medic loop did this even after a better heal
recipient had already made our credit zero. On 00contest B, round 132, champion
7, the original throws after moving to (34,26); the early exit avoids it.
`medic-firstdiff.json` and `medic-errors.json` retain the evidence.

Isolating the stationary medic query gives 52/52 identities with preparation
off. The remaining medic change gives 47/52; all five differences disappear
when both copies use the known ally recall state: 52/52. The selected version
fixes the query directly as well as exiting the ranking loop early.

Against frozen 530 with only that recall fix and preparation disabled in both
arms, the entire final bundle is **228/228 byte-identical at 100M**: 52 wide own
drafts and 176 forced-composition games. This is a diagnostic identity result,
not a claim that the unmodified production reference matches. Production keeps
preparation. Differences caused by preventing the erroneous host query are
intentional bug fixes; fuel-dependent route preparation is the established
coupling documented in fuel-527. Exact identity reports are in results/.

Coverage originally listed 92 paths, but four ladder maps appeared by both
short name and full path (identical file hashes). These are deterministic
duplicates, not independent evidence: 88 unique maps / 176 unique games. The
manifest is now deduplicated. Willow occurs in every game, and every other
champion occurs (including Cassi/Issac together). Full coverage identities
compare unique map-side pairs.

The final development screen has 13,705 → 12,833 exhausted turns, **-6.36%**
[-13.45, +2.07], and 880,033 → 822,982 recorded shortcuts, **-6.48%**
[-10.79, -2.45]. This does not establish the 10% target. The chosen source is
frozen before confirmation. Subsequent retreat-path memoization saves only
0.08 fuel per turn and none on heavy turns, while adding initialization; dropped.
The rank, broad cache and later medic ranking experiments also stopped paying.

Confirmation ran on reserved ladder-v4 seeds 61496020–61496049:
20,400 release games against frozen 530, plus 4,080 debug games per arm against
the same frozen opponent on seeds 20–25. These maps were not used for selection.
