# Mite metadata refresh and one saved replay

At approximately 08:29 UTC on 2026-10-24, the authenticated `cambc 3.0.5` CLI successfully ran `matches list --team ee83f5e5-bcad-4923-86b4-b79ea6083d2e --kind ranked --limit 30 --json`. This follows the separately preserved 429/503 intake attempts about half an hour earlier. No browser was used.

Metadata SHA-256: `00250e19e320964e4728a9b64f9686d22b741eb2f9302a65c6837e00823040ec`. The reviewed count is 19–11 overall and 13–8 in 21 five-pick games. Drafts are unchanged from the prior sample; this does not establish a new submission or a source regression. See `research/mite-ranked-refresh-20261024-v3.md`.

The sole nominated replay was downloaded through `matches download 67f9d74a-673e-4b9a-936a-688c75632a0b --output .../big-world-B-loss-67f9d74a.zip`. It is Big World, Mite on B against :3. Bundle SHA-256: `1ae89813d8134d1f3ddc416457e325d01205f9d8bdaabf56edf916a77043736e`. Its ZIP inventory contains only `replay.repl26a`, 169,695 uncompressed bytes. The raw bundle remains local and is not included in the compact commit. At this checkpoint no decoding or gameplay analysis of that replay has run.

CLI path: `/Users/yufan/Desktop/Development/CambridgeBattlecode2026/current-autumn/tools/runtime/cambc-3.0.5/cambc`, SHA-256 `69617aa6a074415bd8ba8e254d1584df3392d95d1f9e2e2d46db66ff6e187171`.
