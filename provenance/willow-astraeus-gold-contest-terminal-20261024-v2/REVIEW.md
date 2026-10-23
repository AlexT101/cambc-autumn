# Arm B v2: reviewed corrections on cb61eaa

Candidate: `bots/variants/willow-astraeus-gold-contest-terminal-v2-work/src`.
Parent: `bots/baselines/astraeus-cb61eaa/src`, exact Git commit `cb61eaa5276b527c0de85db9b3bcfa0fdadd4a50`, source tree `378a2ea31787e642630d179146ef33e43ca1bb9a`.
Parent aggregate: `369742e3f54259c675c0d4b508a02c0c4517eef6e1cb3ef6f42fa776194180ea`.
Candidate aggregate: `692b6ffe52ea70f9aef3e82609b7133548be295d0eff4cd238a7a5a43ea38fe2`.

The v1 source patch was checked at SHA-256 `929ef51293795d5d503947065fcedd42868f2ce4101146a2e16d06642e653f0c` and applied to a fresh copy of cb61eaa. `ported-v1-src` preserves that intermediate source; its aggregate is `df5dc04a9ce8d0190cd655d40f20fa2d87e37000aa63638202d8f9b984a2e56f`. The only changes from this intermediate are the two requested source corrections in plan.cpp, recorded in `review-corrections.patch`. The complete patch against cb61eaa is `source.patch`. All 29 source files are saved in `before-src`, `ported-v1-src` and `after-src`; manifests use normalized `src/` filenames and the parent recipe `(cd <botdir> && shasum -a 256 src/* | shasum -a 256)`.

## Review corrections

`Search::read_economics` walks each candidate group's existing `members` positions and tests those positions against existing `world.visible`. It never calls `G.tiles()`. Occupancy membership uses the existing prebuilt `StaticMap::group_at` lookup for visible bodies and our native current position. This avoids the prior complement and intersection allocations and the lazy group-tile bitboard allocation. The new qualification code uses fixed 49-entry stack arrays, existing vectors and direct lookup storage; it introduces no dynamic allocation in that code. It does issue one existing visibility-test host call per member examined. This is a source-level statement, not a measured whole-search allocation or fuel claim.

Qualification considers at most 49 distinct groups from the existing 49-cell local grid, caches each result, and short-circuits on the first unseen member. A group may extend outside the grid; all its member positions must be visible. The member scan is bounded by the existing group size; distinct groups have disjoint camp tiles, so the total positions examined is at most the map's camp-tile count. Occupancy scans existing ally/enemy vectors once per otherwise eligible group. No new fuel gate, full-board temporary, group mask, observation refresh or route-field creation is introduced by qualification. Existing search work elsewhere can allocate, and the new terminals can add meaningful fuel or alter exact-query coverage.

The signed field-progress formula remains `(here_steps - endpoint_steps) * step`. It is suppressed only when an endpoint is economic, its group equals `intent.group`, and the field objective is not an altar. Thus duplicate progress toward the same capture objective is removed; a distinct existing farm objective retains its positive or negative route term for every leaf, ordinary strike leaves included. Removing the hypothetical unused later-walk credit at economic leaves remains unchanged.

## Source-only controls

These are algebraic controls of the actual predicate/formula, not executed engine fixtures. Suppose the selected field is reachable, there are at least two candidate tiles and `S.walks` is true. Use an illustrative `step = 10` and current field distance 5:

| Economic endpoint and objective | Endpoint distance | v1 field term | v2 field term |
| --- | ---: | ---: | ---: |
| Different farm group, toward goal | 3 | 0 | +20 |
| Different farm group, away from goal | 7 | 0 | -20 |
| Different farm group, equal distance | 5 | 0 | 0 |
| Same farm group as occupancy | 0 | 0 | 0 (duplicate suppressed) |
| Altar objective, even if stale `intent.group` matches | 3 / 7 | 0 | +20 / -20 |
| Ordinary non-economic endpoint | 3 / 7 | +20 / -20 | +20 / -20 |

Missing field, unreachable field values, fewer than two tiles or disabled goal walking retain the baseline's absent field term. The economic quote is a separate one-turn term and is added once; these examples do not assume a particular quote or winning action. They establish source-level sign preservation, not runtime selection or competitive value.

## Preserved scope and outstanding evidence

Only bot.cpp, plan.cpp and plan.h differ from cb61eaa. The upstream support/fuel, heal visibility/readiness and state cleanups remain in the source. The cb61eaa baseline and control remain byte-identical. The older baseline, v1 candidate and v1 provenance remain intact. No canonical or sibling bot source was edited.

The v1 read-only matching Prices quote, soft current-tile occupancy, fully visible/current cleared gold-only non-Monolith qualification, consistent occupants/holder checks, exclusion of other allied occupants, enemy expiry check, base-gold denial versus own bonus-adjusted prospective capture, four no-strike walk/plain-dash templates, native executor and completed-position success condition are retained. Existing combat, reset/kill/heal/shield competition, retreat, bank/hold/support precedence, Safety code, 24 ordinary growth nodes, 512 leaves, 49 endpoints, 10 exact queries, and global Willow/contesting flags are unchanged. A qualifying economic objective can still lose to safety, combat or unrelated route cost.

No compilation, engine, replay execution or competitive test was performed. The debug GOLDTERM row remains a pre-execution record and does not distinguish all admission, outpricing, safety, refusal and success outcomes. First-contact/mismatched-price abstention, native walk/dash ordering/refusal, sure-kill and reset competition, partial visibility/allied-holder exclusion, six-round capture continuity, economy conversion, fuel and exact-query coverage still need source-known normal-fuel evidence after source review. No earlier runtime claims transfer to cb61eaa or v2. The one-turn quote can remain too modest to beat an optional 55-damage attack; no weight was tuned.
