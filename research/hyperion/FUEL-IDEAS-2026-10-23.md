# Hyperion fuel ideas, 2026-10-23

Inspection of a5749c4, with p99 fuel and out-of-fuel turns as the objective. Hyperion was not edited.
The prototypes below are isolated under `bots/variants/`, copied without `.cambc/`. None adds a fuel
gate, changes a search limit, or substitutes an approximate result when fuel is low.

The existing experiment log is unusually useful here: full fight-input memoization, generic fight
bounds, per-side cast plans, bigger Reach memos, farm ordering/buckets, and broad sight warming have
already disappointed. The remaining opportunities are more specific than those approaches.

**Measurements from this investigation**

Six maps, both sides against hecate, compiled test drafts, 100M fuel, normal local `-O3 -DNDEBUG`
builds: ambush, contest, lanes, gen-chambers-102206117, gen-hourglass-102205812 and
gen-dense-camps-102108100. This covers long fights, dense camps and ordinary ladder play, but is
not the full wide suite and does not cover every topology or draft. There were 77,949 play turns
after round 1. All three candidates produced byte-identical replay payloads in all 12 games.

| Isolated candidate | Mean fuel | p99 fuel | Turns over 100k |
|---|---:|---:|---:|
| Unchanged baseline | 41,977 | 114,160 | 1,555 |
| Stop generating children after the existing 24-node cap | 41,982 | 114,245 | 1,561 |
| Direct chunk intersections for `any_within`, radius <= 8 | 42,180 | 114,209 | 1,563 |
| Direct Chebyshev distance for singleton unseen threats | 41,981 | 114,160 | 1,555 |

These implementations are not gains. No real-budget OOF improvement is claimed; the last column
measures unlimited-budget turns exceeding 100k, not actual OOF events. Real-budget testing was not
expanded for candidates that failed the initial fuel screen. Local debug builds are not release
fuel-exact, as documented in EXPERIMENTS; a promising result would still need release verification.

The cap candidate saved as much as 23,777 on one turn, but made 9,272 turns dearer and only 63
cheaper. The average change on the baseline's worst 1% of turns was -11 fuel. Thus there is real
waste after saturation, but checking at every branch is the wrong implementation. The local
rectangle candidate added ~0.48% total fuel: replacing inexpensive host operations with nested
WASM loops did not pay. The singleton case was too narrow to affect p99.

Artifacts: `replays/fuel/ideas-cap-base-opt.json`, `ideas-cap-stop-opt.json`,
`ideas-local-any-opt.json`, `ideas-singleton-opt.json`. The corresponding bot copies are
`fuel-ideas-base`, `fuel-ideas-cap-stop`, `fuel-ideas-local-any`, `fuel-ideas-singleton`.
An earlier `ideas-cap-base.json` is invalid for comparisons: a sandbox-denied compiler probe left
that separate CMake cache without optimization flags. The `-opt` runs use fresh, checked caches.

**Ideas worth investigating next, in priority order**

1. **Retain results whose inputs survive a kill.** `Safety::invalidate()` at safety.cpp:1767
   drops every Reach build, threat build, camp model and fight memo after any detected death.
   This can concentrate repeated work on already expensive attack/kill turns. Start narrowly:
   keep an unseen enemy's field and area while its `possible` set and radius are unchanged,
   even when a different visible enemy or camp dies. Then retain Reach results for enemies whose
   local blockers, splash targets and ward/visibility inputs did not change.

   Use explicit dependency generations or exact input comparisons, not a coarse round stamp or
   a hash without equality checking. A camp death matters inside some windows but not others;
   a champion death can remove a Varg splash target; linked bodies must be handled together.
   Fight memos can only survive when their complete effective inputs survive. Preserve current
   belief semantics rather than accidentally mixing in the separate mid-turn correctness fixes
   listed in TODO. Measure rebuilds after `refresh`, their cost on baseline tail turns, and how
   many survive the dependency check before attempting the larger refactor.

2. **Cache Reach geometry separately from its damage recipe.** `Reach::at()` at safety.cpp:1526
   tests movement-set intersection, range, sight, ward sight and splash eligibility, then combines
   damage/stun values. `build_ways()` includes Strength and Focus in its recipe, and each build
   invalidates final Blow results. A Heart of Ruin's damage changes with health even while its
   relevant geometry stays identical.

   Store an eligibility bitmask for distinct `(from, range, sight)` geometries, then apply the
   current damage recipe to that mask. The first-turn/second-turn distinction affects damage
   combination but can share geometry when its actual movement mask is equal. Begin with reuse
   within a query/build; cross-turn reuse needs exact movement masks, target/origin, ward visibility
   and Varg targets as dependencies. Keep scalar damage operations in their current order.
   This is different from increasing the existing tile memo, which had no collision problem,
   or retaining a whole fight result whose health inputs almost never repeat.

3. **Vectorize independent candidate scores, not a fight's floating-point sum.** In plan.cpp:1736
   and 1818, the price loop adds one foe's damage to up to 16 candidate accumulators and repeatedly
   finds the best. Those candidates are independent. The local build already enables `-msimd128`
   and the SDK includes `wasm_simd128.h`.

   A structure-of-arrays representation can update four `float` damages and removal masks at once.
   Keep the foe order unchanged within each lane, use ordinary strict f32 operations, and select
   the lowest original index on ties. Do not replace a serial sum with a horizontal reduction,
   reassociate arithmetic, use relaxed SIMD, or assume NaN/signed-zero behavior is irrelevant.
   Small candidate counts may remain scalar, selected solely by count; both implementations must
   produce identical answers. Measure gather/scatter overhead and the actual generated WASM fuel:
   four lanes do not by themselves establish a fourfold saving. This targets the expensive price
   phase without changing its node/query caps or candidate order.

