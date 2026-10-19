# hecate simplification candidates

A review of `bots/hecate/src` (2026-10-18, hecate as of version 20) for code to reuse, simplify, fix or remove.
Four parallel reviews covered `bot.cpp` 1-1512, `bot.cpp` 1513-end with `bot.h`/`params.h`, `world`/`comms`/`turn_order`/`main`/`draft`, and `safety`/`pathing`/`abilities`/`self_abilities`/`champions`/`util.h`.
Nothing here has been played yet. Each item comes from reading the code and grepping every use.
Items marked **[checked]** were re-read and confirmed in the merge pass.
Line numbers are as of commit e32257b.

How to test each bucket:
- **1. Behaviour-preserving:** `tools/fuel/bench.py compare` must show 16/16 byte-identical replays at the 100M budget. No games are needed. Items marked *fuel-only* change only what happens when fuel is short.
- **2. Bug fixes:** A/B each fix against `bots/baselines/` on all maps (ladder + gen + central, both sides).
- **3. Simplification/robustness:** A/B each change. For fuel gates, first count `SHORTCUT` tags with `py tools/fuel/bench.py run hecate --fuel 0`. A gate that never or rarely fires can go with little risk.
- **4. Feature removal:** A/B each removal. Keep it removed if the result is level within noise (±2.5 points on 390 games), since that is the point of removing it.

---

## 1. Behaviour-preserving

### 1.1 Dead code (~170 lines) [checked]
These are never called or never read:
- **safety:** `Safety::threat(int)`, `expected_damage`, `duel`, `should_retreat`.
- **pathing:**
  - `to_group`, plus its `group_slot`/`group_fields_`.
  - `nearest`/`Nearest`, which carries a static 80 KB `std::array<vec2,10000>`.
  - `step_towards(vec2, avoid)` and `teleport_targets`.
  - The `max_detour` parameter of `step_towards(const Field&, ...)`: no caller passes it.
- **champions.h:** `has_heal`, `has_shield`, `has_stun`, `has_ground_aoe`, `stun_reach`.
- **util.h:** `tile_at` and `and_into`.
- **world:**
  - `Altar::mirror`, `CampGroup::mirror` and both `StaticMap::mirror()` overloads, with their build loops.
  - `StaticMap::walkable`.
  - `Altar::lock_tiles`/`lock_`, with its warm-up loop, which only spends fuel.
  - `BushCluster::size`, `ChampionBelief::gems_round` and `last_cast_round`.
  - `DraftPlan::draft_round` and `reserved`.
- **Self `fast_recall`** (bot.cpp:1058, 1243): it is only ever set for enemies (world.cpp:919), so `fast_recall ? home_recall_time : recall_time` is always `recall_time`.
- **Teleport states** (bot.cpp:126, 2514): hecate never buys a teleport crystal, so these checks never fire.
- **Unused include:** `#include <optional>` in bot.h.
- **Small dead branches:**
  - `spell_clear_rounds` tests `spells <= 0` twice.
  - `belief.state != cleared` is re-tested inside the same guard (bot.cpp:1412, 1415).
  - `if (!basic)` (bot.cpp:1107) is always true.
  - In `collect_local_reward`, the `worked_round == world.round` test (bot.cpp:919) can never be true.
  - The siege `member` loop (bot.cpp:2258) only runs when the group has one member, so it always finds 0.
  - The `siege_group() = -1` reset at bot.cpp:2201 repeats the one in `play_turn`.
  - The kite contested branch `if (tiles.is_set(here)) return true;` (bot.cpp:2356) is unreachable, because the P branch in `decide` returns first.

### 1.2 `Threat::credible()` is always true [checked]
- `unseen_weight` returns either 0 or a weight of at least `credible_weight`, `build()` skips weight 0, and visible threats have weight 1.
- So every `credible()` test can be deleted: safety.cpp:612, 652, 686; bot.cpp:49, 1786, 2088; turn_order.cpp:169, 186.

