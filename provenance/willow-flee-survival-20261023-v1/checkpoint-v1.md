# Camp retreat survival: two source-only arms

2026-10-23 America/New_York / 2026-10-24 UTC. Read AGENTS.md and the Cambridge Battlecode rules. Source-only implementation following the [incoming-loss review](../../research/incoming-loss-adaptation-review-20261023-v1.md), with Astra design/source review in [willow-flee-survival-source-review-20261024-v1.md](../../research/willow-flee-survival-source-review-20261024-v1.md). No build, runtime, extraction, tooling script, release numbering, deletion, move, cache copy, canonical edit or root EXPERIMENTS edit. No sibling checkout was touched.

## Frozen identities

Source aggregates use `shasum -a 256 src/* | shasum -a 256` within each bot.

| Arm | Variant | Source SHA-256 |
|---|---|---|
| Parent | `bots/hyperion` | `4db4eecbda37e23dbce0b162d2cf7441a3d32a554d6534cf196e3ffbedcdf2fd` |
| Survival first | `bots/variants/willow-flee-survival-first-work` | `1a1ee8e788c80cd3d38b5531df9e203b253741f9ca1eda4960d22163d57d1764` |
| Survival first plus emergency basic | `bots/variants/willow-flee-survival-basic-work` | `3d18ab0a56f3646a2fc701b5d876324083ff6ba9c44b75df70daf6b4cf566b87` |

The unrelated frozen masks child remains `28e64f631dfcb873338c63bebf52eb2d25bcad9da7c7c235c98b02ff06598852`.

`parent-4db-src/`, `survival-first-src-v1/` and `survival-basic-src-v1/` contain all 29 source files each. Recursive comparison confirms each snapshot matches its source bot byte for byte. Each corresponding `*-files.sha256` manifest has 29 entries. Only `bot.cpp` changes in the primary arm: 29 insertions, 6 deletions, including the revised function comment. The combined arm changes `bot.cpp`, `safety.cpp`, `safety.h` relative to primary: 79 insertions, 1 deletion. No-index whitespace checks produce no diagnostics; diff exit1 denotes source differences.

| Exact patch | SHA-256 |
|---|---|
| `survival-first-v1-vs-4db.patch` | `c68c636f35097440f2fcdf7bab1411876e56acede9ee04a0ff66e0b2b0bb06ab` |
| `survival-basic-v1-vs-4db.patch` | `79af87a18ef98faf03c60a2f294a2234e600235bd57bbb9fb0acd88a6169d80d` |
| `survival-basic-v1-vs-survival-first.patch` | `86a360746859c86952baa2d035256795fe4fa82a45cfd25960e7f7fb4e61427f` |

These are recursive exact source diffs with full variant paths. The combined-versus-primary patch isolates the emergency mechanism.

## Primary source contract

`flee_camps` originally ranks staying and up to eight unblocked neighboring tiles by next-phase `Safety::damage_bound` plus an estimated multi-phase camp exit burden, then home distance. A lower exit burden can beat a step that survives the next phase. The primary arm retains the immediate bound already produced by each original cost evaluation, separately from its exit cost, and reads current native health once.

No candidate, path search, damage query, camp-area query or home-field query is added to that planning pass. It preserves the original in-bounds/current blocked-board candidate pool and compass enumeration. The existing nearest-champion camp targeting and credible unseen-enemy assumptions remain in the immediate bound. Health is used without borrowing a shield margin; immediate bound strictly below HP defines a surviving option.

| Original pass outcome | Primary behavior |
|---|---|
| Cannot move, or no camp damage here | Original early return. |
| Current tile and every evaluated free neighbor survive | Original cost/home selection and original return/fallback behavior. |
| Any evaluated option is lethal and surviving neighbors exist | Try only the saved surviving neighbors, sorted by original exit cost then home distance, stable in compass ties. At most eight attempts, with no forecast or path recomputation. |
| Saved surviving neighbors absent or all rejected, and current tile survives | Return handled, staying here; a lethal ordinary fallback cannot override it. |
| Saved surviving neighbors all rejected, and current tile is lethal | Return false to the existing retreat fallback. |
| Current tile and every evaluated free neighbor are lethal | Retain original selected movement/fallback in primary. |

This preserves ordinary fallback behavior when every evaluated option survives and avoids introducing a general stay preference at a local exit-cost minimum. In the hazard case it prefers a surviving departure before a surviving stay.

