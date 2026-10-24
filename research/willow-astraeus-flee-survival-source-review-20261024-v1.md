# Astraeus camp-survival ports: independent source review

2026-10-24 UTC, Astra. **PASS for source-level port semantics.** No port-specific safety defect found. This does not qualify compilation, activation, native survival, fuel or competitive performance. Read the Cambridge Battlecode rules, actual variant diffs, current Safety/member accounting, native action wrapper, retreat and pathing guard/failure paths. No gameplay edits, build, engine, match, extraction or new tooling.

## Independently verified source identities

Aggregates use `shasum -a 256 src/* | shasum -a 256` inside each bot.

| Source | Aggregate SHA-256 |
|---|---|
| Frozen Astraeus baseline and untouched editable control | `57f6908fcac310582d5b02606d8742c76c10a57f3a871c6a09792af115289369` |
| Astraeus survival-first | `9b1fd50a2dc4918cb779c254f3e6f1eddbc936f0308d65799ed5bc521b7209af` |
| Astraeus survival-basic | `8878fff43f4eba40ea56d7546c213bc0a39ddb1d177b93d47b14a86a9028af31` |
| Approved old survival-first | `1a1ee8e788c80cd3d38b5531df9e203b253741f9ca1eda4960d22163d57d1764` |
| Approved old survival-basic | `3d18ab0a56f3646a2fc701b5d876324083ff6ba9c44b75df70daf6b4cf566b87` |

The frozen baseline matches the provenance before snapshot; both new variants match their respective final snapshots recursively. The basic child's complete `flee_camps` and `emergency_camp_basic` functions compare byte-identical with the reviewed old child. The primary changes only `bot.cpp`; the basic increment changes only `bot.cpp`, `safety.cpp`, `safety.h`. Provenance: `provenance/willow-astraeus-flee-survival-20261024-v1/checkpoint-v1.md`; prior contract: `research/willow-flee-survival-source-review-20261024-v1.md`.

## Mechanism and interactions

The primary retains the existing current-plus-eight-neighbor pool, blocked-board filtering, exit cost and home tie-break. It separates next-phase damage from the longer escape cost. When any evaluated option is lethal, it tries surviving neighbors in stable original preference order, then holds if staying survives. If all evaluated options survive, the original choice remains. Deferred guards are still evaluated by `Pathing::try_move`, not eagerly built during enumeration. Rejected surviving steps with lethal stay return to ordinary retreat; they do not open the emergency certificate.

The child acts only for Prism after staying and every evaluated free neighbor are lethal. It checks fresh native alive/move/basic/channel state and unchanged position, then a visible in-range non-Monolith member whose current HP is basic-killable. Every damaging member of the bounded group must currently be dead or awake, with the target awake. The helper subtracts only the selected member's actual stored contribution and requires the resulting stay bound below fresh HP and below the saved original selected-step bound. Success uses the ordinary exact-target basic wrapper and then Safety refresh/pathing invalidation. It is kill-and-stay: Prism's basic spends the walk. Earlier retreat priorities—champion kill, cast/reset, tribute and dash—remain ahead of it.

**New SafetyBound is compatible.** The survival code still calls `damage_bound`, whose camp term is `camp_damage(p,true,true)`. The member pool stores mitigated Strength, reduced reach and stun state. That camp sum charges exactly stored Strength for an in-range, nonstunned member. `after_camp_kill` validates that same index/reach/stun/contribution before subtraction. It preserves other camps and enemies; it neither subtracts a whole group nor grants speculative allied damage. Astraeus `bound().damage` shares this accounting, while `doubled`, `hits`, `stuns` and probabilistic `threat` remain separate. None is silently substituted into the certificate.

**Changes111/112 remain intact.** Cached visible-ally stun/teleport arrival affects fight estimation and therefore which decisions lead to retreat; it adds no future ally credit to the new helper. Change112 can consider a home-distance-increasing retreat step only when its damage bound is zero and no nonlengthening zero-bound option exists. That does not subsume survival-first's nonzero-but-nonlethal escape. Ordinary retreat still receives control after rejected surviving steps with lethal stay. Astraeus station caching, enemy guards and changed support/search entry paths remain untouched, so the frequency and ordering of activation must be measured anew.

The safety claim is relative to the existing bound, not a complete native forecast. Nearest-champion camp targeting, unseen-threat assumptions and one-phase horizon are inherited. A hidden-blocker rejection invalidates Pathing but does not itself rebuild World/Safety; stale-turn checks catch turn rollover, not newly revealed danger. This qualifies failed-step/hold cases and is not a newly introduced Astraeus mismatch. Candidate-native reads are bounded at16 admitted candidates with groups of at most16 members; fuel still needs measurement, especially SDK error paths.

## Required activation checks

1. On the exact Astraeus baseline/control and primary, retain an actor-known witness where the original exit-cost winner is lethal and an evaluated neighbor survives. Record HP, each immediate bound and exit cost, blocked/guard rejection, selected action, native damage/death and the next decision. Include an all-surviving witness for unchanged choice and a rejected-step witness for fallback/staleness behavior.
2. For the basic child, require a separate true all-evaluated-options-lethal witness. Record the live action/channel flags, target HP/basic damage, all damaging group-member states, charged member contribution, post-kill bound, actual kill/no movement and ensuing damage. A surviving-step case cannot demonstrate emergency activation. Sleeping, stunned, Monolith, unreadable, nonlethal-step and unaffordable-kill cases should decline through the stated predicates.
3. Verify source-known default-fuel native runs, interruption/error behavior and later survival/conversion, then the paired suite if activation supports the mechanism. Old4db outcomes and the public Farm806 nomination do not establish Astraeus activation; public match source identity remains unknown. Keep primary and emergency effects separate.

Reject the proposal if source-known activation fails to remove the predicted charged threat, if a preferred survivor causes worse native immediate survival than the original action, or if extra work repeatedly loses required actions to fuel. A nonactivation result motivates finding the correct witness, not a competitive claim or broader gates.