### 1.3 Restructure `decide()` (bot.cpp:2503-2677, 175 lines)
- **Extract the stages:** `continue_tribute`, `continue_recall`, `retreat`, `hold_capture` and `carry_bag`. `decide` then reads as a ~40-line ladder.
- **Fix the decision-code comment** at bot.cpp:31: it is missing `X` (contest).
- **Recall branch (2544-2563):** all five reasons to keep a recall need `!safety.threatened(here)`. Test it once, then list the reasons. *Fuel-only.*
- **Recall check (2543):** `contains(submitting_gems) ? is_recalling() : contains(recalling)` is always `contains(recalling)`.
- **Bag branch:** when `safe` is true, `may_chain()` returns false only through `can_tribute_here`. Write it as `if (safe) { banking = true; bank_gems(); return; }` and drop that clause from `may_chain`, its only caller.

### 1.4 Shared helpers inside bot.cpp (~60 lines)
- **`allies_on(world, g, below_index = -1)`:** "allies standing on group g" is written four times: `holding_capture`, `step_onto_cleared`, the `ally_holding` lambda (its `lower_only` is always false) and `capture_share`. `sharers()` in `capture_recall` is a fifth copy.
- **Contest logic, three copies** (`contesting`, `kite` and `contest_capture`):
  - `enemy_contests(world, g)` for "the enemy holds it or a visible enemy stands on it".
  - `payout_round(c)` = `held_since + capture_time + 1`, also used in `paying_soon` and `capture_recall`.
  - `free_tiles(G)` for camp tiles with no visible champion on them.
- **`heal_rounds(world, pathing, g, damage)`:** the heal-trip formula is written twice (bot.cpp:1055-1058 and 1299-1307).
- **Approach range of g,** written three times: `farm_evaluation_reserve`, `walk_range` and `prepare_walk`.
- **Copied verbatim** between `siege` and `kite`: `allies_ahead(world, G, here)` and `ally_claims(world, g)`.
- **Other repeated computations:**
  - `stun_reach(self, round)`, in `tribute_to_stun_later` and `can_stop_winning_tribute`.
  - `spawn_route_saving(...)`, in `recall_to_bank` and `capture_recall`.
  - `under_awake_camp(world, p)`, in `finishing_camp` and `wants_shop`.
  - "May shop" (`!remote_shop && rounds_left > endgame_shop_rounds`), in `capture_recall` and `wants_shop`.
  - "Gems left per alive ally", in `gold_worth` and `emblem_gain_rounds`.
- **`bank_gems`:** merge its two tails (dash → submit → break lock → step → submit) under one `const Field&`.
- **Simplify:**
  - `holders()` can be `big_group(G) ? big_holders : 1`.
  - `siege_strongest` can fold into `siege_load`.
  - In the kite tail (bot.cpp:2422), test `first.is_set(here)` once.

### 1.5 Shared helpers across files
- **Valuation constants into params.h.** Kill worth 300 is defined three times: `kill_bonus` in abilities.cpp, `kill_value` in self_abilities.cpp and `life_value` in turn_order.cpp. `gem_value` 15 and the recall-cancel value 60 are each defined twice.
- **`pair_gems(world, e)` / `partner_of`** next to `linked_partner_health`: the Cassi/Issac partner lookup appears in abilities.cpp:94-99, turn_order.cpp:100-107 (`gems_lost`) and self_abilities.cpp:182-185.
- **`groups_near`:** copied in abilities.cpp:123 and self_abilities.cpp:64; make it one `StaticMap` method.
- **`live_enemies`** (turn_order.cpp:51) re-implements world.cpp's `engine::champion`.
- **world.cpp:**
  - `assign`/`assign_or`/`assign_and`/`assign_not` duplicate util.h's `*_into` with the arguments swapped.
  - The two `central_tile` overloads can be one template.
  - The `track_horizon` expiry block is written three times; make it `expired(b)`.
- **safety.cpp:**
  - `considered(e)` for the 4 copies of the enemy filter.
  - `join_allies` and `join_approaching`, shared by `pursuit`, `turns_to_kill_idle` and `fight_key`.
  - `threat_strike`'s stun line (safety.cpp:349) is just `s.stuns[max(0, d-1)]`.
