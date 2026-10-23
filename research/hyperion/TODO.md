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
exhausted; gate removals so far were level at 100M but 4-5x the out-of-fuel turns.

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

Verified in code 2026-10-22; 2-5 and 12-20 found by the 2026-10-23 audit. Logic fixes: A/B each, keep if level.

1. **Mid-turn state after our own actions.** Safety and World assume beliefs fixed for the turn; our actions break it:
   - a killed enemy becomes an unseen threat after `observe()` (only a full update reads liveness; `see_again` runs
     after the strike plan): in observe(), check `engine::alive` for enemies seen this round and now out of sight;
   - camps we wake are not in Safety (`stirring_` is set only by `update_camps`): note the wake when our hit or
     cast touches an asleep group;
   - kills leave walls: `live_camps()` keeps killed members until a full update, and `blocked_` survives attacks;
   - fighters keep turn-start health, shields and cooldowns (`made_` survives `refresh`/`invalidate`);
   - an enemy revealed by a refused step onto its tile: `revealed()` skips our own tile (CHANGES 89).
2. A carrier on a cleared group's tile holds instead of banking: `holding_capture` exits only on `winning_bag`, and
   `decide` takes `holding` before `carry_bag`, the only place `closing()` is weighed. It sits up to 6 rounds even
   when the bag must go now, or when the payout (`held_since` + 6) falls after round 2000 and never pays. Exit when
   `closing()`, past the round limit, or (maybe) while `memory.banking`.
3. An unseen enemy's recall or tribute is taken as completed at `channel_end_round` (world.cpp `update_champion`):
   `possible` only ORs the spawn, as its comment says, but `pos`, `pos_round` and health are replaced (a tribute's
   gems zeroed) though recalls are mostly started and cancelled (stuns and locks cancel tributes). `note_sighting`
   then drops a teammate's sighting from that round, and `age() <= 1` users (pack zone, `paying_soon`,
   `recall_outruns`) read the spawn as a fresh fix. Keep the seen position and health; zero gems only if
   `update_scores` saw the enemy score rise.
4. Unseen threats price range by walking distance: `build_threats` fields `possible` around walls, `Threat::at` feeds
   that into a Strike indexed by Chebyshev distance. A ground cast hits through walls, so an unseen Prism, Stellar or
   Ryth across a wall line is missing from `lethal`, `threatened`, `fight_key` and `enemy_area` (`each_threat` stays a
   bound). `threats_at` also bisects by Chebyshev before the build and reads the field after, so its answer depends on
   whether something built Safety first.
5. A melee carrier's own fifth hit on a lock skips the tribute check: `altar_here` skips locked altars, so no caller
   ran `tribute_ok`; `bank_gems`'s `break_lock` does not return for melee, `step_safely` does not move, and
   `submit_here` skips `tribute_ok` on the turn's start tile (round-limit check included). Same in the pack-zone
   branch. Judge a just-unlocked altar in `submit_here`.
6. Dashers' altar distances: `centre_to_altar` takes `drafted_altar_steps` (walking) unconditionally; guard it as
   `draft_spawn_graph` guards spawn steps (bot.cpp).
7. Enemy stun status in Safety's threats and fights (the planner reads it only for `stunnable`). Conservative: costs
   tributes and fights, not deaths.
