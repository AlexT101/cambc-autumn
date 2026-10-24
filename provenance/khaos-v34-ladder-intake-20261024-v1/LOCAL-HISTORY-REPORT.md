# Local saved-history inventory for the v48 review

Built from existing CLI list JSON only; no API call or replay download was used for this merge. All five inputs and SHA-256 pins are in `local-history-merge.json`. Rows are deduplicated by match UUID. The current list schema does not expose uploaded bot version, so timestamps define only provisional cohorts.

## Submission boundary
Khaos_v34 / server version 48 was submitted at 2026-10-24 10:17:24 UTC. One bounded latest-ranked-30 refresh succeeded at 10:48:39Z after earlier latest-100 failures. The match-list payload does not expose submission ID or bot version, so rows after the submission time are provisional post-submit observations; do not identify them as confirmed version-48 matches.

## Deduplicated local sample
- Unique own-team rows: 310 across ranked and unranked snapshots. The ranked-only deduplicated history has 160 finished rows, 78–82.
- Excluding own ordered first pick 7 leaves 125 ranked finished rows, 69–56; first-pick-7 ranked rows excluded: 35, 9–26.
- Ranked eligible pre-cutoff: 110, 64–46. Provisional post-cutoff: 15, 5–10. The immediately preceding 15 are 7–8. All latest-30 rows are non-Willow-first; latest-30 record is 12–18. Latest 30 by opponent: Prism best girl 1–4, Claudus Maximus 0–5, Mite 4–1.
- One exact map × opponent × side cell is represented pre/post: Fracture vs Claudus Maximus, our side B, one loss each. Other cells have small samples. Matrices: `ranked-map-opponent-side.csv` and `eligible-map-opponent-side.csv`.

## Metadata-only replay candidates for root review
These are suggestions to choose from before any replay retrieval. The metadata cannot establish a fight, retreat, gem-carry or source-version mechanism.

- `deb4ae94-edc6-480f-a0e9-03fd944841bd` — ranked 00elkring, own side b, loss; created 2026-10-24T05:40:14.912Z, finished 2026-10-24T05:40:32.516Z; our picks [5, 1, 6, 7, 11], opponent Intercontinental Fish (`1890540d-1ffc-4847-adbf-d0d08772f268`) picks [1, 2, 11, 3, 0].
- `62589f4b-d504-4bf7-b641-f3e9de95ce9c` — ranked 00pilgrimage, own side a, loss; created 2026-10-24T05:30:14.849Z, finished 2026-10-24T05:30:32.074Z; our picks [5, 1, 6, 7, 11], opponent :3 (`bbe481a7-4575-4826-9a3e-f81c28205de8`) picks [11, 5, 0, 1, 6].
- `da1f5b4e-b98d-4cdf-a2d4-c74e33da360a` — ranked 00elkring, own side b, loss; created 2026-10-24T05:00:16.632Z, finished 2026-10-24T05:00:34.508Z; our picks [5, 1, 6, 7, 11], opponent Univardisty of Shingtonwash (`a4350547-b7a1-47b1-9031-4f7f084ad0d8`) picks [6, 9, 11, 2, 5].

Rationale: `deb4…` is the newest saved eligible loss and a normal Prism-first five-pick draft; `62589…` is a recent :3 Pilgrimage A loss in the same normal draft family; `da1f…` participates in a repeated exact map/opponent/side/draft loss cell against Univardisty (older counterpart `c2d68c52-2ab4-4e94-9650-5e0f31f8e8ec`). These are all pre-submission and are candidates for general macro diagnosis only.

The ranked-latest100 requests returned HTTP 429 and then HTTP 503; see their raw logs and duty receipts. The single allowed latest-30 request later succeeded; no more metadata fetches were made. Two root-selected post-submit replay bundles were downloaded and summarized in `MACRO-RESULT.md`/`MACRO-RESULT.json`; their exact source version remains unknown.
