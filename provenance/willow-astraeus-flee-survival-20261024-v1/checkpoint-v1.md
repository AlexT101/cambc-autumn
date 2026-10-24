# Astraeus camp survival ports: source-only checkpoint

2026-10-24 UTC. Read AGENTS and the Cambridge Battlecode rules, `research/astraeus-integration-review-20261024-v1.md`, and the independently reviewed old-arm contract in `research/willow-flee-survival-source-review-20261024-v1.md`. Prepared two fresh exclusive variants. No build, match, extraction, helper script, canonical/EXPERIMENTS edit, deletion, move, cleanup or `.cambc` copy. The untouched editable Astraeus base remains a source-identical build control. This is source preparation and static verification, not runtime, activation, survival, fuel or competitive qualification.

## Frozen identities

All aggregates use `shasum -a 256 src/* | shasum -a 256` within the corresponding bot.

| Source | Aggregate SHA-256 |
|---|---|
| Frozen `bots/baselines/astraeus-e72724a` | `57f6908fcac310582d5b02606d8742c76c10a57f3a871c6a09792af115289369` |
| Untouched `bots/variants/willow-astraeus-e727-work` | `57f6908fcac310582d5b02606d8742c76c10a57f3a871c6a09792af115289369` |
| New `bots/variants/willow-astraeus-flee-survival-first-work` | `9b1fd50a2dc4918cb779c254f3e6f1eddbc936f0308d65799ed5bc521b7209af` |
| New `bots/variants/willow-astraeus-flee-survival-basic-work` | `8878fff43f4eba40ea56d7546c213bc0a39ddb1d177b93d47b14a86a9028af31` |
| Untouched old `willow-flee-survival-first-work` | `1a1ee8e788c80cd3d38b5531df9e203b253741f9ca1eda4960d22163d57d1764` |
| Untouched old `willow-flee-survival-basic-work` | `3d18ab0a56f3646a2fc701b5d876324083ff6ba9c44b75df70daf6b4cf566b87` |

Every snapshot and manifest contains all29 files. Parent/control/old-arm before and after snapshots compare recursively byte-identical; final new-arm snapshots recursively match their variant sources. The parent's before snapshot is also the complete before state for both fresh clones. Only `src/` was copied.

| Exact source patch | SHA-256 |
|---|---|
| `survival-first-v1-vs-astraeus.patch` | `955f28fab928a8ce7c16ede29b7f5227c26e1998d4fe5baad89fa3f3667d2d7e` |
| `survival-basic-v1-vs-astraeus.patch` | `f09f8039dfee340966628876ac5341a45740e9965a7f9d88d20b3591fc093a25` |
| `survival-basic-v1-vs-survival-first.patch` | `9867f4954d8a591ee19d9b19ef823716e7dae01652fc5f453dba5d72d9f1d91a` |

The primary changes only `bot.cpp`:29 additions/6 deletions. Basic versus primary changes `bot.cpp`, `safety.cpp`, `safety.h`:79 additions/1 deletion. The added/removed line sequences of each exact patch match the corresponding old-arm patch byte for byte after excluding diff headers and hunk coordinates. No port-specific gameplay change was needed. Both no-index whitespace checks emit no diagnostics; exit1 indicates the intended source differences.

## Primary contract retained

The original `flee_camps` current-plus-eight-neighbor pool, blocked-board test, damage/camp-area/home-field queries and original exit-burden comparator remain. Each existing immediate bound is saved separately from its multi-phase exit cost. When every evaluated position is nonlethal, the original selected move/fallback remains. If any evaluated option is lethal, saved nonlethal neighbors are attempted first by original exit cost, home distance and stable compass order, at most8 attempts. A nonlethal stay is handled only after no saved step succeeds. Lethal stay after rejected nonlethal attempts retains ordinary fallback; no rejected-safe-step path triggers the emergency child. Stale checks remain before execution, each retry and after the final failed retry before saved bounds are reused.

Astraeus111/112, the common Willow retreat, zero-bound longer retreat step, deferred support station guard, observation epochs and all new support/search behavior remain untouched outside these exact additions. No removed Willow-specific escape block was restored. No Focus, make-way, ward, draft, macro or shopping policy was compounded.

## Emergency certificate and Astraeus bound proof

The basic child is reached only when staying and every evaluated free neighbor are lethal. It retains Prism-only scope, fresh native alive/move/basic flags, unchanged coordinates, no kept recall/tribute/teleport channel, and the saved original selected-tile bound checked against live HP. A single native basic spends Prism's walk; success is kill-and-stay, with no hit-then-walk extension. Native candidates are capped at16 and each admitted group at16 members. Non-Monolith, currently visible/in-range, alive and fully-awake belief predicates remain; current target HP/position/Strength and every damaging member's native dead/awake state are certified. Any asleep, unreadable or otherwise uncertified harmful member declines that candidate. Current basic damage uses live Strength/passive scaling/Monster multiplier. Stale checks after native own/item/target/group reads and around action/refresh remain unchanged.

The existing **Astraeus safety files were retained**, with only the7-line helper and3-line declaration added. Inspection establishes:

1. `Safety::damage_bound(p)` starts with `camp_damage(p,true,true)` and then adds enemy `Blow.damage` contributions. `Safety::bound(p).damage` starts with the same camp sum and adds the same enemy damage; its doubled/hits/stuns/threat outputs are separate. The port does not replace or call the new bound aggregate for its saved immediate value.
2. `find_members` stores each member's `m.strength * camp_factor_`, existing nearest-champion-reduced reach, native handle, weight and visible stun flag. This is the same contribution representation used by the reviewed old helper.
3. For `worst=true,next=true`, `camp_damage` adds exactly the stored softened Strength for every member whose reduced reach contains `p`, excluding stunned members. It does not multiply that worst-case term by the member's uncertainty weight.
4. `after_camp_kill` requires the initialized, unchanged member pool and a valid index, positive nonstunned Strength, that same `in_square(p,pos,reach)` condition, and a supplied bound at least that contribution. It subtracts only this stored softened Strength. Other camp terms, enemy terms, mitigation and inherited targeting assumptions stay in the supplied bound. It neither removes a group nor borrows future ally/heal damage. The helper is valid for this same-epoch `damage_bound` input; it does not assert that Astraeus's probability predicate or doubled bound is interchangeable with it.
5. The selector requires the resulting stay bound strictly below fresh HP and strictly below the saved lethal selected-step bound before executing. A successful existing attack helper is followed by stale checks, supported `Safety::refresh()` and `Pathing::invalidate()`. It does not synthesize World camp death or replace Astraeus invalidation logic.

This proves compatibility with the current source's charged camp contribution, not an exact native prediction under changed hidden information. Saved bounds still inherit nearest-target and unseen-threat assumptions; hidden-blocker reveals do not trigger a new forecast in this mechanism. Passing a single phase does not establish a complete escape or safe conversion.

## Runtime handoff

Both exact Astraeus ports need their own review and source-known activation/native/default-fuel observations. Old4db results and the public Farm806 nomination do not transfer. The primary may choose a surviving step before the basic arm becomes eligible. Preserve separate source/runtime identities and use a true all-evaluated-options-lethal witness for emergency activation. Root/Luna owns any subsequent tooling, build or runtime authorization; the running1104 audits were not touched.
