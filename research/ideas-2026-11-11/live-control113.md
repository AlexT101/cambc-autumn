# Completed v113 control: conditional policies remain unresolved live

V113 completed all **104 normal groups**, last collected at **2026-11-11 00:26:59 UTC** and recorded complete by the scheduler at **00:27:56**. It won **164/256 against Fish r2 (64.06%)** and **160/256 against Mite r5 (62.50%)**. Opponent-detector groups, suspect groups and deterministic filler repeats are excluded.

V113 is the historical v105 `live-wd-fsnh` behavior rebuilt with the current priority mask. It is **not current Ocean 506**. The submitted workspaces differ only in `model/prio_stream.h`, and their SDK files match. V108, v109, v111 and v112 use the same mask and SDK as v113.

## Matched feature comparisons

The difference is the named arm minus v113. Every row contains **256 matched map/side cells on 128 maps**, both sides. Map IDs, opponent/pin/source group, ordered drafts, seeds and engine/build metadata match in every pair; no context mismatch was excluded. The ± value is a descriptive 95% normal half-width with maps as clusters.

| Arm versus v113 | Opponent | Arm/control wins | Flips for/against | Net wins | Difference, points |
|---|---|---:|---:|---:|---:|
| **v112: channel + carry-follow + Greed** | Fish | 177 / 164 | 43 / 30 | +13 | **+5.08 ± 6.95** |
| **v112: channel + carry-follow + Greed** | Mite | 159 / 160 | 33 / 34 | −1 | **−0.39 ± 6.66** |
| v108: Mite channel conditional | Fish | 174 / 164 | 35 / 25 | +10 | +3.91 ± 6.30 |
| v108: Mite channel conditional | Mite | 157 / 160 | 34 / 37 | −3 | −1.17 ± 6.56 |
| v109: Fish carry-follow conditional | Fish | 176 / 164 | 42 / 30 | +12 | +4.69 ± 7.08 |
| v109: Fish carry-follow conditional | Mite | 161 / 160 | 29 / 28 | +1 | +0.39 ± 5.60 |
| v111: Greed | Fish | 160 / 164 | 2 / 6 | −4 | −1.56 ± 2.16 |
| v111: Greed | Mite | 160 / 160 | 2 / 2 | 0 | 0.00 ± 1.54 |

**Every interval includes zero.** The Fish leads from the conditional arm/bundle remain unresolved; the complete same-mask control does not establish a live gain. V108/v109 include classifier infrastructure as well as the conditional policy, so these are submitted-arm comparisons, not an isolated classifier or individual branch effect. V111 differs only in `economy/shop.cc`; the bundle differs in eleven source files and does not identify the contributions of its three policies.

## Same-behavior mask-context comparison

V113 versus v105 has **no winner flips** on all 336 comparable cells: Fish r2 **164 versus 164 wins in 256 cells**, and Mite r5 **42 versus 42 in 80 cells**. V105's other Mite cells use r4 and are not pooled with r5. The paired win difference is zero in this observed sample; a degenerate zero-width normal interval would not establish general safety or zero variance.

Full score/timing fingerprints agree in **333/336** cells. Three have different rounds, gems, gold and kills despite the same winner. Raw replay bytes were not compared. This therefore does not establish whole-replay identity or prove that every mask rebuild is behaviorally irrelevant.

## Interpretation and evidence

These are small, reused deterministic live suites and several descriptive comparisons, without multiplicity-adjusted claims. No live-only merge follows. The prospective current-base local tests, including off-target and Ocean mirror checks, remain the shipping evidence. This readout creates no additional games, queue changes or repin.

The analysis refuses a partial/dropped/suspect v113 gate and validates created-group live/selected version before reading outcomes. Its calculations reproduced all eight saved v112 comparison counts, flips and map-cluster intervals before v113 finished. Exact saved rows, source/SDK hashes, completed-group proof and reproducible analysis are in `~/tmp-offload/handoff/codex/live-analysis/control113/{analyze.py,matched-inputs.json,evidence-proof.json,report.json,same-behavior-score-audit.json}`. Saved input SHA256: `952a633462cf8a93d4ba6642da30daca5f227a3083a8899c34ea6edcde0a1833`. Operations' terminal proof is `~/tmp-offload/handoff/codex/queue-ops/resume-501/v113-completion-throughput.json`.
