# Preservation staging review

Generated UTC: 20261024T130524Z. This is a review aid only; no files were staged.

The current snapshot lists 385 staging candidates (4,084,544 bytes) and 3454 local-only files (1,286,390,976 bytes). Raw replays, WASM, ZIPs, full match statistics, logs and raw inputs are excluded from staging and represented by hashes in the inventory.

## Coverage by top-level directory

| Directory | Files | Bytes |
|---|---:|---:|
| `[root]` | 107 | 9,625,693 |
| `cassi-five-release-v1` | 9 | 7,827 |
| `connected-escape-160-output-v1` | 326 | 132,025,082 |
| `connected-escape-fixtures-v1` | 5 | 18,613 |
| `connected-escape-release-v1` | 9 | 111,201 |
| `deadline-bound-native-audit` | 6 | 21,070 |
| `deadline-bound-output` | 8 | 4,151,685 |
| `deadline-bound-published-comparison` | 507 | 182,133,312 |
| `economy-inventory-v1` | 5 | 43,475 |
| `economy-inventory-v2` | 8 | 60,798 |
| `edge-economy-draft-screen-v1` | 4 | 49,694 |
| `extracted` | 10 | 438,252 |
| `f475-A-puppet-B-output` | 2 | 507,615 |
| `f475-farm-hop-160-output-v1` | 328 | 126,581,491 |
| `f475-farm-hop-release-v1` | 8 | 6,458 |
| `f475-v33-complete-output-v1` | 150 | 54,864,396 |
| `first-fork-comparisons-v1` | 3 | 4,596 |
| `fixed-role-screen-v1` | 53 | 14,529,303 |
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
| `missing-factorial-pairs-v1` | 656 | 259,478,637 |
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
| `raw` | 7 | 361,386 |
| `receipts` | 8 | 23,411 |
| `starvation-r1-trace-prep` | 123 | 6,902,896 |
| `stellar-five-release-v1` | 9 | 7,867 |
| `vendetta-five-release-v1` | 9 | 7,887 |

## Coverage by file type

| Type | Files | Bytes |
|---|---:|---:|
| `.apply` | 4 | 11,439 |
| `.cpp` | 6 | 873,507 |
| `.csv` | 2 | 55,575 |
| `.debug` | 4 | 0 |
| `.exit` | 3 | 6 |
| `.fuel` | 6 | 1,662 |
| `.gz` | 7 | 787,771 |
| `.json` | 268 | 26,862,152 |
| `.log` | 196 | 943,905 |
| `.manifest` | 31 | 1,729,750 |
| `.md` | 34 | 137,507 |
| `.mjs` | 8 | 31,785 |
| `.patch` | 9 | 107,783 |
| `.py` | 7 | 56,561 |
| `.repl26a` | 1582 | 89,797,738 |
| `.sh` | 5 | 9,965 |
| `.sha256` | 4 | 8,399 |
| `.stdout` | 12 | 100,098 |
| `.tsv` | 7 | 323,173 |
| `.txt` | 72 | 321,723 |
| `.wasm` | 2 | 1,822,362 |
| `.zip` | 2 | 65,386 |
| `full-statistics-json` | 1568 | 1,166,427,273 |

## Review flags

- Candidate paths containing sensitive/auth markers: 0.
- Raw/binary/full-statistics candidate paths: 0. These should be zero; items belong in local-only.

Raw and full-statistics items are explicitly local-only, with hashes only. Root should review the explicit candidate list before staging. The older 12:54 snapshot is retained as a historical pre-completion record.
