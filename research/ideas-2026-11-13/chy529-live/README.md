# Charybdis 529: full live ladder comparison

Completed outcomes on 2026-11-13. Uploaded **v129**, frozen Charybdis 529 at `bbc7cddb6`, compared with **v128**, Charybdis 525 + fuel 01-02. Both are unmasked and book-free, using their own drafts. Candidate uploaded source matches the frozen commit byte for byte.

| Opponent | 529 wins | v128 wins | Net wins | Paired flips for / against |
|---|---:|---:|---:|---:|
| Fish r8 | 194/340 (57.1%) | 197/340 (57.9%) | -3 | 56 / 59 |
| Mite r13 | 226/340 (66.5%) | 204/340 (60.0%) | +22 | 65 / 43 |
| Total | 420/680 (61.8%) | 401/680 (59.0%) | +19 | 121 / 102 |

The gain is concentrated against this Mite pin; Fish is essentially level. The overall gain is 2.8 percentage points on this full ladder sample. Early partial results should not replace this completed comparison.

All **170 ladder maps, both sides, both opponents** were covered exactly once: 680 unique cells in 136 five-game groups, no fillers, dropped groups, or suspect groups. Every candidate create bound live=selected=v129. Both versions use the same actual opponent source groups:

- Fish r8: `01a1d01f-2b0c-7df1-8dfe-43830d22b20b`
- Mite r13: `01a1d598-e831-779c-b788-7710ca8d3f9a`

The Mite baseline's capture group is itself the pin; its absent source_group is expected and was checked against the reference group ID. This is not the scheduler's default v118 comparison.

[results.json](results.json) contains every paired cell, baseline match ID, candidate group/position, source pin, and source digest. Outcomes come from all completed-match records; downloaded rows were cross-checked where available. Full replay collection remains enabled for all v129 games and continues independently after outcomes finish. The JSON records collection progress at audit time rather than claiming every replay was already downloaded.