4. **Give boolean questions a boolean Reach path.** `Safety::approach()` at safety.cpp:1957 and
   `fight_key()` at 2130 ask whether a blow hits, but obtain a full `Blow`. A cache miss can stop
   at the first legal way when only `hits` is requested; damage queries continue to compute the
   maxima, second-turn combination and stun flag as today.

   Track `hit known` separately from `full blow known`: a partial result must never masquerade as
   a complete memo entry. Preserve the teleport shortcut in `Safety::blow`, ward visibility and
   Varg splash. The risk is duplicate work when a damage query immediately follows, since the
   current eager result prewarms it. First count boolean-only queries that never need damage
   before invalidation. This is an output-specific exact short path, not the previously rejected
   attempt to equate Strike with Reach.

5. **Copy mutable state rather than whole records.** `fill()` at safety.cpp:695 copies each full
   Fighter into every simulation. Strength, max health, retaliation, mitigation, kit pointer and
   immunity/link identity need not be repeatedly copied with health, shield and timers. Split
   immutable fighter data from mutable simulation state, referencing the former directly.

   Separately, `Search::grow()` at plan.cpp:1515 saves/restores all 14 health slots even when an
   action changes one unit and possibly its linked partner. A specialized unit-action undo can
   save the old float bits for those slots; ground/splash actions can retain the full snapshot.
   Moves and resets do not themselves mutate health, though recursive children still must restore
   theirs. This saves copying rather than caching another large copied Side. Extra indirections,
   undo bookkeeping and compiler scalarization can cancel the gain; inspect the generated code
   and measure setup cost, not just `sizeof` reductions.

6. **Prepare useful immutable data during genuinely cheap turns, including dead turns.** Existing
   `warm_reach()` at safety.cpp:1306 only visits visible enemies' neighboring tiles and returns
   immediately when we are dead. Available work includes Search's terrain grids, viewer rows,
   static camp membership lists and Reach windows along likely routes or around recurring fights.
   A dead instance retains its own memory, so it can prepare data for its own respawn.

   Rank tasks by observed miss cost and likely reuse, not random enumeration. The previous sight
   warming experiment used only about 1 in 20 warmed masks, so broad warming needs a substantially
   better task choice. Run bounded tasks in the end-of-turn cache queue; publish only complete
   entries. Every miss must synchronously calculate the identical answer. Test queue enabled
   versus disabled with byte-identical unlimited-budget replays and report both total fuel and
   decision-phase p99. Do not expand the existing `centres_ready()` behavior dependence: that
   readiness flag currently changes farm weighting and is not a suitable model for new caches.

7. **Propagate search saturation through the recursive return value.** The measured cap-stop
   prototype proves that post-cap work can be large on individual turns, but broad polling loses.
   A different implementation could return a saturation flag from `grow` through `push`, restore
   the caller's health snapshot, and unwind immediately. Fold the check into the existing return
   path instead of checking every target and branch. Keep exactly the same first 24 nodes, leaf
   order and tie behavior. In particular, do not use the saved fuel to grow extra nodes.

   This remains an untested refinement, not a successful result. Avoid exceptions for unwinding:
   their cost is already known to be substantial. Cache writes skipped after saturation must be
   either unused or reproducible on demand by later phases.

8. **Use exact shape information before building unseen-threat fields.** After CHANGES 108 these
   fields have no walls: they are capped Chebyshev distance from `possible`. A small list gives
   `min(dist(p,q))`; a set proven to fill its bounding rectangle gives distance to that rectangle.
   An arbitrary set still uses the current engine field. Query count and set shape, never remaining
   fuel, can select between equivalent representations.

   The singleton prototype was level at p99, so singleton handling alone is not a priority. A
   useful extension must avoid *building* fields that receive few queries, not just replace their
   inexpensive reads. Keep `Threat::area`, the radius cutoff, roster/order and credibility exactly
   consistent, and invalidate on every possible-set change. Full area consumers can materialize
   it lazily. Broad sets on large maps might justify this; confirm their contribution to tail turns.

9. **Longer-term: cache certified regions of fight outcomes, rather than exact inputs.** Exact
   cross-turn fight keys fail because health changes constantly. An ambitious alternative is a
   certificate saying that a particular result holds throughout a precisely bounded region of
   health/shield inputs, with roster, kit, arrival times and cooldowns fixed. Cheap comparisons
   could then reuse an outcome across several combat turns.

   The certificate must prove the existing simulator's result, accounting for weakest-target
   switches, shields, stuns, deaths, healing and floating-point rounding. The simulator is not
   monotone in roster changes, as earlier experiments demonstrated. A rounded health bucket or
   a merely similar previous fight is not sufficient. One possible construction is conservative
   interval replay of a recorded event trace, rejecting the certificate whenever an event or
   outcome becomes uncertain. Use spare-turn work to build certificates; a miss runs the exact
   simulation. This is substantially more engineering and may never amortize, but it addresses
   why ordinary memoization missed rather than repeating that experiment.

For the next implementation pass I would instrument invalidation reuse and Reach boolean-only
queries first, then prototype SIMD candidate pricing. These need evidence of frequent expensive
cases before larger changes. Keep the six-map screen for iteration, compare matched baseline
tail turns as well as aggregate p99, and only take a successful candidate to a limited real-budget
check. None of the measurements here supports merging a prototype into Hyperion.
