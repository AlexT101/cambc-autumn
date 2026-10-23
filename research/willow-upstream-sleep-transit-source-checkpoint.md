# Willow stalled sleeping-camp transit source checkpoint

2026-10-23. Root authorized the narrow gameplay arm in `research/willow-elkring-own-view-diagnosis.md`. Created a separate **source-only**, unbuilt child `bots/variants/willow-upstream-sleep-transit-work/src` from frozen db5b. Parent/canonical files were not edited. No build, engine, extraction, script/tooling implementation, runtime or EXPERIMENTS work. This is an unqualified future experiment, not a numbered release.

Revision2 addresses root/Astra's dead-proof blocker: `engine::camp_health` maps both not-found and not-in-vision to nullopt, and the parent stores zero for either. An alive group's zero health is therefore insufficient successful-death proof. The exception now conservatively rejects every zero/unknown-health contributor in an alive group. Fresh recognized cleared groups may still be skipped. No native read or ledger was added; partially dead groups may conservatively miss the exception.

Immutable v1 reconstruction artifacts were saved **before** this change: `research/willow-upstream-sleep-transit-source-v1.patch` SHA `e5356ffff900b114a6a4e9c1c6f955964f1149506a2fc722786b4cad53e640e0`, and `research/willow-upstream-sleep-transit-source-v1-checkpoint.md` SHA `01c458835fb6530f0b1556da76c19a456d1c37d23735c284e76aac4bc3fc5c48`. Applying that exact patch to pinned db5b reconstructs original aggregate `1544343d782595a6d5774586f5ffd00425c2be4714b99995c4a43a5b80127f85`.

## Pins and exact scope

Aggregate convention: from each bot directory, `shasum -a 256 src/* | shasum -a 256` (filenames relative to the bot).

| Artifact | SHA-256 |
| --- | --- |
| Frozen parent `willow-upstream-presence-work/src` | `db5b37d5e5c609c2c616d3a39c0f1eb7f5adebf401dcd1be8848e0eede237ab8` |
| New child `willow-upstream-sleep-transit-work/src` | `de1c99aae1085f767a510c465e015cca50fbf979c0319f6037d70d554bd3d001` |
| Complete parent→child patch `research/willow-upstream-sleep-transit-source.patch` | `36674aeec790af90124e63615a8df99ed84afa3a2cc7a8e2ac18aa35d3369727` |
| Child `src/bot.cpp` | `6104b151e12d9d3b3c7415e5b2e67f52f9cd92c30440b90ded8d20f59dfa9a97` |
| Child `src/world.cpp` | `e3a8f76cb824c8894a2ef56c0f06abbaf8a27167082f4f45dd7c78f3270ffa9b` |
| Child `src/world.h` | `bbf202c92649e880ff73586b31b7154825a2371542966f49e466f813f1c10e36` |

Exactly these **three** files differ from db5b: bot.cpp +106 lines, world.cpp +11, world.h +4; total121 insertions, no deletions. Recursive source comparison found all other files identical. The child contains29 source files and no `.cambc`/build cache. Whitespace diff check emitted no diagnostic. No compile or runtime success is claimed.

## Gameplay admission

`bot.cpp:4373–4439` adds three small helpers; the sole policy callsite is in the existing Willow owned-escape retry loop (`4526` onward). The original nine-station comparator is unchanged.

The exception runs only with `leave` true, actual movement availability, an **already-ready** existing home field, and an alive/recent visible enemy whose existing Strike bound can approach within the existing `pursuit_steps`. This gate uses the same known teleport destination origin as current Safety and does not replace latest-main readiness/timing. The parent-selected station must fail strict home-field progress, including a stay or reversal. An already-progressing parent escape is never replaced.

An alternative must be an existing legal adjacent station, strictly homeward in that field, off every static camp tile, with no modeled enemy hit/stun or damage/imminent damage. Its sole safety deficit must be the camp flag. Among these alternatives the existing comparator selects **one finalist**. Only that finalist is certified; if its certificate fails, retain the parent's original choice. This deliberate conservative first arm keeps the rare bailout work bounded to eight rays total per attempt rather than trying eight rays for every station.

