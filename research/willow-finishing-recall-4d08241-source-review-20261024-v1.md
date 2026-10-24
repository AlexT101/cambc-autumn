# Finishing recall: independent source review

2026-10-24. **Source-ready for the bounded fixture/build; no correctness blocker found.** This is not a runtime gain or survival claim. No build, game, helper implementation or canonical edit was performed for this review. Willow-first manipulation batches are excluded.

Reviewed child `bots/variants/willow-finishing-recall-4d08241-work` against frozen parent `bots/baselines/astraeus-4d08241` (aggregate `f599a31faa0251321beb97a726918286e266218ceb3e183b8271e41c5c84718c`). Only `src/bot.cpp` differs; all29 source-manifest entries verify. Pins:

- Child `bot.cpp`: `12b287870f0e516829ccd0ce47765391e273729af1529fdc3df2f719da060d46`.
- `research/willow-finishing-recall-4d08241-source-v1.patch`: `51de2a6cd43dcc820f387adaf34cacaa5cfd65cbd24d6d0e0cf12cf78cf68f5a`.
- Source manifest: `781fe3641afc4333d8c8a1b42f1344b4ba19edf9d96ae092e9e62069b9083d68`.

## Policy and short circuits

Child `bot.cpp:2820–2824` preserves the original `in_pack_zone && !paying_soon` order and does not evaluate payout when the pack test fails. The output records the actual payout suppression; it does not rerun either query. `want_home:2854–2861` initializes that output false before spawn and low-health early exits. All other callers retain the default null output; the normal result, camp checks and fight assessment are unchanged. `outmatched` has only this caller, so its reliance on the caller's initialization is satisfied.

`continue_recall:4163–4174` preserves game-ender precedence and the complete normal `home=true` keep. The new branch (`4176–4186`) requires the existing held-capture condition, normal `home=false`, actual pack suppression, arrival strictly before private payout, and a non-winning capture share. It then uses the same threatened / immediate-safe-tribute / recall-outruns order as the normal home keep. It returns without cancelling or restarting only if all pass. The held-capture test establishes a valid group index; no intervening gameplay action changes the actor's tile before the group lookup.

The strict `capture_share < gems_short` correctly excludes equality and larger winning top-ups, using the existing visible-holder split and pending-tribute accounting. It is limited to the new exception, so it cannot weaken an existing normal safety retreat. The original capture helper, shop/bank alternatives and cancellation path remain intact. A failed contextual keep leaves the stored normal `home=false`; there is no hidden forced-retreat result, persistent commitment bit or change to claim/banking memory. A successful keep uses the existing `K` decision label without pretending that the normal home result changed.

## Cost and evidence limits

Scalar plumbing introduces no additional Safety call or native read. The rare policy branch is **not zero-cost**: `my_position`, `my_channel_time` and `gems_short`'s `my_gems` are actual self host reads (`util.h:78–98,245–249`), and capture sharing scans visible allies. Existing safety/tribute/interception checks now execute on a path where the parent skipped its home keep. If the exception fails, the original capture helper can repeat an existing safety check. These costs are confined by the source conditions; no second `want_home`, second `Safety::stand`, new enemy observation, path field, allocation or independent economic forecast is introduced by the delta. Exact fuel effects remain a runtime question, including compiler effects outside the new branch.

The trusted parent trace in `research/willow-prism-finishing-recall-known-info-20261024-v1.md` confirms pack suppression at738, but the parent skipped `recall_outruns` there. The candidate must actually pass that existing check; this source review does not assume the fixture or native witness will activate. Keep the previously specified positive/negative decision fixtures, including false scalar initialization, equality at the winning-share boundary, unchanged normal-home behavior and cached-false fallback. Native reproduction should establish the new decision and subsequent behavior separately from the source verdict.
