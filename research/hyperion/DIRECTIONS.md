# Open directions (from the 2026-10-28 audit)

Open suggestions from the 30 per-file audit reports ([audit-2026-10-28](audit-2026-10-28/README.md)), grouped by
theme. Each tag names the report and its item number, e.g. (safety 3), as EXPERIMENTS and commits cite them; several
tags mean several reports raised it. Brackets give [severity, effort]. `Tried` / `Partly` give past results. Closed
items are removed (last pruned 2026-11-02, through CHANGES 274; earlier text is in git history).

Largest: safety 1, camp fire by the nearest-champion rule, camps we wake this turn, Varg's splash, Heart of Ruin,
the fuel gates.

## Threats and fights

- **(safety 1) Two-turn threats miss dash-first plans** [high, moderate]. `threat_strike`'s widening and
  `Reach::build_ways` let turn 1 only walk, so a dash then a strike from the landing is missed: Vendetta at 3-4 and
  Vesper at 5 deal 3x Strength where the model gives 1-2x. Fix: in the dash band, max over turn-1 moves of turn-1
  damage plus `s2` without the dash slot. Changes threat levels everywhere. Partly: the full two-turn chain lost
  (47.1%); one cast across both turns shipped (CHANGES 95). Dash-first untried.
- **(safety 3) Champions yet to act shield us from camps** [med, small]. `find_members` cuts a member's reach by any
  nearer visible champion, though an unacted one can step away. A melee ally beside a monster is usually tanking on
  purpose (one champion takes 98% of shared clears' hits), so: enemies get the move bound (1, or 3 with a dash);
  allies stay when their claim is the group or they hold its capture, else get the move bound (simpler: allies
  always stay, as today). Count first how often an ally's cut changes a reach; if almost never, ship the claim
  version. Tried: the move bound for everyone (CHANGES 209 bundle, level), reverted over the allies.
- **(guard 3) The pack radius is the same for every enemy** [med, small]: 5 since CHANGES 239. Per member,
  `threat_strike(world, e).reach + 1` shrinks zones against walking melee and keeps them for dashers.
- **(guard 7, bank 2) Shields don't count as health** [low, small]: the `hurt_health_fraction` checks (fight,
  guard's pack zone, capture) and `tribute_safe` use raw health, so a shielded Varg or HoR retreats, skips chases or
  skips tribute windows. Add the live shield, as `finishing_camp` and `Safety::lethal` do. Related: the pack zone's
  `pz.health` is frozen at the first query but adds the live shield, so a shield cast this turn counts toward
  `ours` but not `hurt` (probably intended).
- **(guard 4) `no_worse` compares enemy exposure only** [low, small]: a step out of an ally's `fight_ally_radius`
  reads as safe. Require `fighting_allies(q) ⊇ fighting_allies(here)`, or skip the shortcut when `here_mask != 0`.
- **(guard 5) A walk then a dash can end 3 from the guarded tile** [low]: bot.cc re-guards after the plan search;
  check the other walk-then-dash flows, now including CHANGES 274's travel.
- **(safety 6) `fighting_allies()` and `Reach::build` caches are keyed on the round** [low, small]: allies seen after
  `see_again()` join fights only next round. Key on an observe counter.
- **(safety 7, guard 2) Teleporting enemies strike from `e.pos`** [low, small] in `engagement_near` and the pack
  zone; use `tp_dest` for their strike (our reach to them stays from `e.pos`).
- **(safety 8) `unseen_weight` is heuristic** [low, med]: counts off-map tiles; `unseen_radius` approximates where
  the chance crosses `credible_weight`. Exact: `count_within` at the boundary or a prefix sum over `possible`.
- **(abilities 2) Unseen-target damage** [low, small] leaves out our `champion_dealt_factor()` and the enemy's
  last-seen shield, as does the `damage_to` fallback. Exact: `raw * dealt * e.taken`, less the shield.
- **(abilities 3) The free-stun test counts only visible reachers** [low-med, small]: count an unseen threat whose
  area covers `here` as unstoppable.
- **(abilities 5) `stun_worth` may read a stale tribute on an unseen enemy** [low, trivial]: its tribute term doesn't
  need `visible`. Check how world.cc keeps `channel` out of sight; gate on visibility or age.
- **(abilities 4) Hits on a recalling enemy don't price the cancelled recall** [med, small]: only `hit_worth_of`
  adds `recall_value`; plan.cc's `hit_unit`, `land_at` and `best_hit` don't, and `x.recall` is read only with a cast
  ready. Always read it, add it on non-kill hits, narrow `hoisted()`'s recall exception. Context: our turn-end
  recall makes enemies look like they recall in ~90% of rounds locally (ladder 5-8%), so any recall-cancel value is
  inflated in self-play A/Bs.
- **(bot 6) The turn-end recall feint shows us recalling to every enemy** [unknown]: it saves a turn on a wanted
  recall; whether ladder bots read the signal is unmeasured, and dropping it was never A/B'd.
- **(fight 1) A ranged dasher one step out walks instead of dashing** [low, small]: since CHANGES 213 only when the
  strike search didn't see every enemy (`!searched`) and in `stop_game_ender`. Gate on
  `dist > range + (ranged && !reset_ready ? 0 : 1)`; a judgement call, as it spends the escape dash.
- **(fight 2, world 4) Simultaneous tributes** [low, med]: `game_ender` flags single bags, so two enemies (or Cassi
  and Issac) whose bags together win go unstopped; `update_scores` empties no bag when several channels end at once
  unless one equals the delta (empty all when they sum to it).
- **(fight 3) `prey`'s self-delay test is ranged-only** [low-med, small]: `strike(self, round).hits(dist)`, as for
  allies, also covers melee two out and ranged at range + 2.
- **(fight 5) `ally_stops` refuses any enemy in a bush** [low, small], though a lock needs no sight and Ryth's ground
  stun hits unseen enemies.
- **(fight 6) `intercept_steps`' walking branch counts reaching range at the altar as a stop** [low, small]; a
  walking carrier needs a kill, stun or lock (`kill_turn` against the channel). Fired in 5 of 1164 games.
- **(champions 1) Marcella's stun needs a spent attack and the reset** [low, small]: `ready_stun_reach` counts her
  reset whenever ready; ally and enemy paths ignore a spent attack with the reset on cooldown (`read_stuns` handles
  self).
- **(champions 2) `raw_output` misses Varg's splash and Ren's retaliation** [low, med]; draft's `spells` also drops
  HoR's landing (harmless while gated on ranged).
- **(self_abilities 1) Varg's `shield_wanted` and `shield_if_needed` disagree** [med, small], so Varg can end a turn
  with neither reset nor shield. Share one `Safety`-based test, but first record which groups our attacks touched
  (`shield_if_needed` counts every group in range once the attack is spent, so it would shield against a camp it
  never woke); "Camps we wake this turn" below needs the same record. A retreat step after the hold can also leave the shield's
  reach. Tried: the shared test alone (CHANGES 210 bundle, level), dropped over the camp case.
- **(self_abilities 5) A Cassi/Issac kill is worth one body** [low, small] in `hit_worth`; add the partner's health
  when known (CHANGES 271 changed chip damage only).
- **(self_abilities 6) No shield on spawn** [low, judgement]: only if spawn deaths show in replays.
- **(combat_priority 1) A dead champion holds a turn slot** [unknown, trivial]: `dead_priority` (13) ranks it above idle
  allies, so the living act an alternation later. State why or A/B.
- **(turn_order 1) `side_damage` misses allies yet to act this round** [low-med, small]: they strike before the enemy's next
  turn whatever the order, but only next-round turns count, so kill bids are under-offered in team fights (an
  unacted enemy also moves in between).
- **(turn_order 2) Enemies on their spawn are never kill targets** [low, judgement]; a burst from outside can kill.
- **(turn_order 3) `offer_heal`** [low]: the ally's next camp hit is not counted from its side (its emblems, the
  nearer-champion cut) [med]; an unacted enemy that can stun us voids the heal (`offer_channel`'s test) [small].

## Camps

- **(bank 3, self_abilities, siege, support, world 5) Camp fire ignores the nearest-champion rule** [med, small each].
  A monster hits only the nearest champion in its range (ties by turn order), but these sum every member in reach:
  `access_fire` (seals altars a crew could use), `threats_near` and `shield_if_needed` (needless escapes and
  shields), siege's `low` (a ranged sieger behind a tank; `kite_productive_action`'s `exposure` already models it)
  and `siege_ready`'s pool, support's exposure, and maybe callers of `CampGroup::strength` / `threat()`. Skip a
  member a visible champion is strictly nearer; count ties. Done: siege's leave test (252), crew damage (256),
  Willow on Safety's `camp_damage` (49.3%, kept). Tried: batch 2's P3a/P3b/P4, lost bundled with P5 (ladder -8, OOF
  +40%); batch 1's `recall_outruns`, reverted. TODO holds the clear-pricing version (level, OOF +36%).
