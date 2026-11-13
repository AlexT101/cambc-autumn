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
    // Willow hands captures to the other allies too (research/ideas-2026-11-07/willow.md).
    if (a.facts().heals()) return true;
    const auto* p = linked_partner(world, a);
    return p && p->alive;
}

// A healthy Prism keeps its bag for Focus with `gems` more in it: short of the win, and early enough to bank
// it later. Else the bag goes to an altar, and a hurt one leaves a hold. Read from a's visible bag and health
// and the team's score, so allies agree.
bool keeps_bag(const World& world, const ChampionBelief& a, int gems) {
    const auto& map = world.map();
    return a.facts().passive == Passive::gem_focus && a.health >= params::hurt_health_fraction * a.max_health
           && world.score.ally + a.gems + gems < static_cast<int>(cambc::constants::winning_gems)
           && rounds_left(world) > tribute_turns(a.gems + gems, a.fast_tribute) + map.width + map.height + endgame_margin;
}

// Gems one gem in a's kept bag is worth beyond itself, at `price` gems a gold: Prism's prism_focus_per_gem
// Focus a gem is what prism_focus_per_gem / growth Focus shards would buy, at shard_price gold each.
float carried_bonus(const World& world, const ChampionBelief& a, int gems, float price) {
    if (!keeps_bag(world, a, gems)) return 0.0f;
    const float shards = cambc::constants::passive_abilities::prism_focus_per_gem / a.facts().focus.growth;
    return std::max(0.0f, price) * shards * static_cast<float>(shard_price);
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

Safety* hold_safety = nullptr;
void use_hold_safety(Safety* safety) { hold_safety = safety; }

const ChampionBelief* living_carrier(const World& world);

// With an enemy in sight, whether Prism ally a's hold on the group it stands on is contested, or the
// enemies we see, a standing idle as a channel does, could kill it or take it below fit_on's health in
// the enemy turns left before the payout (hold_outlasts' window). Kept per ally while the beliefs hold:
// sole_capture_holder is asked for every group farm prices.
bool prism_hold_threatened(const World& world, const ChampionBelief& a, const CampGroup& G) {
    const vec2 at = position_of(a);
    const int g = world.map().group_at(at);
    if (g < 0 || enemy_on(world, G.tiles())) return true;
    const auto& c = world.camps[g];
    if (c.holder != team::ally) return true;
    if (!hold_safety) return true;
    struct Kept {
        int round = -1;
        std::uint32_t generation = 0, observations = 0;
        vec2 pos{-1, -1};
        bool threatened = true;
    };
    static std::array<Kept, 16> kept;
    auto& k = kept[static_cast<std::size_t>(a.index) & 15];
    if (k.round == world.round && k.generation == Safety::hold_generation() && k.observations == world.observations && k.pos == at)
        return k.threatened;
    // Short of fuel, this turn's last answer here, else none: a flip mid-turn would walk us back onto the tiles.
    if (!fuel_ok(hold_safety->fight_cost_estimate() + end_reserve)) return k.round != world.round || k.pos != at || k.threatened;
    const int rounds = c.held_since >= 0 ? std::max(0, c.payout_round() - world.round) : capture_rounds(a.fast_capture);
    const int window = rounds + 1;
    const int harm = hold_safety->turns_to_harm_idle(a, at, window + 1, params::hurt_health_fraction * a.max_health, false);
    k = {world.round, Safety::hold_generation(), world.observations, at, harm != 0 && harm <= window};
    return k.threatened;
}

// The ally that should hold G alone, the rest stepping off (yield_capture): a healthy Prism on it,
// whose Focus grows with its bag, even with an enemy out of sight who may see it, or one in sight
// that cannot hurt it before the payout (prism_hold_threatened): a second holder there only splits
// the gems; with no enemy in sight, on 3 picks, Marcella on what Stellar cleared, or a Prospector
// Tavi on a pure-gold group. Null if none.
const ChampionBelief* sole_capture_holder(const World& world, const CampGroup& G) {
    const bool seen = enemy_seen(world);
    // The carrier on a group with gold, as a Prism on gems: a second body on its tiles at the payout halves
    // what her gold bonus is paid on.
    if (const auto* a = living_carrier(world);
        a && carriable(G) && fit_on(*a, G.tiles()) && a->channel != Channel::tribute && a->channel != Channel::teleport
        && !(a->channel == Channel::recall && a->channel_end_round <= world.round + 1) && !(seen && prism_hold_threatened(world, *a, G))) {
        // Unless an ally there pays the team more on it (a Marcella on a gem-rich group): value_holder's.
        const auto* best = value_holder(world, G);
        if (!best || best == a) return a;
    }
    if (G.gems <= 0) return seen ? nullptr : prospector_gold_holder(world, G);
    const auto& map = world.map();
    const int winning = static_cast<int>(cambc::constants::winning_gems);
    // Only a receiver already standing on the camp can release its donor (join_marcella_capture).
    if (!seen && economy_three(world) && map_economy(map).stellar_map() && rounds_left(world) > map.width + map.height + endgame_margin) {
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
            || (seen && prism_hold_threatened(world, a, G)))
            continue;
        return &a;
    }
    return nullptr;
}