- **comms.cpp:** extract `put_sighting(...)`; the rally and plain sighting writes repeat the same 7 setters.

### 1.6 Globals, map classifiers and parameters
- **Map kind:** `monolith_only()` and `shared_gems_map()` each keep a function-static cache, and the `spell_builds` global is reassigned every turn although it never changes. Compute one map kind once in `StaticMap`.
- **`sieging` global:** it only feeds `camp_trapped`, so pass the value instead. See also bug 2.1.
- **One heal-trip threshold:** merge `shop_heal_fraction`, `siege_heal_fraction` and the literal `0.6f` in `capture_recall` (all 0.6) into one `heal_trip_fraction`.
- **Name the "hurt" 0.5** used in `pack_zone` and `want_home`.
- **`pack_zone`:** its `r = 7` should be a named radius. The comment still says `Strike::max_reach + 2`, which is 8 since item 5.
- **`camp_trapped`'s 7.0 and 2.5** are `exit_cost(4)` and `exit_cost(1)`. Write them that way.
- **`capture_rounds = 6`** is `capture_time + 1`. Derive it.

### 1.7 Beliefs and tracking
- **Delete the round-1 special case in `init_beliefs`** (world.cpp:714-742, ~28 lines). The lineage cache in `track()` produces the same `possible` sets. Confirm with the bench.
- **`fix_nowhere` → `b.tracked = false`** in the death branch (world.cpp:808, 1022). Every reader checks `alive` first.
- **`update_altars`:** keep only the tile loop. The board path picked by fuel calls the same idempotent `seen()`.
- **Make private:**
  - `World::turns_between`, `Moment`, `now`.
  - Safety's `chance_in_reach`, `may_be_hit`, `worst_damage`, `camp_area`, `invalidate`.
  - Pathing's `route`, `closer_neighbours`, `my_pos`, `approach_steps`.
  - `threat_strike`/`turns_before_ours` can move out of the header.
- **`StaticMap::enemy_spawn_tiles`:** only `build()` uses it, so make it a local.

### 1.8 Debug code (world.cpp has ~250 debug lines out of 1669)
- **Move** `dump_beliefs`, `DumpWriter` and `debug_draw` to `world_debug.cpp`.
- **Delete the `debug_log` text paths:**
  - The summary, `trackcheck`, `cdcheck`, and the camp and holder prints. These are plain `std::cout`, which would change the game if turned on.
  - `World::advance()`, which only `trackcheck` uses.
  - The fields only that summary reads: `Scores::ally_delta`, `enemy_tribute_round`/`amount`, `AltarBelief::ally_lock_hits`, `died_round`, `name()`/`str()`.
- **Keep** what `audit_beliefs.py` and `fight_calibration.py` parse: `pos_source`, `respawn_earliest`/`latest`, `last_damaged_round`, `seen_round`, `debug_fights`, `debug_beliefs`.
- **Enemy-ward tracking** (`update_wards`, `WardSighting`, `enemy_wards`, ~35 lines) is only read by debug output. Removing it also drops a `sdk_wards` read every turn.
- **`note_shortcut` is used for decisions that are not fuel shortcuts:**
  - The tags are `farm-local-reward`, `farm-spell-approach`, `farm-spell-cast`, `farm-spell-basic` and `farm-spell-cooldown`.
  - They inflate the `--fuel 0` counts. Drop them or use another tag.
- **`std::cout` → `printf`** in `check_facts_against_engine` and `print_fuel_log`, then drop `<iostream>` from util.h, which every file includes. *Fuel-only*: about 11k of static initialisation.