8. `capture_taken` counts allies bound elsewhere (tributing, recalling, claimed another group).
9. The strike search never opens tiles of units it kills (`free_`/`pass_` fixed in `read_geometry`): a kill can open
   a walk or dash path (a blocker in a corridor; Vendetta's refreshed dash through a cleared camp).
10. A fully shield-absorbed spell ignores Durability in the planner: `min(raw, shield)` should be
    `min(raw * taken, shield)` (plan.cpp `x.spell`, `x.land`).
11. Varg's fallback attacks (`camp_attack_targets`, champion splash) wake neighbouring sleeping groups, unpriced
    (test drafts only).
12. Our winning bag blocks interception: `game_ender` returns null and `continue_tribute` never cancels while
    `winning_bag`, with no comparison of the two channels' ends. Outside a channel `stun_worth` still prices the stun;
    the loss is mid-tribute and the `stop_game_ender` pursuit. Rare (both teams near 1000) but game-deciding.
13. Heart of Ruin's landing ignores Ren's retaliation: `land_at` sums it over visible foes only (the landing hits
    unseen ones), and `dash_away`, `dash_to_attack`, `travel_dash`, `dash_across` and `dash_clears` never check it, unlike
    `enemy_cast`'s `suicidal` and `camp_cast`'s `skip_rens`. A low-health HoR can die to its own escape dash.
14. `fighting_allies` counts allies that cannot act (stunned, mid-teleport) as fighting at once (`arrives_at` 0).
15. A visible unacted enemy is fixed at `now()` with its turn order from ranks, not its `acted` flag; when stale unseen
    priorities rank it before us, `turns_between` never counts its remaining turn and `possible` misses a step (can
    empty, untracking it). Fix at `{round, -1}` when `!acted`; `hold_start` and the respawn `before_us` share it.
16. `awake_over` returns true on `G.threat()` (every member's reach, dead ones included) once `asleep == 0`: falls
    through to the per-member check instead (`finishing_camp`, `wants_shop`).
17. Reach's dash `pass` mask drops every believed-live camp; a camp on a bush tile next to the dasher is unseen to it,
    and the rules let a dash cross unseen camps.
18. `hold_start` can date a hold a round early when the group was not watched last round (a contest that ended this
    round before our turn). The comment's own rule wants the later round.
19. Turn-order bids (test drafts only: they run for `role() < 0` champions): `offer_kills` needs `ours.at(d) > 0` to
    cancel a recall, though a stun alone does; `offer_escape` ignores our shield (`lethal()` adds it);
    `can_act_before` trusts unacted enemies' `next_priority` when it can still change.
20. `play_turn` calls `set_turn_order` outside `act`'s try: a throw there skips the claim and bag posts and the memory
    update, so next turn reads `memory.damage` as 0.

## Candidates

Each needs an A/B (see [../EXPERIMENTS.md](../EXPERIMENTS.md) first). Bundle removals and keep them if level.

- Removals: `keep_walk`'s free-stun logic in `enemy_cast` (still used by retreat and the game-ender intercept),
  replaced by a plain threshold; ground casts at unseen enemies (`max_unseen_tiles`).
- Behaviour: one `run_home()` for `retreat()` and `carry_bag`'s retreat; give kite's stations line of sight, as
  `spell_clear` has (verified 2026-10-23: a unit-spell caster, Marcella in our draft, can stand at a station that
  cannot see the monster and return success each turn); drop kite's contested branch; the strike search's attack
  legality ignores our ward's sight from tiles we move to (`viewers()`), which Reach models for enemy wards; pack-zone ratio `(home || hurt) ? 2.0 : none`;
  walk to lock an altar where a visible
  enemy tributes a big bag (`Altar::lock_tiles()` as goals); spell-clear pricing (`spell_clear_rounds`) tested both
  ways; probabilistic `threatened()` removed (risky: it gates recalls). Ren's specials change only on ladder evidence.
- Two-band turn order with double turns (from HerbertTheBird's deleted herbert bot, `git show e32257b:bots/herbert/src/bands.cpp`):
  priorities in a secret LAST band [1, M) and FIRST band [M, 2M); moving LAST -> FIRST buys two actions in a row.
  Never tried here.
- The enemy's two-turn chain (both slots across two turns, slots readied for turn 2): lost as w2-chain (47.1%,
  ladder 52.9, out-of-fuel turns +20%). Retry only once fuel work frees room, or narrowed to slots readied for turn 2.
- Known bugs, unverified: retreat_step walks back into an Elk's reach when the way home passes it (`recall_outruns`
  ignores camps); idle turns under a Golem (dense-camps).
