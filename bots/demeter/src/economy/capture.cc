// Captures: shares, holders, handing a capture over or yielding it, contests and capture recalls.
#include "../bot_parts.h"

namespace aph {

namespace {

// Rounds from the first hold of a cleared group to its payout: `fast` when a Capture emblem's owner holds.
int capture_rounds(bool fast) { return (fast ? capture_emblem_time : cambc::constants::capture_time) + 1; }
// Ours, by our own Capture emblem: an ally's on the hold is not counted.
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

// A Prospector emblem's owner's extra on `cluster` split `sharers` ways: a part of its share, the
// remainder included when `lowest` (probe-prospector-remainder), rounded down.
int prospected(int cluster, int sharers, bool lowest) {
    return (cluster / sharers + (lowest ? cluster % sharers : 0)) / prospector_part;
}

// Our part of `amount` (`cluster` of it from cluster members) from a capture of G we stand on,
// split with the allies we see on it: the floor share, the remainder to the lowest id.
int our_share(const World& world, const CampGroup& G, int amount, int cluster) {
    const int sharers = 1 + allies_on(world, G.tiles());
    const bool lowest = allies_on(world, G.tiles(), world.me().index) == 0;
    int share = amount / sharers + (lowest ? amount % sharers : 0);
    if (world.me().prospector) share += prospected(cluster, sharers, lowest);
    return share;
}
int gem_share(const World& world, const CampGroup& G) { return our_share(world, G, G.gems, G.cluster_gems); }
// Before gold bonuses.
int gold_share(const World& world, const CampGroup& G) { return our_share(world, G, G.gold, G.cluster_gold); }

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

// Where an ally is now: ours moves within the turn.
vec2 position_of(const ChampionBelief& a) { return a.is_self ? my_position() : a.pos; }

// A visible ally with at least hurt_health_fraction of its health, on `tiles`.
bool fit_on(const ChampionBelief& a, const bitboard& tiles) {
    return a.alive && a.visible && a.health >= params::hurt_health_fraction * a.max_health && test(tiles, position_of(a));
}

// An enemy seen in the last track_horizon rounds may since have walked within sight of p.
bool enemy_may_see(const World& world, vec2 p) {
    for (const auto& e : world.enemies) {
        if (!e.alive) continue;
        const int age = e.age(world.round);
        if (age <= params::track_horizon && dist(e.pos, p) <= vision_radius + age) return true;
    }
    return false;
}

// A's gold from `gold` split n ways, plus the remainder if `lowest`, with the bonuses of its items.
float held_gold(const ChampionBelief& a, const cambc::enum_map<cambc::item_type>& owned, int gold, int n, bool lowest) {
    const int share = gold / n + (lowest ? gold % n : 0);
    return static_cast<float>(share + (has_family(owned, prospector) ? share / prospector_part : 0)) * gold_rate(a.facts(), owned);
}

// kept_recall read live without throwing: one out of our sight since we last looked reads unkept.
bool kept(const ChampionBelief& a) {
    if (a.channel != Channel::recall) return false;
    const auto* live = visible_record(a.handle);
    if (!live || !cambc::champion_state::from_bits_retain(live->state).contains(cambc::champion_state::recalling)) return false;
    std::int32_t turns = 0;
    return cambc::detail::sdk_champion_channel_time(static_cast<std::uint32_t>(a.handle), &turns) == 0 && turns < a.recall_turns() - 1;
}

// Free to hold, as far as channels go, for us or an ally in sight. Our champions start a recall at
// every turn end and cancel it next turn (start_recall), so an ally in sight nearly always reads
// recalling: only one kept through a turn is likely to complete (kept_recall).
bool unbound(const ChampionBelief& a) { return a.channel == Channel::none || (a.channel == Channel::recall && !kept(a)); }

// Still on its tile when a hold paying in round `payout` pays, as far as channels go: none, the
// recall start_recall cancels next turn, or a kept one landing no sooner (capture_recall).
bool stays_for(const ChampionBelief& a, int payout) {
    return a.channel == Channel::none || (a.channel == Channel::recall && (a.channel_end_round >= payout || !kept(a)));
}

// A Prism of ours, in sight, on `tiles`.
bool prism_on(const World& world, const bitboard& tiles) {
    for (const auto& a : world.allies)
        if (a.facts().passive == Passive::gem_focus && a.alive && (a.is_self || a.visible) && in_bounds(position_of(a))
            && test(tiles, position_of(a)))
            return true;
    return false;
}

// Ours live; a visible ally's read into a buffer the next call overwrites, none if it left our sight.
const cambc::enum_map<cambc::item_type>& items_of(const ChampionBelief& a) {
    if (a.is_self) return my_items();
    static cambc::enum_map<cambc::item_type> owned;
    if (cambc::detail::sdk_champion_items(static_cast<std::uint32_t>(a.handle), owned.ptr()) != 0)
        for (auto& n : owned) n = {};
    return owned;
}

// What holding G alone pays A in gold: the group's gold and, for Marcella, 2 a gem once she tributes
// them, with a Prospector emblem's part of the cluster members' rewards, at A's gold bonuses.
float hold_pay(const ChampionBelief& a, const cambc::enum_map<cambc::item_type>& owned, const CampGroup& G) {
    const bool extra = has_family(owned, prospector);
    const float gold = static_cast<float>(G.gold + (extra ? prospected(G.cluster_gold, 1) : 0));
    const float gems = static_cast<float>(G.gems + (extra ? prospected(G.cluster_gems, 1) : 0));
    return (gold + a.facts().tribute_gold_per_gem() * gems) * gold_rate(a.facts(), owned);
}

// The gems holding G alone brings the team: a Prospector emblem adds its part of the gem clusters'.
int hold_gems(const cambc::enum_map<cambc::item_type>& owned, const CampGroup& G) {
    return G.gems + (has_family(owned, prospector) ? prospected(G.cluster_gems, 1) : 0);
}

// Pay a holder must beat the incumbents' by to step on from `steps` away (join_paid_capture): its walk
// there and back and the incumbent's turn to step off, at about 2 gold a champion-round (a round's
// gold and gems). On the tiles already, any gain: nobody walks.
float join_margin(int steps) { return steps == 0 ? 1.0f : 10.0f * static_cast<float>(steps); }

// One holder's capture that two or more allies stand on, one having stepped on to take it
// (join_paid_capture): the one holding it pays most, by join_margin(0) over the next, bringing no
// fewer gems than any of them. The others are not holding it and walk on (yield_capture). Null if none.
const ChampionBelief* paid_capture_holder(const World& world, const CampGroup& G) {
    if (G.has_monolith || holders(G) != 1) return nullptr;
    // Members are edge-connected, so every camp tile is within members - 1 of the centre member.
    const int span = static_cast<int>(G.members.size());
    const auto on_it = [&](const ChampionBelief& a) {
        if (!a.alive || !(a.is_self || a.visible)) return false;
        const vec2 p = position_of(a);
        return in_bounds(p) && dist(p, G.centre) < span && test(G.tiles(), p);
    };
    int on = 0;
    for (const auto& a : world.allies) on += on_it(a);
    if (on < 2) return nullptr;
    const auto& map = world.map();
    const int winning = static_cast<int>(cambc::constants::winning_gems);
    const auto& c = world.camps[static_cast<std::size_t>(&G - map.groups.data())];
    const int payout = c.held_since >= 0 ? c.payout_round() : world.round + capture_rounds(false);
    const ChampionBelief* best = nullptr;
    float best_pay = 0, next_pay = -1;
    int best_gems = 0, most_gems = 0;
    for (const auto& a : world.allies) {
        if (!on_it(a)) continue;
        const auto& owned = items_of(a);
        const float pay = hold_pay(a, owned, G);
        const int gems = hold_gems(owned, G);
        most_gems = std::max(most_gems, gems);
        const int bag = a.is_self ? static_cast<int>(my_gems()) : a.gems;
        const bool eligible = fit_on(a, G.tiles()) && stays_for(a, payout) && world.score.ally + bag + G.gems < winning
                              && rounds_left(world) > tribute_turns(bag + G.gems, a.fast_tribute) + map.width + map.height + endgame_margin;
        if (!eligible) continue;
        if (!best || pay > best_pay) {
            next_pay = best ? best_pay : next_pay;
            best = &a, best_pay = pay, best_gems = gems;
        } else {
            next_pay = std::max(next_pay, pay);
        }
    }
    if (!best || best_gems < most_gems || best_pay < next_pay + join_margin(0)) return nullptr;
    return best;
}

// 3 picks: a healthy Tavi with a Prospector emblem on a pure-gold group in full view holds it
// alone when that pays the team more gold than sharing.
const ChampionBelief* prospector_gold_holder(const World& world, const CampGroup& group) {
    if (!economy_three(world)) return nullptr;
    if (group.gems != 0 || group.gold <= 0 || group.strength > 0 || group.cluster_gold != group.gold) return nullptr;
    const auto& tiles = group.tiles();
    const ChampionBelief* tavi = nullptr;
    for (const auto& a : world.allies)
        if (a.type == cambc::champion_type::tavi && a.channel == Channel::none && fit_on(a, tiles)) tavi = &a;
    if (!tavi) return nullptr;
    // Unlike the group's capture state, every holder's items need it in sight.
    for (const auto& member : group.members)
        if (!test(world.visible, member.pos)) return nullptr;
    cambc::enum_map<cambc::item_type> owned;
    ok(cambc::detail::sdk_champion_items(static_cast<std::uint32_t>(tavi->handle), owned.ptr()));
    if (!has_family(owned, prospector)) return nullptr;
    const float tavi_solo = held_gold(*tavi, owned, group.gold, 1, true);
    for (const auto& a : world.allies) {
        if (a.handle == tavi->handle || !a.alive || !a.visible || !test(tiles, position_of(a))) continue;
        ok(cambc::detail::sdk_champion_items(static_cast<std::uint32_t>(a.handle), owned.ptr()));
        if (held_gold(a, owned, group.gold, 1, true) >= tavi_solo - 0.001f) return nullptr;
    }
    if (tavi->is_self || !test(tiles, my_position())) return tavi;
    // We share Tavi's hold: yield only if the team's gold without us beats it with us. The lowest
    // id takes the remainder: `first` with us, `next` without.
    const int count = 1 + allies_on(world, tiles);
    int first = world.me().index, next = 1 << 30;
    for (const auto& a : world.allies)
        if (!a.is_self && a.alive && a.visible && test(tiles, a.pos)) {
            first = std::min(first, a.index);
            next = std::min(next, a.index);
        }
    float before = 0, after = 0;
    for (const auto& a : world.allies) {
        if (!a.alive || !a.visible || !test(tiles, position_of(a))) continue;
        ok(cambc::detail::sdk_champion_items(static_cast<std::uint32_t>(a.handle), owned.ptr()));
        before += held_gold(a, owned, group.gold, count, a.index == first);
        if (!a.is_self) after += held_gold(a, owned, group.gold, count - 1, a.index == next);
    }
    return after > before + 0.001f ? tavi : nullptr;
}

// The ally that should hold G alone while no enemy is in sight, the rest stepping off
// (yield_capture): a healthy Prism on it, whose Focus grows with its bag; on 3 picks, Marcella on
// what Stellar cleared, or a Prospector Tavi on a pure-gold group; else of two or more on it, the one
// paid most (paid_capture_holder, `by_pay`). Null if none.
const ChampionBelief* sole_capture_holder(const World& world, const CampGroup& G, bool* by_pay) {
    if (by_pay) *by_pay = false;
    if (enemy_seen(world)) return nullptr;
    const auto paid = [&]() -> const ChampionBelief* {
        const auto* a = paid_capture_holder(world, G);
        if (a && by_pay) *by_pay = true;
        return a;
    };
    if (G.gems <= 0) {
        if (const auto* tavi = prospector_gold_holder(world, G)) return tavi;
        return paid();
    }
    const auto& map = world.map();
    const int winning = static_cast<int>(cambc::constants::winning_gems);
    // Only a receiver already standing on the camp can release its donor (join_marcella_capture).
    if (economy_three(world) && map_economy(map).stellar_map() && rounds_left(world) > map.width + map.height + endgame_margin) {
        bool stellar = false;
        for (const auto& a : world.allies) stellar |= a.type == cambc::champion_type::stellar;
        if (stellar)
            for (const auto& a : world.allies)
                if (a.type == cambc::champion_type::marcella && a.channel == Channel::none && fit_on(a, G.tiles())
                    && world.score.ally + a.gems + G.gems < winning && !enemy_may_see(world, position_of(a)))
                    return &a;
    }
    for (const auto& a : world.allies) {
        if (a.facts().passive != Passive::gem_focus || !fit_on(a, G.tiles())
            || a.channel == Channel::tribute || a.channel == Channel::teleport
            || (a.channel == Channel::recall && a.channel_end_round <= world.round + 1)
            || world.score.ally + a.gems + G.gems >= winning
            || rounds_left(world) <= tribute_turns(a.gems + G.gems, a.fast_tribute) + map.width + map.height + endgame_margin
            || enemy_may_see(world, position_of(a)))
            continue;
        return &a;
    }
    return paid();
}

// A hold whose payout falls after the last round never pays.
bool pays_too_late(const CampBelief& c) {
    return c.held_since >= 0 && c.payout_round() > static_cast<int>(cambc::constants::max_rounds);
}

// An enemy hold of c, counting or begun now (a Capture emblem's at the soonest), pays in time.
bool enemy_hold_pays(const World& world, const CampBelief& c) {
    if (c.holder == team::enemy && c.held_since >= 0) return !pays_too_late(c);
    return world.round + capture_rounds(true) <= static_cast<int>(cambc::constants::max_rounds);
}

bool holding_capture_now(const World& world, Pathing& pathing, vec2 here) {
    const int g = world.map().group_at(here);
    if (g < 0 || world.camps[g].state != CampState::cleared || winning_bag(world)) return false;
    const auto& c = world.camps[g];
    if (pays_too_late(c)) return false;
    const auto& G = world.map().groups[g];
    // Waiting for the payout must still leave the walk and the whole bag's tribute before the limit.
    // A bag too late to bank even now gains nothing by leaving: the hold still pays gold (a tiebreak).
    if (my_gems() > 0 && c.held_since >= 0) {
        const int walk = pathing.to_any_altar().at(here);
        if (walk != unreachable && walk + tribute_turns(world, my_gems()) + endgame_slack <= rounds_left(world)
            && std::max(0, c.payout_round() - world.round) + walk + tribute_turns(world, my_gems() + gem_share(world, G))
                       + endgame_slack > rounds_left(world))
            return false;
    }
    // Prism stays while a lower-id holder leaves; the last holder never yields to a remote ally.
    bool by_pay = false;
    if (const auto* sole = sole_capture_holder(world, G, &by_pay)) {
        if (sole->is_self) return true;
        // An ally on it is paid more for holding it: our next work walks us off (yield_capture).
        if (by_pay) return false;
    } else if (enemy_seen(world) && !prism_on(world, G.tiles())) {
        // A sighting rules out a sole holder, but not the pay order towards one that took this hold
        // before this turn (its posted claim: a holder or a joiner): else the lowest index on it, a
        // passer-by too, would take a hold taken by pay back mid-count. A newcomer paid more is not
        // anchored here under threat: the lowest index holds, as without pay.
        if (const auto* paid = paid_capture_holder(world, G); paid && comms::claim_of(world, paid->index) == g)
            return paid->is_self && !enemy_on(world, G.tiles());
    }
    return allies_on(world, G.tiles(), world.me().index) < holders(G) && !enemy_on(world, G.tiles());
}

// On a cleared group's tile, among its first holders() allies by id, with no enemy on any of its
// tiles: stepping off resets the hold's count. Asked a dozen times a turn, so kept while its
// inputs hold: beliefs change only with an observation, and a kill or purchase changes our gems or gold.
bool holding_capture(const World& world, Pathing& pathing) {
    struct Key {
        std::uint32_t round, observations, gems, gold;
        vec2 here;
        bool operator==(const Key&) const = default;
    };
    static Key last{~0u};
    static bool kept = false;
    const Key key{round_now(), world.observations, my_gems(), my_gold(), my_position()};
    if (key == last) return kept;
    last = key;
    return kept = holding_capture_now(world, pathing, key.here);
}

// Allies on cleared group g's tiles make a hold's holders already: those of lower id, if we stand on one.
bool contest_manned(const World& world, int g, vec2 here) {
    const auto& G = world.map().groups[g];
    return allies_on(world, G.tiles(), test(G.tiles(), here) ? world.me().index : 1 << 30) >= holders(G);
}

// Walks to p, then on success runs `moved` before the stale check: a turn resumed late has still
// made the move.
template <class F>
bool walk_then(const World& world, Pathing& pathing, vec2 p, F&& moved) {
    world.throw_if_stale();
    const bool walked = pathing.try_move(p);
    if (walked) moved();
    world.throw_if_stale();
    return walked;
}

// Step off a hold that sole_capture_holder gives to another ally.
bool yield_capture(const World& world, Pathing& pathing, Safety& safety, Memory& memory) {
    const vec2 here = my_position();
    const auto& map = world.map();
    const int g = map.group_at(here);
    if (g < 0 || world.camps[g].state != CampState::cleared) return false;
    const auto& G = map.groups[g];
    bool by_pay = false;
    const auto* prism = sole_capture_holder(world, G, &by_pay);
    // One paid more holds it: we are not holding (holding_capture_now), so the turn goes on to our next
    // work, whose walk takes us off; hurt or not, we stop claiming it. A step off first, the way the
    // first free tile lies, would often cross back over the tiles and stand on them at the payout.
    if (by_pay) {
        if (!prism->is_self && (memory.claim == g || memory.farm_group == g)) {
            debug_block({ std::printf("PYIELD %d %d me %d holder %d type %d left %d mytype %d hp %.2f bag %u\n", world.round, g,
                                      world.me().index, prism->index, static_cast<int>(prism->type), fresh_ally_capture(world, G),
                                      static_cast<int>(world.me().type), static_cast<double>(my_health() / my_max_health()), my_gems()); });
            memory.claim = memory.farm_group = -1;
            memory.crew = false;
        }
        return false;
    }
    if (!my_can_move() || memory.damage > 0 || winning_bag(world)) return false;
    // A Prism's hold is left only with no enemy threat anywhere.
    if (!prism || prism->is_self || safety.any_threat() || safety.camp_damage(prism->pos) > 0) return false;
    // Tavi and Marcella take over a hold: leave only once ours is counting.
    if ((prism->type == cambc::champion_type::tavi || prism->type == cambc::champion_type::marcella) && fresh_ally_capture(world, G) < 0)
        return false;
    const auto& blocked = pathing.blocked();
    for (const auto d : directions) {
        const vec2 p = here + d;
        if (!in_bounds(p) || test(G.tiles(), p) || !test(map.standable, p) || test(blocked, p) || safety.camp_damage(p) > 0) continue;
        if (walk_then(world, pathing, p, [&] {
                memory.claim = memory.farm_group = -1;
                memory.crew = false;
                decision = Branch::farm;
            }))
            return true;
    }
    return false;
}

// 3 picks on Stellar maps: Marcella steps onto the gem group Stellar holds, for the hold to pass
// to her (sole_capture_holder).
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
        // Too near its payout for the hold to pass over.
        if (fresh_ally_capture(world, group) <= 1) continue;
        for (const auto d : directions) {
            const vec2 p = here + d;
            if (!in_bounds(p) || !test(world.visible, p) || !test(group.tiles(), p) || test(pathing.blocked(), p)
                || safety.camp_damage(p) > 0)
                continue;
            if (walk_then(world, pathing, p, [&] {
                    memory.claim = memory.farm_group = g;
                    memory.crew = false;
                    decision = Branch::hold;
                }))
                return true;
        }
    }
    return false;
}

