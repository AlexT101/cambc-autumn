# Completed null114: small net changes conceal many flipped games

V114 completed **104/104 normal groups** on 2026-11-11, with the final collection at **02:32:08 UTC**. Compared with v98 on the same historical opponent snapshots, it changed **57 of 512 winners (11.13%)**, while its combined net was only −1 win. This supports treating small live leads cautiously; it does not measure the variance of rerunning identical binaries.

## Matched results

Every opponent row contains **256 unique map/side cells on all 128 ladder maps, both sides**. Map IDs, sides, opponent IDs, reference labels and source groups, seeds, and engine/build metadata match in every pair. No external-context mismatch was excluded. Opponent-detector groups, suspect groups and deterministic filler repeats are excluded.

The difference is v114 minus v98. Intervals are descriptive 95% normal intervals over map means, with both sides clustered together.

| Opponent snapshot | v114 / v98 wins | Favorable / adverse flips | Net wins | Difference, points | 95% map-cluster interval |
|---|---:|---:|---:|---:|---:|
| Fish r2 | 162 / 164 | 13 / 15 | −2 | −0.78 | [−4.85, +3.28] |
| Mite r3 | 157 / 156 | 15 / 14 | +1 | +0.39 | [−3.60, +4.38] |

Both intervals include zero. These small fixed ladder panels do not establish either a strength gain or a precise universal null-noise distribution. Their net differences can hide considerable changes to individual outcomes.

## What this control changed

V114 is the preserved `v87-null-a` arm against `v87-reup` (v98). The exact archived platform sources differ in only:

- `main.cc`: a volatile 24-iteration loop at each play-turn entry, consuming fuel;
- `model/prio_stream.h`: the current priority mask instead of v98's historical mask.

All other source files and all platform SDK files match. The archived release WASMs are hashed in the evidence proof. This is therefore a **combined burn-and-mask perturbation diagnostic**, not an isolated fuel-burn estimate, identical-source repeat, or test of current Ocean 506. Fuel consumption can alter behavior at budget boundaries, and the two changes cannot be attributed separately here.

Fish uses the same r2 source group in both versions; Mite uses the historical r3 source `01a1bf36-e601-756a-8b37-a90ad3d84ae0` in both. The current Mite snapshot and subsequent repinning decision play no role in this comparison.

## Other changes and limits

Neither our ordered draft nor the opponent's ordered draft changed in any paired cell. Draft equality was **not** an admission condition: drafts are post-treatment outcomes, and differences would have been retained and reported.

All recorded score/timing fields agree in **123/256 Fish cells** and **129/256 Mite cells**: **252/512 overall**. Thus the near-zero net is not broad behavioral identity. Raw replay bytes were not compared. A zero-width interval from a no-flip sample would not establish zero variance; this sample itself has substantial flips and nondegenerate intervals. The saved report additionally provides a conservative bounded interval under an independent-map approximation, without claiming that the fixed ladder maps form a random sample of all future games.

No strength promotion, merge, extra games, queue changes or repin follows from this readout. Local shipping evidence remains necessary.

Reproducible read-only analysis and exact inputs/provenance: `~/tmp-offload/handoff/codex/live-analysis/null114/{analyze.py,matched-inputs.json,evidence-proof.json,report.json}`. The analysis reuses the completed-v113 map-cluster auditor, explicitly removes draft equality from external-context matching, validates all 104 completed/non-suspect groups, and verifies the historical pins and platform source differences. Operations' completion proof is `~/tmp-offload/live20h-plan-20261111/v114-completion-throughput.json`.

Saved matched-input SHA256: `a9712762f733f7b716c5cd7d7cb5d0fe90deb908bd94974af3d040e875fc7789`.
