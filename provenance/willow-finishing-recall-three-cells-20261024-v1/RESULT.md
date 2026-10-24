# Finishing-recall three-cell follow-up

All three authorized Release 100k games completed with normal drafts and zero failed rows. Builds were already up to date; source, SDK bytes and SDK mtimes were left unchanged.

| Game | Result | Candidate A native status | Candidate Prism (actor 0) | Parent comparison |
|---|---|---|---|---|
| f599 parent A vs v33 B, Big World | A 1000–757, r953 | 3 rollovers, 0 errors | control only | Reference for candidate Big World |
| finishing-recall A vs v33 B, Big World | A 1000–757, r953 | 3 rollovers, 0 errors | 510 collected/submitted, 0 bag, 0 deaths, 1016 damage dealt / 31.5 taken | Exact payload match to parent game above; 35,585 inputs on each side, no first input divergence, 954 rounds match |
| finishing-recall A vs v33 B, Pilgrimage | A 1030–210, r1358 | 0 rollovers, 0 errors | 141 collected/submitted, 0 bag, 0 deaths, 1940.5 damage dealt / 720.875 taken | Exact match to reused parent A vs v33 B control; 51,803 inputs each, no first input divergence, 1,359 rounds match |

Opponent v33 had 8 rollovers and 0 errors in the Big World games, and 6 rollovers and 0 errors in Pilgrimage. Statuses were counted from per-champion round snapshots (code 6=rollover, code 7=bot error), not aggregate fault bytes.

Candidate Prism’s recall event counts were 851 starts / 839 cancels / 12 ends on Big World and 1,326 / 1,323 / 2 on Pilgrimage. The Big World candidate output exactly matches the newly run f599 parent output, and the Pilgrimage output exactly matches the saved parent control. The targeted recall change therefore made no observable gameplay change in these cells; all candidate outcomes, inputs, replay payloads, and per-actor state match their parent controls exactly. These fixed-cell diagnostics do not establish general competitive strength.

See [`RESULT.json`](RESULT.json) and [`PRESERVATION-MANIFEST.json`](PRESERVATION-MANIFEST.json) for bundle/inner-payload pins, full per-actor status, controls, and duty receipts.
