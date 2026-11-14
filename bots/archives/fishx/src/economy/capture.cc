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

// Split until each share's tribute fits the window its safety is judged over (tribute_safe): the
// biggest, the lowest id's, takes the remainder.
int holders(const CampGroup& G) {
    int n = 1;
    while (n < params::big_holders && tribute_turns(G.gems / n + G.gems % n, false) > params::tribute_window) ++n;
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

// Gems a gold is worth when allies compare their holds (value_holder): one number for all, so that
// every ally names the same holder. Between gold bonuses and Marcella's tribute gold it cancels
// out, the gems being common to both; it weighs a Prospector emblem's extra gems and the holders' gold efficiencies.
constexpr float holder_gold_price = 0.3f;

// An ally's gold bonuses: its items read only while it is in sight now (error 97 once our move
// lost it), else its passive's alone.
float ally_gold_paid(const World& world, const ChampionBelief& a) {
    if (a.is_self) return gold_paid(world);
    static const cambc::enum_map<cambc::item_type> none{};
    return visible_record(a.handle) ? gold_paid(a) : gold_rate(a.facts(), none);
}

// a's gold efficiency: the fight power (output x max health) its best stat's 5 shards (an emblem) add, times its
// gold rate.
float gold_efficiency(const World& world, const ChampionBelief& a) {
    const auto& f = a.facts();
    const float hp = a.max_health > 0 ? a.max_health : f.health.base;
    const float str = a.max_health > 0 ? a.strength : f.strength.base, foc = a.max_health > 0 ? a.focus : f.focus.base;
    const float p0 = std::max(1.0f, f.raw_output(str, foc)) * hp;
    float best = std::max(1.0f, f.raw_output(str + 5 * f.strength.growth, foc)) * hp;
    best = std::max(best, std::max(1.0f, f.raw_output(str, foc + 5 * f.focus.growth)) * hp);
    const float ryth = f.passive == Passive::health_strength ? cambc::constants::passive_abilities::ryth_health_strength_ratio * 5 * f.health.growth : 0.0f;
    best = std::max(best, std::max(1.0f, f.raw_output(str + ryth, foc)) * (hp + 5 * f.health.growth));
    return std::max(1.0f, best - p0) * ally_gold_paid(world, a);
}
// gold_efficiency, kept per ally until its stats or its being in sight (its gold rate) change: every purchase moves
// a stat, so the kept value is exact. Reading it afresh costs ~480 fuel an ally.
float kept_efficiency(const World& world, const ChampionBelief& a) {
    static std::array<std::array<float, 4>, 64> key{};
    static std::array<float, 64> value{};
    static std::array<bool, 64> known{};
    const int i = a.index & 63;
    const float seen = a.is_self ? 2.0f + gold_paid(world) : visible_record(a.handle) ? 1.0f : 0.0f;
    const std::array<float, 4> k{a.max_health, a.strength, a.focus, seen};
    if (!known[i] || key[i] != k) key[i] = k, value[i] = gold_efficiency(world, a), known[i] = true;
    return value[i];
}
// Each ally's gold efficiency over the mean of the living and us, by index; read once a turn (allies buy only in
// their own turns, we only with our gold).
const std::array<float, 64>& relative_efficiency(const World& world) {
    static std::array<float, 64> rel{};
    static int round = -1;
    static std::uint32_t gold = ~0u;
    if (round != world.round || gold != my_gold()) {
        round = world.round, gold = my_gold();
        // The powers (~1k) only when an efficiency or the living change: mostly they hold.
        constexpr std::size_t most = 8; // a team is at most 5
        static std::array<float, most> last_e{};
        static std::uint64_t last_counted = ~0ull;
        static std::size_t last_n = ~std::size_t{0};
        std::array<float, most> es{};
        std::uint64_t counted = 0;
        const std::size_t allies = std::min(world.allies.size(), most);
        float sum = 0;
        int n = 0;
        for (std::size_t k = 0; k < allies; ++k) {
            const auto& a = world.allies[k];
            const float e = kept_efficiency(world, a);
            es[k] = e;
            if (a.alive || a.is_self) sum += e, ++n, counted |= std::uint64_t{1} << (k & 63);
        }
        if (allies != last_n || counted != last_counted || es != last_e) {
            last_n = allies, last_counted = counted, last_e = es;
            const float mean = std::max(1e-6f, sum / static_cast<float>(std::max(1, n)));
            for (std::size_t k = 0; k < allies; ++k) rel[world.allies[k].index & 63] = std::pow(es[k] / mean, params::efficiency_power);
        }
    }
    return rel;
}

// Cassi or Issac with its partner alive: a death of either takes both bodies and both bags, so the
// pair hands a capture to any other ally there (Intercontinental Fish's pair holds ~1.7 captures by
// r300 against our ~4.7, research/fish-farm-2026-11-02.md).
bool hold_shy(const World& world, const ChampionBelief& a) {
    // Willow hands captures to the other allies too (research/notes/ideas-2026-11-07/willow.md).
    if (a.facts().heals()) return true;
    const auto* p = linked_partner(world, a);
    return p && p->alive;
}

// What a's lone hold of G pays the team, in gems at `price` a gold: its share with a Prospector
// emblem's extra, gems past the win dropped, the gold at its bonuses and Marcella's gold on the gems.
float holder_value(const World& world, const ChampionBelief& a, const CampGroup& G, float price) {
    // The team's score, not our bag (gems_short): allies must agree.
    const int room = std::max(0, static_cast<int>(cambc::constants::winning_gems) - world.score.ally);
    const int gems = std::min(G.gems + (a.prospector ? prospected(G.cluster_gems, 1, true) : 0), room);
    const int gold = G.gold + (a.prospector ? prospected(G.cluster_gold, 1, true) : 0);
    const float rate = ally_gold_paid(world, a);
    // The gold goes further on the more efficient of us: x its relative efficiency (which holds its rate again).
    const float value = static_cast<float>(gems)
                        + price * rate * (static_cast<float>(gems) * a.facts().tribute_gold_per_gem() + static_cast<float>(gold))
                              * relative_efficiency(world)[a.index & 63];
    return hold_shy(world, a) ? params::pair_hold_share * value : value;
}

// Holders of G differ in what it pays: it has gold (priced by efficiency), or gems and a has Marcella's tribute gold.
bool multiplies(const ChampionBelief& a, const CampGroup& G) { return G.gold > 0 || (G.gems > 0 && a.facts().tribute_gold_per_gem() > 0); }

// For value_holder's ties: the more hurt holds, the healthier farms.
bool holds_before(const ChampionBelief& a, float va, const ChampionBelief& b, float vb) {
    if (va > vb + 1e-3f) return true;
    if (vb > va + 1e-3f) return false;
    const float fa = a.health / std::max(1.0f, a.max_health), fb = b.health / std::max(1.0f, b.max_health);
    if (fa != fb) return fa < fb;
    return a.index < b.index;
}

// An ally that cannot take G's hold or keep it: teleporting, recalling away (not the turn-end
// recall every champion starts and cancels when unwanted), or channelling off its tiles.
bool held_back(const World& world, const ChampionBelief& a, bool on) {
    if (a.is_self) return !on && channel_held();
    if (a.channel == Channel::teleport) return true;
    if (a.channel == Channel::tribute) return !on;
    if (a.channel != Channel::recall || !visible_record(a.handle) || !kept_recall(a.handle, a.recall_turns())) return false;
    return !on || a.channel_end_round <= world.round + 1;
}

// Of the allies in sight on or beside G's tiles (us included), the one whose lone hold pays the team
// most, when at least two are there, one is a Marcella or has a gold bonus, and their holds differ
// in value: the rest step off once it stands on a tile. Null otherwise, and for groups
// of several holders.
const ChampionBelief* value_holder(const World& world, const CampGroup& G) {
    if (G.has_monolith || G.gems + G.gold <= 0 || holders(G) != 1) return nullptr;
    const ChampionBelief* best = nullptr;
    float best_value = 0, low = 0;
    int n = 0;
    bool multiplier = false;
    for (const auto& a : world.allies) {
        if (!a.alive || (!a.is_self && !a.visible)) continue;
        const vec2 p = position_of(a);
        const bool on = test(G.tiles(), p);
        if (!on && !test(G.adjacent(), p)) continue;
        if (held_back(world, a, on)) continue;
        const float v = holder_value(world, a, G, holder_gold_price);
        multiplier |= multiplies(a, G) || hold_shy(world, a);
        if (n++ == 0) low = v;
        low = std::min(low, v);
        if (!best || holds_before(a, v, *best, best_value)) best = &a, best_value = v;
    }
    return n >= 2 && multiplier && best_value > low + 1e-3f ? best : nullptr;
}

// Our hold of G would pay more than that of every ally in sight on its tiles, and a tile is free.
bool outvalues_holders(const World& world, const CampGroup& G) {
    if (G.has_monolith || G.gems + G.gold <= 0 || holders(G) != 1) return false;
    const bool multiplier = multiplies(world.me(), G);
    if (!multiplier && hold_shy(world, world.me())) return false;
    const float mine = holder_value(world, world.me(), G, holder_gold_price);
    bool any = false, shy = false;
    for (const auto& a : world.allies) {
        if (a.is_self || !a.alive || !a.visible || !test(G.tiles(), a.pos)) continue;
        if (holder_value(world, a, G, holder_gold_price) + 1e-3f >= mine) return false;
        any = true;
        shy |= hold_shy(world, a);
    }
    return any && (multiplier || shy) && !free_tiles(G.tiles()).is_empty();
}

// A visible ally with at least hurt_health_fraction of its health, on `tiles`.
bool fit_on(const ChampionBelief& a, const bitboard& tiles) {
    return a.alive && a.visible && a.health >= params::hurt_health_fraction * a.max_health && test(tiles, position_of(a));
}

// An enemy in sight sees p, or one out of sight may from a tile it may be on; one tracked no longer
// within track_horizon rounds of a sighting could be anywhere.
bool enemy_may_see(const World& world, vec2 p) {
    for (const auto& e : world.enemies) {
        if (!e.alive) continue;
        if (e.visible ? dist(e.pos, p) <= vision_radius
                      : e.tracked ? possible_within(e, p, vision_radius) : e.age(world.round) <= params::track_horizon)
            return true;
    }
    return false;
}

// A's gold from `gold` split n ways, plus the remainder if `lowest`, with the bonuses of its items.
float held_gold(const ChampionBelief& a, const cambc::enum_map<cambc::item_type>& owned, int gold, int n, bool lowest) {
    const int share = gold / n + (lowest ? gold % n : 0);
    return static_cast<float>(share + (has_family(owned, prospector) ? share / prospector_part : 0)) * gold_rate(a.facts(), owned);
}

// 3 picks: a healthy Tavi with a Prospector emblem on a pure-gold group in full view holds it
// alone when that pays the team more gold than sharing.
const ChampionBelief* prospector_gold_holder(const World& world, const CampGroup& group) {
    if (!economy_three(world)) return nullptr;
    if (group.gems != 0 || group.gold <= 0 || group.strength > 0 || group.cluster_gold != group.gold) return nullptr;
    const auto& tiles = group.tiles();
    const ChampionBelief* tavi = nullptr;
    for (const auto& a : world.allies)
        if (a.type == cambc::champion_type::tavi && !held_by_channel(a) && fit_on(a, tiles)) tavi = &a;
    if (!tavi || !visible_record(tavi->handle)) return nullptr;
    // Unlike the group's capture state, every holder's items need it in sight.
    for (const auto& member : group.members)
        if (!test(world.visible, member.pos)) return nullptr;
    cambc::enum_map<cambc::item_type> owned;
    ok(cambc::detail::sdk_champion_items(static_cast<std::uint32_t>(tavi->handle), owned.ptr()));
    if (!has_family(owned, prospector)) return nullptr;
    const float tavi_solo = held_gold(*tavi, owned, group.gold, 1, true);
    for (const auto& a : world.allies) {
        if (a.handle == tavi->handle || !a.alive || !a.visible || !test(tiles, position_of(a))) continue;
        if (!visible_record(a.handle)) return nullptr; // its items unreadable since our move
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
        if (!a.is_self && !visible_record(a.handle)) return nullptr;
        ok(cambc::detail::sdk_champion_items(static_cast<std::uint32_t>(a.handle), owned.ptr()));
        before += held_gold(a, owned, group.gold, count, a.index == first);
        if (!a.is_self) after += held_gold(a, owned, group.gold, count - 1, a.index == next);
    }
    return after > before + 0.001f ? tavi : nullptr;
}

// The ally that should hold G alone while no enemy is in sight, the rest stepping off
// (yield_capture): a healthy Prism on it, whose Focus grows with its bag; on 3 picks, Marcella on
// what Stellar cleared, or a Prospector Tavi on a pure-gold group. Null if none.
const ChampionBelief* sole_capture_holder(const World& world, const CampGroup& G) {
    if (enemy_seen(world)) return nullptr;
    if (G.gems <= 0) return prospector_gold_holder(world, G);
    const auto& map = world.map();
    const int winning = static_cast<int>(cambc::constants::winning_gems);
    // Only a receiver already standing on the camp can release its donor (join_marcella_capture).
    if (economy_three(world) && map_economy(map).stellar_map() && rounds_left(world) > map.width + map.height + endgame_margin) {
        bool stellar = false;
        for (const auto& a : world.allies) stellar |= a.type == cambc::champion_type::stellar;
        if (stellar)
            for (const auto& a : world.allies)
                if (a.type == cambc::champion_type::marcella && !held_by_channel(a) && fit_on(a, G.tiles())
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
    return nullptr;
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
    const auto* prism = sole_capture_holder(world, G);
    if (prism && prism->is_self) return true;
    // The value holder takes the hold whatever its index; the others keep it until it is on a tile.
    if (const auto* best = prism ? nullptr : value_holder(world, G)) {
        if (best->is_self) return !enemy_on(world, G.tiles());
        if (test(G.tiles(), position_of(*best))) return false;
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
    if (!my_can_move() || memory.damage > 0 || winning_bag(world)) return false;
    const vec2 here = my_position();
    const auto& map = world.map();
    const int g = map.group_at(here);
    if (g < 0 || world.camps[g].state != CampState::cleared) return false;
    const auto& G = map.groups[g];
    const auto* prism = sole_capture_holder(world, G);
    if (!prism) {
        // The value holder, once on a tile and its hold counting.
        prism = value_holder(world, G);
        if (!prism || prism->is_self || !test(G.tiles(), prism->pos) || fresh_ally_capture(world, G) < 0) return false;
    }
    if (prism->is_self || safety.any_threat() || safety.camp_damage(prism->pos) > 0) return false;
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
        if (donor.type != cambc::champion_type::stellar || !donor.alive || !donor.visible || held_by_channel(donor)) continue;
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
        if (incumbent || a.index <= world.me().index || ally_gold_paid(world, a) >= gold_paid(world)
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
            decision = Branch::hold;
        }
    }
    world.throw_if_stale();
    if (!arrived) return false;
    debug_block({ std::printf("HANDOFF %d %d incumbent %d acted %d landing %d %d\n", world.round, g,
                             incumbent->index, static_cast<int>(incumbent->acted), landing->x, landing->y); });
    return true;
}

// A Marcella, or a champion with Vesper Vale's gold bonus or more, taking over the counting ally hold
// of G: what it gains the team in gems at our gold price, the holder's share raised to ours, and in
// `timer` the rounds to the payout; negative when not ours to take. Reads no walk, so the walk's
// field is built only for a group that passes (takeover_worth adds the walk). Callers first ask
// takes_over (per turn) and may_take_over.
bool takes_over(const World& world) {
    const float bonus = 1.0f + static_cast<float>(cambc::constants::passive_abilities::vesper_vale_bonus_gold_percent) / 100.0f;
    return world.me().facts().tribute_gold_per_gem() > 0 || gold_paid(world) >= bonus - 1e-3f;
}

bool may_take_over(const World& world, const CampGroup& G) {
    return !sole_capture_holder(world, G) && !enemy_on(world, G.tiles()) && outvalues_holders(world, G);
}

float takeover_gain(const World& world, const CampGroup& G, int& timer) {
    timer = fresh_ally_capture(world, G);
    if (timer < 2) return -1; // a walk is at least a step
    const ChampionBelief* holder = nullptr;
    float held = 0;
    const float price = prices(world).per_gold;
    for (const auto& a : world.allies) {
        if (a.is_self || !a.alive || !a.visible || !test(G.tiles(), a.pos)) continue;
        if (held_back(world, a, false)) return -1; // cannot step off for us
        const float v = holder_value(world, a, G, price);
        if (!holder || v > held) holder = &a, held = v;
    }
    if (!holder) return -1;
    const float gain = holder_value(world, world.me(), G, price) - held;
    return gain > 0 ? gain : -1;
}

// takeover_gain's `gain` from `walk` steps away, plus the rounds the holder is freed at `work_rate` a
// round; and in `hold` the rounds we then hold. Negative when too near its payout.
float takeover_worth(float gain, int timer, int walk, float work_rate, int& hold) {
    if (walk < 1 || timer < walk + 1) return -1;
    hold = timer - walk;
    return gain + static_cast<float>(hold) * work_rate;
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
    if (!wins && (retaining_gems(world, pathing) || (prism && prism->is_self))) {
        // A bag kept off the altar: only Prism rides home, when the shop and heal there outweigh
        // the rounds the trip costs.
        if (world.me().facts().passive != Passive::gem_focus || !shops_at_home(world) || winning_bag(world)
            || closing(world, pathing) || !recall_outruns(safety) || enemy_on(world, G.tiles()))
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
    // where recall_to_bank keeps it only for a bag it is sure is banking.
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

// Allies in sight on group g's tiles, or free for it and a shorter walk from its tiles than `here`
// (ties to the lower index), already make enough holders. The walk is team_walk_to's, so every ally
// runs the same race.
bool capture_taken(const World& world, Pathing& pathing, int g, vec2 here) {
    const auto& G = world.map().groups[g];
    if (const auto* prism = sole_capture_holder(world, G)) return !prism->is_self;
    const int mine = team_walk_to(world, pathing, g, here);
    const auto& c = world.camps[g];
    const int payout = c.held_since >= 0 ? c.payout_round() : world.round + capture_rounds(false);
    int ahead = 0;
    for (const auto& a : world.allies) {
        if (a.is_self || !a.alive || !a.visible) continue;
        if (test(G.tiles(), a.pos)) {
            const bool leaves = held_back(world, a, true)
                                || (a.channel == Channel::recall && a.channel_end_round < payout
                                    && visible_record(a.handle) && kept_recall(a.handle, a.recall_turns()));
            ahead += !leaves;
            continue;
        }
        const int theirs = team_walk_to(world, pathing, g, a.pos);
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
        const int steps = pathing.to_group(g).at(here);
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
