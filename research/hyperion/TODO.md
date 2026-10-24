# hyperion: open work

## Direction

- A robust, intuitive, logical bot: behaviour derived from the rules (reach, sight, cooldowns, health, walking
  distance, measured rates) over tuned constants, fixed decision orders or special cases.
- Logical changes stay even when level or slightly below 50%; drop only what is clearly worse (below ~47% over ~1100
  games) or wrong.
- No new fuel gates. Make work cheap or bounded instead; the plan is [FUEL-GATES.md](FUEL-GATES.md).
- Keep the teleport, Tavi and Willow code.

## Next, ranked

Out-of-fuel turns are still ~1.5x hecate's in A/Bs ([FUEL-PROFILE.md](FUEL-PROFILE.md)). Exact fuel cuts are mostly
exhausted; gate removals so far were level at 100M but 4-5x the out-of-fuel turns. CHANGES 107-108 added ~2% and
~6% in their A/Bs (the same REF reads 4530-4917 across runs). Not 108's Reach bush-camp passes (+9% alone): no
ladder or gen map has a camp on a bush, so it never fires and that +9% was noise.

1. The farm loop on many-group maps (132 groups: 44k a call, ~300 per pruned group): spatial buckets or an order kept
   across turns so pruned groups are never touched; then remove pick_up's farm-loop gate (farm-partial-evaluation).
2. Cheaper fight sims: non-plain act() for shield kits (44% of sim fuel), and fights that run to the horizon (16% of
   sims, 37% of sim fuel). Needed before the step-guard and prey-cut-short gates can go.
3. One danger model (STRIKE-SEARCH phase 5, overlaps in FUEL-PROFILE): one danger pass per tile per turn across
   want_home, step_guard and the search's end tiles; byte-identical first steps (turn memo for `lethal`, step_guard's
   keys kept across its two calls, a wider Reach memo) first.
4. The remaining gates, one at a time with an A/B: step-guard, prey-cut-short, ward, comms-stale-vision, turn-order.
5. Strike phase 4a's retreat-search fuel (40.8% real, 52.6% at 100M; `orch/strike-p4a-wt` bdb5902 holds an untested
   partial fix), then 4b (`orch/strike-p4b` 6997211, untested).
6. Stellar/Ren compositions and enclosed maps (fortress, lanes, caves, maze, sparse camps): against hecate, first deaths
   came from worse fights (outnumbered, struck first), lone champions picked off in tunnels.
7. Monolith and big-group captures: more Monolith damage than hecate but fewer captures (40 vs 58); big groups woken
   and left to sleep again (archipelago, 00contest).
8. `tools/ab.py` fuel per side, to measure what fuel costs one bot.

## Bugs, ranked

Verified in code 2026-10-22; 8 from the 2026-10-23 audit (its fixes are CHANGES 107-108). Logic fixes: A/B each,
keep if level.

1. **Mid-turn state after our own actions.** Safety and World assume beliefs fixed for the turn; our actions break it:
   - camps we wake are not in Safety (`stirring_` is set only by `update_camps`): note the wake when our hit or
     cast touches an asleep group;
   - kills leave walls: `live_camps()` keeps killed members until a full update, and `blocked_` survives attacks;
   - fighters keep turn-start health, shields and cooldowns (`made_` survives `refresh`/`invalidate`);
   - an enemy revealed by a refused step onto its tile: `revealed()` skips our own tile (CHANGES 89); only Willow's
     steps call `see_again` on a refused move.
   - an enemy we stun is not read as stunned (CHANGES 127 reads stuns at turn start only).
2. The strike search never opens tiles of units it kills (`free_`/`pass_` fixed in `read_geometry`): a kill can open
   a walk or dash path (a blocker in a corridor; Vendetta's refreshed dash through a cleared camp).
3. Varg's fallback attacks (`camp_attack_targets`, champion splash) wake neighbouring sleeping groups, unpriced
   (test drafts only).

## Candidates

Each needs an A/B (see [../EXPERIMENTS.md](../EXPERIMENTS.md) first). Bundle removals and keep them if level.

- Removals: `keep_walk`'s free-stun logic in `enemy_cast` (still used by retreat and the game-ender intercept),
  replaced by a plain threshold; ground casts at unseen enemies (`max_unseen_tiles`).
- Behaviour: one `run_home()` for `retreat()` and `carry_bag`'s retreat; drop kite's contested branch; pack-zone
  ratio `(home || hurt) ? 2.0 : none`; walk to lock an altar where a visible enemy tributes a big bag (`Altar::lock_tiles()` as goals); spell-clear pricing (`spell_clear_rounds`) tested both
  ways; probabilistic `threatened()` removed (risky: it gates recalls). Ren's specials change only on ladder evidence.
- The enemy's two-turn chain (both slots across two turns, slots readied for turn 2): lost as w2-chain (47.1%,
  ladder 52.9, out-of-fuel turns +20%). Retry only once fuel work frees room, or narrowed to slots readied for turn 2.
- Known bugs, unverified: retreat_step walks back into an Elk's reach when the way home passes it (`recall_outruns`
  ignores camps); idle turns under a Golem (dense-camps).