// The farthest walk Prism carries a capture from (farm's 'L' picks): two holds. The farther, the
// longer the group stands empty for an enemy to take, and each candidate builds a field.
int carry_reach() { return 2 * cambc::constants::capture_time; }

// Where ally a is, seen or as it posted it (comms_ally) within the last 2 rounds; in `slack` the steps
// it may have closed since (a posted tile is to within 2).
bool recent_tile(const World& world, const ChampionBelief& a, vec2& at, int& slack) {
    constexpr int recent = 2;
    if (a.visible) return at = a.pos, slack = 0, true;
    int told = -1;
    if (params::comms_ally && comms::told_ally(a.index, at, told) && told >= world.round - recent && told > a.pos_round)
        return slack = world.round - told + 2, true;
    if (a.pos_source == Source::seen && a.pos_round >= world.round - recent && in_bounds(a.pos))
        return at = a.pos, slack = world.round - a.pos_round, true;
    return false;
}

// Prism ally a's Focus is at least twice that of every living enemy Prism we have seen, where its hits
// already kill in duels about half the time: a gem's Focus more there is worth less than an ally's
// capture now. No enemy Prism, or none seen: not.
bool prism_dominant(const World& world, const ChampionBelief& a) {
    float enemy = 0;
    for (const auto& e : world.enemies)
        if (e.alive && e.facts().passive == Passive::gem_focus && e.stats_round >= 0) enemy = std::max(enemy, e.focus);
    if (!(enemy > 0)) return false;
    // Unseen, its Focus moves with the bag it posts.
    const float focus = a.visible ? a.focus
                                  : a.focus + cambc::constants::passive_abilities::prism_focus_per_gem
                                                  * static_cast<float>(comms::bag_of(world, a.index) - a.gems);
    return focus >= 2 * enemy;
}

// Rounds until Prism ally a, at `at`, can stand on cleared group g's tiles: free, its walk; busy with
// another group h (standing on its hold, else its claim), first what is left of that: a counting hold's
// payout (after its walk there), else its walk to h and a whole hold; then the walk on from h. A live or
// respawning h, whose clear or return we cannot time, is past `bound`. Past it, bound + 1 as soon as the
// crow's steps show it; -1 short of fuel for a field still to make. Once per group and round: every cleared group of
// farm's loop asks.
int prism_eta(const World& world, Pathing& pathing, int g, const ChampionBelief& a, vec2 at, int bound) {
    struct Eta {
        int round = -1, bound = -1, eta = -1;
    };
    static std::vector<Eta> etas;
    const auto& map = world.map();
    const int n = static_cast<int>(map.groups.size());
    if (static_cast<int>(etas.size()) != n) etas.assign(map.groups.size(), Eta{});
    auto& e = etas[static_cast<std::size_t>(g)];
    // A pruned bound + 1 is only a floor: a larger bound asks again.
    if (e.round == world.round && (e.eta <= e.bound || bound <= e.bound)) return e.eta;
    e.round = world.round, e.bound = bound;
    const auto& G = map.groups[g];
    int h = a.visible ? map.group_at(a.pos) : -1;
    if (h < 0 || h == g || world.camps[h].state != CampState::cleared || world.camps[h].holder != team::ally) h = comms::claim_of(world, a.index);
    if (h == g || h >= n) h = -1;
    if (h < 0) {
        if (steps_to(G, at) > bound) return e.eta = bound + 1;
        if (!pathing.group_walking_ready(g) && !fuel_ok(full_field_cost_estimate() + end_reserve)) return e.eta = -1;
        return e.eta = team_walk_to(world, pathing, g, at);
    }
    const auto& H = map.groups[h];
    const auto& ch = world.camps[h];
    if (ch.state != CampState::cleared) return e.eta = bound + 1;
    const bool counting = ch.holder == team::ally && ch.held_since >= 0;
    const int hold = counting ? ch.payout_round() - world.round : capture_rounds(a.fast_capture) - 1;
    const auto task = [&](int to_h) { return counting ? std::max(to_h, hold) : to_h + hold; };
    int on = unreachable;
    for (const auto& m : H.members) on = std::min(on, steps_to(G, m.pos));
    if (task(steps_to(H, at)) + on > bound) return e.eta = bound + 1;
    // Fuel for the fields still to make: one made already costs no search.
    const int unmade = !pathing.group_walking_ready(g) + !pathing.group_walking_ready(h);
    if (unmade > 0 && !fuel_ok(static_cast<std::uint64_t>(unmade) * full_field_cost_estimate() + end_reserve)) return e.eta = -1;
    on = unreachable;
    for (const auto& m : H.members) on = std::min(on, team_walk_to(world, pathing, g, m.pos));
    return e.eta = task(team_walk_to(world, pathing, h, at)) + on;
}

