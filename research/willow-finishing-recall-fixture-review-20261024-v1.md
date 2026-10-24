# Finishing-recall decision fixture review

**Final v4 follow-up: the two sensitivity gaps below are closed. No remaining blocker to treating this as bounded source control-flow qualification.** Final pins and scope are recorded at the end; the initial review is preserved as history.

2026-10-24. Source-only review; no tests, builds or helper edits performed. **The extracted branch fixture is meaningful; no gameplay-source blocker. Two mutation results need narrower interpretation/correction before claiming targeted sensitivity.** Worker packaging was active, so pins below identify the inspected version rather than a final immutable package.

Root: `provenance/willow-finishing-recall-decision-fixture-20261024-v1/`.

- `src/extract_fixture.py`: `25cdf8a84b9d7908d78b2aa93c146dc06e2fe6d0fd019cccf84f06722005313b`.
- `src/fixture_harness.cpp.in`: `3a025b956a4cdc50b27c99a631a60dcccc76fac4ad1d1ba9b4adf8c41ca78e7e`.
- `src/mutation_checks.py`: `25a1ff45de62208e17c000fe2cdf13b8d496b1849977a79bdda563d1be288494`.
- `generated/fixture.cpp`: `ab432e7317fcc2f93fc9d12a7e7ed001956d21502c4e29645557be03c8039e9a`.
- Production `bot.cpp`: `12b287870f0e516829ccd0ce47765391e273729af1529fdc3df2f719da060d46`.

## What the fixture establishes

The extractor rejects a different whole-file production SHA and copies the unchanged bodies of `outmatched`, `want_home` and `continue_recall`. The inspected generated bodies match the pinned patch. Its brace scanner suffices for these actual bodies; no replacement policy algorithm is substituted. World, Safety, native accessors and other helper results are explicitly mocked. The expected booleans and call counts are literal independent assertions, not recomputed by the tested predicates.

The positive case exercises the full extracted home path, including one stand call, then keeps the channel with cached `home=false` and no cancellation. The equality top-up case tests the strict winning-share exclusion. The game-ender case expects cancellation before home assessment, absent home value and no pack/payout/stand queries. The no-pack and payout739 cases assert that new-path share classifiers are not called. Threat / immediate tribute / failed-outruns cases assert ordered stopping, entry to the original capture helper and preserved cached false. The normal-home case asserts no stand or new share classification. The scalar test starts its output true and reaches the spawn early return, so entry initialization is non-vacuous. The inspected `logs/test-v3.stdout.log` reports all11 named decision cases plus the scalar group passing.

Scope limits are explicit: `pending-ally-tribute-top-up-declined-classifier-mocked` supplies an already-computed `gems_short` value. It tests use of that classifier, **not** whether visible tributes, carried bags or hidden allies are accounted for correctly; it is effectively another equality boundary. Likewise the no-held-capture case tests a mocked branch condition, not the production deadline or winning-bag calculation. Fixed full health means the low-health short circuit is not exercised; spawn entry initialization is. Mock Safety results do not prove real interception, fixture positions are not the recorded738 state, and mocked accessor counters are not WASM/native fuel measurements. These are appropriate limits for this narrow decision fixture, not reasons to reconstruct the entire engine.

## Narrow correction to sensitivity claims

The inspected `logs/mutation-checks-v2.stdout.log` reports all five mutations detected, but two first failures occur in `positive-safe-pack-suppression`:

- Removing the winning-top-up expression also removes `capture_share` and `gems_short` calls. The positive outcome remains a successful keep; its call-count assertion fails before the winning negative runs. Use a call-preserving `<` to `<=` mutation to test the equality exclusion: the positive must still pass and the own-winning-top-up case should fail behaviorally.
- Replacing `if (game_ender(world))` with `if (false)` removes its call. Again the positive outcome stays correct but its count fails. Preserve the call with `if (game_ender(world) && false)`; the named game-ender case should then fail on decision/home/cancellation rather than an unrelated positive count.

Scalar-initialization removal reaches the intended initialized-output assertion; contextual-keep removal changes the positive decision; early-arrival removal reaches the named payout boundary and incorrectly keeps. Those logs support their respective behavioral claims. The current mutation runner accepts any nonzero test exit, so inspect each `first_failure` rather than treating its aggregate PASS as targeted coverage.

Sent these two small corrections to Luna, retaining prior receipts. One useful optional addition is payout739 with `capture_recall_result=true`, expecting a canonical keep with no cancellation and cached false: current tests prove fallback is called, but always mock it false and therefore do not positively demonstrate that declining the exception permits the old helper to retain the channel. This is a single fallback-result case, not another implementation. No additional broad fixture or gameplay panel is requested.

## Final v4 verification

Read the corrected runner, two mutation patches, `receipts/mutation-checks-v4.json`, updated harness/extraction receipt and `logs/test-v4.stdout.log`; did not execute them. The winning mutation now changes only `<` to `<=`, preserving classifier calls, and first fails `own-winning-top-up-declined` by incorrectly keeping instead of falling back/cancelling. The game-ender mutation preserves its call with `game_ender(world) && false` and first fails `game-ender-cancels-before-home-assessment`, incorrectly computing home and keeping. These directly address the earlier masked failures.

The payout739 case now sets `capture_recall_result=true`, asserts one canonical helper call, no cancellation and cached `home=false`. Its early-arrival mutant still returns true, but skips the canonical helper and enters contextual safety checks: the intended delegation/call-count assertions correctly distinguish those paths. This is meaningful path coverage, not a claim that its final boolean differs. Scalar initialization and contextual-keep mutation failures remain at their intended assertions. All11 named cases plus scalar assertions are reported passing; all five mutation compiles succeed and test executions fail at the specified cases.

Final inspected pins:

- `receipts/FIXTURE-RESULT.md`: `4c3ad7a6fe1ae174c0258485fdef83ff96cfd43750e8fd80e6e2b5e45d67c7fa`.
- `receipts/FIXTURE-RESULT.json`: `b5bb70fa52b1fd9fb8e638ef5027c3de47a308b4c25387333f6b9f8ccb2b027b`.
- `receipts/mutation-checks-v4.json`: `60e9cea02b065b76e93cb0e5494a51be94630a237fb2c10b767124baea6da7a2`.
- `src/fixture_harness.cpp.in`: `9da86d2f167305b6bc747b2bf2033530af1468fd88a97fb83bfe72d04ba2099e`.
- `src/mutation_checks.py`: `65b9e8267b8aa138fda1f518318526940b5621c075d2a2e163aa54e3c5a844c4`.
- `generated/fixture.cpp`: `4c28fe41ad9ebb8b3d56442f61ad92425cc749bea4960ecb225ccbd66d39c026` (also the extraction and mutation receipts' base SHA).

The production source and extractor pins remain unchanged. Actual ally/pending-tribute accounting, interception and capture valuation remain mocked, as the final receipt acknowledges. The normal-home test proves that the new share classifiers are skipped, but does not independently supply a winning-share input; the receipt's “including priority over winning top-up” is a source-flow inference from that bypass, not an additional instantiated case. No new test is needed to preserve that distinction. This qualification does not measure native fuel, recreate738 private state, or establish the reactive game's outcome or competitive benefit.
