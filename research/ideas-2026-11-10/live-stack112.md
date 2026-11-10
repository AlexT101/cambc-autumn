# Live v112: conditional channel, carry-follow and Greed bundle

Completed all 104 groups at 2026-11-10 22:52:08 UTC against unchanged testing pins Fish r2 and Mite r5. There are 512 valid unique map/side cells after excluding filler repeats and opponent-detection probes.

| Opponent | Wins | Win rate |
| --- | ---: | ---: |
| Intercontinental Fish | 177 / 256 | 69.14% |
| Mite | 159 / 256 | 62.11% |

These are results for the historical `live-wd-fsnh` feature branch, not current Ocean 506. The bundle adds Mite-only channel ordering, Fish-only carry-follow and Greed to that branch.

## Matched comparisons

Differences are v112 minus the reference, in percentage points. Uncertainty is a descriptive 95% normal interval half-width using maps as clusters; both sides share a map. Map IDs, sides, opponents, ordered drafts, seeds and engine/build metadata match in every included pair.

| Reference | Fish difference | Mite difference | Qualification |
| --- | ---: | ---: | --- |
| v105 baseline | +5.08 ± 6.95 (256 cells) | 0.00 ± 12.16 (80 cells) | Different priority mask; only 80 Mite cells share r5 |
| v108 channel-only | +1.17 ± 5.27 | +0.78 ± 2.66 | Same mask; adds carry-follow and Greed |
| v109 carry-follow-only | +0.39 ± 2.30 | −0.78 ± 6.34 | Same mask; adds channel ordering and Greed |
| v111 Greed-only | +6.64 ± 6.73 | −0.39 ± 6.48 | Same mask; adds both conditional policies |

All comparisons except the specified v105 Mite subset contain 256 cells per opponent. These comparisons do not isolate an individual policy or establish an additional benefit from combining the policies. No merge follows this result. The already-submitted v113 current-mask v105 control will provide a fuller baseline comparison; prospective local conditional tests remain the shipping evidence.

Saved input rows and calculations: `~/tmp-offload/handoff/codex/live-analysis/stack112/{matched-inputs,report}.json`. Input SHA-256: `bf90e5f2a570c96c37e7835f46fb4c9f4ccfc35bdda2a212b434a84738d9e97f`.
