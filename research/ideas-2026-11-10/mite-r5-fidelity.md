# Mite r5 versus the local Mt3q body, 2026-11-10

The existing body underestimates Mite's early capture income even when both teams'
ordered drafts match. This is an investigation, not a body replacement or a
promotion. Warding became the user's next primary scope before any body arm was
built. Existing body/cache identities and live opponent pins remain untouched.

## Cohorts and checks

- Direct change comparison: 80 map/side cells, our fixed v105 against Mite r4
  (04:11–04:29 UTC) and r5 (06:10–06:29 UTC), downloaded scrims only. Both teams'
  ordered drafts match in all 80. Six pairs have byte-identical replays; 74 differ.
- Local comparator: the same 80 map/side cells from the existing 256-game
  `mre-base-Mt3q-ladder` run, ocean-16d6f78 versus spar-dvn1-Mt3q. Our ordered
  drafts match all 80, Mite's only 37. Mt3q deliberately samples a feature-based
  composition model fitted to historical scrim mixtures: this mismatch does not
  establish a new r4→r5 draft change, nor a simple model bug.
- The local allied bot predates v105, so even the 37 exact-draft cells are
  descriptive fidelity evidence, not an isolated causal body comparison.
- `tools/replay/extract.mjs` decoded 160 live inputs (154 distinct replays) under
  `tools/pooled.py`. All 160 decoded final gem totals and outcomes match the saved
  platform summaries. No hard extraction failures. Soft earned-gold diagnostics
  omit Marcella's tribute income; earned totals here use snapshots, not that sum.

## Current versus previous Mite

Our wins fall 49→42/80; flips are +10/-17, inconclusive for strength. Mite's early
income barely changes: mean earned gold at r300 is 1726→1744. Mite's own deaths
fall 7.65→6.98 per game and ours rise 5.55→6.43; the latter's approximate
map-cluster 95% interval for the change is -0.01 to +1.76 deaths/game. Those are
leads, not established mechanisms.

First observed action divergence is in round 1 for 17 cells, rounds 2–20 for 38,
rounds 21–100 for 14, and later for five. Movement/dash choices dominate. Thus a
late item-build-only explanation is insufficient. This event-prefix comparison
ignores input-step indices; skipped actions can make the first unequal event
belong to the other team, so it is not a causal first-instruction trace.

## Camp selection remains the clearest body gap

On the **37 cells with both ordered drafts identical**, by round 300:

| Mite-side quantity | Live r5 | Mt3q |
|---|---:|---:|
| Capture gold per game (observed payouts) | 1285.6 | 1039.3 |
| Captures per game | 21.27 | 20.41 |
| Base camp gold per game (actual camp types) | 1102.7 | 893.2 |
| Base gold per capture | 51.84 | 43.77 |
| Observed payout / base gold | 1.166 | 1.164 |
| Wolf-containing group captures per game | 8.19 | 6.65 |
| Elk-containing group captures per game | 2.30 | 1.65 |
| Pure gem-cluster group captures per game | 6.27 | 7.68 |
| Pure gold-cluster group captures per game | 4.41 | 4.35 |

The +246 capture-gold gap comes mostly from wolf and elk groups (+177 and +70
observed gold/game). Pure gold-cluster income is slightly lower in real Mite.
This supports investigating monster-versus-gem-cluster farm selection, rather than
assuming richer Vesper/Prospector bonuses or adding more gold-cluster preference.
It does not yet establish which decision rule causes the difference or whether
copying it into ocean would win. Earlier emblem/cohesion/body banking attempts
already failed to close the strength gap; see `../ideas-2026-11-09/oppmodel/mite.md`.

## Extractor metadata correction

The initial decomposition used decoded `map.groups[].gold`. That is unreliable:
57 of 868 groups in these 40 maps disagree with the sum of actual camp types.
For example, 00quarry group 10 contains two Gem clusters but the extractor labels
it 40 gold; observed captures pay zero gold. `buildMap()` associates an engine
group with source-map metadata via its first camp index. This is an extractor
metadata issue, not a contradiction of the engine-verified game rules.

Corrected figures above sum the actual decoded camp types using
`cambc-rules.yaml` rewards. Observed capture totals, draft matching and action
comparisons never depended on the copied reward metadata. The correction is
small on the exact-draft aggregate and leaves the camp-choice conclusion intact.
No shared extractor or pre-existing caches were modified during this study.

## Reproduction and evidence

Artifacts: `~/tmp-offload/mite-r5-fidelity/`:
`prepare.py`, `live-cells.json`, `manifest.tsv`, raw and decoded replays;
`analyze.py`, corrected `features.json` and `report.md`; `diverge.py` and
`first-divergences.json`; `camp_mix.py`, `camp-mix.json` and
`camp-mix-corrected.log`. The initial calculation is retained separately as
`features-original-group-metadata.json`. Heavy analysis ran locally through
`tools/pooled.py`; no new scrims, repins, body edits or cache-name reuse occurred.