- **(safety 2, self_abilities 1; TODO Bugs 1) Camps we wake this turn stay asleep** [med, small-med]: `refresh()`
  checks only deaths and stuns, so `camp_damage`, `camp_area` and `lethal` miss them for the rest of the turn. Fix:
  a per-turn set of groups our attacks and splash touched, read by `refresh()` and `shield_if_needed`. Tried:
  re-reading all state after our hits, 47.3% (lean 49.3%); retry with only the reads that change a decision.
- **(camps 1, self_abilities, plan; TODO Bugs 2) Varg's splash wakes neighbouring groups unpriced** [med, small]:
  farm's cluster hits, targets an `allowed` filter rejected, `attack_target` on an enemy beside a sleeping group,
  `reset_and_attack_camp` (also lacks the Monolith check; could pick the member whose 3x3 holds the most killable
  members) and `best_hit` (the search prices it through `touch1`). With `landing_wakes(world, pos, splash_radius)`,
  skip such targets unless the hit kills (or the group is already `fully_awake()`); a judgement call, as the
  neighbour is sometimes next anyway.
  Partly: a ban (CHANGES 87) was held; the priced version is untested.
- **(camps 6) The splash score reads stale health** [low, trivial]: neighbours count by `health[j] > 0`, 0 after an
  unseen respawn; test `live`.
