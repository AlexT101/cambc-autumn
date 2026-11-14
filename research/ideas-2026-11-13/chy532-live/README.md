# Charybdis 532 with book: live performance

Platform **v138**, submitted at23:40:14 UTC on2026-11-13, became active and
REST at23:49:20. It contains532 (`9ad13ba8347929f83383fe942dbe618d0429153c`)
and40 inherited book entries:31 Fish and9 Mite. The user explicitly requested
immediate submission after release build/smoke, with remaining checks afterward.
All64 uploaded source files matched the frozen combined artifact, unmasked.

The subsequently requested unranked sweep was planned to cover all170 ladder maps from
both sides, separately against Fish r10 and Mite r15. It measures **book-enabled
532**, not natural532 strength. The62 qualification cells are reused; only the
remaining307 Fish and311 Mite cells are queued. Fish runs first. v138 remains
REST and selected for Finals throughout; quota refills do not require another
version upload. The user permanently cancelled all unrankeds at23:56 UTC, before full collection.

Pins:

- Fish r10: `01a1d732-2d11-7f85-85fa-f4953aad836c`, captured23:15:52 UTC.
- Mite r15: `01a1d706-59a1-78b3-9db5-8109569b1865`, captured22:28:00 UTC.

Run `python research/ideas-2026-11-13/chy532-live/audit_performance.py --out
/home/ubuntu/tmp-offload/live-chy532/performance-results.json`. The
`chy532-live-performance-audit` user service previously refreshed that artifact
every60 seconds; it is now stopped and must not be restarted without explicit
new user authorization.
It checks creation-time own version, opponent source, task/result correspondence,
coverage, duplicates, and suspect/dropped groups. It does not claim replay CRC
validation. The book worker separately audits the62 qualification replays.

Runtime plan, source audits, and submission receipt are in
`/home/ubuntu/tmp-offload/live-chy532/`. The book work and remaining local checks
are in `/home/ubuntu/tmp-offload/rbook/chy532-book40-r10-r15/`.

At23:52 UTC, all33 Fish qualification cells were collected:8/31 target losses
became wins, while one of two baseline-winning collateral cells lost. This is
net+7 versus531 on those33 cells. Holding all other cells fixed would give
149/340 (43.8%); that is a conditional calculation, not a measured full-ladder
rate for532. The partial9/33 rate is deliberately loss-weighted and must not
be presented as overall strength. Earlier531 without book scored142/340
(41.8%) on Fish r10 and228/340 (67.1%) on Mite r15.

## Permanent stop and final results

The user permanently stopped all unrankeds at23:56 UTC on2026-11-13. The
scheduler, runner, and audit watchers are stopped, with persistent scheduler
STOP/HOLD and runner STOP markers. All995 previously unsubmitted tasks were
cancelled, including legacy parked work; remaining after-queue steps were
removed and the active sweep archived. No restart timer exists.

All15 already-submitted v138 groups finished. A final read collected their
outcomes without creating games or downloading more replays. Final coverage is
**Fish12/43 (27.9%) and Mite22/29 (75.9%)**, excluding three filler games.
These deliberately targeted partial samples do not estimate full-ladder rates.
On those same cells,531 without book had6/43 and20/29 respectively: net+6 Fish
and+2 Mite for the combined532-plus-book build. This comparison cannot separate
the new draft's effect from the book's effect.

Results and provenance are in `stopped-results.json`. The last three Mite groups
were collected outcome-only, so complete replay-archive validation is not claimed.
At the post-deadline API check, v138 remained active and selected, with
`frozen=true`. The exact1,240,360-byte source bundle is preserved at
`/home/ubuntu/tmp-offload/live-chy532/v138-source.zip`, SHA256
`da3c59e6dfaa4b22874f559bc63970da9a4014e9af9409d322939ac1fece3731`.
