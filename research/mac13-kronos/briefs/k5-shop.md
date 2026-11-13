# Brief k5: shopping-trip probes (four small variants)

You are building probe variants of the Cambridge Battlecode C++ bot `charybdis` for the orchestrator of its macro
refactor. Read `/home/ubuntu/wt/mac13-kronos/AGENTS.md` and `cambc-rules.yaml` (economy, shop, recall). Work ONLY in
`/home/ubuntu/wt/mac13-kronos`; do not touch `/home/ubuntu/cambc-autumn` or other worktrees; do not commit. Never edit
`bots/variants/chy-ref` or `bots/charybdis`. Off limits: `src/draft/` and WHICH emblem/shard a champion buys
(`best_emblem` and its choices). WHEN champions go home to shop is in scope. Each variant:
`./copybot variants/chy-ref variants/NAME` (never copy `.cambc/`), then the edit.

## Evidence
In 1,024 mirror games our Prism holds a lot of unspent gold: on average 50-57 gold over rounds 1-300, 145 (losing
side) / 221 (winning side) over rounds 300-600, 195 / 442 over 600-1000, i.e. 5-7 shards (each +65 health for a
Prism whose base health is 700) unconverted through the mid game, with ~7 shop visits a game. Vesper Vale holds
65-92 over 300-600. Shopping happens only on our spawn (or dead). The decision is `wants_shop`
(`economy/shop.cc:777`): a trip goes when `params::shop_gain_scale` (0.75) x `affordable_prefix(world).gain` (the
farming rounds the stats save, via upkeep cost) + heal beats the recall and walk back. The Prism's capture-time recall
(`economy/capture.cc` ~line 958-969) uses the same gain unscaled. Non-Prism champions do not shop at all below
`emblem_price` gold unless an emblem is begun (`shop.cc:781`). The gain is a farming measure; it ignores what stats
are worth in fights (the Prism war decides ~90% of games). These probes measure the gradient of "shop sooner".

## Variants
1. `k5-ps2`: for the Prism only (`passive == Passive::gem_focus`), multiply the shop value's gain by 2 in
   `wants_shop`'s Prism branch and in the Prism capture-recall test in capture.cc (~967). Implement as a named
   constant (e.g. `prism_shop_weight = 2.0f`) used in both places.
2. `k5-ps4`: the same with 4.0.
3. `k5-os`: non-Prism champions: drop the `gold < emblem_price && !begun_emblem(...)` gate in `wants_shop` (they may
   shop from one shard when the value test passes). Check whether `home_trip`'s `short_gold` (it is
   `p.next.cost - gold`, an emblem's cost) then still blocks the trip at `shop.cc:794`; if it does, make the non-Prism
   trip test use the affordable prefix's value (what the gold buys now) instead of requiring the whole next emblem.
   Say exactly what you changed.
4. `k5-all2`: every champion's shopping value x2: wants_shop (both branches), the Prism capture recall,
   `home_trip`'s `t.emblem` and `farm_recall`'s gain term (one named constant `shop_weight = 2.0f`).

## Stop condition
1. All four build (release). 2. Spawn ONE read-only auditor subagent (tell it explicitly not to edit anything) to check
the four diffs against this brief (the multiplier applied where stated and nowhere else, no change to which items are
bought, release builds unaffected); fix what it finds. 3. Smoke each in parallel:
`source ~/venv/bin/activate && cd /home/ubuntu/wt/mac13-kronos && CAMBC_BIN=/home/ubuntu/cambc-autumn/tools/fastengine/runner/fastrunner FASTRUNNER_MODE=native PATH=$HOME/.cargo/bin:$PATH python tools/ab.py variants/NAME variants/chy-ref --no-test-draft --fuel 200000 --name mac13-kronos-NAME-smoke`
(256 ladder games each): no failed games, no DRAFT-UNFINISHED / PLAN-CHECK. Delete the smoke batches afterwards.
4. Save diffs to `/home/ubuntu/wt/mac13-kronos/research/mac13-kronos/patches/NAME.diff`
(`diff -ru bots/variants/chy-ref/src bots/variants/NAME/src`). Finish 1, 2 and 4 first and write each diff as soon as
it builds (the orchestrator starts screening from the diff's appearance), then smoke. Return what changed per variant,
auditor findings and fixes, smoke results. No large A/Bs.
