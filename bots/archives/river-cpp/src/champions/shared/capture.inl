// Function bodies; src/unity.cpp includes this after every header.

namespace aph {
namespace {
int allies_on(const World& world, const bitboard& tiles, int below)
{
    int n = 0;
    for (const auto& a : world.allies) n += !a.is_self && a.alive && a.visible && a.index < below && test(tiles, a.pos);
    return n;
}

bool enemy_on(const World& world, const bitboard& tiles)
{
    if (!enemy_seen(world)) return false;
    for (const auto& e : world.enemies)
        if (e.alive && e.visible && test(tiles, e.pos)) return true;
    return false;
}

int capture_share(const World& world, int g)
{
    const auto& tiles = world.map().groups[g].tiles();
    const int sharers = 1 + allies_on(world, tiles);
    const bool lowest = allies_on(world, tiles, world.me().index) == 0;
    const int gems = world.map().groups[g].gems;
    return gems / sharers + (lowest ? gems % sharers : 0);
}

bool big_group(const CampGroup& G)
{ return !G.has_monolith && G.gems >= params::big_gems; }

int holders(const CampGroup& G)
{
    if (G.has_monolith) return params::monolith_holders;
    int n = 1;
    while (n < params::big_holders && tribute_turns((G.gems + n - 1) / n) > params::tribute_window) ++n;
    return n;
}

const ChampionBelief* prism_capture_holder(const World& world, const CampGroup& G)
{
    if (G.gems <= 0 || enemy_seen(world) || enemy_on(world, G.tiles())) return nullptr;
    for (const auto& a : world.allies) {
        if (!a.alive || !a.visible || a.facts().passive != Passive::gem_focus) continue;
        const vec2 p = a.is_self ? my_position() : a.pos;
        if (!test(G.tiles(), p) || a.health < params::hurt_health_fraction * a.max_health
            || a.channel == Channel::tribute || a.channel == Channel::teleport
            || (a.channel == Channel::recall && a.channel_end_round <= world.round + 1)
            || world.score.ally + a.gems + G.gems >= static_cast<int>(cambc::constants::winning_gems)
            || rounds_left(world) <= tribute_turns(a.gems + G.gems) + world.map().width + world.map().height + endgame_margin)
            continue;
        bool pressure = false;
        for (const auto& e : world.enemies)
            pressure |= e.alive && e.age(world.round) <= params::track_horizon
                        && dist(e.pos, p) <= vision_radius + e.age(world.round);
        if (pressure) continue;
        return &a;
    }
    return nullptr;
}

bool capture_ours(const World& world, Pathing& pathing, int g)
{
    const auto& G = world.map().groups[g];
    const auto& tiles = G.tiles();
    const auto* prism = prism_capture_holder(world, G);
    if (prism && prism->is_self) return true;
    struct Claimant {
        int index;
        bool on, relieved;
        int gems, steps;
    };
    const auto before = [](const Claimant& x, const Claimant& y) {
        if (x.on != y.on) return x.on;
        if (x.on && x.relieved != y.relieved) return !x.relieved;
        if (x.on ? x.gems != y.gems : x.steps != y.steps) return x.on ? x.gems > y.gems : x.steps < y.steps;
        return x.index < y.index;
    };
    const Field* centre = pathing.centres_ready() ? pathing.from_centre(g) : nullptr;
    const auto claimant = [&](const ChampionBelief& a) {
        const vec2 p = a.is_self ? my_position() : a.pos;
        const bool on = test(tiles, p);
        int steps = 0;
        if (!on) {
            steps = centre ? centre->at(p) : dist(p, G.centre);
            if (steps == unreachable) steps = (1 << 20) + dist(p, G.centre); // past the field's cap
        }
        return Claimant{a.index, on, a.type == cambc::champion_type::heart_of_ruin, a.is_self ? static_cast<int>(my_gems()) : a.gems, steps};
    };
    const Claimant me = claimant(world.me());
    int ahead = prism ? 1 : 0;
    for (const auto& a : world.allies)
        if (!a.is_self && claims::placed(world, a) && (!prism || a.index != prism->index) && before(claimant(a), me)) ++ahead;
    return ahead < holders(G);
}

bool pays_too_late(const CampBelief& c)
{
    return c.held_since >= 0 && c.payout_round() > static_cast<int>(cambc::constants::max_rounds);
}

bool holding_capture(const World& world, Pathing& pathing)
{
    const vec2 here = my_position();
    const int g = world.map().group_at(here);
    if (g < 0 || world.camps[g].state != CampState::cleared || winning_bag(world)) return false;
    const auto& c = world.camps[g];
    if (pays_too_late(c)) return false;
    // Waiting for the payout must still leave the walk and the whole bag's tribute before the limit.
    // A bag too late to bank even now gains nothing by leaving: the hold still pays gold (a tiebreak).
    if (my_gems() > 0 && c.held_since >= 0) {
        const int walk = pathing.to_any_altar().at(here);
        if (walk != unreachable && walk + tribute_turns(my_gems()) + endgame_slack <= rounds_left(world)
            && std::max(0, c.payout_round() - world.round) + walk + tribute_turns(my_gems() + capture_share(world, g))
                       + endgame_slack > rounds_left(world))
            return false;
    }
    return !enemy_on(world, world.map().groups[g].tiles()) && capture_ours(world, pathing, g);
}

int our_capture(const World& world, Pathing& pathing)
{
    const vec2 here = my_position();
    const auto& groups = world.map().groups;
    int best = -1, best_steps = unreachable;
    for (int g = 0; g < static_cast<int>(groups.size()); ++g) {
        const auto& G = groups[g];
        const auto& c = world.camps[g];
        if (c.state != CampState::cleared || G.has_monolith || G.gems + G.gold == 0 || dist(here, G.centre) >= best_steps
            || test(G.tiles(), here) || pays_too_late(c) || enemy_on(world, G.tiles()))
            continue;
        const Field* centre = pathing.centres_ready() ? pathing.from_centre(g) : nullptr;
        const int steps = centre ? centre->at(here) : dist(here, G.centre);
        if (steps < best_steps && capture_ours(world, pathing, g)) best = g, best_steps = steps;
    }
    return best;
}

bool must_yield(const World& world, Pathing& pathing, Safety& safety, const Aims& aims)
{
    if (!my_can_move() || aims.damage > 0 || winning_bag(world)) return false;
    const auto& map = world.map();
    const int g = map.group_at(my_position());
    if (g < 0 || world.camps[g].state != CampState::cleared) return false;
    const auto* prism = prism_capture_holder(world, map.groups[g]);
    return prism && !prism->is_self && !safety.any_threat() && safety.camp_damage(prism->pos) <= 0 && !capture_ours(world, pathing, g);
}

bool step_off_capture(const World& world, Pathing& pathing, Safety& safety, Aims& aims)
{
    const vec2 here = my_position();
    const auto& map = world.map();
    const int g = map.group_at(here);
    const auto& blocked = pathing.blocked();
    for (const auto d : directions) {
        const vec2 p = here + d;
        if (!in_bounds(p) || test(map.groups[g].tiles(), p) || !test(map.standable, p)
            || test(blocked, p) || safety.camp_damage(p) > 0) continue;
        world.throw_if_stale();
        const bool moved = pathing.try_move(p);
        // Before the stale check: a turn resumed late has still made the move.
        if (moved) {
            aims.claim = aims.farm_group = -1;
            aims.crew = false;
            decision = 'F';
        }
        world.throw_if_stale();
        if (moved) return true;
    }
    return false;
}

vec2 relief_landing(const World& world, Pathing& pathing, Safety& safety, const Aims& aims)
{
    if (world.me().type != cambc::champion_type::vesper_vale || aims.banking || aims.damage > 0 || aims.claim < 0
        || !my_can_move() || !my_can_cast() || channelling() || winning_bag(world))
        return {-1, -1};
    const int g = aims.claim;
    const auto& map = world.map();
    if (g >= static_cast<int>(map.groups.size())) return {-1, -1};
    const auto& G = map.groups[g];
    const auto& c = world.camps[g];
    const vec2 here = my_position();
    if (c.state != CampState::cleared || c.state_round != world.round || c.holder != team::ally
        || G.has_monolith || G.gold <= 0 || holders(G) != 1 || test(G.tiles(), here)
        || holding_capture(world, pathing) || enemy_seen(world))
        return {-1, -1};
    for (const auto& m : G.members)
        if (!test(world.visible, m.pos)) return {-1, -1};
    const ChampionBelief* incumbent = nullptr;
    for (const auto& a : world.allies) {
        if (a.is_self || !a.alive || !a.visible || !test(G.tiles(), a.pos)) continue;
        if (incumbent || a.type != cambc::champion_type::heart_of_ruin || a.channel == Channel::tribute || a.channel == Channel::teleport
            || (a.channel == Channel::recall && a.channel_end_round <= world.round + 1))
            return {-1, -1};
        incumbent = &a;
    }
    if (!incumbent || world.score.ally + static_cast<int>(my_gems()) + incumbent->gems + G.gems
                          >= static_cast<int>(cambc::constants::winning_gems)
        || rounds_left(world) <= tribute_turns(my_gems() + G.gems) + map.width + map.height + endgame_margin
        || safety.any_threat() || safety.camp_damage(here) > 0 || safety.camp_damage(incumbent->pos) > 0)
        return {-1, -1};
    const int dash = world.me().facts().slot_of(AbilityKind::dash);
    if (dash < 0 || !world.me().ability_ready(dash, world.round) || my_cooldown(dash) > 0) return {-1, -1};
    std::optional<vec2> landing;
    int steps = unreachable;
    for (const auto p : Tiles<5 * 5>{pathing.dash_landings()}) {
        if (!test(G.tiles(), p) || !test(world.visible, p) || safety.camp_damage(p) > 0) continue;
        const int d = dist(here, p);
        if (!landing || d < steps || (d == steps && tile_index(p) < tile_index(*landing))) landing = p, steps = d;
    }
    return landing ? *landing : vec2{-1, -1};
}

bool relieve_capture(const World& world, Pathing& pathing, Aims& aims, vec2 landing)
{
    const int g = aims.claim;
    const int dash = world.me().facts().slot_of(AbilityKind::dash);
    world.throw_if_stale();
    bool cast = false;
    try {
        cast = cast_slot(dash, landing);
    } catch (const cambc::error&) {
    }
    // Aims before the stale check: a turn resumed late has still made the move.
    bool arrived = false;
    if (cast) {
        pathing.invalidate();
        arrived = my_position() == landing;
        if (arrived) {
            aims.farm_group = g;
            aims.crew = false;
            decision = 'P';
        }
    }
    world.throw_if_stale();
    if (!arrived) return false;
    debug_block({ std::printf("HANDOFF %d %d landing %d %d\n", world.round, g, landing.x, landing.y); });
    return true;
}

bool contesting(const World& world)
{
    const vec2 here = my_position();
    const int g = world.map().group_at(here);
    if (g < 0 || world.map().groups[g].gems == 0 || world.camps[g].state != CampState::cleared || winning_bag(world)) return false;
    const auto& c = world.camps[g];
    if (c.holder == team::enemy && pays_too_late(c)) return false;
    return c.holder == team::enemy || enemy_on(world, world.map().groups[g].tiles());
}

bool paying_soon(const World& world, Pathing& pathing)
{
    if (!holding_capture(world, pathing)) return false;
    const vec2 here = world.me().pos;
    int nearest = unreachable;
    for (const auto& e : world.enemies)
        if (e.alive && e.age(world.round) <= 1) nearest = std::min(nearest, dist(here, e.pos));
    const auto& c = world.camps[world.map().group_at(here)];
    return nearest > 3 && c.held_since >= 0 && c.payout_round() <= world.round + 2;
}

bool capture_recall(const World& world, Pathing& pathing, Safety& safety, Aims& aims)
{
    const vec2 here = my_position();
    if (safety.threatened(here)) return false;
    const int g = world.map().group_at(here);
    const auto& c = world.camps[g];
    if (c.holder != team::ally || c.held_since < 0) return false;
    const int payout = c.payout_round();
    const int channel = my_channel_time();
    if (world.round + channel < payout) return false;
    const auto& G = world.map().groups[g];
    const bool wins = capture_share(world, g) >= gems_short(world);
    const auto* prism = prism_capture_holder(world, G);
    if (!wins && (retaining_gems(world, pathing) || (prism && prism->is_self))) {
        if (world.me().type != cambc::champion_type::prism || !may_shop(world) || winning_bag(world)
            || closing(world, pathing) || !recall_outruns(world, safety) || enemy_on(world, G.tiles()))
            return false;
        const int back = pathing.to_ally_spawn().at(here);
        if (back == unreachable || c.state != CampState::cleared || payout < world.round) return false;
        bool seen = true;
        for (const auto& m : G.members) seen &= test(world.visible, m.pos);
        unsigned gold_in = 0;
        if (seen) {
            const int sharers = 1 + allies_on(world, G.tiles());
            const bool lowest = allies_on(world, G.tiles(), world.me().index) == 0;
            const int base = G.gold / sharers + (lowest ? G.gold % sharers : 0);
            gold_in = static_cast<unsigned>(base + (has_family(my_items(), treasure) ? base / 5 : 0));
        }
        const float value = affordable_prefix(world, gold_in).gain
                            + heal_rounds(world, my_max_health() - my_health(), spawn_steps());
        const int hurt = my_health() < my_max_health() ? 1 : 0;
        return std::isfinite(value) && value > static_cast<float>(std::max(0, channel - (payout - world.round)) + hurt + back);
    }
    const int walk = pathing.to_any_altar().at(here);
    if (walk == unreachable) return false;
    const int sharers = 1 + allies_on(world, G.tiles());
    if (!(home_trip(world, pathing, channel, wins).rounds(walk, payout - world.round, static_cast<std::uint32_t>(static_cast<float>(G.gold / sharers) * gold_paid(world))) < static_cast<float>(walk)))
        return false;
    // The ride banks the share: a payout earlier than we guessed (hold_start) finds us off the hold,
    // where recall_to_bank keeps it only for a bag already banking.
    aims.banking = true;
    return true;
}

int enemy_hold_left(const World& world, const CampBelief& c)
{
    return c.holder == team::enemy && c.held_since >= 0 ? c.payout_round() - world.round : capture_rounds();
}

bool bound_elsewhere(const World& world, const ChampionBelief& a, int g)
{
    if (a.channel == Channel::tribute) return true;
    if (a.channel == Channel::recall && visible_record(a.handle)
        && kept_recall(a.handle, a.fast_recall ? home_recall_time : static_cast<int>(cambc::constants::recall_time)))
        return true;
    return !claims::claims(world, a.index, g);
}

bool capture_taken(const World& world, int g, vec2 here)
{
    const auto& G = world.map().groups[g];
    if (const auto* prism = prism_capture_holder(world, G)) return !prism->is_self;
    int ahead = 0;
    for (const auto& a : world.allies)
        ahead += !a.is_self && a.alive && a.visible
                 && (test(G.tiles(), a.pos)
                     || ((dist(a.pos, G.centre) < dist(here, G.centre)
                          || (dist(a.pos, G.centre) == dist(here, G.centre) && a.index < world.me().index))
                         && !bound_elsewhere(world, a, g)));
    return ahead >= holders(G);
}

bool ally_claims(const World& world, int g)
{
    for (const auto& a : world.allies)
        if (!a.is_self && claims::claims(world, a.index, g)) return true;
    return false;
}

const bitboard& free_tiles(const bitboard& tiles)
{
    static bitboard free{cambc::uninitialized}, units{cambc::uninitialized};
    copy_into(tiles, free);
    occupancy_into(team::ally, units);
    drop(free, units);
    occupancy_into(team::enemy, units);
    drop(free, units);
    return free;
}

bool contest_capture(const World& world, Pathing& pathing, Aims& aims)
{
    const auto& map = world.map();
    const vec2 here = my_position();
    int best = -1, best_steps = unreachable;
    world.each_cleared([&](int g) {
        const auto& G = map.groups[g];
        const auto& c = world.camps[g];
        if (G.gems == 0 || dist(here, G.centre) > vision_radius + 2) return;
        if (!enemy_on(world, G.tiles()) && c.holder != team::enemy) return;
        const int steps = steps_to(G, here);
        if (steps > enemy_hold_left(world, c) || steps >= best_steps) return;
        best = g, best_steps = steps;
    });
    if (best < 0) return false;
    const auto& free = free_tiles(map.groups[best].tiles());
    if (free.is_empty() || !pathing.step_towards(free, nullptr, best_steps + max_detour)) return false;
    aims.claim = best;
    aims.crew = false;
    return true;
}

void hold_capture(const World& world, Aims& aims, bool attacked)
{
    const int held = world.map().group_at(my_position());
    aims.claim = held;
    aims.crew = false;
    if (attacked) return;
    const auto& groups = world.map().groups;
    const auto free_hit = [&](int g) {
        const auto& c = world.camps[g];
        return g != held && (groups[g].strength <= 0 || (c.awake != Awake::asleep && c.asleep == 0));
    };
    if (const int hit = attack_camp(world, free_hit); hit >= 0) {
        cast_at_camp(world, hit);
        reset_and_attack_camp(world, hit);
    }
}

}
}
