# Marcella tribute value: minimal f475 experiment

2026-10-24. Source design only, ready for Sol's isolated implementation and review. This supersedes the older v1 proposal's cold-field allowance and its requirement for a positive recorded activation before implementation. An activation witness is a useful diagnostic, not a permission gate. No change to banking, captures, support, draft, items or safety is proposed.

Base is the exact frozen f475 tree at `provenance/willow-astraeus-clock-recovery-20261024-v1/workspace/bots/service-base-f7/src`, aggregate `f475b8521cada611754076822402a266c43be8de76ce0f2b504b268ff3335824`. Rules give Marcella2 gold per submitted gem, or2.4 with Treasure; no other champion receives that income from her tribute. `gold_paid` (bot.cpp:1330) includes Treasure/Vesper, but farm's `known.gold` (2216) multiplies only group.gold. The passive is absent from farm value. This is a source omission, not proof that filling it improves any particular loss.

## Scope and actual recipient

Add one delayed marginal-income term to **Marcella's ordinary, empty-bag, independently affordable solo candidate**. Leave current bag chains, crew/help valuation, risky/partner-rescued work, siege and winning captures unchanged. Use existing group claim/holder checks and only `holders(group)==1`; no bonus if a current eligible Prism or visible ally is on the capture tiles, or the candidate is an ally's claim. These restrictions establish whose new gems are being priced. They do not require invisible future teammates to stay away. Later changed claims/holders are handled by normal re-evaluation and execution.

Use positive ordinary gems, not gem-cluster type or map names. A damaging or mixed group may qualify after the existing independent health/clear checks; no new harmless-only or zero-base-gold policy is needed. This keeps actual capture gold separate and prices the passive for a feasible solo recipient. Existing safety, claim priority, capture sharing, shop and banking decisions remain authoritative.

## Units, timing and cheap route availability

Reuse farm's `paid`, `per_gold`, selected group weight and the current `prices(world)` quote. Marcella has no Vesper bonus or Cassi gold-farmer multiplier, so the already-paid farm scalar yields:

`B = known.weight * (2 * q) * per_gold`, with `q = group.gems` for this single holder.

This is gem-equivalent future investment value. Treasure is included once through per_gold; do not multiply it again. If per_gold is nonpositive or the capture itself wins, B=0. It is only the new group's gems; existing carried gems never enter this term. Do not cache B across changes in prices, items, group weight or ownership.

For a candidate that already passes normal solo evaluation, use:

`T = steps + wait + clear_rounds + capture_rounds()`

`D = T + L + tribute_turns(q) + recall_turns(world) + H + S`

Here L is the existing finite group-to-altar estimate populated by the ordinary `too_late` call (bot.cpp:2274–2279); S is the finite existing spawn-to-group walking estimate; H is one if current health is below max or the existing solo quote incurs positive camp damage, otherwise zero. On spawn one turn end heals fully. There is no recall/tribute overlap or pre-tribute shop credit. Return to the same group's work area is an explicit conservative reuse of the existing cycle convention, not a commitment to wait for that group's respawn. It prices travel to future productive work without solving a new itinerary.

No new field is necessary. `known.to_altar` is already evaluated before final solo value; do not force it earlier for the new term. For S, call `map.ally_steps(g)` only when `map.drafted()` or `map.from_ally_spawn_ready()` is true; otherwise the delayed bonus is unavailable/zero. Those paths use the draft scalar or an existing field. Never warm a spawn/altar field solely to get this bonus and never substitute Chebyshev or zero for an unavailable/unreachable route. Re-evaluate availability normally next turn; it is an information condition, not a fuel threshold. The existing drafted/field distances are static walking estimates, including the usual centre/spawn-set approximation; they do not certify future occupancy, camp removal, enemy interference or the random recall arrival tile.

Compute the investment horizon once from current own known race information: `min(bag_rounds_left(world), race_left(world))`. Do not call `closing()` merely to enable this term, because it can warm an altar field for an empty bag. Zero the bonus if the full D cannot fit that horizon. Normal score deadlines still apply separately. Future altar locks or contested travel can invalidate a planned trip; preserve normal observed-lock/banking behavior and label this as an economic estimate, not a safety certificate.

Final candidate value is `old_value + rate(world, B, D)`. Keep the old score/capture-gold rate unchanged. This is a delayed additive utility heuristic in the same units as the existing upkeep-based gold price, not a simulation of future purchases or a claim raw gold equals immediate damage. The term cannot make items affordable, shorten HomeTrip, modify `known.gold_in`, fund a crystal/lock, or add a heal benefit before tribute. No gameplay Memory/claim is changed merely by quoting it.

## Pruning and integration invariants

The three optimistic solo-prune sites around2240,2268 and2347 must include B in their optimistic numerator for potentially eligible candidates. Otherwise a candidate whose new final value can win may still be discarded by old arithmetic. At those early stages use only the cheap current-type/bag/group/claim/share conditions; it is safe to include B for a candidate later refused by ownership/health/route checks. Do not perform those expensive checks merely for a prune.

For empty-bag solo work, D is at least the old candidate cycle. Since B and the eligible old worth are nonnegative, `(old_worth+B)/old_optimistic_cycle` is an upper bound on the sum of the two final rates when that denominator is positive: it omits added travel/shop latency and horizon decay. Final scoring uses the actual delayed D. Preserve old comparisons unchanged when B=0, and leave crew/prorated partner values unchanged. A shared tiny scalar helper can compute the nominal bonus; route availability belongs at final scoring. No allocation, enemy scan, message, global solver, extra Safety computation or new fuel gate is required. Bound current extra work to scalar reads/arithmetic per eligible candidate.

Useful arithmetic checks: Treasure applies once; zero bag excludes existing income; claimed/shared/Prism-held/winning and partner-rescued candidates receive no final bonus; unavailable return/altar paths never become zero delay; longer delay cannot increase the same positive bonus; added value is zero after the known race horizon; all optimistic prunes dominate final value. Current ordinary capture gold may remain in both existing reward/HomeTrip accounting, but this new passive term must never enter HomeTrip's pre-tribute budget.

## First activation diagnostic to request

Use the existing source-known f475 Gem Fields A versus frozen v33 row, `planned-v33-output-v2/f475-v33__00gem-fields__f475-A.repl26a` under the intake. Marcella2 captures7 gems from g14 at14, completes tribute at27, takes a36-gem share of g4 at36 and completes that tribute at44. Request a bounded **Marcella2 round44–45** comparison after that known bag liquidation. It has a real subsequent ordinary cycle: g10 capture at92, tribute112. This is a nomination, not a claim the new term must change that choice or that the existing path is defective.

Record the actual bag/type/price/items, chosen group and one best eligible alternative, claim/holder/independent-health result, existing steps/wait/clear/capture/L/S/tribute/recall/H/horizon, old value, nominal B and delayed value. First inspect ordinary accepted-input differences if a controlled child exists; use exact-prefix private quote tracing only when needed. A no-change result can mean the old choice already realizes the passive, not that the implementation failed. If it changes, follow actual capture recipient, tribute completion, eventual shop and next productive work; compare foregone alternative score and race timing. No broad result panel is required to justify this isolated prototype, and no one-cell result is sufficient for release.
