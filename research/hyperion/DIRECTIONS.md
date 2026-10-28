# New directions (from the 2026-10-28 audit)

Every suggestion from the 30 per-file audit reports, grouped by report. Deduplicated: a suggestion several reports
made is one entry, at its first appearance, naming every report that raised it, e.g. "(camps, draft, farm)", with the
other reports' wording kept beneath it and a pointer left at each other place. Marked: a `> Tried:` note under an
entry gives a past result (EXPERIMENTS, CHANGES, or TODO where it records data); `> Partly:` when only a narrower or
bundled version ran; `> Context:` for a measurement that bears on it. Each report's own Changed / Considered sections
stay in [audit-2026-10-28](audit-2026-10-28/README.md).

Done items are removed and the lists renumbered: the mechanical batch (renames, moves, dead code, asserts,
fuel-only caches) is CHANGES 204.

## abilities ([report](audit-2026-10-28/abilities.md))

1. **Escape stun certification is stricter than the rules** (l.354, `controls = e.acted && ...`). With `!e.acted && turns_before_ours(world, e) == 1`, the enemy's only turn before ours is later this round, and a stun removes exactly that turn (rules: abilities.stun), so it's controlled just as well. Dropping `e.acted` would let Prism's escape certify more stuns. I double-checked against `turns_before_ours`: for a visible enemy, `now = !acted`, plus next-round-before-us. Severity: low-medium (Prism escapes). Effort: trivial plus an A/B.
2. **Heart of Ruin's enemy-hitting landings ignore two costs that `camp_cast` prices** (l.377). (a) A landing off a cleared group we're capturing abandons the capture: `camp_cast` skips it, `enemy_cast` doesn't. (b) Landing inside an awake monster's reach: `landing_wakes` only looks at sleeping groups, while `landing_threats` (now a reusable helper) lists awake monsters that would newly reach a landing. `min_landing_value` = 250 partly covers both. Severity: medium for HoR, which is drafted often. Effort: small (reuse `landing_threats` in the keep, plus the capture check), then A/B.
3. **Unseen-target damage estimate** (l.277: `min(raw * e.taken, health)`). It leaves out our Skirmish/Collectors `champion_dealt_factor()` and the enemy's shield (`e.shield`, Varg/HoR) when last seen. The native-failure fallback `damage_to` (l.68: `min(raw, health)`) has neither mitigation nor dealt factor either. Exact versions are cheap: `raw * dealt * e.taken`, less the shield. Severity: low. Effort: small.
4. **Free-stun only counts visible reachers** (l.305-316). A tracked unseen enemy that could reach us next turn is ignored, so a stun on the visible one is taken as making the walk worthless while an unseen threat remains. `Safety` already has unseen threat areas. Consider counting any unseen threat whose area covers `here` as `unstoppable`. Severity: low-medium. Effort: small, needs an A/B.
5. **`hit_worth` exists twice** (here l.79 and `plan.cc:117`, with different signatures and the same maths, but plan.cc's lacks the recall term). Share one in a header so the cast menu and plan search can't drift apart. Severity: maintenance. Effort: small, cross-file. (abilities, plan)
   - plan: **A basic attack or HoR landing on a recalling enemy does not price the cancelled recall**
     (medium severity, small effort). By the rules, any damage cancels a recall, but `x.recall` is
     read only when a non-landing cast is ready (`recall = casts && ...`, :1139), and only
     `spell_unit`/`centre_value` add `params::recall_value`. `hit_unit`, `land_at` (whose `land_stun`
     uses `stun_worth(..., damaging=true)`, which leaves the recall out) and `best_hit` (strike_enemy)
     never add it. abilities.cc's `hit_worth` does add it for any non-kill damage, so the two files
     disagree. To fix: always read `recall`, add `recall_value` on a non-kill hit in `hit_unit` and
     `land_at` (and in `Board`), and narrow `hoisted()`'s recall exception (:718) from spells to any
     strike on a recalling foe.
   > Context: locally enemies look like they are recalling in ~90% of rounds (our recall at every turn end) against
   > 5-8% on the ladder, so any recall-cancel value is inflated in self-play A/Bs (EXPERIMENTS Lessons).
6. **`stun_worth` on unseen enemies reads `e.channel`** (tribute/recall/teleport terms, l.90-101) for area targets. `recall_kept`/`teleport_pending` require `visible`, but the tribute term doesn't, so a tribute seen long ago could keep adding `tribute_value + gems` to an unseen target. Check how world.cc maintains `channel` out of sight (it says "hidden completion may clear channel"). If it can stay stale, gate the tribute term on `e.visible` or on channel age. Severity: low. Effort: trivial once checked.
7. **Camp stun value** (l.461-467) is the monster's raw Strength. It could be scaled by our `camp_hit_factor()` (Jungle/Durability) when we are the nearest target, and it counts a hit that would land on an ally the same as one on us. Minor. Effort: trivial.
8. **Spawn healing under a stun** (`hit_worth`, l.82: non-kill damage to an enemy on its spawn is worth 0 because it heals at its turn end). If a stunned champion's turn end still runs (`rules: turn_end` vs `stun` "removes the target's next turn"), that's right; if a stun skips the turn end too, damage plus a stun on a spawn-camper keeps value. Worth a probe if spawn fights matter. Severity: low.
   > Probed: the lost turn's end still heals on spawn (`probe-stun-spawn-heal`, 2026-10-28), so `hit_worth`'s 0 is
   > right. Nothing to change.
9. **Fuel**: no fuel gates in these files. `max_unseen_tiles` is a bound on aiming work, not a gate. Remaining cost centres are `damage_to` (one host call per visible enemy per slot) and `wake_risk`/`dash_landings_from` (several bitboard calls). The `camp_dealt_factor()` read (items host call) now runs once per non-empty `camp_cast`. It could be cached per turn by whoever owns util/camps.
10. **`cast_at_enemies` stale check** (l.571): either always re-check after `enemy_cast` (it's cheap) or never. The current `lethal_landings_only || attempted` condition reads as an accident.

## bank ([report](audit-2026-10-28/bank.md))

1. **`closing` ignores crystal routes (l.420-428). Gap; low severity, small effort.** With no walk from here or from the recall landing (an altar only a crystal reaches), `walk` becomes 0. The bag then reads as "closing" only `walk + recall + crystal` rounds too late. `hop_route(...).steps` (which already includes the recall out) is the exact figure when we carry or can buy a crystal. It would need `hop_route` moved above `closing`.

2. **`bankable_bag`'s pocket test reads the field at `ally_spawn_centre` (l.371). Gap; trivial.** `closing` reads it at `recall_landing(world)`, which is where a recall actually lands. The two should agree, and the landing tile is the exact one.

3. **`tribute_safe` ignores shields (l.94). Gap; Varg and Heart of Ruin only; small.** It compares `memory.damage * window` against `my_health()`. A live shield (Varg's 2.5x Focus, Heart of Ruin's 1.5x) absorbs damage first. Adding the shield value would let them bank in windows they now skip.
   - `turns_to_kill_idle` may already count the shield through `fighter`; I didn't verify that.
   - `Safety::lethal` adds `shield_value(...)` to health the same way, so this is consistent with existing code.

4. **`access_fire` sums every awake member in reach of the tile (l.349). Gap; low.** A monster attacks the nearest champion in its range (`camps.attack`). With an ally standing nearer to the monster, we take less. For a lone banker this is exact; for a crew at an altar it overestimates and can seal altars that are usable. (bank, self_abilities, siege, support; bot 2's last bullet makes the same point about `camp_damage` on spawn)
   - self_abilities: **Camp threats ignore "nearest champion".** Files: `self_abilities.cc` `threats_near` (~line 63), `shield_if_needed` (~line 545). Medium severity, small effort.
     - The rules say an awake monster hits the nearest champion of either team in its range, with ties going by turn order.
     - Every awake monster in reach is counted as a threat to us. That inflates `danger`, so we escape or skip travel dashes needlessly. It also makes Varg and Heart of Ruin shield when an ally (or an enemy) stands nearer the monster.
     - The fix is exact and cheap: skip a member if a visible champion is strictly nearer to it. Visible champion tiles are already a host bitboard.
     - Equal distance needs the turn order (`rounds.champion_order`); counting ties as threats is safe.
   - siege: **Siege `low` ignores nearest-champion targeting** (`siege.cc` ~190-198). Modelling gap,
     medium severity, small effort.
     - `hit` sums every live member whose reach covers us. A monster attacks only the *nearest*
       champion, so a ranged sieger behind a melee tank takes nothing from members nearer the tank.
     - `kite_productive_action`'s `exposure(p, supported)` already models this, with
       `tanked = ally nearer the member`; reuse it here.
     - `siege_ready`'s pool check makes the same assumption (all live Strength hits the team every
       round for the whole clear). It overstates the cost, because members die during the clear.
       That one is a tuning question.
   - support: **Exposure is all-or-nothing for camps.** support.cc:36-41. Modelling gap; severity low or unclear; effort medium.
     - Any live monster in reach makes a tile unsafe, even asleep ones or ones that a nearer ally draws (camp attacks hit the nearest champion).
     - That is deliberately conservative for Willow ("holds no fight"). But near a camp the team is farming, every tile in reach is ruled out, so Willow may hang back further than heal range allows.
     - An exact version would use `Safety::camp_area()` (nearest-champion aware), plus a margin for the ally leaving.
   > Partly: Assumption audit batch 2's P3a (shared-clear fire by stand tile) and P3b/P4 (fire handed to teammates in
   > steps, lethal camp tiles in retreat) lost bundled with P5: ladder -8 points, out-of-fuel turns +40%, not split;
   > batch 1's C (`recall_outruns` under camp fire, ignoring nearer champions) was reverted (EXPERIMENTS "Assumption
   > audit, batches 1-2"; TODO Candidates). One champion takes 98% of shared clears' camp hits (EXPERIMENTS
   > "Champion-time audit"). Willow's exposure moved onto Safety's `camp_damage` (awake camps), still counting sleeping
   > members on purpose: 49.3%, kept (EXPERIMENTS "Astraeus Willow exposure on Safety").

5. **`access_fire`'s cache is keyed on (round, access version) only (l.310-312). Low.** If our own attack wakes a camp later in the same turn, a later call that turn reads the stale fire. It is harmless today because the callers run before attacks, but it is fragile. Keying on the camps' `version` (`CampBelief::version`) as well would make it exact.

6. **`place_lock` treats each ally separately when testing for a win (l.49). Low.** `ours_wins` checks `score.ally + ally.gems` per ally. Two allies tributing together at one altar, whose combined bags win, still let us cancel them to stop a non-winning enemy tribute. The rule is "worth it only against a win", so summing the allies' bags at the altar is the exact version.

7. **Recall landing ignores unseen allies (l.116-125). Low.** `recall_landing` skips only allies it can see. An ally on spawn just out of sight (spawns are small, so this is rare) or arriving the same round is not considered. The result only feeds `closing`'s walk estimate, so the impact is at most a step.

No fuel gates live in bank.cc. The only fuel-conditioned work related to it is `bot.cc:373`, which warms `flood_altar_walk` when `fuel_ok`. That one is a warm-up, not a worse choice, so it is fine.

## bot ([report](audit-2026-10-28/bot.md))

