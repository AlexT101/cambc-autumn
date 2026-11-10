# Warding: Mite r5, Ad Astra, and ocean498 (2026-11-10)

The observed policies justify targeted tests, not a conclusion that Ocean needs more wards. Ad Astra's sampled wards are exclusively in bushes. Mite places substantially more wards and often leaves one on a camp without gaining immediate information. Ocean has at least as much observed ward-only basic-attack use in these descriptive samples.

## Evidence and limitations

Artifacts: `~/tmp-offload/warding-2026-11-10/`. `jobs.json` names every game, side, map, timestamp and decoded source; `audit.json` contains every measured ward and validation counts. `warding-tools/select_replays.py` selects the sample from existing copied archives; `warding-tools/audit.py` reproduces the analysis with `python3 tools/pooled.py 4 -- python3 research/ideas-2026-11-10/warding-tools/audit.py`. No new platform scrims or downloads were needed.

Forty deterministic hash-selected common map/side cells from 55 available cells compare Mite r5's fixed-v105 games (Nov10 ~06:00) with the latest available Ad Astra game for each cell (Nov9 02:00–22:00). Ocean-v105 is the opposing side in the Mite games. Ad Astra's opponents and both teams' drafts vary. These are descriptions of policies and their realized use, not matched strength or causal ward-value estimates. Five Ad Astra games predate the platform's 05:25 engine change; a matched 35-cell sensitivity subset excluding them preserves the findings below.

| Forty games per team | Mite r5 | Ad Astra | Ocean v105 |
|---|---:|---:|---:|
| Wards | 6,982 | 4,030 | 4,086 |
| Wards per 100 alive champion-rounds | 4.22 | 2.45 | 2.54 |
| On bush tiles | 62.9% | 100% | 74.9% |
| On camp tiles (may also be bush) | 15.6% | 0.4% | 1.5% |
| New visible tiles per placement | 29.15 | 28.39 | 32.37 |
| New bush tiles per placement | 5.24 | 5.78 | 6.16 |
| Placement with a visible enemy within 4 | 4.4% | 13.7% | 5.8% |
| Confirmed ward-only basic attacks / all champion attacks | 344/4,122 (8.35%) | 278/5,409 (5.14%) | 389/4,332 (8.98%) |
| Wards subsequently enabling at least one such attack | 139 (1.99%) | 122 (3.03%) | 143 (3.50%) |

On the 35 cells after the engine change: bush placement remains 64.6% / 100% / 76.8%; camp placement 14.3% / 0.3% / 1.4%; confirmed ward-only attack shares 7.95% / 5.43% / 9.84%, respectively. This is a sensitivity check, not an independent sample.

A ward's new tiles are exact shadowcast sight minus the actor's current personal and previous ward sight. The future-use measurement counts only basic attacks with an identified champion target, not spells, movement, retreat, camp intelligence or effects on teammates' communicated beliefs. Nine attacks (2 Mite, 7 Ocean) had no reconstructed personal or ward sight and are excluded from the confirmed numerator. All 120 decoded cohort views passed extractor hard validation, and every reconstructed placement is within radius 2. Ignoring `teleport_start.f` is necessary: that extractor field can contain an uninitialized (0,0), whereas `teleport_end.to` is authoritative. There is no engine-rule contradiction.

Mite's camp wards add only 2.13 immediate tiles on average; 769/1,088 add none. This supports an information-retention hypothesis, not an immediate-reveal hypothesis. The geometric maximum-new-bush candidate score is descriptive only: it ignores hidden blockers and allied-ward occupancy. It also is not necessarily the opponent's objective. Ocean already achieves that geometric maximum more often than the others in the whole sample.

## Placement timing

A second pass over the same 120 cohort views separates current-turn reveal from retained information (`warding-tools/timing.py`, artifacts `timing.json` and `timing.log`). Ad Astra moves before 3,551/4,030 placements (88.1%); no observed placement is followed by movement or a cast by that actor in the same turn, and only 14 are followed by a basic attack. None of its 278 confirmed ward-only champion attacks uses a ward placed in that same turn. Mite has 19 immediate ward-only attacks enabled by 12 placements, versus 325 later attacks; Ocean has 23 immediate attacks enabled by 21 placements, versus 366 later attacks.

Thus Ad Astra's higher frequency of placements near visible enemies does not establish an aggressive early-reveal policy. In these games, its observed attack use is entirely later-turn information. Ocean's current early reveal mechanism has measurable immediate use and remains enabled in all three experimental arms. Spells and non-attack information value remain unmeasured; this timing comparison inherits the cohort confounds above.

## Prior null results and new experimental questions