// A one-holder capture in sight that allies hold and that holding alone pays us more than each of
// them by join_margin of our steps, bringing no fewer gems; null if none. `step`: our step there,
// onto a free tile or (two steps) next to one; `gain`: our pay over the incumbents', `net` less the
// margin; `incumbent`: the best paid one's type. Not a hold a Prism or a 3-pick role keeps, nor one an
// incumbent's channel keeps it on or takes it from.
struct PaidJoin {
    int group = -1, steps = 0, left = 0, incumbent = -1;
    vec2 step{-1, -1};
    float gain = 0, net = 0;
};
PaidJoin paid_join(const World& world, Pathing& pathing, Safety& safety) {
    const auto& map = world.map();
    const vec2 here = my_position();
    const int winning = static_cast<int>(cambc::constants::winning_gems);
    const auto& blocked = pathing.blocked();
    // A tile to stand on or walk through: free, in sight, out of every camp's reach.
    const auto open = [&](vec2 p) { return in_bounds(p) && test(world.visible, p) && !test(blocked, p) && !(safety.camp_damage(p) > 0); };
    std::array<int, 16> near{};
    int n = 0;
    for (const int g : map.groups_near(here, 2))
        if (n < static_cast<int>(near.size())) near[n++] = g;
    PaidJoin best;
    for (int i = 0; i < n; ++i) {
        const int g = near[i];
        const auto& G = map.groups[g];
        const auto& c = world.camps[g];
        if (G.has_monolith || holders(G) != 1 || c.state != CampState::cleared || c.state_round != world.round
            || test(G.tiles(), here) || world.score.ally + static_cast<int>(my_gems()) + G.gems >= winning)
            continue;
        float most = -1;
        int most_gems = 0, incumbent = -1;
        bool bound = false, passive = false;
        for (const auto& a : world.allies) {
            if (a.is_self || !a.alive || !a.visible || dist(a.pos, G.centre) >= static_cast<int>(G.members.size()) || !test(G.tiles(), a.pos))
                continue;
            // A Prism keeps its holds for its Focus, even when sole_capture_holder passes it over.
            bound |= !unbound(a) || a.facts().passive == Passive::gem_focus;
            const auto& owned = items_of(a);
            if (const float pay = hold_pay(a, owned, G); pay > most) {
                most = pay, incumbent = static_cast<int>(a.type);
                passive = (a.facts().passive == Passive::bonus_gold && G.gold > 0) || (a.facts().tribute_gold_per_gem() > 0 && G.gems > 0);
            }
            most_gems = std::max(most_gems, hold_gems(owned, G));
        }
        if (most < 0 || bound || hold_gems(my_items(), G) < most_gems) continue;
        const float gain = hold_pay(world.me(), my_items(), G) - most;
        // The incumbent's own gold passive pays on this group (Vesper's 33%, Marcella's tribute gold):
        // taking its hold only moves pay from one passive to the other, so the join clears twice the margin.
        const float scale = passive ? 2.0f : 1.0f;
        const auto margin = [&](int steps) { return join_margin(steps) * scale; };
        if (gain < margin(1) || (best.group >= 0 && gain - margin(1) <= best.net) || sole_capture_holder(world, G)) continue;
        int steps = 3;
        vec2 step{-1, -1};
        for (const auto d : directions) {
            const vec2 p = here + d;
            if (!open(p)) continue;
            if (test(G.tiles(), p)) {
                steps = 1, step = p;
                break;
            }
            if (steps == 3 && test(map.standable, p))
                for (const auto e : directions)
                    if (const vec2 q = p + e; q != here && in_bounds(q) && test(G.tiles(), q) && open(q)) {
                        steps = 2, step = p;
                        break;
                    }
        }
        if (steps > 2 || gain < margin(steps)) continue;
        // On it by the end of our turn steps - 1 rounds on, and the incumbent off in its next turn,
        // before the payout.
        const int left = fresh_ally_capture(world, G);
        if (left < steps + 1) continue;
        if (best.group < 0 || gain - margin(steps) > best.net) best = {g, steps, left, incumbent, step, gain, gain - margin(steps)};
    }
    return best;
}