- **(plan 2) `wake()` bans any group with a sleeping Monolith** [judgement]: price it like other strikers; ban only
  when we or an ally would be in its reach.
- **(self_abilities 3) `danger` weighs every camp as 2** [med, med]: a wolf counts as a Monolith or an enemy. Use
  Strength x `camp_hit_factor()` and `threat_strike(...).at(d)`; drop stunned camps.
- **(siege 1) Siege `exposure` counts groups that can't attack soon** [low-med, small, judgement]: respawning groups
  and asleep members of other groups.
- **(siege 5, params 3) Siege's pool check uses the team's max health and our own `camp_hit_factor()`** [low, small]:
  use last-seen ally health and each ally's taken factor.
- **(abilities 6) A camp stun is worth the raw Strength** [trivial]: scale by `camp_hit_factor()` when we're the
  target; a hit on an ally counts the same.
- **(farm 3) `struggling` overstates an ally's danger** [low, small]: ignores its Jungle/Durability, shield, heals.
- **(world 1) Wake inferred from a health drop** [low-med, small] (`read_members`): if asleep at `health_round`, the
  test should be `<=`; if already awake, damage doesn't keep it awake. Branch on the prior `member_asleep(i)`.
- **(world 2) Unseen awake groups go unknown a round late** [low-med, judgement]: exact needs the round each member
  last had a champion in range.

## Clear and farm model

