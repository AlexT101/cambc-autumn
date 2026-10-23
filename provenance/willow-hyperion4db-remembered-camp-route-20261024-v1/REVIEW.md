# Isolated old4db Band activation candidate

Frozen control: `bots/baselines/hyperion-4db-remembered-camp-route-control/src`.
Candidate: `bots/variants/willow-hyperion4db-remembered-camp-route-work/src`.
Control/canonical-before aggregate: `4db4eecbda37e23dbce0b162d2cf7441a3d32a554d6534cf196e3ffbedcdf2fd`.
Candidate aggregate: `0620e6589ba0c1ff908d94538c525b517ed5d8ee3a443e9fe26a9ccc5449a724`.
Both contain all 29 source files, without `.cambc`. Recipe: `(cd <botdir> && shasum -a 256 src/* | shasum -a 256)`.

The control was copied from the current `bots/hyperion/src` only after its aggregate was checked as old4db. Canonical was not edited. Full `before-src` and `after-src` snapshots plus relative manifests pin every source file. `canonical-after-src` and its manifest independently preserve canonical unchanged after implementation. The frozen control is a separate untouched source directory suitable for a source-known same-side historical Band activation pair.

The cb61 route patch applied mechanically to this fresh copy. Pathing.cpp/pathing.h were byte-identical between old4db and cb61 before the patch and remain byte-identical between their candidates afterward. Bot.cpp's farm contexts applied without manual changes. Only bot.cpp, pathing.cpp and pathing.h differ from control; selected farm ranking, goals, caps, direct native actions, global occupancy, combat/escape/dash/guard behavior and unrelated old4db behavior retain this witness lineage.

The exact implementation, source truth-table/call-chain controls, current native vision pairing, tile clearing precedence, scratch allocation statements and unresolved runtime risks are documented in `provenance/willow-astraeus-remembered-camp-route-20261024-v1/REVIEW.md`. This witness uses the same explicit farm-only policy, not a broader remembered obstacle model. Fresh visible emptiness wins over stale belief; native current camp occupancy wins over stale dead belief; unseen believed-live members remain obstacles. The policy reaches hidden-blocker retries, make_way and all farm route/field/crow fallbacks.

No build, engine or match was run. No change in the qualified Band action sequence, useful arrival, reward, survival or fuel is claimed. This is the isolated source candidate required to test that mechanism against the preserved 4db control. It is not a competitive claim for newer cb61 Astraeus.
