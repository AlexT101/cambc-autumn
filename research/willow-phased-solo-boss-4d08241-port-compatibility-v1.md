# Phased solo boss port to upstream4d08241

2026-10-24. Source-only port of reviewed f7 v3 onto upstream commit `4d08241123b88ad0365d4b0ad346cd65a329b699`. No build, engine, replay, helper script, tooling change or canonical update. The f7 v3 tree remains exactly `b4a7d993fa954e459b89e21e25fc52834ba6574f29d5ad60528c2fbc861a0f95`; canonical f7 remains `f475b8521cada611754076822402a266c43be8de76ce0f2b504b268ff3335824`.

The frozen newest baseline is `bots/baselines/astraeus-4d08241/src`, extracted directly with `git archive` from that commit's29 source files. The separate child is `bots/variants/willow-phased-solo-boss-4d08241-work/src`. No `.cambc` cache was copied. Only the reviewed boss delta plus the necessary signature adaptation distinguishes child from newest baseline; no new gameplay restriction or enhancement was added.

| Pinned artifact | SHA-256 |
| --- | --- |
| Newest29-file baseline aggregate / `astraeus-4d08241-source-manifest.sha256` | `f599a31faa0251321beb97a726918286e266218ceb3e183b8271e41c5c84718c` |
| Ported30-file child aggregate / `willow-phased-solo-boss-4d08241-source-v1-manifest.sha256` | `0b777e56af33fceff78228c1cdc393ecdb26d66b6b5a136596a07e0ff0c49c61` |
| Newest-baseline→child `willow-phased-solo-boss-4d08241-source-v1.patch` | `9e76b5032118e4c89b709d62bfd677df03165fe237431f22b77d0046de4e1bb1` |
| Frozen-f7-v3→ported-child `willow-phased-solo-boss-f7-to-4d08241-port-v1.patch` | `0dca9933f109d8dba1e8da313d27c43f76ed775a1cf56c9b74b504bfa555571a` |

Manifests use `shasum -a 256 src/*` from each bot directory; their hashes equal the corresponding aggregate recipe `shasum -a 256 src/* | shasum -a 256`. These versioned receipts are immutable.

## Four upstream fixes retained

1. **Capture allocation.** `capture_taken` now takes an integer group ID and uses `bound_elsewhere` to exclude nearby allies committed to another group, tributing or keeping a recall. The new boss helper's private forward declaration and sole call now pass that ID. The upstream siege and kite callers retain the upstream ID arguments. No obsolete `const CampGroup&` overload remains. This intentionally inherits upstream's allocation behavior while retaining the boss arm's existing Prism/holder and explicit same-group claim checks.
2. **Shield pricing.** Latest plan.cpp is retained byte for byte. Reduced damage now drains the shield consistently in spell fallback and landing valuation. The Marcella camp forecast neither uses these champion shield prices nor replaces them.
3. **Dash-aware altar distances.** Latest pathing.cpp is retained byte for byte. Dashers use their own field graph when crossable terrain makes draft walking distances unsuitable. The boss arm remains Marcella-only and retains its separate camp-aware transit fields; ordinary actors inherit the upstream correction unchanged.
4. **Mid-turn enemy death.** Latest world.cpp is retained byte for byte. During `World::observe`, an enemy previously alive/visible this turn whose native record disappears gets a liveness check, accurate mid-turn respawn bounds and cleared alive/visible/tracked/gem/channel state on confirmed death. `observe()` still increments its observation epoch, updates champion state and records its sight position; it still does not refresh camps. The boss token therefore invalidates on the same epoch boundary, its `vision_from` getter remains compatible, and `see_again` reconstructs Safety using the corrected enemy state. Exact native boss/member reads remain necessary and unchanged. No new broad liveness refresh was added by the port.

## Source verdict and remaining work

The frozen-f7-v3→port diff contains precisely the four upstream source fixes plus the two mechanical boss-helper signature edits. The newest-baseline→port diff contains the same reviewed boss integration, Memory job, vision getter and helper as f7 v3, with the updated capture function interface. Whitespace inspection is clean; there is no source-level compatibility blocker identified. Independent port review is requested before any latest-base build. The authorized runtime worker builds frozen f7 v3 first; this port has no runtime qualification or competitive claim.

## Independent review addendum

The independent reviewer read the frozen port diff and full-patch receipts, recomputed the actual source-tree aggregates (`f599a31f…` baseline and `0b777e56…` child), and verified the receipt hashes above. Direct file comparisons confirm the child's `plan.cpp`, `pathing.cpp` and `world.cpp` are byte-identical to the newest baseline. Its only `world.h` change is the read-only `vision_from` getter against existing `sight_pos_`; `observe()` still advances the epoch and updates that position, so the boss descriptor/cache contract remains compatible with the upstream enemy-death fix.

All capture allocation call sites and the helper forward declaration use the new integer group ID; no old overload remains. The upstream `bound_elsewhere` implementation, actual-occupant exception, Prism handling and original siege/kite callers are retained. The boss helper's pre-existing explicit same-group claim rejection is unchanged. The complete f7-v3→latest port diff adds only the four upstream fixes and those two required helper signature/call adaptations; no further boss policy change was found.

**Source-ready: the authorized latest-baseline build and paired mechanism check may proceed after the scheduled f7-v3 work.** This is compatibility approval only. No build, engine execution or competitive result was produced by this reviewer; compare the latest child against its exact latest baseline, not the f7 control.
