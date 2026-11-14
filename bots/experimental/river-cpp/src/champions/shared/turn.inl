// Function bodies; src/unity.cpp includes this after every header.

namespace aph {
namespace {
void log_fight(const char* tag, const World& world, Safety& safety, vec2 p, const Trade& t, int target)
{
    if (!debug_fights || !fuel_ok(end_reserve + 15000)) return;
    std::printf("%s %d %u %d %d %d %c %d %d %d %d %d %d %d %d %d %d", tag, world.round,
                static_cast<std::uint32_t>(world.me().handle), p.x, p.y, static_cast<int>(world.me().health), decision,
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

bool channelling()
{
    using cambc::champion_state;
    const auto state = my_state();
    return state.contains(champion_state::recalling) || state.contains(champion_state::submitting_gems)
           || state.contains(champion_state::teleporting);
}

bool attack_enemy(const World& world)
{
    if (!my_can_attack()) return false;
    const auto target = attack_target(world);
    if (!target) return false;
    try {
        attack_champion(*target);
        return true;
    } catch (const cambc::error&) {
        return false;
    }
}

[[gnu::noinline]] void see_again(World& world, Pathing& pathing, Safety& safety)
{
    world.observe();
    pathing.invalidate();
    std::destroy_at(&safety);
    std::construct_at(&safety, world);
    forget_pack_zone(world);
    // Willow's guard follows what we see; hyperion's keeps the tile it was worked out from.
    if (const auto held = pathing.held_guard(); world.me().type == cambc::champion_type::willow && (held.guard || held.fn))
        guard_steps(world, pathing, safety);
}

void see_stuns(World& world, Safety& safety)
{
    if (!world.read_stuns()) return;
    std::destroy_at(&safety);
    std::construct_at(&safety, world);
    safety.refresh(); // as after the hits that cast it: a kill is read as gone
}

bool see_revealed(World& world, Pathing& pathing, Safety& safety)
{
    // Off the map, Ren's reflection killed us this turn.
    const vec2 here = my_position();
    if (here.x < 0 || !world.revealed(here, Strike::max_reach, pathing.take_bump()) || world.is_stale()) return false;
    debug_block({ std::printf("REVEAL %d %u %c\n", world.round, my_handle(), decision); });
    see_again(world, pathing, safety);
    return true;
}

}
}
namespace aph {
void prepare_walk(const World& world, Pathing& pathing, const Aims& aims, std::uint64_t fuel_floor)
{
    const int g = aims.farm_group >= 0 ? aims.farm_group : aims.claim; // the group we clear, else our claim
    if (!world.me().alive || channelling() || g < 0 || g >= static_cast<int>(world.camps.size())) return;
    pathing.prepare_approach(g, walk_range(world, g), fuel_floor);
}

void prepare_next_turn(const World& world, Pathing& pathing, const Aims& aims)
{
    prepare_walk(world, pathing, aims, end_reserve);
}

void count_use(const World& world, vec2 start, bool could_attack)
{
    if (!world.me().alive) return;
    const auto& f = world.me().facts();
    bool dashed = false;
    int resets = 0;
    for (int s = 0; s < 2; ++s) {
        std::int32_t cooldown = 0;
        ok(cambc::detail::sdk_champion_cooldown(my_handle(), static_cast<std::uint32_t>(s), &cooldown));
        if (cooldown < ability_cooldown) continue;
        ++use.casts[s];
        dashed |= f.abilities[s].kind == AbilityKind::dash;
        resets += f.abilities[s].kind == AbilityKind::attack_reset;
    }
    const bool walked = !f.walk_and_attack_independent() && my_position() != start && !dashed;
    use.attacks += std::max(0, (could_attack && !my_can_attack()) + resets - walked);
}

void act(World& world, Pathing& pathing, Safety& safety, Aims& aims)
{
    const vec2 start = world.me().pos;
    const bool could_attack = my_can_attack();
    prepare_walk(world, pathing, aims, walk_first_floor);
    const int claim = aims.claim;
    Turn turn{world, pathing, safety, aims};
    run_champion(turn);
    // A turn without siege() (a fight, a heal) keeps the siege while our claim stays on it; a chase
    // or a bag takes us away from it.
    if (!sieged && (aims.claim != claim || decision == 'C' || (bankable_bag(world, pathing) > 0 && !retaining_gems(world, pathing))))
        aims.siege = false;
    if (world.me().alive && see_revealed(world, pathing, safety)) searched = false;
    if (!support_owned && strike_after(world, pathing, safety).searched)
        searched = true, searched_at = my_position(), searched_hit = !my_can_attack();
    pathing.set_guard(nullptr);
    if constexpr (debug_fights)
        if (world.me().alive && !test(world.map().ally_spawn, start) && fuel_ok(end_reserve + 15000))
            if (const auto t = safety.fight(start); t.enemies > 0) log_fight("FF", world, safety, start, t);
    // The search priced heal and shield where its plan ended, not a later walk or hit by the goal.
    if (!support_owned && (!searched || my_position() != searched_at || !my_can_attack() != searched_hit)) {
        heal_ally(world); // allies in reach after walking
        shield_if_needed(world, safety, aims.claim);
    }
    end_ward = place_ward(world, aims); // where we end the turn
    place_lock(world);
    if (!support_owned) start_recall(world);
    count_use(world, start, could_attack);
}

int engaged_group(const World& world, Pathing& pathing)
{
    const vec2 here = world.me().pos;
    if (holding_capture(world, pathing)) return world.map().group_at(here);
    const int range = world.me().facts().attack_range();
    const auto& groups = world.map().groups;
    int best = -1, best_dist = range + 1;
    for (int g = 0; g < static_cast<int>(groups.size()); ++g) {
        const auto& c = world.camps[g];
        if (c.state != CampState::alive || c.awake == Awake::asleep || dist(here, groups[g].centre) > range + 8) continue;
        for (int i = 0; i < static_cast<int>(groups[g].members.size()); ++i)
            if (c.health[i] > 0 && dist(here, groups[g].members[i].pos) < best_dist) best = g, best_dist = dist(here, groups[g].members[i].pos);
    }
    return best;
}

void play_turn(World& world, Pathing& pathing, Aims& aims)
{
    Safety safety{world};
    pathing.set_safety(&safety);
    struct Unset {
        Pathing& p;
        ~Unset() { p.set_safety(nullptr); }
    } unset{pathing};
    const auto* record = world.me().alive ? &my_record() : nullptr;
    aims = Aims{};
    if (record) {
        aims.damage = world.self_damage;
        // The group we are clearing is ours to finish, as if we claimed it first (an ally nearer it does
        // not take it from us); else our claim.
        aims.farm_group = engaged_group(world, pathing);
        aims.claim = aims.farm_group >= 0 ? aims.farm_group : claims::of(world, world.self_index);
        aims.crew = aims.farm_group >= 0 && claims::theirs(world, aims.farm_group) && claims::of(world, world.self_index) != aims.farm_group;
        aims.banking = bag_bound_for_altar(world, pathing, safety);
        // Read before siege() only by a recall going on and by camp hits we stand in.
        if (channelling() || safety.camp_damage(world.me().pos) > 0)
            if (const int g = siege_held(world, pathing, aims); g >= 0) aims.siege = true, aims.claim = g;
    }
    decision = '-';
    sieged = false;
    searched = false;
    struck = false;
    support_owned = support_requested = support_offered = support_retreat = end_ward = false;
    comms::support_intent(world.round, false);
    siege_group() = -1;
    const int camp_hits_before = camp_hits();
    if (world.me().alive) note_upkeep(world, safety, aims.damage);
    stunned_turn = record && my_stunned(cambc::champion_state::from_bits_retain(record->state));
    // A failed act still posts the turn order.
    try {
        act(world, pathing, safety, aims);
    } catch (const std::exception& e) {
        std::printf("r%u act error: %s\n", cambc::round_number(), e.what());
    }
    // Not StaleTurn: a stale turn abandons the rest.
    try {
        if (!world.is_stale()) see_stuns(world, safety);
        set_turn_order(world, safety);
    } catch (const std::exception& e) {
        std::printf("r%u turn order error: %s\n", cambc::round_number(), e.what());
    }
    if (!world.is_stale() && world.me().alive) {
        bool intent = support_requested;
        // support_offered was judged in the vision we had: a ward since may show a threat.
        if (world.me().type == cambc::champion_type::willow && support_offered) {
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
    comms::claim(aims.claim);
    comms::bag(world.me().alive ? static_cast<int>(my_gems()) : 0);
    if (!world.is_stale()) publish_turn_order(world, 0);
    world.note_self_health(world.me().alive ? my_health() : 0);
    upkeep.camp_turns += camp_hits() != camp_hits_before;
    debug_block({ std::printf("D %d %u %c %d %d\n", world.round, static_cast<std::uint32_t>(world.me().handle), decision, aims.farm_group, aims.claim); });
}

}