1. **The mend turn stands still, but `home_trip` prices it as free when a spawn tile is a step closer.** (bot.cc decide's `mend` branch; `economy/shop.cc:543-555`.) Medium value, small to moderate effort.
   - `home_trip` sets `hurt = 0` when a landing tile one step nearer the altar exists. Its reasoning: we step there and the turn end on spawn still heals.
   - `decide`'s `'H'` branch only attacks and casts; it never walks.
   - So the recall's value assumes a step the bot never takes, and every hurt recall arrival costs a full turn (or a step).
   - Fix: in the mend branch, when `my_can_move()` (and for ranged champions, when we didn't attack), step to a spawn tile nearer the next goal: the altar field when carrying, else the farm group's approach.
2. **Mend on a 1-HP deficit.** `mend = on_spawn && my_health() < my_max_health() && ...` (bot.cc decide). Small value, small effort.
   - Any deficit costs a whole turn on spawn; a recall arriving at 990/1000 waits a turn for 10 HP.
   - Making suggestion 1's step removes most of the cost. Otherwise, compare the gain with `heal_rounds_now()`.
   - Also, the camp condition could be exact: mend while `my_max_health() - my_health() > safety.camp_damage(p)`, so a mend turn nets health. That ends the "mend forever" case without refusing to mend at all.
   - `camp_damage` also ignores that a monster hits only the nearest champion, so an ally on spawn nearer the camp takes the hit.
   > Partly: CHANGES 139 added the current camp condition (`mend` skips when a camp can hit our tile, after a hurt
   > champion mended forever under an awake camp); the exact net-health test is untried.
3. **A ranged champion with a dash gives it up after attacking.** `if (attacked && !walk_and_attack_independent()) return;` (bot.cc decide, before wants_shop). Low-medium value, small effort.
   - The ranged attack spends the walk, but no ability spends the walk (rules: `abilities.exclusive`).
   - So Vesper Vale (ranged plus dash) skips shop/chase/contest/siege/farm, and their dash hops, whenever she has attacked.
   - The farm's own dash hops (`take_hop`) could still run with `!my_can_move()`.
   - Check what farm does with a spent walk before relaxing the return for dash holders.
4. **`count_use` misses casts when Vendetta's passive readies both slots on a kill** (bot.cc count_use). Low value, trivial effort.
   - A slot cast this turn then shows cooldown 0, so the cast, and for her reset the extra attack, go uncounted. This feeds `shop.cc:35-40`'s focus-or-strength choice.
   - A related small over-count: for Vesper Vale, walk + dash + reset + attack counts 2 attacks, because `dashed` cancels `walked`.
   - Fix: count casts by comparing `my_cooldown` with the turn-start cooldowns, or set a flag at each cast site.
5. **Bush ward tile choice** (bot.cc `ward_bushes`, the `Tiles<3>{best}` loop). Low-medium value, moderate effort.
   - The ward goes on the first of up to 3 cluster tiles in scan order (those not beside us preferred).
   - A ward's sight is the 13x13 square around its tile even inside its cluster (rules: `vision.occlusion`, `wards.vision`), so in a big cluster the tile decides which part we see.
   - Better: pick the tile whose radius-6 square covers the most cluster tiles within ability range of here and of our work. That is the same score the cluster choice already uses.
   - I couldn't find a reason for the "not beside us" preference. If it has one, it deserves a comment.
6. **An ally's ward on our drafted tile** (bot.cc `ward_planned`). Low value, small effort.
   - A visible allied ward on the drafted tile makes us fall back to a bush ward, but its vision is not ours (rules: `vision.personal`). A neighbour of the drafted tile would give nearly the same sight.
   - An *unseen* allied ward there is a hidden blocker: we retry, and fail, every turn while in range. That's one wasted host call a turn.
7. **Fuel gate in `ward_bushes`.** `if (!fuel_ok(floor)) note_shortcut("ward-no-bushes-fuel")`, plus the `find_bush_clusters(..., floor)` refusals. Low value, moderate effort.
   - The cost is only a ward a turn late, and main.cc's turn-end queue already grows clusters around us.
   - To remove the gate, make the end-of-turn bush ward choose only from clusters already grown, so its cost is bounded. A missing cluster then waits for the queue instead of for fuel.
   > Context: in the gate-removal runs the ward gate was the second culprit after pick_up's (`fuel/no-gates-1c`, 5.1x
   > out-of-fuel turns, all gates together; EXPERIMENTS Fuel, "Gate removals"). CHANGES 174 has the turn-end queue grow
   > `ward_bushes`' clusters around us first. The bounded version is untried.
8. **`memory.damage` is net of a teammate's heal between our turns** (bot.cc play_turn). Low value, moderate effort. Willow healing us hides damage taken in the same gap. Reading heals would need buff or heal events; I'm noting it only because several branches read `damage > 0` as "under fire".
9. **Recall started at every turn end** (bot.cc `start_recall`). Unknown value; needs an A/B or a look at enemy bots. The trick makes a wanted recall a turn shorter, but it shows us as `recalling` to every enemy that sees us (rules: `vision.visible_champions` exposes state). An enemy bot that hunts recalling champions, or reads it as retreat, gets a free signal every turn. Worth weighing against the turn saved.
    > Context: because of it, enemies look like they are recalling in ~90% of rounds locally against 5-8% on the
    > ladder (EXPERIMENTS Lessons); dropping it has not been A/B'd.

## bot_parts ([report](audit-2026-10-28/bot_parts.md))

1. **camps.cc:35, bot_parts.h `CampAttackTargets`: candidates are truncated before they are ranked.** `camp_attack_targets` fills `found[16]` in `positions_within` scan order and only then sorts by score. A ranged champion reaches 48 tiles, so next to a big group (or several groups) the best-scored member can be dropped unseen. Fix: keep the top 16 by insertion while scanning; it is just as bounded.
   - Fuel: `attack_camp_targets` tries targets in order, and each refused attack throws (about 3.9k). Sixteen unseen live tiles (bush-hidden camps, stale beliefs) could cost about 62k. A cheap visibility test before each `attack()` would bound that without a fuel gate.
   - Severity low to medium; effort small.
2. **`decision` drives behaviour.** act() reads `'W'` and `'C'` (bot.cc:404/407), and farm reads `'F'` (farm.cc:393). Branch logic keyed on a trace letter is fragile: renaming a letter, or setting `'F'` from capture.cc:220, silently changes farming. Suggest an `enum class Branch`, or explicit flags such as `sieged`. Severity low; effort small.
3. **shop.cc:572 `note_income_start`: a payout and a tribute in the same window are lost.** A capture payout that arrives in the same window as our tribute completing is not recorded. Tribute completes at our turn end, after `note_income_end`, so the next start sees `gems < gems_at` and skips the payout. The rules let a channelling champion on a camp tile hold it, so this can happen whenever we tribute from a camp tile next to an altar. I haven't checked how often the bot does that. The result is that Prospector/Capture passive pricing (`income.holds`, `prospected_*`) runs slightly low.
   - Exact fix: also record in `note_income_end` that a tribute is about to complete (`my_channel_time() == 1` with channel tribute), and take `gems_at = 0` for the next start.
   - The same applies to Marcella's tribute gold, which arrives in that window.
   - Severity low; effort small.

## camps ([report](audit-2026-10-28/camps.md))

1. **Varg's splash wakes other non-Monolith groups too** (camps.cc:38-62, and `reset_and_attack_camp` in combat/self_abilities.cc:289). Two cases:
   - Farm's harmless "resource" hits on a cluster can wake a diagonally adjacent wolf, elk or golem group.
   - An `allowed` filter (siege's `h == g`, support's harmless-only) can wake a group it rejected.

   Whether that is acceptable is a judgement call (sometimes the neighbour is next anyway), so it is unfixed.
   - Suggested fix: for Varg, reject a target whose splash reaches a live camp of a group `allowed` rejects and that is not already `fully_awake()`.
   - `reset_and_attack_camp` also needs the Monolith check added here, because it picks its own target. It belongs in self_abilities.cc.

   Severity medium for Varg drafts; effort small. (camps, self_abilities, plan)
   - self_abilities: **Varg's splash wakes camps, and it isn't modelled.** Location: `attack_target` ~line 245, `reset_and_attack_camp`. Medium severity for Varg, small effort.
     - Varg's basic attack also hits camps within 1 of the target. An enemy standing next to a sleeping strong group (wolves, elk, golem, monolith) is valued only for its champion damage, and hitting it wakes the group onto us.
     - `landing_wakes(world, t.pos, splash_radius)` already answers this; skip such targets unless the hit kills.
     - In `reset_and_attack_camp`, Varg picks the member nearest death and ignores the splash. Choosing the member whose 3x3 holds the most (or the most killable) members would be exact.
   - plan: **`strike_enemy` ignores Varg's splash on camps** (low, small). `best_hit` sums splash only on
     enemy champions, so a Varg attack next to a sleeping camp member wakes its group without that
     being priced. The search does price this through `touch1`. farm.cc calls `strike_enemy`, and so
     does plan_strikes' fallback after a refused move.
   > Partly: audit phases 2-3 (CHANGES 87) had Varg's attacks skip any target whose splash touches a sleeping camp; it
   > was held as a ban where the search prices wakes, and the priced version (wake cost on champion hits, waking camp
   > targets ranked last) is untested (EXPERIMENTS "Audit phases 2-3"). Still TODO Bugs 2.
2. **Ren's damage model ignores reach** (camps.cc:205-224, the reflect path of `min_camp_damage`). It charges every living attacker every round (`left[j].strength * k`). The non-reflect path charges only the strikers whose reach covers the stand tile (`fire`).
   - On spread groups (a line of golems, mixed elk and wolf), Ren's clear damage is overstated, so farm and finishing_camp turn down clears Ren could take.
   - Fix: charge `fire`-masked strikers. That needs `clear_fire`'s per-member masks, not just its sums.

   Severity medium for Ren; effort medium.
3. **Ground spells reach 5, not 4** (camps.cc:434, `spell_clear_rounds`). Ground casts hit the 3x3 around a tile within 4, so `AbilityFacts::reach()` is 5. An elk or golem (range 4) can be hit with no reply from distance 5 by Stellar's or Prism's ground spell, but the code rejects every group with an attacker of reach >= 4.
   - Exact model: ground-spell output only, against attackers of reach 4.
   - Value is low (Stellar's ground spell does ~12/turn against a 2400 hp elk), so it would mostly matter for finishing a wounded elk.

   Severity low; effort small. (camps, siege)
   - siege: **Siege casters never cast from out of reach of elk, golems or Monoliths** (`siege.cc` ~222,
     `tiles(ability_range)` minus threat). Modelling gap, medium severity, small-to-medium effort.
     - The "cast from out of its reach" branch builds tiles within 4 (ability range) of a live member
       and drops the threat. Every member with reach >= 4 (elk, golem, Monolith) threatens all of
       those tiles, so the set is empty except for wolves. The caster then falls back to `range`
       (3), inside reach.
     - A **ground** spell reaches 5 (range 4 plus radius 1). Stellar and Prism could hit an elk or
       golem (reach 4) from distance 5 without being hit, as `kite`'s ground stations already do.
       A Monolith (reach 5) has no such tile.
     - Fix: give ground casters the stations `kite` builds (centres within 1 of a member, cast
       tiles within 4 of a centre, minus threat), and check that `cast_at_camp` aims ground casts
       at a centre next to the member.
4. **Spell kiting is ranged-only** (economy/farm.cc:662: `spells = ranged ? spell_output : 0`). Marcella's 2x unit spell and Ren's 1.1x reach 4 > wolf range 3 just as well, and `safe_targets` already handles melee basic attacks on harmless members. This looks like an arbitrary restriction. Severity low-medium (Marcella drafts on wolf maps); effort small, but it changes behaviour, so A/B it. (camps, draft, farm)
   - draft: **Kiting is modelled only for ranged champions**, both in `type_facts` (`spells` needs
     `f.ranged`) and in farm (`economy/farm.cc:662`). Melee champions with a unit-target damage spell
     (Marcella 2x, Ren 1.1x, range 4) out-range wolves (range 3) just as well; the rules allow a melee
     champion to cast without walking into range. This is a modelling gap that belongs to farm
     first; the draft should follow whatever farm does. Medium effort; needs an A/B.
   - farm: **Melee damage spells never kite** (`const float spells = world.me().facts().ranged ? spell_output(...) : 0`). Marcella (slot 1: damage 2, unit, range 4), Ren (slot 0: 1.1 stun, unit) and Heart of Ruin's dash landing all deal spell damage from beyond a wolf's reach of 3. They are excluded from both `spell_clear_rounds` and `beyond_spare`'s `kites`. The rates are low (Marcella about 15 a round at base), so the main loss is the zero-health clear for a hurt melee champion.
     - The gate looks arbitrary rather than modelled. Let `spell_clear_rounds` decide; it already returns -1 when no spell reaches.
     - Severity: low. Effort: small, but it changes behaviour, so it needs an A/B.
   > Partly: CHANGES 201 applies a rule of this kind only to `kite()` on shared-gem maps (melee champions kite only if
   > their spells a turn out-damage their basic attacks): 59.2% of 120 on fresh shared-gem maps, unconfirmed. Farm's
   > ranged-only gate is untouched; generalising to siege and farm on every map is TODO 11 (no run). Marcella's
   > `kite()` unit stations: 50.3% (CHANGES 108).
5. **`breach` charges one round of fire too many** (camps.cc:129). Our first hit wakes the group, and the killing hit lands before that round's camp phase, so `turns` hits cost `turns - 1` rounds of fire (as `min_camp_damage` does with `damage -= left[0].fire`).
   - It also ignores other awake groups reaching `here`, the attack reset (`reset_and_attack_camp` runs right after), and spells.
   - Today's version is conservative. `(turns - 1)` is the exact form, plus the reset if `has_attack_reset`.

   Severity low; effort trivial (behaviour change).
6. **`stand_reach`'s stand tile is a heuristic** (camps.cc:236-260). It uses `range` tiles out from the member, away from the group's middle, clamped to the map, ignoring walls and other camps.
   - Exact version: for each member, take the minimum over `standable` tiles within `range` of the striker mask. Choose by fewest strikers with everyone alive, or better, by the mask's strength.
   - It is static and built once per group and range: at most ~49 tiles x n members x 32 strikers. Build it lazily per group, as now, never all groups on round 1.

   Severity medium (clear damage feeds every farm decision); effort medium.
7. **`camp_dealt_with` and `champion_dealt_with` duplicate world.cc's `emblems()`** (economy/camps.cc, model/world.cc).
   One family test (`has_family`, emblems.h) and a cached read of our own factors (re-read after a purchase) are
   shared now; the dealt-factor formulas are still written in both places. Severity low; effort small.
8. **The splash score reads stale health** (camps.cc:60). It counts neighbours with `health[j] > 0`, while the target's own health falls back to full when the belief says dead. After an unseen respawn, Varg's splash bonus reads 0. Use `live_health`-style logic on live tiles, e.g. `test(live, members[j].pos)`. Severity low; effort trivial.
9. **`min_camp_damage` assumes we stand at one tile per member** (camps.cc:191-202). It ignores rounds spent walking between stand tiles. For melee clearing a spread group that understates `rounds`, and the damage while walking under fire. This is a modelling gap, not an obvious fix. Severity low-medium; effort medium.

## capture ([report](audit-2026-10-28/capture.md))

1. **Prospector rounding disagrees between two places.** `prospected(cluster, n)` (capture.cc:28, used by `our_share`, farm.cc and shop.cc) takes 25% of the floor share only. `held_gold` (capture.cc:82, the Tavi decision) takes 25% of the share including the remainder. The rule ("25% of its share of the cluster members' rewards") does not settle whether the lowest id's remainder counts. A probe should settle it, then one formula should be used. Severity: low (a gem or gold or two). Effort: probe plus a one-line change.
   > Probed: the remainder counts (`probe-prospector-remainder`, 2026-10-28), so `held_gold` is right and `prospected`
   > undercounts for a lowest-id owner. The one-line fix is open.
2. **Gold-only groups are never contested.** `contesting` (capture.cc:356) and `contest_capture` (capture.cc:464) both require `gems != 0`. An enemy on a gold-cluster group, or an enemy Tavi with a Prospector emblem, captures it freely, even when we are standing next to it. Gold is the first tiebreak and buys shards. Whether to deny it is a judgement call, but a cheap contest of a group already in reach could be worth A/B testing. Severity: low to medium on Tavi-gold maps. Effort: small, then an A/B.
   > Partly: wider contests of enemy gem holds (750280ce, 4 versions, best 50.6%) were level or lost (EXPERIMENTS
   > "Contesting enemy capture holds"); gold-only groups untried.
3. **`enemy_hold_left` ignores an enemy's Capture emblem** (capture.cc:406). When the hold's count is not read, it falls back to `capture_rounds(false)` = 6. The world already stores `fast_capture` for enemies (world.cc:1716). When a visible enemy on the tiles has it, the bound should be 4, and the joining rule `min(R+6, J+3)` should apply. Usually the timer is read and this is exact, so the fallback matters only for unread holds. siege.cc:430 shares it. Severity: low. Effort: small.
4. **`free_hit` treats an `unknown` group as awake** (capture.cc:487). See above. This is a modelling gap: a holder can wake a possibly sleeping group, whose fire then contests our hold through damage or a retreat. Consider `c.fully_awake()` for consistency with farm.cc:306. Severity: low. Effort: one line plus an A/B.
5. **The time-left tests use map size as a stand-in for the walk to an altar.** `sole_capture_holder` (capture.cc:138, 152), `join_marcella_capture` and `take_capture_handoff` (capture.cc:304) use `width + height + endgame_margin`. `pathing.to_any_altar().at(p)` is already cached and is exact for our own position. The Marcella branch (138) also leaves out the tribute turns that the Prism branch (152) adds. Severity: low (only in the last ~150 rounds on big maps). Effort: small.
6. **`holders(G)` ignores the Tribute emblem** (capture.cc:48, `tribute_turns(..., false)`). A team whose holders own Tribute emblems could split big groups fewer ways. This is a heuristic choice and probably deliberate, so it is a note only. (capture, params)
   - params: **`holders` ignores the Tribute emblem** (capture.cc:60, `tribute_turns(..., false)`). A Tribute-emblem holder's shorter channel could allow fewer holders. Severity: low. Effort: small.
7. **The fix's bound could cover more.** `contesting` / `contest_capture` still contest gem holds whose gems the enemy cannot bank before round 2000: they pay late, or far from an altar. Only the gold tiebreak is at stake then. Severity: endgame only, low. Effort: medium, because it needs the enemy holder's walk to an altar.

## champions ([report](audit-2026-10-28/champions.md))

1. **`stun_reach` ignores a walk before a stun that does not exclude walking.**
   - **Where:** `champions.h` `stun_reach`; used by `World::ready_stun_reach` (`model/world.h:452`), `ally_stops` (`combat/fight.cc:442`) and `stoppable_winning_tribute` (`combat/fight.cc:420`).
   - **Rules:** no ability spends the walk, and only excludes-walking spells forbid a walk before them.
   - **Effect:** three champions can stun one tile farther in a single turn than `stun_reach` says:
     - Cassi: walk, then stun, reach 5 (not 4).
     - Heart of Ruin: walk, then dash 2, then the radius-1 landing, reach 4 (not 3).
     - Marcella: as a melee champion she can walk, attack, reset, then make the stunning attack, reach 2 (not 1).
   - **Consequences:**
     - `ally_stops` under-counts allies that can stop a winning enemy tribute, so the self champion may divert for a stop an ally would have made.
     - `stoppable_winning_tribute` misses an enemy one tile beyond the no-walk reach.
   - **Fix:** add `stun_reach_with_walk(slot) = stun_reach(slot) + (abilities[slot].excludes_walking ? 0 : 1)` for this-turn questions about a champion that can still move. This is general: Ryth, Prism, Tavi and Ren are all excludes-walking and get +0. Callers must also check `can_move` or stun state. The callers are outside this file, so I did not change them.
   - **Severity / effort:** low-medium, small effort; it changes behaviour, so it needs an A/B. (champions, fight)
   - fight: **`ally_stops` returns false for any enemy in a bush**, including the lock case, which needs no
     sight of the enemy, and Ryth's ground stun, which hits unseen enemies. Conservative (we stop it ourselves), so low severity.
     It also counts only an ally's current distance, not a walk before a non-excluding stun or a lock
     placement. Effort: small.
2. **Marcella's stun needs a prior attack.**
   - **Where:** `ready_stun_reach` (`model/world.h:452`) counts her reset slot whenever the cooldown is ready.
   - **Rules:** the reset fails while the attack is unspent, so she must first attack something in range, which can be the stun target itself, and must still have the reset this turn.
   - **Effect:** the model is right when the first attack hits the same target. When planning an ally Marcella's stop in `ally_stops`, though, it ignores whether her attack is already spent with the reset on cooldown. `World::read_stuns` handles this for self (`!my_can_attack()`), but the ally and enemy paths do not.
   - **Severity / effort:** low, small effort.
3. **`ChampionFacts::raw_output` misses two passives.** It is used by the draft and by fight sizing.
   - **Missing:**
     - Varg's splash: up to Strength again per extra enemy adjacent to the target.
     - Ren's retaliation: 0.2 x Focus per hit he *takes*, which is a function of incoming hits rather than output, so it may belong in a separate "punish" term.
   - **Also:** `draft.cc:143`'s `spells` counts only `AbilityKind::damage` and so drops Heart of Ruin's landing damage, which `raw_output` includes via `lands()`. That is harmless today because `spells` is gated on `ranged`, and Heart is melee.
   - **Severity / effort:** low, medium effort, needs an A/B.
4. **Ryth's passive is computed outside the table.**
   - **Where:** `economy/shop.cc:143-144` adds `ryth_health_strength_ratio * health growth` to Strength per health shard.
   - **Suggestion:** a `ChampionFacts::strength_per_health(float bonus_health)` helper next to the table would keep passive arithmetic in one place, beside `tribute_gold_per_gem`.
   - **Also:** `draft.cc` uses base stats only, so this does not affect the draft.
   - **Severity / effort:** cosmetic.
5. **Fuel gate on dashes in `economy/farm.cc:711`.**
   - **Where:** `static const int dash_kind = 150 * n_groups < full_field_cost_estimate() ? facts().dash_kind() : 0;`
   - **Effect:** on maps with many groups it drops dash-aware fields (`dash_walls` / `landing_dash_walls`) for every dashing champion (Vesper, Vendetta, Issac, Ren, Heart of Ruin). This is a fuel gate on a modelling choice. Making the dash field cheap, for example by caching per-group fields or building them incrementally across turns, would let it go.
   - **Severity / effort:** medium, medium effort; this is outside my file, so it belongs to the farm auditor.

## combat_priority ([report](audit-2026-10-28/combat_priority.md))

1. **Our own cooldown-1 slots count as not ready** (combat_priority.h:54, with the self cooldowns
   read at turn_order.cc:33-36). `priority_self` reads our cooldowns before our turn-end tick. A
   slot reading 1 will be 0 at our next turn, and the bot's own model agrees: `read_strike` uses
   `ready_round = round + cooldown`, ready when `cooldown <= 1`. So our `outgoing` undercounts
   abilities that come ready next turn. For enemies, the raw value read at our turn start is right
   for their next turn. Fix: compare `self.cooldowns[slot] > 1` for self only, by passing a
   threshold or adjusting `priority_self`. Severity low-medium (it shifts when we enter the danger
   band); effort trivial; needs an A/B.
2. **Role champions never bid for the bands** (turn_order.cc:392). Prism, Vesper, Ryth, Vendetta,
   Marcella and Heart of Ruin, which are exactly the usual draft, skip four checks:
   - `offer_kills`: an exact team kill check that acts before the enemy;
   - `offer_channel`: protects our ending recall or tribute;
   - `offer_escape`;
   - `offer_heal`.

   They rely only on this heuristic, which uses a single-champion kill ratio, start-of-turn enemy
   health and no allies. The bands look strictly more informed, so A/B enabling them for every
   champion. Severity possibly medium; effort trivial plus an A/B. (combat_priority, turn_order)
   - turn_order: **Teacher champions (Prism, Vesper, Ryth, Vendetta, Marcella, HoR) never bid** (:386). A teacher-champion Marcella or Vendetta at kill range of a low enemy is ranked only by `teacher_priority`'s danger buckets, which compare strike to health but with no "act before that enemy" condition. Consider letting every champion bid `kill` (and Prism `protect` for its tribute) on the shared scale; the band scale is already above every teacher value. Needs an A/B.
   > Tried: every champion bidding the kill band (kills and channel cancels; heal, escape and channel bids still
   > non-teacher only) as `b7-bands`: 49.3% of 1104, out-of-fuel turns +5%, dropped (EXPERIMENTS "Double turns from
   > turn order"). The heal, escape and channel bands for the teacher six are untried.
3. **Stale inputs**:
   - `outgoing` divides by the enemy's health and shield at our turn start (world.cc:1694), so
     damage we dealt this turn is not counted.
   - `stunned` is also from turn start, so an enemy we stunned this turn still counts as
     `incoming`.

   `live_enemies` in turn_order.cc already reads current health per enemy, so threading
   health and a fresh `stun_pending` into `live_start_enemies` would be cheap (one raw read per
   enemy). Severity low; effort small.
4. **We ignore our own pending stun.** `priority_self` never sets `self.stunned`. If we lose our
   next turn, `outgoing` should be 0. Low, since a stunned champion can still set its priority on
   the skipped turn.
5. **Missing damage modifiers.** The target's Durability (`taken` 0.9) is ignored, as are our
   Skirmish (+5% to champions) and Collectors bonuses (`ChampionBelief::dealt`). Camp damage is
   also missing: it lands in the camp phase before next round's champion turns, so
   `incoming / (self_hp - camp_damage)` would be closer. Low; small.
6. **Duplicates compute_strike** (safety.cc:758). `strike()` is compute_strike without stuns and
   at one distance. The two have to be kept in sync by hand: a new champion or a rules change
   must be made in both. Calling compute_strike costs more: it fills a 7-entry array per call
   (up to 12 calls per priority), but stays well under 1k per turn. Alternatively, make it a
   constexpr template over an `add(reach, damage, stuns)` sink and use it in both places. Low;
   small-medium effort, cross-file.
7. **Simplify the type enum** (combat_priority.h:11). `Type` mirrors `cambc::champion_type` and
   needs 13 static_asserts in turn_order.cc:41-53. `role()` could switch on
   `cambc::champion_type` directly, since champions.h already includes cambc.h. That would delete
   the enum and the asserts. Cosmetic; cross-file.
8. **A dead champion still holds a turn slot.** `World::slot` counts all allies, and
   `dead_priority` (13) puts a dead champion ahead of idle living allies. That pushes the living
   ones one alternation later, after another enemy turn. This may be intended (idle champions
   prefer to act late), but the effect should be stated or A/B'd: with it below idle, the living
   would act earlier. Severity unknown; trivial to test.

## comms ([report](audit-2026-10-28/comms.md))

1. **The priority payload (claim plus support intent) is lost whenever an ally's raw turn rank is 0.** `turn_order.cc:97` `packed_priority` returns 0 for raw 0, and `comms.cc` `payload_of` reads priority 0 as "no payload".
   - Raw 0 is a normal value. `idle_priority` is `role + 8 - 8*bucket`, so a champion with role 0 and 10-20% health missing, or role 8 and 20-30% missing, publishes no claim and no support intent.
   - For Willow/Prism pairs, `support_mailbox` then sees no payload and the intent lapses after two rounds.
   - Fix (turn_order.cc): encode raw 0 as `(7 - index) << 16 | payload`. Ordering looks preserved: rank_code(0) - rank_code(0) = 0 gives a rank of 7 - index, which is below raw 1's (rank_code(1) - rank_code(0)) * 8 + ... ≥ 8, and above every negative raw.
   - Check why raw 0 was pinned to 0 ("bots read a champion they have not seen as priority 0") before changing it. Turn order changes, so it needs an A/B.
   - Severity: medium. Effort: small. (comms, support_mailbox)
   - support_mailbox: **A raw turn rank of 0 erases the whole payload: the support intent and the claim**
     (turn_order.cc:97-98, `packed_priority`: `if (raw == 0) return 0;`). The idle priority is
     `role + 8 - 8*floor(10*(1 - hp/den))` (idle_priority.h). Prism has role 0, so with no gems, no
     danger bucket and no wish band, it gets raw 0 at 80-90% health. That is exactly when it might start
     asking for a heal, and its request and claim are then not sent: `payload_of` reads priority 0 as
     "none" (comms.cc:254). Willow (role -1) never hits 0 when idle. A `wish.priority()` with band 0 and
     value 0 also gives raw 0.
     Fix: let raw 0 pack to the payload alone, `return payload`. Values 0..65535 still sort between rank
     -1 (negative) and rank +1 (>= 65536), and `>> priority_payload_bits` still reads them as rank 0
     (turn_order.cc:194). The cost is that two raw-0 allies would tie-break on payload rather than id.
     Alternatively, keep `7 - index` in the rank for raw 0 and offset it so it stays non-zero.
     Severity: medium for the Prism/Willow pair and claims. Effort: small, plus an A/B.
   > Context: raw 0 was kept 0 on purpose in the comms packing (CHANGES 141; bundle 49.9% of 1104): "hecate played
   > differently until this held" (EXPERIMENTS "Comms packing"). Changing it is untried.
2. **A capture record can be overwritten before a teammate reads it when turn order changes.** `send()` treats only records that are fresh *to us* as protected (`camp_free`).
   - Say P posts in round r and teammate T acted before P in round r. If P (or someone who read it) acts before T in round r+1, the slot can be reused for another capture or a second sighting.
   - T then never learns of the capture, because `told_respawn` stops anyone re-posting it.
   - Claims and bags have reminders for this; captures don't.
   - Exact fix: keep a record you wrote, or read, in round r-1 protected in round r while some teammate's `prev_rank` was before the writer's and its `rank` is after ours. Cheaper alternative: let the poster re-post once in its next turn.
   - Severity: low-medium (only when priorities reorder). Effort: small.
3. **The second sighting slot disappears on large maps with big teams.** Examples: 100x100 with 5 enemies and ~60 groups needs 42 + 24 = 66 bits, which is over 64, so `L.second` is false.
   - Options:
     - Drop the second slot's own 3-bit write count. Its parity plus a rotated enemy usually changes the bits anyway.
     - Quantise health to quarters (2 bits).
     - Share one write count across both slots.
   - Each option saves 1-3 bits, which is enough for 100x100 with 5 enemies at moderate group counts.
   - Severity: low-medium (big ladder maps are where scouting matters most). Effort: small, but the layout is a wire format, so every instance must change together, which is automatic since all run the same bot.
4. **Sightings carry no channel state and no shield.**
   - `sight_value` posts health without the shield (Varg, Heart of Ruin), so receivers underestimate effective health.
   - No bit says the enemy is tributing or recalling, though a tributing enemy at an altar is the highest-value interrupt. On maps with spare bits, a 1-bit "channelling" flag would fit.
   - Severity: low-medium. Effort: small for the bit, more for the receivers to use it.
5. **A same-enemy sighting is never replaced within a round** (`send()` `replaces`: `index != e.index`). An enemy turn can fall between the teammate's turn and ours. If our position for that enemy differs, ours is strictly newer, but receivers date both "from the round's start" (`World::note_sighting`), and the first written wins.
   - Allow replacement when the position differs and our urgency is no worse. Related: the first-slot choice could skip an enemy already in this round's second slot when the positions match.
   - Severity: low. Effort: small.
6. **The mates cache is from the turn start.** `urgency()` builds `U.mates`, including `visible`, at `receive()`. After `send()`'s observe, we may see a mate we didn't before, so urgency stays slightly high (conservative). Low severity.
7. **`refresh` in `main.cc` is an existing fuel gate.** It reads `moved && fuel_ok(end_reserve)` and otherwise notes `comms-stale-vision`.
   - The observe is needed only to post sightings of enemies our move revealed.
   - A bounded alternative: read only the enemy champions' raw `in_sight` and `champion info` (~12-20 fuel each, ≤6 enemies) instead of a full `observe()`. That makes it cheap enough to drop the gate.
   - Severity: low. Effort: medium (World API).
8. **Bags are clamped at 127 fours (508 gems).** Receivers then underestimate an ally carrying more, for example after a monolith (200 gems) plus kills. This is rare, and one more bit fixes it where there's room. Low severity.

## crew_work ([report](audit-2026-10-28/crew_work.md))

1. **Exclusive spells cannot follow a walk, but the caller's reach assumes they can** (`farm.cc:548-551` together with this function). Severity: low; effort: small, in farm.cc.
   - The caller sets `reach` to the max of basic reach and every damage ability's `reach()`, e.g. 5 for Ryth/Prism/Stellar ground spells, 4 for unit spells. Every damage spell is `excludes_walking`, and a dash uses the turn's one cast. So a spell-reached arrival really happens on turn `earliest_work_delay(gap_spell) + 1`, not on the turn the last tile is closed.
   - The result is one turn optimistic whenever the spell, not the basic attack, sets the reach.
   - Exact fix: `min(f(d - basic_reach), f(d - spell_reach) + 1)`, with the `+1` only when `gap_spell > 0`. That is two calls instead of one.
2. **Ranged basic attacks cannot follow a walk** (rules `turn.ranged`). Severity: low; effort: small to medium.
   - Prism, Stellar and Cassi have no attack reset, so their walk-then-attack arrival is really `f(gap) + 1`.
   - Vesper, Tavi and Willow can walk, reset, then attack, but the reset is a cast, so it conflicts with a dash that turn. A ranged dasher (Vesper) can still dash without walking and then attack, closing `dash_steps` that turn rather than `1 + dash_steps`.
   - An exact model needs a "may damage after walking" flag per arrival option. The header's "no cast conflicts" caveat covers this today; it is the same one-turn over-credit as item 1.
3. **Code duplicated across bots.** The function is copied verbatim into hyperion, hermes, river, river_ac and the baselines. This needs no action for astraeus; it is noted only so that a fix to item 1 or 2 is not expected to propagate.

## draft ([report](audit-2026-10-28/draft.md))

1. **Later draft turns can never afford some ward sites** (`draft.cc:711`, severity low,
   effort small). The cost is `5000 + 2000 * ward_box area`, on top of the 40k `draft_reserve`:
   - A two-member group's box (e.g. 6x5 = 30) needs 105k.
   - An altar site's box (7x7 = 49) needs 143k.

   Both exceed a 100k draft turn. If the first (10M) turn does not finish the ward search, no later
   turn ever does: `analyse` returns at that site every turn, and the index section is never
   written. Today the first turn always finishes, so it is latent. Fix: estimate per candidate
   tile (or split a site's candidates across turns) so the bound is under the 60k a turn has free.
   That removes a stall rather than adding a gate.
2. **`type_facts`' heal walk is a Chebyshev guess where the exact steps are known**
   (`draft.cc:200`, severity low, behaviour change). It uses
   `dist(map.landing_tiles[0], group.centre)`, but `a.steps[g][0]` (the walk from our spawn) is
   already computed when `type_facts` runs. Farm's opening uses the Chebyshev distance from the
   spawn centre (`economy/farm.cc:658`), so the two already differ slightly. Either match farm
   exactly, or use the exact steps in both. It only changes lead ranking, so it needs an A/B.
3. Merged into "Spell kiting is ranged-only" (4) under camps.
4. **`best_ward`'s "own sight" is measured from the group centre** (`draft.cc:~475`). Champions
   working a group stand on its camp tiles, and for an altar, on a tribute tile rather than the
   altar. Scoring the union of sight from the camp tiles (or the likely stand tile) would rate
   wards against what the worker actually sees. Judgement call, draft-only fuel.
5. **Header docs** (`draft.h`, the section comment on `DraftPlan`) are accurate but dense. No
   error found; I checked each section's layout against the writers and readers.

## farm ([report](audit-2026-10-28/farm.md))

1. **`spell_clear`'s kite tile ignores other groups' reach** (farm.cc `spell_clear`, where `reach` is drawn only from `G`'s members). The goal tiles must be out of the chosen group's attacker reach, but a neighbouring awake group can still hit us there. `spell_clear_rounds` then values the clear as costing no health. Kites near camp clusters may stand under fire every turn without the farm valuation knowing.
   - Exact version: also draw the reach of awake, live strikers of groups near the goal set (`groups_near`), or at least drop goals in `Safety`'s camp threat.
   - Severity: medium on dense camp maps, only for ranged champions with damage spells (Prism, Stellar, Cassi, Tavi). Effort: small.
2. Merged into "Spell kiting is ranged-only" (4) under camps.
3. **A hop group's recall-out time is added to `steps`** (loop: `steps = walk + tp_crystal_time + inner + (centre_to_altar(g) == unreachable ? recall_turns : 0)`). That recall belongs to banking (after the capture), not the approach. Counted in `steps` it shrinks the respawn `wait` by up to `recall_turns`, and so admits groups that will still be respawning on arrival. It also inflates `help_steps`, `best_steps` and the search cap.
   - Fix: add it to `bank` / `cycle_bank` instead.
   - Severity: low (crystal-region maps only). Effort: small.
4. **`struggling` overstates an ally's danger** (`a.health - min_camp_damage(...)`). It ignores the ally's damage-taken emblems (Jungle, Durability), its self-shield (Varg, Heart of Ruin; `shielded_clear`) and any heals. We help more often than the ally needs, which is "one champion per camp otherwise" broken. The ally's emblems are known (`camp_dealt` is read for allies, so a `camp_taken` equivalent likely exists in `world.cc`).
   - Severity: low. Effort: small.
5. **Ren's partner clear ignores reflection.** The main loop's `min_camp_damage(world, g, strength + partner_output, &joint_rounds)` passes no `reflect`, and `beyond_spare`'s `shared` matches it. The joint clear is therefore overcosted for Ren, so a partnered group can be wrongly called risky. The prune and the main loop agree, so this is a modelling gap, not an inconsistency.
   - Severity: low. Effort: small, but `min_camp_damage`'s reflect path is single-clearer.
6. **The partial-evaluation fuel gate** (`room()`, `farm-partial-evaluation`, `fuel_ok(full_field_cost_estimate ...)` break, `farm-kept-target`, `crow-flies-farm`). Each group's value depends on facts kept across turns (`GroupFacts`, version-keyed) plus our position and `best_value`. The loop could resume where it stopped last turn, or re-weigh only groups whose belief or context changed, instead of restarting from `first`. That would make a full evaluation bounded across turns rather than gated within one.
   - Severity: medium (the bench shows about 0.8% of turns over 100k, some of them farm). Effort: large.
   > Partly: CHANGES 175 stops the loop exactly once no group left in the nearest order can beat the best (heavy-set
   > out-of-fuel turns 1579 -> 365), but not while banking; `farm-partial-evaluation` still fires 20k times on the
   > heavy set (TODO 1). The loop ungated with a limit of 12 estimates (`fuel/farm-ungate`): out-of-fuel turns 2193
   > vs 416 on 6 heavy maps, held (EXPERIMENTS Fuel, "Gate removals"). Resuming across turns is untried.
7. **`engaged`'s threat bound** uses `members.size() - 1 + reach`. `CampGroup::threat_radius()` is exact (and `ally_engaged` itself uses it). The two give the same result; whether the switch saves fuel depends on whether `threat_radius()` is already warm. Fuel only.

## fight ([report](audit-2026-10-28/fight.md))

1. **`game_ender` ignores a walking carrier whenever our bag wins** (fight.cc `game_ender`, the
   `if (win && !(tributing && ...)) continue;` line). The comment says "our winning bag outruns a
   walking carrier", but that is not computed. If an enemy with `need` gems stands one step from an
   altar and we are 30 steps from ours, it lands first. `intercept_steps` already computes `theirs`
   (walk to the nearest altar + channel), so compare `turn_start(e, round + theirs)` with `win_lands`, as
   the tributing case does. Severity: high when it happens (it decides the game), but rare. Effort:
   small.
2. **Ren (and any dasher whose other slot is an enemy cast) can spend its escape dash's cast on a
   stun while retreating** (`retreat`, the else-branch `cast_at_enemies(world, escape_step_value)`).
   Only Heart of Ruin gets `keep_dash`. For Ren (stun slot 0 + dash slot 1, one cast a turn), a stun worth more than
   `cast_cost + walk` (40 + 210) costs both the walk (excludes walking) and the dash. Generalise
   `keep_dash` to "has a dash and its other slot hits enemies", or count the dash's escape value
   in the threshold. Prism's `prism_retreat_walk` rule (a cast may take the escape walk only if it
   kills or stuns the sole threat) similarly applies to every walk-excluding caster (Ryth, Stellar,
   Tavi, Ren, Cassi, Marcella slot 1), not only Prism. Severity: medium for those champions. Effort:
   small to medium; needs an A/B.
3. **A ranged dasher one step outside attack range walks instead of dashing** (`chase`'s `> range + 1` gate, and the same in
   `stop_game_ender`). For Vesper (the only ranged dasher) a walk spends the attack, and with its reset on
   cooldown it gets no hit this turn, while a dash then attack would land one. Gate on
   `dist > range + (ranged && !reset_ready ? 0 : 1)`. It is a judgement call (it spends the escape
   dash), so I didn't change it. Severity: low to medium. Effort: small; A/B.
4. **`intercept_steps` treats "in attack range" as stopping a tribute or teleport** (`stop = steps`).
   Damage interrupts neither; only a kill (or a stun or lock) stops them. Reaching range does not mean the
   bag is taken by `last`. A rough exact check: `effective_hp(e) / our damage per turn` turns of
   hitting must fit too, or drop `steps` from `stop` for tributes and teleports, leaving stun and lock.
   Severity: medium in endgames (it chases tributes it can't stop instead of other work). Effort:
   small.
5. **`intercept_steps` is one turn pessimistic for free or walk-compatible stops.** `stop <= last - round`
   counts walking `stop` turns and then acting the turn after. A lock placement is free (same turn as
   the last step), as is a melee attack or a non-walk-excluding stun (Cassi, Marcella's reset). Use
   `stop - 1` for those. Severity: low (conservative). Effort: small.
6. **`game_ender` considers single bags only.** Two enemies tributing at once (or Cassi and Issac
   each tributing their own bag) whose bags together reach `need` are not flagged, though stopping
   either keeps them short. Severity: low (rare). Effort: medium (sum the in-flight tributes like
   `gems_short`).
7. **`prey`'s self-delay test is ranged-only** (`delayed` for `a.is_self`). A melee champion two or
   more steps out (no dash) can't hit this turn either, and a ranged one at range + 2 or more stays delayed
   even with a reset. `strike(self, world.round).hits(dist)` (as for allies) would cover every
   champion and ability uniformly, if `Strike` models the ranged walk/attack allowance (its header
   says it follows the rules' action allowances). Severity: low to medium (chase decisions).
   Effort: small; A/B.
8. **Fuel gate: `prey`'s `fuel_ok(fight_cost_estimate() + reserve)` cut (`prey-cut-short`).** When
   fuel is short it stops simulating candidates, so no chase. The `lost` memo already dedups equal
   fights, and with at most 6 enemies the loop is bounded. If `chase_trade` could be bounded per
   call (a cap on simulated turns), the gate could go. Effort: medium (lives in safety.cc).
   > Tried: CHANGES 176 narrowed `prey-cut-short` (its own floor for the fight key, lost fights skipped first) with the
   > step-guard gates: out-of-fuel turns +16%, reverted. TODO 2: cheaper fight sims are needed before the step-guard
   > and prey-cut-short gates can go (shield kits 44% of sim fuel, horizon-length fights 37%).
9. Merged into "`stun_reach` ignores a walk before a stun that does not exclude walking" (1) under champions.
10. **`sure_kill` ignores our shield against Ren's retaliation** (`retaliation * taken >= health`),
   while `attack_target` uses health plus `my_live_shield`. Conservative: Varg and Heart of Ruin with
   a shield up skip a sure kill on a low Ren. Add the shield to `OurHit::health` (one `shield_value` read
   when `shield_slot >= 0`). Severity: low. Effort: tiny.
11. **`intercept_steps` uses `pair_gems` for a walking Cassi/Issac's channel length**, but each body
   tributes its own bag (`b = ceil(gems/10)` per body). It overestimates their channel, so we think
   we can intercept later than we can. Severity: low. Effort: tiny (use `e.gems`, or the max of the
   two bodies' channels).

## guard ([report](audit-2026-10-28/guard.md))

1. **Fuel gates in `step_guard` drop the whole guard** (guard.cc:331 `step-guard-entry`, 434 `step-guard-look`; 395 `step-guard-sim` keeps a partial guard). When fuel is short we step with no guard at all, into tiles that hand the enemy the first strike.
   - Make it bounded instead: the bound-pass tiles (`exposed[0..bounded)`, or `step_guard_cover`'s board) are a cheap superset with no Reach and no fight. Two ways:
     - Return them as the guard when a later stage can't be afforded, which is conservative rather than permissive.
     - Better, cap the work: at most one union fight plus one fight a tile, sorted as now, under a fixed budget, which would let the entry gate go.
   - Severity medium (it bites in exactly the crowded fights where the guard matters). Effort small to medium.
   > Tried: CHANGES 176 narrowed the step-guard gates (entry gate after the bounding pass, every gated return decaying
   > the estimate): out-of-fuel turns +16%, reverted but for the tags. The step guard folded into the strike search:
   > no gain in three runs, and the guard hit its fuel gate twice as often (EXPERIMENTS). The step guard on `stand_of`
   > with limits instead of gates (`fuel/guard-fold`): out-of-fuel turns 861 -> 2931, held (EXPERIMENTS Fuel, "Gate
   > removals"). Returning the bound-pass tiles as the guard is untried; TODO 2 says cheaper fight sims come first.
2. **The pack zone ignores teleports** (guard.cc:86). A teleporting enemy's box is drawn around `e.pos`, not `tp_dest`. It is the same class of bug as the fix, but changing it would alter retreat behaviour, so it is left for a deliberate change. Low severity, small effort.
3. **`pack_radius` is uniform (max_reach + 1 = 7) for every member** (guard.cc:30-35, 107-114). A walking melee enemy with no dash strikes at 2, yet its box is 15 wide. The box could use each member's `threat_strike(world, e).reach + 1` (or `fight_reach`) and be exact per champion. That would shrink zones against Ryth, Marcella and Varg and keep them for Vesper and dashers. Medium severity (it over-retreats against melee packs); small effort. Behaviour-changing, so it needs an A/B.
4. **`no_worse` compares enemy exposure only** (guard.cc:281). A step that keeps the same enemies and damage but leaves an ally's `fight_ally_radius` is treated as safe as our tile, yet its fight has fewer allies. One fix is to also require `fighting_allies(q) ⊇ fighting_allies(here)`, or to drop the shortcut whenever `here_mask != 0`. Low severity (one or two steps rarely change the ally set); small effort, but `fighting_allies` is in Safety.
5. **A walk then a dash can end 3 from `here`** (guard.cc:483-486). The deferred guard is centred on the tile it was worked out from, with radius `dash_range`; a dash after a walk can land up to 3 from that tile, outside the guarded square. `bot.cc:309` re-guards after the plan search moves us. I couldn't verify that every other walk-then-dash flow (farm, bank, chase) re-guards. Worth checking in pathing/plan. Low severity.
6. **Heart of Ruin's dash landing is not modelled.** It deals 1.5 Focus damage and stuns enemies within 1 of the landing tile. A guarded tile next to an enemy may be the best landing because that enemy loses its next turn. The guard prices that tile as if the enemy still acts. Plan/abilities may already value the landing, but the guard can veto it. Medium severity for HoR only; medium effort.
7. **Pack-zone self health mixes times.** It is frozen at the first query (`pz.health`) but adds the live `a.shield` (guard.cc:91), and `hurt` ignores the shield (line 79). Varg/HoR shields cast this turn count toward `ours` but not toward `hurt`. Probably intended; noting it. Low. (guard, params)
   - params: **Shields don't count in health thresholds.** `hurt_health_fraction` is checked against raw health (fight.cc:194, fight.cc:270, guard.cc:79 `pz.health`, capture.cc:139). A Varg (2.5 x Focus shield) or Heart of Ruin with a shield up reads as hurt and retreats or skips chases it could take. The check could use health plus live shield, as `finishing_camp` already does (camps.cc:517, `my_health_and_shield`). Severity: low. Effort: small, but changes behaviour, so it needs an A/B.

## idle_priority ([report](audit-2026-10-28/idle_priority.md))

1. **Gems are a yes/no flag, but what a camp kill costs depends on the gem count**
   (`idle_priority.h:16`, `gems > 0`). Severity low-medium, effort medium.
   - A champion killed by a camp loses all its carried gems (`combat.camp_kill`). One gem and 80
     gems get the same halving.
   - The real question in a camp tie is whether the hit kills. That depends on absolute
     `health + shield` against the strength of the monsters in range (with jungle/durability
     emblems), not on the health fraction.
   - An exact version would rank allies by the cost of absorbing a tie hit:
     `life + gem_value * gems` if it kills, else roughly zero.
   - This is behaviour-changing and needs an A/B.
   > Partly: river's camp-hit dodge (rank ourselves lowest when a tie hit would take us below the recall line and an
   > ally stays above 35%) fired 0-3 times a game, too rare to measure (EXPERIMENTS, river 2026-10-27).
2. **`role()` gives -1 to every non-teacher champion** (`combat_priority.h:27-37`): stellar,
   cassi, issac, willow, ren, varg and tavi. Within a health tenth, these act last, so they never
   take a tie hit before a teacher champion. That is backwards for the natural camp tanks. Severity
   low, effort small, needs an A/B.
   - Ren reflects 0.2x Focus to monsters that hit it.
   - Varg's shield soaks hits.
   - Willow and the Cassi pair are fragile, so -1 suits them.
3. **The priority is set a round late.** It takes effect from the next round (`rounds.team_order`),
   so the idle ordering protects against camp ties one round late. When a champion's health
   or gems change mid-turn (a capture payout, a hit), the next round's camp phase still uses this
   priority, which is fine because `set_turn_order` runs at the end of the turn. Only a stale case
   remains: the turn-order fuel shortcut (`turn_order.cc:379-389`) keeps the old rank. That is an
   existing fuel gate, but the idle computation itself is ~tens of instructions. The expensive
   part is the band logic and `priority_self`'s host reads, not this file. No action here. (idle_priority, turn_order)
   - turn_order: **Fuel-short path keeps last turn's rank** (:425-429, a fuel gate, severity low, effort trivial). When `fuel < end_reserve` we keep the previous turn's rank, possibly a stale kill or protect bid. Yet the same branch already computes `plain_priority` when no rank exists, so it is affordable. Always taking `plain_priority` (one `priority_self` plus a few teacher strikes, a few thousand fuel at most) would remove the gate. The bids themselves are what is expensive (threats, refresh). Needs an A/B: it changes behaviour only on short turns.
   > Tried: removing the turn-order gate (bb414db): out-of-fuel turns +13%, held (EXPERIMENTS Fuel, "Gate removals").
4. **Wider question.** The idle ordering only matters for camp tie hits and for who reaches
   contested tiles or captures first. If (1) and (2) are fixed, consider dropping the
   health-fraction buckets entirely in favour of the exact "who should absorb a tie hit" ranking.
   Effort medium, needs an A/B.

## main ([report](audit-2026-10-28/main.md))

1. **A ward placed this turn never refreshes comms vision** (`main.cc:266-270`, `bot.cc:217`). `refresh` (and so `world.observe()` in `comms::send`) is triggered only by `moved`. A ward placed this turn adds up to 13x13 of vision that `send` never reads, so a sighting the new ward makes isn't posted until next turn. Fix: also refresh when `cambc::self().ward_cooldown()` shows a placement this round (or `Memory` records one). Severity low to medium, effort small.
2. **While dead, the queue warms around the death tile** (`main.cc:221`). A dead belief keeps its last `pos` (`world.cc:1581` doesn't reset it), so 60 dead turns warm a radius-20 ring around where we died. The next walk starts from spawn. Warming around `spawn()`, then along the walk to `memory.farm_group`, is probably more useful. This changes fuel only (and therefore real-budget play), so it needs an A/B. Severity low, effort small.
3. **The queue's budget scaling ignores start-up** (`main.cc:147-149`). The comment says it "fills the same at any budget", but on the first turn the real budget has already paid start-up before `start` is read, and the 100M run hasn't. So bench/100M runs warm slightly more on turn 1 than the ladder does. This matters only if bench results are meant to mirror the ladder exactly. One fix is to read `start` at the top of `main()` for the first turn. Severity low.
4. **Arena capacity is unmeasured.** It would help to add a `debug_block` that prints `arena_used` at round 2000 on a 100x100 map with a long game. If the arena ever fills, fix the `(n | 1)` waste from "Considered" and maybe size the arena from that measurement. Effort small.
5. **A resumed out-of-fuel turn inside the queue** (`main.cc` `TurnEndQueue::run`). If the queue ever overran (its estimates were wrong), the resumed round would keep warming, down to `floor`, from the new round's fresh 100k before the real turn runs. Only `prepare_next_turn` is followed by an `is_stale()` check; `around()`, `warm_up` and `warm_centres` aren't. A cheap `world.is_stale()` test inside `room()` (one host call per tile) would bound this. Severity low (it needs a misestimate first), effort trivial.
6. **`print_fuel_log` is skipped on every early return** in `play_turn`, so debug fuel samples pile up and print under a later turn. This is debug-only. An RAII guard would fix it. Severity cosmetic.
7. **`comms::send`'s `moved` vs `sight_pos_`**: these are equivalent today, because `observe()` updates `me().pos`. If that ever changes, `moved` should compare against World's `sight_pos_` (it is private now). There's nothing to do now.

## map_economy ([report](audit-2026-10-28/map_economy.md))

S1. **Monoliths inflate the supply denominators** (map_economy.h:48-51). Severity medium, effort small, needs an A/B. A reachable monolith adds 200 gems / (150+6) ≈ 1.28 to `gems` per round. That is more than three 3-gem-cluster groups (21/56 ≈ 0.375 each). Yet with 20000 HP and 200 Strength, that supply is rarely realised. `damaging_gems` already leaves monoliths out. As written, one monolith can flip `cluster_gem_map`/`stellar_map`/`prospector_map` to false. Try skipping `has_monolith` groups in `gems`/`gold` as well.

S2. **The weight ignores clear time** (map_economy.h:47). Severity medium, effort medium. A capture cycle is clear time + 6 + respawn. A cluster (120 HP) dies in a turn or two, while a golem group (5000 HP) or an elk group takes tens of turns. The weight `1/(respawn+6)` therefore overrates monster supply against cluster supply, which biases `prospector_map`/`stellar_map` towards false. Possible fix: add `group.health / k` for a nominal team damage k (draft.cc already estimates clear times for picks).

S4. **`total_gems` counts unreachable groups and monoliths** (map_economy.h:34, used at draft.cc:1029). Severity low-medium, effort trivial, judgement call. The draft picks the gold-only roster (`gold_three`) only when `total_gems == 0`. A single monolith, or gems we cannot reach, switches it to `mixed_three`. Reachable non-monolith gems may be the intended test.

S5. **`mixed_gems` is neither weighted nor gated by `ours`** (map_economy.h:54). Severity low. One enemy-favoured mixed group sets it, while every other stellar_map input is a weighted ratio. That is probably fine on symmetric maps, since the mirror group exists too. Note it if `stellar_map` misfires.

S6. **Groups exactly between the spawns count fully for both teams** (`own <= enemy`, map_economy.h:45). Severity low. For `tavi_map`'s pure-gold groups this counts contested central gold as ours. Weighting ties at 0.5 is an option.

S8. **The caches ignore their argument** (map_economy.h:62, 68, 83). Severity none. `map_economy(map)` and the two `static` lambdas cache the first call's input. That is correct for one map per instance, but the signatures suggest otherwise. A comment or a parameterless accessor on `StaticMap` would make it explicit.

The thresholds (`12` steps, `120` gold, the `2x` and `4x` ratios) are tuned constants. Revisit them only through an A/B.

## map_features ([report](audit-2026-10-28/map_features.md))

1. **The `crystals = false` fuel gate** (map_features.h:33-36, draft.cc `choose`). On maps whose
   spawns only a dash or crystal joins, the bot throws (~3.9k) and falls back to the table draft.
   The README puts two level-2 travels at ~8.6M on a 72x72 archipelago. The fix above makes level 2
   slightly dearer (more seeds). It could be made cheap and exact. The fallback needs only `fA`/`fB`
   up to `S` (front, altars) plus S itself, so the Dial loop could stop once `S` is settled, with
   the remaining tiles counted only for altars. Or skip crystal targets with `d[j] <= v + 9` via a
   precomputed 7x7 "any far tile" bit. No ladder map needs it, and it only matters if
   competition-style maps ever disconnect spawns on foot. Severity low, effort medium.
2. **Parity coverage**: the level-2 bug passed native parity because no corpus map exercises a
   crystal origin with all-walkable neighbours. `replays/audit-mf/fz.mjs` + `fz.cc` (scratch,
   gitignored) is a 30-line fuzz of `travel` against `Grid.travel`. A similar fuzz in
   `tools/draftlab/` (random grids through `native_main.cc` plus a travel-only mode) would cover the
   paths real maps don't. Severity low, effort small.
3. **Detour's `cheby` is a JS quirk the model was fitted on** (map_features.cc:430-431, generate.mjs
   metrics). It measures from A's spawn corner `(sx, sy)` to its mirror (B's *opposite* corner) and
   subtracts `sw` on both axes, even when the gap runs along y (where `sh` is the relevant size). So
   it overstates the true spawn-to-spawn Chebyshev gap by `sw - 1` (or by a mix of `sw`/`sh`). It is
   consistent across maps, so it is harmless to the model as fit, but if metrics ever changes,
   compute `max(|gapx|, |gapy|)` between the two spawn rectangles and refit. Severity low.
4. **Perspective and opponent picks** (no change, judgement): all features are from absolute team 0's
   side. That is fine: the symmetry makes A's and B's values equal except for sideGroups' tile-index
   tie-break on equidistant groups, which assigns those groups to one side by tile index rather
   than by who reaches them. The draft could also use what the rules give it: earlier rounds' enemy
   picks are visible (`draft.visibility`). The deployed model drops counter terms (fit at ~1e-4), so
   that is a lab question, not a code one.

## params ([report](audit-2026-10-28/params.md))

1. **attack_target's kill worth ignores the bag** (combat/self_abilities.cc:224). `worth` scores a kill as `s.health + life_value`, with no `gem_value * pair_gems`. Everywhere else (abilities.cc:91 `hit_worth`, plan.cc, turn_order.cc:265) a kill includes the bag. So reset-and-attack and Varg splash target choice will not prefer finishing a gem carrier over an empty-handed body of similar health. Chip damage also uses raw `useful_damage` rather than the `kill_distance` curve that the rest of the combat valuation uses. Fix: add the bag (cheap; `pair_gems` needs the belief, which `Seen` would have to carry), or use `kill_distance`. Severity: low to medium. Effort: small.
2. **`track_horizon` is a fixed 10 rounds** (world.cc:1949; capture.cc:137,155). "Could be anywhere" really depends on map size and on how fast the champion moves (dash champions grow `possible` faster). On a 100x100 map, 10 rounds of walking covers a 21x21 square, nowhere near the whole map. An exact test: stop tracking once `possible` covers the reachable map, or bound the work per belief rather than by rounds. Severity: low to medium (vision and pressure judgments go blind early on big maps). Effort: medium.
   > Tried: forgetting unseen enemies after 5 rounds instead of 10: 49.2% (EXPERIMENTS, river comparisons). In river,
   > a tracker without the horizon (`possible` grows forever, weights still from `tracked_recently`) played identical
   > games but cost +10% fuel a turn, ~20 points at 100k (EXPERIMENTS, river leave-one-out E).
3. **One `recall_health_fraction` for every champion** (fight.cc:182, farm.cc:273, support.cc:146/415, shop.cc:197/213, draft.cc:145). Heart of Ruin deals up to +50% damage at low health and has a self-shield, so its best recall line is lower. Glass bodies (Prism 700, Stellar 650, Cassi 600) are at 0.35 x 700 = 245, which an Elk plus a ranged champion's spell can take in two rounds. A per-champion line, or one in effective hit counts (health against the strongest credible hit), would fit every draft. Severity: medium (judgement-heavy, needs A/B). Effort: medium.
   > Partly: river's "safe recall line" (10% instead of 35% when no enemy can reach within the recall's turns + 1,
   > dashers 2 more tiles): 52.1% at 100k, 47.1% unlimited, neutral (EXPERIMENTS, river 2026-10-27). A per-champion
   > line is untried.
4. Merged into "Pack-zone self health mixes times" (7) under guard.
5. **`siege_ready` uses the team's max health** (siege.cc:105-109). A half-dead team commits to a Monolith as readily as a fresh one. Unseen allies' current health is unknown (personal vision), but the last-seen health, or one's own current health for self, is available. Severity: low. Effort: small.
6. **`kite` measures with a straight-line distance** (siege.cc:430). `steps = dist(here, centre)` is a Chebyshev distance, compared against `wait` with `kite_early`. Elsewhere (`siege_candidate`, farm) path steps are used, so behind walls it sets out too early or picks the wrong group. Severity: low. Effort: small (`map.ally_steps` or a pathing field). (params, siege)
   - siege: **`kite` target choice** (`siege.cc` ~442-466). Simplification or gap, low-medium severity,
     small effort.
     - The cost is Chebyshev distance to the centre, not walking steps, so a group across a lake
       looks near.
     - A cleared group that then fails `capture_taken` or is beyond `2 * vision_radius` ends the
       whole kite (`return false`), when the next-best live big group could have been kited.
     - Fix: apply those cleared-group conditions inside the selection loop.
7. Merged into "`holders(G)` ignores the Tribute emblem" (6) under capture.
8. **The gold-farmer test is written twice**, differently: draft.cc:148 (Cassi by type, `team_size() == 3`) and farm.cc:297 (`linked_pair && !melee`, `economy_three`). A shared `gold_farmer(type, map)` helper would stop them drifting. Severity: low. Effort: small.

## pathing ([report](audit-2026-10-28/pathing.md))

S1. **make_way backs off from allies that will never move** (pathing.cc:662-700). Medium severity, small effort.
If our only way is through an adjacent ally and we carry fewer gems (or the same number and a lower
champion_type), we step to the free neighbour farthest from that ally. Nothing checks that the ally is
trying to pass us. Some allies never move: one channelling (tribute at an altar, recall), one holding a
capture tile, one parked in a corridor. Against them we back off, replan next turn, walk back and back
off again. The ally is adjacent and so visible, and its state is readable: when it is channelling or
cannot move, or still stands where it stood last turn, don't back off and treat its tile as a wall.
Also, only adjacent allies are considered. With an ally two tiles down a 1-wide corridor the route
ends exhausted and make_way does nothing.

S2. **Unguarded wide re-search in step_towards(Field)** (pathing.cc:752). Medium severity (fuel), trivial effort.
After a failed capped search (`here + 16`), it may run a second search capped at `here + 96`, with no
fuel check at all. On a 100x100 map that costs about 4000 + 169 x (here + 116) fuel, e.g. ~45k at
here=150, on top of the first search. Both searches matter for correctness, so bound the work rather
than gating it. Either reuse the first search's result (route_exhausted_ already short-circuits a dry
search), or make the first search the wide one when the kept route is unusable, so only one search runs.

S3. **The static-descend fuel gate fires before the kept route is consulted** (pathing.cc:745). Low-medium, small effort.
`step_towards(Field)` skips step_towards when `search_cost_estimate(here + 16) + end_reserve` isn't
available. But route() usually reuses `kept_route_` and runs no search at all (kept_steps). Move the
check into route(), just before `compute_to_with_expansion_count`. The gate would then trip only when a
search has to run, and the descend fallback stays for that case. This narrows an existing gate rather
than adding one.

S4. **Teleport targets skip dead members of live groups** (pathing.cc:820). Low, needs a probe.
`teleport_targets` re-admits camp tiles only for groups that are not `alive`. A member killed in a
group with other members still alive leaves an empty tile. The rules say "not a live camp", and also
"A dead camp's tile (its group cleared or respawning) is a valid target", which reads as group-level
but is ambiguous. `sdk_has_camp` already tells a seen empty tile apart. If a probe shows such tiles are
legal targets, drop the group-state test for seen tiles.
> Probed: legal; the champion lands on the dead member's tile while its group reads alive
> (`probe-teleport-dead-member`, 2026-10-28). The fix is open.

S5. **approach_steps treats an unreachable centre field as walk_cap** (pathing.cc:184). Low, small effort.
A centre field is stored only when complete (a capped field is returned only if whole). So `at(me) ==
unreachable` means no static walk leads from us to the centre. For range 0 (capture), every camp tile
connects cardinally to the centre over tiles walkable on static terrain. The approach search must
therefore fail, and we can return null without running a walk_cap-layer search. For range > 0 (ranged
attacks across holes) the search can still succeed, so the shortcut is exact only for range 0.

S6. **prepare_approach underbudgets for unfarmed groups** (pathing.cc:209). Low.
The added cost covers the centre field. For a group that is not farmed (a Monolith or no reward),
`approach_steps(.., true)` may build `from_ally_spawn()` instead, a full field, and its cost is not
counted.

S7. **Attack tiles exclude other cleared groups' camp tiles** (pathing.cc:328). Low.
`attack_tiles` intersects with `standable`, which drops every camp tile on the map and re-adds only this
group's dead members. A tile of a neighbouring cleared or respawning group is a legal place to stand and
attack from. Excluding live_camps() (camps believed alive) instead of camp_tiles would be exact. It
costs work on each call, so cache it keyed by live_flips().

S8. **Attack tiles ignore our ward** (pathing.cc:301). Low, design.
`member_attack_tiles` requires sight from the attacker's own tile. The rules let a ward's vision count
for attacks, so if our ward sees the member, every open tile within range is an attack tile. This
matters most for camps in bushes. It doesn't fit the cache. Instead, each turn the ward sees the member,
add `square(member, range) & open`.
   > Partly: the strike search already treats a target our own ward sees as attackable from any tile in range
   > (`Search::ward_sees`): 49.9%, kept (CHANGES 108). `attack_tiles` is unchanged.

S9. **Routes don't treat believed-alive unseen camps as walls** (pathing.cc:426). Low.
`occupied_into` uses `camps_into`, which holds only visible camps. A camp on a bush tile stays unseen
until we enter its cluster, so a route through it bumps: one wasted try and a fresh search each round.
OR-ing `live_camps() & ~vision` into the walls would be exact under our beliefs. It is cheap (two board
ops) but changes routes.
> Context: no ladder, gen or gen-s1 map has a camp on a bush; CHANGES 108's bush-camp pass in Reach (51.1%) never
> fires, and its +9% out-of-fuel turns were noise (TODO intro).

S10. **Inside danger the whole connected danger region is freed** (pathing.cc:512). Design question.
While we stand in danger the route ignores danger entirely, so it may walk deeper in towards the goal.
Alternatives: route to the nearest safe tile first when the path to the goal stays in danger, or free
only the tiles within one step of the region's edge. A judgement call, not a bug.

S11. **step_closer's aim is redundant at its callers** (farm.cc:476, siege.cc:572). Trivial.
Both pass the target as the aim. The aim only breaks ties, on Manhattan distance to the same target,
so it does no harm.

## plan ([report](audit-2026-10-28/plan.md))

1. Merged into "`hit_worth` exists twice" (5) under abilities.
2. **Stun counted on kills** (low-medium, small, cross-file). See above. A stunning cast that kills
   scores `stun_worth` on top of the kill. So the search may spend Ryth's, Prism's or Tavi's cast
   (or Marcella's reset arm) on a kill a basic attack already makes, instead of keeping the cast
   for a shield, a heal or the next turn. The fix is to add the stun only when the blow does not
   kill, here and in abilities.cc, and to decide whether a kill on a tributing enemy should then
   get the tribute part separately.
3. **Walk-alone leaf only for Prism and Stellar** (medium, needs an A/B). `plan_strikes` (:1729)
   offers "walk, nothing else" as a priced leaf only for ranged champions without a reset, a dash
   or a non-exclusive hit spell. For Cassi, Vesper, Tavi and Willow the walk node is grown but is
   `owed`, so it is never settled. Their "attack here" option is then weighed against "do nothing
   here plus `step`", both priced at the start tile's danger, never against a walk to a safer tile.
   Offering the terminal walk leaf for every ranged champion that can walk (`!melee && can_walk &&
   moves && !walked_first`) would make this consistent.
4. **Landings use a hard ban where attacks and spells price the wake** (medium, medium effort).
   `land_bad` (:432, :1212) refuses any HoR landing that touches a sleeping striker, even when it
   also hits a foe. Basic attacks and ground casts instead go through `wake()`, which prices who the
   woken camp hits. The landing also stuns the camp members within 1, which then skip their next
   attack, and neither path models that. Routing landings through `wake_at` would make HoR's
   choices consistent with the other champions'. The cost/on_us for stunned members should drop
   their first hit.
5. Merged into "Varg's splash wakes other non-Monolith groups too" (1) under camps.
6. **`wake()` bans any group with a sleeping Monolith outright** (:1403), even when the Monolith's
   reach covers no champion. This is a judgement call (a woken Monolith is dangerous for 2+ phases),
   but it could be priced like the other strikers, with a ban only when we or an ally would be in
   its reach.
7. **Fuel.** There are no fuel gates in these files. `max_nodes`, `max_exact_queries` and
   `max_sets` are fixed bounds. `read_spells` still makes one `my_damage_to` host call per foe per
   ready slot. If `raw * x.taken` with the shield arithmetic (already the catch fallback) matches
   the engine exactly, which I have not checked, those calls could go. That is worth looking at
   only if read time shows up in `SRCH` traces.

## safety ([report](audit-2026-10-28/safety.md))

1. **The two-turn widening misses dash-first plans, so Strike is not an upper bound** (`safety.cc` `threat_strike`, about line 905; `Reach::build_ways` turn loop). High severity, moderate effort.
   - **What it models:** `widened[d] = max(s2.at(d-1), s.at(d) + (d <= basic+walk ? s : 0))`. On the first of two turns the enemy only walks one step, or adds a second basic only within plain basic reach.
   - **What it misses:** a dash on turn 1, then a strike on turn 2 from the landing.
   - **Vendetta** (70 Strength, reset and dash both ready), at d = 3 to 4: turn 1 walk + dash + attack, turn 2 reset + 2 attacks gives 3s (210). The model gives s (70) at d = 4 and 2s at d = 3.
   - **Vesper** at d = 5: dash + attack, then reset + 2 attacks gives 3s. The model gives s.
   - **Who it hits:** every dash champion (Vesper, Vendetta, Ren, Issac, Heart of Ruin), whenever the enemy has two turns before ours, which is common.
   - **Reach** has the same gap (turn-2 ways start only from walked sets), so the REACH-BOUND debug check stays silent.
   - **Fix:** for d in the dash band, add the second turn's best from within basic reach of the target. Exactly: max over turn-1 moves (walk, or dash + walk) of turn-1 damage plus `s2` without the dash slot at the remaining distance.
   - `most_damage` (`k.at(0) + hs`) happens to still bound it.
   - Any fix changes threat levels everywhere, so it needs an A/B.
   > Partly: the enemy's two-turn chain in `threat_strike` (both slots across two turns, slots readied for turn 2) lost
   > as w2-chain: 47.1%, ladder 52.9, out-of-fuel turns +20% (EXPERIMENTS; TODO Candidates); its narrowed form (one
   > cast across both turns) shipped as CHANGES 95, 50.1%. Dash-first turn-1 moves specifically are untried.
2. **Camps we wake this turn are not seen after `refresh()`** (`Safety::refresh`, `find_members`). Medium severity, small to medium effort.
   - `find_members` walks `world.each_stirring()`, which is alive and not asleep as of `observe()`.
   - When we hit or stun a member of an asleep group, rules `camps.wake` wake the whole group. `refresh()` only checks deaths and stuns, so `camp_damage`, `camp_area` and `lethal` keep treating the group as asleep for the rest of our turn (guard steps after attacking, melee walk after attack).
   - **Fix:** World (or the attack path) records the groups we damaged this turn, and `refresh()` treats them as stirring and re-runs `find_members`.
   - The fix lives in World and the attack code, not here.
   > Tried: re-reading state after our own hits (camps we wake among it) lost: 47.3%, a lean version 49.3%, both with
   > more out-of-fuel turns (EXPERIMENTS `p1a-state`; TODO Bugs 1, retry narrowed to the reads that change a decision).
3. **`find_members` lets champions who have not acted shield us at their current tiles** (`safety.cc` about lines 1750-1755). Medium severity, small effort.
   - A member's reach toward us is cut to `d - first(o)` by any visible champion nearer the monster.
   - Champions yet to act this round (`!acted`) can walk or dash away before the next camp phase, leaving us the nearest.
   - **Sound version:** count `o` only if it has acted, or use `d + its move` (1, or 3 with a ready dash) for unacted ones.
   - This under-states camp danger next to allies or enemies.
4. **Heart of Ruin's passive is frozen in fights** (`make_fighter`: `strength = c.strength * c.scale`). Low to medium severity, small effort.
   - The Trade sim keeps its Strength and Focus at their starting scale. In reality it grows to +50% as it loses health, so fights against or with Heart of Ruin understate its late damage.
   - **Fix:** a per-fighter `missing_bonus`, applied in `act()` when `max_health > 0`. It is off the plain path anyway, because Heart of Ruin's shield makes its kit not plain.
   > Tried, bundled: batch 2's P5 (Heart of Ruin's scaling in Trade) lost together with P3a/P3b/P4, ladder -8 points,
   > out-of-fuel turns +40%, not split (EXPERIMENTS "Assumption audit, batches 1-2"; TODO Candidates: bench P5 first,
   > on branch `audit/batch2`). TODO 2 also lists HoR's passive at event turns (HoR sims already run out of fuel).
5. **Existing fuel gate in `trade()`.** Low severity, medium effort.
   - With `fuel_floor = end_reserve`, `simulate` returns {-1, -1} and the fight reads as lost and as our fall ("fight-cut").
   - The sim is already bounded (`fight_horizon`, quiet-turn fast paths). A hard cap on the work per fight (half-turns times fighters) would let us drop the floor rather than choose worse.
6. **Turn-scoped static caches in `fighting_allies()` and `Reach::build` go stale** (they are keyed on `world.round`). Low severity, small effort.
   - After `see_again()` (we moved and see new allies), allies who just came into sight are not in fights or Reach blockers until next round.
   - **Fix:** key them on a World observe counter instead.
7. **`engagement_near()` measures the enemy strike from `e.pos`** (`safety.cc` about line 882). Low severity, small effort.
   - For a teleporting enemy the strike applies from `tp_dest`.
   - It is left alone because our own reach to it is correctly from `e.pos`. The fix would split the two distances.
8. **Unseen weight is heuristic** (`unseen_weight`, `unseen_radius`). Low severity, medium effort.
   - **Ignores map edges:** `(2r+1)^2 / tiles` counts window tiles off the map.
   - **Approximate radius:** `unseen_radius` approximates where the true chance `count_within(possible, p, reach) / tiles` crosses `credible_weight`.
   - **Exact alternative:** `field.compute` already gives distances. One `count_within` at the radius boundary tiles, or a box-sum over a `possible` prefix table, would place the cut exactly, at a cost comparable to the field.
9. **Varg's splash and the fights.** Low severity, a modelling note.
   - Trade focuses all damage on the weakest member, so Varg's splash onto a second adjacent body (rules `varg.passive`) and our own splash are ignored.
   - With items, these are the main things the sim leaves out, along with positioning.

## self_abilities ([report](audit-2026-10-28/self_abilities.md))

1. Merged into "`access_fire` sums every awake member in reach of the tile" (4) under bank.
2. **`shield_wanted` and `shield_if_needed` disagree (Varg).** Location: `self_abilities.cc` ~line 181 vs ~line 545. Medium severity, small effort (needs a `Safety&` in `reset_and_attack_enemy`, a cross-file signature change).
   - `reset_and_attack_enemy` holds the reset when `shield_wanted` sees any visible enemy within `threat_strike(...).reach`. That's coarse: no Reach pathing, no teleport destination, no camps.
   - `shield_if_needed` uses `safety.blow(e, here).hits` plus camps.
   - When `shield_wanted` says yes and the later `shield_if_needed` says no, Varg ends the turn with neither the reset nor the shield.
   - Fix: pass `Safety&` and use the same test in both.
3. Merged into "Varg's splash wakes other non-Monolith groups too" (1) under camps.
4. **`dash_to_attack` can dash to a target it then won't attack.** Location: ~line 386. Low to medium severity, small effort.
   - When no target is given, it picks finishable enemies without `attack_target`'s retaliation filter. If the pick is Ren and its retaliation would kill us, `attack_target` refuses afterwards. The dash is spent and leaves us next to the enemy.
   - Add `e.retaliation() * world.me().taken < my_health_and_shield(world)` to the filter.
   - It also ignores an enemy's `shield` in the "chase" fraction (`e.health / e.max_health`). That's a minor point.
5. **`danger` weighs every camp as 2.** Location: ~line 77. Medium severity, medium effort.
   - A wolf (20 Strength) counts the same as a monolith (200), and the same as an enemy two tiles inside its reach.
   - A damage-based score would be exact rather than a heuristic: monster Strength x `camp_hit_factor()`, and `threat_strike(...).at(d)` for enemies.
   - Stunned camps (`camp_stunned`) skip their next attack and could be dropped.
6. **The travel-dash pause is a throttle shared across goals.** Location: `dash_towards(goals)` ~line 345, `failed_search_pause`. Low to medium severity, small effort.
   - A failed search blocks every travel dash, for any goal, for 4 rounds. `farm.cc` calls this with two different goal sets (cleared group tiles, attack tiles), so a failure on one suppresses the other.
   - The search is bounded (about 1.5k + (20 + layers) per 8x8 chunk, capped by `max_steps`). Removing the pause, or keying it on the goal group, should be affordable; measure with the fuel bench and an A/B.
   - It isn't conditional on fuel, but it chooses worse to save fuel.
7. **Killing a linked pair is undervalued.** Location: `attack_target`'s `worth` (~line 235). Low severity, trivial effort.
   - A kill returns `s.health + life_value`, but killing Cassi or Issac kills both bodies (and hands over both bags). Adding the visible partner's health, when it is known, would rank a pair kill correctly.
8. **No shield on spawn.** Location: `shield_if_needed` ~line 550. Low severity; a judgement call.
   - Healing on spawn happens at our turn end, and enemies can attack into the spawn. A burst bigger than full health between our turns, from several enemies or a stun chain, would still be absorbed by a shield cast on spawn.
   - Worth an A/B only if spawn deaths show up in replays.
9. **The `ready()`-first pattern costs fuel.** See the fuel note under **Changed**. Callers that run every turn without a cheap facts check first (`shield_wanted`, and other files' `ready` equivalents) may be worth the same early exit. Fuel-only; check with the bench.

## shop ([report](audit-2026-10-28/shop.md))

1. **Greed, Skirmish and Collectors are never bought.** `shop.cc:345-370` (best_stat) and the passive loop in `or_passive` never offer them; best_emblem only finishes one that is already begun, which never happens.
   - Greed: 25 shards with the stats of 35, against Power's 30 for 25 (five emblems of 6).
   - Skirmish: +5% to champions.
   - Collectors: +1% to camps and champions per family; with 3-4 families it is close to Monster's camp bonus, and it applies to champions too.
   - Greed cannot simply be added as a candidate, because candidates are compared by `saved` alone, which only works when every one costs 150. Greed costs 750 and pays its bonus only at 25 shards, so it needs a per-gold comparison or a multi-emblem horizon.
   - Skirmish and Collectors' champion side needs a fight-value term; the upkeep model is camp-only.
   - Severity: medium for long games. Effort: medium.
   > Tried: Collectors (3+ families) and Greed as candidates (p2w2-sinks): 51.8%, level, out-of-fuel turns +6%, Greed
   > never bought, Collectors ~0.34 a champion-game in place of Bruiser; dropped. Skirmish as a forced first emblem
   > (emb-td-skirm): 46.6%, the worst first emblem, with no fight term (EXPERIMENTS "Phase 2" emblem tables). TODO
   > Candidates: retry only with a fight term.
2. **main_stat ignores Focus-scaled heals and shields, and the landing term is inconsistent.** `shop.cc:31-43`.
   - Willow's heal (3x Focus) is her main job, but she has no damage spell, so main_stat gives Strength.
   - Varg's (2.5x) and Heart of Ruin's (1.5x) shields scale with Focus and are uncounted.
   - Heart of Ruin's landing damage (`lands()`) counts in the measured `cast` but not in the `spells` prior (line 41 sets `cast = spells`), so its prior is lower than its measured rate.
   - Severity: medium for Willow, low otherwise. Effort: low (add heal and shield multipliers, weighted by casts, and add landings to `spells`).
3. **affordable_prefix's single-entry cache thrashes.** `shop.cc:499-543`. Calls with `gold_in > 0` (capture.cc:378, Prism capture recall) and with `gold_in = 0` (wants_shop) have different `budget / shard_price` keys. When both happen near each other, each call reruns the full best_emblem chain, about 5-25 best_emblem calls. A two-entry cache, or keying `gold_in = 0` separately, removes that. Severity: fuel only, low-medium. Effort: low.
   > Context: not fuel-only as it stands. The cache keys on gold, stats and main stat but not on items, upkeep or
   > income, so a second entry would return values the current code recomputes (2026-10-28).
4. **Prism never takes a shopping trip from where walking can't reach spawn, unlike everyone else.** `shop.cc:618` returns false when `back == unreachable`. The non-Prism arm (line 626) skips the comparison and shops, relying on the per-turn recall that continue_recall keeps (bank.cc:743). A Prism in a crystal pocket with gold never goes home to shop. Severity: low. Effort: low, but it changes behaviour, so it needs an A/B.
5. **The shop trip's `hurt` comes from the altar field.** wants_shop's non-Prism arm uses `home_trip(...).hurt` (`shop.cc:544-556`). That says whether the first step from the recall landing towards an altar stays on spawn, but after shopping we walk back out towards `here`, not an altar. Prism uses `hurt = 1` whenever hurt. The exact test is the same check against `to_ally_spawn`-reversed distances, or a field to `here`. Severity: low (one turn of cost error). Effort: low-medium.
6. **emblem_begun and best_emblem's begun logic are two lists that must agree.** `shop.cc:104-116` against `shop.cc:331-343`, `384-401`. emblem_begun accepts any stat of Jungle, Power, Durability and Bruiser; best_emblem finishes only some of them (for example Durability only in Health, Power in Health only for Prism). They agree today only because best_emblem never starts the others. A single `begun_emblem(world, owned) -> optional<{family, stat}>` used by both would remove the drift risk. Severity: low. Effort: low-medium.
7. **The lock is bought from leftover gold, which can push the next shard back.** `bot.cc:224-226` calls buy_lock after buy_shards. With 35 gold the lock leaves 25, one short of a shard. Whether a lock beats a shard sooner is a judgement call that isn't priced anywhere. Severity: low. Effort: medium (price the lock).
8. **Ryth's Health shards are under-priced.** best_stat (`shop.cc:345`) offers Power only in the main stat, which is Strength or Focus. For Ryth (health_strength) a Health shard gives 100 HP plus 1 Strength, and add_shards already models that, but only Bruiser and Durability Health are candidates, never Power Health. Severity: low. Effort: trivial (add `value(power, health_stat)` when `f.passive == Passive::health_strength`), then A/B.
9. **Retaliation kill gold can be misattributed.** note_income_start (`shop.cc:572`) assumes gold gained between turns is a capture payout. Ren's retaliation can kill during an enemy turn: its 100 gold is then counted as capture gold if we stood on a group, and dropped otherwise. Severity: very low. Effort: low.
10. **Tavi's sell-on-spawn passive (full refund) is unmodelled.** Tavi could re-spec begun shards when its main stat flips. Severity: low. Effort: medium.

## siege ([report](audit-2026-10-28/siege.md))

1. Merged into "Ground spells reach 5, not 4" (3) under camps.
2. Merged into "`access_fire` sums every awake member in reach of the tile" (4) under bank.
3. **`exposure` counts groups that cannot attack within the horizon** (`siege.cc` ~391-399).
   Modelling gap, low-medium severity, small effort.
   - Respawning groups are counted. Only `alive && health <= 0` members are skipped.
   - The rules say a group returns *asleep* and attacks only once damage or a stun wakes it.
     Neighbouring asleep groups (h != g) are counted as attacking too.
   - Our action here only damages g. The only way they wake within 2 phases is if someone else
     hits them.
   - Skipping respawning groups and `member_asleep(i)` members of h != g would stop the step
     search refusing productive tiles next to sleeping camps. This is a judgement call (another
     champion could wake them), so I didn't make the change.
4. **`kite_productive_action` gives up near any harmless member** (`siege.cc` ~312). Modelling gap,
   medium severity on stampede-like maps, medium effort.
   - A live gem or gold cluster within 5 of us returns false, because its range-5 viewer tiles
     were not prepared. Big groups usually contain clusters, so the interior and step decision is
     often skipped exactly where it would act.
   - Fix: prepare the clusters' viewers in `kite`'s `prepare_member` loop (they are static and
     cached), or use the cluster's `attack_range` tiles, which are cheaper. Then target clusters
     with basic attacks in `damage`.
5. **Unit-spell melee kite from unit stations whatever `kites_with_spells` says** (`siege.cc` 489).
   Inconsistency, low severity, trivial effort.
   - `unit_stations = !ground_stations && unit_range > 0` skips `kites_with_spells`. Marcella
     (2x60/8 = 15 a turn against 45x1.125 = 50.6 for her basic attacks) and Ren therefore stand
     at unit-spell stations, out of reach of wolves only, while shop.cc buys them Strength
     because `kites_with_spells` is false.
   - Either gate `unit_stations` on `kites_with_spells` too (they then stand guard like other
     non-casters), or document why unit casts are worth it for them.
   > Context: CHANGES 201 (59.2% of 120 on fresh shared-gem maps, unconfirmed) left Marcella her unit stations while
   > dropping her forced Focus; Marcella's unit stations themselves were 50.3% (CHANGES 108). Non-kiters standing
   > guard outside the group (ba53bab): 49.5%, the guards idled and gold fell (EXPERIMENTS, shared-gem maps).
6. Merged into "`kite` measures with a straight-line distance" (6) under params.
7. **The reset model misses an attack spent earlier in the turn** (`siege.cc` 374). Exactness,
   very low severity, trivial effort.
   - The reset is modelled only if the simulated basic attack hit, or a ranged walk spent the
     attack. If the attack was already spent at turn 0 (`!can_attack`), the reset is legal too.
     The exact condition is `attacked || !attack`.
   - Only Ryth, with enough Focus to pass `kites_with_spells`, has a reset slot and ground
     stations, so this almost never fires.
8. **Siege staging counts only visible allies** (`siege.cc` ~168-180). Modelling gap, low
   severity, medium effort.
   - Allies at the far side of a Monolith's stage ring (radius 7) can be out of sight, so the team
     waits out `siege_max_wait` though it has gathered.
   - Fix: use comms claims or the last-seen positions of allies whose claim is g.
9. **`siege_ready` and `low` use our own `camp_hit_factor()` for the whole team** (`siege.cc` 109,
   196). Approximation, low severity. Allies' Jungle and Durability are known from their items
   (beliefs track `camp_dealt`); a per-ally taken factor would make the pool check exact.
10. **Fuel gates.** These are existing gates, not new ones.
    - `siege`'s `tiles` (prepare with `end_reserve`): on short fuel it notes `siege-no-tiles` and
      falls back to a square around the strongest member.
    - `kite`'s `prepare_member` loop: one failed prepare drops *all* stations, and the bot reverts
      to guard squares.
    - Both build static, per-group, per-range boards. Warming them for the current claim during
      spare turns (pathing's `warm_up`) would make the fallback almost never fire. A partial
      fallback in `kite`, which keeps the stations already prepared, would also degrade less.

## support ([report](audit-2026-10-28/support.md))

1. **Prism's formation window points the wrong way at bushes.** support.cc:429, `formation_view = attack_viewers(world, mate->pos, ...)`. Severity medium on bush maps; effort small to medium. Needs a probe first.
   - `attack_viewers(t)` returns the tiles from which *we* would see `t`. For a recovery, the question is whether *Willow* at `mate->pos` sees Prism. Sight is symmetric except at bushes ("a bush tile cannot be seen from outside"), and there it fails both ways:
     - Willow is off a bush and Prism is on an adjacent bush tile. That tile is in `near` (`sight(t, false)` is the full 3x3 for a non-bush `t`), so Prism counts it as in view, but Willow can't see it. Prism can spend up to `support_turns` turns waiting for a heal that can't come.
     - Willow is in a bush. `attack_viewers` gives only her cluster's near tiles, so Prism gives up a recovery that Willow, who sees out, could heal.
   - Willow's own ward (`sdk_wards` lists owners) isn't counted either.
   - Fix: for the Prism side, test candidates against Willow's sight. When `mate->pos` is off bushes, one host call does it: `map.walls_and_bushes.shadow_cast(mate->pos, range)`, tested per candidate tile. In a bush, use `StaticMap::viewers`-style cluster casting, or that same cast as a conservative subset.
   - Caveat: the rules YAML doesn't say whether an ally-target ability needs the ally in vision. The code assumes it does (`heal_viewers`, `heal_ally` reads only live visible allies). A probe should confirm before anything relies on it.
   > Probed: the heal needs the ally in Willow's own sight; unseen in range is refused (`probe-willow-heal-vision`,
   > 2026-10-28). The code's assumption holds, so the fix stands. Untested: an ally seen only through Willow's ward.
2. **`immediate_camp_finish` and `forgone` count camps Willow won't hit.** support.cc:276 and :311. Severity low; effort small.
   - Both count any visible member, or any live camp tile, in attack range. That includes asleep monster groups and awake non-work groups, which the stationary attack (`attack_support_camp`) never targets.
   - An asleep, damaged wolf in range (camps never regenerate) therefore blocks the independent heal step, or raises its bar, for nothing.
   - Restrict both to `strength <= 0` groups, plus the work group when awake, matching the attack predicate.
3. **`formation_turns` survives a lost mate.** support.cc. Severity low; effort trivial, but it is a design call.
   - When the mate goes out of sight, only `formation_start` is reset, so a later formation can expire early. The `support_turns` comment now says Willow's count carries on; resetting both instead is untested.
4. Merged into "`access_fire` sums every awake member in reach of the tile" (4) under bank.
5. **`heal_station` and the formation loop skip cleared camp tiles for Willow only** (support.cc:232, :475). Prism may step onto one, which turns into `holding_capture` and so ends the support next turn. If the skip exists to avoid accidental captures or respawn blocks, it probably applies to Prism's recovery steps too. Check the intent. Low.
6. **`local_support` is ~200 lines for two roles.** Most branches are `if (prism)` / `if (willow)`. Splitting it into `prism_recovery` and `willow_formation`, sharing the candidate loop as a helper, would make it much easier to read. Medium effort; it must stay byte-identical, so bench with `map_model_draft = false` as above. The current test drafts never pair Prism with Willow.
7. **Bench coverage.** The audit bench (`--test-draft` on 00ambush, 00lanes, 01hooks, 00interlock) never exercises the Prism-Willow pair. The model drafts on those maps don't pair them either. Any future change to this file needs a `map_model_draft = false` copy, or a test composition with both.

## support_mailbox ([report](audit-2026-10-28/support_mailbox.md))

1. Merged into "The priority payload (claim plus support intent) is lost whenever an ally's raw turn rank is 0" (1) under comms.
2. **Round-tag aliasing after 4+ skipped sender turns** (support_mailbox.h:15, :53). The tag is
   `round & 3`. A sender that skipped publishing (`world.is_stale()`, bot.cc:481) for exactly 4-5
   rounds reads as age 0-1, so an old positive is taken as fresh. Bits 11-15 of the 16-bit payload are
   free, so the tag could be `round & 31` (mask 31 in `encode` and the age). Severity: low (needs long
   fuel outages). Effort: trivial, but it changes priorities, so A/B it.
3. **The first message after a gap or a revival is discarded** (support_mailbox.h:46-50). The payload
   carries its own round, so it doesn't need `continuous` to be dated. Only `sent`/`positive` need
   clearing. Reading the payload even on reset rounds (when both are alive now) would cut a round of
   latency after our own missed turn. After a revival this mostly doesn't matter: the sender's
   pre-revival payload was published with `both_alive = false`, so it was negative anyway. Severity:
   low. Effort: trivial; changes behaviour.
4. **Modelling gap: the mailbox links exactly one healer to one protected mate** (comms.cc:236-250).
   Willow can heal any ally, but any other ally's need is visible only through Willow's own reading of
   its health, with no request. If more mates benefit, a per-ally "wants heal" bit could go in each
   ally's payload, since every ally already publishes one. Severity: unknown; needs an experiment.
   Effort: medium.
5. **Freshness window**: `valid` accepts a positive for 2 rounds after it was sent
   (support_mailbox.h:63), even if the sender has since withdrawn it out of sight. That is inherent to
   vision-gated reads and is the right trade-off; noted only for completeness.

## turn_order ([report](audit-2026-10-28/turn_order.md))

1. **`offer_escape` bids even when it cannot save us** (turn_order.cc:346-361, severity medium, effort small). It bids `protect` if *total* damage (camps, plus unacted enemies doubled, plus everyone's next-round blow) reaches our health. Camp damage and unacted enemies' this-round turns land before our next turn whatever the order, so the bid only helps if that unavoidable part alone does **not** kill us. Splitting the sum (unavoidable < hp <= total) would stop doomed champions outranking allies' useful bids (another ally's kill, Willow's heal). `may_escape` (:324) would need the same split.
2. **`offer_channel` bids for threats that ordering cannot deny** (:295-310, severity low-medium, effort small). Any threat from `threats_at` triggers the bid. An enemy that has not acted this round gets a turn before our channel completes whatever our rank. So if every threat comes from such an enemy whose one-turn strike already reaches us, the bid is wasted. `offer_escape`'s `turns_before_ours` logic is the model to reuse. Separately, our own recall and teleport add `15 x gems` to the value, while the enemy-side recall and teleport cancels in `offer_kills` (:279-282) don't. A recall cancel doesn't cost gems, so one side is inconsistent.
3. **`side_damage` misses allies yet to act this round** (:248-255, severity low-medium, effort small). An ally acting after us this round strikes the enemy before the enemy's next-round turn whatever the order. Only allies' next-round turns (ranked before `their`) are counted, so kill bids are under-offered in team fights. The caveat is that the enemy (if unacted) also moves in between.
4. **`offer_heal` ignores the ally's shield, Durability, turn order and the second blows from unacted enemies** (:364-379, severity low, effort small). It compares raw summed strikes with `ally.health`. `ally.shield` (Varg/HoR) and `ally.taken` exist on the belief and should enter (`damage * taken >= health + shield`). It also never checks `can_act_before` against the enemies concerned, unlike `offer_kills`.
5. Merged into "The priority is set a round late" (3) under idle_priority.
6. **Enemies on their spawn are never kill targets** (:263, severity low). Rules let us attack into the enemy spawn. A champion standing there has healed to full at its turn end, but a big burst (e.g., Stellar/Prism spell plus basic, or allies) can still kill it from outside. This is a judgement call, but `test(enemy_spawn, ...)` could become a check that some tile from which we can hit it is reachable.
7. Merged into "Role champions never bid for the bands" (2) under combat_priority.

## util ([report](audit-2026-10-28/util.md))

1. **The capped `make_field` boundary** (`util.h`). `layers >= max_layers` also rejects a field whose deepest step is exactly `max_layers - 1`, which is complete. That costs one wasted recompute at twice the cap. Using `layers > max_layers` would only be safe if the engine reports a cut-short search as `max_layers + 1` layers. That needs a probe. Low severity.
2. **Combined buff read in self_abilities.** `buff_state(c)` (util.h) reads the shield and a pending stun in one host call, and plan.cc's foe read uses it. `combat/self_abilities.cc`'s `attack_target` still reads `stun_pending` and `shield_value` separately; its shield read waits on finding the enemy's belief in a loop, so merging the two needs a small restructure. Small saving, small effort.
3. **`round_now()` and `checked_round()` are two raw reads of the same import** (`util.h:230-241`). The only difference is that `round_now` swallows a failure as round 0, which makes `throw_if_stale` throw. One function would do, and `checked_round`'s name hides that it is also just the round. Cosmetic, cross-file rename.
4. **Modelling check, no issue found.** `my_stunned` treats any listed stun buff at turn start as taking this turn. That matches `rounds.turn_start`: buffs that reached 0 expire before the turn runs. Marcella (stun-immune) never has the buff, and a champion on its respawn turn has no `can_*` bits but no stun buff either, so neither is misread. `stun_pending` (`duration > 0`) and `camp_stunned` (`timer > 0`) also agree with `abilities.stun` and probe-campstun.

## world ([report](audit-2026-10-28/world.md))

1. **Camp wake inferred from a health drop is not exact** (world.cc `update_camp` `read_members`, `now - health_round[i] < camp_sleep_time`). If the member was asleep at `health_round`, any drop since means it woke at or after that round. The phase after waking counts as occupied, so it is surely awake through `health_round + 2`: the exact test is `<=`. If the member was already awake, damage does not keep it awake (camps.sleep), so even a 1-round gap can end asleep, and "awake" is wrong. Branch on `member_asleep(i)` from before the read. This only matters when no striker's own state is readable, such as a member killed while the strikers are out of view. Severity low-medium, effort small.
2. **Unseen awake groups go "unknown" late** (`update_camps` and `update_camp`, `round - c.state_round > camp_sleep_time`). A group seen awake may already have had 1 unoccupied phase, so it can sleep 1 round after it was last seen. The current rule keeps "awake" for 3 rounds. This is a judgement call (avoiding a camp vs farming it), but it could be exact if we kept the round each member was last seen with a champion in its range. Low-medium.
3. **The respawn window assumes the previous full update was last round** (`update_champion`, `respawn_earliest = round - 1 + respawn_time`). After a turn lost to fuel, the death could be earlier. Use the previous `updated_round_`. Only the belief dump reads `respawn_earliest` and `respawn_latest`, so either use them (for example, to predict when an enemy returns) or drop them. Low.
   > Context: `tools/replay/audit_beliefs.py` reads the two fields from the belief dump (`respawn_window_wrong`), so
   > dropping them breaks that audit; the window fix is still open.
4. **Simultaneous enemy tributes** (`update_scores`): with 2 or more candidates whose channel ended, no bag is emptied unless one unseen bag equals the whole delta. If the candidates' bags sum to the delta, empty them all. Low.
5. **An unseen enemy's shield never expires** (`read_shield` runs only while visible). Most readers check `visible`, but `combat_priority.h` adds `enemy.shield` directly. Either age it by `shield_turns` or zero it when the enemy leaves sight. Low.
6. **Fuel trap worth recording:** moving the `make_*foot` bodies into a shared helper cost about 32 fuel a turn for no visible reason (inlining around `foot()` and its callers). Small "pure" refactors near hot accessors need the bench.
7. **`CampGroup::strength` and `threat()` are whole-group sums and unions.** Callers that treat `strength` as "damage to us" overcount when only some members reach us. Worth checking in camp-safety callers (outside this file).

## Review of the audit fixes (2026-10-28)

- **Damage taken on our spawn (bot.cc `play_turn`).** `memory.health` stores our health before the spawn's turn-end
  heal, so a hit taken on spawn before our next turn reads as damage only where it exceeds what the heal restored.
  The audit's fix (record max health when ending on spawn) was dropped: `memory.damage` is read as a lasting drain,
  and the heal undoes spawn hits every turn. With it, `tribute_safe` (bank.cc:95) and the keep-channel test
  (bank.cc:710) would refuse or cancel tributes, and the altar branch (bank.cc:783) would retreat, at altars beside our
  spawn under pokes that cannot kill us; `note_upkeep` would price spawn hits as costing a trip home. Direction: keep
  "under fire" (spawn hits count) apart from the survival rate and upkeep (spawn hits don't, unless one round's hits
  could kill), then decide per consumer.
  > Tried: in the 11-fix bundle (EXPERIMENTS "Audit fixes", 49.7% of 1164), never alone; the bench's games never took
  > damage on spawn.
