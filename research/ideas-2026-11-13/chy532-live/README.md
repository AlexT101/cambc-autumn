# Charybdis 532 with book: live performance

Platform **v138**, submitted at23:40:14 UTC on2026-11-13, became active and
REST at23:49:20. It contains532 (`9ad13ba8347929f83383fe942dbe618d0429153c`)
and40 inherited book entries:31 Fish and9 Mite. The user explicitly requested
immediate submission after release build/smoke, with remaining checks afterward.
All64 uploaded source files matched the frozen combined artifact, unmasked.

The subsequent user-requested unranked sweep covers all170 ladder maps from
both sides, separately against Fish r10 and Mite r15. It measures **book-enabled
532**, not natural532 strength. The62 qualification cells are reused; only the
remaining307 Fish and311 Mite cells are queued. Fish runs first. v138 remains
REST and selected for Finals throughout; quota refills do not require another
version upload. Full collection extends beyond the23:59 Finals deadline.

Pins:

- Fish r10: `01a1d732-2d11-7f85-85fa-f4953aad836c`, captured23:15:52 UTC.
- Mite r15: `01a1d706-59a1-78b3-9db5-8109569b1865`, captured22:28:00 UTC.

Run `python research/ideas-2026-11-13/chy532-live/audit_performance.py --out
/home/ubuntu/tmp-offload/live-chy532/performance-results.json`. The
`chy532-live-performance-audit` user service adds `--watch`, refreshes that
artifact every60 seconds, and exits when both340-cell sweeps are collected.
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