### 1.9 Fuel-only caches and allocations that add code without saving much
- **The `strike()` memo** (safety.cpp:313-331) duplicates `Safety::Foe::strike` and turn_order's `Strikes`.
- **farm's `GroupFacts.centre`/`.home`/`.to_altar`** cache values that `from_centre`, `home_ground` and `centre_to_altar` already cache. The static is also named `facts`, which shadows `aph::facts()`.
- **`local_spell_plan`'s static station memo** caches eight vector additions.
- **siege():**
  - It allocates `bitboard inner`, `goals` and by-value `tiles()`/`square()` results every turn; the rest of bot.cpp uses static scratch boards.
  - `siege_load` is computed twice per turn.
- **`prey()`'s lazy `std::optional<float> strength`.**
- **`closer_neighbours`** re-checks the guard that `try_move` already checks and allocates a vector.
- **`any_threat()`** runs a pointless `any_within` per unseen enemy.
- **`ensure_picked`/`all_champions`/`picked_round`** (draft.cpp): the preference list already holds all 11 champions. Wrap `write_plan` in try/catch instead.

### 1.10 Names and comments
- **Shadowed names:**
  - In `farm()`, the local `float partner` shadows `partner(world)` and the claimed block's `left` shadows `rounds_left`'s `left`.
  - The `Field` in comms.cpp shadows `aph::Field`.
- **Stale comments:**
  - `killable_now` (bot.cpp:1763) describes `want_home`'s lethal check.
  - `contesting` says "big group", but the threshold is 40 gems.
  - `Memory::siege` says "a Monolith"; it also covers big groups.
  - `siege_heal_trip` says "a caster"; it applies to any champion.
  - `Memory::farm_group` says "kept to walk on when fuel is short"; it also drives stickiness, the shield and `prepare_walk`.
  - `Memory::farm_spell` says it is "revalidated before ranged passing hits"; it is only read at bot.cpp:1059.
  - main.cpp says "only comms reads vision again".

---

## 2. Bug fixes

### 2.1 `memory.siege`/`staged_since` are only cleared inside `siege()` [checked]
- **Where:** bot.cpp:2207/2223.
- **What happens:**
  - Every branch that ends the turn earlier leaves `memory.siege` set: P, bag, R, S, chase, X and death.
  - On Monolith-only maps, a holder banking a 100-gem share keeps `sieging` true, which disables `camp_trapped`.
  - Below 0.6 health, `siege_heal_trip` keeps the pre-started recall every turn, even after `recall_to_bank` judged walking quicker.
  - `staged_since` survives a retreat. A champion that comes back counts `siege_max_wait` as already elapsed and engages alone.
- **Fix:** at the end of `decide`, clear both unless this turn ran `siege()`.
- **Test:** check the Monolith-only maps separately. Item 1 won 70.7% there, and the accidental heal-recall may be part of that.

### 2.2 Melee champions are priced as spell-clearers with nothing to carry it out [checked]
- **Where:** bot.cpp:1412-1422, 1454.
- **What happens:**
  - `spell_clear_rounds` applies to any champion with a damage spell, including melee Ren and Ryth, who are both in the draft.
  - When the spell clear wins, it zeroes the group's damage and sets `farm_spell`.
  - The only code that carries a spell clear out, `local_spell_plan`, returns at once for non-ranged champions.
  - So melee walks to basic-attack range of a group it priced at zero damage, and `affordable()` lets it through because it is `farm_group`.
- **Fix:** gate spell pricing on "ranged with a damage spell". It goes away entirely with 4.1.

### 2.3 `threat_reach()` overstates enemy reach [checked]
- **Where:** self_abilities.cpp:50-55.
- **What happens:** it uses `max(range, spell reach) + (dash ? 3 : 1)`, ignoring one cast per turn, exclusive spells blocking the walk, and a ranged walk spending the attack.

  | Champion | `threat_reach` | `compute_strike` |
  |---|---|---|
  | Ren | 7 | 4 |
  | Ryth, Stellar, Prism, Vesper | 6 | 5 |
  | Marcella, Tavi | 5 | 4 |

- **Effects:**
  - `shield_if_needed` wastes Varg's 8-round shield on a Ren 5-7 tiles away.
  - Dash landings (`threats_near`/`danger`) avoid too much.
- **Fix:** use `threat_strike(world, e).reach`. That also drops a fourth threat model.