enum class Leave { no, claimed, near };

// A group's cleared episode (its geometry_version): the round we first asked of it, whether we left
// it for a Prism that had not claimed it, and whether that leave has lapsed; since when we keep off it
// for the carrier (awaits_carrier).
struct LeftRecord {
    std::uint32_t version = ~0u;
    int first = -1;
    bool left = false, lapsed = false;
    int awaited = -1;
};

// Group g's record for its present cleared episode.
LeftRecord& left_record(const World& world, int g) {
    static std::vector<LeftRecord> records;
    if (records.size() != world.map().groups.size()) records.assign(world.map().groups.size(), LeftRecord{});
    auto& left = records[static_cast<std::size_t>(g)];
    if (const auto version = world.camps[g].geometry_version; left.version != version) left = LeftRecord{version, world.round};
    return left;
}

// The team's carrier, Vesper Vale: her passive pays a third more on every capture share's gold, so a group
// with gold that one holder takes pays the team most with her alone on it at the payout (holder_value).
bool carrier(const ChampionBelief& a) { return a.facts().passive == Passive::bonus_gold; }
bool carriable(const CampGroup& G) { return G.gold > 0 && !G.has_monolith && holders(G) == 1; }
// A payout needs its holder only in its last round (rules capture.reward), and a hold counts from whoever
// first stands on a tile (capture.timing): on two tiles or more a mate begins it and she joins before it pays.
// On one tile nobody joins: it is left empty for her or kept.
bool relayed(const CampGroup& G) { return carriable(G) && G.members.size() >= 2; }

// The team's carrier by ally index, -1 for a team without one.
int carrier_index(const World& world) {
    static const int index = [&] {
        for (const auto& a : world.allies)
            if (carrier(a)) return a.index;
        return -1;
    }();
    return index;
}
const ChampionBelief* living_carrier(const World& world) {
    const int index = carrier_index(world);
    if (index < 0) return nullptr;
    const auto& a = world.allies[static_cast<std::size_t>(index)];
    return a.alive ? &a : nullptr;
}

// The steps from `from` onto a tile of G no ally in sight but `walker` stands on, given the `walk` to its nearest
// tile: a step more when a tile that near is taken, and no fewer than the crow's to a free one. The carrier and
// the mate that times a count for her both measure her way with it.
int walk_to_free(const World& world, const CampGroup& G, const ChampionBelief& walker, vec2 from, int walk) {
    int crow = unreachable;
    bool taken_near = false;
    for (const auto& m : G.members) {
        bool taken = false;
        for (const auto& a : world.allies)
            taken |= &a != &walker && a.alive && (a.is_self || a.visible) && position_of(a) == m.pos;
        const int d = dist(from, m.pos);
        if (taken) taken_near |= d <= walk;
        else crow = std::min(crow, d);
    }
    return std::max(walk + (taken_near ? 1 : 0), crow);
}

// A count of `rounds` to its payout pays the carrier alone only if she stands on a tile a turn of ours
// before it: `walk` steps off, she arrives in walk - 1 rounds (a round later once she has acted this
// round), and we step off in our next turn, at worst the round after.
bool carrier_in_time(const ChampionBelief& a, int walk, int rounds) { return walk + (a.acted ? 1 : 0) < rounds; }

// Off the carrier, no enemy in sight: cleared group g, with gold, is her claim from off its tiles (farm's
// carry picks, or her own farm choice), she is in our sight, and a count running, or begun now, would pay
// before she stands on a free tile of it. We keep off its tiles, the count reset or not begun, until one
// begun now pays her (carrier_in_time); await_carrier then begins it. A wait ends for good after
// carry_reach rounds, the longest slip she claims at, or once it is cut short. A one-tile group not yet
// held is left empty while she is in sight and on it sooner than a count of ours would pay.
bool awaits_carrier(const World& world, Pathing& pathing, int g, const LeftRecord& left) {
    const auto* a = living_carrier(world);
    if (!a || a->is_self || left.lapsed || comms::claim_of(world, a->index) != g) return false;
    const auto& G = world.map().groups[g];
    if (!carriable(G)) return false;
    const auto& c = world.camps[g];
    if (enemy_seen(world) || c.holder == team::enemy || winning_bag(world)) return false;
    if (left.awaited >= 0 && world.round - left.awaited >= carry_reach()) return false;
    const bool held = c.holder == team::ally && c.held_since >= 0, relay = relayed(G);
    if (!relay && held) return false;
    // A wait under way goes on while she is out of our sight; none begins for a carrier we cannot place.
    if (!a->visible) return relay && left.awaited >= 0;
    if (test(G.tiles(), a->pos) || held_back(world, *a, false) || a->health < params::hurt_health_fraction * a->max_health) return false;
    // A count we begin is as long as our own Capture emblem makes it.
    const int rounds = held ? c.payout_round() - world.round : capture_rounds(world);
    // Short of fuel for the walk's field, a wait under way stands: the crow's steps could end it too early, for good.
    if (!pathing.group_walking_ready(g) && !fuel_ok(full_field_cost_estimate() + end_reserve)) return relay && left.awaited >= 0;
    return carrier_in_time(*a, walk_to_free(world, G, *a, a->pos, team_walk_to(world, pathing, g, a->pos)), rounds) != relay;
}

