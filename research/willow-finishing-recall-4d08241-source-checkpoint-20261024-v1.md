# Finishing recall source checkpoint

2026-10-24. Read Cambridge Battlecode rules and `research/willow-prism-finishing-recall-known-info-20261024-v1.md`, including cost/API and decisive-capture fixtures. Gameplay source only; no build/game, scripts, extraction, SDK/tool change, canonical edit, EXPERIMENTS change or numbered release.

Frozen parent `bots/baselines/astraeus-4d08241`, aggregate `f599a31faa0251321beb97a726918286e266218ceb3e183b8271e41c5c84718c`; all29 parent source checksums verified unchanged.
New isolated child `bots/variants/willow-finishing-recall-4d08241-work` (src only, no .cambc).
Source manifest `research/willow-finishing-recall-4d08241-source-v1-manifest.sha256`, aggregate `781fe3641afc4333d8c8a1b42f1344b4ba19edf9d96ae092e9e62069b9083d68`.
Delta `research/willow-finishing-recall-4d08241-source-v1.patch`, SHA256 `51de2a6cd43dcc820f387adaf34cacaa5cfd65cbd24d6d0e0cf12cf78cf68f5a`.
Only bot.cpp changes:22 insertions/4 deletions. No whitespace diagnostics from no-index diff check.

The root-reported trusted latest-parent prefix matched27,690 inputs/739 hashes. Its737 home=true becomes738 home=false specifically when paying_soon suppresses already-evaluated pack membership;738 channel1 lands739 before payout740. That establishes the narrow source cause this experiment targets. This worker did not rerun that prefix.

`want_home` has an optional bool output initialized false before every early path. Its existing outmatched query preserves in_pack_zone-before-paying_soon order and skips paying_soon when outside the pack. It sets the output only from the already-evaluated true pack/true paying-soon result. Low-health short circuit, spawn return, lethal/stand/pursuit logic and ordinary callers remain unchanged; no second pack query or Safety::stand is added.

Only continue_recall requests the scalar. Its game_ender check and normal home=true keep remain first and unchanged. In the existing held-capture branch, normal home=false plus suppressed-pack fact may retain the current channel only when it lands strictly before private payout, the current capture share is smaller than existing gems_short, and existing unthreatened → no immediate safe tribute → recall_outruns checks pass in that order. Success records the existing kept-recall decision K. The cached home remains false even on success. If any new condition fails, the original capture helper/cancellation/dispatch path continues with home=false. No global commitment, champion/round/map identity, gem threshold or fuel gate exists.

The own-winning top-up exclusion uses the existing capture_share and gems_short classifiers, including visible allies' ongoing tributes. It applies only to the new exception; it does not weaken normal home=true retreat. Existing holding_capture excludes already-winning bags and the known hold deadline case. No broader race veto or economic solver is added.

Source-case expectations for Luna's production-branch fixtures (not run here): ordinary suppressed-pack/early-arrival/safe hold may keep; own winning top-up and visible pending-tribute top-up reject only this exception; no suppressed pack and payout-at-arrival defer to canonical behavior; threatened/safe tribute/failed outrun reject in original check order; game_ender cancels first; normal home=true is unchanged even for a winning capture. Rejected contextual checks do not assign home=true or force a particular fallback decision.

Added cost is a local bool, optional stores, private timing comparison, bounded existing capture-share/shortage allied scans and previously skipped existing keep checks. No new native observation, field, board, pack scan, threat forecast or second stand simulation is added. Channel-time and existing helper scalar reads follow the same APIs as capture_recall. Actual compiled cost and behavior remain for Luna. Astra independently verified the pinned bot.cpp/all29 manifest entries and found no blocker: `research/willow-finishing-recall-4d08241-source-review-20261024-v1.md`. Source-ready for Luna fixtures/build; no runtime result is claimed.