### 2.4 `update_scores` erases a visible enemy's new channel [checked]
- **Where:** world.cpp:1497-1500.
- **What happens:**
  - When a tribute lands, the inferred tributer gets `channel = none` even if it is visible and was just read recalling.
  - Recall-cancel offers (turn_order.cpp:147) and cast valuation then miss it.
  - This is common, because bots pre-start a recall.
- **Fix:** only touch `!visible` tributers.

### 2.5 `bag_at_stake` uses the partner's last-seen bag
- **Where:** bot.cpp:341-344. Three of the four reviews reported this.
- **What happens:**
  - `p->gems` is refreshed only while the partner is visible. Cassi, as gold farmer, and Issac are often apart.
  - The stale bag feeds `brake_bag`, the pack zone, the farm pack gate, `may_chain` and the v17 health floors.
- **Fix:** `p->visible ? p->gems : max(p->gems, comms::bag_of(world, p->index))`. `closing()` already reads `bag_of`. The comms bag is at most a round old and in units of 4.

### 2.6 `contesting()` ignores a winning bag [checked]
- **Where:** bot.cpp:1617.
- **What happens:**
  - `holding_capture()` gives up for `winning_bag()`, but `contesting()` doesn't.
  - Standing on a contested cleared group with a bag that wins the game, the P branch returns every turn while an enemy stays there.
- **Fix:** add `if (winning_bag(world)) return false;`.

### 2.7 kite's fuel fallback walks into the monsters [checked]
- **Where:** bot.cpp:2438-2442.
- **What happens:** when `!safe_here`, it steps towards `G.centre`, deeper into reach.
- **Fix:** delete the gate (the searches are capped at 24 layers anyway), or step out of `threat` as at 2451-2457.

### 2.8 The fight sim misses our death from Ren's reflect on our own turn [checked]
- **Where:** safety.cpp:236-240.
- **What happens:**
  - After `act(us, them)` only `them.alive == 0` is checked.
  - If our hit kills their last fighter while Ren's reflect kills us, the sim reports a win with `self_falls = false`.
- **Fix:** check our side after our turn too. This is rare.

### 2.9 `emblem_gain_rounds` overvalues shopping
- **Where:** bot.cpp:652-664.
- **What happens:**
  - The +0.15 Jungle term stays on forever on shared-gem maps, where `buy_shards` skips Jungle (`spell_builds`).
  - After Jungle and Power, the next emblem is Durability Health, but the gain is still main-stat growth.
  - Both inflate shop and capture-recall trips.
- **Fix:** `if (!spell_builds && ...)`, and price the Durability step.

### 2.10 `siege_candidate()` chooses before checking readiness
- **Where:** bot.cpp:2152-2178.
- **What happens:** on a normal map with an alive Monolith (limit 0 there, so never ready) and a 150+ gem group, a nearer Monolith shadows the ready big group.
- **Fix:** skip alive Monoliths unless `monolith_only()`. First count the suite maps with this layout.

### 2.11 Smaller bugs
- **`bank_gems` idles** when an enemy lock exists and no per-altar field is affordable (bot.cpp:421-431). Fall back to `to_any_altar()`.
- **A rally outlives an out-of-fuel turn** (comms.cpp:161). `state.fighting` is only cleared in `send()`. Reset it in `receive()`.
- **Dead champions run `observe()` every turn** (main.cpp:69). `me().pos` isn't updated on death, so `moved` is always true. Use `moved = me().alive && ...`. *Fuel only.*
- **Short fuel resets our turn priority to 0** (turn_order.cpp:221-243). Return without touching priority instead.
- **`dash_to_attack` score overflow** (self_abilities.cpp:348): `danger*1000 + spawn.at(p)` isn't clamped, and an unreachable landing adds 65535. Clamp to 999 as `dash_away` does.
- **kite sets `memory.claim = g` before giving up** (bot.cpp:2354). Set it after the check.
- **The fight sim's stun can target an enemy that hasn't arrived** (safety.cpp:192-199: `act()` ignores `arrives_at`). This undervalues our stuns in `pursuit`.
- **`collect_local_reward` scans radius 11 with `positions_within`** (bot.cpp:965), whose contract is r ≤ 8 (`Tiles<17*17>`). It is practically unreachable, and it goes away with 4.1.
- **kite and contest_capture disagree on contest timing:**
  - kite allows `steps > left + 1` measured to the centre; `contest_capture` uses `steps > left` to the nearest tile.
  - By the rules the latter is right. Unifying them under the 1.4 helpers settles it.