// Off Prism, no enemy in sight: a Prism ally keeping its gems (as far as the team's tests show), healthy
// and free to walk, near cleared gem group g. Claimed by it, within carry_reach, the group is left
// (`claimed`) when even at Prism's nearest it misses the payout of our hold on it (2 rounds or more off, as
// prism_takeover asks), or of one we would begin on arrival (prism_coming's complement). Unclaimed, it
// is left (`near`) when empty or held from this round or last and Prism is due on it before the lapse
// (prism_eta), unless Prism is dominant, or reaches our hold before its payout (prism_takeover's), or
// the leave has lapsed. Left empty, Prism holds it whole. A hold we stayed on for
// Prism sure to come in time we keep: Prism held up on the way would otherwise have us leave it as it is
// about to pay.
Leave leave_for_prism(const World& world, Pathing& pathing, int g, const LeftRecord& left) {
    static int kept_group = -1, kept_since = -1;
    const auto& map = world.map();
    const auto& G = map.groups[g];
    const auto& c = world.camps[g];
    if (enemy_seen(world) || c.holder == team::enemy || winning_bag(world)) return Leave::no;
    const bool held = c.holder == team::ally && c.held_since >= 0;
    // A hold taken back after a lapse is not left again, claimed or not.
    if (held && (left.lapsed || c.payout_round() - world.round < 2 || (g == kept_group && c.held_since == kept_since))) return Leave::no;
    const int winning = static_cast<int>(cambc::constants::winning_gems);
    // Short of fuel for a walk's field, the crow's steps: no more than the walk.
    const bool walks = pathing.group_walking_ready(g) || fuel_ok(full_field_cost_estimate() + end_reserve);
    const auto walk_from = [&](vec2 p) { return walks ? team_walk_to(world, pathing, g, p) : steps_to(G, p); };
    for (const auto& a : world.allies) {
        if (a.is_self || !a.alive || a.facts().passive != Passive::gem_focus) continue;
        const bool claimed = comms::claim_of(world, a.index) == g;
        // Unclaimed, the wait runs from our first sight of it cleared; only a hold just begun is left.
        if (!claimed && (left.lapsed || world.round - left.first >= cambc::constants::capture_time || (held && c.held_since < world.round - 1)
                         || prism_dominant(world, a)))
            return Leave::no;
        if (a.visible && test(G.tiles(), a.pos)) return Leave::no; // there: sole_capture_holder's
        if (a.visible && (held_back(world, a, false) || a.health < params::hurt_health_fraction * a.max_health)) continue;
        const int bag = a.visible ? a.gems : comms::bag_of(world, a.index);
        vec2 at;
        int slack = 0;
        if (world.score.ally + bag + G.gems >= winning
            || rounds_left(world) <= tribute_turns(bag + G.gems, a.fast_tribute) + map.width + map.height + endgame_margin
            || !recent_tile(world, a, at, slack))
            continue;
        if (!claimed) {
            // Left only for a Prism due on it before the lapse would hand it back (prism_eta), from the
            // posted tile itself: its drift may go either way. A Prism that has acted this round moves
            // next round, a round later than one still to act.
            const int remaining = cambc::constants::capture_time - (world.round - left.first) - (a.visible && a.acted ? 1 : 0);
            const int eta = prism_eta(world, pathing, g, a, at, remaining);
            // Short of fuel for the field, a leave under way stands: lapsing it would hand the group back for good.
            if (eta < 0) return left.left && !held ? Leave::near : Leave::no;
            if (eta > remaining) return Leave::no;
            if (!held) return Leave::near;
            const int rounds = c.payout_round() - world.round;
            if (eta - slack >= rounds) return Leave::near;
            if (eta + slack < rounds && test(G.tiles(), my_position())) kept_group = g, kept_since = c.held_since;
            return Leave::no;
        }
        // No walk is shorter than the crow's: most groups are out of reach before a field is read.
        if (steps_to(G, at) - slack > carry_reach()) return Leave::no;
        const int walk = walk_from(at);
        if (walk - slack > carry_reach()) return Leave::no;
        // Left already, claimed now: a Prism nearer than our hold's payout would call us back to begin it.
        if (!held && left.left && !left.lapsed) return Leave::claimed;
        const int rounds = held ? c.payout_round() - world.round : capture_rounds(world) - 1 + std::max(1, walk_from(my_position()));
        if (walk - slack >= rounds) return Leave::claimed;
        if (held && walk + slack < rounds && test(G.tiles(), my_position())) kept_group = g, kept_since = c.held_since;
        return Leave::no;
    }
    return Leave::no;
}

