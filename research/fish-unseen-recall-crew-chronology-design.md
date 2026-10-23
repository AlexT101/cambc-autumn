# Unseen recall and crew chronology: bounded diagnostic design

Read-only,2026-10-23. Compared exact4c4, frozen upstreamfbda source15dcd64 and current source337f; no edits to gameplay, controls or runtime. This refines `willow-fish-same-roster-source-bisection-review.md`. It does not attribute the emulator strata to a source block without a gate witness.

## Smallest useful ablation

In4c4 `World::update_champion`, an unseen recall passing its presumed end overwrites `pos`, `pos_round` and `pos_source` with inferred spawn. Upstream107 correctly preserves the last sighting because the channel might have been cancelled. Both versions still reset remembered health/scale and clear the active `channel`; `seen_channel` remains recall until another live record arrives.

The unchanged farm `work_arrival` (`fbda bot.cpp:1941–1983`) admits an invisible anchor only when `pos_source==seen`, `pos_round==stats_round`, stats round is positive, position is in bounds, and seen channel is not teleport. Thus the upstream retained record can qualify where4c4's inferred record did not. An invalid anchor returns a default arrival whose `delay()` is0, rather than unknown or infinite.

For a **farm-only diagnostic**, add one exclusion to `seen_anchor`: reject `a.seen_channel==Channel::recall && a.channel==Channel::none`. This recreates4c4's default-delay0 consequence for the just-described retained unseen-completion records, without reverting World metadata, enemy sighting acceptance, score/bag fixes or other ally-position consumers. It is smaller and more attributable than reverting the entire ad70701 commit or adding back spawn writes. The invisible-source/anchor predicates remain the outer qualification. It is intentionally an optimistic diagnostic, **not a correct production remedy**.

An ally-only restoration of the three spawn assignments inside the unseen recall-completion branch is the smallest direct World ablation, but would also alter other consumers of ally position; prefer the farm-only gate if the purpose is crew valuation. Neither is authorized here.

## When it can actually change a choice

The ally must still have a same-group posted claim, be alive/unseen, retain a last seen record of a recall that has passed its presumed end, and have positive remaining earliest-arrival delay. If it was last seen already in attack/cast reach of that group, the direct earliest delay is0 despite the recall; if enough rounds have elapsed, aging also makes delay0. Those common cases are **identical** before/after this source change. Genuine retreat normally clears the worker's claim, further narrowing applicability. A moving end-turn recall stub can remain claimed and be cancelled out of our sight: that is a concrete way to reach this record combination without a real recall ever completing. An unclaimed candidate does not use this crew branch, and a visible ally was not affected by the metadata removal. A first clear before any applicable observed recall completion cannot be explained by it. No saved actor-view/branch trace yet demonstrates these conditions in a regression cell; do not promote it from possibility to cause.

The earliest-arrival envelope deliberately allows immediate recall cancellation, no terrain/cast conflict, unknown Home and ready spawn dash. Vendetta additionally gets optimistic repeated kill-refunded dashes. Retained recall does not therefore mean a mandatory wait at spawn. Do not reinterpret its remaining timer as certain channel commitment.

## Exact formula influence and an example

For self travel `steps`, respawn wait-at-group `waiting`, and claimant output `O`, `crew_work` subtracts `O * min(working,delay)` from the predicted pre-arrival work, where `working=max(0,steps-waiting)` and `delay=max(0,anchor_round+earliest-now-waiting)`. The claimed branch then computes:

```
health_left = H - max(0, others * working - delayed_damage)
rounds = health_left / (self_output + others)
part = self_output * rounds / H       // except a winning capture uses 1
value = rate((weighted_gems + weighted_gold) * part, trip + rounds)
```

Both HP and deadline filters use the resulting rounds/share. Larger delay leaves more work for us, so the change can **increase** our predicted reward share and resurrect a formerly skipped camp, even while increasing clear time. It is not simply an extra travel penalty that discourages gold camps.

Concrete known-information example, not an observed game: at100 an already-acted no-dash claimant is seen recalling, nominal end105,21 tiles from its claimed camp with modeled reach4. `earliest_work_delay(17,1,...)` is17; let the optimistic route from spawn be25, so direct17 wins. It remains unseen at106. Upstream retains the record, giving delay11;4c4's inferred-spawn record produces default0. With self steps10, no respawn wait, H1500 and self/claimant output100 each: old prework1000 leaves500 HP, own clear2.5 turns and own share1/6; retained-record prework0 leaves1500 HP, clear7.5 and own share1/2. For H1000, old would reject `health_left<=0` while new sees work remaining. These are actual consequences of the source equations, independent of enemy pressure. Ownership at payout is still not guaranteed by proportional damage share.

## Correct direction preserving information

Keep the World fix. The actual modeling gap is that unknown arrival maps to the same0 used for already-here, while delayed arrival is applied only before **our** arrival. If a claimant's remaining delay exceeds our travel, `rounds=health_left/(self+others)` still credits its full DPS immediately when we reach the camp. In the example above it arrives at least one turn after us; with the same optimistic output assumptions, the clear takes8 turns rather than7.5.

A bounded prospective correction would preserve `known anchor` separately and carry each claimant's residual delay into the forecast. With at most the existing small ally roster, solve `H_left = S*T + sum(O_i * max(0,T-residual_i))` by ordered arrival breakpoints or another exact bounded piecewise calculation, and compute our contribution from that same T. Unknown/uncertain remote work must remain distinguishable from already engaged work. This improves internal value consistency, but earliest possible arrival and a posted claim still do not promise that an unseen ally will help. Do not use them to make an otherwise unsafe entry affordable; retain own-HP admission or separately verified current local support. No future heal or tank guarantee is introduced. This is a larger semantic repair than the diagnostic gate and should wait for a witnessed actual error, not be bundled into the current controls.

## Stronger next early-game branch to check

If the exact unseen-completion gate never executes with positive delay, inspect107's `awake_over` change before broad combat/late-bank reversions. It directly affects `finishing_camp` and the shopping recall veto (`fbda bot.cpp:2513–2540,3335`). Old code returned true for any live non-asleep group's static threat footprint when `asleep==0`; the new code requires a live damaging awake member actually reaching the tile. Dense partially cleared groups can have only dead/harmless members covering our position. Then old `finishing_camp` can return true with zero modeled damage and suppress the low-health recall, while new returns false and `want_home` recalls. If harmless members remain, a kill-reset worker may lose a cheap finishing opportunity even though the per-member danger fix itself is correct. This needs a low-health/remaining-member witness; it is not evidence to restore false camp fire.

Minimum discriminator: `health<recall_fraction*max`, not holding/winning, old static awake predicate true/new member predicate false, remaining camp HP/types/current attack reach, `finishing_camp` result and chosen home/shop branch. If activated, a separately justified safe immediate-finish exception could preserve the corrected danger model; do not infer affordable completion from old group coverage alone. Capture hold dating is the next ownership-specific block when its unseen-last-round/holder-change gate actually executes. Neither threat geometry nor teleport/ward rules can explain an early cell where their necessary enemy/teleport/ward predicates never occurred.

The current97 factorial/high-fuel results and the emulator's caught97 limitation remain separate. Identical high-fuel same-handler BossBattle trajectories support a budget-mediated integration difference there; this upstream chronology hypothesis does not supersede that finding.