---

## 3. Simplification and robustness (changes play, needs A/B)

### 3.1 Collapse the fuel machinery
Measure first with `--fuel 0`, then remove each gate whose `SHORTCUT` count is negligible. A gate that falls back to "count it as lost" or "don't act" can usually go, because the simulation's own `end_reserve` cut already counts a cut fight as lost.

| Gate | Where | Falls back to | Proposal |
|---|---|---|---|
| farm no-evaluation | bot.cpp:1200-1225 + `FarmEvaluationReserve` | nearest-group mini-farm with its own `worth` rule | In the loop, use cheap steps (`ally_steps`/`dist`) when a field is unaffordable, then delete the gate and the mini-farm (~30 lines). Check large maps, where it "can last hundreds of rounds". |
| walk_on kept target | bot.cpp:1185-1191 | reverts `farm_group`/`claim` to last turn's choice | Drop it; the centre-field descent is always available. |
| prepare_walk / prepare_next_turn | bot.cpp:2693-2715, main.cpp | precomputed approach (40k floor at turn start) | Remove (~15 lines) if `farm-no-route`/`crow-flies-farm` counts don't rise. |
| step_towards_funded | pathing.cpp:446-477 | no move (`siege-route-fuel`) | Fold into `step_towards(goals, nullptr, cap)` with an uncapped search. This keeps the item-11 swirl fix. |
| simulate fuel cut | safety.cpp:220-258, `Trade::cut` | lost, self falls | Remove the `fuel_floor` parameter; every caller already gates. |
| known_fight + step_guard gate | safety.cpp:702-709, bot.cpp:1857 | partial guard | Drop both; a cut fight is lost and guards the tile, which is safer. |
| want_home simulate gate | bot.cpp:1804-1806 | skips the visible fight-lost check | Same reasoning. |
| chase fallback | bot.cpp:1944 | `step_closer`, which ignores the pack zone | Remove; `prey` already reserved this fuel. |
| approach layers from fuel | pathing.cpp:133-136 | depth depends on remaining fuel | Use `width + height`; `approach_steps`' four fallbacks can then shrink. |
| capped centre-field warm-up | pathing.cpp:234-266, util.h:169-180 | doubling `centre_cap` | One `cached()` path behind one gate (~30 lines). |
| failed_search_pause | self_abilities.cpp:23, 289, 319 | 4-round travel-dash pause, even with unlimited fuel | Remove; the search gate is enough. |
| farm spell-branch layers | bot.cpp:1060-1097 | hand copy of `camp_cast_cost` | Rely on `cast_at_camp`'s own gate (or 4.1). |
| turn-order gates | turn_order.cpp:153-157, 232 | no offers | One combined gate. |
| cost estimates | util.h:185-194 | `field_cost_estimate` vs `search_cost_estimate` | One formula. |

Keep the gates that guard real per-turn work and fall back sensibly:
- The farm loop's per-group gate.
- `find_bush_clusters` (a large cluster costs ~100k).
- The pursuit gate (a cut pursuit would mean retreating too often).
- `prey`.
- The `enemy-cast`/`camp-cast` gates.
- `prepare_member`.
- The travel-dash search gate.

### 3.2 Teammate sightings add the whole enemy spawn to `possible`
- **Where:** world.cpp:966-967.
- **What happens:**
  - With a 4x4 spawn the set is ~45 tiles after one turn, so `unseen_radius` drops from 3 to ~1.
  - After ~3 turns the enemy falls below `credible_weight` and stops counting as a threat at all. A sighting of our own stays at weight 1 for ~5 turns.