The [earlier Mite study](../ideas-2026-11-08/mite-wards.md) tested extra fresh-bush wards, broad camp wards and removing the reveal-ward combat gate on the older oc-base25. Their large samples were approximately level. Broad camp scanning increased out-of-fuel turns by 36%. These variants therefore do not blindly repeat those implementations. CHANGES473 already made planned-ward site scores and ward sight masks exact, but explicitly deferred exact turn-end bush tile ranking for fuel risk.

All new arms independently copy **`variants/oc-campsh-498`**, the full frozen working498 including fuel497. Commit2905 alone omits fuel497. No arm stacks another ward experiment, modifies opponent bodies, changes drafts, or modifies working Ocean.

- **`variants/oc-wtile-498`** keeps the existing bush cluster selection, replacement trigger and candidate restriction. Within that chosen cluster, it ranks candidate tiles by actual ward sight covering tiles within ability range of the actor and its claimed work. Stable ties preserve the first tile; a 7,000-fuel floor bounds the search, and existing first-three placement fallback remains. This tests the previously deferred exact tile ranking, including its runtime cost.
- **`variants/oc-wbush-498`** disables only planned wards on non-bush tiles and falls back to Ocean's existing bush policy. Bush planned wards and combat reveal wards stay unchanged. This Ad Astra-inspired ablation asks whether non-bush planned wards are useful relative to conserving/reusing the ward for bushes; it is not a reconstruction of Ad Astra's whole policy.
- **`variants/oc-wcamp-498`** adds a fallback only when no planned ward applies and the existing bush policy placed nothing. It looks only at camp tiles within radius 2, requires a known cleared/respawning group, and keeps an existing ward within 8 tiles. Its fixed local board scan avoids the older whole-map camp scan. A 7,000-fuel floor bounds attempts. This tests a cheap form of Mite-style retained camp information; it intentionally does not copy every camp placement.

`warding-tools/prepare.py` reproduces these source changes and refuses to overwrite existing arms. `warding-tools/sources.json` records the sealed source fingerprints; the artifact `source-manifest.json` lists every source file hash, with exact patches beside it. The frozen base source fingerprint must equal the queue's known full498 fingerprint `d0a0755075bf4010dc1ac96e7b209aafd3791ba1a8bc1c3b625d56e55f38a23e`.

## Matched fuel gates

Each arm gets separate normal-budget and `--fuel 200000` fresh gates against the same frozen base. Both candidate and reference face the same Flp4/Mt3q bodies, noise blocks, maps and sides within each fuel condition. Both teams receive the selected budget; this scales the engine's first-turn/draft allowance too, so the raised-budget comparison measures the whole game under that budget. Do not pool the two budgets or interpret their difference as a clean estimate of only our ward-search cost.

`fgate.py --fuel` passes the value to ab.py and appends `-fuel200000` to game, lock, log and final result names. Cache acceptance also requires matching summary fuel metadata; normal-budget names remain unchanged. Three tests check unchanged normal names, all nine selected/cached budget combinations, and the actual launched command. Raised-budget `--no-run` reads zero normal-budget cells.

The queue should run these six behavior gates before pending draft/tuning rounds, without interrupting active jobs. They share reference results only within a matching budget and retain the normal sequential gate interpretation: high-H0 alone is not rejection, and narrow results require judgment. There is no strength conclusion or promotion at preparation time.

## Preparation validation

All three release builds passed. Four maps (`00ambush`, `00breadcrumbs`, `00great-wall`, `00lanes`), both sides against frozen `spar-dvn1-Mt3q`, cover base plus three arms at both budgets: **64 successful games, zero errors, early losses or draft handoff failures**, and identical ordered drafts for every arm/reference cell. The first fixture used replay-normalized `00great_wall` rather than the real `00great-wall` filename; those failed jobs played no games and are excluded. Corrected fixtures passed before queue admission.

All 64 extracted replays pass hard validation. The smoke confirms actual mechanisms: bush-only produces 599/599 bush wards at normal fuel and 617/617 at doubled fuel; camp-watch produces 301/274 camp wards versus base46/42. At doubled fuel, exact tile ranking's first differing event is a different ward destination in four cells, and the other four cells are identical; normal fuel also exhibits earlier fuel-sensitive trajectory changes. The replay checks are in artifact `mechanism.json`, with first divergences and source replay paths.

Normal-budget candidate out-of-fuel turns across the eight games are base34, tile33, camp37, bush45. All are zero at doubled fuel (both teams). These are a mechanism smoke, not a cost benchmark or a win-rate estimate: altered trajectories change both game length and workload. Fresh gates determine usefulness.

`queue-commands.json` in the artifact directory names the six wrapper commands; queue operations owns admission and ongoing execution. The wrapper checks the sealed base/arm hashes on every start. Neither opponent pinning nor live submission selection is part of these experiments.