// leave_for_prism, with each cleared episode's record. A Prism that has not claimed a group we left
// within capture_time rounds is not coming: it is ours to capture as usual, or it could stand empty
// for good. A leave cut short (an enemy in sight, Prism lost or hurt) is not resumed either: leaving
// again would have us step on and off it by turns.
bool left_for_prism(const World& world, Pathing& pathing, int g, bool cleared_now) {
    if (g < 0) return false;
    const auto& G = world.map().groups[g];
    const auto& c = world.camps[g];
    const bool gems = G.gems > 0 && world.me().facts().passive != Passive::gem_focus;
    if ((!gems && !(carrier_index(world) >= 0 && carriable(G))) || G.has_monolith || (c.state != CampState::cleared && !cleared_now)) return false;
    auto& left = left_record(world, g);
    // A wait for the carrier that ends is not resumed: the count we then begin is hers to reach, or ours.
    if (awaits_carrier(world, pathing, g, left)) {
        if (left.awaited < 0) left.awaited = world.round;
        return true;
    }
    if (left.awaited >= 0) left.lapsed = true;
    if (!gems) return false;
    const Leave leave = leave_for_prism(world, pathing, g, left);
    if (leave == Leave::near) left.left = true;
    if (leave == Leave::no && left.left) left.lapsed = true;
    return leave != Leave::no;
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
    if (!prism && left_for_prism(world, pathing, g)) return false;
    // The value holder takes the hold whatever its index; the others keep it until it is on a tile.
    if (const auto* best = prism ? nullptr : value_holder(world, G)) {
        if (best->is_self) return !enemy_on(world, G.tiles());
        if (test(G.tiles(), position_of(*best))) return false;
    }
    return allies_on(world, G.tiles(), world.me().index) < holders(G) && !enemy_on(world, G.tiles());
}

