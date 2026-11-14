// Function bodies; src/unity.cpp includes this after every header.

namespace aph {
bool camps_reach_spawn(const World& world)
{
    static int known = -1;
    if (known >= 0) return known == 1;
    known = 0;
    const auto& map = world.map();
    if (map.ally_spawn_tiles.empty()) return false;
    vec2 lo = map.ally_spawn_tiles[0], hi = lo;
    for (const vec2 t : map.ally_spawn_tiles)
        lo = {std::min(lo.x, t.x), std::min(lo.y, t.y)}, hi = {std::max(hi.x, t.x), std::max(hi.y, t.y)};
    for (const auto& g : map.groups)
        for (const auto& m : g.members)
            if (std::max({lo.x - m.pos.x, m.pos.x - hi.x, lo.y - m.pos.y, m.pos.y - hi.y, 0}) <= m.reach) known = 1;
    return known == 1;
}

}
namespace aph {
namespace steps {
bool dead(Turn& t)
{
    auto& world = t.world;
    if (!world.me().alive || bankable_bag(world, t.pathing) == 0 || retaining_gems(world, t.pathing)) t.aims.banking = false;
    if (world.me().alive) return false;
    t.aims.claim = -1;
    // The crystal first: an altar only it reaches holds our bags, and shards could spend its gold.
    buy_crystal(world, t.pathing);
    buy_shards(world); // the dead can only shop
    buy_lock();
    return true;
}

bool channel(Turn& t)
{
    // One state read covers the channels until one is cancelled; a channel excludes the others.
    t.state = my_state();
    if (t.state.contains(cambc::champion_state::teleporting)) return true;
    if (t.state.contains(cambc::champion_state::submitting_gems) && continue_tribute(t.world, t.pathing, t.safety, t.aims, t.home)) {
        if constexpr (debug_state_lines) debug_block({ note_altar(t.world); });
        return true;
    }
    return false;
}

bool errand(Turn& t)
{
    // Was: || (siege_heal_trip(t.aims, t.safety) && !recall_beats_walk(t.world, t.pathing));
    return wants_shop(t.world, t.pathing, t.safety, t.aims) || (siege_heal_trip(t.aims, t.safety) && near_home(t.world, t.pathing));
}

int retreat_score(Turn& t, int top)
{
    // Was: note_exposure(t.world); read only by the recall rules' bush test (recall_spot), off since 2026-10-28.
    if (t.state.contains(cambc::champion_state::recalling)) {
        if (keep_recall(t.world, t.pathing, t.safety, t.aims, t.home) || !drop_recall()) return top;
        t.state = my_state();
    }
    // Danger is assess's to judge (a ward prepare places may show more): until then, asked again there. An
    // errand is judged when its turn comes, after the strike search and banking (retreat()).
    return !t.assessed || t.leave ? fight_home_level : errand_level;
}

bool retreat(Turn& t)
{
    if (channelling()) {
        if constexpr (debug_state_lines) debug_block({ note_target(nearest_goal(t.world.map().ally_spawn, my_position())); });
        return true; // the recall carries us
    }
    if (t.leave) {
        aph::retreat(t.world, t.pathing, t.safety, t.aims);
        return true;
    }
    if (!errand(t)) return false;
    decision = 'S';
    t.aims.claim = -1;
    if (siege_heal_trip(t.aims, t.safety)) sieged = true; // the trip keeps the siege until home
    step_safely(t.pathing, t.pathing.to_ally_spawn(), t.safety);
    return true;
}

bool prepare(Turn& t)
{
    auto& world = t.world;
    // A ward shares the recall's channel, so this is its first chance; its sight counts this turn
    // (probe-ward-sight). Growing clusters here would starve the search: the turn end grows them.
    if (place_ward(world, t.aims, false)) {
        see_again(world, t.pathing, t.safety);
        t.home.reset();
    }
    t.on_spawn = test(world.map().ally_spawn, my_position());
    if (t.on_spawn) buy_crystal(world, t.pathing);
    if ((t.on_spawn || world.me().facts().passive == Passive::remote_shop) && buy_shards(world)) t.home.reset();
    if (t.on_spawn) buy_lock();
    return false;
}

bool idle(Turn& t)
{ return !t.world.me().can_act(t.world.round); }

bool ender(Turn& t)
{
    if (const auto* ender = game_ender(t.world)) {
        stop_game_ender(t.world, t.pathing, t.aims, *ender);
        note_target(ender->pos);
        return true;
    }
    return false;
}

bool assess(Turn& t)
{
    auto& world = t.world;
    t.willow = world.me().type == cambc::champion_type::willow;
    t.prism = world.me().type == cambc::champion_type::prism;
    // Healing needs a turn end on spawn; a recall arrives at turn start.
    // Not under an awake camp: it hits us every round, so we would mend forever while it stays awake.
    t.mend = t.on_spawn && my_health() < my_max_health() && !(camps_reach_spawn(world) && t.safety.camp_damage(my_position()) > 0);
    t.leave = !t.mend && (t.home ? *t.home : want_home(world, t.pathing, t.safety, t.aims));
    // Willow at work heals first, and the work goes on without the strike search.
    t.working = t.willow && !t.mend && !t.leave && support_work(world, t.pathing, t.safety, t.aims);
    t.strikes = !t.working && strike_possible(world);
    t.mate_eligible = false;
    t.assessed = true;
    return false;
}

bool support(Turn& t)
{
    auto& world = t.world;
    if (!t.mend && (t.prism || (t.willow && !t.leave && !t.working))
        && support_endpoint(world, t.willow ? cambc::champion_type::prism : cambc::champion_type::willow)
        && local_support(world, t.pathing, t.safety, t.aims, t.leave, t.mate_eligible))
        return true;
    if (t.willow && !t.mend && !t.leave && !t.strikes && !stunned_turn && !t.working && !t.mate_eligible && !support_retreat
        && willow_independent_heal_step(world, t.pathing, t.safety))
        return true;
    if (support_retreat) {
        heal_ally(world);
        aph::retreat(world, t.pathing, t.safety, t.aims);
        return true;
    }
    return false;
}

bool tend(Turn& t)
{
    if (!t.strikes || t.mend || t.leave) {
        heal_ally(t.world);
        if (!t.strikes || !(reset_may_kill(t.world) || landing_ready(t.world))) shield_if_needed(t.world, t.safety, t.aims.claim);
    }
    return false;
}

bool mend(Turn& t)
{
    if (!t.mend) return false;
    decision = 'H';
    if constexpr (debug_state_lines) debug_block({ note_nearest_enemy(t.world); });
    const bool attacked = attack_enemy(t.world);
    if (attacked) reset_and_attack_enemy(t.world, true);
    cast_at_enemies(t.world);
    if (attacked) reset_and_attack_enemy(t.world);
    return true;
}

bool guard(Turn& t)
{
    guard_steps(t.world, t.pathing, t.safety);
    return false;
}

int capture_score(Turn& t, int top)
{
    using C = Turn::Capture;
    if (t.capture == C::unasked) {
        t.holding = holding_capture(t.world, t.pathing) || contesting(t.world);
        t.relief = relief_landing(t.world, t.pathing, t.safety, t.aims);
        t.capture = must_yield(t.world, t.pathing, t.safety, t.aims) ? C::leave
                    : in_bounds(t.relief)                ? C::relieve
                    : t.holding                          ? C::stay
                                                         : C::go;
    }
    switch (t.capture) {
    case C::leave:
    case C::relieve: return top;
    case C::stay: return stay_level;
    case C::go: return go_level;
    default: return 0;
    }
}

Advance::Advance(Turn& t) : pathing(t.pathing), refusals(t.pathing.refusals())
{
        pathing.set_advance([&t](vec2 p) { return want_home_at(t.world, t.pathing, t.safety, t.aims, p); });
    }

Advance::~Advance()
{ pathing.set_advance(nullptr); }

bool Advance::stopped() const
{ return pathing.refusals() > refusals; }

bool capture(Turn& t)
{
    using C = Turn::Capture;
    switch (t.capture) {
    case C::leave: return step_off_capture(t.world, t.pathing, t.safety, t.aims);
    case C::relieve: return relieve_capture(t.world, t.pathing, t.aims, t.relief);
    case C::stay: {
        if constexpr (debug_state_lines) debug_block({
            if (const int g = t.world.map().group_at(my_position()); g >= 0) note_target(t.world.map().groups[g].centre);
        });
        hold_capture(t.world, t.aims, t.attacked);
        return true;
    }
    case C::go: {
        if (holding_capture(t.world, t.pathing) || contesting(t.world)) { // strike walked us onto ours
            hold_capture(t.world, t.aims, t.attacked);
            return true;
        }
        if (!my_can_move() || winning_bag(t.world)) return false;
        const Advance advance{t};
        const int g = our_capture(t.world, t.pathing);
        if (g < 0) return false;
        const auto& G = t.world.map().groups[g];
        const auto* zone = keeps_out_of_pack(t.world, t.pathing) ? pack_zone(t.world) : nullptr;
        if (!t.pathing.step_towards(G.tiles(), zone, unreachable, G.centre)) return advance.stopped();
        t.aims.farm_group = t.aims.claim = g;
        t.aims.crew = false;
        decision = 'O';
        return true;
    }
    default: return false;
    }
}

bool strike(Turn& t)
{
    auto& world = t.world;
    auto& pathing = t.pathing;
    auto& safety = t.safety;
    auto& aims = t.aims;
    t.attacked = false;
    if (t.strikes) {
        Intent intent;
        intent.anchored = t.holding;
        intent.walks = !t.holding && (retaining_gems(world, pathing) || !can_tribute_here(world));
        // A carrier's step banks a turn sooner, freeing a turn of output for the farm.
        intent.step_value = farm_step_value(world);
        // An enemy already in attack range was not worth leaving (want_home): the fight is here.
        if (enemy_within(world, my_position(), world.me().facts().attack_range())) intent.walks = false;
        // The goal most likely walks to an altar when carrying, else to the farm choice.
        intent.to_altar = bankable_bag(world, pathing) > 0 && !retaining_gems(world, pathing);
        intent.group = aims.farm_group;
        struck = true;
        const auto planned = plan_strikes(world, pathing, safety, intent);
        t.attacked = planned.attacked;
        searched = planned.searched;
        searched_at = my_position();
        searched_hit = !my_can_attack();
        if (!searched) heal_ally(world);
        // The search priced nothing against an enemy its own moves revealed.
        if (see_revealed(world, pathing, safety)) searched = false;
        // A cast the search left priced the shield at nothing, blind to the goal's coming camp hit:
        // judged here, before farm's camp reset or dash takes it.
        shield_if_needed(world, safety, aims.claim);
    }
    decision = t.holding ? 'P' : t.attacked ? 'A' : decision;
    if (!cambc::self().is_alive()) return true;
    if (!my_can_attack() || !my_can_cast()) see_stuns(world, safety), safety.refresh();
    // The guard was placed around the tile we started on: the goal steps from where the search left us.
    if (my_position() != world.me().pos && (my_can_move() || my_can_cast())) guard_steps(world, pathing, safety);
    return false;
}

bool bank(Turn& t)
{
    if (bankable_bag(t.world, t.pathing) <= 0 || retaining_gems(t.world, t.pathing)) return false;
    const Advance advance{t};
    carry_bag(t.world, t.pathing, t.safety, t.aims, t.attacked);
    return true;
}

bool spent(Turn& t)
{
    if constexpr (debug_state_lines) debug_block({ note_nearest_enemy(t.world); });
    return t.attacked && !t.world.me().facts().walk_and_attack_independent();
}

bool chase(Turn& t)
{
    const Advance advance{t};
    return aph::chase(t.world, t.pathing, t.safety) || advance.stopped();
}

bool contest(Turn& t)
{
    const Advance advance{t};
    if (!contest_capture(t.world, t.pathing, t.aims)) return advance.stopped();
    decision = 'X';
    return true;
}

bool siege(Turn& t)
{
    decision = 'F';
    if (!(t.world.map().shared_gems ? kite(t.world, t.pathing, t.aims) : aph::siege(t.world, t.pathing, t.aims))) return false;
    decision = 'G';
    return true;
}

bool farm(Turn& t)
{
    const Advance advance{t};
    aph::farm(t.world, t.pathing, t.safety, t.aims);
    if (t.aims.farm_group >= 0) note_target(t.world.map().groups[t.aims.farm_group].centre);
    return true;
}

}
}
