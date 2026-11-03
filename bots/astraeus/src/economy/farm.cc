// The farm loop: which group to work next, and the walk and hits towards it.
#include "../bot_parts.h"
#include <wasm_simd128.h>

namespace aph {

namespace {

constexpr float stickiness = 1.2f;

// Pathing::attack_tiles once prepared, null if preparing could take the fuel below `floor()`.
// Member tiles are static once prepared, so the union is kept while the same members live.
struct KeptAttackTiles {
    int group = -1, range = -1;
    std::array<std::uint64_t, 4> alive{};
    bool respawning = false; // its camp tiles left out (Pathing::attack_tiles)
    bitboard tiles;
};
KeptAttackTiles kept_attack_tiles;

// Whether farm_attack_tiles keeps the group's union as its live members are now.
bool attack_tiles_kept(const World& world, int group, int range, std::array<std::uint64_t, 4>& alive, bool& keeps) {
    const auto& kept = kept_attack_tiles;
    const auto& health = world.camps[group].health;
    keeps = health.size() <= 64 * kept.alive.size();
    alive = {};
    for (std::size_t i = 0; i < health.size() && keeps; ++i)
        if (health[i] > 0) alive[i >> 6] |= std::uint64_t{1} << (i & 63);
    return keeps && kept.group == group && kept.range == range && kept.alive == alive
           && kept.respawning == (world.camps[group].state == CampState::respawning);
}

// What farm_attack_tiles would spend decoding drafted tiles not decoded yet (measured on a bushy
// map's first turn: indexing a block ~8k, each member ~2k); undrafted tiles are prepared within
// its own floor.
std::uint64_t attack_tiles_cost(const World& world, Pathing& pathing, int group, int range) {
    if (group < 0 || group >= static_cast<int>(world.camps.size()) || world.camps[group].state == CampState::cleared) return 0;
    std::array<std::uint64_t, 4> alive;
    bool keeps;
    if (attack_tiles_kept(world, group, range, alive, keeps) || !world.map().attack_tiles_drafted(group, range)) return 0;
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
    std::array<std::uint64_t, 4> alive;
    bool keeps;
    if (attack_tiles_kept(world, group, range, alive, keeps)) return &kept.tiles;
    // Drafted tiles need no preparing, and asking per member costs ~130 each.
    if (!world.map().attack_tiles_drafted(group, range) && !pathing.prepare_attack_tiles(group, range, floor())) return nullptr;
    pathing.attack_tiles(group, range, kept.tiles);
    kept.group = keeps ? group : -1, kept.range = range, kept.alive = alive;
    kept.respawning = world.camps[group].state == CampState::respawning;
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
    if (sole_capture_holder(world, G) || (allies_on(world, G.tiles()) >= holders(G) && !outvalues_holders(world, G))) return false;
    const vec2 here = my_position();
    for (const auto d : directions)
        if (in_bounds(here + d) && test(G.tiles(), here + d) && pathing.try_move(here + d)) return true;
    return false;
}

// The approach to a farm choice: onto its tiles once cleared, else into attack range.
int walk_range(const World& world, int g) {
    return g >= 0 && g < static_cast<int>(world.camps.size()) && world.camps[g].state != CampState::cleared
               ? world.me().facts().attack_range()
               : 0;
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
            || test(G.tiles(), here) || sole_capture_holder(world, G) || enemy_on(world, G.tiles()))
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
                    || (holders(G) == 1 && (multiplies(world, world.me(), G) || (!shy && hold_shy(world, a)))
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
    float home = -1;
    int to_altar = -1;
    std::uint32_t context = 0, gold_context = 0, version = ~0u;
    bool sticky = false;
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

// An upper bound on each group's pre-facts prune bound (farm_turn's rated_below test), from the map
// alone: a group's worth is at most its gems and gold unweighted (a weight is at most 1 off our last
// choice; negative prices count as 0), its trip at least the Chebyshev distance (or a recall by way
// of spawn from as close), and its clear and a crew only lengthen the trip or shrink our part. Each
// float operation of rated_below's chain is monotone, so a group whose upper bound is below
// best_value fails rated_below too; the 2e-4 slack covers the worth's sums taken in another order.
// The prune itself costs ~300 fuel a group (~50k a call on ~220-group maps), this ~15 in f32x4 lanes.
// +inf where the prune does not apply (the win; a striker within help_radius, which may be helped).
// Banking, the loop has no such prune, but a group changes nothing whose value stays below both the
// best and the cycle from the altar, and whose own cycle from the altar stays below the latter: its
// trip is at least the Chebyshev distance less the bank's (bank_now), and its walk out from the altar
// at least the nearest altar's distance less the tribute range, or the recall and the walk from
// spawn. `alt` gets the latter bound; kited groups (the risky pick) are never skipped.
struct PreUpper {
    vec2 here;
    int short_by, recall;
    float per_gold, tribute_gold, cap_rounds, horizon, bank_now;
    bool recall_out, prospector, banking;
    FarmRecall via;
};
[[gnu::noinline]] void pre_prune_upper(const PreUpper& p, const StaticMap& map, float* out, float* alt) {
    // Per map, eight columns of `lanes` words in one allocation, written through locals (stores
    // through the static's own pointers made the compiler reload them for every group).
    struct Static {
        const StaticMap* map = nullptr;
        int lanes = 0;
        std::unique_ptr<std::int32_t[]> words;
        std::int32_t *cx, *cy, *spawn_near, *gems, *striker, *kited, *altar_near;
        float* worth;
        bool altars_known = false;
        int short_by = -1;
        float per_gold = 0, tribute_gold = 0;
        bool prospector = false;
    };
    static Static st;
    const int n = static_cast<int>(map.groups.size()), lanes = (n + 3) & ~3;
    const CampGroup* const groups = map.groups.data();
    if (st.map != &map || st.lanes != lanes) {
        st.map = &map, st.lanes = lanes, st.short_by = -1, st.altars_known = false;
        st.words.reset(new std::int32_t[8 * static_cast<std::size_t>(lanes)]);
        std::int32_t* const w = st.words.get();
        std::int32_t *const cx = st.cx = w, *const cy = st.cy = w + lanes, *const spawn_near = st.spawn_near = w + 2 * lanes;
        std::int32_t *const gems = st.gems = w + 3 * lanes, *const striker = st.striker = w + 4 * lanes, *const kited = st.kited = w + 5 * lanes;
        st.altar_near = w + 6 * lanes, st.worth = reinterpret_cast<float*>(w + 7 * lanes);
        const vec2 spawn = map.ally_spawn_centre;
        const bool shared = map.shared_gems;
        for (int g = 0; g < n; ++g) {
            const auto& group = groups[g];
            cx[g] = group.centre.x, cy[g] = group.centre.y;
            spawn_near[g] = dist(spawn, group.centre);
            gems[g] = group.gems;
            striker[g] = group.strength > 0 ? -1 : 0;
            kited[g] = shared && !group.has_monolith && group.gems >= params::big_gems ? -1 : 0; // big_group
        }
        // Padding lanes: never read back, but their arithmetic must not trap.
        for (int g = n; g < lanes; ++g)
            for (int c = 0; c < 8; ++c) w[c * lanes + g] = 0;
    }
    if (st.short_by != p.short_by || st.per_gold != p.per_gold || st.tribute_gold != p.tribute_gold || st.prospector != p.prospector) {
        st.short_by = p.short_by, st.per_gold = p.per_gold, st.tribute_gold = p.tribute_gold, st.prospector = p.prospector;
        const float per_gold = std::max(0.0f, p.per_gold), tribute_gold = std::max(0.0f, p.tribute_gold);
        const int short_by = p.short_by;
        float* const worth = st.worth;
        if (p.prospector) {
            for (int g = 0; g < n; ++g) {
                const auto& group = groups[g];
                const float gems = static_cast<float>(std::min(group.gems + prospected(group.cluster_gems, 1), short_by));
                const float gold = static_cast<float>(group.gold + prospected(group.cluster_gold, 1));
                worth[g] = std::max(0.0f, gems + per_gold * gold + tribute_gold * gems);
            }
        } else {
            for (int g = 0; g < n; ++g) {
                const auto& group = groups[g];
                const float gems = static_cast<float>(std::min(group.gems, short_by)), gold = static_cast<float>(group.gold);
                worth[g] = std::max(0.0f, gems + per_gold * gold + tribute_gold * gems);
            }
        }
    }
    const std::int32_t *const t_cx = st.cx, *const t_cy = st.cy, *const t_spawn = st.spawn_near, *const t_gems = st.gems;
    const std::int32_t *const t_striker = st.striker, *const t_kited = st.kited, *const t_altar = st.altar_near;
    const float* const t_worth = st.worth;
    const v128_t hx = wasm_i32x4_splat(p.here.x), hy = wasm_i32x4_splat(p.here.y), short_by = wasm_i32x4_splat(p.short_by);
    const v128_t help = wasm_i32x4_splat(params::help_radius);
    const v128_t one = wasm_f32x4_splat(1.0f), slack = wasm_f32x4_splat(1.0002f), horizon = wasm_f32x4_splat(p.horizon);
    const v128_t cap = wasm_f32x4_splat(p.cap_rounds), exposure = wasm_f32x4_splat(params::max_exposure);
    const v128_t channel = wasm_f32x4_splat(static_cast<float>(p.via.channel)), value = wasm_f32x4_splat(p.via.value);
    const v128_t out_base = wasm_i32x4_splat(p.via.channel + p.via.hurt);
    const v128_t inf = wasm_f32x4_splat(std::numeric_limits<float>::infinity());
    const auto rated = [&](v128_t w, v128_t trip) __attribute__((always_inline)) {
        const v128_t rounds = wasm_f32x4_pmax(wasm_f32x4_add(trip, cap), one);
        return wasm_f32x4_mul(wasm_f32x4_div(w, wasm_f32x4_mul(rounds, wasm_f32x4_add(one, wasm_f32x4_div(rounds, horizon)))), slack);
    };
    if (p.banking) {
        // The nearest altar's distance less the tribute range, by group: four altars a step.
        if (!st.altars_known) {
            st.altars_known = true;
            for (int g = 0; g < lanes; ++g) st.altar_near[g] = unreachable;
            const int altars = static_cast<int>(map.altars.size()), padded = (altars + 3) & ~3;
            std::vector<std::int32_t> ax(padded, 1 << 20), ay(padded, 1 << 20);
            for (int a = 0; a < altars; ++a) ax[a] = map.altars[a].pos.x, ay[a] = map.altars[a].pos.y;
            for (int g = 0; g < n && altars > 0; ++g) {
                const v128_t cx = wasm_i32x4_splat(st.cx[g]), cy = wasm_i32x4_splat(st.cy[g]);
                v128_t near = wasm_i32x4_splat(1 << 20);
                for (int a = 0; a < padded; a += 4)
                    near = wasm_i32x4_min(near, wasm_i32x4_max(wasm_i32x4_abs(wasm_i32x4_sub(wasm_v128_load(&ax[a]), cx)),
                                                               wasm_i32x4_abs(wasm_i32x4_sub(wasm_v128_load(&ay[a]), cy))));
                const int least = std::min(std::min(wasm_i32x4_extract_lane(near, 0), wasm_i32x4_extract_lane(near, 1)),
                                           std::min(wasm_i32x4_extract_lane(near, 2), wasm_i32x4_extract_lane(near, 3)));
                st.altar_near[g] = std::max(0, least - cambc::constants::submit_gems_range);
            }
        }
        const v128_t bank_now = wasm_f32x4_splat(p.bank_now), zero = wasm_f32x4_splat(0.0f);
        const v128_t recall = wasm_i32x4_splat(p.recall);
        for (int g = 0; g < n; g += 4) {
            const v128_t near = wasm_i32x4_max(wasm_i32x4_abs(wasm_i32x4_sub(wasm_v128_load(&t_cx[g]), hx)),
                                               wasm_i32x4_abs(wasm_i32x4_sub(wasm_v128_load(&t_cy[g]), hy)));
            const v128_t w = wasm_f32x4_mul(wasm_v128_load(&t_worth[g]), exposure);
            const v128_t trip = wasm_f32x4_pmax(zero, wasm_f32x4_sub(wasm_f32x4_convert_i32x4(near), bank_now));
            const v128_t out_walk = wasm_i32x4_min(wasm_v128_load(&t_altar[g]), wasm_i32x4_add(recall, wasm_v128_load(&t_spawn[g])));
            const v128_t skip = wasm_v128_or(wasm_v128_load(&t_kited[g]), wasm_i32x4_ge(wasm_v128_load(&t_gems[g]), short_by));
            wasm_v128_store(&out[g], wasm_v128_bitselect(inf, rated(w, trip), skip));
            wasm_v128_store(&alt[g], wasm_v128_bitselect(inf, rated(w, wasm_f32x4_convert_i32x4(out_walk)), skip));
        }
        return;
    }
    for (int g = 0; g < n; g += 4) {
        const v128_t near = wasm_i32x4_max(wasm_i32x4_abs(wasm_i32x4_sub(wasm_v128_load(&t_cx[g]), hx)),
                                           wasm_i32x4_abs(wasm_i32x4_sub(wasm_v128_load(&t_cy[g]), hy)));
        v128_t trip = wasm_f32x4_convert_i32x4(near);
        if (p.recall_out)
            trip = wasm_f32x4_pmin(trip, wasm_f32x4_pmax(channel, wasm_f32x4_sub(wasm_f32x4_convert_i32x4(
                                                                    wasm_i32x4_add(out_base, wasm_v128_load(&t_spawn[g]))), value)));
        const v128_t rounds = wasm_f32x4_pmax(wasm_f32x4_add(trip, cap), one);
        const v128_t w = wasm_f32x4_mul(wasm_v128_load(&t_worth[g]), exposure);
        v128_t bound = wasm_f32x4_mul(wasm_f32x4_div(w, wasm_f32x4_mul(rounds, wasm_f32x4_add(one, wasm_f32x4_div(rounds, horizon)))), slack);
        const v128_t helped = wasm_v128_and(wasm_v128_load(&t_striker[g]), wasm_i32x4_le(near, help));
        bound = wasm_v128_bitselect(inf, bound, wasm_v128_or(helped, wasm_i32x4_ge(wasm_v128_load(&t_gems[g]), short_by)));
        wasm_v128_store(&out[g], bound);
    }
}

// The first turn has its own instance: its extra prunes would make every later call dearer. So
// do later turns' banking calls, out of line, past pick_up.
template <bool opening, bool banking = false> [[gnu::flatten]] bool farm_turn(World& world, Pathing& pathing, Safety& safety, Memory& memory);
[[gnu::noinline]] bool farm_banking(World& world, Pathing& pathing, Safety& safety, Memory& memory);
template <bool opening, bool banking> [[gnu::flatten]] bool farm_turn(World& world, Pathing& pathing, Safety& safety, Memory& memory) {
    world.throw_if_stale();
    auto& memo = farm_memo();
    if (!banking && pick_up(world, pathing, memory)) return true;
    const auto& map = world.map();
    const auto& groups = map.groups;
    const int range = world.me().facts().attack_range();
    const float strength = camp_output(world.me()), soften = camp_hit_factor(), reflect = world.me().retaliation();
    const float max_health = my_max_health();
    const float line = recall_line(world, safety);
    const float spare_health = (my_health() - line * max_health) / params::camp_risk;
    // Trips home: the health we spend before one and on each, as crew.cc prices them.
    const float trip_spare = std::max(0.0f, my_health() - line * max_health) / params::crew_trip_risk;
    const float usable_health = max_health * (1.0f - line) / params::crew_trip_risk;
    const float shield = self_shield_amount(world.me());
    const int bag = banking ? memo.banked_bag : bankable_bag(world, pathing);
    const bool banking_now = banking || (bag > 0 && !retaining_gems(world, pathing));
    const int short_by = gems_short(world);
    if (world.is_stale()) return true;
    if constexpr (!opening && !banking)
        if (banking_now) return memo.banked_bag = bag, farm_banking(world, pathing, safety, memory);
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
    const auto kited = [&](int g) __attribute__((always_inline)) { return map.shared_gems && big_group(groups[g]); };
    const auto strong = [&](int g) __attribute__((always_inline)) {
        return groups[g].strength > 0 && (!groups[g].has_monolith || !map.monolith_only) && world.camps[g].state != CampState::cleared && !kited(g);
    };
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
        return shielded_clear(soften * min_camp_damage(world, g, strength, &rounds, reflect), rounds, shield) <= spare_health
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
    const bool gold_farmer = economy_three(world) && world.me().facts().passive == Passive::remote_shop && map_economy(map).tavi_map();
    // A ranged hit in passing costs the walk: only for our choice, or gems no ally will clear. A
    // group that hits back and that we will not finish is only woken by it: hit one only while an
    // ally clears it or, melee, once every striker is awake anyway. Allies merely walking past
    // its reach clear nothing.
    const auto passing = [&](int g) __attribute__((always_inline)) {
        if (!affordable(g)) return false;
        if (g == memory.farm_group) return true;
        if (taken(g)) return false;
        if (groups[g].strength > 0) return ((kited(g) || claimed_by_ally(g)) && ally_engaged(world, g)) || (melee && world.camps[g].fully_awake());
        return melee || groups[g].gems > 0 || gold_farmer;
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
    if (!banks_bag && attack_in_range()) return true;
    if (world.is_stale()) return true;

    // Holders keep a capture going, and more only split the reward.
    const auto ally_holding = [&](int g) __attribute__((always_inline)) {
        return sole_capture_holder(world, groups[g]) || allies_on(world, groups[g].tiles()) >= holders(groups[g]);
    };

    const vec2 here = my_position();
    if (holding_capture(world, pathing)) return true;
    // Carrying, whatever made us retreat stays out of bounds: we route around it or wait outside
    // it rather than step in to be sent back out. Empty-handed, a step in risks nothing (the zone
    // starts beyond any strike's reach) and keeps us at hand for when the pack moves on.
    const auto* zone = bag_at_stake(world) > 0 ? pack_zone(world) : nullptr;

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
            // Else down the static walls.
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
    const float per_gold = prices(world).per_gold * paid * (gold_farmer ? params::gold_farmer_weight : 1.0f);
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
        memory.crew = memory.claim == memory.farm_group && memory.crew;
        memory.claim = memory.farm_group;
        walk_on(memory.farm_group);
        return true;
    }
    // Empty-handed, the recall started at this turn's end reaches a group by way of spawn
    // (FarmRecall), kept by recall_to_farm under the same tests; this turn's walk is spent either
    // way. Not where the recall would be cancelled or not started, nor out of a pocket (its own way).
    const bool recall_out = !banks_bag && my_gems() == 0 && !in_pocket && !stunned_turn && !memory.siege
                            && !test(map.ally_spawn, here) && !channelling() && !safety.threatened(here)
                            && recall_outruns(world, safety, recall_turns(world));
    const FarmRecall via_recall = recall_out ? farm_recall(world, pathing, recall_turns(world)) : FarmRecall{};
    std::optional<Field> from_here;
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
            const float damage = min_camp_damage(world, g, camp_output(a), &rounds, a.retaliation(), a.facts().attack_range());
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
        arrival.reach = f.basic_reach();
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
        const int dash = f.slot_of(AbilityKind::dash);
        const int dash_steps = dash >= 0 ? f.abilities[dash].range() : 0;
        arrival.dash_ready = dash >= 0 ? a.ready_round[dash] - arrival.anchor_round : 0;
        const int first_turn = a.acted ? 1 : 0;
        const bool dash_maybe_ready = a.cooldowns_uncertain();
        arrival.direct = earliest_work_delay(arrival.distance - arrival.reach, first_turn, arrival.dash_ready, dash_steps,
                                            ability_cooldown, dash_maybe_ready);
        // Allies' Home ownership is unknown: allow the fastest new recall and a ready dash on arrival.
        arrival.recall_delay = a.seen_channel == Channel::recall && a.recall_kept ? std::max(0, a.channel_end_round - arrival.anchor_round)
                                                              : first_turn + home_recall_time;
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
        return arrival;
    };
    const auto crew_work = [&](int g, int working, int waiting) __attribute__((always_inline)) {
        CrewWork total;
        for (const auto& a : world.allies) {
            if (a.is_self || !a.alive || comms::claim_of(world, a.index) != g) continue;
            const float output = camp_output(a);
            total.output += output;
            const auto arrival = work_arrival(a, g);
            // Age the work round from the observation, never a guessed hidden position or turn order.
            const int delay = arrival.delay(world.round, waiting);
            total.delayed_damage += output * static_cast<float>(std::min(working, delay));
        }
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
    // Health lost to camps comes back only on spawn: a recall and the walk back out.
    const auto heal = [&](int g, float damage) __attribute__((always_inline)) {
        // The first turn's walk back from a group is the Chebyshev distance, a bound: no field from spawn yet.
        int out = opening ? dist(map.ally_spawn_centre, groups[g].centre) : group_facts[g].to_spawn;
        if (out < 0) out = group_facts[g].to_spawn = pathing.centre_to_spawn(g);
        return out == unreachable ? 0.0f : heal_rounds(world, damage, static_cast<float>(out));
    };
    // Steps from our spawn's centre tile, where a recall lands, to a group's centre.
    const auto spawn_steps = [&](int g) __attribute__((always_inline)) {
        int& out = group_facts[g].to_spawn;
        if (out < 0) out = pathing.centre_to_spawn(g);
        return out;
    };
    // A trip home for health: the walk home or a recall, whichever is quicker, and the walk from spawn
    // back to the group (`steps`, the walk from here, where none from spawn is known).
    const auto home_trip = [&](int g, int steps) __attribute__((always_inline)) {
        int out = opening ? dist(map.ally_spawn_centre, groups[g].centre) : spawn_steps(g);
        if (out == unreachable) out = steps;
        return static_cast<float>(std::min(recall_turns(world), out) + out);
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
    const auto crew_share = [&](const CrewPlan& plan) { return shielded_clear(soften * plan.my_damage, plan.rounds, shield); };
    // The prunes' bounds for a strong group, whose crew may clear it: a crew is us and living
    // allies, each once, so its output O is at most the whole team's; we get our part S / O (all of
    // a winning capture) and its clear takes at least our fastest times S / O. Only our claim's hold
    // (crew_hold) raises it. So a rated bound is crew_rate's up to the team's output (`crew_most`),
    // a plain ratio worth / (trip + fastest S / O) falls with O and stays ours, and a winning
    // capture's bounds take the fastest at the team's output (prune_fastest). Except for our claim
    // or Monolith operation, and for Ren, whose plain prunes are no bound.
    const auto held = [&](int g) __attribute__((always_inline)) { return strong(g) && (g == memory.claim || g == memory.mono_group); };
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
    // Middle-band pricing: a group in the middle band is worth mid_exposure of itself. The bounds
    // below that take the weight as at most 1 scale by params::max_exposure.
    const auto exposure = [&](int g) {
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
    const auto loop_reserve = [&]() __attribute__((always_inline)) {
        const int g = best >= 0 ? best : memory.farm_group;
        if (g != reserved_for) {
            reserved_for = g;
            reserved = walk_reserve(g);
            if (g >= 0) reserved += search_cost_estimate((g == best ? best_steps : dist(here, groups[g].centre)) + max_detour) + travel + tiles_reserve();
        }
        return reserved;
    };
    // With the costliest approach and route to spare, the reserve need not be read.
    const auto loop_floor = small_cost_estimate + end_reserve, ample = loop_floor + 2 * pathing.max_approach_cost() + travel;
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
                    takeover = takeover || (steps_to(groups[g], here) < cambc::constants::capture_time && allies_on(world, groups[g].tiles()) > 0);
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
        worth *= params::max_exposure;
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
        const float worth = static_cast<float>(gems) + per_gold * static_cast<float>(gold) + tribute_gold * static_cast<float>(gems);
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
    const float most_tribute = std::max(0.0f, tribute_gold), most_per_gold = std::max(0.0f, per_gold);
    const FarmMemo::Most* most = nullptr;
    float tested_value = 0; // the threshold the stop was searched for
    const auto threshold = [&]() __attribute__((always_inline)) { return banks_bag ? std::max(best_value, from_altar_value) : bar_lt(); };
    const auto beyond = [&](int j) __attribute__((always_inline)) {
        const auto& m = most[j];
        const int near = m.near - offset;
        if (!banks_bag && near <= params::help_radius) return false;
        const int gems = std::max(0, std::min(prospector ? m.gems_prospected : m.gems, short_by));
        const float worth = params::max_exposure * (static_cast<float>(gems) * (1.0f + most_tribute)
                            + most_per_gold * static_cast<float>(prospector ? m.gold_prospected : m.gold));
        if (banks_bag) return rate(world, worth, std::max(0.0f, static_cast<float>(near) - bank_now) + cap_rounds) * 1.0001f < tested_value;
        return rate(world, worth, std::min(static_cast<float>(near), via_bound(m.spawn_near, 0)) + cap_rounds) * 1.0001f < tested_value;
    };
    // Banking: whether the group's cycle from the altar stays below the threshold.
    const auto altar_below = [&](int g) __attribute__((always_inline)) {
        const int walk = altar_out(g, pathing.centre_to_altar(g));
        if (walk == unreachable) return true;
        const int gems = std::max(0, std::min(worth_gems[g], short_by));
        const float worth = params::max_exposure * (static_cast<float>(gems) * (1.0f + most_tribute) + most_per_gold * worth_gold[g]);
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
        return left >= ample + decode_bound || left >= loop_floor + loop_reserve();
    };
    float mono_seen = -1; // for the traces: our Monolith operation's value this turn, -1 if not reached
    // The pre-facts prunes below, bounded for every group up front (pre_prune_upper): a group whose
    // upper bound is below best_value, which only rises, is pruned there, with nothing read or kept
    // in between. Not for Ren (reflected clears skip the prunes of strong groups) or with crystal
    // hops (group_hop works on a timetable); nor with no strength (clears of no length). The first
    // turn's bound, without its clears, prunes little on maps of fewer groups: there the pass and
    // its tables cost more than they save.
    const bool pre_pruned = !banks_bag && !hop_any && reflect <= 0 && strength > 0 && (opening ? rated && n_groups >= 128 : tight);
    // Banking: groups that change neither the best nor the cycle from the altar (pre_prune_upper).
    const bool pre_banked = banking && !hop_any && strength > 0;
    static std::vector<float> pre_upper, pre_alt;
    if (pre_pruned || pre_banked) {
        if (static_cast<int>(pre_upper.size()) < n_groups + 3) pre_upper.resize(n_groups + 3), pre_alt.resize(n_groups + 3);
        PreUpper p;
        p.here = here, p.short_by = short_by, p.per_gold = per_gold, p.tribute_gold = tribute_gold;
        p.cap_rounds = cap_rounds, p.horizon = horizon, p.recall_out = recall_out, p.prospector = prospector, p.via = via_recall;
        p.banking = pre_banked, p.bank_now = bank_now, p.recall = pre_banked ? recall_turns(world) : 0;
        float* const out = pre_upper.data();
        pre_prune_upper(p, map, out, pre_alt.data());
        // Claims, our last choice and groups whose crew we hold are never pruned before facts.
        constexpr float none = std::numeric_limits<float>::infinity();
        for (std::size_t w = 0; w < claimed_bits.size(); ++w)
            for (auto bits = claimed_bits[w]; bits; bits &= bits - 1)
                if (const int g = static_cast<int>(64 * w) + std::countr_zero(bits); g < n_groups) out[g] = none;
        for (const int g : {farm_group, memory.claim, memory.mono_group})
            if (g >= 0 && g < n_groups && (g == farm_group || !prunable(g) || pre_banked)) out[g] = none;
    }
    static const bool any_mono = [&] {
        for (int g = 0; g < n_groups; ++g)
            if (farm_monolith(world, g)) return true;
        return false;
    }();
    int k = 0;
    for (; k < evaluated && room(); ++k) {
        int g = order ? (*order)[k] : (first + k) % n_groups;
        // best_value moves only with best, from 0.
        if (can_bound && threshold() != tested_value) tested_value = threshold(), stop = stop_from(k);
        if (k >= stop) {
            while (k < evaluated && !is_claimed(g = (*order)[k]) && !held(g) && !(hops && map.may_hop(g)) && (!banks_bag || altar_below(g))) ++k;
            if (k == evaluated) break;
        }
        if (pre_pruned && barred() && pre_upper[g] < bar_lt()) continue;
        if (pre_banked && best >= 0 && pre_upper[g] < std::min(best_value, from_altar_value) && pre_alt[g] < from_altar_value) continue;
        const auto& group = group_data[g];
        const auto& belief = camp_data[g];
        // A help call overrides the best and the share (kept off only by a Monolith best): once one is
        // set, only a group that may be a nearer help changes the pick.
        if (help_group >= 0 && !any_mono && !may_help(group, belief, dist(here, group.centre))) continue;
        if ((group.has_monolith && map.monolith_only) || group.gems + group.gold == 0 || (belief.state == CampState::cleared && ally_holding(g)))
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
                        worth = kf.gems + kf.gold;
                    } else {
                        const float gems = static_cast<float>(std::min(worth_gems[g], short_by));
                        worth = gems + per_gold * worth_gold[g] + tribute_gold * gems;
                    }
                    float fastest;
                    if (kf.version == belief.version && kf.fastest_strength == strength) fastest = kf.fastest;
                    else if (belief.version == 0) fastest = group.health / strength;
                    else kf.version = belief.version, kf.fastest_strength = strength, fastest = kf.fastest = fastest_clear(world, g, strength);
                    if (rated_below(worth, soonest(group, belief, near), fastest, crew_most(g, false))) continue;
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
        if (known.context != context || known.sticky != (g == farm_group)) {
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
            // A Monolith's long clear gives the enemy time to steal it: its side counts twice.
            if (group.has_monolith) weight *= known.home;
            known.weight = weight;
            // A Prospector emblem's extra as if alone on the capture, as the reward is valued.
            known.gems = weight * static_cast<float>(std::min(group.gems + (prospector ? prospected(group.cluster_gems, 1) : 0), short_by));
            known.context = context;
            known.sticky = g == farm_group;
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
        // Ren's for the rated prunes; its plain ones keep the fastest.
        const float exposed = exposure(g);
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
                const float worth = (known.gems + known.gold) * exposed;
                const float trip = std::max(0.0f, soonest(group, belief, near) - bank_now + bank);
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
                if (!from_here) {
                    if ((!tight || g == farm_group) && !claimed && barred() && beaten_near(false)) continue;
                    if (!fuel_ok(full_field_cost_estimate() + loop_floor + loop_reserve())) break;
                    from_here = make_field(pathing.static_walls(), single(here));
                    world.throw_if_stale();
                }
                steps_known = from_here->at(group.centre);
            }
        }
        int steps = steps_known;
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
                if (!pathing.hop_ready(h) && !fuel_ok(2 * full_field_cost_estimate() + loop_floor + loop_reserve())) break;
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
        // A group still respawning when we would arrive costs the wait there.
        const int respawn = respawn_in(belief);
        const int wait = std::max(0, respawn - steps);
        // The rounds stood there run from our arrival. A dasher travels by the turn (step_towards),
        // so measured by its walk a dash would lengthen the wait and drop the group we are nearing.
        const int idle = respawn > 0 && steps == steps_known ? std::max(0, respawn - pathing.travel_turns(steps)) : wait;
        if (idle > params::max_wait) continue;
        // By way of spawn when sooner (`steps` stays the walk: the help radius and the walk's search
        // cap read it). `reach`: rounds until we are there, the stop's value not taken off; `there`:
        // and until it is back.
        const float via = recall_out && steps_known != unreachable ? via_recall.sooner(spawn_steps(g), respawn, steps)
                                                                   : static_cast<float>(unreachable);
        const bool by_spawn = via < static_cast<float>(unreachable);
        const int reach = by_spawn ? via_recall.channel + via_recall.hurt + spawn_steps(g) : steps;
        const int there = std::max(reach, respawn);
        // A Monolith is a crew's, never a help call's.
        if (!banks_bag && group.strength > 0 && !group.has_monolith && belief.state == CampState::alive && steps <= params::help_radius
            && (steps < help_steps || (steps == help_steps && earlier(g, help_group))) && struggling(g))
            help_group = g, help_steps = steps;
        // A capture's gold that completes an emblem shortens the trip home (HomeTrip::rounds) though worth
        // counts it too: floored, so a chain never costs less than nothing and every filter below agrees.
        const float trip = std::max(0.0f, (by_spawn ? via : static_cast<float>(steps + wait)) - bank_now + bank);
        const float gems = known.gems * exposed, gold = known.gold * exposed, fastest = known.fastest;
        // Skip the costly clearing estimate for groups that cannot beat the best even with no
        // clearing. A crew's share can.
        if (!claimed && barred() && prunable(g)
            && ((rated && g != farm_group && beaten(gems + gold, trip, prune_fastest(g, quickest, wins), walk_out, cycle_bank, crew_most(g, wins)))
                || ((!rated || g == farm_group || reflect > 0)
                    && (gems + gold) / (trip + cap_rounds + prune_fastest(g, fastest, wins)) <= bar_le()
                    && (!banks_bag || (gems + gold) / (static_cast<float>(walk_out + capture) + cycle_bank + prune_fastest(g, fastest, wins)) <= from_altar_value))))
            continue;
        // No known way to an altar (sealed, or a centre walls hide) is no deadline: the gold still counts.
        const auto too_late = [&](float clear_rounds) __attribute__((always_inline)) {
            if (known.to_altar < 0) known.to_altar = pathing.centre_to_altar(g);
            const int last = known.to_altar;
            return last != unreachable
                   && static_cast<float>(std::min(steps + wait, there) + capture + last + tribute_turns(world, bag + group.gems)) + clear_rounds > static_cast<float>(left);
        };
        const float worth = gems + gold - toll;
        // Health past what we can spare costs trips home, each a recall and the walk back out. By
        // way of spawn we arrive healed.
        const float budget = by_spawn ? usable_health : trip_spare;
        const float trip_home = home_trip(g, steps);
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
            // claimers are those seen lately and whose expected allies only shrink r. The rate rises
            // in r up to sqrt(trip (horizon + trip)) (rounds of at least 1), then falls; a winning
            // capture's falls in r.
            if (worth > 0 && health > 0 && (shared >= 0 || best >= 0) && g != memory.mono_group) {
                float others = 0;
                const auto& allies = crew_allies_now();
                for (int i = 0; i < allies.n; ++i)
                    if (const auto& a = allies.at[i]; !a.a->is_self && a.a->alive && a.claim == g && (!op || a.seen)) others += crew_output(a);
                const float r = wins ? 0.0f : std::min(health / (strength + others), std::max(std::sqrt(trip * (horizon + trip)), 1.0f - trip));
                const float most = rate(world, worth * (wins ? 1.0f : strength * r / health), trip + r)
                                   * (op && memory.claim == g ? crew_hold(g) : 1.0f) * 1.0001f;
                if (most < shared_value || (best >= 0 && most < best_value)) continue;
            }
            const int waiting = fresh ? std::max(0, belief.respawn_round - round) : 0;
            const int working = std::max(0, reach - waiting);
            const auto crew = crew_work(g, working, waiting);
            const float health_left = health - std::max(0.0f, crew.output * static_cast<float>(working) - crew.delayed_damage);
            if (health <= 0 || health_left <= 0) continue;
            // A strong group's crew as its proposer counts it, available allies included: joining
            // only on the claimers seen so far, each joiner would find too small a crew.
            const bool expect = may_expect(g);
            const CrewPlan plan = op ? plan_crew(world, crew_allies_now(), g, strength, expect, crew_cap(g)) : CrewPlan{};
            const float others = op ? plan.output - strength : crew.output;
            // A capture that wins the game is the team's, not a share: what counts is how soon.
            const float rounds = health_left / (strength + others), part = wins ? 1.0f : strength * rounds / health;
            const int trips = op ? extra_trips(crew_share(plan), budget, usable_health) : 0;
            // No capture rounds: the claimer holds it, and the crew moves on once it is cleared.
            // A crew we are in holds us against small pulls: one member leaving shrinks it for the rest.
            const float value = rate(world, worth * part, trip + rounds + static_cast<float>(trips) * trip_home)
                                * (op && memory.claim == g ? crew_hold(g) : 1.0f);
            // Only a better share counts, and the final pick takes none a group of our own beats.
            if (g == memory.mono_group) mono_seen = value;
            if ((value < shared_value || (value == shared_value && !earlier(g, shared))) || (best >= 0 && value <= best_value) || too_late(rounds))
                continue;
            // Kited, we take the hits alone: our share of them must fit the health we spare. Unless we
            // see the camp's health falling, as if the claimers did nothing before we arrive.
            if (kited(g) && group.strength > 0) {
                const bool worked = belief.last_damaged_round >= round - 1;
                float joint_rounds = 0;
                const float hits = soften * min_camp_damage(world, g, strength + others, &joint_rounds)
                                   * (worked ? strength * rounds / health : strength / (strength + others));
                if (hits > spare_health) continue;
            }
            shared = g, shared_value = value, shared_steps = steps;
            if (may_floor()) floor_value = value;
            shared_priced = {'J', trips, plan.tank ? plan.tank->index : -1, plan.n_expected, strength + others, crew_share(plan)};
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
        const float alone_damage = shielded_clear(soften * known.damage, known.rounds, shield);
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
        if (kite >= 0 && kite < clear_rounds + heal(g, alone_damage) + static_cast<float>(trips) * trip_home) {
            spell = true;
            clear_rounds = kite, trips = 0;
            priced = {'K', 0, -1, 0, strength};
        }
        // A Monolith is a crew's only: alone, the walk there is often given up for nearer camps on
        // the way, and a lone chip only softens it for whoever comes next.
        bool late = too_late(clear_rounds) || (group.has_monolith && belief.state != CampState::cleared);
        float value = late ? 0.0f : rate(world, worth, trip + clear_rounds + capture + static_cast<float>(trips) * trip_home);
        // Banking: the cycle from the altar after the tribute (from_altar_value's candidate).
        const float via_altar = banks_bag && walk_out != unreachable && belief.state == CampState::respawning
                                    ? std::max(0.0f, static_cast<float>(belief.respawn_round - round - walk_out) - bank_now) : 0.0f;
        const auto altar_rate = [&](float part_worth, float rounds, int home_trips) __attribute__((always_inline)) {
            return rate(world, part_worth, static_cast<float>(walk_out) + cycle_bank + via_altar + rounds + capture + static_cast<float>(home_trips) * trip_home);
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
                for (int i = 0; i < allies.n; ++i) {
                    const auto& a = allies.at[i];
                    if (a.a->is_self || !a.a->alive) continue;
                    if (a.claim == g) {
                        if (a.seen) claimers += crew_output(a), all += crew_output(a), ++members;
                    } else if (expect && crew_available(world, allies, a, g)) {
                        all += crew_output(a), ++members;
                    }
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
                const int my_trips = extra_trips(crew_share(plan), budget, usable_health);
                // Held while ours, as a crew's share is; a fresh proposal with an op of an ally's under
                // way gives way to joining it rather than split the free allies.
                const float hold = memory.claim == g ? crew_hold(g)
                                   : plan.claimers == 0 && rival_op() ? params::crew_rival_factor : 1.0f;
                const float crew_value = rate(world, worth * part, trip + plan.rounds + capture + static_cast<float>(my_trips) * trip_home) * hold;
                debug_block({
                    if (group.has_monolith && round % 25 == 0)
                        std::printf("MONO VALUE %d %u g%d worth %.0f part %.2f trip %.0f rounds %.0f trips %d home %.0f crew %d+%d output %.0f value %.4f best-so-far %.4f\n",
                                    round, my_handle(), g, worth, part, trip, plan.rounds, my_trips, trip_home, plan.claimers, plan.n_expected,
                                    plan.output, crew_value, best_value);
                });
                if (crew_value > value) {
                    value = crew_value, late = false, spell = false;
                    clear_rounds = plan.rounds, trips = my_trips, share = worth * part;
                    priced = {'C', my_trips, plan.tank ? plan.tank->index : -1, plan.n_expected, plan.output, crew_share(plan)};
                }
            }
        }
        if (g == memory.mono_group) mono_seen = value;
        if (late) continue;
        if (value > best_value || (value == best_value && earlier(g, best)))
            best = g, best_value = value, best_steps = steps, best_spell = spell, best_priced = priced;
        if (banks_bag && walk_out != unreachable) from_altar_value = std::max(from_altar_value, altar_rate(share, clear_rounds, trips));
    }
    if (k < evaluated) note_shortcut("farm-partial-evaluation");
    // An ally's hold that pays more with us on it: the rounds we then hold free the holder, worth
    // what our best cycle earns a round, so the walk is what it costs.
    if (!banks_bag && !memory.banking && evaluated == n_groups && takes_over(world)) {
        const float work_rate = best_value;
        world.each_cleared([&](int g) {
            const auto& G = groups[g];
            // A payout is at most capture_time rounds away, so no longer walk arrives before it (takeover_worth).
            const int least = steps_to(G, here); // no walk to its tiles is shorter
            if (least >= cambc::constants::capture_time || allies_on(world, G.tiles()) == 0 || !may_take_over(world, G)) return;
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
    if (best < 0) {
        // Cut short before weighing even last turn's choice: walk on towards it, as its crew if we were.
        if (k == 0 && memory.farm_group >= 0)
            memory.claim = memory.farm_group, memory.crew = crew_of_choice, walk_on(memory.farm_group);
        // Waiting on a respawning group's camp tile would hold it back for good (rules capture.respawn).
        else if (const int on = map.group_at(here); on >= 0 && world.camps[on].state == CampState::respawning)
            pathing.step_towards(map.standable, zone);
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
    if (recall_out && steps_data[best] == best_steps
        && via_recall.sooner(spawn_steps(best), respawn_in(world.camps[best]), best_steps) < static_cast<float>(unreachable)) {
        memory.recall_farm = best;
        debug_block({ std::printf("RFCHOOSE %d %u %d %d %d %d\n", round, my_handle(), best, best_steps, spawn_steps(best),
                                  static_cast<int>(via_recall.value)); });
    }
    if (map.any_group_hop() && beyond_walk(world, pathing, best) && (in_pocket || cross(best))) return true;
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
    // With an enemy near, a dasher's live routes walk round the hole lines its fields cross.
    const bool dasher = world.me().facts().has_dash();
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
        if (search) {
            if (!pathing.step_towards(off_zone(groups[best].tiles()), zone, cap, groups[best].centre) && dasher) walk_on(best);
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
    // In range and sight with the attack unspent: our pick may have been refused in passing.
    std::optional<bitboard> refused;
    if (test(*tiles, here) && my_can_attack() && attack_camp(world, [&](int g) { return g == best; }) < 0) {
        refused.emplace(*tiles);
        refused->set(here, false);
    }
    const auto& goals = refused ? *refused : *tiles;
    if (test(goals, here)) { // attacked from here; stay
        cast_at_camp(world, best);
        reset_and_attack_camp(world, best);
        if (melee) step_onto_cleared(world, pathing, best);
        return true;
    }
    bool walked = fuel_ok(search_cost_estimate(cap) + end_reserve)
                      ? pathing.step_towards(off_zone(goals), zone, cap, groups[best].centre)
                            || pathing.step_towards_within(off_zone(groups[best].adjacent()), zone, cap, groups[best].centre)
                      : (note_shortcut("farm-no-route"), walk_on(best));
    if (!walked && dasher) walk_on(best);
    if (walked) {
        // A hit on a champion is worth its damage; on a camp, the gems it brings closer.
        see_revealed(world, pathing, safety);
        if (!strike_enemy(world)) attack_camp(world, passing);
        cast_at_camp(world, best); // only casts that allow walking remain
        reset_and_attack_camp(world, best);
    }
    return true;
}
bool farm_banking(World& world, Pathing& pathing, Safety& safety, Memory& memory) {
    return farm_turn<false, true>(world, pathing, safety, memory);
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
