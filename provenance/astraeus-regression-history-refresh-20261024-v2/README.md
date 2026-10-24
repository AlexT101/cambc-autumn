# Lightweight ranked-history refresh

Retrieved own-team history through the authenticated `cambc 3.0.5` CLI at approximately 07:59 UTC on 2026-10-24. Command: `cambc matches list --team me --kind ranked --limit 30 --json`. No replay download, browser, simulation or extraction.

The 30 finished matches were created between 07:00 and 07:50 UTC. Team `547efb5b-57e5-4355-8501-3b331f506d62` (`willow best girl`) wins 17 and loses 13. Its 26 five-pick matches are 15–11. Every own draft begins with champion ID 5 (Prism); no Willow-first ladder-manipulation match enters these counts. These are changing map/opponent schedules with no exposed submission IDs, so the totals neither establish a source regression nor a recovery.

A subsequent metadata-only request for Mite (`ee83f5e5-bcad-4923-86b4-b79ea6083d2e`) returned HTTP 429. One delayed retry returned HTTP 503. Both empty outputs and error messages are retained. No Mite refresh was obtained; the earlier saved replay evidence remains the basis for its analysis. There are no further retries in this intake.

CLI: `/Users/yufan/Desktop/Development/CambridgeBattlecode2026/current-autumn/tools/runtime/cambc-3.0.5/cambc`, SHA-256 `69617aa6a074415bd8ba8e254d1584df3392d95d1f9e2e2d46db66ff6e187171`. Mite command: `cambc matches list --team ee83f5e5-bcad-4923-86b4-b79ea6083d2e --kind ranked --limit 30 --json`.