- **(camps 2, farm 4) Ren's clear damage** [med, med]: `min_camp_damage`'s reflect path charges every living
  attacker every round, not those reaching the stand tile (needs `clear_fire`'s per-member masks), and the partner
  clear passes no `reflect`, overcosting it.
- **(camps 3) Ground spells reach 5** [low-med, small]: `spell_clear_rounds` rejects any group with reach-4
  attackers, and siege's out-of-reach casting leaves only wolves, falling back inside reach. Stellar and Prism hit
  elk and golems from 5: give siege `kite`'s ground stations and aim `cast_at_camp` at a centre beside the member.
- **(camps 4, siege 3) Spell kiting by champion kind** [low-med, small]: farm (`ranged ? spell_output : 0`) and
  draft's `type_facts` leave out Marcella, Ren and HoR's landing, which out-range wolves; let `spell_clear_rounds`
  decide. Siege's `unit_stations` skips `kites_with_spells`, so Marcella and Ren stand at unit stations while shop
  buys them Strength: gate it on `kites_with_spells` too, or document why. Partly: CHANGES 201's rule for shared-gem `kite()` (59.2% of 120); Marcella's stations 50.3%;
  guards outside the group 49.5%.
- **(camps 5) `stand_reach`'s stand tile is a guess** [med, med]: range tiles out from the group's middle, ignoring
  walls and camps. Exact: per member, the min over standable tiles in range of the striker mask; lazy per group.
- **(camps 7) `min_camp_damage` ignores walking between stand tiles** [low-med, med].
- **(farm 1) `spell_clear`'s kite tile ignores other groups' reach** [med on dense maps, small]: add awake strikers of
  `groups_near`, or drop goals in Safety's camp threat.
- **(farm 2) A hop group's recall out is counted in `steps`** [low, small]: it shrinks the respawn wait and inflates
  `help_steps`; move it to `bank` / `cycle_bank`.
- **(crew_work 1, 2) Arrivals are a turn early when a spell or a ranged attack closes the gap** [low, small]: an
  excludes-walking spell can't follow a walk (`min(f(d - basic), f(d - spell) + 1)`), and Prism, Stellar and Cassi
  can't attack after walking.
- **(siege 2) `kite_productive_action` gives up near a harmless member** [med on stampede maps, med]: prepare cluster
  viewers in `kite`'s `prepare_member` loop, then hit clusters with basic attacks.
- **(params 4, siege) `kite`'s target** [low-med, small]: Chebyshev distance to the centre, not steps; a cleared
  group failing `capture_taken` or beyond `2 * vision_radius` ends the kite instead of trying the next group.
- **(siege 4) Siege staging counts only visible allies** [low, med]: use claims or last-seen positions.

## Heart of Ruin

- **(abilities 1) Enemy-hitting landings skip `camp_cast`'s costs** [med, small]: leaving a capture we hold, and
  landing in an awake monster's reach (reuse `landing_threats`). `min_landing_value` 250 partly covers both.
- **(plan 1) Landings near sleeping camps are banned, not priced** (`land_bad`) [med, med]: route through `wake_at`,
  crediting the landing's stun of members within 1 (their first hit dropped). CHANGES 274 keeps the travel veto too.
- **(guard 6) The guard ignores the landing's stun** [med, med]: a tile beside an enemy may be best because that
  enemy loses its turn.
- **(safety 4) Its passive is frozen in fight sims** [low-med, small]: a per-fighter `missing_bonus` in `act()`.
  Tried: in batch 2's P5, lost bundled, not split.
- **(self_abilities 2) A landing beside Ren then an attack draws two retaliations** [low, unverified]: neither
  `landing_suicidal` nor `attack_target` (nor `step_to_kill`) sums them. `dash_to_attack` also ignores the shield.

## Capture, banking, comms

- **(capture 1) Gold-only groups are never contested** [low-med on Tavi-gold maps, small]. Partly: wider contests of
  gem holds were level or lost (best 50.6%).
- **(capture 2) `enemy_hold_left` ignores the Capture emblem** for unread holds [low, small]: bound 4 and
  `min(R+6, J+3)` with `fast_capture`. Siege shares it.
- **(capture 3) `free_hit` treats an unknown group as awake** [low, one line]: `fully_awake()`, as farm does.
- **(capture 4) Endgame tests use `width + height` for the walk to an altar** [low, small]: `to_any_altar().at(p)`
  is cached; the Marcella branch also leaves out the tribute turns.
- **(capture 6) Contests of gem holds the enemy can't bank before round 2000** [endgame, med].
- **(bank 1) `closing` ignores crystal routes** [low, small]: `hop_route(...).steps`, moved above it.
- **(bank 4) `access_fire`'s cache is keyed on (round, access version)** [low]: a camp woken later in the turn reads
  stale fire; add the camps' version. Harmless while callers run before attacks.
- **(bank 5) `place_lock` tests allies' bags one at a time** [low]: sum the bags at the altar.
- **(bank 6) `recall_landing` ignores unseen allies** [low]: at most a step in `closing`.
- **(bot_parts 1, shop 8) `note_income_start` misreads income** [low, small]: a payout in the window our tribute
  completes in is lost (gems fell), and Marcella's tribute gold with it (record a completing tribute in
  `note_income_end`); Ren's retaliation kill gold reads as capture gold. Prospector and Capture pricing run low.
- **(comms 1) A capture record can be overwritten unread when turn order changes** [low-med, small]: `send()` guards
  only records fresh to us and `told_respawn` stops re-posting. Guard one written or read last round while a
  teammate's order moved past us, or let the poster re-post once.
- **(comms 7) Bags clamp at 127 fours (508 gems)** [low]: one more bit where there's room.
- **(support_mailbox 1) The round tag aliases after 4-5 skipped turns** (`round & 3`) [low, trivial]: bits 11-15 are
  free; use `round & 31`.
- **(support_mailbox 2) The first message after a gap is dropped** [low, trivial]: the payload carries its round;
  clear only `sent` / `positive`.
- **(support_mailbox 3) One healer, one protected mate** [unknown, med]: a per-ally "wants heal" bit.

## Willow and Prism

