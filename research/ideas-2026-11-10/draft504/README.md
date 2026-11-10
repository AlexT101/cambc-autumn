# Draft17: one Ocean 506 refit and two opponent-preference ablations

The user explicitly authorized one draft lab followed by tuning, then requested recent Fish/Mite-informed nudges and a separate overall pick-rate ablation. This remains **one 800,000-game collection**. Preparation is held until independent review; no automatic lab refill, merge or live submission follows.

The frozen base is `variants/oc-dfuel-506`, commit `183a1295c335a83d03679f93fcb11cdbde5617b2`. Before first heavy work, both committed Ocean and the queue's base policy must match it. A started experiment stays frozen. The directory name `draft504` is historical.

## Collection and three approaches

Collection keeps the previous approved design: 100k fuel, native release cambc 5.0.1, 799k–800k games within 18 hours; F25-guided exploration; exact shipped draft10 F92 sampler; no champion locks. Local opponent shares remain Fish Flp4 .3, Mite Mt3q .3, Ocean mirror .2, frozen astraeus/proteus .1 each. The historical top-eight composition prior is unchanged, so changing our own preference is not confounded with changing the opponent distribution. No old training games are pooled.

The control is the original F92 refit with one search of `w,dev` penalties. Two fixed directions augment that refit:

- **Flat:** one overall champion-inclusion vector, across all maps **and pick counts**. The same intercept direction applies to 3, 4 and 5 picks; all map coefficients are zero.
- **Conditional:** three pick-count offsets plus shared slopes on the existing first 25 F92 features. Strong ridge values 16/64/256 are compared on five map-grouped folds of archive drafts only; a tie chooses the strongest ridge. No game outcome selects this prior.

[The preference protocol](preference-proposal.md) specifies provenance, weighting, calibration and limits. All arms share the collection; there is no grid of behavior strengths. Zero slopes alias control, and identical exported headers share one candidate and its games.

## Fixed evaluation

All fixed panels contain exactly 1,024 fresh maps after byte deduplication. Training uses seeds 2412000–2412099 (at least 24,000 retained maps). All panels are disjoint from training, one another, the 128 ladder maps, the standard fresh-gate pool and old draft10 training maps. Predetermined replacement seeds fill collisions before outcomes exist; exhaustion holds for review.

| Stage | Fuel | Primary seeds | Replacement seeds | Noise blocks | Maximum fresh games |
|---|---:|---|---|---|---:|
| Selection: 3 approaches + 506 | 200k | 2412910–13 | 2412914–19 | 1–64 | 131,072 |
| Confirmation: selected + control + 506 | 200k | 2412920–23 | 2412924–29 | 65–192 | 196,608 |
| Separately admitted normal confirmation | 100k | 2412900–03 | 2412904–09 | 193–320 | 196,608 |

Every map plays both sides against fixed Flp4/Mt3q. Repeated noise realizations are averaged **within each map**, together with sides and opponents. The interval uses map-level sample standard deviation (`ddof=1`), divided by sqrt(1,024), and z=1.96. Opponent and pick-count readouts are descriptive. No interim outcome stops or decisions occur.

Selection makes two one-sided comparisons against control, Bonferroni family alpha .05. A nudge qualifies only if its lower bound is positive. Choose the qualifying arm with the greatest mean; an exact tie favors flat. If neither qualifies, retain control. Confirmation then tests the frozen choice against 506 and, for a nudge, against unnudged control, on untouched maps and new noise blocks. Every required lower bound must be positive; control alone retains conservative z=1.96. Selection evidence is never pooled into confirmation.

The 128 ladder maps are diagnostic only. Run them once at 200k (noise 1) for all distinct approaches and 506, then reuse those cells for the confirmation report. A normal-fuel run uses new 100k diagnostic cells at noise 193. Archive priors already saw these ladder maps, so they cannot establish generalization.

After 200k confirmation, write `review-required.json`. A normal run requires a coordinator admission binding the manifest, positive confirmation result, selected arm and its source hash. It uses the exact frozen winner. Only the coordinator may eventually create `draft17-reviewdone`; tune8 remains behind that decision.

## Source, fuel and resources

Each candidate changes only `draft/draft_model.h`. Require native key/team parity, a release build, and first-turn measurements without missing, unfinished, capped or over-10M drafts before games. Audit exact map/side coverage, source identity, release/engine/fuel metadata and body sources before each evaluated block. Recheck candidate sources before publishing a stage result. Failed or incomplete child processes fail closed for recovery review.

The shared pool has 86 slots: training games at most 64 workers, F92/OOF fitting 24, planning 12, readers 8. Fixed evaluation uses four AB controllers sharing the same aggregate 86-slot pool. Prior fits, scalar calibration, source generation and release builds reserve their CPU slots; builds explicitly use serial compiler settings. Each evaluation phase uses the standard compile-ahead helper with 16 process workers/eight future blocks; no warm games. It drains on phase exit. `CAMBC_COMPILE_AHEAD=0` disables it. Training and preference fitting do not start that helper.

## Commands and artifacts

`python3 research/ideas-2026-11-10/draft504/run.py --check` performs sealed preparation checks only. The same command without `--check` requires localq admission. A normal confirmation additionally requires `--normal-admission /absolute/path/to/admission.json`.

Artifacts live in `~/tmp-offload/localq/rounds/draft17/`: sealed protocol/config/manifest and inputs; selected maps; training/F92 data; five-fold OOF provenance; preference directions and calibrated slopes; distinct candidate sources; first-turn/parity checks; block audits; `selection.json`, `confirmation.json`, optional `normal.json`, and the review marker. Original preparation artifacts remain under `preference-amendment-before/`.
