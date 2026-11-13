Committed `5b10912a1` as CHANGES 531. **The 10% target was not met**; further cuts stopped paying after 15 development variants.

Kept shared camp-exposure calculations, deferred support/medic queries, ward-search reuse, and a fix for querying allies hidden after movement.

| Confirmed measurement | Before → after | Change, 95% CI |
|---|---:|---:|
| Release exhausted turns | 179,881 → 174,727 | −2.87% [−4.57, −1.21] |
| Debug exhausted turns | 38,574 → 37,313 | −3.27% [−7.58, +1.37] |
| Uncensored debug shortcuts | 2,408,156 → 2,352,266 | −2.32% [−4.20, −0.43] |

Release win rate: **50.40% [49.72, 51.09]**, over 20,400 fresh-map games.

100M identity: **146/228 directly identical; 228/228 in diagnostics** isolating the recall-query bug and existing preparation coupling. All champions were covered.

`bots/charybdis` matches the tested candidate. Completed replays were deleted; no `fuel530-*` sessions remain. Full evidence: [research report](/home/ubuntu/wt/fuel-530/research/fuel-530/README.md).