- **Fix:** drop the spawn here, since `grow()` adds it after `recall_time` anyway. Alternatively, send a "recalling" bit; bits 32-35 and 62-63 are free.

### 3.3 Run `observe()` regardless of comms
- **Where:** comms.cpp:180, main.cpp:68-72.
- **What happens:** it is skipped whenever a teammate posted a sighting this round, yet next turn's tracking and `prepare_next_turn` rely on it.
- **Fix:** call it in main as `if (moved && alive)`, and drop the `refresh` parameter.

### 3.4 Retreat and siege/kite logic
- **Pack-zone ratios:**
  - At home the ratio is `min(2.0, 2.5)`, so "hurt" has no effect there; away and healthy it is 100.
  - Try `ratio = (home || hurt) ? 2.0 : no zone`, which drops a parameter.
  - EXPERIMENTS lists lone champions walking into packs away from home as an open problem, so test this rather than assume it.
- **Delete kite's contested branch** (bot.cpp:2349-2367, ~19 lines). `contest_capture` runs just before it and covers a superset.
- **kite stations ignore line of sight:** kite draws plain Chebyshev squares, while siege uses `attack_tiles(g, ability_range)`. Unit-target spells need sight. Give both one `standoff_tiles(g, r)`. Test on shared-gem maps, where kite wins 77%.
- **siege goals can go empty when fuel is short** (bot.cpp:2280-2287): if the attack tiles aren't ready, melee silently walks back to the radius-5 stage ring. Drop the floor or log a shortcut.
- **One cast/attack order in siege's two tails** (bot.cpp:2307-2319).
- **One `run_home()`** for the W-branch retreat and the R branch. W would then also try `flee_camps`.
- **`recall_outruns`:** use the cached, two-turn-aware `safety.strike_of(e)` instead of a fresh `strike()`.
- **`shield_if_needed`:** pass `memory.claim`, not the stale `farm_group`, while sieging or holding.

### 3.5 Farm consistency
- The crew value leaves out `capture_rounds`, which the solo and partner values include (bot.cpp:1406). This is inherited from nemesis-v2, so test it.
- Hits after a walk or dash use `affordable`, not `passing` (bot.cpp:1500, 1506), so they skip ally-claimed and gold-only filtering.
- There are three "health we can spare" models: v17's literal 0.6 with a bag, `recall_health_fraction`, and `spare_health`. Use one helper. This is moot with 4.1.

### 3.6 Fight sim consistency
- `turns_to_kill_idle` should add enemies with `join()`, as `pursuit` does, rather than `fighter()` plus a manual health assignment.

---

## 4. Feature removal

Ordered by lines saved against evidence that the feature helps.