// Steps towards a capture paid_join finds, as long as nothing else holds us: once we stand on it,
// paid_capture_holder names us and the incumbents walk on to their next work (yield_capture).
bool join_paid_capture(const World& world, Pathing& pathing, Safety& safety, Memory& memory) {
    // Prism keeps the holds it stands on for its Focus (sole_capture_holder), and Willow follows its mate.
    if (world.me().facts().passive == Passive::gem_focus || world.me().facts().heals()) return false;
    const auto& map = world.map();
    // Working a Monolith or big group with the team (siege; kite claims its group without memory.siege):
    // the join would leave it for the hold's rounds.
    const int claim = memory.claim;
    const bool big_work = memory.siege || (claim >= 0 && claim < static_cast<int>(map.groups.size())
                                           && (map.groups[claim].has_monolith || big_group(map.groups[claim])));
    const bool able = my_can_move() && !channelling() && !memory.banking && memory.damage <= 0 && !big_work && !winning_bag(world)
                      && !enemy_seen(world) && my_health() >= params::hurt_health_fraction * my_max_health()
                      && rounds_left(world) > map.width + map.height + endgame_margin
                      && !holding_capture(world, pathing) && !contesting(world);
    if (!able) return false;
    const auto j = paid_join(world, pathing, safety);
    if (j.group < 0) return false;
    if (!walk_then(world, pathing, j.step, [&] {
            memory.claim = memory.farm_group = j.group;
            memory.crew = false;
            decision = Branch::hold;
        }))
        return false;
    debug_block({
        const auto& G = map.groups[j.group];
        std::printf("PJOIN %d %d me %d type %d steps %d left %d gain %.0f gems %d gold %d bag %u inc %d net %.0f\n", world.round, j.group,
                    world.me().index, static_cast<int>(world.me().type), j.steps, j.left, static_cast<double>(j.gain), G.gems, G.gold, my_gems(),
                    j.incumbent, static_cast<double>(j.net));
    });
    // On the tiles: the hold needs no turn, so a hit elsewhere in reach as any holder takes.
    if (j.steps == 1) hold_capture(world, memory, false);
    return true;
}

