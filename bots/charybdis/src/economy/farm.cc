// The farm loop: which group to work next, and the walk and hits towards it.
#include "../bot_parts.h"
#include <wasm_simd128.h>

namespace aph {

namespace {

constexpr float stickiness = 1.2f;
// pack_zone's cost with a bag at stake: p50 0.7k, p99 3.3k, at most ~10k (wa maps, real budget).
constexpr std::uint64_t pack_zone_cost_bound = 3500;

// Pathing::attack_tiles once prepared, null if preparing could take the fuel below `floor()`.
// Member tiles are static once prepared, so the union is kept while the same members live.
struct KeptAttackTiles {
    int group = -1, range = -1;
    std::uint32_t version = 0;
    CampState state = CampState::alive;
    bitboard tiles;
};
KeptAttackTiles kept_attack_tiles;

bool attack_tiles_kept(const World& world, int group, int range) {
    const auto& kept = kept_attack_tiles;
    const auto& c = world.camps[group];
    // A non-alive group can retain positive unseen health, which attack_tiles still reads.
    return kept.group == group && kept.range == range
           && kept.version == (c.state == CampState::alive ? c.geometry_version : c.version) && kept.state == c.state;
}

// What farm_attack_tiles would spend decoding drafted tiles not decoded yet (measured on a bushy
// map's first turn: indexing a block ~8k, each member ~2k); undrafted tiles are prepared within
// its own floor.
std::uint64_t attack_tiles_cost(const World& world, Pathing& pathing, int group, int range) {
    if (group < 0 || group >= static_cast<int>(world.camps.size()) || world.camps[group].state == CampState::cleared) return 0;
    if (attack_tiles_kept(world, group, range) || !world.map().attack_tiles_drafted(group, range)) return 0;
    std::uint64_t cost = world.map().attack_tiles_indexed(group) ? 0 : 9000;
    const auto& health = world.camps[group].health;
    for (int i = 0; i < static_cast<int>(health.size()); ++i)
        if (health[i] > 0 && !pathing.attack_tiles_ready(group, i, range)) cost += 2500;
    return cost;
}

// No group's attack_tiles_cost is higher.
std::uint64_t attack_tiles_cost_bound(const StaticMap& map) {
    static std::uint64_t bound = 0;
    if (bound == 0) {
        std::size_t most = 0;
        for (const auto& g : map.groups) most = std::max(most, g.members.size());
        bound = 9000 + 2500 * most;
    }
    return bound;
}

template <class Floor>
[[gnu::noinline]] const bitboard* farm_attack_tiles(const World& world, Pathing& pathing, int group, int range, Floor floor) {
    auto& kept = kept_attack_tiles;
    if (attack_tiles_kept(world, group, range)) return &kept.tiles;
    // Drafted tiles need no preparing, and asking per member costs ~130 each.
    if (!world.map().attack_tiles_drafted(group, range) && !pathing.prepare_attack_tiles(group, range, floor())) return nullptr;
    pathing.attack_tiles(group, range, kept.tiles);
    kept.group = group, kept.range = range;
    kept.version = world.camps[group].state == CampState::alive ? world.camps[group].geometry_version : world.camps[group].version;
    kept.state = world.camps[group].state;
    return &kept.tiles;
}

// After our attack killed a group's last monster, walk onto a free camp tile of it within a step,
// unless allies in sight already hold it (holders: more would only split the gems).
bool step_onto_cleared(const World& world, Pathing& pathing, int g) {
    if (!my_can_move()) return false;
    const auto& G = world.map().groups[g];
    for (std::size_t i = 0; i < G.members.size(); ++i) {
        try {
            if (G.camp(static_cast<int>(i)).is_alive()) return false;
        } catch (const cambc::error&) {
            return false;
        }
    }
    // Our belief has the group alive still: the SDK's reads above find it cleared.
    if (sole_capture_holder(world, G) || (allies_on(world, G.tiles()) >= holders(G) && !outvalues_holders(world, G))
        || left_for_prism(world, pathing, g, true))
        return false;
    const vec2 here = my_position();
    for (const auto d : directions)
        if (in_bounds(here + d) && test(G.tiles(), here + d) && pathing.try_move(here + d)) return true;
    return false;
}

// A step off `here` onto a free tile off camp tiles and `avoid`.
bool step_aside(const World& world, Pathing& pathing, vec2 here, const bitboard* avoid) {
    if (!my_can_move()) return false;
    const auto& walls = pathing.blocked();
    std::array<vec2, 8> tiles;
    int n = 0;
    for (const auto d : directions)
        if (const vec2 p = here + d; in_bounds(p) && test(world.map().standable, p) && !test(walls, p) && !(avoid && test(*avoid, p))) tiles[n++] = p;
    for (int i = 0; i < n; ++i)
        if (pathing.try_move(tiles[i])) return true;
    return false;
}

// The approach to a farm choice: onto its tiles once cleared, else into attack range.
int walk_range(const World& world, int g) {
    return g >= 0 && g < static_cast<int>(world.camps.size()) && world.camps[g].state != CampState::cleared
               ? world.me().facts().attack_range()
               : 0;
}

// G when a walk to it is to be searched, else -1.
int walk_target(const World& world, Pathing& pathing, int g) {
    if (g < 0 || g >= static_cast<int>(world.camps.size()) || !world.me().alive || channel_held()
        || (world.map().any_group_hop() && beyond_walk(world, pathing, g)))
        return -1;
    return g;
}

// No walk of ours from here reaches the group: only a recall out of our pocket or the crystal's hop
// into its region (StaticMap::group_hop) do.
bool beyond_walk(const World& world, Pathing& pathing, int g) {
    const auto& map = world.map();
    const vec2 here = my_position();
    const int h = map.group_hop(g);
    if (h >= 0 && test(map.hops()[h].pocket, here)) return false;
    if (!pathing.on_foot(here)) return true;
    if (!map.any_group_hop()) return false;
    static std::vector<signed char> on_foot; // by group, -1 until read: our static walls never change
    if (on_foot.size() != map.groups.size()) on_foot.assign(map.groups.size(), -1);
    if (on_foot[g] < 0) {
        static bitboard both{cambc::uninitialized};
        and_into(map.groups[g].tiles(), pathing.foot(), both);
        on_foot[g] = !board_empty(both);
    }
    return !on_foot[g];
}

// Farm's spell clear (spell_clear_rounds): from a tile within ability range of a live attacker of
// the group but out of every attacker's reach, casting at the attackers, with basic attacks on
// what cannot hit back. False with no such tile or way to one, for the usual approach.
bool spell_clear(const World& world, Pathing& pathing, int g, const bitboard* zone, int cap) {
    const auto& G = world.map().groups[g];
    const auto& c = world.camps[g];
    static bitboard reach{cambc::uninitialized}, goals{cambc::uninitialized};
    reach.clear();
    // Targets only among the first 32 members (the mask's width), but every member's reach is avoided.
    std::uint32_t attackers = 0;
    for (std::size_t i = 0; i < G.members.size(); ++i)
        if (c.health[i] > 0 && G.members[i].strength > 0) {
            if (i < 32) attackers |= 1u << i;
            reach.draw_chebyshev(G.members[i].pos, static_cast<float>(G.members[i].reach));
        }
    if (!attackers) return false;
    if (!pathing.prepare_member_tiles(g, ability_range, attackers, end_reserve)) {
        note_shortcut("spell-clear-no-tiles");
        return false;
    }
    goals.clear();
    for (std::size_t i = 0; i < G.members.size() && i < 32; ++i)
        if (attackers >> i & 1) goals |= pathing.member_attack_tiles(g, static_cast<int>(i), ability_range);
    drop(goals, reach);
    if (zone) drop(goals, *zone);
    if (goals.is_empty()) return false;
    const auto hit = [&]() __attribute__((always_inline)) {
        cast_at_camp(world, g, true);
        attack_camp(world, [&](int h) { return h == g || world.map().groups[h].strength <= 0; });
        reset_and_attack_camp(world, g);
    };
    if (test(goals, my_position())) {
        hit();
        return true;
    }
    if (zone) reach |= *zone;
    if (!pathing.step_towards(goals, &reach, cap, G.centre)) return false;
    if (!test(reach, my_position())) hit();
    return true;
}

// Our spawn tiles' bounding box, read once.
std::pair<vec2, vec2> ally_spawn_box(const StaticMap& map) {
    static std::optional<std::pair<vec2, vec2>> box;
    if (!box) {
        vec2 lo{map.width, map.height}, hi{-1, -1};
        for (const auto p : map.ally_spawn_tiles) {
            lo.x = std::min(lo.x, p.x), lo.y = std::min(lo.y, p.y);
            hi.x = std::max(hi.x, p.x), hi.y = std::max(hi.y, p.y);
        }
        box.emplace(lo, hi);
    }
    return *box;
}

// Chebyshev steps from p to the group's nearest camp tile.
int steps_to(const CampGroup& G, vec2 p) {
    int steps = unreachable;
    for (const auto& m : G.members) steps = std::min(steps, dist(p, m.pos));
    return steps;
}

// Walking steps from p onto the group's nearest camp tile; steps_to where no walk reaches it.
int walk_to(const World& world, Pathing& pathing, int g, vec2 p) {
    const int steps = pathing.to_group(g).at(p);
    return steps != unreachable ? steps : steps_to(world.map().groups[g], p);
}

// walk_to on foot alone, the same field for every ally: for comparing our walk with theirs.
int team_walk_to(const World& world, Pathing& pathing, int g, vec2 p) {
    const int steps = pathing.to_group_walking(g).at(p);
    return steps != unreachable ? steps : steps_to(world.map().groups[g], p);
}

// Our farm choice or claim, cleared this turn and short of holders, goes to the nearest of the
// allies in sight claiming it (ties to the lower index), so the others move on rather than split
// the share. Before anything else farm does, since a ranged hit in passing would cost the step.
bool pick_up(const World& world, Pathing& pathing, Memory& memory) {
    if (!my_can_move() || memory.banking) return false;
    const auto& map = world.map();
    const vec2 here = my_position();
    for (const int g : {memory.farm_group, memory.claim}) {
        if (g < 0 || g >= static_cast<int>(map.groups.size())) continue;
        const auto& G = map.groups[g];
        const auto& c = world.camps[g];
        if (c.state != CampState::cleared || c.state_round != world.round || G.has_monolith || G.gems + G.gold == 0
            || test(G.tiles(), here) || sole_capture_holder(world, G) || enemy_on(world, G.tiles()) || left_for_prism(world, pathing, g))
            continue;
        // A holder already there yields to us if our hold pays more (value_holder).
        const bool outvalues = outvalues_holders(world, G);
        if (allies_on(world, G.tiles()) >= holders(G) && !outvalues) continue;
        const int steps = steps_to(G, here);
        if (steps > params::pick_up_radius) continue;
        bool ours = true;
        const bool shy = holders(G) == 1 && hold_shy(world, world.me());
        for (const auto& a : world.allies) {
            if (a.is_self || !a.alive || !a.visible || comms::claim_of(world, a.index) != g) continue;
            const int d = steps_to(G, a.pos);
            // Cassi and Issac leave it to any other claimer in pick-up reach.
            if (shy && !hold_shy(world, a) && d <= params::pick_up_radius) ours = false;
            ours &= d > steps || (d == steps && a.index > world.me().index) || outvalues
                    || (holders(G) == 1 && (multiplies(world.me(), G) || (!shy && hold_shy(world, a)))
                        && holder_value(world, world.me(), G, holder_gold_price) > holder_value(world, a, G, holder_gold_price) + 1e-3f);
        }
        if (!ours) continue;
        memory.farm_group = memory.claim = g;
        memory.crew = false;
        return pathing.step_towards(G.tiles(), nullptr, steps + max_detour);
    }
    return false;
}

// The most a crew's share of `worth` rates at, rate(worth / k, base + fastest / k), for a crew of
// k times our output, k in [lo, hi]: our part is 1 / k, and its clear no quicker than our fastest
// over k. In k, worth / (k base + fastest) falls, but the rate's horizon term rises: the rate peaks
// at k = fastest / sqrt(base (horizon + base)), so it is the rate there, held in [lo, hi].
float crew_rate(const World& world, float worth, float base, float fastest, float lo, float hi) {
    const float horizon = cycle_horizon(world.map());
    const float k = std::clamp(fastest / std::sqrt(base * (horizon + base)), lo, hi);
    return rate(world, worth / k, base + fastest / k);
}

// For farm's prunes: a group that cannot beat `best` (nor, with `from_altar` at least 0, the best
// cycle from the altar after `walk`) at `trip` rounds. The value is rated, falling with the
// rounds, and no clear is quicker than the `fastest` (for Ren, reflected_clear). A clear shared
// with an unclaimed `partner` is quicker but pays only our part. With `crew` above 0, a crew of up
// to `crew` times our output may clear it, paying our part (crew_rate), partners included.
bool rated_beaten(const World& world, float worth, float trip, float fastest, float strength, float partner, float best, float from_altar,
                  int walk, float cycle_bank, float crew) {
    const float cap = static_cast<float>(capture_rounds(world));
    float bound = crew > 0 ? crew_rate(world, worth, trip + cap, fastest, 1.0f, crew) : rate(world, worth, trip + cap + fastest);
    if (partner > 0 && crew <= 0) {
        const float part = strength / (strength + partner);
        bound = std::max(bound, rate(world, worth * part, trip + cap + fastest * part));
    }
    const float altar_base = static_cast<float>(walk) + cap + cycle_bank;
    // The slack covers float rounding where a clear takes exactly the fastest.
    return bound * 1.0001f < best
           && (from_altar < 0
               || (crew > 0 ? crew_rate(world, worth, altar_base, fastest, 1.0f, crew) : rate(world, worth, altar_base + fastest)) * 1.0001f
                      < from_altar);
}

// Static per group once read: its centre field (once warm) and that field's steps to our
// spawn, its home_ground weight, its centre_to_altar steps, its own tribute and each holder's
// gold (`tribute` 0 until read, read again when our Tribute or Prospector emblem changes them).
// Then its reward and the walks to bank it, kept while `context` holds (the gold's worth while
// `gold_context` also does), and its fastest clear while its belief holds.
struct GroupFacts {
    const Field* centre = nullptr;
    int to_spawn = -1;
    int gap = -1, gap_range = -1; // home_gap, for range gap_range
    float home = -1;
    int to_altar = -1;
    std::uint32_t context = 0, gold_context = 0, version = ~0u;
    bool sticky = false, planned = false;
    std::uint8_t emblems = 0; // `emblems` when `tribute` and `gold_in` were read
    int walk = 0, chained_tribute = 0, tribute = 0;
    std::uint32_t gold_in = 0;
    float weight = 0, gems = 0, gold = 0, fastest = 0, fastest_strength = 0, walked_bank = 0, walked_cycle = 0;
    // Clearing it alone, kept while `clearing` and its belief hold.
    std::uint32_t clearing = 0, clear_version = ~0u;
    float damage = 0, rounds = 0, kite = -1;
};
struct FarmContext {
    int bag, short_by;
    bool banking;
    std::uint8_t emblems;
    bool operator==(const FarmContext&) const = default;
};
struct FarmClearing {
    float strength, reflect, spells, basic;
    int range;
    bool operator==(const FarmClearing&) const = default;
};
// farm's kept readings, one set for both of its versions.
struct FarmMemo {
    std::vector<int> centre_steps; // by group, -1 until read
    vec2 steps_from{-1, -1};
    std::array<GroupFacts, 256> few_facts;
    std::vector<GroupFacts> many_facts;
    FarmContext last_context{};
    std::uint32_t context = 0;
    float last_per_gold = 0, last_tribute_gold = 0;
    std::uint32_t gold_context = 0;
    int carry_group = -1, carry_round = -1; // the ally's capture our pick in carry_round takes over (prism_takeover)
    FarmClearing last_clearing{};
    std::uint32_t clearing = 0;
    // By group: from each position of its nearest_groups order on, the most any group there holds.
    struct Most {
        int gems, gems_prospected, gold, gold_prospected;
        int near; // the position's own distance from the group's centre
        int spawn_near; // the least Chebyshev distance from our spawn's centre tile of any group there
    };
    // Left unwritten until built (a value-initialised table cost ~1 fuel a byte), null until then.
    std::vector<std::unique_ptr<Most[]>> most_from;
    // By group, for the tables: gems and gold with a Prospector emblem's extra, and the Chebyshev
    // distance from our spawn's centre tile.
    struct Reach {
        int gems_prospected, gold_prospected, spawn_near;
    };
    std::vector<Reach> reach;
    // By group, for later turns' rated bound: gems and gold with a Prospector emblem's extra if
    // `worth_prospector`.
    std::vector<int> worth_gems;
    std::vector<float> worth_gold;
    bool worth_prospector = false;
    int banked_bag = 0; // bankable_bag, for the banking instance
};
FarmMemo& farm_memo() {
    static FarmMemo memo;
    return memo;
}

// Carrying gems, farming on chains a capture onto the bag: it saves the walk to the altar and
// back but keeps the bag at risk for longer. It goes ahead only if the next group, by the time it
// adds to the trip, beats the best cycle starting from the altar; false means bank instead.
// Fixed at the first call of farm_turn<opening>, banking or not (the costliest field grows).
template <bool opening> int farm_dash_kind(const World& world, int n_groups) {
    static const int kind = 150 * static_cast<std::uint64_t>(n_groups) < full_field_cost_estimate() ? world.me().facts().dash_kind() : 0;
    return kind;
}

// An enemy in sight within crew_enemy_radius of a Monolith, none of them in its reach.
bool mono_contested(const World& world, int g) {
    const auto& G = world.map().groups[g];
    bool near = false;
    for (const auto& e : world.enemies) {
        if (!e.alive || !e.visible) continue;
        if (test(G.threat(), e.pos)) return false;
        near |= dist(e.pos, G.centre) <= params::crew_enemy_radius;
    }
    return near;
}

// The most exposure() gives: max_exposure, tuned apart, may lie below mid_exposure.
inline constexpr float exposure_most = std::max({1.0f, params::mid_exposure, params::max_exposure});

// Upper bounds on farm_turn's pre-facts prunes (its rated_below test), from the map and a few of the
// turn's facts. Each float operation of the bounded chain is monotone, and the 2e-4 slack covers sums
// taken in another order, so a group bounded below the bar fails the prune's own test too. +inf where
// a prune does not apply: the win, a striker within help_radius (it may be helped), banking a kited
// group (the risky pick).
// - Worth: gems and gold (negative prices count as 0), at the home weight read so far. The gems'
//   price `tribute_gold` is farm_turn's bound_tribute: Marcella's tribute gold plus a keeping Prism's Focus.
// - Trip: at least the Chebyshev distance, or a recall by way of spawn from as close. Banking, less
//   the bank's (bank_now) plus a floor on the walk home; the walk out from the altar (`alt`) is at
//   least the nearest altar's distance less the tribute range, or the recall and the walk from spawn.
// - Clear: at least the fastest (health left / strength). A crew k times our output (a striker's, k
//   up to `crew_most`) pays worth / k and clears in fastest / k: crew_rate's bound at the clamped best
//   k, which falls with the trip and the fastest. Later turns also take the alone clear at an
//   unclaimed partner's part (`other_part`), as rated_below does.
// Banking, `test` and `test_alt` get the plain-ratio prune's two ratios; Ren's reflection leaves
// strikers unprunable there.
// - Exposure: max_exposure for `out` off banking (rated_below's, at its factor); exposure_most for the
//   bounds on the loop's own tests (`value`, banking's four). Banking, `old` and `old_alt` are a prune
//   of its own at max_exposure: the trip and walk out above with no floor, clear or weight.
struct PreUpper {
    vec2 here;
    int short_by, recall;
    float per_gold, tribute_gold, cap_rounds, horizon, bank_now;
    bool recall_out, prospector, banking, reflects = false;
    FarmRecall via;
    const float* health = nullptr; // World::clear_health
    float clear_scale = 0, other_part = 1;
    const float* weight = nullptr; // by group, home_ground's weight once read, 1 before (its most)
    // Banking: the walk home is at least min(the altar's distance, bank_floor), the recall's arrival
    // less what the stop is worth; 0 where no recall arrives in time.
    float bank_floor = 0;
    float crew_most = 1; // the team's output over ours
    float *out = nullptr, *alt = nullptr, *test = nullptr, *test_alt = nullptr, *old = nullptr, *old_alt = nullptr;
    // Later turns: `out` at the weight, for the best alone (bar_lt's test reads the unweighted worth
    // while the facts' context is stale).
    float* value = nullptr;
};
// By group (padded to 4 lanes), the home_ground weights read so far, 1 for the rest.
const float* known_weights(int n) {
    if (n <= 256) return home_weights().data();
    static std::vector<float> ones;
    if (static_cast<int>(ones.size()) < n + 3) ones.assign(n + 3, 1.0f);
    return ones.data();
}
// Per map, the groups' columns the bounds read: ten of `lanes` words in one allocation.
struct PreColumns {
    const StaticMap* map = nullptr;
    int lanes = 0;
    std::unique_ptr<std::int32_t[]> words;
    std::int32_t *cx, *cy, *spawn_near, *gems, *striker, *kited, *altar_near, *gold, *pro_gems, *pro_gold;
    bool altars_known = false;
    std::vector<std::uint64_t> done; // bit b: block b written this turn, past the first 64
    // The columns for `map` (with the altars' once banking), every block unwritten.
    [[gnu::noinline]] void begin(const StaticMap& map, bool banking);
};
PreColumns pre_columns;

void PreColumns::begin(const StaticMap& m, bool banking) {
    const int n = static_cast<int>(m.groups.size()), padded = (n + 3) & ~3;
    const CampGroup* const groups = m.groups.data();
    if (map != &m || lanes != padded) {
        map = &m, lanes = padded, altars_known = false;
        words.reset(new std::int32_t[10 * static_cast<std::size_t>(padded)]);
        std::int32_t* const w = words.get();
        std::int32_t *const x = cx = w, *const y = cy = w + padded, *const near = spawn_near = w + 2 * padded;
        std::int32_t *const g_gems = gems = w + 3 * padded, *const strikes = striker = w + 4 * padded, *const kite = kited = w + 5 * padded;
        altar_near = w + 6 * padded;
        std::int32_t *const g_gold = gold = w + 7 * padded, *const p_gems = pro_gems = w + 8 * padded, *const p_gold = pro_gold = w + 9 * padded;
        const vec2 spawn = m.ally_spawn_centre;
        const bool shared = m.shared_gems;
        for (int g = 0; g < n; ++g) {
            const auto& group = groups[g];
            x[g] = group.centre.x, y[g] = group.centre.y;
            near[g] = dist(spawn, group.centre);
            g_gems[g] = group.gems;
            strikes[g] = group.strength > 0 ? -1 : 0;
            kite[g] = shared && !group.has_monolith && group.gems >= params::big_gems ? -1 : 0; // big_group
            g_gold[g] = group.gold;
            p_gems[g] = group.gems + prospected(group.cluster_gems, 1), p_gold[g] = group.gold + prospected(group.cluster_gold, 1);
        }
        // Padding lanes: never read back, but their arithmetic must not trap.
        for (int g = n; g < padded; ++g)
            for (int c = 0; c < 10; ++c) w[c * padded + g] = 0;
    }
    if (banking && !altars_known) {
        // The nearest altar's distance less the tribute range, by group: four altars a step.
        altars_known = true;
        for (int g = 0; g < padded; ++g) altar_near[g] = unreachable;
        const int altars = static_cast<int>(m.altars.size()), four = (altars + 3) & ~3;
        std::vector<std::int32_t> ax(four, 1 << 20), ay(four, 1 << 20);
        for (int a = 0; a < altars; ++a) ax[a] = m.altars[a].pos.x, ay[a] = m.altars[a].pos.y;
        for (int g = 0; g < n && altars > 0; ++g) {
            const v128_t x = wasm_i32x4_splat(cx[g]), y = wasm_i32x4_splat(cy[g]);
            v128_t near = wasm_i32x4_splat(1 << 20);
            for (int a = 0; a < four; a += 4)
                near = wasm_i32x4_min(near, wasm_i32x4_max(wasm_i32x4_abs(wasm_i32x4_sub(wasm_v128_load(&ax[a]), x)),
                                                           wasm_i32x4_abs(wasm_i32x4_sub(wasm_v128_load(&ay[a]), y))));
            const int least = std::min(std::min(wasm_i32x4_extract_lane(near, 0), wasm_i32x4_extract_lane(near, 1)),
                                       std::min(wasm_i32x4_extract_lane(near, 2), wasm_i32x4_extract_lane(near, 3)));
            altar_near[g] = std::max(0, least - cambc::constants::submit_gems_range);
        }
    }
    done.assign(static_cast<std::size_t>((padded / 4 + 63) / 64), 0);
}

// The bounds a block of 4 groups at a time, at the loop's first test of one of them (its order is not
// the groups'), so the pass costs what the groups reached do. Nothing they read changes during the
// loop: a home weight is read only by its own group's facts, after its test. Inlined into the loop,
// whose locals then hold the constants.
struct PreLanes {
    // What the blocks read of PreUpper and the columns, copied so that none is reloaded.
    struct {
        const float *health, *weight;
        float *out, *alt, *test, *test_alt, *value, *old, *old_alt;
        bool banking, recall_out;
        float other_part;
    } p;
    struct {
        const std::int32_t *cx, *cy, *spawn_near, *gems, *striker, *kited, *altar_near;
    } t;
    const std::int32_t *worth_gems, *worth_gold;
    v128_t hx, hy, short_by, help, one, slack, horizon, cap, exposure, most_exposure, most_scale, channel, value, out_base, inf;
    v128_t crew_most, bank_now, zero, recall, clear, bank_floor, reflects, other_part, per_gold, tribute_gold;

