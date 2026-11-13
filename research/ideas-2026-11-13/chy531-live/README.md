# Charybdis 531 live comparison

In progress: platform **v132**, uploaded 2026-11-13 at18:55:42 UTC and first active at18:57:13.
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
REST remains latest book131 between quota windows. No fixed quota reserve; teammate
requests take priority as slots return. Current-Fish book repinning follows this campaign
and does not change these comparison pins.

Runtime evidence and completion auditors are in
`/home/ubuntu/tmp-offload/live-chy531/`: `intent.json`, `played_progress.py`,
`final_audit.py`, and `audit_archives.py`. The final audit requires all680 collected
records, matching pin provenance and frozen uploaded source. Archive verification
checks every ZIP's CRC and the presence of its replay and binary summary.
Final results and archive audit will be retained here once complete.
