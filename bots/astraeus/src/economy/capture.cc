// Captures: shares, holders, handing a capture over or yielding it, contests and capture recalls.
#include "../bot_parts.h"

namespace aph {

namespace {

// Rounds from the first hold of a cleared group to its payout: `fast` when a Capture emblem's owner holds.
int capture_rounds(bool fast) { return (fast ? capture_emblem_time : cambc::constants::capture_time) + 1; }
// Ours: an ally's Capture emblem on the hold is not counted.
int capture_rounds(const World& world) { return capture_rounds(world.me().fast_capture); }

// Allies other than us in sight on `tiles`; with `below`, only those of a lower index.
int allies_on(const World& world, const bitboard& tiles, int below) {
    int n = 0;
    for (const auto& a : world.allies) n += !a.is_self && a.alive && a.visible && a.index < below && test(tiles, a.pos);
    return n;
}

bool enemy_on(const World& world, const bitboard& tiles) {
    if (!enemy_seen(world)) return false;
    for (const auto& e : world.enemies)
        if (e.alive && e.visible && test(tiles, e.pos)) return true;
    return false;
}

// Our part of the gems a capture we stand on pays: shares are floored, the lowest id gets the rest.
// Our part of `amount` split over the allies on `tiles` and us: the floor share, and the remainder
// to the lowest id.
int split_share(const World& world, const bitboard& tiles, int amount) {
    const int sharers = 1 + allies_on(world, tiles);
    const bool lowest = allies_on(world, tiles, world.me().index) == 0;
    return amount / sharers + (lowest ? amount % sharers : 0);
}

// A Prospector emblem's owner's extra on `cluster` split `sharers` ways: a part of its share, rounded down.
int prospected(int cluster, int sharers) { return cluster / sharers / prospector_part; }

int capture_share(const World& world, int g) {
    const auto& G = world.map().groups[g];
    int share = split_share(world, G.tiles(), G.gems);
    if (world.me().prospector) share += prospected(G.cluster_gems, 1 + allies_on(world, G.tiles()));
    return share;
}

// Our base gold from a capture of G, as capture_share.
int gold_share(const World& world, const CampGroup& G) {
    int share = split_share(world, G.tiles(), G.gold);
    if (world.me().prospector) share += prospected(G.cluster_gold, 1 + allies_on(world, G.tiles()));
    return share;
}

// A group other than a Monolith too big for one champion or a crew, like stampede's shared block
// of elk and gem clusters.
bool big_group(const CampGroup& G) { return !G.has_monolith && G.gems >= params::big_gems; }

// Split until each share's tribute fits the window its safety is judged over (tribute_safe).
int holders(const CampGroup& G) {
    int n = 1;
    while (n < params::big_holders && tribute_turns((G.gems + n - 1) / n, false) > params::tribute_window) ++n;
    return n;
}

// While our team captures the group (read live), the rounds to payout; else -1.
int fresh_ally_capture(const World& world, const CampGroup& group) {
    world.throw_if_stale();
    cambc::detail::camp_group_capture_state capture{};
    const int code = cambc::detail::sdk_camp_group_capture_state(group.handle, &capture);
    world.throw_if_stale();
    return code == 0 && capture.state == static_cast<std::int32_t>(cambc::map::camp_group_capture_type::ally_capturing) ? capture.timer : -1;
}

// v61, 3 picks: a healthy Tavi with a Prospector emblem on a pure-gold group in full view holds it
// alone when that pays the team more gold than sharing (each holder's bonuses read from its items).
const ChampionBelief* prospector_gold_holder(const World& world, const CampGroup& group) {
    if (!economy_three(world)) return nullptr;
    if (group.gems != 0 || group.gold <= 0 || group.strength > 0 || group.cluster_gold != group.gold) return nullptr;
    const ChampionBelief* tavi = nullptr;
    for (const auto& a : world.allies)
        if (a.type == cambc::champion_type::tavi && a.alive && a.visible && a.health >= params::hurt_health_fraction * a.max_health
            && a.channel == Channel::none && test(group.tiles(), a.is_self ? my_position() : a.pos))
            tavi = &a;
    if (!tavi) return nullptr;
    // Unlike the group's capture state, this comparison needs every holder's item bonuses.
    for (const auto& member : group.members)
        if (!test(world.visible, member.pos)) return nullptr;
    cambc::enum_map<cambc::item_type> owned;
    ok(cambc::detail::sdk_champion_items(static_cast<std::uint32_t>(tavi->handle), owned.ptr()));
    if (!has_family(owned, prospector)) return nullptr;
    const float tavi_solo = static_cast<float>(group.gold + group.gold / prospector_part) * gold_rate(tavi->facts(), owned);
    for (const auto& a : world.allies) {
        if (a.handle == tavi->handle || !a.alive || !a.visible || !test(group.tiles(), a.is_self ? my_position() : a.pos)) continue;
        ok(cambc::detail::sdk_champion_items(static_cast<std::uint32_t>(a.handle), owned.ptr()));
        const float solo = static_cast<float>(group.gold + (has_family(owned, prospector) ? group.gold / prospector_part : 0))
                           * gold_rate(a.facts(), owned);
        if (solo >= tavi_solo - 0.001f) return nullptr;
    }
    if (tavi->is_self || !test(group.tiles(), my_position())) return tavi;
    // We share Tavi's hold: yield only if the team's gold without us beats it with us.
    const int count = 1 + allies_on(world, group.tiles());
    if (count <= 1) return nullptr;
    int first = world.me().index, next = 1 << 30;
    for (const auto& a : world.allies)
        if (!a.is_self && a.alive && a.visible && test(group.tiles(), a.pos)) {
            first = std::min(first, a.index);
            next = std::min(next, a.index);
        }
    float before = 0, after = 0;
    for (const auto& a : world.allies) {
        if (!a.alive || !a.visible || !test(group.tiles(), a.is_self ? my_position() : a.pos)) continue;
        ok(cambc::detail::sdk_champion_items(static_cast<std::uint32_t>(a.handle), owned.ptr()));
        const auto gold = [&](int n, bool lowest) {
            const int share = group.gold / n + (lowest ? group.gold % n : 0);
            return static_cast<float>(share + (has_family(owned, prospector) ? share / prospector_part : 0)) * gold_rate(a.facts(), owned);
        };
        before += gold(count, a.index == first);
        if (!a.is_self) after += gold(count - 1, a.index == next);
    }
    return after > before + 0.001f ? tavi : nullptr;
}

const ChampionBelief* prism_capture_holder(const World& world, const CampGroup& G) {
    const bool three = economy_three(world);
    if (!three && G.gems <= 0) return nullptr;
    if (enemy_seen(world) || enemy_on(world, G.tiles())) return nullptr;
    if (G.gems <= 0) return prospector_gold_holder(world, G);
    // v61, 3 picks on Stellar maps: Marcella holds what Stellar cleared. Only a receiver already
    // standing on the camp can release its donor.
    if (three && map_economy(world.map()).stellar_map() && rounds_left(world) > world.map().width + world.map().height + endgame_margin) {
        bool stellar = false;
        for (const auto& a : world.allies) stellar |= a.type == cambc::champion_type::stellar;
        if (stellar)
            for (const auto& a : world.allies) {
                const vec2 p = a.is_self ? my_position() : a.pos;
                bool pressure = false;
                for (const auto& e : world.enemies)
                    pressure |= e.alive && e.age(world.round) <= params::track_horizon && dist(e.pos, p) <= vision_radius + e.age(world.round);
                if (a.type == cambc::champion_type::marcella && a.alive && a.visible && !pressure && test(G.tiles(), p)
                    && a.health >= params::hurt_health_fraction * a.max_health
                    && world.score.ally + a.gems + G.gems < static_cast<int>(cambc::constants::winning_gems) && a.channel == Channel::none)
                    return &a;
            }
    }
    for (const auto& a : world.allies) {
        if (!a.alive || !a.visible || a.facts().passive != Passive::gem_focus) continue;
        const vec2 p = a.is_self ? my_position() : a.pos;
        if (!test(G.tiles(), p) || a.health < params::hurt_health_fraction * a.max_health
            || a.channel == Channel::tribute || a.channel == Channel::teleport
            || (a.channel == Channel::recall && a.channel_end_round <= world.round + 1)
            || world.score.ally + a.gems + G.gems >= static_cast<int>(cambc::constants::winning_gems)
            || rounds_left(world) <= tribute_turns(a.gems + G.gems, a.fast_tribute) + world.map().width + world.map().height + endgame_margin)
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

// A hold whose payout falls after the last round never pays.
bool pays_too_late(const CampBelief& c) {
    return c.held_since >= 0 && c.payout_round() > static_cast<int>(cambc::constants::max_rounds);
}

// On a cleared group's tile that no lower-id ally also holds, with no enemy on any of its tiles:
// stepping off loses the capture's progress, and it pays within six rounds.
bool holding_capture(const World& world, Pathing& pathing) {
    const vec2 here = my_position();
    const int g = world.map().group_at(here);
    if (g < 0 || world.camps[g].state != CampState::cleared || winning_bag(world)) return false;
    const auto& c = world.camps[g];
    if (pays_too_late(c)) return false;
    // Waiting for the payout must still leave the walk and the whole bag's tribute before the limit.
    // A bag too late to bank even now gains nothing by leaving: the hold still pays gold (a tiebreak).
    if (my_gems() > 0 && c.held_since >= 0) {
        const int walk = pathing.to_any_altar().at(here);
        if (walk != unreachable && walk + tribute_turns(world, my_gems()) + endgame_slack <= rounds_left(world)
            && std::max(0, c.payout_round() - world.round) + walk + tribute_turns(world, my_gems() + capture_share(world, g))
                       + endgame_slack > rounds_left(world))
            return false;
    }
    const auto& tiles = world.map().groups[g].tiles();
    // Prism stays while a lower-id holder leaves; the last holder never yields to a remote ally.
    if (const auto* prism = prism_capture_holder(world, world.map().groups[g]); prism && prism->is_self) return true;
    return allies_on(world, tiles, world.me().index) < holders(world.map().groups[g]) && !enemy_on(world, tiles);
}

// Allies on cleared group g's tiles make a hold's holders already: those of lower id, if we stand on one.
bool contest_manned(const World& world, int g, vec2 here) {
    const auto& G = world.map().groups[g];
    return allies_on(world, G.tiles(), test(G.tiles(), here) ? world.me().index : 1 << 30) >= holders(G);
}

bool yield_capture(const World& world, Pathing& pathing, Safety& safety, Memory& memory) {
    if (!my_can_move() || memory.damage > 0 || winning_bag(world)) return false;
    const vec2 here = my_position();
    const auto& map = world.map();
    const int g = map.group_at(here);
    if (g < 0 || world.camps[g].state != CampState::cleared) return false;
    const auto* prism = prism_capture_holder(world, map.groups[g]);
    if (!prism || prism->is_self || safety.any_threat() || safety.camp_damage(prism->pos) > 0) return false;
    // Tavi and Marcella take over a hold: leave only once ours is counting.
    if ((prism->type == cambc::champion_type::tavi || prism->type == cambc::champion_type::marcella)
        && fresh_ally_capture(world, map.groups[g]) < 0)
        return false;
    const auto& blocked = pathing.blocked();
    for (const auto d : directions) {
        const vec2 p = here + d;
        if (!in_bounds(p) || test(map.groups[g].tiles(), p) || !test(map.standable, p)
            || test(blocked, p) || safety.camp_damage(p) > 0) continue;
        world.throw_if_stale();
        const bool moved = pathing.try_move(p);
        // Before the stale check: a turn resumed late has still made the move.
        if (moved) {
            memory.claim = memory.farm_group = -1;
            memory.crew = false;
            decision = 'F';
        }
        world.throw_if_stale();
        if (moved) return true;
    }
    return false;
}

// v61, 3 picks on Stellar maps: Marcella steps onto the gem group Stellar holds, for the hold to
// pass to her (prism_capture_holder).
bool join_marcella_capture(const World& world, Pathing& pathing, Safety& safety, Memory& memory) {
    if (!economy_three(world) || world.me().type != cambc::champion_type::marcella || !my_can_move() || channelling()
        || memory.damage > 0 || winning_bag(world) || memory.banking || enemy_seen(world)
        || rounds_left(world) <= world.map().width + world.map().height + endgame_margin
        || !map_economy(world.map()).stellar_map() || holding_capture(world, pathing))
        return false;
    const vec2 here = my_position();
    for (const auto& donor : world.allies) {
        if (donor.type != cambc::champion_type::stellar || !donor.alive || !donor.visible || donor.channel != Channel::none) continue;
        const int g = world.map().group_at(donor.pos);
        if (g < 0) continue;
        const auto& group = world.map().groups[g];
        const auto& camp = world.camps[g];
        if (group.gems <= 0 || camp.state != CampState::cleared || camp.state_round != world.round || test(group.tiles(), here)
            || safety.any_threat())
            continue;
        if (fresh_ally_capture(world, group) <= 1) continue;
        for (const auto d : directions) {
            const vec2 p = here + d;
            if (!in_bounds(p) || !test(world.visible, p) || !test(group.tiles(), p) || test(pathing.blocked(), p)
                || safety.camp_damage(p) > 0)
                continue;
            world.throw_if_stale();
            const bool moved = pathing.try_move(p);
            if (moved) {
                memory.claim = memory.farm_group = g;
                memory.crew = false;
                decision = 'P';
            }
            world.throw_if_stale();
            if (moved) return true;
        }
    }
    return false;
}

// A dasher paid more gold takes a one-holder gold capture from a higher-id ally paid less. Arrive
// before it leaves: only its actual observation of our lower-id body releases the hold.
bool take_capture_handoff(const World& world, Pathing& pathing, Safety& safety, Memory& memory) {
    if (!world.me().facts().has_dash() || memory.banking || memory.damage > 0
        || memory.round != world.round - 1 || memory.claim < 0 || memory.live_claim != memory.claim
        || !my_can_move() || !my_can_cast() || channelling() || winning_bag(world))
        return false;
    const int g = memory.claim;
    const auto& map = world.map();
    if (g >= static_cast<int>(map.groups.size())) return false;
    const auto& G = map.groups[g];
    const auto& c = world.camps[g];
    const vec2 here = my_position();
    if (c.state != CampState::cleared || c.state_round != world.round || c.holder != team::ally
        || G.has_monolith || G.gold <= 0 || holders(G) != 1 || test(G.tiles(), here)
        || holding_capture(world, pathing) || enemy_seen(world))
        return false;
    for (const auto& m : G.members)
        if (!test(world.visible, m.pos)) return false;
    const ChampionBelief* incumbent = nullptr;
    for (const auto& a : world.allies) {
        if (a.is_self || !a.alive || !a.visible || !test(G.tiles(), a.pos)) continue;
        if (incumbent || a.index <= world.me().index || gold_paid(a) >= gold_paid(world)
            || a.channel == Channel::tribute || a.channel == Channel::teleport
            || (a.channel == Channel::recall && a.channel_end_round <= world.round + 1))
            return false;
        incumbent = &a;
    }
    if (!incumbent || world.score.ally + static_cast<int>(my_gems()) + incumbent->gems + G.gems
                          >= static_cast<int>(cambc::constants::winning_gems)
        || rounds_left(world) <= tribute_turns(world, my_gems() + G.gems) + map.width + map.height + endgame_margin
        || safety.any_threat() || safety.camp_damage(here) > 0 || safety.camp_damage(incumbent->pos) > 0)
        return false;
    const int dash = world.me().facts().slot_of(AbilityKind::dash);
    if (dash < 0 || !world.me().ability_ready(dash, world.round) || my_cooldown(dash) > 0) return false;
    std::optional<vec2> landing;
    int steps = unreachable;
    for (const auto p : Tiles<5 * 5>{pathing.dash_landings()}) {
        if (!test(G.tiles(), p) || !test(world.visible, p) || safety.camp_damage(p) > 0) continue;
        const int d = dist(here, p);
        if (!landing || d < steps || (d == steps && tile_index(p) < tile_index(*landing))) landing = p, steps = d;
    }
    if (!landing) return false;
    world.throw_if_stale();
    bool cast = false;
    try {
        cast = cast_slot(dash, *landing);
    } catch (const cambc::error&) {
    }
    // Memory before the stale check: a turn resumed late has still made the move.
    bool arrived = false;
    if (cast) {
        pathing.invalidate();
        arrived = my_position() == *landing;
        if (arrived) {
            memory.farm_group = g;
            memory.crew = false;
            decision = 'P';
        }
    }
    world.throw_if_stale();
    if (!arrived) return false;
    debug_block({ std::printf("HANDOFF %d %d incumbent %d acted %d landing %d %d\n", world.round, g,
                             incumbent->index, static_cast<int>(incumbent->acted), landing->x, landing->y); });
    return true;
}

// Allies far from the group need no threat board, which costs ~400 fuel to build.
bool ally_engaged(const World& world, int group) {
    const auto& G = world.map().groups[group];
    for (const auto& a : world.allies)
        if (!a.is_self && a.alive && a.visible && dist(a.pos, G.centre) <= G.threat_radius()) return allies_on(world, G.threat()) > 0;
    return false;
}

// On a cleared group's tile worth contesting while the enemy holds it or stands on another:
// leaving lets their hold pay. One body stops their count, so a hold's holders are enough: when
// both sides stand on it, nothing pays until a fight, and the rest of us would stand idle forever.
bool contesting(const World& world) {
    const vec2 here = my_position();
    const int g = world.map().group_at(here);
    if (g < 0 || world.map().groups[g].gems == 0 || world.camps[g].state != CampState::cleared || winning_bag(world)) return false;
    const auto& c = world.camps[g];
    if (c.holder == team::enemy && pays_too_late(c)) return false;
    if (contest_manned(world, g, here)) return false;
    return c.holder == team::enemy || enemy_on(world, world.map().groups[g].tiles());
}

// Recall from a capture we hold (holding_capture), timed to land home the turn it pays: the gems
// skip the walk when an altar is nearer by way of home, and the stop heals and shops.
bool capture_recall(const World& world, Pathing& pathing, Safety& safety, Memory& memory) {
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
        if (world.me().facts().passive != Passive::gem_focus || !may_shop(world) || winning_bag(world)
            || closing(world, pathing) || !recall_outruns(world, safety) || enemy_on(world, G.tiles()))
            return false;
        const int back = pathing.to_ally_spawn().at(here);
        if (back == unreachable || c.state != CampState::cleared || payout < world.round) return false;
        bool seen = true;
        for (const auto& m : G.members) seen &= test(world.visible, m.pos);
        unsigned gold_in = 0;
        if (seen) gold_in = static_cast<unsigned>(static_cast<float>(gold_share(world, G)) * gold_paid(world));
        const float value = affordable_prefix(world, gold_in).gain
                            + heal_rounds_now(world);
        const int hurt = my_health() < my_max_health() ? 1 : 0;
        return std::isfinite(value) && value > static_cast<float>(std::max(0, channel - (payout - world.round)) + hurt + back);
    }
    const int walk = pathing.to_any_altar().at(here);
    if (walk == unreachable) return false;
    const auto gold_in = static_cast<std::uint32_t>(static_cast<float>(gold_share(world, G)) * gold_paid(world));
    if (!(home_trip(world, pathing, channel, wins).rounds(walk, payout - world.round, gold_in) < static_cast<float>(walk)))
        return false;
    // The ride banks the share: a payout earlier than we guessed (hold_start) finds us off the hold,
    // where recall_to_bank keeps it only for a bag already banking.
    memory.banking = true;
    return true;
}
// Rounds before an enemy hold pays: a body of ours on a camp tile by then stops it.
int enemy_hold_left(const World& world, const CampBelief& c) {
    return c.holder == team::enemy && c.held_since >= 0 ? c.payout_round() - world.round : capture_rounds(false);
}

// An ally that will not come to group g: tributing, on a recall kept through a turn, or working
// towards another group.
bool bound_elsewhere(const World& world, const ChampionBelief& a, int g) {
    if (a.channel == Channel::tribute) return true;
    if (a.channel == Channel::recall && visible_record(a.handle)
        && kept_recall(a.handle, a.recall_turns()))
        return true;
    const int claim = comms::claim_of(world, a.index);
    return claim >= 0 && claim != g;
}

// Allies in sight on group g's tiles, or free for it and nearer its centre than `here` (ties to
// the lower index), already make enough holders.
bool capture_taken(const World& world, int g, vec2 here) {
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

bool ally_claims(const World& world, int g) {
    for (const auto& a : world.allies)
        if (!a.is_self && comms::claim_of(world, a.index) == g) return true;
    return false;
}

// Of `tiles`, those with no champion we see on them, in a scratch board valid until the next call.
const bitboard& free_tiles(const bitboard& tiles) {
    static bitboard free{cambc::uninitialized}, units{cambc::uninitialized};
    copy_into(tiles, free);
    occupancy_into(team::ally, units);
    drop(free, units);
    occupancy_into(team::enemy, units);
    drop(free, units);
    return free;
}

// A cleared gem group in sight that the enemy holds or stands on, and that we can reach before the
// hold pays: a body of ours on one of its tiles stops the count. Its gems, denied within a few
// steps, beat any farm cycle's rate, however small the group.
bool contest_capture(const World& world, Pathing& pathing, Memory& memory) {
    const auto& map = world.map();
    const vec2 here = my_position();
    int best = -1, best_steps = unreachable;
    world.each_cleared([&](int g) {
        const auto& G = map.groups[g];
        const auto& c = world.camps[g];
        if (G.gems == 0 || dist(here, G.centre) > vision_radius + 2) return;
        if (!enemy_on(world, G.tiles()) && c.holder != team::enemy) return;
        if (contest_manned(world, g, here)) return;
        const int steps = steps_to(G, here);
        if (steps > enemy_hold_left(world, c) || steps >= best_steps) return;
        best = g, best_steps = steps;
    });
    if (best < 0) return false;
    const auto& free = free_tiles(map.groups[best].tiles());
    if (free.is_empty() || !pathing.step_towards(free, nullptr, best_steps + max_detour)) return false;
    memory.claim = best;
    memory.crew = false;
    return true;
}

// On a capture we hold or contest: the hold needs no turn, so hit another group in reach that
// cannot hit back or already does.
void hold_capture(const World& world, Memory& memory, bool attacked) {
    const int held = world.map().group_at(my_position());
    memory.claim = held;
    memory.crew = false;
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

} // namespace

} // namespace aph