    [[gnu::always_inline]] PreLanes(const PreUpper& p, const PreColumns& c)
        : p{p.health, p.weight, p.out, p.alt, p.test, p.test_alt, p.value, p.old, p.old_alt, p.banking, p.recall_out, p.other_part},
          t{c.cx, c.cy, c.spawn_near, c.gems, c.striker, c.kited, c.altar_near} {
        worth_gems = p.prospector ? c.pro_gems : c.gems, worth_gold = p.prospector ? c.pro_gold : c.gold;
        hx = wasm_i32x4_splat(p.here.x), hy = wasm_i32x4_splat(p.here.y), short_by = wasm_i32x4_splat(p.short_by);
        help = wasm_i32x4_splat(params::help_radius);
        one = wasm_f32x4_splat(1.0f), slack = wasm_f32x4_splat(1.0002f), horizon = wasm_f32x4_splat(p.horizon);
        cap = wasm_f32x4_splat(p.cap_rounds), exposure = wasm_f32x4_splat(params::max_exposure);
        most_exposure = wasm_f32x4_splat(exposure_most), most_scale = wasm_f32x4_splat(exposure_most / params::max_exposure);
        channel = wasm_f32x4_splat(static_cast<float>(p.via.channel)), value = wasm_f32x4_splat(p.via.value);
        out_base = wasm_i32x4_splat(p.via.channel + p.via.hurt);
        inf = wasm_f32x4_splat(std::numeric_limits<float>::infinity());
        crew_most = wasm_f32x4_splat(p.crew_most), bank_now = wasm_f32x4_splat(p.bank_now), zero = wasm_f32x4_splat(0.0f);
        recall = wasm_i32x4_splat(p.recall), clear = wasm_f32x4_splat(p.clear_scale), bank_floor = wasm_f32x4_splat(p.bank_floor);
        reflects = wasm_i32x4_splat(p.reflects ? -1 : 0), other_part = wasm_f32x4_splat(p.other_part);
        per_gold = wasm_f32x4_splat(std::max(0.0f, p.per_gold)), tribute_gold = wasm_f32x4_splat(std::max(0.0f, p.tribute_gold));
    }

