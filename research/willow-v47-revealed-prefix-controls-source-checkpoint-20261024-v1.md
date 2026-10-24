# v47 three-pick order/proxy controls and income synergy

2026-10-24. Root-authorized fixed source controls following `research/willow-v47-three-pick-screen-interpretation-20261024-v1.md`, SHA256 `2472cc8b766caa1183e6e752b8513e5fe97588c3334ceb81bae54905a8e59b3c`. Cambridge Battlecode rules previously read. No dynamic selector, new map/opponent threshold, scripts/helper implementation, git operation, build/game, SDK/tool edit, canonical/EXPERIMENTS change, upstream fetch, release or submission.

Frozen f475 parent verified as `f475b8521cada611754076822402a266c43be8de76ce0f2b504b268ff3335824`: `provenance/willow-astraeus-clock-recovery-20261024-v1/workspace/bots/service-base-f7`. The four draft controls are independent src-only copies. Existing f475 P/V/HoR and `willow-v47-marcella-three-work` M/V/HoR (aggregate `5dc0f00960864250fa2fb26cac4d309c7cf55b9e4ffbc03c4b7b3c7a011b11fa`) remain unchanged for reuse.

| Child under bots/variants | Ordered default three selections |29-file source aggregate |
| --- | --- | --- |
| willow-v47-delayed-prism-three-work | Vesper / Heart of Ruin / Prism | `f299a82c63f53eb33eba61ebd81983bed170644ce102895aec9c7a09ce652eac` |
| willow-v47-delayed-marcella-three-work | Vesper / Heart of Ruin / Marcella | `3e6d4dd4a7e5cf42bc9fd1dd889ba647a0561cea46efabb061cff7a41aea8103` |
| willow-v47-proxy-mvt-three-work | Marcella / Vendetta / Tavi | `9f67c51e334a32988e0045240802c73e94915c4a27b22f5041c8f07f0e37b5ce` |
| willow-v47-proxy-vhv-three-work | Vesper / Heart of Ruin / Vendetta | `5e7c5d880db62136b8d30e25a66d1f7e57a36fe8e68dedaa591114fc0f3d67e7` |
| willow-v47-marcella-three-income-work | Marcella / Vesper / Heart of Ruin, plus reviewed income | `e2e58e265e60546f9e44b65085c2a3939168c8cd92af1d8d93818aeb1fad4e2b` |

Each manifest is `research/<child-name-without-work>-source-v1-manifest.sha256`;29 entries each, all145 entries verified. Its SHA256 equals the listed aggregate. No `.cambc`, backup/reject files or added-line trailing whitespace. For the first four children only draft.cpp differs from f475, exactly10 inserted lines; all other28 complete source files match. The synergy child differs only in bot.cpp and draft.cpp; other27 files match f475.

## Draft implementation and communication

The current three-pick pattern is retained: inside default draft_order, after the untouched test_draft early return, use the already-read picks==3 condition, a constexpr copy of the full params::draft_preference array and typed SDK enum assignments to entries0/1/2. All recipes have three distinct intended selections. Later preference entries retain their original positions. The native pick_first_available duplicate/unavailable handling and ensure_picked fallback code remain byte-identical; no replay numeric IDs or forced pick action is used. SDK enum spellings vesper_vale, heart_of_ruin, prism, marcella, vendetta and tavi were checked directly.

One/two/four/five-pick default paths, the four-pick swap, test-composition path, params, native_pick and full original fallback array remain unchanged. All four draft-only children have exact f475 gameplay. Their new branch adds no native query, map analysis, field or gameplay-turn work. The delayed controls differ from one another in exactly the final named enum, documented by their component-relative patch.

The native simultaneous-pick visibility contract is untouched. The existing current_draft(ally) read remains solely for availability/deduplication; no enemy-pick read is added. These fixed controls select the complete order at the first default draft_order call. They do not adapt their third pick, infer the hidden third enemy pick or pretend a revealed-prefix classifier exists. The last slot occurs after two opposing rounds could legally have been observed; a later adaptive selector requires separate source evidence and approval.

Static map Analysis, DraftPlan layout/version and carried analysis state, read_draft_plan validation, write_plan and write-before-pick ordering are unchanged. No selector metadata or communications field is added. Existing map buffer completion still follows its existing fuel budget; source inspection does not claim byte-identical completed runtime buffers. Comms.cpp/h, roster lookup and actor-identity handling remain exact f475 in all five children.

Order changes intentionally change actor IDs/tie initiative, initial allocation and claims, even when the final set of champions is unchanged. Therefore delayed-P versus early-P and delayed-M versus early-M are order controls; comparing P/M at the same order/proxy tests composition interaction. Proxy folders label only fixed recipes with our f475 gameplay, not replicas of an opponent's code, hidden information or adaptation. No map/team identity rule is installed.

## Exact income union

Verified complete input manifest for reviewed `willow-v47-marcella-tribute-value-work`, aggregate `8701885d1e7d6d3d69c10bcea80289d3e59b3c01824ff4834162062dcf1ab58f`, and the fixed-M3 manifest before composition. The synergy child copies the complete income source and replaces only draft.cpp with the complete fixed-M3 file. Child bot.cpp compares byte-identical to income; draft.cpp compares byte-identical to fixed-M3. Component-relative ordered added/removed source lines match both original deltas exactly, excluding only diff headers/context/locations. No overlapping gameplay merge was needed.

The reviewed income scope/delay/optimistic prunes and no-future-budget rule remain exact. It is not newly restricted to three-pick matches; the requested exact income component retains its existing Marcella scope, while only the roster intervention is count3. No support, hop, escape, mixed qualifier, recall, Boss diagnostic, communications or v48 overlay exists. This is the separate12-cell six-map/both-side common-v33 synergy arm, using the existing fixed-M3 control.

## Patch pins

Ordinary unified diffs under research:

| Patch | SHA256 |
| --- | --- |
| willow-v47-delayed-prism-three-source-v1.patch | `a59338765959d8a0b847ca1e8a12362de741abed22b39229942aef2ccb678035` |
| willow-v47-delayed-marcella-three-source-v1.patch | `a07de712923474839e864f4744a6cd79d4fc707866c276e72726796cca51c3ca` |
| willow-v47-proxy-mvt-three-source-v1.patch | `a4f09ea16af670b1a6ba5f351cc90be688bed9e6d52caa64117bd9a5678b795b` |
| willow-v47-proxy-vhv-three-source-v1.patch | `fc080038910f377ab9332ac592d8e3aee8e1707ba807c37726bfe7d90ad5edcf` |
| willow-v47-marcella-three-income-source-v1.patch | `ec9325725d3ea14b8753f8f3cba8b601a345f958626602f197df30da9e7470f9` |
| willow-v47-marcella-three-income-vs-income-source-v1.patch | `85b0f01885c6cbcfa36044208233d41cb98b28cfe62c00c7c235a512c67ca78c` |
| willow-v47-marcella-three-income-vs-marcella-three-source-v1.patch | `769ea789843bc04f98d544d56a9c0e210f601b17a54c7f491c8ebb6642bcef00` |
| willow-v47-delayed-marcella-vs-delayed-prism-three-source-v1.patch | `18bc758b046993e7013c575d751a05aa8fa4bb79b153e2ac2df9b4c335c41286` |

Root owns source review and Luna owns the planned32-row Fragment/Packs/both-side/two-proxy screen and separate12-cell synergy comparison, including accepted roster/IDs, native errors/rollovers and any income activation/conversion evidence. No runtime, cost-equivalence, selector, causal or strength conclusion follows from this checkpoint.
