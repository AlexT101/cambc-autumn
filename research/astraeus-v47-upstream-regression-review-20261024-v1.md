# Latest Astraeus / upstream v47: bounded regression review

2026-10-24. **The newly fetched commits introduce no Astraeus source or draft change. Existing evidence does not establish that the latest Willow Astraeus regressed, but does not establish an improvement either.** This is a source/text review, with no builds, games, replay decoding, canonical edits or submission. Live artifact attribution is a separate root investigation.

## Identity and draft

`origin/main=dc9867a95029a90e84366ebd1a79794a164e9947` has two commits after `f7d54e9`:

- `88b8c3c`: regenerates `gen` and `gen-s1` from seeds 1023/1024 to 1025/1026; adds per-rank scrim group counts. No bot source change.
- `dc9867a`: freezes `bots/baselines/v47` and removes two older upstream baselines. Its message calls this “astraeus f7d54e9, the live submission.” This is explicit upstream attribution, not independent proof of the server's uploaded bytes/version.

Verified Git source-tree identity: `f7d54e9:bots/astraeus/src`, `dc9867a:bots/astraeus/src` and `dc9867a:bots/baselines/v47/src` all equal **`f311d05a87d7ea04e79ca55f9bc295232a57032b`**. This is our already-reviewed f7 source (local frozen aggregate `f475b8521cada611754076822402a266c43be8de76ce0f2b504b268ff3335824`), not a new implementation at dc9867a.

`params.h` has `test_draft=false`, `willow_draft=true`. Normal ordered drafts are:

| Picks | Ordered champions |
|---|---|
| 3 | Prism, Vesper Vale, Heart of Ruin |
| 4 | Prism, Vesper Vale, Marcella, Heart of Ruin |
| 5 | Prism, Vesper Vale, Marcella, Willow, Heart of Ruin |

`draft.cpp`, `draft_selection.h` and `params.h` are unchanged since Astraeus's initial `8d240cc` import. Compared with upstream v44, the only selection difference is the new configurable flag, which is true: effective own drafts are identical. Hyperion's five-pick alternative uses Ryth/Vendetta instead of Willow; its three/four-pick rosters match. No normal path here drafts Willow first. Earlier anomalous live batches cannot be assigned to this upload from draft appearance or timing alone.

## What the reported comparisons actually test

Upstream `dc9867a:research/EXPERIMENTS.md:296–333` contains no new test result after f7. These are reports, not independently pinned executable/run receipts:

| Compared source change | Reported scope/result | Interpretation |
|---|---|---|
| Earlier Astraeus315910d vs Hyperion c71 | Own drafts, 1104 games: Willow on 50.1%, off 49.9%; both five-pick totals49.8% | Approximately level. Willow-on versus Hyperion changes both support source and five-pick composition. The two settings were compared to a common opponent, not directly to each other. |
| Earlier Astraeus315910d vs v44 | Same effective own drafts for Willow-on:52.8%/1104, CI49.9–55.7; five-pick53.6% | Best broad source-matched historical evidence, but not latest f7 and not a decisive gain. v44's source identity equals our released Khaos_v33/a00fff, per `astraeus-source-identity-20261024-v1.json`. |
| de55 fuel cuts vs e727 | Own-draft wide bench52/52 identical, fuel−1.54% | Cost-only stage; does not imply complete cb61/f7 behavior identity. |
| 4217 logic fixes vs de55 | Five-pick422 games53.6%; fresh seed1031 178games46.6%; pooled51.5% | Mixed suite direction, pooled level. Neither a clean regression finding nor a demonstrated benefit. |
| Latest four-line Prism change vs cb61 | Five-pick600 games49.5%, CI45.5–53.5; OOF3421/3441 | Closest incremental check of f7: level. Wide bench52/52 identical, but31 branch entries found zero attack targets, so it did not validate successful attacks. |

Our own frozen cb61 control scored57–55 against released v33 on112 physical-side cells. This includes all40 published maps plus selected generated cells, with reused mechanism witnesses; it is not an independent full-suite estimate or a latest-f7 regression comparison. Our earlier4db result524–580/1104 concerns a different source and must not be relabeled Astraeus/v47. The local service/Gold/route candidates are absent from v47; their changes/outcomes cannot explain its live performance.

Map identity matters now: upstream's regenerated `gen`/`gen-s1` names no longer identify the same test inputs as the old1104 panel. Nor are results against different opponent uploads, side mixes or pick counts an isolated source comparison. Historical OOF totals also varied on repeated upstream runs, so their exact differences lack the determinism/pinning guarantees of our frozen ledgers.

## Source-specific mechanisms to distinguish if a live deficit is confirmed