The ray certificate:

- Reuses `willow_station_members_near` and consumes each span completely before another tile lookup. No borrowed span or member pointer survives observe/cache growth.
- Requires a recognized current group-state reading and observation epoch. A freshly known cleared group contributes nothing. Alive-group contributors with zero/unknown health reject, even with current health freshness; no unproved death can silently certify a future path. Every relevant live damaging member must have a successful current asleep read, current visible tile and existing asleep belief. Unknown, awake, respawning, stale or live member index≥64 rejects. Root explicitly approved conservative rejection beyond the certificate bitmask.
- Tries the proposed step direction and its reverse first, then the other six fixed directions. Each ray is at most `max_camp_reach+1` steps, stops on bounds/static terrain/current blockers/static camp tiles, and accepts only an actual camp-free endpoint. No new board, path field, global route or native camp/occupancy/readiness query is constructed. Root approved bounded tests of already-held boards; these still have their normal SDK bitboard-test cost.
- Accumulates full unmitigated Strength of the **union** of all living strikers reaching any point on the entry/bailout path. Earlier ray coordinates deduplicate static members without another container. Requires HP **strictly greater** than this union times entry-plus-exit phases. It never borrows an ally tank, item mitigation, future heal or hypothetical enemy behavior. Reaching an affordable certificate stops the scan early; rising cost stops an unaffordable ray.

This is a camp-wake reserve for a possible local bailout, not a promise that a whole home route is tankable or that future enemy movement cannot intercept it. Reevaluate each turn. The proposed station still has the original exact enemy/stun veto; no hypothetical future enemy search is added along the certificate ray.

## Freshness and invalidation

`CampBelief` stores one64-bit successful-asleep mask and an observation-epoch stamp; no per-member vector or allocation was added. Only Willow populates these certificates. `World::update_camp` clears the old mask/stamp **before** any group read, stamps only recognized alive/cleared codes, and sets a member bit only from the existing successful `engine::camp_awake` result. `health_round` by itself is not used as asleep proof. Dead/unknown/awake reads leave the corresponding bit clear; a failed read cannot inherit yesterday's mask. Restore/respawn and received capture clear the mask.

`World::update` and `World::observe` increment a scalar observation epoch before reading. An observe expires every previous certificate in constant work; it does **not** manufacture a fresh camp observation. In particular, `see_again` after a hidden-blocker failure reconstructs current Safety/stations but cannot reuse the certificate that admitted the failed move. With no extra native camp reads, this may conservatively decline further sleeper exceptions for the rest of that turn. The ordinary parent retry selection remains available. No span, target pointer or cached Safety record is retained across that refresh.

The owned escape heals useful allies before movement as before, and cannot perform camp damage/stun/reset work during the exception. Its existing early return and act ownership suppress the ordinary strike/farm work. Turn-end ward/lock/recall handling remains unchanged. The successful move still refreshes once and returns; failure still refreshes then retries with current records. At most one successful movement occurs. Holding, banking, local-support formation/recovery, strict station construction and `SupportExposure::safe()` are unchanged outside this escape exception.

## Review and runtime handoff

Actual root/Astra source review is required before any build. This checkpoint performs source inspection, exact changed-file/hash comparison and whitespace checking only.

Two debug-block-only lines are present: `WT` records an admitted replacement, parent/child home distances, actual HP, wake reserve and exit length; `WT-MOVE` records the attempted tile and native move result. No production logging or generic diagnostic framework was added.

First runtime mechanism target is actor A3 on Elkring r309–313 from the pinned own-view diagnosis. Verify the executed branch, actual legal/risk records, admission and continuation; an independent enemy/legality rejection is a result, not a reason to force admission. Compare B8 r665–673 as a rejection/regression window: its unknown camp cannot be treated as asleep. Check fresh unknown/awake and partial-read rejection, live index≥64 rejection, insufficient HP, blocked/off-map ray exits, original already-progressing choice, stale resume and hidden-blocker failure. Then measure native fuel/error impact, camp deaths, retained healing service and gem conversion before broad qualification.
