// The turn: decide() takes the first branch that applies (channels, shopping, Willow-Prism support,
// the strike search, a capture, a bag, a shopping trip, a chase, a contest, a siege or kite, the
// farm), act() wraps it in the free actions that end the turn, and play_turn() keeps memory and comms.
#include "bot_parts.h"

namespace aph {

namespace {

struct {
    bool chose = false; // the strike search chose this turn's cast, heals and shields included
    vec2 at{};          // where its plan ended
    bool hit = false;   // whether we had attacked by then
} search;
bool end_ward = false; // the turn-end ward, seeing more than our last observe

void note_search(bool chose) { search = {chose, my_position(), !my_can_attack()}; }

// The heal and shield the search priced still fit: we end where its plan did, attacked or not as then.
bool search_priced_end() { return search.chose && my_position() == search.at && !my_can_attack() == search.hit; }

// Read by tools/replay/fight_calibration.py.
void log_fight(const char* tag, const World& world, Safety& safety, vec2 p, const Trade& t, int target) {
    if (!debug_fights || !fuel_ok(end_reserve + 15000)) return;
    std::printf("%s %d %u %d %d %d %c %d %d %d %d %d %d %d %d %d %d", tag, world.round,
                static_cast<std::uint32_t>(world.me().handle), p.x, p.y, static_cast<int>(world.me().health), static_cast<char>(decision),
                static_cast<int>(t.lost), t.turns_to_kill_us, t.turns_to_kill_them, t.allies, t.enemies,
                static_cast<int>(t.our_health), static_cast<int>(t.their_health), target, static_cast<int>(safety.camp_damage(p)),
                static_cast<int>(safety.lethal(p)));
    for (const float d : t.dealt) std::printf(" %d", static_cast<int>(d));
    for (const auto& a : world.allies)
        if (a.alive && !a.is_self && a.visible && dist(p, a.pos) <= safety_params::fight_ally_radius)
            std::printf(" a%u", static_cast<std::uint32_t>(a.handle));
    for (const auto& th : safety.threats())
        if (const auto b = th.at(p); b.hits)
            std::printf(" %u%c:%d:%d:%d", static_cast<std::uint32_t>(world.enemies[th.enemy].handle), th.visible ? 'v' : 'u',
                        th.visible ? dist(p, th.pos) : -1, static_cast<int>(b.damage), world.round - world.enemies[th.enemy].pos_round);
    std::printf("\n");
}

bool try_ward(vec2 p, Memory& memory) {
    throw_if_stale();
    try {
        if (!cambc::self().place_ward(p)) return false;
    } catch (const cambc::error&) {
        return false;
    }
    memory.ward = p;
    memory.bushes_watched = {-1, -1};
    return true;
}

// Attackers in a bush stay unseen from outside it, and a ward inside sees across its cluster.
// Our one ward never expires, so replace it only by a cluster with more tiles in ability range of
// here and of our work (claimed group or waited-at altar), where we will be again.
bool ward_bushes(const World& world, Memory& memory) {
    const auto& map = world.map();
    const vec2 here = my_position();
    const auto floor = small_cost_estimate + end_reserve;
    // Off the map: killed this turn (Ren's retaliation), after world.me() was read alive.
    if (here.x < 0 || here == memory.bushes_watched) return false;
    // The board (~1.9k of shifts) waits for the turn-end queue: until then a square around us answers.
    if (!(map.near_bushes_ready() ? test(map.near_bushes(), here) : any_within(map.bushes, here, ward_range()))) return false;
    // Our ward's cluster too, which a planned ward may have put down unseen.
    const bool ward_in_bush = in_bounds(memory.ward) && test(map.bushes, memory.ward);
    if (!map.find_bush_clusters(here, ward_range(), floor) || (ward_in_bush && !map.find_bush_clusters(memory.ward, 0, floor))) {
        note_shortcut("ward-no-bushes-clusters");
        return false;
    }
    // Scratch boards: allocating one costs more than the host operations on it.
    static bitboard candidates{cambc::uninitialized}, inner{cambc::uninitialized}, scratch{cambc::uninitialized},
        best{cambc::uninitialized};
    candidates.clear();
    candidates.draw_chebyshev(here, cambc::constants::ward_placement_radius);
    candidates &= map.bushes;
    if (test(map.bushes, here)) drop(candidates, map.bush_cluster(here).tiles);
    // As a candidate it could only tie with itself.
    const BushCluster* warded = ward_in_bush ? &map.bush_cluster(memory.ward) : nullptr;
    if (warded) drop(candidates, warded->tiles);
    if (candidates.is_empty()) {
        memory.bushes_watched = here;
        return false;
    }
    drop(candidates, map.enemy_spawn);
    cambc::vision::ward_tiles_into(team::ally, scratch);
    drop(candidates, scratch);
    const vec2 work = memory.claim >= 0        ? map.groups[memory.claim].centre
                      : memory.wait_altar >= 0 ? map.altars[memory.wait_altar].pos
                                               : vec2{-1, -1};
    // An ability reaches farther than any basic attack.
    const auto score = [&](const bitboard& tiles) {
        const int n = static_cast<int>(count_within(tiles, here, ability_range));
        return in_bounds(work) ? n + static_cast<int>(count_within(tiles, work, ability_range)) : n;
    };
    inner.clear();
    inner.draw_chebyshev(here, 1.0f);
    bool found = false;
    int best_score = warded ? score(warded->tiles) : 0;
    while (!candidates.is_empty()) {
        const auto& c = map.bush_cluster(first_tile(candidates));
        if (const int s = score(c.tiles); s > best_score) {
            best.clear();
            best |= c.tiles;
            best &= candidates; // the cluster's tiles we may ward
            scratch.clear();
            scratch |= best;
            drop(scratch, inner); // those not beside us, if any
            if (!scratch.is_empty()) best.swap(scratch);
            found = true, best_score = s;
        }
        drop(candidates, c.tiles);
    }
    if (!found) return false;
    // A teammate's ward unseen in the bush blocks its tile, and allies pick the same tile first.
    for (auto p : Tiles<3>{best})
        if (try_ward(p, memory)) return true;
    return false;
}

// The draft's ward tile for our work (claimed group, else waited-at altar): placed once in range,
// then kept while that work lasts. Null without one.
std::optional<bool> ward_planned(const World& world, Memory& memory) {
    const auto& map = world.map();
    const int site = memory.claim >= 0        ? memory.claim
                     : memory.wait_altar >= 0 ? static_cast<int>(map.groups.size()) + memory.wait_altar
                                              : -1;
    if (site < 0) return std::nullopt;
    const vec2 p = map.drafted_ward(site);
    if (p.x < 0) return std::nullopt;
    if (memory.ward == p) return false;
    const vec2 here = my_position();
    if (here.x < 0 || dist(here, p) > ward_range()) return std::nullopt;
    // A visible allied ward on the tile is an error (wards.placement).
    static bitboard allied{cambc::uninitialized};
    cambc::vision::ward_tiles_into(team::ally, allied);
    if (test(allied, p) || !try_ward(p, memory)) return std::nullopt;
    return true;
}

// `bushes`: a bush ward if no planned one goes down.
bool place_ward(const World& world, Memory& memory, bool bushes) {
    world.throw_if_stale();
    // A stun refuses every ward, and the thrown error costs ~3.9k fuel.
    if (stunned_turn || !world.me().alive || channelling() || cambc::self().ward_cooldown() > 0) return false;
    if (const auto planned = ward_planned(world, memory)) return *planned;
    return bushes && ward_bushes(world, memory);
}

// What we see changed mid-turn. Safety's beliefs are fixed for its life, so it starts again.
[[gnu::noinline]] void see_again(World& world, Pathing& pathing, Safety& safety) {
    pathing.settle_guard();
    world.observe();
    pathing.invalidate();
    std::destroy_at(&safety);
    std::construct_at(&safety, world);
    forget_pack_zone(world);
    // Willow's guard follows what we see; hyperion's keeps the tile it was worked out from.
    if (const auto held = pathing.held_guard(); world.me().facts().heals() && (held.guard || held.fn))
        guard_steps(world, pathing, safety);
}

// A stun we cast takes its target's next turn, which Safety's threats and fights count: it starts again.
void see_stuns(World& world, Safety& safety) {
    if (!world.read_stuns()) return;
    std::destroy_at(&safety);
    std::construct_at(&safety, world);
    safety.refresh(); // as after the hits that cast it: a kill is read as gone
}

// Our walk or dash brought an enemy into sight that could strike us, or that we could strike,
// before our next turn.
bool see_revealed(World& world, Pathing& pathing, Safety& safety) {
    // Off the map, Ren's reflection killed us this turn.
    const vec2 here = my_position();
    if (here.x < 0 || !world.revealed(here, Strike::max_reach, pathing.take_bump()) || world.is_stale()) return false;
    debug_block({ std::printf("REVEAL %d %u %c\n", world.round, my_handle(), static_cast<char>(decision)); });
    see_again(world, pathing, safety);
    return true;
}

// A camp member's reach covers a tile of our spawn, read once.
bool camps_reach_spawn(const World& world) {
    static int known = -1;
    if (known >= 0) return known == 1;
    known = 0;
    // As any_within(ally_spawn, m.pos, m.reach) for every member, without its four board calls a
    // member (~300k on maps of thousands): a spawn tile within reach lies in the spawn's box too.
    const auto& tiles = world.map().ally_spawn_tiles;
    if (tiles.empty()) return false;
    vec2 lo = tiles[0], hi = tiles[0];
    for (const auto t : tiles) lo = {std::min(lo.x, t.x), std::min(lo.y, t.y)}, hi = {std::max(hi.x, t.x), std::max(hi.y, t.y)};
    for (const auto& g : world.map().groups)
        for (const auto& m : g.members) {
            const vec2 p = m.pos;
            if (std::max({lo.x - p.x, p.x - hi.x, lo.y - p.y, p.y - hi.y}) > m.reach) continue;
            for (const auto t : tiles)
                if (dist(t, p) <= m.reach) return (known = 1);
        }
    return false;
}

// The turn end heals anywhere on spawn, as home_trip prices it: a step on spawn nearer the next goal
// (an altar with a bag, else our farm group), no more exposed than here.
void mend_step(const World& world, Pathing& pathing, Safety& safety, const Memory& memory) {
    if (!my_can_move()) return;
    const int g = memory.farm_group;
    const Field* goal = my_gems() > 0 ? &pathing.to_any_altar()
                        : g >= 0 && g < static_cast<int>(world.camps.size()) ? &pathing.to_group(g) : nullptr;
    if (!goal) return;
    const vec2 here = my_position();
    const auto& blocked = pathing.blocked();
    std::optional<Safety::Bound> risk; // read once a step gains
    int best = goal->at(here);
    std::optional<vec2> step;
    for (const auto d : directions) {
        const vec2 p = here + d;
        if (!in_bounds(p) || !test(world.map().ally_spawn, p) || test(blocked, p) || goal->at(p) >= best) continue;
        if (!risk) risk = safety.bound(here);
        if (const auto r = safety.bound(p); r.doubled > risk->doubled || (r.stuns && !risk->stuns)) continue;
        best = goal->at(p), step = p;
    }
    if (step) pathing.try_move(*step);
}

// Buys what we may here: consumables on our spawn or dead, shards there too or anywhere for Tavi.
// The crystal first: an altar only it reaches holds our bags, and shards could spend its gold.
// True if shards changed our stats.
bool shop(const World& world, const Memory& memory, bool consumables, bool shards) {
    if (consumables) buy_crystal(memory);
    const bool bought = shards && buy_shards(world);
    if (consumables) buy_lock();
    return bought;
}

// The strike search's walk, hits and casts, then the heal and shield it left. True if it attacked.
bool search_strikes(World& world, Pathing& pathing, Safety& safety, const Memory& memory, bool holding, bool contested) {
    Intent intent;
    intent.anchored = holding;
    // Both sides on its tiles, only a fight ends a contest: we may close in without stepping off.
    if (contested) intent.hold = &world.map().groups[world.map().group_at(my_position())].tiles();
    intent.walks = !holding && (retaining_gems(world, pathing) || !can_tribute_here(world));
    // A carrier's step banks a turn sooner, freeing a turn of output for the farm.
    intent.step_value = farm_step_value(world);
    // An enemy already in attack range was not worth leaving (want_home): the fight is here.
    if (enemy_within(world, my_position(), world.me().facts().attack_range())) intent.walks = false;
    // The goal most likely walks to an altar when carrying, else to the farm choice.
    intent.to_altar = banks_bag(world, pathing);
    intent.group = memory.farm_group;
    struck = searched = true;
    const auto planned = plan_strikes(world, pathing, safety, intent);
    note_search(planned.searched);
    if (!search.chose) heal_ally(world, safety);
    // The search priced nothing against an enemy its own moves revealed.
    if (see_revealed(world, pathing, safety)) search.chose = searched = false;
    // A cast the search left priced the shield at nothing, blind to the goal's coming camp hit:
    // judged here, before farm's camp reset or dash takes it.
    shield_if_needed(world, safety, memory.claim);
    return planned.attacked;
}

void decide(World& world, Pathing& pathing, Safety& safety, Memory& memory) {
    // Last turn's, for continue_recall: kept only while that recall is, else farm sets it again.
    const int recall_farm = std::exchange(memory.recall_farm, -1);
    if (!world.me().alive || !banks_bag(world, pathing)) memory.banking = false;
    if (!world.me().alive) {
        if (recall_farm >= 0) {
            debug_block({ std::printf("RFDEAD %d %u %d\n", world.round, my_handle(), recall_farm); });
        }
        memory.claim = -1;
        shop(world, memory, true, true); // the dead can only shop
        return;
    }
    // One state read covers the channels until one is cancelled; a channel excludes the others.
    const auto state = my_state();
    if (recall_farm >= 0 && !state.contains(cambc::champion_state::recalling)) {
        debug_block({ std::printf("RF%s %d %u %d\n", test(world.map().ally_spawn, my_position()) ? "LAND" : "LOST", world.round, my_handle(), recall_farm); });
    }
    if (state.contains(cambc::champion_state::teleporting)) return;
    // want_home's answer once a channel's check asked it, until a ward or shards change what we know.
    std::optional<bool> home;
    if (state.contains(cambc::champion_state::submitting_gems) && continue_tribute(world, pathing, safety, memory, home)) return;
    if (state.contains(cambc::champion_state::recalling) && continue_recall(world, pathing, safety, memory, home, recall_farm)) return;
    // A channel refuses a ward, so this is its first chance; its sight counts this turn
    // (probe-ward-sight). Only a planned one: a bush ward needs its clusters grown (a giant one costs
    // ~90k), which the turn end does within its fuel.
    if (place_ward(world, memory, false)) {
        see_again(world, pathing, safety);
        home.reset();
    }

    // Shopping, heals and shields do not move us.
    const bool on_spawn = test(world.map().ally_spawn, my_position());
    if (shop(world, memory, on_spawn, on_spawn || world.me().facts().passive == Passive::remote_shop)) home.reset();
    if (!world.me().can_act(world.round)) return;
    if (const auto* ender = game_ender(world)) {
        stop_game_ender(world, pathing, memory, *ender);
        return;
    }
    const bool willow = support_healer(world.me());
    const bool prism = support_protected(world, world.me());
    // Healing needs a turn end on spawn; a recall arrives at turn start. Under an awake camp, only
    // while we miss more than it takes a round: else we would mend forever while it stays awake.
    const float missing = on_spawn ? my_max_health() - my_health() : 0.0f;
    const bool mend = missing > 0 && missing > (camps_reach_spawn(world) ? safety.camp_damage(my_position()) + 0.01f : 0.0f);
    const bool leave = !mend && (home ? *home : want_home(world, pathing, safety, memory));
    // Willow at work heals first, and the work goes on without the strike search.
    const bool willow_free = willow && !mend && !leave;
    const bool working = willow_free && support_work(world, pathing, safety, memory);
    const bool strikes = !working && strike_possible(world);
    bool mate_eligible = false;
    if (((prism && !mend) || (willow_free && !working)) && support_endpoint(world, !willow)
        && local_support(world, pathing, safety, memory, leave, mate_eligible))
        return;
    if (willow_free && !working && !strikes && !stunned_turn && !mate_eligible && !support_retreat
        && willow_independent_heal_step(world, pathing, safety, memory.farm_group))
        return;
    if (support_retreat) {
        heal_ally(world, safety);
        retreat(world, pathing, safety, memory);
        return;
    }
    // On the turns the search plans, it weighs heals and shields against its other casts. Else a
    // shield would take the one cast from a reset's killing attack or a dash landing on enemies.
    if (!strikes || mend || leave) {
        heal_ally(world, safety);
        if (!strikes || !(reset_may_kill(world) || landing_ready(world))) shield_if_needed(world, safety, memory.claim);
    }
    if (mend) {
        decision = Branch::mend;
        const bool attacked = attack_enemy(world);
        if (attacked) reset_and_attack_enemy(world, true);
        cast_at_enemies(world);
        if (attacked) reset_and_attack_enemy(world);
        mend_step(world, pathing, safety, memory);
        return;
    }
    if (leave) {
        retreat(world, pathing, safety, memory);
        return;
    }

    guard_steps(world, pathing, safety);
    if (join_marcella_capture(world, pathing, safety, memory)) return;
    if (yield_capture(world, pathing, safety, memory)) return;
    if (take_capture_handoff(world, pathing, safety, memory)) return;
    const bool contested = contesting(world);
    const bool holding = holding_capture(world, pathing) || contested;
    const bool attacked = strikes && search_strikes(world, pathing, safety, memory, holding, contested);
    decision = holding ? Branch::hold : attacked ? Branch::attack : decision;
    if (!cambc::self().is_alive()) return;
    if (!my_can_attack() || !my_can_cast()) pathing.settle_guard(), see_stuns(world, safety), safety.refresh();
    // The guard was placed around the tile we started on: the goal steps from where the search left us.
    if (my_position() != world.turn_start && (my_can_move() || my_can_cast())) guard_steps(world, pathing, safety);
    if (holding) {
        hold_capture(world, memory, attacked);
        return;
    }
    // The work's steps keep off the tiles want_home would send us back from (guard_work). A chase
    // keeps the step guard: its fight weighs who walks in.
    const auto strike_guard = pathing.held_guard();
    if (my_can_move() || my_can_cast()) guard_work(world, pathing, safety, memory.damage);
    if (banks_bag(world, pathing)) {
        carry_bag(world, pathing, safety, memory, attacked);
        return;
    }
    // After the search the goal takes only what the search left and could not price: its walk, camp
    // work, a travel dash (a dash the search plays only before a strike). A ranged attack spent the walk.
    if (my_can_move() && wants_shop(world, pathing, safety, memory)) {
        decision = Branch::shop;
        memory.claim = -1;
        step_safely(world, pathing, pathing.to_ally_spawn(), safety);
        return;
    }
    const auto work_guard = pathing.held_guard();
    pathing.restore_guard(strike_guard);
    if (chase(world, pathing, safety)) return;
    strike_guard_known(pathing, my_position());
    pathing.restore_guard(work_guard);
    if (contest_capture(world, pathing, memory)) {
        decision = Branch::contest;
        return;
    }
    decision = Branch::farm;
    if (world.map().shared_gems ? kite(world, pathing, memory) : siege(world, pathing, memory)) {
        decision = Branch::siege;
        return;
    }
    farm(world, pathing, safety, memory);
}

// Recalling every turn end and cancelling next turn when not wanted makes a wanted recall a
// turn shorter. Damage before then cancels it at no cost. A stunned champion cannot start one:
// the engine refuses it, and the thrown error costs ~3.9k fuel.
void start_recall(const World& world) {
    if (stunned_turn || !world.me().alive || channelling()) return;
    // Ren's reflected damage can kill us in our own turn: dead, we read as off the map.
    const vec2 here = my_position();
    if (here.x < 0 || test(world.map().ally_spawn, here)) return;
    throw_if_stale();
    try {
        cambc::self().recall();
    } catch (const cambc::error&) {
    }
}

// Our farm choice when a walk to it is to be searched, else -1.
int walk_target(const World& world, Pathing& pathing, const Memory& memory) {
    const int g = memory.farm_group;
    if (!world.me().alive || channelling() || g < 0 || g >= static_cast<int>(world.camps.size())
        || (world.map().any_group_hop() && beyond_walk(world, pathing, g)))
        return -1;
    return g;
}

} // namespace

void prepare_next_turn(const World& world, Pathing& pathing, const Memory& memory, std::uint64_t fuel_floor) {
    // Next turn's walk, searched from where that turn starts: act() then finds it ready.
    if (const int g = walk_target(world, pathing, memory); g >= 0) pathing.prepare_approach(g, walk_range(world, g), fuel_floor);
    // Next turn's farm loop starts from our choice: its order is made here when the fuel is spare,
    // rather than in the loop's turn.
    const auto& map = world.map();
    if (const int g = memory.farm_group; g >= 0 && !map.nearest_groups_ready(g) && fuel_ok(fuel_floor + 100 * map.groups.size() + 3000))
        map.nearest_groups(g);
    // The walk altar_access left unknown, so that the first camp change updates it rather than floods.
    if (altar_walk_pending && fuel_ok(fuel_floor + full_field_cost_estimate())) flood_altar_walk(world, pathing, altar_walk());
}

// Read from our state at the turn's end: a slot cast this turn has its full cooldown, and each reset
// restored a spent attack. A ranged walk spent the attack without one.
void count_use(const World& world, vec2 start, bool could_attack) {
    if (!world.me().alive) return;
    const auto& f = world.me().facts();
    bool dashed = false;
    int resets = 0;
    for (int s = 0; s < 2; ++s) {
        if (my_cooldown(s) < ability_cooldown) continue;
        ++use.casts[s];
        dashed |= f.abilities[s].kind == AbilityKind::dash;
        resets += f.abilities[s].kind == AbilityKind::attack_reset;
    }
    const bool walked = !f.walk_and_attack_independent() && my_position() != start && !dashed;
    use.attacks += std::max(0, (could_attack && !my_can_attack()) + resets - walked);
}

// The turn's walk, hits and casts, and the free actions that end it.
void act(World& world, Pathing& pathing, Safety& safety, Memory& memory) {
    const vec2 start = world.me().pos;
    const bool could_attack = my_can_attack();
    // The walk to our farm choice is searched out to our tile: from where the turn starts, before
    // anything moves us. The turn end before has usually made it.
    if (const int g = walk_target(world, pathing, memory); g >= 0) pathing.approach(g, walk_range(world, g));
    const int claim = memory.claim;
    decide(world, pathing, safety, memory);
    if (decision != Branch::wait_altar) memory.wait_altar = -1;
    // A turn without siege() (a fight, a heal) keeps the siege while our claim stays on it; a chase
    // or a bag takes us away from it.
    if (!sieged && (memory.claim != claim || decision == Branch::chase || banks_bag(world, pathing))) {
        memory.siege = false;
        memory.staged_since = -1;
    }
    if (world.me().alive && see_revealed(world, pathing, safety)) search.chose = false;
    if (!support_owned && strike_after(world, pathing, safety).searched) note_search(true);
    pathing.set_guard(nullptr);
    if constexpr (debug_fights)
        if (world.me().alive && !test(world.map().ally_spawn, start) && fuel_ok(end_reserve + 15000))
            if (const auto t = safety.fight(start); t.enemies > 0) log_fight("FF", world, safety, start, t);
    // Nothing else takes the cast now. The search values a heal at what could hit the ally before
    // the slot is back, so a plan may leave one worth casting.
    if (!support_owned) heal_ally(world, safety); // allies in reach after walking
    if (!support_owned && !search_priced_end()) shield_if_needed(world, safety, memory.claim);
    end_ward = place_ward(world, memory); // where we end the turn
    place_lock(world);
    if (!support_owned) start_recall(world);
    count_use(world, start, could_attack);
}

void play_turn(World& world, Pathing& pathing, Memory& memory) {
    Safety safety{world};
    const int live_claim = world.me().facts().has_dash() && memory.claim >= 0
                               && memory.claim < static_cast<int>(world.camps.size())
                               && world.camps[memory.claim].state == CampState::alive
                               && world.camps[memory.claim].state_round == world.round
                               ? memory.claim : -1;
    const auto* record = world.me().alive ? &my_record() : nullptr;
    const float health = record ? record->health : 0;
    memory.damage = memory.round == world.round - 1 ? std::max(0.0f, memory.health - health) : 0;
    if (!record || health > memory.camp_fled) memory.camp_fled = -1;
    decision = Branch::none;
    sieged = false;
    search.chose = false;
    struck = searched = false;
    support_owned = support_requested = support_offered = support_retreat = end_ward = false;
    comms::support_intent(world.round, false);
    siege_group() = -1;
    const int camp_hits_before = camp_hits();
    if (world.me().alive) note_upkeep(world, safety, memory.damage), note_income_start(world);
    stunned_turn = record && my_stunned(cambc::champion_state::from_bits_retain(record->state));
    // A failed act still posts the claim, the bag and the health that next turn's damage reads.
    // Neither catch takes StaleTurn: a stale turn abandons the rest.
    try {
        act(world, pathing, safety, memory);
    } catch (const std::exception& e) {
        std::printf("r%u act error: %s\n", cambc::round_number(), e.what());
    }
    try {
        if (!world.is_stale()) see_stuns(world, safety);
        set_turn_order(world, safety);
    } catch (const std::exception& e) {
        std::printf("r%u turn order error: %s\n", cambc::round_number(), e.what());
    }
    if (!world.is_stale() && world.me().alive) {
        bool intent = support_requested;
        // support_offered was judged in the vision we had: a ward since may show a threat.
        if (world.me().facts().heals() && support_offered) {
            intent = true;
            if (end_ward) {
                see_again(world, pathing, safety);
                float amount = 0;
                intent = heal_ready(world, world.me(), amount) && exposure_here(world, safety).safe();
            }
        }
        world.throw_if_stale();
        comms::support_intent(world.round, intent);
    }
    // Willow's formation wait (support.cc) ends with a heal, or a camp hit outside support.
    if (world.me().alive && world.me().facts().heals()
        && ((!support_owned && camp_hits() != camp_hits_before) || my_cooldown(world.me().facts().slot_of(AbilityKind::heal)) >= ability_cooldown))
        memory.formation_start = -1, memory.formation_turns = 0;
    comms::claim(memory.claim);
    comms::bag(world.me().alive ? static_cast<int>(my_gems()) : 0);
    if (!world.is_stale()) publish_turn_order(world, comms::priority_payload(world));
    memory.live_claim = live_claim;
    memory.round = world.round;
    memory.health = world.me().alive ? my_health() : 0;
    if (world.me().alive) note_income_end(world);
    upkeep.camp_turns += camp_hits() != camp_hits_before;
    debug_block({ std::printf("D %d %u %c %d %d\n", world.round, static_cast<std::uint32_t>(world.me().handle), static_cast<char>(decision), memory.farm_group, memory.claim); });
}

} // namespace aph
