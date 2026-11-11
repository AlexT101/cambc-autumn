# E4 "mono": the Monolith's 200 gems belong on the Prism (bots/variants/mono)

Read /home/ubuntu/wt/macro-o4/research/macro-delphi/briefs/common.md first and follow it. Candidate dir:
`bots/variants/mono` (create it: `./copybot charybdis variants/mono`). Reference: `bots/variants/charybdis-ref`.

## Why (measured on 512 charybdis mirror games)
- 23% of maps (117/512) have a Monolith (rules: 20000 health, Strength 200, range 5, 300 gold and **200 gems**,
  respawn 150). In 60% of those games nobody ever captures it; the first team to capture it won 37 of 47.
- The game is the Prism duel: a Prism gains 1.5 Focus per carried gem; 78% of Prism deaths are kills by the enemy
  Prism, and the dead Prism had under 0.8x the killer's Focus in 87%. 200 gems on our Prism is +300 Focus, more than
  the typical Focus gap between the two Prisms at round 400 (winner ~750 vs loser ~590).
- charybdis prices a carried gem for its Prism (`carried_bonus`, economy/capture.cc; farm.cc `keep_bonus`/
  `keep_most`) but **excludes the Monolith everywhere** (farm.cc line ~986 `!G.has_monolith`, the 'G'/'L'/'Q' carry picks
  ~222/2337, `leave_for_prism` in capture.cc returns false on `G.has_monolith`). Earlier Monolith programmes lost
  against ocean because they pulled champions off cheaper camps; none had this price, and macro6 left "carry price
  on the Monolith" as an open lead (research/macro-2026-11-11/macro6/macro6.md, Lessons 6 and L-1).

## Design (read economy/crew.cc's Monolith operation `farm_monolith`/`mono_engage`/`mono_trapped`, farm.cc's crew branch
and the 'late'/`too_late` logic around line 2150-2230, capture.cc holder logic `holder_value`/`sole_capture_holder`
first)
1. **Price.** For a keeping Prism, the Monolith's gems in its crew/claimed values get `carried_bonus(world, me, gems,
   price)` exactly as other gem groups do via `keep_bonus` (respect `keeps_bag`, i.e. short of the win: if the 200
   gems would win, no bonus; the win itself is worth more anyway). For non-Prism crew members, the Monolith's crew
   value adds the Prism's carried bonus on the whole reward when our keeping Prism is alive and a member of (or
   claims) the operation, since the capture will be put on it (point 2). Keep the prune bounds consistent (any bound
   that assumes the Monolith has no bonus must now include it).
2. **Holder.** At a cleared Monolith group, the capture goes on our keeping Prism: allies hold it until the Prism is
   on a tile, then step off before the payout (the same mechanics as `leave_for_prism` / 'G' takeover / `prism_hold_tiles`
   for other groups: extend those to the Monolith rather than writing a parallel mechanism). If the Prism is not in
   reach before the payout (or dead), allies capture as today.
3. Do not otherwise change when the Monolith operation launches (gather share, waits), the draft or emblems.
4. Debug traces: Monolith operations started, cleared, captured, and by whom (Prism share).

## Done when
Builds; three local games on Monolith maps finish without bot errors (find maps in maps/macro-dev with a Monolith:
`grep -l` is not possible on binary maps; use the ladder maps whose names contain "monolith", e.g. `ls maps | grep -i
mono`, and generated `gen-monolith-*` maps in maps/macro-dev); traces show the price and hold firing. Report as
common.md asks.
