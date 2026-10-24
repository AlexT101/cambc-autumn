# Published 40-map static economy inventory

Run `node inventory.mjs` from the repository root. It uses the existing native map decoder and Grid camp grouping, verifies each source map SHA-256 against the published40 map-inventory manifest, and writes `RESULT.json` / `RESULT.md`.

Counts and ordinary reward totals describe the entire native map layout, including mirrors. They are not per-team accessible resources. Accessibility, visibility, capture control, and strategic selection are not inferred. Current reward values are from `cambc-rules.yaml`.
