# Independent source recovery audit

2026-10-23, updated for index-v2. **All34 published source trees pass. The previously missing pinned emulator, diagnostic source and two aliases are now verified. Recovery is not established for every historical directory or build artifact.** This auditor used read-only commands; only this approved report was written. No source edits, builds, runtime or deletions by this auditor.

Audited current index: `recovery/incident-20261023-bots-recovery/recovery-index-v2.json`, SHA-256 `151ebe8e4a92d8ee0d2f751cb7870d578ee1432d93fd721211633b9d13f8ba1f`. Independently recomputed all34 aggregates using `shasum -a 256 src/* | shasum -a 256` from each bot directory and checked every file count. All pass. Its30 distinct source aggregates are supported by preserved pre-incident research checkpoints or provenance setup/release records, not just the new index. The previous30-tree index-v1 audit also passed (index SHA `61ca5443f7ca99725954084b133f285b5aa6542a6060372e80e26b43fa2e8203`).

The v2 index is a recovery-time snapshot: its `source_only`/empty `extra_entries` fields now have one subsequent exception. Root rebuilt Khaos_v33, whose root now also contains `.cambc` and `compile_commands.json`; its source hash is unchanged. All other33 indexed roots still contain only `src` at this audit. The empty comms directory is not one of the34 verified sources.

| Recovered group | Trees checked | Matching aggregate prefixes |
|---|---:|---|
| Khaos_v32/v33 | 2 | db5b37d5 / a00fff45 |
| Git baselines4c4/fbda/8be/b7/eaee | 5 | 7f773ba8 / 15dcd64d / d8d3cc1d / d6bac059 / a97aeefd |
| Fish old draft/prefix and both97 factorial controls | 4 | b8108db1 / 2797a671 / 37c3ccb7 / e9a9a182 |
| Audit transit/ready-heal/live-ally/audit107 | 4 | c71fc573 / 06b266ef / ee1b404d / a00fff45 |
| Old/latest deadline-stage | 2 | 73545517 / 42980a43 |
| Original/latest/value forecast | 3 | 0e989629 / 647a10e0 / 0bac63b7 |
| Integrated latest clone | 1 | 337f42a5 |
| Four-pick experiment | 1 | 157f5f79 |
| Local Monolith v1/v2/corrected | 3 | 5b0a9d87 / bbd8695f / 56f17fec |
| Upstream coordinated/heal-view/presence/sleep v1/corrected | 5 | 1670a7e8 / bafc4934 / db5b37d5 / 1544343d / de1c99aa |
| Restored deployed-v33 / Monolith-v2 baseline aliases | 2 | a00fff45 / bbd8695f |
| Forecast funnel diagnostic / fixed roster emulator | 2 | 92578884 / 10e5eeaa |

The full hashes and paths remain in the pinned index. Original supporting records include the corresponding `research/*source-checkpoint.md` files; exact4c4 is additionally pinned by `provenance/fish-roster-emulator-preflight/setup-before-extension.json`. Earlier independent checks also confirmed canonical `bots/hyperion` at337f and tracked `bots/baselines/v44` at a00fff; those are outside this34-tree reconstruction list.

## Resolved additions and remaining exceptions

- Fixed roster emulator `bots/variants/hyperion-fish-roster-emulator-fbda803` now matches aggregate `10e5eeaabd57580f2ccd59240f36341209c2337fa9f190c8ea310b79943c90ac` and independently rehashed `draft.cpp` pin `4f69a438903fae3f29dd867c86ae0ba3bf67a13b109ce6a0428bf97c8fa3c470`.
- Forecast diagnostic `bots/variants/willow-fbda803-forecast-funnel-diagnostic-work` now matches aggregate `92578884b914a98649eab69fa7a3e95ecf7c81e8edc5c70c3681c402ba9a9da9` and independently rehashed `bot.cpp` pin `63cf04958bb4ffee686e5e5295f4f605c7e0820e0b6b30875cdcd5963c47a1ad`. The recovery manifests identify complete source diffs preserved in the task's historical tool output as the reconstruction material for both additions. Matching authoritative source hashes establishes exact recovered content; these are reconstructed files, not surviving original directories.
- Both original baseline paths `bots/baselines/willow-local-monolith-crew-bbd869` and `bots/baselines/hyperion-deployed-v33-a00fff` now exist and independently match bbd869 and a00fff respectively.
- `bots/variants/ladder_manip` remains unknown. No assertion that it was empty or harmless to lose is justified. The empty `willow-comms-pair-index-work` contains no source and is correctly excluded from the30 verified trees.
- Original `.cambc` caches were lost. Root subsequently rebuilt Khaos_v33 separately; this audit independently hashed its raw `bot.wasm` as `f1e94a1e5c5c45c9907ef1e237c88e079157aa153fdbf116516627c31e85ebb7` and injected `bot-injected.wasm` as `4fcd9435b5f77abcc42576baa1533dbc8b681bd720632adae160df9792bf1792`. Both exactly match preserved `provenance/Khaos_v33-release/release.json`. That proves binary content equivalence for this release pair, not recovery of original build intermediates or every other experiment's WASM. Other build products remain unverified; no build was run by this auditor.

The index correctly clarifies that the initial `git_status_at_capture` was captured **after** two release trees were restored; it is not a pre-incident inventory. Index-v2 replaces v1's descriptive non-file component entries with actual manifest paths. Its runtime-artifact statement predates the later Khaos_v33 rebuild and should be read with the exception above. The34 successes establish exact source bytes reconstructed from archives/Git/patches/transcript diffs, not survival of original directories, timestamps, all build products, or an exhaustive pre-incident inventory. Replays, research and provenance remain the original supporting evidence; this report does not modify them.