// On a cleared group's tile, among its first holders() allies by id, with no enemy on any of its
// tiles: stepping off resets the hold's count. Asked a dozen times a turn, so kept while its
// inputs hold: beliefs change only with an observation, and a kill or purchase changes our gems or gold;
// a sole Prism's threat test (prism_hold_threatened) reads Safety too.
bool holding_capture(const World& world, Pathing& pathing) {
    struct Key {
        std::uint32_t round, observations, gems, gold, generation;
        vec2 here;
        bool operator==(const Key&) const = default;
    };
    static Key last{~0u};
    static bool kept = false;
    const Key key{round_now(), world.observations, my_gems(), my_gold(), Safety::hold_generation(), my_position()};
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

// Step off a hold that sole_capture_holder gives to another ally. A group left for a Prism on its way
// (left_for_prism) is farm's to walk away from, a step towards our next work, and ours to step off only
// `after_farm`, if farm left us on it: an aimless step off first had the walk on cross back onto it.
bool yielded_sole_prism = false;
bool yielded_in_sight() { return yielded_sole_prism; }

bool yield_capture(const World& world, Pathing& pathing, Safety& safety, Memory& memory, bool after_farm) {
    yielded_sole_prism = false;
    if (!my_can_move() || winning_bag(world)) return false;
    const vec2 here = my_position();
    const auto& map = world.map();
    const int g = map.group_at(here);
    if (g < 0 || world.camps[g].state != CampState::cleared) return false;
    const auto& G = map.groups[g];
    const auto* prism = sole_capture_holder(world, G);
    const bool left = !prism && left_for_prism(world, pathing, g);
    if (left != after_farm) return false;
    // A threat out of sight keeps us on only another's hold: Prism's, or the carrier's, is no safer shared
    // (sole_capture_holder has judged the enemies in sight).
    const bool sole_prism = prism && (prism->facts().passive == Passive::gem_focus || carrier(*prism));
    // Hit, by an enemy seen or not, staying only splits the sole Prism's payout (the step guard prices the step).
    if (memory.damage > 0 && !sole_prism) return false;
    if (left) {
        if (safety.any_threat()) return false;
    } else {
        if (!prism) {
            // The value holder, once on a tile and its hold counting.
            prism = value_holder(world, G);
            if (!prism || prism->is_self || !test(G.tiles(), prism->pos) || fresh_ally_capture(world, G) < 0) return false;
        }
        if (prism->is_self || (!sole_prism && safety.any_threat()) || safety.camp_damage(prism->pos) > 0) return false;
        // Tavi and Marcella take over a hold: leave only once ours is counting.
        if ((prism->type == cambc::champion_type::tavi || prism->type == cambc::champion_type::marcella) && fresh_ally_capture(world, G) < 0)
            return false;
    }
    const auto& blocked = pathing.blocked();
    for (const auto d : directions) {
        const vec2 p = here + d;
        if (!in_bounds(p) || test(G.tiles(), p) || !test(map.standable, p) || test(blocked, p) || safety.camp_damage(p) > 0) continue;
        // After farm, its choice stands.
        if (walk_then(world, pathing, p, [&] {
                yielded_sole_prism = sole_prism && enemy_seen(world);
                if (after_farm) return;
                memory.claim = memory.farm_group = -1;
                memory.crew = false;
                decision = Branch::farm;
            }))
            return true;
    }
    // Inside a big group no step leaves it: walk out across it, still on it until the last step.
    if (sole_prism) {
        bool inside = true;
        for (const auto d : directions) inside &= !in_bounds(here + d) || test(G.tiles(), here + d) || !test(map.standable, here + d);
        if (inside && pathing.step_towards(G.adjacent(), nullptr, cambc::constants::capture_time)) {
            yielded_sole_prism = enemy_seen(world);
            memory.claim = memory.farm_group = -1;
            memory.crew = false;
            decision = Branch::farm;
            world.throw_if_stale();
            return true;
        }
    }
    return false;
}

// The group we kept off for the carrier at our last turn.
int awaited_group = -1;

// A cleared group we stand on or cleared from here that we keep off for the carrier to join (awaits_carrier): we
// wait beside its tiles, hitting what cannot hit back, and step on to begin the count once the wait ends,
// whether she is then in time or no longer coming. One mate waits: the nearest in sight (ties to the lower
// index).
bool await_carrier(const World& world, Pathing& pathing, Safety& safety, Memory& memory) {
    const int was = std::exchange(awaited_group, -1);
    if (carrier_index(world) < 0 || carrier(world.me()) || channelling() || winning_bag(world)) return false;
    const auto& map = world.map();
    const vec2 here = my_position();
    const int range = world.me().facts().attack_range();
    const bool can_move = my_can_move();
    int seen[4], n = 0;
    for (const int g : {map.group_at(here), was, memory.farm_group, memory.claim}) {
        if (g < 0 || g >= static_cast<int>(map.groups.size()) || std::find(seen, seen + n, g) != seen + n) continue;
        seen[n++] = g;
        const auto& G = map.groups[g];
        const auto& c = world.camps[g];
        if (c.state != CampState::cleared || !relayed(G)) continue;
        const int steps = steps_to(G, here);
        if (steps > range) continue;
        const bool on = steps == 0;
        if (!left_for_prism(world, pathing, g)) {
            // The wait is over: the count is ours to begin.
            if (g != was || on || steps > 1 || left_record(world, g).awaited < 0 || allies_on(world, G.tiles()) > 0
                || enemy_on(world, G.tiles()) || c.holder == team::enemy)
                continue;
            // Our step spent (a ranged hit), it is begun next turn.
            if (!can_move) {
                awaited_group = g;
                continue;
            }
            for (const auto d : directions) {
                const vec2 p = here + d;
                if (!in_bounds(p) || !test(G.tiles(), p) || test(pathing.blocked(), p) || safety.camp_damage(p) > 0) continue;
                if (walk_then(world, pathing, p, [&] {
                        memory.claim = memory.farm_group = g;
                        memory.crew = false;
                        decision = Branch::hold;
                    })) {
                    debug_block({ std::printf("CARRY BEGIN %d %u g%d waited %d\n", world.round, my_handle(), g, world.round - left_record(world, g).awaited); });
                    return true;
                }
            }
            continue;
        }
        if (left_record(world, g).awaited < 0 || safety.any_threat() || memory.damage > 0) continue;
        bool nearest = true;
        for (const auto& a : world.allies) {
            if (a.is_self || !a.alive || !a.visible || carrier(a) || held_back(world, a, false)) continue;
            const int d = steps_to(G, a.pos);
            // Only an ally that would wait too: within its own reach of the tiles, as we are.
            nearest &= d > a.facts().attack_range() || d > steps || (d == steps && a.index > world.me().index);
        }
        if (!nearest) continue;
        const auto waits = [&] {
            awaited_group = g;
            memory.farm_group = g, memory.claim = -1, memory.crew = false;
            decision = Branch::await;
        };
        bool moved = steps == 1;
        if (!can_move) {
        } else if (on) {
            for (const auto d : directions) {
                const vec2 p = here + d;
                if (!in_bounds(p) || test(G.tiles(), p) || !test(map.standable, p) || test(pathing.blocked(), p) || safety.camp_damage(p) > 0) continue;
                if ((moved = walk_then(world, pathing, p, waits))) break;
            }
        } else if (steps > 1 && fuel_ok(search_cost_estimate(steps + max_detour) + end_reserve)) {
            moved = pathing.step_towards(G.adjacent(), nullptr, steps + max_detour);
            world.throw_if_stale();
        }
        if (!moved) continue;
        hold_capture(world, memory, false);
        waits();
        debug_block({ std::printf("CARRY AWAIT %d %u g%d steps %d since %d\n", world.round, my_handle(), g, steps, left_record(world, g).awaited); });
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
            || safety.any_threat() || left_for_prism(world, pathing, g))
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
        || holding_capture(world, pathing) || enemy_seen(world) || left_for_prism(world, pathing, g))
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

// What a turn alive of ours has earned, in gems at `per_gold` a base gold: our captures' gems and gold,
// prior-weighted as gem_income_rate (shop.cc's income). Camps never regenerate (rules camps.sleep), so the
// work a carry interrupts is only put off: its rounds away cost this, not the rate of the pick left standing.
float earning_rate(const World& world, float per_gold) {
    const float turns = static_cast<float>(upkeep.turns) + prior_rounds_per_gem * income_prior_gems;
    return (income.gems + income_prior_gems + per_gold * (income.capture_gold + income_prior(world.map()).gold * income_prior_gems)) / turns;
}

// The carrier's own pick of a cleared group with gold: what her lone hold gains the team over that of the
// best mate in sight on its tiles or within its own reach of them (where it cleared it from), the holder
// it has otherwise, in gems at `price` a gold; negative with no such mate or no gain. In `mate` that
// hold's value and the mate's camp output, and whether a mate stands on a tile.
float carry_gain(const World& world, const CampGroup& G, float price, CarryMate& mate) {
    mate = {};
    bool any = false;
    for (const auto& a : world.allies) {
        if (a.is_self || !a.alive || !a.visible) continue;
        const bool on = test(G.tiles(), a.pos);
        if (!on && steps_to(G, a.pos) > a.facts().attack_range()) continue;
        if (held_back(world, a, false)) {
            if (on) return -1.0f; // cannot step off for us
            continue;
        }
        const float v = holder_value(world, a, G, price);
        if (!any || v > mate.value) mate.value = v, mate.output = camp_output(a);
        mate.on |= on, any = true;
    }
    return any ? holder_value(world, world.me(), G, price) - mate.value : -1.0f;
}

// Prism keeping its gems (keeps_gems) may hold G's capture from off its tiles: sole_capture_holder's
// tests of us, read before we get there. In `goal` the free tiles no camp hits.
bool prism_carries(const World& world, Safety& safety, const CampGroup& G, bitboard& goal) {
    if (G.gems <= 0 || G.has_monolith || enemy_seen(world) || test(G.tiles(), my_position())) return false;
    const auto& map = world.map();
    const int bag = static_cast<int>(my_gems());
    if (my_health() < params::hurt_health_fraction * my_max_health()
        || world.score.ally + bag + G.gems >= static_cast<int>(cambc::constants::winning_gems)
        || rounds_left(world) <= tribute_turns(bag + G.gems, world.me().fast_tribute) + map.width + map.height + endgame_margin
        || enemy_on(world, G.tiles()))
        return false;
    copy_into(free_tiles(G.tiles()), goal);
    bool calm = false;
    for (const auto& m : G.members) {
        if (enemy_may_see(world, m.pos)) return false;
        if (!test(goal, m.pos)) continue;
        if (safety.camp_damage(m.pos) > 0) goal.set(m.pos, false);
        else calm = true;
    }
    return calm;
}

// prism_carries an ally's counting gem capture of G: on arrival before the payout we are its sole
// holder and the allies step off (yield_capture) with the tiles never empty; after it, they have
// left it to us (left_for_prism). In `timer` the rounds to the payout.
bool prism_takeover(const World& world, Safety& safety, const CampGroup& G, int& timer, bitboard& goal) {
    if (G.gems <= 0 || G.has_monolith || enemy_seen(world) || test(G.tiles(), my_position()) || sole_capture_holder(world, G)) return false;
    bool held = false;
    for (const auto& a : world.allies) {
        if (a.is_self || !a.alive || !a.visible || !test(G.tiles(), a.pos)) continue;
        // A channel but a recall's cannot step off for us, and a recall landing now leaves the tiles.
        if (a.channel == Channel::tribute || held_back(world, a, true)) return false;
        held = true;
    }
    if (!held || !prism_carries(world, safety, G, goal)) return false;
    timer = fresh_ally_capture(world, G);
    return timer >= 2; // a walk is at least a step
}

// No ally on G's tiles is on a kept recall that lands before `round`, leaving them.
bool holders_stay(const World& world, const CampGroup& G, int round) {
    for (const auto& a : world.allies)
        if (!a.is_self && a.alive && a.visible && test(G.tiles(), a.pos) && a.channel == Channel::recall && visible_record(a.handle)
            && kept_recall(a.handle, a.recall_turns()) && a.channel_end_round <= round)
            return false;
    return true;
}

// On a cleared group's tile where another ally, Prism, is the sole holder (sole_capture_holder), or
// that we leave for one on its way (left_for_prism): ours to yield.
bool yields_to_prism(const World& world, Pathing& pathing) {
    const int g = world.map().group_at(my_position());
    if (g < 0 || world.camps[g].state != CampState::cleared) return false;
    const auto* prism = sole_capture_holder(world, world.map().groups[g]);
    return prism ? !prism->is_self && (prism->facts().passive == Passive::gem_focus || carrier(*prism)) : left_for_prism(world, pathing, g);
}

// Off its tiles: those of the cleared gem group a Prism ally in sight holds alone (sole_capture_holder),
// where a step of ours that ends would split its payout. Null if none, or if we stand on them unless `on_too`.
const bitboard* prism_hold_tiles(const World& world, bool on_too) {
    if (world.me().facts().passive == Passive::gem_focus || carrier(world.me())) return nullptr;
    for (const auto& a : world.allies) {
        if (a.is_self || !a.alive || !a.visible || (a.facts().passive != Passive::gem_focus && !carrier(a))) continue;
        const int g = world.map().group_at(a.pos);
        if (g < 0 || world.camps[g].state != CampState::cleared) return nullptr;
        const auto& G = world.map().groups[g];
        if ((!on_too && test(G.tiles(), my_position())) || sole_capture_holder(world, G) != &a) return nullptr;
        return &G.tiles();
    }
    return nullptr;
}

// Off Prism, on G's counting capture we hold (group g): a Prism ally claims it from off its tiles and
// walks there before the payout (prism_takeover).
bool prism_coming(const World& world, Pathing& pathing, const CampGroup& G, const CampBelief& c, int g) {
    if (world.me().facts().passive == Passive::gem_focus || G.gems <= 0 || c.holder != team::ally || c.held_since < 0) return false;
    for (const auto& a : world.allies) {
        if (a.is_self || !a.alive || a.facts().passive != Passive::gem_focus || comms::claim_of(world, a.index) != g) continue;
        if (a.visible && test(G.tiles(), a.pos)) return false; // there: sole_capture_holder's
        return team_walk_to(world, pathing, g, a.pos) < c.payout_round() - world.round;
    }
    return false;
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
    // Prism on the tiles or on its way takes the hold: off the recall, we yield it (yield_capture).
    if (!wins && ((prism && !prism->is_self && prism->facts().passive == Passive::gem_focus) || prism_coming(world, pathing, G, c, g)))
        return false;
    // Prism's own hold rides home only out of an enemy's possible sight, as before sole_capture_holder stopped asking.
    if (!wins && (retaining_gems(world, pathing) || (prism && prism->is_self && !enemy_may_see(world, here)))) {
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
    if (left_for_prism(world, pathing, g)) return true;
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
        return;
    }
    // No basic reaches one, but a cast may: the hold keeps us on this tile, so an excludes-walking
    // cast forgoes no walk, and a ready slot not cast now loses the round (rules abilities.cooldown).
    const vec2 here = my_position();
    // camp_cast's own group-independent test, once rather than per group.
    if (!my_can_cast() || engagement_near(world, here, world.me().facts().cast_reach())) return;
    std::array<std::pair<int, int>, 16> near; // (distance, group): groups_near's vector is reused by camp_cast
    int n = 0;
    for (int g : world.map().groups_near(here, world.me().facts().cast_reach())) {
        if (n == static_cast<int>(near.size())) break;
        // Unlike free_hit, not an unknown wake state: from cast range it may hide strikers we would wake.
        if (world.camps[g].state != CampState::alive || g == held
            || !(groups[g].strength <= 0 || (world.camps[g].awake == Awake::awake && world.camps[g].asleep == 0)))
            continue;
        int d = unreachable;
        const auto& ms = groups[g].members;
        for (std::size_t i = 0; i < ms.size(); ++i)
            if (world.camps[g].health[i] > 0) d = std::min(d, dist(here, ms[i].pos));
        if (d != unreachable) near[n++] = {d, g};
    }
    std::sort(near.begin(), near.begin() + n);
    for (int k = 0; k < n; ++k)
        if (cast_at_camp(world, near[k].second)) return;
}

} // namespace

} // namespace aph
