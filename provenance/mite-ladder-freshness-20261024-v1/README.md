# Mite ladder metadata freshness

Root refreshed 30 match-history rows through the CLI. The saved metadata file has filesystem mtime 2026-10-24 10:16:17.892224 UTC; treat that as an approximate local save time, not a server timestamp. The exact source bytes and SHA-256 are pinned in `PRESERVATION-MANIFEST.json`.

The response contains 25 finished matches (21 wins, 4 losses) and 5 queued matches, spanning three numeric draft profiles. The queue is still pending in this snapshot. No replay was downloaded.

The raw match rows identify a Mite team ID, but this metadata does not establish which source submission produced those games. No submission version or source identity is inferred. A possible next step, only after authorization, is to choose one finished loss by match ID and inspect that one replay.