    [[gnu::always_inline]] void block(int g) const {
        const auto rate_of = [&](v128_t w, v128_t rounds) __attribute__((always_inline)) {
            rounds = wasm_f32x4_pmax(rounds, one);
            return wasm_f32x4_mul(wasm_f32x4_div(w, wasm_f32x4_mul(rounds, wasm_f32x4_add(one, wasm_f32x4_div(rounds, horizon)))), slack);
        };
        // crew_rate's: a crew k times our output pays w / k and clears in fastest / k, best at the clamped k.
        const auto crew_rated = [&](v128_t w, v128_t trip, v128_t fastest, v128_t most) __attribute__((always_inline)) {
            const v128_t base = wasm_f32x4_add(trip, cap);
            const v128_t k = wasm_f32x4_pmin(wasm_f32x4_pmax(wasm_f32x4_div(fastest, wasm_f32x4_sqrt(wasm_f32x4_mul(base, wasm_f32x4_add(horizon, base)))), one), most);
            return rate_of(wasm_f32x4_div(w, k), wasm_f32x4_add(base, wasm_f32x4_div(fastest, k)));
        };
        const v128_t near = wasm_i32x4_max(wasm_i32x4_abs(wasm_i32x4_sub(wasm_v128_load(&t.cx[g]), hx)),
                                           wasm_i32x4_abs(wasm_i32x4_sub(wasm_v128_load(&t.cy[g]), hy)));
        // The scalar max(0, gems + per_gold gold + tribute_gold gems), operation for operation.
        const v128_t gems = wasm_f32x4_convert_i32x4(wasm_i32x4_min(wasm_v128_load(&worth_gems[g]), short_by));
        const v128_t gold = wasm_f32x4_convert_i32x4(wasm_v128_load(&worth_gold[g]));
        const v128_t worth = wasm_f32x4_pmax(zero, wasm_f32x4_add(wasm_f32x4_add(gems, wasm_f32x4_mul(per_gold, gold)), wasm_f32x4_mul(tribute_gold, gems)));
        const v128_t striker = wasm_v128_load(&t.striker[g]);
        const v128_t fastest = wasm_f32x4_mul(wasm_v128_load(&p.health[g]), clear);
        const v128_t most = wasm_v128_bitselect(crew_most, one, striker);
        if (p.banking) {
            const v128_t w = wasm_f32x4_mul(wasm_f32x4_mul(worth, most_exposure), wasm_v128_load(&p.weight[g]));
            const v128_t altar_near = wasm_v128_load(&t.altar_near[g]);
            const v128_t bank = wasm_f32x4_pmin(wasm_f32x4_convert_i32x4(altar_near), bank_floor);
            const v128_t walk = wasm_f32x4_convert_i32x4(near);
            v128_t trip = wasm_f32x4_pmax(zero, wasm_f32x4_add(wasm_f32x4_sub(walk, bank_now), bank));
            v128_t old_walk = walk;
            // Carrying, the recall out to the group may be the sooner way (recall_out). The loop prices
            // that trip on to an altar healed, which can undercut `bank`: no floor on it.
            if (p.recall_out) {
                const v128_t via = wasm_f32x4_pmax(channel, wasm_f32x4_sub(wasm_f32x4_convert_i32x4(wasm_i32x4_add(out_base, wasm_v128_load(&t.spawn_near[g]))), value));
                trip = wasm_f32x4_pmin(trip, wasm_f32x4_pmax(zero, wasm_f32x4_sub(via, bank_now)));
                old_walk = wasm_f32x4_pmin(old_walk, via);
            }
            const v128_t out_near = wasm_f32x4_convert_i32x4(wasm_i32x4_min(altar_near, wasm_i32x4_add(recall, wasm_v128_load(&t.spawn_near[g]))));
            const v128_t out_walk = wasm_f32x4_add(out_near, bank);
            const v128_t skip = wasm_v128_or(wasm_v128_load(&t.kited[g]), wasm_i32x4_ge(wasm_v128_load(&t.gems[g]), short_by));
            const v128_t tuned = wasm_f32x4_mul(worth, exposure);
            wasm_v128_store(&p.old[g], wasm_v128_bitselect(inf, rate_of(tuned, wasm_f32x4_add(wasm_f32x4_pmax(zero, wasm_f32x4_sub(old_walk, bank_now)), cap)), skip));
            wasm_v128_store(&p.old_alt[g], wasm_v128_bitselect(inf, rate_of(tuned, wasm_f32x4_add(out_near, cap)), skip));
            // A crew's clear is no quicker than the team's output allows; alone, than ours. Ren's
            // reflection clears strikers quicker still: none counted.
            const v128_t reflected = wasm_v128_and(reflects, striker);
            const v128_t quick = wasm_v128_andnot(fastest, reflected);
            wasm_v128_store(&p.out[g], wasm_v128_bitselect(inf, crew_rated(w, trip, quick, most), skip));
            wasm_v128_store(&p.alt[g], wasm_v128_bitselect(inf, crew_rated(w, out_walk, quick, most), skip));
            // The plain ratios: a zero denominator gives inf or NaN, which no prune passes.
            const v128_t base = wasm_f32x4_add(cap, fastest);
            const v128_t unprunable = wasm_v128_or(skip, reflected);
            wasm_v128_store(&p.test[g], wasm_v128_bitselect(inf, wasm_f32x4_mul(wasm_f32x4_div(w, wasm_f32x4_add(trip, base)), slack), unprunable));
            wasm_v128_store(&p.test_alt[g], wasm_v128_bitselect(inf, wasm_f32x4_mul(wasm_f32x4_div(w, wasm_f32x4_add(out_walk, base)), slack), unprunable));
            return;
        }
        v128_t trip = wasm_f32x4_convert_i32x4(near);
        if (p.recall_out)
            trip = wasm_f32x4_pmin(trip, wasm_f32x4_pmax(channel, wasm_f32x4_sub(wasm_f32x4_convert_i32x4(
                                                                     wasm_i32x4_add(out_base, wasm_v128_load(&t.spawn_near[g]))), value)));
        const v128_t w = wasm_f32x4_mul(worth, exposure);
        // rated_below's two: a crew's (no partner counted), alone or at an unclaimed partner's part (with
        // none, alone is the crew's k = 1).
        v128_t rated_most = crew_rated(w, trip, fastest, most);
        if (p.other_part < 1.0f)
            rated_most = wasm_f32x4_pmax(rated_most, rate_of(wasm_f32x4_mul(w, other_part), wasm_f32x4_add(wasm_f32x4_add(trip, cap), wasm_f32x4_mul(fastest, other_part))));
        const v128_t helped = wasm_v128_and(striker, wasm_i32x4_le(near, help));
        const v128_t unbounded = wasm_v128_or(helped, wasm_i32x4_ge(wasm_v128_load(&t.gems[g]), short_by));
        const v128_t bound = wasm_v128_bitselect(inf, rated_most, unbounded);
        wasm_v128_store(&p.out[g], bound);
        // The bound is linear in the worth. inf x a weight of 0 is NaN, which prunes nothing.
        if (p.value) wasm_v128_store(&p.value[g], wasm_f32x4_mul(wasm_f32x4_mul(bound, most_scale), wasm_v128_load(&p.weight[g])));
    }
};

// work_arrival's `earliest` reads only these (and the ally's type, fixed by its index), so it is
// kept per group and ally while they hold: a claimer standing at its group, or unseen at its last
// sighting, asks the same each turn. -1: no live member. One table for every farm_turn instance.
struct KeptArrival {
    bool known;
    bool visible;
    std::int32_t x, y; // plain ints: a vec2 member would give the table a run-time initialiser
    std::uint32_t version;
    int dash_ready, recall_delay, first_turn, earliest;
};
std::array<std::array<KeptArrival, 8>, 256> kept_arrival;

// This turn's mirror pull and denial (params::comeback), on while cooked.
struct MirrorPull {
    bool on = false;
    vec2 mirror{-1, -1};
    float deny_scale = 1; // enemy-side groups' worth
};
MirrorPull mirror_pull(const World& world) {
    MirrorPull m;
    if (!comeback::cooked(world)) return m;
    m.on = true;
    m.mirror = world.map().mirror(my_position());
    m.deny_scale = 1.0f + params::comeback::deny_w;
    return m;
}

// The first turn has its own instance: its extra prunes would make every later call dearer. So
// do later turns' banking calls, out of line, past pick_up.
// `repricing`: only the pick, during our recall's channel, which may then go on to its
// choice (Memory::recall_farm); nothing acts.
constexpr bool banks_bag_of(bool banking, bool banking_now, bool opening) { return opening ? banking_now : banking; }

// The draft's opening plan (draft/open_plan.h): within its horizon, our next planned group while it has a live
// member, no enemy in sight near it and our gems are not headed for an altar. A step is done once its group stands
// cleared and held, or respawning; cleared and not yet held, farm takes the capture itself.
int open_plan_choice(const World& world, Memory& memory) {
    if constexpr (!params::open_plan::on) return -1;
    if (world.round > params::open_plan::horizon) return -1;
    const auto& map = world.map();
    for (;; ++memory.open_step) {
        if (memory.open_step >= params::open_plan::steps) return -1;
        const int g = map.opening_group(world.me().index, memory.open_step);
        if (g < 0) return -1;
        const auto& c = world.camps[g];
        if (c.state == CampState::respawning || (c.state == CampState::cleared && c.holder)) continue;
        if (c.state == CampState::cleared) return -1;
        for (const auto& e : world.enemies)
            if (e.alive && e.visible && dist(e.pos, map.groups[g].centre) <= params::open_plan::enemy_near) return -1;
        return g;
    }
}

// Our claim, while it is the capture our last pick carried ('G' or 'L'), withdrawn.
void drop_carry_claim(Memory& memory) {
    auto& memo = farm_memo();
    if (memo.carry_group >= 0 && memory.claim == memo.carry_group) memory.claim = -1;
    memo.carry_group = -1;
}

template <bool opening, bool banking = false, bool repricing = false> [[gnu::flatten]] bool farm_turn(World& world, Pathing& pathing, Safety& safety, Memory& memory);
[[gnu::noinline]] bool farm_banking(World& world, Pathing& pathing, Safety& safety, Memory& memory);
template <bool opening, bool banking, bool repricing> [[gnu::flatten]] bool farm_turn(World& world, Pathing& pathing, Safety& safety, Memory& memory) {
    world.throw_if_stale();
    auto& memo = farm_memo();
    if (!banking && !repricing && pick_up(world, pathing, memory)) return true;
    const auto& map = world.map();
    const auto& groups = map.groups;
    // Before our own facts below: a turn handed to farm_banking reads them there.
    const int bag = banking ? memo.banked_bag : bankable_bag(world, pathing);
    const bool banking_now = banking || (bag > 0 && !retaining_gems(world, pathing));
    // A capture is worth something only if allies' long tributes are cancelled (a stun or a lock
    // does it, again and again on a contested altar), so it is priced as if they will be.
    const int short_by = gems_short(world, params::tribute_window);
    if (world.is_stale()) return true;
    if constexpr (!opening && !banking)
        if (banking_now) return memo.banked_bag = bag, farm_banking(world, pathing, safety, memory);
    // The opening plan's group for us now; with a weight, it is the choice the loop starts from, weighted.
    const int planned_now = !banking && !repricing && !banks_bag_of(banking, banking_now, opening) && params::open_plan::weight > 0
                                ? open_plan_choice(world, memory) : -1;
    const int range = world.me().facts().attack_range();
    const float strength = camp_output(world.me()), soften = camp_hit_factor(), reflect = world.me().retaliation();
    const float max_health = my_max_health();
    const float line = recall_line(world, safety);
    const float spare_health = (my_health() - line * max_health) / params::camp_risk;
    // Trips home: the health we spend before one and on each, as crew.cc prices them.
    const float trip_spare = std::max(0.0f, my_health() - line * max_health) / params::crew_trip_risk;
    const float usable_health = max_health * (1.0f - line) / params::crew_trip_risk;
    const float shield = self_shield_amount(world.me());
    const int shield_slot = world.me().facts().slot_of(AbilityKind::shield);
    const float shield_ready_in = shield_slot < 0 ? 0.0f : static_cast<float>(std::max(0, world.me().ready_round[shield_slot] - world.round));
    // An operation we proposed fails once we have stood in its reach crew_wait_rounds with nobody
    // claiming it or in its reach: it is weighed alone from then on, and not proposed for a while.
    if (const int g = memory.crew_proposed; g >= 0) {
        if (memory.claim != g || memory.crew || world.camps[g].state == CampState::cleared) {
            memory.crew_proposed = memory.crew_reached = -1;
        } else if (crew_in_reach(world, g, my_position(), farm_monolith(world, g) ? groups[g].reach + 2 : range)) {
            bool joined = false;
            for (const auto& a : world.allies)
                joined |= !a.is_self && a.alive
                          && (comms::claim_of(world, a.index) == g || (a.visible && crew_in_reach(world, g, a.pos, a.facts().attack_range())));
            if (memory.crew_reached < 0 || joined) memory.crew_reached = world.round;
            else if (world.round - memory.crew_reached >= params::crew_wait_rounds) {
                if (g < static_cast<int>(memory.crew_ban.size())) memory.crew_ban[g] = world.round + params::crew_ban_rounds;
                debug_block({ std::printf("CREW BAIL %d %u g%d since %d\n", world.round, my_handle(), g, memory.crew_reached); });
                memory.crew_proposed = memory.crew_reached = -1;
            }
        }
    }
    // Strong live groups: a crew can clear them quicker than any solo bound allows, so the prunes
    // below bound them at the team's output (prune_fastest).
    // Big groups on shared-gems maps are kite()'s: their claimers cast from out of reach, so they are
    // no crew taking turns at the hits, and no operation is proposed on them.
    const auto kited_of = [&](int g) __attribute__((always_inline)) { return map.shared_gems && big_group(groups[g]); };
    const auto strong_of = [&](int g) __attribute__((always_inline)) {
        return groups[g].strength > 0 && (!groups[g].has_monolith || !map.monolith_only) && world.camps[g].state != CampState::cleared && !kited_of(g);
    };
    // The farm loop's group, read once there; -1 elsewhere.
    int read_g = -1;
    bool read_strong = false, read_kited = false;
    const auto kited = [&](int g) __attribute__((always_inline)) { return g == read_g ? read_kited : kited_of(g); };
    const auto strong = [&](int g) __attribute__((always_inline)) { return g == read_g ? read_strong : strong_of(g); };
    // Farm's Monolith operation (farm_monolith): bookkeeping for the gather and the traces.
    if (memory.mono_group >= 0) memory.mono_taken += memory.damage;
    // A sleeping Monolith is woken only once mono_gather_share of the crew's output stands within a
    // step of the staging ring (us counted, coming or not), or after mono_max_wait there; an awake
    // one is worked at once. `output`: the crew's as priced.
    const auto mono_engage = [&](int g, float output) {
        const auto& c = world.camps[g];
        if (c.state != CampState::alive || c.awake == Awake::awake) return true;
        const auto& G = groups[g];
        const auto near = [&](vec2 p) {
            for (std::size_t i = 0; i < G.members.size(); ++i)
                if (c.health[i] > 0 && G.members[i].strength > 0 && dist(p, G.members[i].pos) <= G.reach + 2) return true;
            return false;
        };
        float staged = strength;
        for (const auto& a : world.allies)
            if (!a.is_self && a.alive && a.visible && comms::claim_of(world, a.index) == g && near(a.pos)) staged += camp_output(a);
        if (staged >= params::mono_gather_share * output) return true;
        return memory.mono_group == g && memory.mono_staged >= 0 && world.round - memory.mono_staged >= params::mono_max_wait;
    };
    if (farm_monolith(world, memory.farm_group) && memory.claim == memory.farm_group && mono_engage(memory.farm_group, memory.mono_output))
        siege_group() = memory.farm_group;
    const bool banks_bag = opening ? banking_now : banking;
    // Groups in passing pay too (gold clusters are never chosen below), but not one whose clear
    // costs more health than we can spare.
    const auto affordable = [&](int g) __attribute__((always_inline)) {
        if (g == memory.farm_group || groups[g].strength <= 0) return true;
        float rounds = 0;
        float ready_in = shield_ready_in;
        if (ready_in > 0) {
            int trip = unreachable;
            // Not me().pos (the turn-start tile): the strike search may have moved us. Off the map, we were killed.
            const vec2 now = my_position(), here = now.x >= 0 ? now : world.me().pos;
            for (const auto& m : groups[g].members) trip = std::min(trip, std::max(0, dist(here, m.pos) - range));
            ready_in = std::max(0.0f, ready_in - static_cast<float>(trip));
        }
        return shielded_clear(soften * min_camp_damage(world, g, strength, &rounds, reflect), rounds, shield, ready_in) <= spare_health
               || ally_engaged(world, g);
    };
    std::array<std::uint64_t, 4> ally_claims{}; // bit g: comms carries groups below 255
    for (const auto& a : world.allies)
        if (const int c = comms::claim_of(world, a.index); !a.is_self && c >= 0 && c < 256) ally_claims[c >> 6] |= std::uint64_t{1} << (c & 63);
    const auto claimed_by_ally = [&](int g) __attribute__((always_inline)) {
        return g < 256 && (ally_claims[g >> 6] >> (g & 63) & 1);
    };
    // An ally's claim makes us its crew rather than its rival, unless we claimed it first.
    const auto taken = [&](int g) __attribute__((always_inline)) {
        return claimed_by_ally(g) && (memory.claim != g || memory.crew);
    };
    const bool melee = world.me().facts().walk_and_attack_independent();
    // With three picks, Tavi takes the harmless gold-only groups on maps of pure-gold groups. Cassi
    // farms with the pack: Intercontinental Fish's deals 80% of its camp damage in crews of 3+.
    const bool gold_farmer = farms_gold(world, world.me());
    // A ranged hit in passing costs the walk: only for our choice, or gems no ally will clear. A
    // group that hits back and that we will not finish is only woken by it: hit one only while an
    // ally clears it or, melee, once every striker is awake anyway. Allies merely walking past
    // its reach clear nothing.
    const auto passing = [&](int g) __attribute__((always_inline)) {
        if (g == memory.farm_group) return true;
        // The clear's price last: the other tests are cheap reads.
        if (taken(g)) return false;
        if (groups[g].strength > 0)
            return (((kited(g) || claimed_by_ally(g)) && ally_engaged(world, g)) || (melee && world.camps[g].fully_awake())) && affordable(g);
        return (melee || groups[g].gems > 0 || gold_farmer) && affordable(g);
    };
    // Rather than wake a sleeping striker group with a ranged hit that kills nothing, finish a
    // harmless resource group already damaged and wholly in range: its index in `resources`, or -1.
    // Called only for an ordinary farming turn's hit.
    const auto prefer_partial = [&](const CampAttackTargets& ordinary, const CampAttackTargets& resources) {
        if (ordinary.n == 0 || resources.n == 0 || holding_capture(world, pathing)) return -1;
        const auto& alternative = ordinary.found[0];
        const int g = alternative.group;
        const auto& G = groups[g];
        const auto& c = world.camps[g];
        if (G.has_monolith || G.members[alternative.member].strength <= 0 || c.state != CampState::alive) return -1;
        const vec2 here = my_position();
        bool striker = false;
        for (int i = 0; i < static_cast<int>(G.members.size()); ++i) {
            if (G.members[i].strength <= 0) continue;
            if (!test(world.visible, G.members[i].pos) || c.health_round[i] != world.round || !(c.health[i] >= 0)) return -1;
            if (c.health[i] <= 0) continue;
            striker = true;
            if (!c.member_asleep(i)) return -1;
        }
        if (!striker) return -1;
        const auto live = my_record();
        const float basic = live.strength * damage_scale(world.me().facts().passive, live.health, live.max_health)
                            * camp_dealt_factor();
        if (!(basic > 0) || !(c.health[alternative.member] > basic)) return -1;
        std::array<int, 16> checked;
        int n_checked = 0;
        for (int k = 0; k < resources.n; ++k) {
            const int h = resources.found[k].group;
            if (std::find(checked.begin(), checked.begin() + n_checked, h) != checked.begin() + n_checked) continue;
            checked[n_checked++] = h;
            const auto& H = groups[h];
            const auto& known = world.camps[h];
            // Strength is the members' sum, so none of them strikes.
            if (h == g || H.has_monolith || H.strength > 0 || H.gems + H.gold <= 0 || known.state != CampState::alive) continue;
            // An ally's claim wins even over our own.
            if (claimed_by_ally(h) || sole_capture_holder(world, H) || allies_on(world, H.tiles()) >= holders(H)) continue;
            bool partial = false, alive = false, fresh = true, in_range = true;
            for (int i = 0; i < static_cast<int>(H.members.size()); ++i) {
                const auto& m = H.members[i];
                fresh &= test(world.visible, m.pos) && known.health_round[i] == world.round && known.health[i] >= 0;
                partial |= known.health[i] < m.max_health;
                if (known.health[i] <= 0) continue;
                alive = true;
                in_range &= dist(here, m.pos) <= range;
            }
            if (fresh && alive && partial && in_range) return k;
        }
        return -1;
    };
    const auto attack_in_range = [&]() __attribute__((always_inline)) {
        CampAttackTargets resources;
        const bool ordinary = !melee && decision == Branch::farm && !memory.banking && !memory.siege && siege_group() < 0;
        const auto targets = camp_attack_targets(world, passing, ordinary ? &resources : nullptr);
        int hit = -1;
        if (ordinary) {
            const int preferred = prefer_partial(targets, resources);
            if (preferred >= 0 && attack_camp_target(world, resources.found[preferred])) {
                hit = memory.farm_group = memory.claim = resources.found[preferred].group;
                memory.crew = false;
            }
        }
        if (hit < 0) hit = attack_camp_targets(world, targets);
        if (hit >= 0 && hit != memory.claim) {
            memory.crew = taken(hit);
            memory.claim = hit;
        }
        // Our hit cleared the group: a melee walk onto its tile starts the capture a round sooner.
        if (hit >= 0 && melee && step_onto_cleared(world, pathing, hit)) {
            memory.farm_group = hit;
            return true;
        }
        if (hit < 0 || melee) return false; // walk on
        cast_at_camp(world, hit);
        reset_and_attack_camp(world, hit);
        return true;
    };
    const bool keeps = keeps_gems(world, pathing);
    // On the way to take over an ally's capture, a ranged hit in passing costs the step that makes the payout,
    // and its claim the claim the ally leaves the group to us by (left_for_prism).
    const int carried = memo.carry_group;
    const bool taking_over = keeps && carried >= 0 && memo.carry_round == world.round - 1 && carried == memory.farm_group && world.camps[carried].state == CampState::cleared
                             && !test(groups[carried].tiles(), my_position());
    if (!repricing && !banks_bag && !taking_over && attack_in_range()) return true;
    if (world.is_stale()) return true;

    // Holders keep a capture going, and more only split the reward.
    const auto ally_holding = [&](int g) __attribute__((always_inline)) {
        return sole_capture_holder(world, groups[g]) || allies_on(world, groups[g].tiles()) >= holders(groups[g]);
    };

    const vec2 here = my_position();
    if (holding_capture(world, pathing)) return true;
    MirrorPull pull;
    if constexpr (!opening) pull = mirror_pull(world);
    // steps less the pull's cut, from `mirror_steps` (a lower bound of them keeps the result one).
    const auto pulled_steps = [&](float steps, float mirror_steps) __attribute__((always_inline)) {
        if (!pull.on) return steps;
        return steps - params::comeback::pull_lam * std::max(0.0f, steps - params::comeback::pull_c * mirror_steps);
    };
    const auto pulled_near = [&](int g, int near) __attribute__((always_inline)) {
        if (!pull.on) return near;
        return static_cast<int>(std::floor(pulled_steps(static_cast<float>(near), static_cast<float>(dist(pull.mirror, groups[g].centre)))));
    };
    // Carrying, whatever made us retreat stays out of bounds: we route around it or wait outside
    // it rather than step in to be sent back out. Empty-handed, a step in risks nothing (the zone
    // starts beyond any strike's reach) and keeps us at hand for when the pack moves on.
    // Read only by the walks after the loop: drawn then (the loop moves nothing), not on turns cut short of them.
    const bool zoned = bag_at_stake(world) > 0;
    const bitboard* zone = nullptr;
    const auto need_zone = [&] { zone = zoned ? pack_zone(world, safety) : nullptr; };

    // Beyond our walk: from a pocket the turn-end recall takes us home (continue_recall); from our
    // walk, the crystal's hop, by way of our spawn to buy one.
    const bool in_pocket = map.any_group_hop() && !pathing.on_foot(here);
    const auto cross = [&](int g) {
        const int h = map.group_hop(g);
        if (in_pocket || h < 0) return false;
        memory.wants_crystal = true;
        if (!carries_crystal() && test(map.ally_spawn, here)) buy_crystal(memory);
        // No safe start or landing: the hop is set aside for a while rather than stood on.
        if (carries_crystal() && !take_hop(world, pathing, safety, memory, h, &pathing.to_group(g)))
            memory.hop_refused = h, memory.hop_refused_until = world.round + 2 * ability_cooldown;
        else if (!carries_crystal()) step_safely(world, pathing, pathing.to_ally_spawn(), safety);
        return true;
    };
    // Short of fuel, walk on towards the last choice rather than run out mid-turn. Static fields
    // are kept, so after the first walk to a group this costs a descent.
    const int previous = memory.farm_group;
    const auto walk_on = [&](int g) __attribute__((always_inline)) {
        if (g < 0) return false;
        if (map.any_group_hop() && beyond_walk(world, pathing, g)) return cross(g);
        // A respawning group returns only once its camp tiles are empty (Pathing::attack_tiles):
        // a walk or dash towards it stops short of them.
        const auto off = [&](int target) __attribute__((always_inline)) -> const bitboard* {
            if (world.camps[target].state != CampState::respawning) return zone;
            static bitboard tiles{cambc::uninitialized};
            copy_into(groups[target].tiles(), tiles);
            if (zone) tiles |= *zone;
            return &tiles;
        };
        // Descending it walks around walls and live camps; a live route only helps past allies.
        const auto walk = [&](const Field& field, int target) __attribute__((always_inline)) {
            return pathing.walk_down(field, off(target), groups[target].centre);
        };
        if (const auto* field = pathing.prepare_approach(g, walk_range(world, g), end_reserve)) return walk(*field, g);
        const bool ready_previous = previous >= 0 && previous != g && pathing.approach_ready(previous, walk_range(world, previous));
        // Too short of fuel to search the way: the choice stands, walked down a field already made.
        if (pathing.approach_skipped()) {
            if (const auto* centre = pathing.from_centre(g)) return pathing.descend(*centre, off(g), groups[g].centre);
            if (ready_previous) {
                note_shortcut("farm-kept-target");
                return walk(*pathing.approach(previous, walk_range(world, previous)), previous);
            }
        } else {
            // No way round the live camps within the search's cap: last turn's choice, whose way is known.
            if (ready_previous) {
                note_shortcut("farm-kept-target");
                memory.farm_group = memory.claim = previous;
                memory.crew = false;
                return walk(*pathing.approach(previous, walk_range(world, previous)), previous);
            }
            // The static walls' way leads into the camps that close it; pricing now knows (live_steps).
            if (pathing.live_steps(g, walk_range(world, g)) >= 0) return false;
            if (const auto* centre = pathing.centre_field(g)) return pathing.descend(*centre, off(g), groups[g].centre);
        }
        note_shortcut("crow-flies-farm");
        return pathing.step_closer(groups[g].centre, off(g), groups[g].centre);
    };
    // The walk comes before choosing better: fuel for its search is kept back from the evaluation.
    const auto walk_reserve = [&](int g) __attribute__((always_inline)) { return g < 0 ? std::uint64_t{0} : pathing.approach_cost(g, walk_range(world, g)); };
    // Centre fields give the steps a field from here would, without its cost. Walls are static, so
    // the steps are kept while we stand still, as when attacking a camp.
    auto& centre_steps = memo.centre_steps;
    auto& steps_from = memo.steps_from;
    if (here != steps_from) {
        steps_from = here;
        centre_steps.assign(groups.size(), -1);
    }
    // Per base gold of a group: we are paid it with our bonuses.
    const float paid = gold_paid(world);
    float per_gold = prices(world).per_gold * paid * (gold_farmer ? params::gold_farmer_weight : 1.0f);
    // Gold is worth more to the more efficient of us (relative_efficiency): it completes stronger emblems sooner
    // funnelled than spread.
    per_gold *= relative_efficiency(world)[world.me().index & 63];
    const int n_groups = static_cast<int>(groups.size());
    auto& few_facts = memo.few_facts;
    auto& many_facts = memo.many_facts;
    if (n_groups > static_cast<int>(few_facts.size()) && static_cast<int>(many_facts.size()) != n_groups) many_facts.assign(n_groups, {});
    GroupFacts* const group_facts = n_groups > static_cast<int>(few_facts.size()) ? many_facts.data() : few_facts.data();
    const bool prospector = world.me().prospector;
    const auto emblems = static_cast<std::uint8_t>(world.me().fast_tribute | prospector << 1);
    auto& last_context = memo.last_context;
    auto& context = memo.context;
    if (const FarmContext now{bag, short_by, banks_bag, emblems}; context == 0 || !(now == last_context))
        last_context = now, ++context;
    // Marcella is paid gold for each gem she tributes, with our gold bonus (probe-marcella-gold).
    const float per_gem = world.me().facts().tribute_gold_per_gem();
    const float tribute_gold = per_gem > 0 ? prices(world).per_gold * paid * per_gem : 0.0f;
    auto& last_per_gold = memo.last_per_gold;
    auto& last_tribute_gold = memo.last_tribute_gold;
    auto& gold_context = memo.gold_context;
    if (gold_context == 0 || per_gold != last_per_gold || tribute_gold != last_tribute_gold)
        last_per_gold = per_gold, last_tribute_gold = tribute_gold, ++gold_context;
    // A Prism keeping its gems (keeps_gems) gains carried_bonus on each gem of a capture it takes part in,
    // at its takeover price: every pick type, the carries' 'G' and 'L' too. Applied past the kept facts,
    // which hold none of it. Not on a Monolith or a capture that wins. keeps_bag only tightens with the
    // gems, so `keep_most`, a gem's at 1, bounds every group's: the prunes add it to the gems' price as
    // tribute_gold is.
    const bool keeper = keeps;
    const float keeper_price = keeper ? prices(world).per_gold : 0.0f;
    const float keep_most = keeper && short_by > 1 ? carried_bonus(world, world.me(), 1, keeper_price) : 0.0f;
    const auto keep_bonus = [&](const CampGroup& G) __attribute__((always_inline)) {
        return keep_most > 0 && G.gems > 0 && G.gems < short_by && !G.has_monolith ? carried_bonus(world, world.me(), G.gems, keeper_price) : 0.0f;
    };
    const float bound_tribute = tribute_gold + keep_most;
    const float spells = world.me().facts().ranged ? spell_output(world.me()) : 0.0f, basic = std::max(1.0f, basic_output(world.me()));
    auto& last_clearing = memo.last_clearing;
    auto& clearing = memo.clearing;
    if (const FarmClearing now{strength, reflect, spells, basic, range}; clearing == 0 || !(now == last_clearing))
        last_clearing = now, ++clearing;
    // After a fight's search, the turn's walk goes on to last turn's choice (a bag is banked): the
    // fight has already taken the turn's work, and the evaluation is done again once it is over.
    // The loop below would weigh no group, so none of its setup is read (~5-7k, on turns the
    // search has left short). The memo contexts above still advance: some kept facts read more
    // than their context holds, and skipping a turn's context changed later choices.
    if (struck && memory.farm_group >= 0) {
        if (banks_bag) return false;
        if (world.is_stale()) return true;
        need_zone();
        memory.crew = memory.claim == memory.farm_group && memory.crew;
        memory.claim = memory.farm_group;
        // A spawn stand of the group heals what its fire takes (home_stands): held and fired from, or
        // walked to, before the walk on, which would leave it. Not a Monolith, staged below.
        const int g = memory.farm_group;
        static bitboard near{cambc::uninitialized};
        if (!groups[g].has_monolith && home_stands_near(world, pathing, safety, g, range, near)) {
            if (test(near, here)) {
                if (my_can_attack()) attack_camp(world, [&](int h) { return h == g; });
                cast_at_camp(world, g);
                reset_and_attack_camp(world, g);
                return true;
            }
            if (pathing.step_towards_funded(near, end_reserve)) return true;
        }
        walk_on(g);
        return true;
    }
    // The recall started at this turn's end reaches a group by way of spawn
    // (FarmRecall), kept by recall_to_farm under the same tests; this turn's walk is spent either
    // way. Not where the recall would be cancelled or not started, nor out of a pocket (its own way).
    // Carrying too (a recall keeps the gems), with the bag's walk to an altar then from the group.
    // While repricing, our own recall is the one channelling.
    const bool recall_out = !in_pocket && !stunned_turn && !memory.siege
                            && !test(map.ally_spawn, here) && (repricing || !channelling()) && !safety.threatened(here)
                            && recall_outruns(safety, repricing ? static_cast<int>(my_channel_time()) : recall_turns(world));
    const FarmRecall via_recall = recall_out ? farm_recall(world, pathing, repricing ? static_cast<int>(my_channel_time()) : recall_turns(world)) : FarmRecall{};
    std::optional<Field> from_here;
    int centred = 0; // centre fields made in place of from_here
    const Field* to_altar = banks_bag ? &pathing.to_any_altar() : nullptr;
    const int left = bag_rounds_left(world);
    // A bag rides a recall home when that reaches an altar sooner (recall_to_bank). Started during
    // a capture, the recall lands as it pays (capture_recall). Once a group's gems make the bag
    // win, the stop on spawn is worth nothing.
    std::optional<HomeTrip> trip_home, winning_trip;
    if (to_altar) {
        trip_home = winning_trip = home_trip(world, pathing, recall_turns(world), winning_bag(world));
        winning_trip->heal = winning_trip->emblem = 0;
    }
    // A bag by way of spawn reaches the group healed and shopped: its trip on to an altar is
    // worth no second stop.
    std::optional<HomeTrip> healed_home, healed_winning;
    if (to_altar && recall_out) {
        healed_home = *trip_home, healed_winning = *winning_trip;
        healed_home->heal = healed_home->emblem = 0, healed_home->hurt = healed_winning->hurt = 0;
    }
    const float bank_now = to_altar && to_altar->at(here) != unreachable ? trip_home->rounds(to_altar->at(here), 0, 0) : 0.0f;
    float from_altar_value = 0;
    // Kited groups too costly for us alone (risky) only when nothing else is left: idling is worse.
    int best = -1, best_steps = unreachable, risky = -1, risky_steps = unreachable, shared = -1, shared_steps = unreachable;
    bool best_spell = false;
    float best_value = 0, risky_value = 0, shared_value = 0;
    // How the best and the share were priced, for the traces and the proposal: mode (S alone, K
    // kited, C crew, J joining), our extra trips home, the crew's tank, its expected allies, its output.
    struct Priced {
        char mode = '-';
        int trips = 0, tank = -1, expected = 0;
        float output = 0, damage = 0; // damage: ours, after our emblems
    };
    Priced best_priced, shared_priced;
    // An ally in sight clearing its claimed damaging group gets help only if finishing it alone
    // would take it below the recall line: one champion per camp otherwise.
    const auto struggling = [&](int g) __attribute__((always_inline)) {
        if (!claimed_by_ally(g)) return false;
        for (const auto& a : world.allies) {
            if (a.is_self || !a.alive || !a.visible || comms::claim_of(world, a.index) != g || !test(groups[g].threat(), a.pos))
                continue;
            float rounds = 0;
            const float damage = a.camp_taken * min_camp_damage(world, g, camp_output(a), &rounds, a.retaliation(), a.facts().attack_range(), home_survivable(a));
            if (a.health - damage < params::recall_health_fraction * a.max_health) return true;
        }
        return false;
    };
    // Joining allies on a group, our part of its gems is our share of the damage still to deal
    // when we arrive, and of the camps' hits.
    struct CrewWork {
        float output = 0, delayed_damage = 0;
    };
    const vec2 spawn_lo = ally_spawn_box(map).first, spawn_hi = ally_spawn_box(map).second;
    struct WorkArrival {
        int anchor_round = -1, member = -1, reach = 0, distance = unreachable, spawn_distance = unreachable;
        int dash_ready = 0, direct = 0, recall_delay = 0, recall_route = unreachable, earliest = 0;
        int delay(int round, int waiting = 0) const {
            return anchor_round < 0 ? 0 : std::max(0, anchor_round + earliest - round - waiting);
        }
    };
    const auto work_arrival = [&](const ChampionBelief& a, int g) __attribute__((always_inline)) {
        WorkArrival arrival;
        const bool seen_anchor = !a.visible && a.pos_source == Source::seen && a.pos_round == a.stats_round
                                 && a.stats_round > 0 && in_bounds(a.pos) && a.seen_channel != Channel::teleport;
        if ((!a.visible && !seen_anchor) || a.channel == Channel::teleport) return arrival;
        const auto& group = groups[g];
        const auto& belief = world.camps[g];
        arrival.anchor_round = a.visible ? world.round : a.stats_round;
        const auto& f = a.facts();
        const int dash = f.slot_of(AbilityKind::dash);
        arrival.dash_ready = dash >= 0 ? a.ready_round[dash] - arrival.anchor_round : 0;
        const int first_turn = a.acted ? 1 : 0;
        // Allies' Home ownership is unknown: allow the fastest new recall and a ready dash on arrival.
        arrival.recall_delay = a.seen_channel == Channel::recall && a.recall_kept ? std::max(0, a.channel_end_round - arrival.anchor_round)
                                                              : first_turn + home_recall_time;
        KeptArrival* kept = nullptr;
        if (static_cast<std::size_t>(g) < kept_arrival.size() && static_cast<std::size_t>(a.index) < kept_arrival[0].size()) {
            kept = &kept_arrival[static_cast<std::size_t>(g)][static_cast<std::size_t>(a.index)];
            if (kept->known && kept->visible == a.visible && kept->x == a.pos.x && kept->y == a.pos.y && kept->version == belief.geometry_version && kept->dash_ready == arrival.dash_ready
                && kept->recall_delay == arrival.recall_delay && kept->first_turn == first_turn) {
                if (kept->earliest < 0) return WorkArrival{};
                arrival.earliest = kept->earliest;
                return arrival;
            }
            *kept = {true, a.visible, a.pos.x, a.pos.y, belief.geometry_version, arrival.dash_ready, arrival.recall_delay, first_turn, -1};
        }
        // Not basic_reach(): Varg's splash reaches a member only through a hit on one within its attack range.
        arrival.reach = f.attack_range();
        // Readiness and walking exclusions can only delay this earliest effect.
        for (const auto& ability : f.abilities)
            if (ability.kind == AbilityKind::damage) arrival.reach = std::max(arrival.reach, ability.reach());
            else if (ability.lands()) arrival.reach = std::max(arrival.reach, ability.radius);
        const bool alive = belief.state == CampState::alive;
        const int n = static_cast<int>(group.members.size());
        // Only `earliest` is read: a member in reach makes it 0 whatever the rest.
        for (int i = 0; i < n; ++i) {
            if (alive && belief.health[i] <= 0) continue;
            if (const int d = dist(a.pos, group.members[i].pos); d < arrival.distance) {
                arrival.distance = d, arrival.member = i;
                if (d <= arrival.reach) break;
            }
        }
        if (arrival.member < 0) return WorkArrival{};
        const int dash_steps = dash >= 0 ? f.abilities[dash].range() : 0;
        const bool dash_maybe_ready = a.cooldowns_uncertain();
        arrival.direct = earliest_work_delay(arrival.distance - arrival.reach, first_turn, arrival.dash_ready, dash_steps,
                                            ability_cooldown, dash_maybe_ready);
        // By way of spawn takes at least the recall: only then can it beat the walk.
        if (arrival.direct > arrival.recall_delay && !map.ally_spawn_tiles.empty())
            for (int i = 0; i < n; ++i) {
                if (alive && belief.health[i] <= 0) continue;
                const auto p = group.members[i].pos;
                const int dx = std::max({spawn_lo.x - p.x, 0, p.x - spawn_hi.x});
                const int dy = std::max({spawn_lo.y - p.y, 0, p.y - spawn_hi.y});
                arrival.spawn_distance = std::min(arrival.spawn_distance, std::max(dx, dy));
            }
        arrival.recall_route = arrival.spawn_distance == unreachable ? unreachable
                                   : arrival.recall_delay + earliest_work_delay(arrival.spawn_distance - arrival.reach, 0, 0, dash_steps,
                                                                               ability_cooldown, dash_maybe_ready);
        arrival.earliest = std::min(arrival.direct, arrival.recall_route);
        if (kept) kept->earliest = arrival.earliest;
        return arrival;
    };
    // From the crew table's claimers (`allies`), or without one from the allies themselves: a table
    // costs more to read than one pass, so a group no plan prices does not read it.
    const auto crew_work = [&](const CrewAllies* allies, int g, int working, int waiting) __attribute__((always_inline)) {
        CrewWork total;
        const auto add = [&](const ChampionBelief& a, float output) __attribute__((always_inline)) {
            total.output += output;
            if (working == 0) return; // no rounds of ours for its delay to take
            const auto arrival = work_arrival(a, g);
            // Age the work round from the observation, never a guessed hidden position or turn order.
            const int delay = arrival.delay(world.round, waiting);
            total.delayed_damage += output * static_cast<float>(std::min(working, delay));
        };
        if (!allies) {
            for (const auto& a : world.allies)
                if (!a.is_self && a.alive && comms::claim_of(world, a.index) == g) add(a, camp_output(a));
            return total;
        }
        for (int k = 0; k < allies->n_claiming; ++k)
            if (const auto& x = allies->at[allies->claiming[static_cast<std::size_t>(k)]]; x.claim == g) add(*x.a, crew_output(x));
        return total;
    };
    // For the prunes' bounds: an ally in reach with no claim of its own may share a clear.
    float unclaimed_partner_output = 0;
    for (const auto& a : world.allies)
        if (!a.is_self && a.alive && a.visible && dist(here, a.pos) <= params::partner_radius && comms::claim_of(world, a.index) < 0)
            unclaimed_partner_output = std::max(unclaimed_partner_output, camp_output(a));
    const auto centre_field = [&](int g) __attribute__((always_inline)) {
        auto& known = group_facts[g];
        if (!known.centre) known.centre = pathing.from_centre(g);
        return known.centre;
    };
    const auto gap = [&](int g) __attribute__((always_inline)) {
        auto& known = group_facts[g];
        if (!map.from_ally_spawn_ready()) return static_cast<float>(home_gap(map, g, range)); // a bound until the field is made
        if (known.gap_range != range) known.gap = home_gap(map, g, range), known.gap_range = range;
        return static_cast<float>(known.gap);
    };
    // The first turn's walk from our spawn to a group: the drafted steps (home_side reads them too).
    const auto opening_steps = [&](int g) __attribute__((always_inline)) {
        const int steps = map.ally_steps(g);
        return steps != unreachable ? steps : dist(map.ally_spawn_centre, groups[g].centre);
    };
    // Health lost to camps comes back only on spawn: a heal trip from the group's nearest stand (home_gap).
    const auto heal = [&](int g, float damage) __attribute__((always_inline)) {
        if (damage <= 0) return 0.0f;
        int out = opening ? opening_steps(g) : group_facts[g].to_spawn;
        if (out < 0) out = group_facts[g].to_spawn = pathing.centre_to_spawn(g);
        return out == unreachable ? 0.0f : heal_rounds(world, damage, gap(g), static_cast<float>(out));
    };
    // Steps from our spawn's centre tile, where a recall lands, to a group's centre.
    const auto spawn_steps = [&](int g) __attribute__((always_inline)) {
        int& out = group_facts[g].to_spawn;
        if (out < 0) out = pathing.centre_to_spawn(g);
        return out;
    };
    // A trip home for health (heal_trip): from the group's nearest stand off our spawn, walking home and
    // back or by a recall and the walk from spawn back to the group (`steps`, the walk from here, where
    // none from spawn is known).
    const auto home_trip = [&](int g, int steps) __attribute__((always_inline)) {
        int out = opening ? opening_steps(g) : spawn_steps(g);
        if (out == unreachable) out = steps;
        return heal_trip(world, gap(g), static_cast<float>(out));
    };
    // An ally claims a strong live group: an operation under way.
    std::optional<bool> rival;
    const auto rival_op = [&]() {
        if (!rival) {
            rival = false;
            for (const auto& a : world.allies)
                if (const int c = comms::claim_of(world, a.index); !a.is_self && c >= 0 && c < static_cast<int>(groups.size()) && strong(c)) rival = true;
        }
        return *rival;
    };
    // Available allies are expected on a strong group unless an operation on it failed lately or
    // an enemy in sight stands near it: a crew there walks into a fight, not a clear.
    const auto may_expect = [&](int g) {
        if (g < static_cast<int>(memory.crew_ban.size()) && memory.crew_ban[g] > world.round) return false;
        for (const auto& e : world.enemies)
            if (e.alive && e.visible && dist(e.pos, groups[g].centre) <= params::crew_enemy_radius) return false;
        return true;
    };
    // A Monolith operation is long: one member leaving it shrinks the crew for the rest for longer.
    const auto crew_hold = [&](int g) { return groups[g].has_monolith ? params::mono_stickiness : params::crew_stickiness; };
    // A Monolith takes the whole team.
    const auto crew_cap = [&](int g) { return groups[g].has_monolith ? static_cast<int>(world.allies.size()) : params::crew_cap; };
    // Read on first need. Static: its vec2s would be zeroed on every call.
    static CrewAllies crew_table;
    bool crew_read = false;
    const auto crew_allies_now = [&]() -> const CrewAllies& {
        if (!crew_read) crew_allies(world, line, crew_table), crew_read = true;
        return crew_table;
    };
    // Our camp damage in a crew's clear (share_damage), after our emblems and shield.
    const auto crew_share = [&](const CrewPlan& plan, int arrive) {
        return shielded_clear(soften * plan.my_damage, plan.rounds, shield, std::max(0.0f, shield_ready_in - static_cast<float>(arrive)));
    };
    // The prunes' bounds for a strong group, whose crew may clear it: a crew is us and living
    // allies, each once, so its output O is at most the whole team's; we get our part S / O (all of
    // a winning capture) and its clear takes at least our fastest times S / O. Only our claim's hold
    // (crew_hold) raises it. So a rated bound is crew_rate's up to the team's output (`crew_most`),
    // a plain ratio worth / (trip + fastest S / O) falls with O and stays ours, and a winning
    // capture's bounds take the fastest at the team's output (prune_fastest). Except for our claim
    // or Monolith operation, and for Ren, whose plain prunes are no bound.
    const auto held = [&](int g) __attribute__((always_inline)) { return (g == memory.claim || g == memory.mono_group) && strong(g); };
    const auto prunable = [&](int g) __attribute__((always_inline)) { return !strong(g) || (reflect <= 0 && !held(g)); };
    float crew_scale = -1;
    const auto team_scale = [&]() __attribute__((always_inline)) {
        if (crew_scale < 0) {
            float team = strength;
            for (const auto& a : world.allies)
                if (!a.is_self && a.alive) team += camp_output(a);
            crew_scale = strength / team;
        }
        return crew_scale;
    };
    // The team's output over ours for a strong group short of the win, else 0 (no crew bound).
    const auto crew_most = [&](int g, bool wins) __attribute__((always_inline)) { return strong(g) && !wins ? 1.0f / team_scale() : 0.0f; };
    const auto prune_fastest = [&](int g, float fastest, bool wins) __attribute__((always_inline)) {
        return strong(g) && wins ? fastest * team_scale() : fastest;
    };
    // After the tribute, the walk out from the altar or a recall and the walk from spawn.
    const auto altar_out = [&](int g, int walk) __attribute__((always_inline)) {
        if (walk == unreachable) return walk;
        const int out = spawn_steps(g);
        return out == unreachable ? walk : std::min(walk, recall_turns(world) + out);
    };
    const auto respawn_in = [&](const CampBelief& belief) __attribute__((always_inline)) {
        return belief.state == CampState::respawning ? std::max(0, belief.respawn_round - world.round) : 0;
    };
    // The trip by way of spawn from as close as the Chebyshev distance, for the prunes' bounds.
    const vec2 spawn_centre = map.ally_spawn_centre;
    const auto via_bound = [&](int spawn_near, int respawn) __attribute__((always_inline)) {
        return recall_out ? via_recall.rounds(spawn_near, respawn) : static_cast<float>(unreachable);
    };
    // The soonest trip to a group `near` away as the crow flies: walking, or by way of spawn.
    const auto soonest = [&](const CampGroup& group, const CampBelief& belief, int near) __attribute__((always_inline)) {
        const int respawn = respawn_in(belief);
        return std::min(static_cast<float>(std::max(near, respawn)), via_bound(dist(spawn_centre, group.centre), respawn));
    };
    int help_group = -1, help_steps = unreachable;
    // Middle-band pricing: a group in the middle band is worth mid_exposure of itself. The prunes
    // below that take the weight as at most 1 scale by params::max_exposure, the bounds by exposure_most.
    const auto exposure_of = [&](int g) {
        const float s = home_side(map, g, opening);
        // Smoothstep over [bound - mid_edge, bound + mid_edge] at each bound, so near-identical groups weigh alike.
        const auto ease = [](float x) {
            x = std::clamp(x, 0.0f, 1.0f);
            return x * x * (3.0f - 2.0f * x);
        };
        constexpr float e = params::mid_edge;
        const float in = std::min(ease((s - params::mid_low_share + e) / (2 * e)), ease((params::own_ground_share + e - s) / (2 * e)));
        return 1.0f + (params::mid_exposure - 1.0f) * in;
    };
    // home_side keeps a group's side once read (the first 256), so its exposure is fixed with it.
    static std::array<float, 256> exposure_kept = [] {
        std::array<float, 256> a;
        a.fill(-1);
        return a;
    }();
    const auto exposure = [&](int g) __attribute__((always_inline)) {
        if (static_cast<std::size_t>(g) >= exposure_kept.size()) return exposure_of(g);
        float& e = exposure_kept[static_cast<std::size_t>(g)];
        if (e < 0) e = exposure_of(g);
        return e;
    };
    // First readings of each group (clears, fields) can cost several times the estimate: stop with
    // enough left for the walk after it, and read last turn's choice first so that a cut-short loop
    // still weighs it. Without one, the nearest group worth farming as the crow flies.
    int first = memory.farm_group >= 0 && memory.farm_group < n_groups ? memory.farm_group : -1;
    if (first < 0) {
        int nearest = unreachable;
        for (int g = 0; g < n_groups; ++g) {
            if (groups[g].has_monolith || groups[g].gems + groups[g].gold == 0) continue;
            const int steps = dist(here, groups[g].centre);
            if (steps < nearest) first = g, nearest = steps;
        }
        if (first < 0) first = 0;
    }
    const int evaluated = n_groups;
    // Nothing in the loop moves us or changes the fields walk_reserve reads.
    int reserved_for = -2;
    std::uint64_t reserved = 0;
    // With the dash ready the walk is also a travel plan (Pathing::travel: its plan ~8k, the crossing trace ~3k).
    const int dash_slot = world.me().facts().slot_of(AbilityKind::dash);
    const std::uint64_t travel = dash_slot >= 0 && my_can_cast() && my_cooldown(dash_slot) <= 0 ? travel_cost_estimate : 0;
    // On the first turn no turn end has decoded the choice's attack tiles yet: the walk decodes
    // them (farm_attack_tiles). Later the turn-end queue decodes the nearest groups' first.
    int tiles_for = -2;
    std::uint64_t decode = 0;
    const auto tiles_reserve = [&]() __attribute__((always_inline)) {
        if constexpr (opening)
            if (const int g = best >= 0 ? best : memory.farm_group; g != tiles_for) tiles_for = g, decode = attack_tiles_cost(world, pathing, g, range);
        return decode;
    };
    // The pack zone, drawn after the loop, comes out of the loop's budget too.
    const auto loop_floor = small_cost_estimate + end_reserve + (zoned ? pack_zone_cost_bound : 0);
    // After the first turn: what the rest of the turn spends before the turn order (which keeps
    // end_reserve), by banking and a ready dash, per search chunk and per chunk and layer of the walk
    // to the choice: its 95th percentile on cut loops at the real budget walking without a dash, the
    // 96-98th otherwise. Its route search and travel plan are most of it; the approach search the first
    // turn keeps back for runs on a tenth of cut turns, and banking walks cost less than their layers say.
    struct AfterLoop {
        std::uint64_t base, per_chunk, quarters_per_layer;
    };
    const AfterLoop after = banks_bag ? (travel ? AfterLoop{24700, 40, 2} : AfterLoop{20400, 0, 3})
                                      : (travel ? AfterLoop{21400, 30, 6} : AfterLoop{16400, 30, 3});
    const std::uint64_t chunks = search_chunks();
    const int most_layers = map.width + map.height + max_detour;
    const auto after_loop = [&](int layers) __attribute__((always_inline)) {
        const auto l = static_cast<std::uint64_t>(std::clamp(layers, 0, most_layers));
        return end_reserve + after.base + chunks * after.per_chunk + chunks * after.quarters_per_layer * l / 4;
    };
    // With the floor included.
    const auto loop_reserve = [&]() __attribute__((always_inline)) {
        const int g = best >= 0 ? best : memory.farm_group;
        if (g != reserved_for) {
            reserved_for = g;
            const int layers = g < 0 ? 0 : (g == best ? best_steps : dist(here, groups[g].centre)) + max_detour;
            if constexpr (opening) {
                reserved = loop_floor + walk_reserve(g);
                if (g >= 0) reserved += search_cost_estimate(layers) + travel + tiles_reserve();
            } else {
                reserved = g < 0 ? loop_floor : after_loop(layers);
            }
        }
        return reserved;
    };
    // With the costliest approach and route to spare, the reserve need not be read.
    const auto ample = opening ? loop_floor + 2 * pathing.max_approach_cost() + travel : after_loop(most_layers);
    const std::uint64_t decode_bound = opening ? attack_tiles_cost_bound(map) : 0;
    // Nothing in the loop changes memory, the round or the warm-up.
    const int round = world.round, farm_group = memory.farm_group;
    const bool crew_of_choice = memory.claim == farm_group && memory.crew;
    // taken() as a mask.
    auto claimed_bits = ally_claims;
    if (memory.claim >= 0 && memory.claim < 256 && !memory.crew)
        claimed_bits[memory.claim >> 6] &= ~(std::uint64_t{1} << (memory.claim & 63));
    // Draft spawn distances use walking walls; dashers keep the live field's graph unless the plan
    // says the two agree.
    static const bool draft_spawn_graph = !world.me().facts().has_dash() || map.crossable.is_empty() || map.dash_spawn_steps_drafted();
    // The draft's dash steps (a dasher's otherwise from a field from here) take ~150 fuel a group to
    // decode: on a small map the field is cheaper.
    const int dash_kind = farm_dash_kind<opening>(world, n_groups);
    const CampGroup* const group_data = groups.data();
    const CampBelief* const camp_data = world.camps.data();
    int* const steps_data = centre_steps.data();
    const int bag_tribute = bag > 0 ? tribute_turns(world, bag) : 0;
    int crystal = -1; // read on first need: 2 carried, 1 to buy, 0 neither
    // Nearest to last turn's choice first: a loop cut short has weighed the likeliest groups, and
    // an early good best prunes the rest sooner. With no choice yet, by index from `first`.
    const auto* order = memory.farm_group == first ? map.nearest_groups(first) : nullptr;
    // The prunes' bounds hold but for Ren, whose reflection clears faster than its output, and in a
    // pocket, whose recall out can beat the Chebyshev distance.
    const bool tight = reflect <= 0 && !in_pocket;
    // The first turn's extra prunes: later loops start from last turn's choice, and the plain
    // bound already skips most groups for less. Ren's take reflected_clear for the fastest; its
    // plain prunes, which its reflection can beat, still decide, so its order stays.
    const bool rated = opening && !in_pocket && !recall_out; // the first turn starts on spawn: never recall_out
    // The draft's guesses at the first choice (DraftPlan's leads) go first: an early good best
    // prunes the rest. As the prunes skip only groups that cannot reach the best, and ties still go
    // to the earlier group in the usual order, the choice is the usual one.
    static std::vector<std::uint8_t> led;
    int n_lead = 0;
    if (opening && !order && tight && evaluated == n_groups && n_groups <= 256) {
        std::array<int, DraftPlan::leads> lead;
        n_lead = map.drafted_leads(world.me().index, lead);
        if (n_lead > 0) {
            static_assert(DraftPlan::leads == 2);
            if (static_cast<int>(led.size()) != n_groups) led.resize(n_groups);
            std::uint8_t* out = led.data();
            const int l0 = lead[0], l1 = n_lead > 1 ? lead[1] : -1;
            out[0] = static_cast<std::uint8_t>(l0);
            int w = 1;
            if (l1 >= 0) out[w++] = static_cast<std::uint8_t>(l1);
            for (int g = first; g < n_groups; ++g)
                if (g != l0 && g != l1) out[w++] = static_cast<std::uint8_t>(g);
            for (int g = 0; g < first; ++g)
                if (g != l0 && g != l1) out[w++] = static_cast<std::uint8_t>(g);
            order = &led;
        }
    }
    // Once a share is set (shared_value > 0), an own group whose value stays below it changes no
    // pick: the share wins unless the best beats it, and below it the best only wins if the share
    // does not. So the prunes below skip own groups under max(best_value, floor). Not banking (its
    // pick reads best_value against the cycle from the altar), nor where best_value is read past
    // that test: kited groups (the risky pick when no best is set) and a takeover in reach (its work
    // rate is best_value). Ties go to the best, so the floor prunes only what is strictly below it.
    float floor_value = 0;
    int floor_ok = -1; // read on the first share
    const auto may_floor = [&]() {
        if (floor_ok < 0) {
            static const bool any_kited = [&] {
                for (int g = 0; g < n_groups; ++g)
                    if (kited(g)) return true;
                return false;
            }();
            bool takeover = false;
            if (!memory.banking)
                world.each_cleared([&](int g) {
                    takeover = takeover || (steps_to(groups[g], here) < cambc::constants::capture_time && allies_on(world, groups[g].tiles()) > 0
                                            && pathing.to_group(g).at(here) < cambc::constants::capture_time);
                });
            floor_ok = !banks_bag && !any_kited && !takeover;
        }
        return floor_ok > 0;
    };
    // Groups under these are pruned: `bar_lt` for tests `x < bar`, `bar_le` for `x <= bar`; `barred`
    // while either is set.
    const auto barred = [&]() __attribute__((always_inline)) { return best >= 0 || floor_value > 0; };
    const auto bar_lt = [&]() __attribute__((always_inline)) { return best >= 0 ? std::max(best_value, floor_value) : floor_value; };
    const auto bar_le = [&]() __attribute__((always_inline)) {
        const float below = floor_value > 0 ? std::nextafter(floor_value, 0.0f) : 0.0f;
        return best >= 0 ? std::max(best_value, below) : below;
    };
    // rated_beaten by the best so far. Callers leave out our last choice, whose clear a partner
    // claiming it may share.
    const auto beaten = [&](float worth, float trip, float fastest, int walk, float cycle_bank, float crew) __attribute__((always_inline)) {
        return rated_beaten(world, worth, trip, fastest, strength, unclaimed_partner_output, bar_lt(),
                            banks_bag ? from_altar_value : -1.0f, walk, cycle_bank, crew);
    };
    // rated_beaten before farm reads the group's facts, with its turn constants hoisted: empty-handed
    // and short of the win, no walk to an altar is in the trip and the weight is at most 1. Each rate
    // is tested alone, as the larger of the two fails the test exactly when either does.
    const int capture = capture_rounds(world);
    const float cap_rounds = static_cast<float>(capture);
    const float horizon = cycle_horizon(map);
    const float partner_part = unclaimed_partner_output > 0 ? strength / (strength + unclaimed_partner_output) : 0.0f;
    const auto rated_below = [&](float worth, float trip, float fastest, float crew) __attribute__((always_inline)) {
        const auto rated = [&](float w, float rounds) __attribute__((always_inline)) {
            rounds = std::max(rounds, 1.0f);
            return w / (rounds * (1.0f + rounds / horizon));
        };
        const float near_trip = trip + cap_rounds;
        // The slack covers float rounding where a clear takes exactly the fastest.
        worth *= params::max_exposure * pull.deny_scale;
        if (crew > 0) { // crew_rate's
            const float k = std::clamp(fastest / std::sqrt(near_trip * (horizon + near_trip)), 1.0f, crew);
            return rated(worth / k, near_trip + fastest / k) * 1.0001f < bar_lt();
        }
        const float bar = bar_lt();
        return rated(worth, near_trip + fastest) * 1.0001f < bar
               && (unclaimed_partner_output <= 0 || rated(worth * partner_part, near_trip + fastest * partner_part) * 1.0001f < bar);
    };
    const auto unweighed_beaten = [&](const CampGroup& group, const CampBelief& belief, int g, float trip) __attribute__((always_inline)) {
        const int gems = std::min(group.gems + (prospector ? prospected(group.cluster_gems, 1) : 0), short_by);
        const int gold = group.gold + (prospector ? prospected(group.cluster_gold, 1) : 0);
        const float worth = static_cast<float>(gems) + per_gold * static_cast<float>(gold) + bound_tribute * static_cast<float>(gems);
        // At version 0 every member is alive at full health: the bound needs no pass over them.
        const float fastest = reflect > 0          ? reflected_clear(world, g, strength, reflect)
                              : belief.version == 0 ? group.health / strength
                                                    : fastest_clear(world, g, strength);
        return rated_below(worth, trip, fastest, crew_most(g, false));
    };
    const int* worth_gems = nullptr;
    const float* worth_gold = nullptr;
    if constexpr (!opening) {
        if (static_cast<int>(memo.worth_gems.size()) != n_groups || memo.worth_prospector != prospector) {
            memo.worth_prospector = prospector;
            memo.worth_gems.resize(n_groups), memo.worth_gold.resize(n_groups);
            for (int g = 0; g < n_groups; ++g) {
                const auto& G = groups[g];
                memo.worth_gems[g] = G.gems + (prospector ? prospected(G.cluster_gems, 1) : 0);
                memo.worth_gold[g] = static_cast<float>(G.gold + (prospector ? prospected(G.cluster_gold, 1) : 0));
            }
        }
        worth_gems = memo.worth_gems.data(), worth_gold = memo.worth_gold.data();
    }
    // The wait for a group respawning when we would arrive, and whether it may be the group we
    // help (no bound covers that) for a walk of at least `near`.
    const auto near_wait = [&](const CampBelief& belief, int near) __attribute__((always_inline)) {
        return belief.state == CampState::respawning ? std::max(0, belief.respawn_round - round - near) : 0;
    };
    const auto may_help = [&](const CampGroup& group, const CampBelief& belief, int near) __attribute__((always_inline)) {
        return !banks_bag && group.strength > 0 && belief.state == CampState::alive && near <= params::help_radius
               && (near < help_steps || (n_lead > 0 && near == help_steps));
    };
    // With leads first, ties still go to the group earlier in the usual order.
    const auto earlier = [&](int g, int than) __attribute__((always_inline)) {
        return n_lead > 0 && than >= 0 && (g - first + n_groups) % n_groups < (than - first + n_groups) % n_groups;
    };
    const auto is_claimed = [&](int g) __attribute__((always_inline)) { return g < 256 && (claimed_bits[g >> 6] >> (g & 63) & 1); };
    // Nearest to `first` first, every group from position k on is at least r_k - D from here (r_k
    // from first's centre, D ours to it) and walks no fewer steps. Once the most any of them holds,
    // that close and cleared at once, cannot beat the best (only rising), none of them can change
    // the choice: weight is at most 1 off our last choice, and with no bag to bank the trip is at
    // least the steps. Past help_radius none is helped. Still weighed: a crew's share (no capture
    // in its cycle) and crystal hops (shorter than the crow flies).
    // Banking, the trip is at least the steps less bank_now (bank >= 0), and a group skipped must
    // also not raise from_altar_value (at most its worth over its altar walk and the capture) to the
    // larger of the best and from_altar_value: below it, it changes neither the choice nor whether
    // we bank, as both only rise.
    const bool hop_any = map.any_group_hop(); // group_hop(g) >= 0 only then
    const bool can_bound = !opening && order && !in_pocket;
    const bool hops = can_bound && hop_any;
    const int offset = dist(here, groups[first].centre);
    const float most_tribute = std::max(0.0f, tribute_gold) + keep_most, most_per_gold = std::max(0.0f, per_gold);
    const FarmMemo::Most* most = nullptr;
    float tested_value = 0; // the threshold the stop was searched for
    const auto threshold = [&]() __attribute__((always_inline)) { return banks_bag ? std::max(best_value, from_altar_value) : bar_lt(); };
    const auto beyond = [&](int j) __attribute__((always_inline)) {
        const auto& m = most[j];
        const int near = m.near - offset;
        if (!banks_bag && near <= params::help_radius) return false;
        const int gems = std::max(0, std::min(prospector ? m.gems_prospected : m.gems, short_by));
        const float worth = params::max_exposure * pull.deny_scale * (static_cast<float>(gems) * (1.0f + most_tribute)
                            + most_per_gold * static_cast<float>(prospector ? m.gold_prospected : m.gold));
        const float via = via_bound(m.spawn_near, 0);
        if (banks_bag) return rate(world, worth, std::max(0.0f, std::min(static_cast<float>(near), via) - bank_now) + cap_rounds) * 1.0001f < tested_value;
        return rate(world, worth, std::min(static_cast<float>(near), via) + cap_rounds) * 1.0001f < tested_value;
    };
    // Banking: whether the group's cycle from the altar stays below the threshold.
    const auto altar_below = [&](int g) __attribute__((always_inline)) {
        const int walk = altar_out(g, pathing.centre_to_altar(g));
        if (walk == unreachable) return true;
        const int gems = std::max(0, std::min(worth_gems[g], short_by));
        const float worth = params::max_exposure * pull.deny_scale * (static_cast<float>(gems) * (1.0f + most_tribute) + most_per_gold * worth_gold[g]);
        return rate(world, worth, static_cast<float>(walk) + cap_rounds) * 1.0001f < tested_value;
    };
    // The first position the bound covers. It holds from there on (r_k rises, the most held falls),
    // so it is searched for, and again only when the best rises.
    int stop = n_groups;
    const auto stop_from = [&](int k) {
        if (!most) {
            auto& most_from = memo.most_from;
            auto& reach = memo.reach;
            if (static_cast<int>(most_from.size()) != n_groups) {
                most_from.clear(), most_from.resize(n_groups);
                reach.resize(n_groups);
                for (int g = 0; g < n_groups; ++g) {
                    const auto& G = groups[g];
                    reach[g] = {G.gems + prospected(G.cluster_gems, 1), G.gold + prospected(G.cluster_gold, 1), dist(map.ally_spawn_centre, G.centre)};
                }
            }
            auto& from_first = most_from[first];
            if (!from_first) {
                from_first.reset(new FarmMemo::Most[n_groups]);
                FarmMemo::Most* const out = from_first.get();
                const FarmMemo::Reach* const r = reach.data();
                const std::uint8_t* const at = order->data();
                const vec2 origin = groups[first].centre;
                FarmMemo::Most run{0, 0, 0, 0, 0, unreachable};
                for (int j = n_groups - 1; j >= 0; --j) {
                    const int g = at[j];
                    const auto& G = group_data[g];
                    run.gems = std::max(run.gems, G.gems), run.gold = std::max(run.gold, G.gold);
                    run.gems_prospected = std::max(run.gems_prospected, r[g].gems_prospected);
                    run.gold_prospected = std::max(run.gold_prospected, r[g].gold_prospected);
                    run.near = dist(origin, G.centre);
                    run.spawn_near = std::min(run.spawn_near, r[g].spawn_near);
                    out[j] = run;
                }
            }
            most = from_first.get();
        }
        int lo = k, hi = stop;
        while (lo < hi)
            if (const int mid = (lo + hi) / 2; beyond(mid)) hi = mid;
            else lo = mid + 1;
        return lo;
    };
    // Fuel rises within a turn only when the engine resumed it, a round late: a stale tail leaves
    // at once instead of weighing groups on the next round's budget.
    std::uint64_t seen = ~std::uint64_t{0};
    const auto room = [&]() __attribute__((always_inline)) {
        const std::uint64_t left = fuel();
        if (left > seen) world.throw_if_stale();
        seen = left;
        return left >= ample + decode_bound || left >= loop_reserve();
    };
    float mono_seen = -1; // for the traces: our Monolith operation's value this turn, -1 if not reached
    // The pre-facts prunes below, bounded before each group's facts (PreLanes): a group whose
    // upper bound is below best_value, which only rises, is pruned there, with nothing read or kept
    // in between. Not for Ren (reflected clears skip the prunes of strong groups) or with crystal
    // hops (group_hop works on a timetable); nor with no strength (clears of no length). The first
    // turn's bound, without its clears, prunes little on maps of fewer groups: there the pass and
    // its tables cost more than they save.
    const bool pre_pruned = !pull.on && !banks_bag && !hop_any && reflect <= 0 && strength > 0 && (opening ? rated && n_groups >= 128 : tight);
    // Banking: groups that change neither the best nor the cycle from the altar (PreUpper).
    const bool pre_banked = !pull.on && banking && !hop_any && strength > 0;
    static std::vector<float> pre_upper, pre_alt, pre_test, pre_test_alt, pre_value, pre_old, pre_old_alt;
    // claim_most reads worth_gems and worth_gold, which the first turn has none of.
    const bool pre_valued = pre_pruned && !opening, pre_claims = !opening && (pre_pruned || pre_banked);
    const float* pre_health = nullptr;
    // Claims, our last choice and groups whose crew we hold are never pruned before facts.
    std::array<int, 3> pre_kept{-1, -1, -1};
    PreUpper p{};
    if (pre_pruned || pre_banked) {
        if (static_cast<int>(pre_upper.size()) < n_groups + 3) {
            for (auto* v : {&pre_upper, &pre_alt, &pre_test, &pre_test_alt, &pre_value, &pre_old, &pre_old_alt}) v->resize(n_groups + 3);
        }
        p.here = here, p.short_by = short_by, p.per_gold = per_gold, p.tribute_gold = bound_tribute;
        p.cap_rounds = cap_rounds, p.horizon = horizon, p.recall_out = recall_out, p.prospector = prospector, p.via = via_recall;
        p.banking = pre_banked, p.bank_now = bank_now, p.recall = pre_banked ? recall_turns(world) : 0;
        // Shaved for fastest_clear's sum taken member by member.
        p.health = pre_health = world.clear_health.data(), p.clear_scale = 0.9999f / strength, p.reflects = reflect > 0;
        p.crew_most = 1.0f / team_scale(), p.other_part = unclaimed_partner_output > 0 ? partner_part : 1.0f;
        p.weight = known_weights(n_groups);
        p.out = pre_upper.data(), p.alt = pre_alt.data(), p.test = pre_test.data(), p.test_alt = pre_test_alt.data();
        p.old = pre_old.data(), p.old_alt = pre_old_alt.data();
        if (pre_valued) p.value = pre_value.data();
        if (pre_banked && trip_home) {
            const auto& t = *trip_home;
            if (t.from_spawn != unreachable) {
                const int arrive = std::max(0, t.channel - capture) + t.hurt + t.from_spawn;
                if (arrive <= t.deadline) p.bank_floor = std::max(0.0f, static_cast<float>(arrive) - std::max(t.heal, t.heal + t.emblem));
            }
        }
        pre_columns.begin(map, pre_banked);
        int i = 0;
        for (const int g : {farm_group, memory.claim, memory.mono_group})
            pre_kept[i++] = g >= 0 && g < n_groups && (g == farm_group || !prunable(g) || pre_banked) ? g : -1;
    }
    // Plain locals, read only where the pass is begun (a few splats a turn otherwise).
    const PreLanes pre_lanes(p, pre_columns);
    // Group g's bounds, read only below.
    std::uint64_t pre_done = 0; // bit b: block b written, for the first 64 (a local word: a test a group)
    const auto pre_bounds = [&](int g) __attribute__((always_inline)) {
        const int b = g >> 2;
        const std::uint64_t bit = std::uint64_t{1} << (b & 63);
        if (b < 64) {
            if (pre_done & bit) return;
            pre_done |= bit;
        } else {
            auto& word = pre_columns.done[static_cast<std::size_t>(b >> 6)];
            if (word & bit) return;
            word |= bit;
        }
        pre_lanes.block(b << 2);
        constexpr float none = std::numeric_limits<float>::infinity();
        const auto unpruned = [&](int h) __attribute__((always_inline)) {
            pre_upper[h] = none;
            if (pre_banked) pre_test[h] = none, pre_old[h] = none;
            if (pre_valued) pre_value[h] = none;
        };
        const int lo = g & ~3;
        if (lo < 256)
            for (auto bits = claimed_bits[lo >> 6] >> (lo & 63) & 15; bits; bits &= bits - 1)
                if (const int h = lo + std::countr_zero(bits); h < n_groups) unpruned(h);
        for (const int h : pre_kept)
            if ((h & ~3) == lo) unpruned(h);
    };
    // An upper bound on the claimed branch's `most` before the group's facts: its part S r / health of
    // the worth (as PreUpper's, weighted) over the trip and r rounds, r at most health / S, from
    // as close as PreUpper's trip. No bound for the win, a striker that may be helped (the help
    // call is read before the branch) or no health read. Our last choice, claim and Monolith group are
    // left out by the caller (stickiness, a crew's hold, the Monolith's).
    // Our part S r / health of a claimed group's worth over the trip and r rounds, at the r that rates
    // best within `clear` rounds: the rate rises in r up to sqrt(trip (horizon + trip)) (rounds of at
    // least 1), then falls.
    const auto claim_bound = [&](float worth, float health, float clear, float trip) __attribute__((always_inline)) {
        const float r = std::min(clear, std::max(std::sqrt(trip * (horizon + trip)), 1.0f - trip));
        return rate(world, worth * (strength * r / health), trip + r);
    };
    const auto claim_most = [&](int g) {
        constexpr float none = std::numeric_limits<float>::infinity();
        const auto& G = groups[g];
        const float health = pre_health[g];
        const int near = dist(here, G.centre);
        if (!(health > 0) || G.gems >= short_by || (!banks_bag && G.strength > 0 && near <= params::help_radius)) return none;
        float trip = static_cast<float>(near);
        // Carrying too, the recall out may be sooner.
        if (recall_out) trip = std::min(trip, via_recall.rounds(dist(spawn_centre, G.centre), 0));
        if (banks_bag) trip = std::max(0.0f, trip - bank_now);
        const float gems = static_cast<float>(std::min(worth_gems[g], short_by));
        const float worth = std::max(0.0f, gems + std::max(0.0f, per_gold) * worth_gold[g] + std::max(0.0f, tribute_gold) * gems);
        const float weight = g < 256 ? home_weights()[static_cast<std::size_t>(g)] : 1.0f;
        // The join's Focus is no share: at most its rate over the trip and the hold (rate is linear in worth).
        const float carry = gems * keep_bonus(G) * exposure_most * weight;
        return (claim_bound(worth * exposure_most * weight, health, health / strength, trip) + (carry > 0 ? rate(world, carry, trip + cap_rounds) : 0.0f))
               * 1.0002f;
    };
    static const bool any_mono = [&] {
        for (int g = 0; g < n_groups; ++g)
            if (farm_monolith(world, g)) return true;
        return false;
    }();
    // Nothing in the loop acts or moves: the travel dash stays as first read.
    int loop_dash = -2;
    const auto loop_travel_turns = [&](int steps) __attribute__((always_inline)) {
        if (loop_dash == -2) loop_dash = pathing.travel_wait();
        return Pathing::travel_turns_after(steps, loop_dash);
    };
    // By group, whether the loop priced it by way of spawn (read for the best only).
    static std::vector<std::uint8_t> routed;
    if (static_cast<int>(routed.size()) != n_groups) routed.assign(n_groups, 0);
    int k = 0;
    for (; k < evaluated && room(); ++k) {
        int g = order ? (*order)[k] : (first + k) % n_groups;
        // best_value moves only with best, from 0.
        if (can_bound && !pull.on && threshold() != tested_value) tested_value = threshold(), stop = stop_from(k);
        if (k >= stop) {
            while (k < evaluated && !is_claimed(g = (*order)[k]) && !held(g) && !(hops && map.may_hop(g)) && (!banks_bag || altar_below(g))) ++k;
            if (k == evaluated) break;
        }
        if ((pre_pruned && barred()) || (pre_banked && best >= 0)) pre_bounds(g);
        if (pre_pruned && barred() && (pre_upper[g] < bar_lt() || (pre_valued && best >= 0 && pre_value[g] < best_value))) continue;
        if (pre_claims && is_claimed(g) && (best >= 0 || shared >= 0) && g != farm_group && g != memory.claim && g != memory.mono_group) {
            const float most = claim_most(g);
            if ((best >= 0 && most < best_value) || (shared >= 0 && most < shared_value)) continue;
        }
        if (pre_banked && best >= 0
            && ((pre_upper[g] < std::min(best_value, from_altar_value) && pre_alt[g] < from_altar_value)
                || (pre_test[g] <= best_value && pre_test_alt[g] <= from_altar_value)
                || (pre_old[g] < std::min(best_value, from_altar_value) && pre_old_alt[g] < from_altar_value)))
            continue;
        const auto& group = group_data[g];
        const auto& belief = camp_data[g];
        read_g = -1, read_kited = kited_of(g), read_strong = strong_of(g), read_g = g;
        // A help call overrides the best and the share (kept off only by a Monolith best): once one is
        // set, only a group that may be a nearer help changes the pick.
        if (help_group >= 0 && !any_mono && !may_help(group, belief, dist(here, group.centre))) continue;
        // A hold by the enemy pays them, and the group respawns: contesting it is contest_capture's. A
        // live big group our kite works is kite()'s: a lone farmer would wake it on the casters. A group
        // whose siege stands we cannot hold even at full health this turn is no farm crew's either.
        if ((group.has_monolith && map.monolith_only) || group.gems + group.gold == 0
            || (belief.state == CampState::cleared && (ally_holding(g) || belief.holder == team::enemy))
            || (belief.state != CampState::cleared && kited(g) && kite_owns(world, g)) || siege_declines(world, g)
            || (belief.state == CampState::cleared && left_for_prism(world, pathing, g)))
            continue;
        // A Monolith with an enemy in sight near it is not taken up: our crew would clear it for
        // them. Unless the enemy already stands in its reach, taking the hits.
        if (group.has_monolith && g != memory.claim && belief.state != CampState::cleared && mono_contested(world, g)) continue;
        const bool claimed = is_claimed(g);
        // Carrying, compare whole trips: the gems score only after the walk to an altar and the
        // tribute. Empty-handed, only a capture that wins counts that walk, as no later one shares
        // it. Gems past the win are worth nothing.
        const bool wins = group.gems >= short_by;
        // Later turns: the same bound before facts, the fastest clear and steps, for every group (the
        // facts' weighted worth while they hold). The fastest it reads is the one the facts keep.
        if constexpr (!opening) {
            if (tight && !banks_bag && !wins && !claimed && barred() && g != farm_group && prunable(g) && (!hop_any || map.group_hop(g) < 0)) {
                if (const int near = dist(here, group.centre); !may_help(group, belief, near)) {
                    auto& kf = group_facts[g];
                    float worth;
                    if (kf.context == context && !kf.sticky && kf.gold_context == gold_context) {
                        worth = kf.gems + kf.gold + kf.gems * keep_most;
                    } else {
                        const float gems = static_cast<float>(std::min(worth_gems[g], short_by));
                        worth = gems + per_gold * worth_gold[g] + bound_tribute * gems;
                    }
                    float fastest;
                    if (kf.version == belief.version && kf.fastest_strength == strength) fastest = kf.fastest;
                    else if (belief.version == 0) fastest = group.health / strength;
                    else kf.version = belief.version, kf.fastest_strength = strength, fastest = kf.fastest = fastest_clear(world, g, strength);
                    if (rated_below(worth, soonest(group, belief, pulled_near(g, near)), fastest, crew_most(g, false))) continue;
                }
            }
        }
        // A first turn's facts cost a few hundred fuel a group. Empty-handed and short of the win
        // no walk to an altar is in the trip, and the weight is at most 1: a group the rated bound
        // rules out from as close as the Chebyshev distance needs none.
        if (rated && !banks_bag && !wins && !claimed && barred() && g != farm_group && prunable(g) && (!hop_any || map.group_hop(g) < 0)) {
            if (const int near = dist(here, group.centre); !may_help(group, belief, near)
                && unweighed_beaten(group, belief, g, static_cast<float>(near + near_wait(belief, near))))
                continue;
        }
        auto& known = group_facts[g];
        if (known.context != context || known.sticky != (g == farm_group) || known.planned != (g == planned_now)) {
            if (known.tribute == 0 || known.emblems != emblems) {
                known.emblems = emblems;
                known.tribute = tribute_turns(world, group.gems);
                const int n = holders(group);
                known.gold_in = static_cast<std::uint32_t>(group.gold / n + (prospector ? prospected(group.cluster_gold, n) : 0));
            }
            const Field* to_bank = to_altar ? to_altar : wins ? &pathing.to_any_altar() : nullptr;
            // A recall only goes home: the way out from an altar is walked.
            if (to_bank && known.to_altar < 0) known.to_altar = pathing.centre_to_altar(g);
            known.walk = to_bank ? known.to_altar : unreachable;
            // Chained, the gems join the bag's one tribute; from the altar they need their own.
            known.chained_tribute = tribute_turns(world, bag + group.gems) - (banks_bag ? bag_tribute : 0);
            // The bank terms when the way back is walked.
            const bool banks = static_cast<float>(known.walk) < static_cast<float>(unreachable);
            known.walked_bank = banks ? static_cast<float>(known.walk) + static_cast<float>(known.chained_tribute) : 0.0f;
            known.walked_cycle = banks ? static_cast<float>(known.walk) + static_cast<float>(known.tribute) : 0.0f;
            // From the draft's spawn steps; without a plan, two spawn floods once a game.
            if (known.home < 0) known.home = home_ground(map, g, opening);
            float weight = known.home;
            // Staying with last turn's choice keeps near ties from turning us back and forth.
            if (g == farm_group) weight *= stickiness;
            // The plan's group is weighted on its own: farm's last choice keeps its stickiness, so the two do not trade places.
            if (g == planned_now) weight *= params::open_plan::weight;
            // A Monolith's long clear gives the enemy time to steal it: its side counts twice.
            if (group.has_monolith) weight *= known.home;
            known.weight = weight;
            // A Prospector emblem's extra as if alone on the capture, as the reward is valued.
            known.gems = weight * static_cast<float>(std::min(group.gems + (prospector ? prospected(group.cluster_gems, 1) : 0), short_by));
            known.context = context;
            known.sticky = g == farm_group;
            known.planned = g == planned_now;
            known.gold_context = 0;
        }
        if (known.gold_context != gold_context) {
            const int gold = group.gold + (prospector ? prospected(group.cluster_gold, 1) : 0);
            const int gems = group.gems + (prospector ? prospected(group.cluster_gems, 1) : 0);
            known.gold = known.weight * (per_gold * static_cast<float>(gold) + tribute_gold * static_cast<float>(std::min(gems, short_by)));
            known.gold_context = gold_context;
        }
        if (known.version != belief.version || known.fastest_strength != strength)
            known.version = belief.version, known.fastest_strength = strength, known.fastest = fastest_clear(world, g, strength);
        const float bonus = keep_bonus(group);
        // Ren's for the rated prunes; its plain ones keep the fastest.
        const float exposed = exposure(g) * (pull.on && home_side(map, g, opening) < 0.5f ? pull.deny_scale : 1.0f);
        const float quickest = rated && reflect > 0 ? reflected_clear(world, g, strength, reflect) : known.fastest;
        const int walk = known.walk;
        // From the altar after the tribute, the cycle may go out by way of spawn.
        const int walk_out = banks_bag ? altar_out(g, walk) : walk;
        // The trip home is health-dependent, so it stays out of the kept facts.
        float bank = known.walked_bank, cycle_bank = known.walked_cycle;
        if (to_altar) {
            const float back = (wins ? winning_trip : trip_home)->rounds(walk, capture, static_cast<std::uint32_t>(static_cast<float>(known.gold_in) * paid));
            const bool banks = back < static_cast<float>(unreachable);
            bank = banks ? back + static_cast<float>(known.chained_tribute) : 0.0f;
            cycle_bank = banks ? back + static_cast<float>(known.tribute) : 0.0f;
        }
        auto& steps_known = steps_data[g];
        if (steps_known < 0) {
            // A walk is never shorter than the Chebyshev distance, and the trip grows with the walk: a
            // group that cannot beat the best from that close needs no steps. A recall out of a pocket
            // or a crystal hop can be shorter (its nearest source and landing need not pair).
            const auto beaten_near = [&](bool by_rate) __attribute__((always_inline)) {
                const int near = dist(here, group.centre);
                if (in_pocket || !prunable(g) || may_help(group, belief, near) || (hop_any && map.group_hop(g) >= 0)) return false;
                const float worth = (known.gems + known.gold + known.gems * bonus) * exposed;
                // Banking by way of spawn, the loop prices the trip on to an altar healed, which can
                // undercut `bank`: that way takes no floor for it.
                const int respawn = respawn_in(belief);
                const int pulled = pulled_near(g, near);
                const float trip = to_altar ? std::max(0.0f, std::min(static_cast<float>(std::max(pulled, respawn)) + bank,
                                                                      via_bound(dist(spawn_centre, group.centre), respawn)) - bank_now)
                                            : std::max(0.0f, soonest(group, belief, pulled) - bank_now + bank);
                const float fastest = prune_fastest(g, known.fastest, wins);
                if (by_rate) return beaten(worth, trip, opening ? prune_fastest(g, quickest, wins) : fastest, walk_out, cycle_bank, crew_most(g, wins));
                const float near_cycle = trip + cap_rounds + fastest;
                return near_cycle > 0 && worth / near_cycle <= bar_le()
                       && (!banks_bag || worth / (static_cast<float>(walk_out + capture) + cycle_bank + fastest) <= from_altar_value);
            };
            // Walking is symmetric: a group's centre field, once made, gives our steps to it. The sources
            // below give the same steps (the prunes skip only groups that cannot beat the best).
            if (const auto* centre = centre_field(g)) {
                steps_known = centre->at(here);
            } else if ((tight || rated) && !claimed && barred() && g != farm_group && beaten_near(true)) {
                continue;
            } else if (const auto drafted = draft_spawn_graph ? map.drafted_spawn_steps(here, g) : std::nullopt) {
                steps_known = *drafted;
            } else if (const auto dashed = map.drafted_dash_steps(world.me().index, here, g, dash_kind)) {
                steps_known = *dashed;
            } else {
                const Field* made = nullptr;
                if (!from_here) {
                    if ((!tight || g == farm_group) && !claimed && barred() && beaten_near(false)) continue;
                    if (!fuel_ok(full_field_cost_estimate() + loop_reserve())) break;
                    // The first groups' centre fields give the same steps for the same flood each,
                    // and stay made; a third group's floods from here.
                    if (!opening && centred < 2) ++centred, made = pathing.centre_field(g);
                    if (!made) from_here = make_field(pathing.static_walls(), single(here));
                    world.throw_if_stale();
                }
                if (made) {
                    group_facts[g].centre = made;
                    steps_known = made->at(here);
                } else {
                    pathing.want_centre(g);
                    steps_known = from_here->at(group.centre);
                }
            }
        }
        int steps = steps_known;
        // The pull's steps from our mirror tile: the group's centre field read there, else the crow's.
        float mirror_steps = -1;
        const auto mirror_walk = [&]() __attribute__((always_inline)) {
            if (mirror_steps < 0) {
                const int crow = dist(pull.mirror, group.centre);
                const auto* centre = static_cast<float>(steps) > params::comeback::pull_c * static_cast<float>(crow) ? centre_field(g) : nullptr;
                const int at = centre ? centre->at(pull.mirror) : unreachable;
                mirror_steps = static_cast<float>(at != unreachable ? std::max(at, crow) : crow);
            }
            return mirror_steps;
        };
        const auto pulled_walk = [&](int s) __attribute__((always_inline)) {
            return pull.on ? pulled_steps(static_cast<float>(s), mirror_walk()) : static_cast<float>(s);
        };
        // Beyond our walk (beyond_walk): out of a pocket by a recall; into another region by its
        // crystal hop (StaticMap::group_hop) from our spawn, where one is bought (`toll`) unless
        // carried, and out of it again by a recall unless it holds an altar.
        float toll = 0;
        if (steps == unreachable && map.any_group_hop()) {
            int out = 0;
            vec2 from = here;
            if (in_pocket) out = recall_turns(world), from = recall_landing(world), steps = pathing.to_ally_spawn().at(group.centre);
            int h = map.group_hop(g);
            if (h == memory.hop_refused && round < memory.hop_refused_until) h = -1;
            if (steps == unreachable && h >= 0 && crystal < 0) crystal = carries_crystal() ? 2 : can_buy_crystal() ? 1 : 0;
            if (steps == unreachable && h >= 0 && crystal > 0) {
                if (crystal == 1 && !in_pocket) out = pathing.to_ally_spawn().at(here), from = map.ally_spawn_centre;
                if (!pathing.hop_ready(h) && !fuel_ok(2 * full_field_cost_estimate() + loop_reserve())) break;
                const int walk = pathing.to_hop(h).at(from), inner = pathing.from_landings(h).at(group.centre);
                if (walk != unreachable && inner != unreachable) {
                    steps = walk + cambc::constants::tp_crystal_time + inner
                            + (pathing.centre_to_altar(g) == unreachable ? recall_turns(world) : 0);
                    if (crystal == 1) toll = prices(world).per_gold * static_cast<float>(cambc::consumable_type::tp_crystal.cost());
                }
            }
            steps = steps == unreachable || out == unreachable ? unreachable : steps + out;
        }
        if (steps == unreachable) continue;
        // The walk goes round live camps (approach()): where its search has run, its steps, or what it
        // proved of them, are ours. The static steps stay the bound where it walks no farther.
        const bool walked = steps == steps_known;
        if (walked) {
            const int live = pathing.live_steps(g, belief.state != CampState::cleared ? range : 0);
            if (live == unreachable) continue;
            steps = std::max(steps, live);
        }
        // A group still respawning when we would arrive costs the wait there.
        const int respawn = respawn_in(belief);
        const int wait = std::max(0, respawn - steps);
        // The rounds stood there run from our arrival. A dasher travels by the turn (step_towards),
        // so measured by its walk a dash would lengthen the wait and drop the group we are nearing.
        const int idle = respawn > 0 && walked ? std::max(0, respawn - loop_travel_turns(steps)) : wait;
        if (idle > params::max_wait) continue;
        // By way of spawn when sooner (`steps` stays the walk: the help radius and the walk's search
        // cap read it). `reach`: rounds until we are there, the stop's value not taken off; `there`:
        // and until it is back.
        float via = recall_out && steps_known != unreachable ? via_recall.sooner(spawn_steps(g), respawn, steps)
                                                             : static_cast<float>(unreachable);
        // Carrying, by way of spawn only while that stays sooner with the trip on to an altar.
        if (to_altar && via < static_cast<float>(unreachable)) {
            const float back = (wins ? healed_winning : healed_home)->rounds(walk, capture, static_cast<std::uint32_t>(static_cast<float>(known.gold_in) * paid));
            const float healed = back < static_cast<float>(unreachable) ? back + static_cast<float>(known.chained_tribute) : 0.0f;
            if (via + healed < static_cast<float>(steps + wait) + bank) via += healed - bank;
            else via = static_cast<float>(unreachable);
        }
        const bool by_spawn = via < static_cast<float>(unreachable);
        const int reach = by_spawn ? via_recall.channel + via_recall.hurt + spawn_steps(g) : steps;
        routed[g] = by_spawn;
        const int there = std::max(reach, respawn);
        // A Monolith is a crew's, never a help call's.
        if (!banks_bag && group.strength > 0 && !group.has_monolith && belief.state == CampState::alive && steps <= params::help_radius
            && (steps < help_steps || (steps == help_steps && earlier(g, help_group))) && struggling(g))
            help_group = g, help_steps = steps;
        // A capture's gold that completes an emblem shortens the trip home (HomeTrip::rounds) though worth
        // counts it too: floored, so a chain never costs less than nothing and every filter below agrees.
        const float trip = std::max(0.0f, (by_spawn ? via : pulled_walk(steps) + static_cast<float>(wait)) - bank_now + bank);
        const float gems = known.gems * exposed, gold = known.gold * exposed, fastest = known.fastest, carried = gems * bonus;
        // Skip the costly clearing estimate for groups that cannot beat the best even with no
        // clearing. A crew's share can.
        if (!claimed && barred() && prunable(g)
            && ((rated && g != farm_group && beaten(gems + gold + carried, trip, prune_fastest(g, quickest, wins), walk_out, cycle_bank, crew_most(g, wins)))
                || ((!rated || g == farm_group || reflect > 0)
                    && (gems + gold + carried) / (trip + cap_rounds + prune_fastest(g, fastest, wins)) <= bar_le()
                    && (!banks_bag || (gems + gold + carried) / (static_cast<float>(walk_out + capture) + cycle_bank + prune_fastest(g, fastest, wins)) <= from_altar_value))))
            continue;
        // No known way to an altar (sealed, or a centre walls hide) is no deadline: the gold still counts.
        const auto too_late = [&](float clear_rounds) __attribute__((always_inline)) {
            if (known.to_altar < 0) known.to_altar = pathing.centre_to_altar(g);
            const int last = known.to_altar;
            return last != unreachable
                   && static_cast<float>(std::min(steps + wait, there) + capture + last + known.chained_tribute + (banks_bag ? bag_tribute : 0))
                              + clear_rounds > static_cast<float>(left);
        };
        // Solo, kited and as the crew's proposer the Focus is in the worth (a crew's part of it, as of
        // the rest); joining, the share is of `plain` and the Focus is added whole.
        const float plain = gems + gold - toll, worth = plain + carried;
        // Health past what we can spare costs trips home, each a recall and the walk back out. By
        // way of spawn we arrive healed.
        const float budget = by_spawn ? usable_health : trip_spare;
        // Read on first need: home_gap builds the group's StandReach, which a group no trip prices never needs.
        float trip_home_rounds = -1;
        const auto trips_home = [&](float n) __attribute__((always_inline)) {
            if (n <= 0) return 0.0f;
            if (trip_home_rounds < 0) trip_home_rounds = home_trip(g, steps);
            return n * trip_home_rounds;
        };
        // A cleared Monolith's capture is split over its holders: each member weighs taking it.
        if (claimed && !(group.has_monolith && belief.state == CampState::cleared)) {
            if (belief.state == CampState::cleared) continue;
            const bool op = group.strength > 0 && !kited(g);
            const bool fresh = belief.state == CampState::respawning;
            float health = 0;
            for (std::size_t i = 0; i < group.members.size(); ++i) health += fresh ? group.members[i].max_health : belief.health[i];
            // The value below, held as it is, needs neither the crew's arrivals nor its plan to be
            // bounded: it is rate(worth S r / health, trip + r + trips home) in the rounds r it
            // takes, with r at most health / (S + others). An operation's crew is plan_crew's, whose
            // claimers are those seen lately and whose expected allies only shrink r. A winning
            // capture's rate falls in r.
            const bool bounded = plain > 0 && health > 0 && (shared >= 0 || best >= 0) && g != memory.mono_group;
            float others_claiming = 0;
            // The Focus on the weighted gems, held for the capture's rounds; in the bounds, its rate
            // over the trip and the hold alone.
            float carry = carried, hold = carry > 0 ? cap_rounds : 0.0f;
            const float carry_most = carry > 0 ? rate(world, carry, trip + hold) : 0.0f;
            const auto beaten_claimed = [&](float most) __attribute__((always_inline)) {
                most = (most + carry_most) * (op && memory.claim == g ? crew_hold(g) : 1.0f) * 1.0001f;
                return most < shared_value || (best >= 0 && most < best_value);
            };
            if (bounded) {
                const auto& allies = crew_allies_now();
                for (int k = 0; k < allies.n_claiming; ++k)
                    if (const auto& a = allies.at[allies.claiming[static_cast<std::size_t>(k)]]; a.claim == g && (!op || a.seen)) others_claiming += crew_output(a);
                if (beaten_claimed(wins ? rate(world, plain, trip) : claim_bound(plain, health, health / (strength + others_claiming), trip))) continue;
            }
            const int waiting = fresh ? std::max(0, belief.respawn_round - round) : 0;
            const int working = std::max(0, reach - waiting);
            const auto crew = crew_work(op || crew_read ? &crew_allies_now() : nullptr, g, working, waiting);
            const float health_left = health - std::max(0.0f, crew.output * static_cast<float>(working) - crew.delayed_damage);
            if (health <= 0 || health_left <= 0) continue;
            // The bound above again with r at most health_left / (S + others): the claimers' work before
            // we arrive leaves our part less to clear. Checked before the plan, which only shrinks r.
            if (bounded && op && !wins && health_left < health
                && beaten_claimed(claim_bound(plain, health, health_left / (strength + others_claiming), trip)))
                continue;
            // A strong group's crew as its proposer counts it, available allies included: joining
            // only on the claimers seen so far, each joiner would find too small a crew.
            const bool expect = may_expect(g);
            const CrewPlan plan = op ? plan_crew(world, crew_allies_now(), g, strength, expect, crew_cap(g)) : CrewPlan{};
            const float others = op ? plan.output - strength : crew.output;
            // A capture that wins the game is the team's, not a share: what counts is how soon.
            const float rounds = health_left / (strength + others), part = wins ? 1.0f : strength * rounds / health;
            const float damage = op ? crew_share(plan, reach) : 0.0f;
            const int trips = op ? extra_trips(damage, budget, usable_health) : 0;
            // Kited, we take the hits alone: our share of them must fit the health we spare. Unless we
            // see the camp's health falling, as if the claimers did nothing before we arrive.
            const bool kite_hit = kited(g) && group.strength > 0;
            float hits = -1;
            const auto kite_hits = [&]() {
                if (hits < 0) {
                    const bool worked = belief.last_damaged_round >= round - 1;
                    float joint_rounds = 0;
                    hits = soften * min_camp_damage(world, g, strength + others, &joint_rounds)
                           * (worked ? strength * rounds / health : strength / (strength + others));
                }
                return hits;
            };
            // The Focus is ours only if the clear leaves us fit to keep the bag (keeps_bag's health).
            if (carry > 0 && my_health() - (kite_hit ? kite_hits() : damage) < params::hurt_health_fraction * max_health) carry = 0, hold = 0;
            // No capture rounds but a keeping Prism's: the claimer holds it, and the crew moves on once it is cleared.
            // A crew we are in holds us against small pulls: one member leaving shrinks it for the rest.
            const float value = rate(world, plain * part + carry, trip + rounds + hold + trips_home(static_cast<float>(trips)))
                                * (op && memory.claim == g ? crew_hold(g) : 1.0f);
            // Only a better share counts, and the final pick takes none a group of our own beats.
            if (g == memory.mono_group) mono_seen = value;
            if ((value < shared_value || (value == shared_value && !earlier(g, shared))) || (best >= 0 && value <= best_value) || too_late(rounds))
                continue;
            if (kite_hit && kite_hits() > spare_health) continue;
            shared = g, shared_value = value, shared_steps = steps;
            if (may_floor()) floor_value = value;
            shared_priced = {'J', trips, plan.tank ? plan.tank->index : -1, plan.n_expected, strength + others, damage};
            continue;
        }
        if (known.clearing != clearing || known.clear_version != belief.version) {
            known.clearing = clearing, known.clear_version = belief.version;
            known.damage = known.rounds = 0, known.kite = -1;
            if (belief.state != CampState::cleared) {
                known.damage = min_camp_damage(world, g, strength, &known.rounds, reflect);
                if (group.strength > 0) known.kite = spell_clear_rounds(world, g, range, spells, basic);
            }
        }
        // A clear under way casts as the shield's cooldown allows, after the shield already up for
        // its turns left; any other starts once it is back.
        const bool under_way = g == memory.farm_group && belief.awake != Awake::asleep;
        float alone_damage = shielded_clear(soften * known.damage, known.rounds, shield,
                                            std::max(0.0f, shield_ready_in - (under_way ? 0.0f : static_cast<float>(reach))));
        if (under_way && world.me().shield > 0 && known.rounds > 0)
            alone_damage -= std::min(world.me().shield, soften * known.damage / known.rounds
                                                            * std::min(known.rounds, static_cast<float>(world.me().shield_turns)));
        const float alone_rounds = known.rounds, kite = known.kite;
        // Kited, we work it beside kite()'s casters or not at all: a clear that costs more health
        // than we spare is risky, taken only when nothing else is left, unless an ally is engaged or
        // an unclaimed partner near us shares it.
        if (kited(g)) {
            const bool alive = belief.state == CampState::alive;
            if (best >= 0 && (alone_damage <= spare_health || unclaimed_partner_output <= 0 || !alive)) {
                const float quickest = kite >= 0 ? std::min(alone_rounds, kite) : alone_rounds;
                if (worth / (trip + quickest + capture) <= best_value
                    && (!banks_bag || worth / (static_cast<float>(walk_out) + cycle_bank + quickest + capture) <= from_altar_value))
                    continue;
            }
            float rounds = alone_rounds, damage = alone_damage;
            const bool cast = kite >= 0 && (damage > spare_health || kite < rounds + heal(g, damage));
            if (cast) damage = 0, rounds = kite;
            if (too_late(rounds)) continue;
            float value = rate(world, worth, trip + rounds + capture);
            if (damage > spare_health && unclaimed_partner_output > 0 && alive) {
                float joint_rounds = 0;
                const float part = strength / (strength + unclaimed_partner_output);
                if (soften * min_camp_damage(world, g, strength + unclaimed_partner_output, &joint_rounds) * part <= spare_health)
                    damage = 0, value = rate(world, worth * part, trip + joint_rounds + capture);
            }
            if (damage > spare_health && !ally_engaged(world, g)) {
                if (value > risky_value || (value == risky_value && earlier(g, risky))) risky = g, risky_value = value, risky_steps = steps;
                continue;
            }
            if (value > best_value || (value == best_value && earlier(g, best)))
                best = g, best_value = value, best_steps = steps, best_spell = cast, best_priced = {cast ? 'K' : 'S', 0, -1, 0, strength, damage};
            if (banks_bag && walk_out != unreachable) {
                const float via_altar = belief.state == CampState::respawning ? std::max(0.0f, static_cast<float>(belief.respawn_round - round - walk_out) - bank_now) : 0.0f;
                from_altar_value = std::max(from_altar_value, rate(world, worth, static_cast<float>(walk_out) + cycle_bank + via_altar + rounds + capture));
            }
            continue;
        }
        const int alone_trips = extra_trips(alone_damage, budget, usable_health);
        // A crew may share a clear that costs us trips alone.
        const bool crewable = strong(g) && (alone_trips > 0 || group.has_monolith);
        // Otherwise it takes us alone at least the quicker of the two ways.
        if (barred() && !crewable) {
            const float quickest = kite >= 0 ? std::min(alone_rounds, kite) : alone_rounds;
            if (worth / (trip + quickest + capture) <= bar_le()
                && (!banks_bag || worth / (static_cast<float>(walk_out) + cycle_bank + quickest + capture) <= from_altar_value))
                continue;
        }
        float clear_rounds = alone_rounds, share = worth;
        int trips = alone_trips;
        bool spell = false;
        Priced priced{'S', trips, -1, 0, strength, alone_damage};
        // Clearing with spells from out of the camps' range is slower but costs no health.
        if (kite >= 0 && kite < clear_rounds + heal(g, alone_damage) + trips_home(static_cast<float>(trips))) {
            spell = true;
            clear_rounds = kite, trips = 0;
            priced = {'K', 0, -1, 0, strength};
        }
        // A Monolith is a crew's only: alone, the walk there is often given up for nearer camps on
        // the way, and a lone chip only softens it for whoever comes next.
        bool late = too_late(clear_rounds) || (group.has_monolith && belief.state != CampState::cleared);
        float value = late ? 0.0f : rate(world, worth, trip + clear_rounds + capture + trips_home(static_cast<float>(trips)));
        // Banking: the cycle from the altar after the tribute (from_altar_value's candidate).
        const float via_altar = banks_bag && walk_out != unreachable && belief.state == CampState::respawning
                                    ? std::max(0.0f, static_cast<float>(belief.respawn_round - round - walk_out) - bank_now) : 0.0f;
        const auto altar_rate = [&](float part_worth, float rounds, int home_trips) __attribute__((always_inline)) {
            return rate(world, part_worth, static_cast<float>(walk_out) + cycle_bank + via_altar + rounds + capture + trips_home(static_cast<float>(home_trips)));
        };
        if (crewable) {
            // Allies claiming it and, unless an operation on it failed lately, the available ones a
            // proposal of ours would bring. Our part of the gems is our part of the output.
            const bool expect = may_expect(g);
            // plan_crew's crew is us, the claimers seen lately and, expected, available allies: its
            // clear is no quicker than at all their output, and our part no more than beside the
            // claimers. Under that the plan changes neither this value nor the best. Banking, its
            // cycle from the altar must also stay under from_altar_value, and so must the alone
            // cycle's, which applies where the plan's would have replaced it.
            bool may_beat = true;
            if (worth > 0 && g != memory.mono_group) {
                float claimers = 0, all = strength;
                int members = 0;
                const auto& allies = crew_allies_now();
                const std::uint32_t mine = crew_claimer_bits(allies, g);
                for (std::uint32_t b = mine | (expect ? crew_available_bits(world, allies, g) : 0u); b; b &= b - 1) {
                    const int i = std::countr_zero(b);
                    const auto& a = allies.at[static_cast<std::size_t>(i)];
                    if (mine >> i & 1) claimers += crew_output(a);
                    all += crew_output(a), ++members;
                }
                // Short of the win, our part is S / O for O in [S + claimers, all] (crew_rate).
                const float lo = (strength + claimers) / strength, hi = all / strength;
                const float hold = memory.claim == g ? crew_hold(g) : 1.0f;
                const auto crew_bound = [&](float base) __attribute__((always_inline)) {
                    return wins ? rate(world, worth, base + fastest / hi) : crew_rate(world, worth, base, fastest, lo, hi);
                };
                const float most = crew_bound(trip + cap_rounds) * hold * 1.0001f;
                may_beat = most >= value && !((best >= 0 && most < best_value) || most < floor_value);
                if (!may_beat && most >= value && banks_bag && walk_out != unreachable) {
                    const float via_altar_out = static_cast<float>(walk_out) + cycle_bank + via_altar + cap_rounds;
                    may_beat = crew_bound(via_altar_out) * 1.0001f >= from_altar_value || (!late && altar_rate(share, clear_rounds, trips) > from_altar_value);
                }
                // These are plan_crew's claimers and available allies: with none, its crew is us alone.
                if (members == 0) may_beat = false;
            }
            const CrewPlan plan = may_beat ? plan_crew(world, crew_allies_now(), g, strength, expect, crew_cap(g)) : CrewPlan{};
            if (may_beat && plan.output > strength && !too_late(plan.rounds)) {
                const float part = wins ? 1.0f : strength / plan.output;
                const int my_trips = extra_trips(crew_share(plan, reach), budget, usable_health);
                // Held while ours, as a crew's share is; a fresh proposal with an op of an ally's under
                // way gives way to joining it rather than split the free allies.
                const float hold = memory.claim == g ? crew_hold(g)
                                   : plan.claimers == 0 && rival_op() ? params::crew_rival_factor : 1.0f;
                const float crew_value = rate(world, worth * part, trip + plan.rounds + capture + trips_home(static_cast<float>(my_trips))) * hold;
                debug_block({
                    if (group.has_monolith && round % 25 == 0)
                        std::printf("MONO VALUE %d %u g%d worth %.0f part %.2f trip %.0f rounds %.0f trips %d home %.0f crew %d+%d output %.0f value %.4f best-so-far %.4f\n",
                                    round, my_handle(), g, worth, part, trip, plan.rounds, my_trips, trips_home(1), plan.claimers, plan.n_expected,
                                    plan.output, crew_value, best_value);
                });
                if (crew_value > value) {
                    value = crew_value, late = false, spell = false;
                    clear_rounds = plan.rounds, trips = my_trips, share = worth * part;
                    priced = {'C', my_trips, plan.tank ? plan.tank->index : -1, plan.n_expected, plan.output, crew_share(plan, reach)};
                }
            }
        }
        if (g == memory.mono_group) mono_seen = value;
        if (late) continue;
        if (value > best_value || (value == best_value && earlier(g, best)))
            best = g, best_value = value, best_steps = steps, best_spell = spell, best_priced = priced;
        if (banks_bag && walk_out != unreachable) from_altar_value = std::max(from_altar_value, altar_rate(share, clear_rounds, trips));
    }
    read_g = -1;
    if (k < evaluated) note_shortcut("farm-partial-evaluation");
    need_zone();
    // An ally's hold that pays more with us on it: the rounds we then hold free the holder, worth
    // what our best cycle earns a round, so the walk is what it costs.
    if (!banks_bag && !memory.banking && evaluated == n_groups && takes_over(world)) {
        const float work_rate = best_value;
        world.each_cleared([&](int g) {
            const auto& G = groups[g];
            // A payout is at most capture_time rounds away, so no longer walk arrives before it (takeover_worth).
            const int least = steps_to(G, here); // no walk to its tiles is shorter
            if (least >= cambc::constants::capture_time || allies_on(world, G.tiles()) == 0 || !may_take_over(world, G)
                || left_for_prism(world, pathing, g))
                return;
            int timer = 0;
            const float gain = takeover_gain(world, G, timer);
            if (!(gain > 0) || timer < least + 1) return;
            const int walk = pathing.to_group(g).at(here);
            if (walk == unreachable) return;
            int hold = 0;
            const float worth = takeover_worth(gain, timer, walk, work_rate, hold);
            if (!(worth > 0)) return;
            const float value = rate(world, worth, static_cast<float>(walk + hold));
            if (value > best_value) best = g, best_steps = walk, best_value = value, best_spell = false, best_priced = Priced{'T'};
        });
    }
    // Keeping our gems, as Prism: an ally's gem capture we reach before it pays ('G'), all of it ours once the
    // ally yields, over the rounds to the payout. One we cannot reach in time, within carry_reach, the
    // ally leaves to us (left_for_prism), as it does a cleared group we head for ('L'): ours over the
    // walk and a whole hold of our own.
    static bitboard carry_goal{cambc::uninitialized}, goal{cambc::uninitialized};
    const int reach = carry_reach();
    if (keeps && !banks_bag && !memory.banking) {
        world.each_cleared([&](int g) {
            const auto& G = groups[g];
            const int least = steps_to(G, here); // no walk to its tiles is shorter
            if (G.gems <= 0 || least > reach) return;
            const bool held = allies_on(world, G.tiles()) > 0;
            // Left empty: our carry pick, or our claim that an ally's claim keeps out of the loop.
            if (!held && (g != memory.claim || world.camps[g].holder == team::enemy || (memo.carry_group != g && !claimed_by_ally(g)))) return;
            const int gems = std::min(G.gems + (prospector ? prospected(G.cluster_gems, 1) : 0), short_by);
            const int gold = G.gold + (prospector ? prospected(G.cluster_gold, 1) : 0);
            const float worth = static_cast<float>(gems) * (1.0f + keep_bonus(G)) + per_gold * static_cast<float>(gold);
            // The fewest rounds it can take (a payout comes after our arrival): no better than the best, and not
            // the best already, it is not picked (a worth's rate falls with its rounds).
            if (best != g && worth >= 0 && !(rate(world, worth, static_cast<float>(least + (held ? 1 : capture_rounds(world)))) > best_value)) return;
            int timer = 0;
            if (held ? !prism_takeover(world, safety, G, timer, goal) : !prism_carries(world, safety, G, goal)) return;
            if (!fuel_ok(full_field_cost_estimate() + loop_reserve())) return;
            int walk = pathing.to_group(g).at(here);
            if (walk == unreachable) return;
            // The field's nearest tile may be one we cannot take: the goal's, a step on at most beside it,
            // and no nearer than the crow flies.
            int crow = unreachable;
            bool off_goal = false;
            for (const auto& m : G.members) {
                const int d = dist(here, m.pos);
                if (test(goal, m.pos)) crow = std::min(crow, d);
                else off_goal |= d <= walk;
            }
            walk = std::max(walk + (off_goal ? 1 : 0), crow);
            if (walk > reach) return;
            // A holder whose recall lands before we arrive leaves the tiles empty for a whole hold of ours.
            const bool in_time = held && walk < timer && holders_stay(world, G, round + walk);
            // No more than the loop's bound on a cleared group: the walk is at least the crow's.
            const int rounds = in_time ? timer : walk + capture_rounds(world);
            const float value = rate(world, worth, static_cast<float>(rounds));
            // Our pick already, taken over as the carry for its goal and the carry's stickiness.
            if (value > best_value || (best == g && !in_time)) {
                best = g, best_steps = walk, best_value = std::max(value, best_value), best_spell = false, best_priced = Priced{in_time ? 'G' : 'L'};
                copy_into(goal, carry_goal);
            }
        });
    }
    // Keeping our gems, as Prism: an ally's clear under way of a gem group within carry_reach ('Q'), worked
    // (hit last round, or a claimer in reach), the whole capture ours as for 'G' and 'L'. There before the
    // clear ends we join it as crew, if we can afford its fire; after, a free tile beside the claimers'
    // makes us its sole holder (sole_capture_holder) at their payout, else it is left to us once cleared
    // (left_for_prism) for a whole hold of ours. A group the claimers fill is not taken: its hold can't be
    // handed over. Posted as the carry ('G', 'L'), so a turn off the way withdraws it.
    if (keeps && !banks_bag && !memory.banking && !enemy_seen(world) && my_health() >= params::hurt_health_fraction * max_health) {
        const int bag = static_cast<int>(my_gems()), winning = static_cast<int>(cambc::constants::winning_gems);
        std::array<int, 8> asked;
        int n_asked = 0;
        for (const auto& a : world.allies) {
            if (a.is_self || !a.alive) continue;
            const int g = comms::claim_of(world, a.index);
            if (g < 0 || g >= n_groups || n_asked == static_cast<int>(asked.size()) || std::find(asked.begin(), asked.begin() + n_asked, g) != asked.begin() + n_asked)
                continue;
            asked[static_cast<std::size_t>(n_asked++)] = g;
            const auto& G = groups[g];
            const auto& c = world.camps[g];
            if (c.state != CampState::alive || G.gems <= 0 || G.has_monolith || steps_to(G, here) > reach || enemy_on(world, G.tiles())
                || (kited(g) && kite_owns(world, g)) || siege_declines(world, g)
                || world.score.ally + bag + G.gems >= winning
                || rounds_left(world) <= tribute_turns(bag + G.gems, world.me().fast_tribute) + map.width + map.height + endgame_margin)
                continue;
            float output = 0;
            int claimers = 0;
            bool worked = c.last_damaged_round >= round - 1;
            for (const auto& b : world.allies) {
                if (b.is_self || !b.alive || comms::claim_of(world, b.index) != g) continue;
                output += camp_output(b), ++claimers;
                if (b.visible) worked = worked || crew_in_reach(world, g, b.pos, b.facts().attack_range());
            }
            if (!worked || !(output > 0) || claimers >= static_cast<int>(G.members.size())) continue;
            float health = 0;
            for (std::size_t i = 0; i < G.members.size(); ++i) health += std::max(0.0f, c.health[i]);
            if (!(health > 0)) continue;
            const float clear = health / output, ours = clear + static_cast<float>(capture_rounds(false));
            const int gems = std::min(G.gems + (prospector ? prospected(G.cluster_gems, 1) : 0), short_by);
            const int gold = G.gold + (prospector ? prospected(G.cluster_gold, 1) : 0);
            const float worth = static_cast<float>(gems) * (1.0f + keep_bonus(G)) + per_gold * static_cast<float>(gold);
            // Its rounds grow with the walk, at least the crow's: no better than the best then, it is not picked.
            const auto rounds_at = [&](int walk) { return static_cast<float>(walk) < ours ? ours : static_cast<float>(walk + capture_rounds(world)); };
            if (worth >= 0 && !(rate(world, worth, rounds_at(steps_to(G, here))) > best_value)) continue;
            bool seen = false;
            for (const auto& m : G.members) seen |= enemy_may_see(world, m.pos);
            if (seen || !fuel_ok(full_field_cost_estimate() + loop_reserve())) continue;
            const int walk = pathing.to_group(g).at(here);
            if (walk == unreachable || walk > reach) continue;
            const float value = rate(world, worth, rounds_at(walk));
            if (value > best_value && !(static_cast<float>(walk) < clear && !affordable(g)))
                best = g, best_steps = walk, best_value = value, best_spell = false, best_priced = Priced{'Q'};
        }
    }
    if (banks_bag && (best < 0 || best_value <= from_altar_value)) return false;
    if (banks_bag && attack_in_range()) return true;
    if (world.is_stale()) return true;
    if (best < 0 && risky >= 0) best = risky, best_steps = risky_steps, best_value = risky_value, best_priced = Priced{'r'};
    const int prev_claim = memory.claim;
    const bool prev_crew = memory.crew;
    memory.claim = best;
    memory.crew = false;
    bool spell = best >= 0 && best_spell;
    Priced chosen = best_priced;
    if (chosen.mode == 'Q') memory.crew = true; // the claim an ally's leave_for_prism reads; the clear's crew if we come in time
    if (shared >= 0 && (best < 0 || shared_value > best_value)) {
        best = shared, best_steps = shared_steps, memory.claim = shared, memory.crew = true, spell = false, chosen = shared_priced;
        if (prev_claim != shared || !prev_crew) {
            debug_block({ std::printf("CREW JOIN %d %u g%d tank %d trips %d output %.0f value %.4f\n", round, my_handle(), shared,
                                      chosen.tank, chosen.trips, chosen.output, shared_value); });
        }
    }
    // Help does not pull a member off a Monolith operation.
    if (help_group >= 0 && !(farm_monolith(world, best) && memory.claim == best))
        best = help_group, best_steps = help_steps, memory.claim = help_group, memory.crew = true, spell = false, chosen = Priced{'H'};
    if constexpr (!banking && !repricing && params::open_plan::weight <= 0) {
        // A help call (an ally struggling at its group) keeps its pull.
        if (const int planned = banks_bag || help_group >= 0 ? -1 : open_plan_choice(world, memory); planned >= 0 && planned != best) {
            const int s = steps_data[planned];
            best = planned, best_steps = s >= 0 && s != unreachable ? s : dist(here, groups[planned].centre);
            memory.claim = planned, memory.crew = claimed_by_ally(planned), spell = false, chosen = Priced{'P'};
            debug_block({ std::printf("OPENPLAN step %d %u g%d k %d\n", round, my_handle(), planned, memory.open_step); });
        }
    }
    // Valued with allies we expect to join: our proposal, which their crew branch sees as our claim.
    if (best >= 0 && !memory.crew && chosen.mode == 'C' && chosen.expected > 0 && memory.crew_proposed != best) {
        memory.crew_proposed = best, memory.crew_reached = -1;
        debug_block({ std::printf("CREW PROPOSE %d %u g%d expected %d tank %d trips %d output %.0f value %.4f\n", round, my_handle(), best,
                                  chosen.expected, chosen.tank, chosen.trips, chosen.output, best_value); });
    }
    debug_block({
        static int last_claim = -2, last_trips = -1;
        static char last_mode = 0;
        static bool listed = false;
        if (opening && !listed && world.me().index == 0) {
            listed = true;
            for (int g = 0; g < n_groups; ++g)
                std::printf("CREW GROUP g%d at %d,%d gems %d gold %d strength %.0f health %.0f spawn %d\n", g, groups[g].centre.x, groups[g].centre.y,
                            groups[g].gems, groups[g].gold, groups[g].strength, groups[g].health, spawn_steps(g));
        }
        if (memory.claim != last_claim || chosen.mode != last_mode || chosen.trips != last_trips) {
            last_claim = memory.claim, last_mode = chosen.mode, last_trips = chosen.trips;
            std::printf("CREW PICK %d %u g%d %c trips %d tank %d expected %d output %.0f damage %.0f hp %.0f/%.0f\n", round, my_handle(), memory.claim,
                        chosen.mode, chosen.trips, chosen.tank, chosen.expected, chosen.output, chosen.damage, my_health(), max_health);
        }
    });
    if constexpr (!repricing) memo.carry_group = best >= 0 && (chosen.mode == 'G' || chosen.mode == 'L' || chosen.mode == 'Q') ? best : -1, memo.carry_round = round;
    if (best < 0) {
        if constexpr (repricing) return true;
        // Cut short before weighing even last turn's choice: walk on towards it, as its crew if we were.
        if (k == 0 && memory.farm_group >= 0)
            memory.claim = memory.farm_group, memory.crew = crew_of_choice, walk_on(memory.farm_group);
        else
            pathing.leave_respawning(zone);
        return true;
    }
    memory.farm_group = best;
    if (farm_monolith(world, best) && memory.claim == best) {
        if (memory.mono_group != best) {
            memory.mono_group = best, memory.mono_staged = -1, memory.mono_since = round, memory.mono_taken = 0;
            debug_block({ std::printf("MONO START %d %u g%d %c expected %d output %.0f trips %d hp %.0f/%.0f\n", round, my_handle(), best,
                                      chosen.mode, chosen.expected, chosen.output, chosen.trips, my_health(), max_health); });
        }
        if (chosen.output > 0) memory.mono_output = chosen.output;
    } else if (memory.mono_group >= 0) {
        debug_block({ std::printf("MONO END %d %u g%d for %d taken %.0f state %d value %.4f now g%d %c value %.4f\n", round, my_handle(), memory.mono_group,
                                  round - memory.mono_since, memory.mono_taken, static_cast<int>(world.camps[memory.mono_group].state), mono_seen,
                                  best, chosen.mode, best == shared ? shared_value : best_value); });
        memory.mono_group = -1, memory.mono_staged = -1;
    }
    // As the loop priced it; recall_to_farm keeps the turn-end recall while it stays sooner.
    if (recall_out && steps_data[best] != unreachable && chosen.mode != 'T' && chosen.mode != 'G' && chosen.mode != 'L' && chosen.mode != 'Q'
        && via_recall.sooner(spawn_steps(best), respawn_in(world.camps[best]), best_steps) < static_cast<float>(unreachable)
        && (!to_altar || routed[best])) {
        memory.recall_farm = best;
        debug_block({ std::printf("RFCHOOSE %d %u %d %d %d %d gems %u bank %d\n", round, my_handle(), best, best_steps, spawn_steps(best),
                                  static_cast<int>(via_recall.value), my_gems(), static_cast<int>(banks_bag)); });
    }
    if constexpr (repricing) return true;
    if (map.any_group_hop() && beyond_walk(world, pathing, best) && (in_pocket || cross(best))) return true;
    const auto heal_before_waking = [&]() {
        if (!(memory.crew || chosen.expected > 0) || world.camps[best].state != CampState::alive
            || world.camps[best].awake != Awake::asleep || groups[best].has_monolith) return false;
        const auto& G = groups[best];
        // Even every member firing for the longest exit cannot make this check refuse.
        if (soften * G.strength * static_cast<float>(G.reach + 1) < my_health_and_shield(world)) return false;
        return [&]() __attribute__((noinline)) {
            const auto& c = world.camps[best];
            const vec2 at = my_position();
            if (test(map.ally_spawn, at) || steps_to(G, at) > range) return false;
            float fire = 0;
            int phases = 0;
            for (std::size_t i = 0; i < G.members.size(); ++i) {
                if (c.health[i] <= 0 || G.members[i].strength <= 0) continue;
                const int out = std::max(0, G.members[i].reach - dist(at, G.members[i].pos) + 1);
                fire += G.members[i].strength * static_cast<float>(out);
                phases = std::max(phases, out);
            }
            const float escape = shielded_clear(soften * fire, static_cast<float>(phases), shield, shield_ready_in);
            if (escape < my_health_and_shield(world)) return false;
            float clear_rounds = 0;
            const float clear_damage = soften * min_camp_damage(world, best, strength, &clear_rounds, reflect);
            if (shielded_clear(clear_damage, clear_rounds, shield, shield_ready_in) < my_health_and_shield(world)) return false;
            // The crew's future healing trip must precede a first hit we cannot walk away from.
            debug_block({ std::printf("CREW PREHEAL %d %u g%d escape %.0f hp %.0f\n", round, my_handle(), best, escape, my_health()); });
            memory.claim = -1;
            memory.camp_fled = my_health();
            retreat(world, pathing, safety, memory);
            return true;
        }();
    };
    if (heal_before_waking()) return true;
    // A sleeping Monolith: wait just out of its reach for the crew (mono_engage).
    if (memory.mono_group == best && world.camps[best].state == CampState::alive) {
        if (!mono_engage(best, memory.mono_output)) {
            siege_group() = -1;
            const auto& G = groups[best];
            const auto& c = world.camps[best];
            static bitboard ring{cambc::uninitialized};
            clear_board(ring);
            for (std::size_t i = 0; i < G.members.size(); ++i)
                if (c.health[i] > 0 && G.members[i].strength > 0) draw_square(ring, G.members[i].pos, static_cast<float>(G.reach + 1));
            ring &= map.standable;
            drop(ring, G.threat());
            if (zone) drop(ring, *zone);
            if (test(ring, here)) {
                if (memory.mono_staged < 0) {
                    memory.mono_staged = round;
                    debug_block({ std::printf("MONO STAGE %d %u g%d crew-output %.0f\n", round, my_handle(), best, memory.mono_output); });
                }
                return true;
            }
            if (!pathing.step_towards(ring, zone, best_steps + max_detour, G.centre)) walk_on(best);
            return true;
        }
        siege_group() = best;
        if (memory.mono_staged != -2) {
            int crew = 1;
            for (const auto& a : world.allies)
                crew += !a.is_self && a.alive && a.visible && comms::claim_of(world, a.index) == best;
            debug_block({ std::printf("MONO ENGAGE %d %u g%d crew-in-sight %d crew-output %.0f staged-since %d awake %d hp %.0f\n", round, my_handle(),
                                      best, crew, memory.mono_output, memory.mono_staged, static_cast<int>(world.camps[best].awake), my_health()); });
            memory.mono_staged = -2;
        }
    }
    const int cap = best_steps + max_detour;
    const bool search = fuel_ok(search_cost_estimate(cap) + end_reserve);
    // In a scratch board, valid until the next call.
    const auto off_zone = [&](const bitboard& goals) __attribute__((always_inline)) -> const bitboard& {
        if (!zone) return goals;
        static bitboard outside{cambc::uninitialized};
        outside.clear();
        outside |= goals;
        outside |= *zone;
        outside ^= *zone;
        return outside;
    };
    if (world.camps[best].state == CampState::cleared) {
        // Taking over, to a tile the ally yields to us on (prism_takeover).
        if (search) {
            const bool carry = chosen.mode == 'G' || chosen.mode == 'L';
            if (!pathing.step_towards(off_zone(carry ? carry_goal : groups[best].tiles()), zone, cap, groups[best].centre)) walk_on(best);
        } else {
            note_shortcut("farm-no-route");
            walk_on(best);
        }
        return true;
    }
    if (spell && dist(here, groups[best].centre) <= vision_radius + ability_range
        && spell_clear(world, pathing, best, zone, cap))
        return true;
    if (cast_at_camp_on_approach(world, best)) return true;
    const auto* tiles = farm_attack_tiles(world, pathing, best, range, [&] { return end_reserve + walk_reserve(best); });
    if (!tiles) {
        note_shortcut("farm-no-attack-tiles");
        walk_on(best);
        return true;
    }
    // Stands on our spawn where a camp phase leaves us above the safe line cost no health: the turn end
    // heals (home_stands), so they are walked to first. In range off them, a step onto one beside us
    // is worth taking before the attack (a ranged attack: rules turn.ranged) while the camps fire on
    // us here; off a spawn tile whose fire has outgrown home_room, to one that fits, melee hitting first.
    static bitboard home{cambc::uninitialized}, refuge{cambc::uninitialized};
    const bool in_range = test(*tiles, here);
    const bool homed = home_stands(world, pathing, safety, *tiles, best, home);
    const bool at_home = homed && test(home, here);
    const bool on_spawn = test(map.ally_spawn, here);
    const float fire = in_range && !at_home && (homed || on_spawn) ? phase_fire(world, safety, here, best) : 0.0f;
    if (homed && in_range && !at_home && fire > 0 && my_can_move() && any_within(home, here, 1)) {
        for (const auto d : directions) {
            const vec2 t{here.x + d.x, here.y + d.y};
            if (!in_bounds(t) || !test(home, t) || (zone && test(*zone, t)) || !pathing.try_move(t)) continue;
            if (my_can_attack()) attack_camp(world, [&](int g) { return g == best; });
            cast_at_camp(world, best);
            reset_and_attack_camp(world, best);
            return true;
        }
    }
    // Melee leaves after its hit for any spawn tile that fits; a ranged step costs the attack, so ranged
    // leaves only for a stand it fires from, else it would pace off and back, never attacking.
    const bool burning = on_spawn && in_range && !at_home && fire > home_room(world, safety)
                         && (melee ? (home_tiles(world, pathing, safety, refuge), refuge.set(here, false), !board_empty(refuge)) : homed);
    // On a respawning group's camp tile as it falls due, round start would find us there and hold it
    // back (rules capture.respawn): no stand to fire or wait from. Ranged leaves before its attack.
    const auto due = [&](int g) { return g >= 0 && world.camps[g].state == CampState::respawning && world.camps[g].respawn_round <= round + 1; };
    const int on_group = map.group_at(here);
    // So does an ally on one whose only way off is our tile: our stand holds the group back too.
    const auto boxed_by_us = [&]() {
        const auto& walls = pathing.blocked();
        for (const auto& a : world.allies) {
            if (a.is_self || !a.alive || !a.visible || dist(a.pos, here) != 1 || !due(map.group_at(a.pos))) continue;
            bool exit = false;
            for (const auto d : directions)
                if (const vec2 p = a.pos + d; p != here && in_bounds(p) && test(map.standable, p) && !test(walls, p)) exit = true;
            if (!exit) return true;
        }
        return false;
    };
    const bool boxes_in = !due(on_group) && boxed_by_us();
    const bool holds_back = due(on_group) || boxes_in;
    // In range and sight with the attack unspent: our pick may have been refused in passing.
    std::optional<bitboard> refused;
    if (in_range && (melee || !burning) && (melee || !holds_back) && my_can_attack() && attack_camp(world, [&](int g) { return g == best; }) < 0) {
        refused.emplace(*tiles);
        refused->set(here, false);
    }
    if (holds_back) {
        if (!refused) refused.emplace(*tiles);
        if (boxes_in) refused->set(here, false);
        else drop(*refused, groups[on_group].tiles());
    }
    // Melee walks after its hit (rules turn.melee): on to a stand while the camps fire on us here.
    const bool to_home = homed && (!in_range || (melee && fire > 0));
    const auto& goals = burning ? (melee ? refuge : home) : to_home ? home : refused ? *refused : *tiles;
    if (test(goals, here)) { // attacked from here; stay
        cast_at_camp(world, best);
        reset_and_attack_camp(world, best);
        if (melee) step_onto_cleared(world, pathing, best);
        return true;
    }
    // Each search under its own fuel check. Off a burning tile, never towards the group.
    const auto funded = [&] { return fuel_ok(search_cost_estimate(cap) + end_reserve); };
    const bool searched = funded();
    bool walked = searched ? pathing.step_towards(off_zone(goals), zone, cap, groups[best].centre)
                                 || (to_home && funded() && pathing.step_towards(off_zone(*tiles), zone, cap, groups[best].centre))
                                 || (!burning && funded() && pathing.step_towards_within(off_zone(groups[best].adjacent()), zone, cap, groups[best].centre))
                           : (note_shortcut("farm-no-route"), !burning && walk_on(best));
    if (!walked && burning && my_can_attack() && attack_camp(world, [&](int g) { return g == best; }) >= 0) reset_and_attack_camp(world, best);
    // The way round live camps past the cap, or no way: the approach search finds which (live_steps).
    const bool walked_on = !walked && !burning && searched && walk_on(best);
    if (!walked && !walked_on && holds_back && !(boxes_in ? step_aside(world, pathing, here, zone) : pathing.leave_respawning(zone)) && in_range && my_can_attack()
        && attack_camp(world, [&](int g) { return g == best; }) >= 0)
        reset_and_attack_camp(world, best);
    if (walked) {
        // A hit on a champion is worth its damage; on a camp, the gems it brings closer.
        see_revealed(world, pathing, safety);
        if (heal_before_waking()) return true;
        if (!strike_enemy(world)) attack_camp(world, passing);
        cast_at_camp(world, best); // only casts that allow walking remain
        reset_and_attack_camp(world, best);
    }
    return true;
}
bool farm_banking(World& world, Pathing& pathing, Safety& safety, Memory& memory) {
    return farm_turn<false, true>(world, pathing, safety, memory);
}

void farm_reprice(World& world, Pathing& pathing, Safety& safety, Memory& memory) {
    farm_turn<false, false, true>(world, pathing, safety, memory);
}

bool farm(World& world, Pathing& pathing, Safety& safety, Memory& memory) {
    return world.round == world.first_round ? farm_turn<true>(world, pathing, safety, memory) : farm_turn<false>(world, pathing, safety, memory);
}

// A farming turn's output lands on camps: in enemy health points, the gems it earns at the map's
// gems per camp health point.
float farm_step_value(const World& world) {
    static float density = -1;
    if (density < 0) {
        float gems = 0, health = 0;
        for (const auto& g : world.map().groups) {
            if (g.gems == 0 || (g.has_monolith && !world.map().monolith_only)) continue;
            gems += static_cast<float>(g.gems);
            for (const auto& m : g.members) health += m.max_health;
        }
        density = health > 0 ? gems / health : 0.0f;
    }
    return output(world.me()) * density * params::gem_value;
}

} // namespace

} // namespace aph
