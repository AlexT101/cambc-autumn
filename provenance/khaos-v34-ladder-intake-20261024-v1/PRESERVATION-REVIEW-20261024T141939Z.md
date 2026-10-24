# Current selective preservation review

Generated UTC: 20261024T141939Z. Review only; no files were staged. The full inventory remains available; the explicit incremental candidate list compares against the 14:12Z pre-run snapshot and is not a git diff. Root should reconcile it against HEAD 8946d0b.

Current intake tree: 6273 files, 647 candidate files (6,628,620 bytes), and 5626 local-only files (2,097,647,270 bytes). Incremental compact candidate delta: 53 files (428,537 bytes). Raw and full-stat artifacts remain local-only with hashes.

## Work status

- 480-row Marcella combination screen: 480 games, 0 stats fault games, native audit complete=True.
- Fixed-three role screen: {'status': 'complete', 'games': 72, 'native_phase_bot_errors': 0}.
- Generalist support-18 screen: {'status': 'complete', 'games': 18, 'failed': 0, 'errors': 0, 'baseline_refs_corrected_and_present': True}.
- 44-row order/proxy/income screen: {'status': 'complete', 'games': 44, 'native_phase_audit_complete': True, 'native_bot_errors': 0, 'manifest_equals_plan': True, 'release_builds_pass': True}.
- Runtime-owned BossBattle recorder/trace settled; fullcap bundles remain local-only.

## Current coverage by top-level intake directory

| Directory | Files | Bytes |
|---|---:|---:|
| `[root]` | 121 | 14,435,385 |
| `bossbattle-support-p-trace-prep` | 143 | 38,648,766 |
| `cassi-five-release-v1` | 9 | 7,827 |
| `connected-escape-160-output-v1` | 326 | 132,025,082 |
| `connected-escape-execution-160-output-v1` | 320 | 130,802,511 |
| `connected-escape-execution-release-v1` | 28 | 933,910 |
| `connected-escape-fixtures-v1` | 5 | 18,611 |
| `connected-escape-release-v1` | 9 | 111,201 |
| `deadline-bound-native-audit` | 6 | 21,070 |
| `deadline-bound-output` | 8 | 4,151,685 |
| `deadline-bound-published-comparison` | 507 | 182,133,312 |
| `economy-inventory-v1` | 5 | 43,475 |
| `economy-inventory-v2` | 8 | 60,798 |
| `edge-economy-draft-screen-v1` | 71 | 16,745,971 |
| `elk-arena-ho4-trace-prep` | 125 | 6,759,266 |
| `extracted` | 10 | 438,252 |
| `f475-A-puppet-B-output` | 2 | 507,615 |
| `f475-farm-hop-160-output-v1` | 328 | 126,581,491 |
| `f475-farm-hop-release-v1` | 8 | 6,458 |
| `f475-v33-complete-output-v1` | 150 | 54,864,396 |
| `first-fork-comparisons-v1` | 3 | 4,596 |
| `fixed-role-screen-v1` | 53 | 14,529,303 |
| `fixed-three-role-screen-v1` | 185 | 59,125,062 |
| `fixtures` | 1 | 2,273 |
| `fracture-vesper6-r472-480` | 10 | 407,346 |
| `gem-fields-action-trace-prep` | 34 | 1,507,953 |
| `gem-fields-identity` | 1 | 144,835 |
| `gem-fields-prism-quote-trace-prep` | 66 | 436,981 |
| `gem-fields-puppet-output` | 2 | 507,631 |
| `generalist-support-18-v1` | 66 | 14,460,351 |
| `hop-escape-mixed-published-160-v1` | 334 | 131,147,703 |
| `hop-escape-mixed-published-release-v1` | 8 | 10,157 |
| `hop-escape-published-160-v1` | 332 | 132,448,795 |
| `hop-escape-published-release-v1` | 8 | 9,887 |
| `logs` | 38 | 81,142 |
| `marcella-combination-screen-480-v1` | 1006 | 389,793,141 |
| `marcella-delayed-tribute-scalar-fixtures-v1` | 3 | 8,153 |
| `marcella-tribute-value-160-output-v1` | 320 | 125,964,890 |
| `marcella-tribute-value-release-v1` | 18 | 977,641 |
| `missing-factorial-pairs-v1` | 674 | 261,214,574 |
| `mixed-alone-published-160-v1` | 334 | 128,602,099 |
| `mixed-alone-published-release-v1` | 8 | 10,049 |
| `native-audit-80-input` | 1 | 33,034 |
| `native-audit-f475-puppet-input` | 1 | 544 |
| `native-audit-f475-v33-input` | 1 | 4,593 |
| `native-audit-input` | 1 | 1,090 |
| `native-audit-three-gem-fields-puppet-input` | 1 | 568 |
| `native-audit-three-selfplay-input` | 1 | 770 |
| `native-audit-v47-recall-vs-f475-input` | 1 | 2,695 |
| `native-audit-v48-v33-input` | 1 | 4,616 |
| `native-audit-v48-walk-vs-f475-input` | 1 | 2,745 |
| `own-view-firstfork-v1` | 9 | 244,964 |
| `own-view-windows-v1` | 2 | 225,621 |
| `ownview-batch` | 1 | 959 |
| `planned-control-ablation-output` | 16 | 8,492,674 |
| `planned-output` | 160 | 62,434,857 |
| `planned-selfplay-output` | 4 | 2,271,879 |
| `planned-v33-output-v2` | 36 | 15,014,064 |
| `ranked-refresh-v2` | 30 | 2,126,705 |
| `ranked-refresh-v3` | 4 | 20,853 |
| `raw` | 7 | 361,386 |
| `receipts` | 8 | 23,411 |
| `starvation-r1-trace-prep` | 123 | 6,902,896 |
| `stellar-five-release-v1` | 9 | 7,867 |
| `three-pick-order-proxy-income-screen-v1` | 153 | 35,397,568 |
| `vendetta-five-release-v1` | 9 | 7,887 |