1. **Latest f7 only:** `bot.cpp:4833–4836` lets a stationary recovering Prism attack an enemy, otherwise a camp whose entire group has no strength. There is no new draft/Willow decision change. A successful basic may have a retaliation consequence (notably Ren), or its queries may shift a marginal fuel boundary. The no-target bench leaves successful-attack behavior unexercised. Nominate this only when a changed loss actually enters this branch and attacks or runs out there; ordinary Willow formation failures are not evidence against these four lines.
2. **cb61 readiness/geometry:** `heal_ready` now recognizes a future allied heal despite the routine turn-end recall; heal viewers admit current-tile/own-ward vision; Prism recovery uses the actual spawn field. These can change where/how long Prism waits and can construct a cold route field. A ready heal is still an opportunity, not guaranteed service. A source-known first divergence showing extra recovery delay with no delivered heal/productive work would justify investigating readiness/turn-order/support availability; a cold-field rollover would motivate cost work. Both remain hypotheses, not discovered defects. Keep visibility correctness while testing timing/value.
3. **Older Astraeus refactor versus v44:** Willow's threat-driven ordinary retreat replaces its custom escape/economy path; search heal value is capped by predicted recipient damage; support walks use partial re-observation. These can alter useful service, exposure and farm conversion even with identical drafts. The strongest witness would be lost service/work at the first matched decision with then-visible ally needs and enemy threats. Whole-game healing or final deaths cannot isolate these branches.

Existing Band route oscillation, mixed-map Monolith exclusion and the source-known Gold farm/retreat reversal remain inherited weaknesses, not newly proved regressions. The Gold initiative-boundary explanation was explicitly falsified in its corrected note; do not revive it here. There is no basis for a blanket Willow rollback, for applying the local shopper arms, or for treating old random-looking drafts as this source.

The next decision depends first on the uploaded-source/version match and what release it should beat. If those match f7/v47 and v44/a00fff, use their unchanged own drafts and exact common map/side cells to distinguish a source regression from a changed live opponent mix. For a suspected latest increment specifically, cb61 versus f7 is the clean boundary; the new dc9867a commit is not one.

## Fresh ranked metadata: 05:50 UTC follow-up

**User clarification supersedes the earlier anomaly investigation:** the Willow-first batches are ladder manipulation and are excluded from this regression question. Do not investigate their source, randomization or fallback further. The four selected normal five-pick replays below are unchanged; their uploaded-source versions still remain unknown.

Evidence: `provenance/astraeus-regression-history-intake-20261024-v1/{REPORT.md,summary.json}`. The pinned CLI exposes no submission ID/version, so these are observed drafts and outcomes, not a source-version cohort. Root additionally verified all v44 source files against `bots/baselines/hyperion-deployed-v33-a00fff/src`; v44 means authored Khaos_v33 / server44 / a00fff here.

After the prior03:40:12.979 cutoff, the60 new ranked games go26–34. Willow-first drafts account for9–21/30; normal Prism-first drafts17–13/30. Restricting further to the actual five-pick roster `[5,1,6,7,11]`, the latest window is **14–11/25 (56%)**, versus **18–8/26 (69.2%)** in the earlier portion of the newest100. Thus the lower recent score is not entirely explained by the Willow-first batches, but the normal-roster comparison is small and unmatched: prior A13/18,B5/8 versus latest A4/9,B10/16, with different opponent and map mixtures. It does not establish a latest-source regression. The newest normal five-pick groups include both losses and wins, including Fish Boss Battle and a three-win Claudus five-pick set.

Seven current exact-cell matches share opponent UUID, map, side and both ordered drafts with saved history. All seven current rows are normal five-pick losses: three cells previously won and four previously lost. The report's five `loss→loss` transitions count one cell's two earlier losses, so there are eight prior/current comparisons, not eight distinct current cells. Exact drafts control composition, not either team's executable.

### Bounded replay selection (four total; pending root/runtime authorization)

| Pair | Earlier win | Current loss | Fixed inputs / initial actors |
|---|---|---|---|
| Fish, Elkring B | `67fc71af-7d66-40e8-8c82-a0d400cbea6f`,02:10 | `deb4ae94-edc6-480f-a0e9-03fd944841bd`,05:40 | Own `[5,1,6,7,11]`, opponent `[1,2,11,3,0]`; own Prism5 / Willow8 |
| :3, Pilgrimage A | `9da66955-6268-428c-a955-1549cd080c33`,03:30 | `62589f4b-d504-4bf7-b641-f3e9de95ce9c`,05:30 | Own `[5,1,6,7,11]`, opponent `[11,5,0,1,6]`; own Prism0 / Willow3 |

These supply normal-roster loss/win controls on two opponents, while controlling both drafts and physical side. Prefer these pairs to four unrelated losses. Fish Gem Fields is another exact win→loss cell but duplicates the same opponent/time group and is lower priority for this bounded workload.

Metadata cannot identify an honest decisive round. First use compact accepted actions, native status and capture/death chronology from the selected four only; compare sequences per actor, ignoring absolute step indices and benign actor interleaving. Locate the earliest persistent movement/attack/service difference or rollover and determine whether our or the opponent's policy differs first. Then request at most nine-round actor-known windows around that seam, initially Prism/Willow if involved, otherwise the actual diverging actor. Read visibility, cooldowns, own/ally HP, live camp/hold state and delivered service/work. A global capture/death nominates a window; it is not information the actor necessarily had. A first divergence is also not automatically the decision that caused the final loss. No extraction was started by this review.

### Archived anomalous draft source check — superseded by user clarification

Preserved as the earlier source check, not an active hypothesis or work request: current normal draft code does not configure `[7,…]`. `test_draft=false`; its test tables have no Willow-first row, and the only Willow test row puts her fifth. The earlier prefix audit did not establish bot-call provenance. The user has now identified these batches as ladder manipulation and instructed us to ignore them; no further random/fallback or source-identity investigation is needed for them.
