# Pilgrimage group 12: access, available allies and the next useful check

2026-10-24. Bounded file/source review only. **The objective loss is well established; an avoidable known-information gameplay error is not yet established.** The strongest next check is one exact-prefix v47 harness replay of the new loss, focused on Willow's post-heal step at769. Do not add a grouping rule or duplicate the newest capture-holder fix from these observations. All Willow-first ladder-manipulation batches are excluded.

Evidence is the already extracted normal five-pick pair under `provenance/ladder-history-replays-20261024-v1/`: old match `9da66955-6268-428c-a955-1549cd080c33`, payload `4ca5aa1e2eeecd1d3f25c1fe4d38d6476c8554111ca570944f93b181549d3512`; new `62589f4b-d504-4bf7-b641-f3e9de95ce9c`, payload `e546793a8c82d0bbc32eb725a0217e21b6518b72ec0818c944a04560f394a96d`. Read `extract/astraeus/<first16>/rounds.json.gz` and bounded `events.jsonl.gz` selections; map `extract/astraeus/maps/8caf8eb913649931.json`; native Willow window `actor-window-exports-v1/three-pilgrimage-new-willow3.json`, with hashes/alignment in `actor-window-run-receipt.json`. Source attribution for these public games remains unknown. The preceding matched review preserves the full capture timeline.

## Control was lost before the capture channel

The shared 4×4 block x23–26/y56–59 contains four Elk, eight Gold clusters and four Gem clusters:88 gems,520 base gold,60-round respawn. Through the same1403-round horizon, own group12 rewards fall440→88 gems and enemy rewards rise176→704. Clears convert in6–8 rounds without a recorded capture reset. The main observed failure is access to productive clearing and territory, rather than repeated abandonment of an already-cleared winning capture.

The new loss's local sequence is particularly concrete:

- r768 enemy Vesper8 attacks Marcella2 for295 from the bush at22,54. At Willow's769 activation she sees only ally Marcella21,57,1163/1500HP, and no enemy. She heals337 from18,57 (`s155853`), then moves19,57 (`s155854`).
- Vesper attacks Willow late769 for295, then attacks/resets first770 and kills her before her next activation (`s155888`, `156034–156036`). Willow had no intervening escape turn. Vesper's personal ward23,54 was placed764; this is observer evidence, not Willow's knowledge.
- Marcella still performs useful clearing:90 damage to Gem64 at770, its remaining30 at771, then420 Damage to Elk18. Vesper chases and kills her777. Enemy Prism6 casts into the block at773/775 and lands its final clearing hit777; his88-gem payout follows784. The support loss therefore precedes the clearing loss, but it does not prove that preserving Willow alone would win the contest.

## Nearby bodies were not an immediately available rescue team

These are observer end-round positions and geometric lower bounds, **not** route lengths, actor knowledge or readiness promises.

| Situation | Own local bodies | Other available-position context |
|---|---|---|
|New769, before the fatal next activation|Marcella21,57; Willow19,57|Prism24,39 is at least17 steps from group12; Vesper15,35 at least21; HoR32,3 at least53. Only Marcella is visible in Willow's native start observation.|
|New777 clear|Marcella/Willow dead; own Prism23,46|Prism is still at least10 walking steps from a camp tile, with seven rounds until payout. This is not an obvious missed immediate capture intervention.|
|Old983 clear →989 own payout|HoR26,57 alone on the group|Vesper9,49, Prism5,45, Marcella3,42, Willow4,31 are all distant. Enemy Prism had died946 to HoR, transferring103 gems; no constant Willow formation was required for this first takeover.|
|Old1127 clear →1133 own payout|Willow22,57 and HoR26,57; both become paid holders|This later visit does include local support. It is one successful configuration, not evidence all approaches should wait for it.|
|New1070 clear →1076 only own payout|Prism25,54, Vesper22,57, Marcella22,56, HoR24,57|Willow is10,57 at1070 and16,56 at1076, outside immediate heal range. Useful conversion is possible without waiting for Willow.|

At old1214 Marcella also receives a solo88-gem payout while Willow is3,46. Successful visits vary with opposing occupancy, local damage and opportunity; a blanket “stay together” rule would discard observed productive configurations.

## The narrow actionable uncertainty is the post-heal movement

At new769 the heal already lands from18,57. The step to19,57 still leaves every group12 member outside Willow's basic range3; the nearest camp x-coordinate is23. The export identifies only Gem64 at23,59 as currently known alive120HP; adjacent camp entries are static-map-only. Thus this step supplies prospective route progress, not another immediate heal or a current group12 basic. The visible ally's recent injury is real information, but it does not reveal the hidden attacker's location or prove that staying is safe against a mobile opponent.

Under frozen f7 source, `local_support` requires a visible Prism endpoint; none is in this observation. `willow_independent_heal_step` declines when the heal already lands from here. The accepted heal-then-walk sequence is consequently more consistent with an ordinary farm or retreat continuation than with following a Prism formation. This is a source-informed nomination, not attribution of the public branch. Existing Willow `guard_steps`/station safety already considers credible unseen threats. Without its actual enemy beliefs, guard evaluation and chosen goal, adding another risk gate would be speculation.

Latest upstream `2d62cdb` (in fetched `4d08241123b88ad0365d4b0ad346cd65a329b699`) already changes `capture_taken` to exclude visible off-target allies bound to tribute, a kept recall or another claim, while counting actual occupants. It should not be reimplemented. The current pair provides no corresponding cleared-camp abandonment witness, and routine recall stubs at timer4 are not evidence those allies have committed to leave. That fix is relevant source context, not an explanation established for this loss.

## One bounded follow-up, not another broad panel

The fetched harness README and `trace-bot/TRACE_SCHEMA.md` now describe `--version v47`/`trace-bot-v47`, pinned to f7d54e9e. Recommend one later sole-worker job on the **new** Pilgrimage payload: validate release versus opponent puppet through the target769 activation; if it differs earlier, report the first mismatch and stop attributing subsequent private branches to this public game. Only if the prefix matches, validate recorder/trace trust through the same activation and inspect763–769, actor3. The repo's reported320/320 release matches and302/320 recorder matches concern its own cohort and do not prove this selected game matches.

Read the existing trace's actual `TE home/decide/support`, farm target/candidate decision, enemy beliefs and guard/exposure information. The decisive question is whether19,57 was admitted because (a) the relevant threat was absent from beliefs, (b) a known threat was evaluated but the destination/continuation logic admitted it, or (c) the turn was a different goal/retreat branch. Preserve the337 heal when comparing any candidate continuation. An unmatched or untrusted prefix supplies no private-state explanation; an exact trace that consistently prices both endpoints as safe falsifies a claimed known-threat guard inconsistency and shifts the issue to information quality.

This is a precise diagnosis experiment with existing tooling, not authorization to implement a hold-position rule, force a fight, redirect distant allies or run a new broad panel. No new replay download, decoder, helper, simulation or build was performed for this note.
