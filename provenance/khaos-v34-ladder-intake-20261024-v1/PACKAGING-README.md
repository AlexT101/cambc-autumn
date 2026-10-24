# Selective preservation snapshot

`PRESERVATION-INVENTORY-<timestamp>.json` records every file under this intake directory as either a review staging candidate or local-only, with byte size and SHA-256. `STAGING-CANDIDATES-<timestamp>.txt` is the explicit review list for root; it does not stage or modify Git. Regenerate with `python3 package_snapshot.py` after new artifacts arrive. Older snapshots are retained and marked superseded.

The staging list includes compact plans/results, summaries, native audit receipts, build and source pins, small source patches and tooling, validated trace summaries, and the corrected economy inventory/fixtures. Raw replay files, WASM, ZIPs, full match statistics, raw input dumps, logs, oversized files, and auth/login paths remain local and are hash-listed in the inventory. Failed-attempt references and pins remain represented by their compact receipts and pending manifests.

The as-of snapshot keeps the newest 18-cell generalist-support panel pending. Root row review is outstanding; all 18 output cells are absent. Support-P lacks baseline refs for Gem Fields A and Fracture B. Support-S and Support-C reuse six completed baseline cells each. This package does not claim global experiment completion.