## Current coverage by file type

| Type | Files | Bytes |
|---|---:|---:|
| `.apply` | 4 | 11,439 |
| `.bin` | 1 | 72,163 |
| `.check_cache` | 1 | 85 |
| `.cmake` | 4 | 11,136 |
| `.cpp` | 11 | 3,882,639 |
| `.csv` | 2 | 55,575 |
| `.debug` | 4 | 0 |
| `.exit` | 3 | 6 |
| `.from-escape-trace-src` | 2 | 339,505 |
| `.fuel` | 7 | 63,843 |
| `.gz` | 19 | 3,200,388 |
| `.json` | 447 | 52,451,915 |
| `.log` | 382 | 7,039,831 |
| `.manifest` | 49 | 2,769,153 |
| `.md` | 50 | 204,032 |
| `.mjs` | 11 | 43,645 |
| `.ninja` | 2 | 36,107 |
| `.o` | 1 | 1,550 |
| `.patch` | 11 | 127,167 |
| `.patch-v1-wrong-pathing-comparison` | 1 | 314,743 |
| `.py` | 13 | 94,261 |
| `.rej` | 1 | 305,618 |
| `.repl26a` | 2528 | 144,395,437 |
| `.sh` | 7 | 16,157 |
| `.sha256` | 4 | 8,399 |
| `.stdout` | 23 | 15,262,405 |
| `.tsv` | 11 | 755,674 |
| `.txt` | 151 | 503,749 |
| `.verify_globs` | 1 | 77 |
| `.wasm` | 16 | 14,630,737 |
| `.yaml` | 1 | 21,044 |
| `.zip` | 4 | 216,462 |
| `full-statistics-json` | 2501 | 1,857,440,948 |

## Review flags

- Current candidate content matched the sensitive-string screen: 0 paths.
- Raw replays, WASM, ZIPs, full statistics, build/run logs, raw timelines, and large files are excluded from the delta candidate list.
- Exact referenced research checkpoints, source patches, and 29-file manifests are hash-pinned in `provenance/khaos-v34-ladder-intake-20261024-v1/RESEARCH-SOURCE-PINS-20261024T141939Z.json`; each entry is marked for root reconciliation with HEAD.
- The explicit delta file list is `provenance/khaos-v34-ladder-intake-20261024-v1/STAGING-CANDIDATES-DELTA-20261024T141939Z.txt`; full path dispositions and hashes are in `provenance/khaos-v34-ladder-intake-20261024-v1/PRESERVATION-INVENTORY-20261024T141939Z.json`.