Deferred guard materialization remains in the existing `Pathing::try_move`; it is not forced while enumerating. A guard refusal/native hidden blocker may trigger the next saved surviving attempt, only in the hazard path. Staleness is checked before execution, before each retry, and after the retry loop before using saved bounds. Successful movement keeps the existing native move contract.

The pass does not certify all legal moves: guards are checked at execution, unseen blockers may reveal new information, and the precomputed Safety bounds are not reforecast after those reveals. These limits already exist in the decision model; the new retry contract is bounded to its saved candidates. Multi-turn departure/progress remains unproved.

## Emergency basic source contract

The combined arm adds a Prism-only kill-and-stay alternative after primary selection finds no evaluated surviving neighbor and staying is lethal. It deliberately skips cases where a saved surviving step was rejected. It compares the same-epoch current-tile and original selected-tile immediate bounds, both lethal against fresh native HP. If the old selection is staying, that same lethal stay is the comparison. It does not assume an attack can be followed by walking: Prism's basic spends the walk.

The selector reuses `Safety::awake_members`, already built by the original cost calls. It scans that retained list, shortlisting at most16 native-certified candidates within current native attack range and held vision. No new all-map camp enumeration, route search, enemy model or fuel gate is added. The target's group must have at most16 public members, contain no Monolith, and have an existing alive/fully-awake belief. The caps are fixed work bounds, with no fuel-dependent admission.

`Safety::after_camp_kill(p, bound, member_index)` is a pure read of that unchanged, initialized pool. It requires a valid index, positive softened Strength, no next-phase stun, and the exact same in-square reach predicate as `camp_damage(worst=true,next=true)`. It removes only this entry's actually charged contribution from the supplied same-epoch bound. A member assigned elsewhere or outside charged reach is rejected. Every other camp and enemy contribution, including credible unknown threats, stays in the bound. No whole-group subtraction, hypothetical teammate attack or new allied tanking discount is applied; the existing nearest-champion targeting assumptions remain.

The resulting stay bound must be strictly below fresh native HP and strictly below the proposed lethal step bound. The execution certificate then requires:

- Current native alive, move-ready and attack-ready flags, no recall/tribute/teleport channel, and unchanged current coordinates.
- Fresh visible camp record with the exact candidate handle/position, positive current HP no greater than the exact current basic, and native Strength matching its public design.
- Current basic from native own Strength, current passive scaling, and current Monster family multiplier. Scope is Prism, whose basic has no splash or retaliation collateral.
- Fresh native state for every damaging member of this bounded group: each is either dead or already awake, and the chosen target is awake. An asleep, unknown, absent-vision or rejected read rejects the candidate. Waking a harmful group is not admitted.
- Staleness checks after native own-state/items/target/group reads and around the original attack helper. A rejected certificate or native attack retains the ordinary fallback; no stale certificate is allowed to fall through into an old move.

A successful basic uses existing `attack_camp_target` bookkeeping, then checks staleness, calls supported `Safety::refresh()` so the observed dead member invalidates its caches, invalidates Pathing occupancy, and checks staleness again. It does not simulate death by mutating World camp beliefs or rely on `World::observe` to refresh camp health. The native camp attack is the only new successful action in this branch; no AoE/cast extension or post-basic walk is introduced.

## Evidence and qualification boundary

Astra's final source review independently verified both frozen aggregates and passed these contracts after the post-native staleness fixes. Static checks above confirm snapshots, scope and whitespace only. Neither arm has been compiled or run by this implementation task, and there is no activation, survival, fuel, rollout or match-result claim.

Farm806 is a nomination for the primary movement mechanism: the existing actor-own record admits a plausible surviving northwestern step, while the actual chosen step is lethal. The emergency child is intentionally narrower and may not activate there. The public replay's executable identity is unknown; it does not prove the current canonical branch or either child's behavior.

Root/Luna owns subsequent builds/tooling/runtime. Qualify source-known primary movement selection, native action legality, next-phase damage and actual departure/productive progress before comparing paired map/side results and default-fuel behavior. The combined arm additionally needs a source-known all-evaluated-options-lethal witness showing actual fresh-certificate basic activation and reduced next-phase damage. Existing source A/B and unused-map confirmation requirements remain applicable before accepting a gameplay gain.