// A dasher paid more gold takes a one-holder capture paying gold from a higher-id ally paid less.
// Arrive before it leaves: only its actual observation of our lower-id body releases the hold.
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
    // Paid more for holding it (Marcella's tribute gold, a Prospector's clusters), the incumbent keeps the hold
    // (paid_capture_holder): we would only land beside it.
    if (hold_pay(*incumbent, items_of(*incumbent), G) >= hold_pay(world.me(), my_items(), G) + join_margin(0)) return false;
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
            decision = Branch::hold;
        }
    }
    world.throw_if_stale();
    if (!arrived) return false;
    debug_block({ std::printf("HANDOFF %d %d incumbent %d acted %d landing %d %d\n", world.round, g,
                             incumbent->index, static_cast<int>(incumbent->acted), landing->x, landing->y); });
    return true;
}

// Another ally stands where the group's monsters reach. The radius test skips building the
// threat board (~400 fuel) while every ally is far.
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
    if (!enemy_hold_pays(world, c)) return false;
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
    const bool wins = gem_share(world, G) >= gems_short(world);
    const auto* prism = sole_capture_holder(world, G);
    if (!wins && (retaining_gems(world, pathing) || (prism && prism->is_self && prism->facts().passive == Passive::gem_focus))) {
        // A bag kept off the altar: only Prism rides home, when the shop and heal there outweigh
        // the rounds the trip costs.
        if (world.me().facts().passive != Passive::gem_focus || !shops_at_home(world) || winning_bag(world)
            || closing(world, pathing) || !recall_outruns(world, safety) || enemy_on(world, G.tiles()))
            return false;
        const int back = pathing.to_ally_spawn().at(here);
        if (back == unreachable || payout < world.round) return false;
        bool seen = true;
        for (const auto& m : G.members) seen &= test(world.visible, m.pos);
        unsigned gold_in = 0;
        if (seen) gold_in = static_cast<unsigned>(static_cast<float>(gold_share(world, G)) * gold_paid(world));
        const float value = affordable_prefix(world, gold_in).gain + heal_rounds_now(world);
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
    if (a.channel == Channel::recall && visible_record(a.handle) && kept_recall(a.handle, a.recall_turns())) return true;
    const int claim = comms::claim_of(world, a.index);
    return claim >= 0 && claim != g;
}

// Allies in sight on group g's tiles, or free for it and nearer its centre than `here` (ties to
// the lower index), already make enough holders.
bool capture_taken(const World& world, int g, vec2 here) {
    const auto& G = world.map().groups[g];
    if (const auto* prism = sole_capture_holder(world, G)) return !prism->is_self;
    const int mine = dist(here, G.centre);
    int ahead = 0;
    for (const auto& a : world.allies) {
        if (a.is_self || !a.alive || !a.visible) continue;
        if (test(G.tiles(), a.pos)) {
            ++ahead;
            continue;
        }
        const int theirs = dist(a.pos, G.centre);
        ahead += (theirs < mine || (theirs == mine && a.index < world.me().index)) && !bound_elsewhere(world, a, g);
    }
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
        if (!enemy_hold_pays(world, c) || contest_manned(world, g, here)) return;
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
