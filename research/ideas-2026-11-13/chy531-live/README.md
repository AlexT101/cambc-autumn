# Charybdis 531 live comparison

Parked on user instruction at19:46 UTC: platform **v132**, uploaded 2026-11-13 at18:55:42 UTC and first active at18:57:13.
Frozen source: `bots/variants/chy-531`, main commit `c451e3387`.
The uploaded workspace's61 source files match that commit exactly; the sorted
`relative path + NUL + contents` SHA256 is
`ba9aea9dfe30cde533409098897c21e0c03fb67f55e940733413bf74a1ecdc3d`.
Release build and smoke passed. Own drafts, book-free, unmasked.

Compare against completed book-free **529/v129** on all170 ladder maps, both sides,
against Fishr8 and Miter13:680 unique cells,136 five-game groups, no filler games.
The opponent source groups are:

- Fishr8: `01a1d01f-2b0c-7df1-8dfe-43830d22b20b`
- Miter13: `01a1d598-e831-779c-b788-7710ca8d3f9a`

The campaign uses `data/set-full170.json`, ordered by an outcome-independent hash.
Each four-group block covers five maps against both opponents from both sides.
The scheduler's explicit baseline is129, independent of its legacy control118.
The user prioritized the new Fish pin and book over completing this comparison.
100 groups /500 games were submitted; the remaining36 groups /180 games are held in
the scheduler's `parked_task_ids`, with the original campaign archived locally.
Fishr9's book-free host baseline and loss-only book refresh run first. The collected
comparison retains its original Fishr8/Miter13 pins. See `partial-results.json`.
The new Fish baseline uses **v132/531**, and the replacement book will use the same host.
The briefly prepared v128 baseline submitted zero games and is held.
All500 submitted comparison replays passed ZIP CRC checks, with binary summaries present
(`partial-archive-audit.json`).
REST became **v133 (531 + 51-entry book)** at20:30:26 UTC, replacing v131's525 host.
The scheduler now switches between v132 book-free531 and v133 book531, with no fixed quota reserve.

## New Fish r9 baseline

The separate latest-Fish campaign uses v132 against source group
`01a1d67e-e307-7f33-9412-90716c3b4ad9`. It covers all170 ladder maps from both sides:
340 unique cells in69 groups, including five filler games that are excluded from win rates.
`audit_fish_r9.py` checks the planned map coverage, own version at creation, opponent pin,
suspect/dropped groups, and result provenance. It writes `fish-r9-results.json`; use
`--require-complete` for a final audit. This campaign collects outcomes and drafts only;
it does not claim downloaded replay archives. The old500 archived comparison games remain intact.
Results on r9 must not be described as a same-pin comparison with529's r8 results.

Completed at20:37 UTC: **159/340 wins (46.8%)**, 181 losses. All69 groups and345
outcome records collected; five filler records excluded. The final audit passed
with clean provenance and complete map/side coverage (`fish-r9-results.json`).

## New Mite r14 baseline

After the same-v134 direct comparison proved r13 stale, v132/531 played all170
ladder maps from both sides against fresh Mite source
`01a1d6cd-2c33-7999-a960-ab7bd32a52c1`, captured at21:25:32 UTC.
Completed at21:40 UTC: **224/340 wins (65.9%)**, 116 losses. All69 groups and345
outcome records are collected; five fillers are excluded. Source provenance,
own version at creation, and complete map/side coverage passed the final audit.
This baseline is outcome-only, with no replay archive claim.

Reproduce with `python research/ideas-2026-11-13/chy531-live/audit_fish_r9.py
--opponent mite --refset r14 --pin 01a1d6cd-2c33-7999-a960-ab7bd32a52c1
--require-complete`. Results are in `mite-r14-results.json`. Runtime handoff and
task IDs are in `/home/ubuntu/tmp-offload/live-chy531/mite-r14/`.

## New Mite r15 baseline

The matched v136 probes showed r14 stale on all five cells, including changed
ordered drafts. The evidence is in `../rbook/mite-r14-stale-v136.json`.
Book-free v132 captured r15 at22:28:00 UTC, source
`01a1d706-59a1-78b3-9db5-8109569b1865`.

Completed and audited at22:36 UTC: **228/340 wins (67.1%)**, 112 losses.
All170 maps and both sides are covered by69 collected groups; five filler
records are excluded. The audit passed own-version, pin, and result provenance
checks. This is outcome-only collection, with no replay archive claim. The r14
and r15 rates concern different opponent pins and are not a bot-change A/B.

Reproduce with `python research/ideas-2026-11-13/chy531-live/audit_fish_r9.py
--opponent mite --refset r15 --pin 01a1d706-59a1-78b3-9db5-8109569b1865
--require-complete`. Results are in `mite-r15-results.json`; runtime handoff is
in `/home/ubuntu/tmp-offload/live-chy531/mite-r15/`.

The original 529-to-531 comparison remains parked at500/680 games. Its runtime
auditors in `/home/ubuntu/tmp-offload/live-chy531/` (`final_audit.py` and
`audit_archives.py`) require680 records and do not audit these completed
opponent-pin baselines. Its500 collected replay archives remain preserved.