- **(support 1) Prism's window with Willow in a bush** [low-med, small-med] is still `attack_viewers`. Exact: cast
  from her tile with every bush but her cluster opaque.
- **(support 2) `formation_turns` survives a lost mate** [low, design]; resetting both is untested.
- **(support 3) Only Willow skips cleared camp tiles** [low]: Prism may step on one, which becomes a hold and ends the
  support. Check the intent.
- **(support 4, 5) Split `local_support`** (~200 lines, two roles) into `prism_recovery` and `willow_formation`
  [med effort, byte-identical]. The bench never pairs Prism with Willow: bench with `map_model_draft = false` or a
  composition with both.

## Shop

- **(shop 1) Greed is never bought** [low-med]: candidates compare `saved` at 150 each; Greed (750, paid only at 25
  shards) needs a per-gold or multi-emblem comparison. The emblem table (CHANGES 232-233) now buys Collectors and
  Skirmish. Tried: Greed as a candidate, never bought (p2w2-sinks).
- **(shop 2) `main_stat` ignores Focus-scaled heals and shields** [med for Willow, low]: Willow's 3x heal, Varg's and
  HoR's shields, and HoR's landing in the `spells` prior. Partly: heals and landings only bundled with CHANGES 207
  (49.2% vs 51.3%, cut short); shields untried.
- **(shop 3) `affordable_prefix`'s one-entry cache thrashes** between `gold_in > 0` and 0 [fuel, low]. Not fuel-only
  as is: the key leaves out items, upkeep and income.
- **(shop 4) Prism never shops from where walking can't reach spawn** (`back == unreachable`) [low].
- **(shop 5) The shop trip's `hurt` reads the altar field** though we walk back to `here` [low].
- **(shop 6) The lock comes from leftover gold** and can delay the next shard; unpriced [low, med].
- **(shop 7) Ryth's Power Health is not a candidate** [low, trivial]: `value(power, health_stat)` for
  `health_strength`.
- **(shop 9) Tavi's full-refund sales are unmodelled** [low, med]: re-spec when the main stat flips.
- **(bot 1) `count_use`** [low, trivial] misses Vendetta's kill-readied casts and counts Vesper's walk + dash + reset
  + attack as 2 attacks; compare cooldowns with the turn start.
- **(params 5) The gold-farmer test is written in draft.cc, farm.cc and crew.cc** [low]: one helper.

## Paths and wards

- **(pathing S1) make_way backs off from allies that won't move** [med, small]: channelling, holding a capture or
  parked. Read the adjacent ally's state and treat its tile as a wall. (CHANGES 253 fixed the line of allies.)
- **(pathing S3) An unreachable centre field at range 0 means no approach** [low, small]: return null without the
  walk_cap search.
- **(pathing S4) `prepare_approach` underbudgets unfarmed groups**, which may build `from_ally_spawn()` [low].
- **(pathing S5) `attack_tiles` drops other cleared groups' camp tiles** [low]: exclude `live_camps()` instead,
  cached by `live_flips()`. CHANGES 254 did it for siege's fire tiles.
- **(pathing S6) `attack_tiles` ignores our ward** [low, design]; the strike search already uses it (`ward_sees`).
- **(pathing S8) In danger, the whole danger region is freed** [design]: route to the nearest safe tile first, or
  free only its edge.
- **(bot 2) The bush ward's tile** [low-med, moderate] is the first of 3 cluster tiles; pick the one whose radius-6
  square covers most of the cluster near us and our work. The "not beside us" preference is unexplained.
- **(bot 3) An ally's ward on our drafted tile** [low, small]: its sight isn't ours, so take a neighbour; an unseen
  one is a hidden blocker retried every turn.

## Draft and map

- **(draft 1) Later draft turns can't afford big ward sites** (`5000 + 2000 * area` over the 40k reserve) [low,
  latent]: if round 0 doesn't finish the search, no later turn will. Split a site's candidates across turns.
- **(draft 2) `type_facts`' heal walk is Chebyshev** though `a.steps[g][0]` is known; farm differs slightly [low].
- **(draft 3) `best_ward` measures own sight from the group centre**, not the camp or tribute tiles [judgement].
- **(map_economy S1-S6) Supply weights** [low]: they now feed only `stellar_map` (capture) and `tavi_map` (crew,
  farm, `choose_table_draft`). Monoliths inflate `gems` (S1); weights ignore clear time (S2); `total_gems` counts
  unreachable groups and Monoliths (S4, table draft only); `mixed_gems` is unweighted (S5); groups between the spawns
  count fully for both (S6). The thresholds are tuned: change them only through an A/B.
