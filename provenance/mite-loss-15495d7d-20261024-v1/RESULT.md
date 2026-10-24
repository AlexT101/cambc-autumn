# Mite replay fetch — 15495d7d

The requested finished loss could not be downloaded: both CLI attempts returned HTTP 429 (“Public API is busy”). The failed attempts and duty-cycle receipts are preserved. No replay file was produced, so no extraction or match-economy interpretation is available.

The exact target row is present in the saved latest-30 metadata page: created 2026-10-24 10:11:10.276 UTC, finished 10:14:18.950 UTC, `00road_of_riches` (road of riches), position 3, Mite physical A loss vs `:3` physical B. Ordered drafts are Mite `[1, 2, 0, 10, 6]` and `:3` `[11, 2, 1, 6, 0]`; both report engine 1.0.3. No submission identity is inferred.

See `preflight.json`, `RESULT.json`, and `PRESERVATION-MANIFEST.json`. No additional API calls were made after the two HTTP 429 responses.