# Cached-visible ally stun read: minimal source repair

2026-10-23. Root authorized a separate source-only child of ready-heal06b266: `bots/variants/willow-audit-live-ally-work/src`. Only `safety.cpp` changes, 9 insertions/3 deletions. No eager observation scan, World fields, extra SDK call, native visibility probe, diagnostic instrumentation, new fuel gate or general combat redesign. Parent06b266, c71fc, references, canonical, releases and EXPERIMENTS remain unchanged. No build, runtime, extraction or script was run.

| Artifact | SHA-256 |
| --- | --- |
| Frozen ready-heal parent aggregate | `06b266efc20e36955c22ea9db743e1a71ea9ab9eb82463825f8284f0af33f68f` |
| **Child source aggregate** | **`ee1b404d8e50bc188c092739142d6a1f5bcf078756f643588d2693ccf94c7b10`** |
| Changed `src/safety.cpp` | `cfe93d7af44cb40dd0297a2bf87ade13b24d87a378a6c77ca2b53783101bbf48` |
| Full parent→child `research/willow-audit-live-ally-source.patch` | `6ec7e36fd9e407245d5f3fc9cfdd281e4c6e3ed54cca1df801dcf126635e4561` |
| All29-file `research/willow-audit-live-ally-source-manifest.sha256` | `ee1b404d8e50bc188c092739142d6a1f5bcf078756f643588d2693ccf94c7b10` |

Aggregate recipe: `shasum -a 256 src/* | shasum -a 256` from the bot directory. The manifest is that first command's output. All28 other files are identical to06b266; parent aggregate rechecked unchanged. Source-only folder has no `.cambc`.

## Actual behavior and proof boundary

`research/willow-audit-not-in-vision-source-diagnosis.md` establishes the source mismatch: allies already read this round retain cached `visible` after movement and even `World::observe`, but latest-main `make_slot` started a fresh buff read under that cached bit. Cached positions/stats remaining stable does not guarantee present SDK visibility. Existing saved act-error97 records nominate LostWorld reference r18 in both swapped games for later attribution, but have no SDK call-site/actor proof yet.

`stun_pending`656 now returns `optional<bool>`. It performs exactly the original single raw buff query. Success preserves the original interpretation: a stun duration>0 returns true; duration0, absent stun or zero buffs returns false. Error97 returns unknown before reading the shared buffer. Every other code still passes through `ok`, including98: no documented expected not-found contract was assumed and no broad exception was swallowed.

`make_slot` retains every original eligibility gate and import order: enemy/self/dead/believed-hidden fighters take the old generic branch; visible-ally timing starts at `acted ? round+1 : round`; teleport keeps its original arrival precedence; stun-immune Marcella makes no buff call. For the remaining ally, known positive stun or unknown visibility sets `arrives_at=1`; known absent/expired stun leaves0. Thus a same-round known-positive stun remains at least equally conservative if a rebuilt Safety later loses sight, without retaining a separate snapshot. A previously unstunned/duration0 ally that becomes hidden may now receive a conservative one-turn delay. No guaranteed immediate participation or future health is credited from unknown state.

This preserves the prior stale-ally inclusion/position model and `made_` caching. It fixes the provable thrown97 site without claiming that hidden allies cannot participate or that the broader model is exact. Handling unknown differs from simply returning false: missing data cannot increase the assumed immediate allied force. The change is gameplay-relevant, so fuel-only exact replay identity is not claimed at an affected error branch.

## Verification and handoff

Read the actual full source delta and checked whitespace without diagnostics. Existing safety/world headers already include `<optional>`. Successful buff reads and all noneligible paths retain the original actions/import counts; only the97 branch avoids throwing and chooses the explicit conservative delay. The initial unpinned eager-snapshot draft was replaced before review handoff; its World fields/imports are absent from this final source and patch.

Root/Astra actual review precedes Luna compile/runtime. Minimum later checks: positive/zero/absent stun; believed-visible ally lost after walk/dash/ward sight change; Safety reconstruction and repeated fights; immune/TP/self/enemy unchanged; non97 errors still propagate. Trace the existing failing import in reference LostWorld r18 to attribute the saved error and compare caught-error frequency after repair; other97 sources may remain. No runtime success or broad competitive benefit is asserted here.