- **(map_features 2) Fuzz `travel` against `Grid.travel`** in `tools/draftlab/` [low, small]: no corpus map caught
  the level-2 bug; a scratch 30-line fuzz is in `replays/audit-mf/fz.mjs` + `fz.cc` (gitignored).
- **(map_features 3) Detour's `cheby` overstates the spawn gap by `sw - 1`** [low]: harmless as fit; fix and refit
  if metrics change.
- **(params 1) `track_horizon` is a fixed 10 rounds** [low-med, med]: a 21x21 square on 100x100. Tried: 5 rounds
  49.2%; no horizon, identical games at +10% fuel.
- **(params 2) One recall line for every champion** [med]: by threat since CHANGES 235 (0.18 or 0.35); a
  per-champion line (HoR's low-health damage, glass bodies) is untried.

## World and memory

- **(bot 5, review 2026-10-28) `memory.damage`** [low-med, moderate] is net of Willow's heals between turns, and on
  spawn the turn-end heal hides hits. Keep "under fire" (spawn hits count) apart from survival and upkeep (they
  don't, unless one round's could kill), then decide per consumer: `tribute_safe`, bank's keep-channel test and
  altar retreat, `note_upkeep`. Tried: recording max health on spawn, in the 11-fix bundle (49.7%), dropped.
- **(world 3) The respawn window assumes the last full update was last round** [low]: use the previous
  `updated_round_`. `tools/replay/audit_beliefs.py` reads the window.
- **(main 2) While dead, the queue warms around the death tile** [low, small]: warm around spawn and the walk out.
- **(main 3) Turn 1's queue budget ignores start-up** [low]: bench runs warm more than the ladder.
- **(main 4) Arena capacity is unmeasured**: print `arena_used` at round 2000 of a long 100x100 game.

## Fuel gates and costs

Existing gates to make bounded ([FUEL-GATES.md](FUEL-GATES.md)); most wait on cheaper fight sims (TODO).

- **(guard 1) The step guard drops entirely on fuel** (`step-guard-entry`, `-look`; `-sim` keeps part) [med,
  small-med]: return the bound-pass tiles as the guard, or cap the work. Causes TODO's two-round cycles. Tried:
  narrowed gates (CHANGES 176, OOF +16%); folded into the strike search (no gain); `stand_of` with limits (OOF 861 ->
  2931).
- **(fight 4) `prey-cut-short`** [med]: bound `chase_trade` per call. Tried: narrowed in CHANGES 176, OOF +16%.
- **(farm 5) `farm-partial-evaluation`** [med, large]: resume the loop across turns, or re-weigh only changed groups.
  Partly: the nearest-order stop (CHANGES 175, banking too since 226); ungated at 12 estimates, OOF 2193 vs 416.
- **(champions 4) `farm_dash_kind`** [med, med]: on many-group maps dashers lose dash-aware fields; cache per-group
  fields or build them across turns.
- **(pathing S2) `static-descend` fires before the kept route is consulted** [low-med, small]: check in `route()`
  just before a search runs.
- **(pathing S10) The wide re-search (`here + 6 * max_detour`) runs unchecked** after a failed capped search and
  descend: a known cost; bound it only through an A/B or a resumable search.
- **(siege 6) `siege-no-tiles` and `kite`'s `prepare_member`** [low]: warm the claim's boards in spare turns; keep
  the stations already prepared (CHANGES 266 keeps built ones).
- **(comms 6) `comms-stale-vision`** [low, med]: the observe now feeds only respawn records. Removing the gate raised
  rounds 1-10 OOF (CHANGES 250).
- **(plan 3) `read_spells`' `my_damage_to` per foe per slot**: drop it if `raw * x.taken` with the shield matches.
- **(abilities 7) `camp_dealt_factor()` per `camp_cast`**: cache per turn; also `damage_to`, `wake_risk`,
  `dash_landings_from`.
- **(self_abilities 7) Cheap `ready()` checks first** in every-turn callers such as `shield_wanted`.
- **(farm 6) `engaged`'s bound** could use `threat_radius()`.
- **(util 1) The capped `make_field` rejects complete fields at D = cap - 1 and cap** (probed): pass cap + 2, or test
  `visited`'s border; only if it shows in profiles.
- **(main 5) A resumed out-of-fuel queue keeps warming**: test `world.is_stale()` in `room()`.