| # | Feature | Lines | Evidence | Notes |
|---|---|---|---|---|
| 4.1 | **v17 port:** `local_spell_plan`, `collect_local_reward`, the spell branch in `farm()`, `FarmSpellPlan`/`FarmEvaluationReserve`, Memory `farm_spell`/`farm_station`/`worked_*` | ~335 | Item 10's bundle was level, and so was hecate vs v17 locally. It is the most fuel-gated code in the bot (~25 gates) and has its own hazard model, pathing and health floor. | A/B `collect_local_reward` first. If it goes, also try dropping spell pricing (`spell_clear_rounds`, `safe_targets`, `basic_output`, `best_spell`, ~50 lines), which also settles 2.2. Ladder-motivated, so also scrim. |
| 4.2 | **DraftPlan** (draft.h/.cpp, world and pathing hooks) | ~230 | Pure fuel cache: every value equals what champions compute. Byte-identical at 100M. | Decide with `--fuel 0` on 100x100 and bushy maps (turn 1-5 shortcuts, lost turns). Cheapest partial cut: the per-spawn-tile offsets (~35 lines). Attack-tile packing (~75) saves the most real fuel. |
| 4.3 | **Delayed tribute stun:** `tribute_to_stun_later`, D branch, `alive_now`, the `hold` parameter through `attack_enemy`/`attack_target`/`reset_and_attack_enemy`/`cast_at_enemies`/`dash_to_attack` | ~55 | Never tested. A stun cancels a tribute whenever it lands; waiting only wastes the enemy's channel turns while ours idles. | Keep `can_stop_winning_tribute`. |
| 4.4 | **`killable_now`** + `want_home`'s kill plumbing + `Safety::fight`'s `exclude`/`fight_key` handling | ~40 | Item 8: level, fires ~0.15 times a game. It also checks only our own Cassi/Issac body. | |
| 4.5 | **Lineage sharing** (`Tracked`, `tracked_`, `lineages_`, `track()`) | ~55 | Fuel only; byte-identical to always calling `advance_and_prune`. Saves 2-7k per extra enemy per turn while they share a lineage (rounds 2-10, joint respawns). | Bench first. If kept, still do 1.7's round-1 cut. |
| 4.6 | **`keep_walk` free-stun logic** in `enemy_cast` (abilities.cpp:218-239, 257, 309-312) | ~30 | Never tested. | Compare against a plain `keep_walk_value` threshold. |
| 4.7 | **Ground casts at unseen enemies** (abilities.cpp:285-300, `max_unseen_tiles`) | ~18 | Never tested. | |
| 4.8 | **Probabilistic `threatened()`** (`hit_given_reach`, `recall_risk`, `unknown_camp_weight`) | ~25 | Never tested. | It gates recall, capture-recall and tribute, and recall behaviour differs between local games and the ladder (EXPERIMENTS), so this is riskier. |
| 4.9 | **Rally bit** (comms bit 31, `sight_fight`, `post_rally`) | ~15 | No receiver treats a rally differently, and "rally assist" was level or lost. | Make the chase target the preferred enemy in the round-robin instead. |
| 4.10 | **Big-group sieges on normal maps** (`big_rounds`, `big_respawn_wait`, the big branch of `siege_ready`) | ~10 | Sieges on normal maps lost (39.6%; 5-40%). | Count the suite maps that have a non-Monolith group of 150+ gems alongside other gem camps first. |
| 4.11 | **Ren specials:** reflect in `min_camp_damage` (bot.cpp:491-508), Ren's Focus build | ~20 | Shipped in item 10's level bundle; "Ren Focus builds" lost 42.3% locally. | Remove only on ladder evidence. |
| 4.12 | **Debug-only extras:** `check_facts_against_engine` (~60, could move to `rules-verification/probes/`), `debug_log` text paths and enemy wards (1.8) | ~150 | Debug only. | |

**Keep.** These have evidence behind them:
- `step_guard`, `pursuit`, `threat_strike` (item 5, +5 points).
- Monolith sieges and the range-4 casting (item 1, 70.7% on Monolith-only maps).
- kite on shared-gem maps (77%).
- `contest_capture` (+1.3 points, no suite worse).
- `camp_trapped`, `finishing_camp`, siege stickiness.
- `start_recall`'s pre-start (removing it lost 20.8%).
- Bush wards (removing them leaned worse, 46.7-48.2%) and the periodic scouting ward.
- `step_towards_funded`'s uncapped search (the item-11 swirl stall).
- The single-condition item-7 fixes (little to gain).

---

## Suggested order
1. **One bucket-1 commit,** checked byte-identical with `tools/fuel/bench.py compare`. This is ~400-500 lines lighter and makes everything after it easier to read.
2. **`--fuel 0` bench on the cleaned bot:** count `SHORTCUT` tags per gate after dropping the non-fuel tags in 1.8, and record lost turns. That count decides which rows of 3.1, 4.2 and 4.5 can go.
3. **Bug fixes 2.1-2.7, one A/B each.** They are small and independent. 2.1 and 2.3 affect the most games.
4. **4.1 (v17 port), the largest single cut.** Then 4.3, 4.4 and 4.6-4.9, each A/B'd and kept out if the result is level.
5. **The 3.x behaviour changes,** testing 3.2 and 3.4 first.
