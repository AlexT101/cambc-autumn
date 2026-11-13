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

[[gnu::always_inline]] inline bool bushes_in_ward_range(const StaticMap& map, const vec2& here) {
    // The board waits for the turn-end queue; until then a square around us answers.
    return map.near_bushes_ready() ? test(map.near_bushes(), here) : any_within(map.bushes, here, ward_range());
}

[[gnu::always_inline]] inline void bush_ward_candidates(const StaticMap& map, const vec2& here, bitboard& candidates) {
    candidates.clear();
    candidates.draw_chebyshev(here, cambc::constants::ward_placement_radius);
    candidates &= map.bushes;
    if (test(map.bushes, here)) drop(candidates, map.bush_cluster(here).tiles);
}

// The reveal ward (Idea C), after a fight last turn or health lost since our last turn (a hidden attacker, or
// camps): a ward into the unseen bush cluster within ward range that most likely holds an enemy that could strike
// us, or we it. It sees the cluster from placement, so this turn's strikes see what it reveals. True once a tile is
// tried: a failed try onto a hidden unit reveals that tile (turn.hidden_blocker).
inline constexpr std::uint64_t reveal_fuel_floor = 60000, reveal_grow_fuel = 15000;
int warded_round = -1000; // our last placement: the ward is back cambc::constants::ward_cooldown rounds later
bool reveal_ward(const World& world, Memory& memory) {
    // The scan (~500 fuel) falls in heavy fight turns: skipped outright while the ward recharges.
    static float last_health = -1;
    const bool hurt = world.me().health < last_health;
    last_health = world.me().health;
    if (world.round < warded_round + static_cast<int>(cambc::constants::ward_cooldown)) return false;
    if (stunned_turn || !world.me().alive || (!engaged_before && !hurt)) return false;
    const auto& map = world.map();
    const vec2 here = world.me().pos;
    // Scalar bounds first: most turns have no unseen enemy near.
    std::uint32_t maybe = 0;
    const int own = world.me().facts().attack_range();
    // Every champion's one-turn reach bound, not its own (attack_reach_in_turn costs too much here).
    const int reach = std::max<int>(Strike::max_reach, own) + 1;
    for (const auto& e : world.enemies) {
        if (!e.alive || e.visible || !e.tracked || e.index >= 16) continue;
        // Where it could strike us from, or we it; `possible` lies within a step a turn of its last
        // tile, and a dash's 2 more.
        if (dist(here, e.pos) - e.turns_since_fixed - (e.facts().has_dash() ? 2 + 2 * (e.turns_since_fixed / 8) : 0) > reach) continue;
        maybe |= 1u << e.index;
    }
    if (!maybe) return false;
    world.throw_if_stale();
    if (here.x < 0 || !bushes_in_ward_range(map, here)) return false;
    if (cambc::self().ward_cooldown() > 0 || channelling()) return false;
    // One test for all: their possible tiles in bushes near us (most turns: none).
    static bitboard hidden{cambc::uninitialized};
    bool first = true;
    for (auto left = maybe; left; left &= left - 1) {
        const auto& e = world.enemies[static_cast<std::size_t>(std::countr_zero(left))];
        if (first) and_into(e.possible, map.bushes, hidden), first = false;
        else or_into(hidden, e.possible, hidden);
    }
    and_into(hidden, map.bushes, hidden);
    if (!any_within(hidden, here, reach)) return false;
    std::uint32_t suspects = 0;
    for (auto left = maybe; left; left &= left - 1) {
        const auto& e = world.enemies[static_cast<std::size_t>(std::countr_zero(left))];
        and_into(e.possible, map.bushes, hidden);
        if (any_within(hidden, here, reach)) suspects |= 1u << e.index;
    }
    if (!suspects) return false;
    // The rest of the turn comes after: a giant cluster (~90k) grows over turns, 15k a turn, its work kept.
    if (!map.find_bush_clusters(here, ward_range(), std::max(reveal_fuel_floor, fuel() - std::min<std::uint64_t>(fuel(), reveal_grow_fuel)))) {
        note_shortcut("reveal-no-clusters");
        return false;
    }
    static bitboard candidates{cambc::uninitialized}, inside{cambc::uninitialized}, mass{cambc::uninitialized},
        best_mass{cambc::uninitialized};
    bush_ward_candidates(map, here, candidates);
    drop(candidates, map.enemy_spawn);
    const BushCluster* pick = nullptr;
    float best = 0;
    while (!candidates.is_empty()) {
        const auto& c = map.bush_cluster(first_tile(candidates));
        float score = 0;
        bool credible = false;
        mass.clear();
        for (auto left = suspects; left; left &= left - 1) {
            const auto& e = world.enemies[static_cast<std::size_t>(std::countr_zero(left))];
            and_into(e.possible, c.tiles, inside);
            const auto& close = within(inside, here, reach);
            const auto n = board_count(close);
            if (!n) continue;
            mass |= close;
            const float share = static_cast<float>(n) / static_cast<float>(board_count(e.possible));
            credible |= share >= params::reveal_mass;
            // Last seen in or beside the cluster: it most likely ran into it.
            score += share * (any_within(c.tiles, e.pos, 1) ? params::reveal_prior : 1.0f);
        }
        if (credible && score > best) best = score, pick = &c, best_mass.clear(), best_mass |= mass;
        drop(candidates, c.tiles);
    }
    if (!pick) return false;
    static bitboard tiles{cambc::uninitialized}, allied{cambc::uninitialized};
    tiles.clear();
    tiles.draw_chebyshev(here, cambc::constants::ward_placement_radius);
    tiles &= pick->tiles;
    drop(tiles, map.enemy_spawn);
    cambc::vision::ward_tiles_into(team::ally, allied);
    drop(tiles, allied);
    // The tile seeing most of the suspects' tiles (ward sight: radius 6), tried best first.
    Unwritten<std::pair<int, vec2>, 25> scratch;
    auto& order = scratch.a;
    int n = 0;
    for (auto p : Tiles<25>{tiles}) {
        const int seen = static_cast<int>(count_within(best_mass, p, static_cast<int>(cambc::constants::ward_vision_radius)));
        int i = n++;
        for (; i > 0 && order[static_cast<std::size_t>(i - 1)].first < seen; --i) order[static_cast<std::size_t>(i)] = order[static_cast<std::size_t>(i - 1)];
        order[static_cast<std::size_t>(i)] = {seen, p};
    }
    for (int i = 0; i < n; ++i)
        if (try_ward(order[static_cast<std::size_t>(i)].second, memory)) {
            warded_round = world.round;
            debug_block({
                const vec2 w = order[static_cast<std::size_t>(i)].second;
                std::printf("RWARD %d %u %d %d %u %.2f\n", world.round, my_handle(), w.x, w.y, suspects, best);
            });
            return true;
        }
    return n > 0;
}

// The ward policy. A ward tile's value is the sight it adds over our own of tiles an enemy can stand
// on, as the draft's best_ward weighs it: three times within ability reach, once within ward reach
// (placement 2 plus ward sight 6), around where we will be (our work site's stand tiles) and here.
// A bush tile is seen only from inside its cluster (vision.occlusion), so a ward in a cluster beside
// our work scores all of it. Our current ward is valued alike, and replaced only by a clear margin:
// it keeps watching our work while we walk home and back, and moves once our work does.
inline constexpr float ward_replace_margin = 1.25f;
inline constexpr int ward_reach = 2 + 6;
// Fuel to score one candidate (a shadowcast and its chunks), and a site's boards (a cast a stand tile).
inline constexpr std::uint64_t ward_candidate_cost = 1500, ward_site_cost = 6000;

// What a ward (radius 6) or a champion (8) on p sees: from a bush, its own cluster too. p's cluster
// must be found.
void ward_sight_from(const StaticMap& map, vec2 p, int r, bitboard& out) {
    static bitboard opaque{cambc::uninitialized};
    if (!test(map.bushes, p)) return map.walls_and_bushes.shadow_cast_into(p, static_cast<std::uint16_t>(r), out);
    xor_into(map.walls_and_bushes, map.bush_cluster(p).tiles, opaque);
    opaque.shadow_cast_into(p, static_cast<std::uint16_t>(r), out);
}

// The chunks within r of p: [x0, x1] x [y0, y1].
struct SightWindow {
    int x0, x1, y0, y1;
};
inline SightWindow sight_window(vec2 p, int r) {
    const auto& layout = cambc::detail::layout();
    return {std::max(0, p.x - r) >> 3, std::min(layout.width - 1, p.x + r) >> 3, std::max(0, p.y - r) >> 3,
            std::min(layout.height - 1, p.y + r) >> 3};
}

// ward_sight_from at one radius, by tile, as its window's chunks row by row: the map fixes it, and a
// champion weighs the same tiles again and again (86% of ward casts repeated one). The cast leaves
// nothing beyond r of p, so the window is all of it. Static and zero: nothing to clear.
struct SightCache {
    static constexpr int tiles = 100 * 100, words = 3 * 3;
    std::uint64_t sight[tiles][words];
    bool known[tiles];
};
SightCache ward_sights, champion_sights;

// p's sight at r (always the same r for a cache), cast into `out` on first ask; null off the map or
// for a map or window too large for the cache.
const std::uint64_t* cached_sight(const StaticMap& map, SightCache& cache, vec2 p, int r, const SightWindow& w, bitboard& out) {
    // Rows of at most 3 chunks, as the scoring reads them.
    if (!in_bounds(p) || map_width * map_height > SightCache::tiles || w.x1 - w.x0 > 2 || w.y1 - w.y0 > 2) return nullptr;
    const int i = tile_index(p);
    std::uint64_t* const words = cache.sight[i];
    if (!cache.known[i]) {
        ward_sight_from(map, p, r, out);
        const std::uint64_t* const seen = out.ptr();
        const int stride = static_cast<int>(cambc::detail::layout().chunk_stride);
        std::uint64_t* to = words;
        // At most 3x3 words: vectorised, the copy's alias checks cost ~400.
#pragma clang loop vectorize(disable) interleave(disable)
        for (int cy = w.y0; cy <= w.y1; ++cy)
#pragma clang loop vectorize(disable) interleave(disable)
            for (int at = cy * stride + w.x0, end = cy * stride + w.x1; at <= end; ++at) *to++ = seen[at];
        cache.known[i] = true;
    }
    return words;
}

// ward_sight_from(map, p, vision_radius, out), from the cache once cast.
void champion_sight_into(const StaticMap& map, vec2 p, bitboard& out) {
    const SightWindow w = sight_window(p, vision_radius);
    const int i = in_bounds(p) && map_width * map_height <= SightCache::tiles ? tile_index(p) : -1;
    if (i >= 0 && champion_sights.known[i]) {
        clear_board(out);
        std::uint64_t* const board = out.ptr();
        const std::uint64_t* from = champion_sights.sight[i];
        const int stride = static_cast<int>(cambc::detail::layout().chunk_stride);
#pragma clang loop vectorize(disable) interleave(disable)
        for (int cy = w.y0; cy <= w.y1; ++cy)
#pragma clang loop vectorize(disable) interleave(disable)
            for (int at = cy * stride + w.x0, end = cy * stride + w.x1; at <= end; ++at) board[at] = *from++;
        return;
    }
    if (!cached_sight(map, champion_sights, p, vision_radius, w, out)) ward_sight_from(map, p, vision_radius, out);
}

// Where we will be, as a draft ward site (altar a at groups + a): our claimed group, else an altar we
// wait at (farm_group stays set while we do), else our farm group; -1 for none.
int ward_site(const StaticMap& map, const Memory& memory) {
    const int groups = static_cast<int>(map.groups.size());
    if (memory.claim >= 0 && memory.claim < groups) return memory.claim;
    if (memory.wait_altar >= 0 && memory.wait_altar < static_cast<int>(map.altars.size())) return groups + memory.wait_altar;
    if (memory.farm_group >= 0 && memory.farm_group < groups) return memory.farm_group;
    return -1;
}

// The site's share of every ward's value: tiles an enemy can stand on within ability reach (near) and
// ward reach (far) of its stand tiles (a group's camp tiles, else the altar's tribute tiles) that a
// champion on one of them may not see. A group's camp tiles count in both: reading a camp's state
// needs one in view (camps.state), and between visits we are away. False if a stand tile's bush
// cluster is not found above `floor`.
bool ward_site_boards(const StaticMap& map, int site, std::uint64_t floor, bitboard& near, bitboard& far) {
    static bitboard own{cambc::uninitialized}, one{cambc::uninitialized};
    const int groups = static_cast<int>(map.groups.size());
    bool first = true, found = true;
    const auto add = [&](vec2 p) {
        if (!found) return;
        if (test(map.bushes, p) && !map.find_bush_clusters(p, 0, floor)) {
            found = false;
            return;
        }
        champion_sight_into(map, p, first ? own : one);
        if (!first) own &= one;
        first = false;
    };
    const auto draw = [&](bitboard& out, int r) {
        clear_board(out);
        if (site < groups)
            for (const auto& m : map.groups[site].members) draw_square(out, m.pos, static_cast<float>(r));
        else
            draw_square(out, map.altars[site - groups].pos, static_cast<float>(r + 1));
        out &= map.open_for_them;
        drop(out, own);
        if (site < groups)
            for (const auto& m : map.groups[site].members) set_tile(out, m.pos);
    };
    if (site < groups)
        for (const auto& m : map.groups[site].members) add(m.pos);
    else {
        const vec2 a = map.altars[site - groups].pos;
        for (int dy = -1; dy <= 1; ++dy)
            for (int dx = -1; dx <= 1; ++dx)
                if (const vec2 q{a.x + dx, a.y + dy}; in_bounds(q) && test(map.open_for_us, q)) add(q);
        if (first) add(a);
    }
    if (!found) return false;
    draw(near, ability_range);
    draw(far, ward_reach);
    return true;
}

// 3 a tile of `near` and 1 of the rest of `far` (near within far) a ward on w sees. w's cluster must be found.
int ward_value(const StaticMap& map, vec2 w, const bitboard& near, const bitboard& far) {
    static bitboard sight{cambc::uninitialized};
    const int r = static_cast<int>(cambc::constants::ward_vision_radius);
    const auto& layout = cambc::detail::layout();
    const int stride = static_cast<int>(layout.chunk_stride);
    const SightWindow window = sight_window(w, r);
    const int x0 = window.x0, x1 = window.x1, y0 = window.y0, y1 = window.y1;
    const std::uint64_t *const near_w = near.ptr(), *const far_w = far.ptr();
    if (const std::uint64_t* seen = cached_sight(map, ward_sights, w, r, window, sight)) {
        const auto chunk = [&](int at, std::uint64_t s) {
            return 2 * __builtin_popcountll(s & near_w[at]) + __builtin_popcountll(s & far_w[at]);
        };
        int value = 0;
        const int nx = x1 - x0 + 1;
#pragma clang loop vectorize(disable) interleave(disable)
        for (int cy = y0, at = y0 * stride + x0; cy <= y1; ++cy, at += stride, seen += nx) {
            value += chunk(at, seen[0]);
            if (nx > 1) value += chunk(at + 1, seen[1]);
            if (nx > 2) value += chunk(at + 2, seen[2]);
        }
        return value;
    }
    ward_sight_from(map, w, r, sight);
    const std::uint64_t* const seen = sight.ptr();
    // Whole chunks, unmasked: the cast overwrites the board, so it holds nothing beyond r of w.
    const auto chunk = [&](int at) {
        const std::uint64_t s = seen[at];
        return 2 * __builtin_popcountll(s & near_w[at]) + __builtin_popcountll(s & far_w[at]);
    };
    int value = 0;
    // At r 6 a row spans at most 3 chunks, read at fixed offsets: as a loop it cost ~2x (best_ward).
    if (x1 - x0 <= 2)
        for (int cy = y0, at = y0 * stride + x0; cy <= y1; ++cy, at += stride) {
            value += chunk(at);
            if (x1 > x0) value += chunk(at + 1);
            if (x1 > x0 + 1) value += chunk(at + 2);
        }
    else
        for (int cy = y0; cy <= y1; ++cy)
            for (int at = cy * stride + x0, end = cy * stride + x1; at <= end; ++at) value += chunk(at);
    return value;
}

// When our ward is ready: the best tile within placement range, if it beats our current ward's value
// by the margin. `start`: the turn's start, where the strike search follows and bush clusters grow
// at most reveal_grow_fuel (the turn end grows the rest).
bool place_ward(const World& world, Memory& memory, bool start) {
    world.throw_if_stale();
    // A stun refuses every ward, and the thrown error costs ~3.9k fuel.
    if (stunned_turn || !world.me().alive || channelling() || cambc::self().ward_cooldown() > 0) return false;
    const auto& map = world.map();
    // Off the map: killed this turn (Ren's retaliation), after world.me() was read alive.
    const vec2 here = my_position();
    if (here.x < 0) return false;
    int site = ward_site(map, memory);
    static bitboard near{cambc::uninitialized}, far{cambc::uninitialized}, own{cambc::uninitialized},
        tiles{cambc::uninitialized}, allied{cambc::uninitialized};
    cambc::vision::ward_tiles_into(team::ally, allied);
    const int allied_near = static_cast<int>(count_within(allied, here, ward_range()));
    // The map is static: a look from the same tile, for the same site, ward and allied wards in
    // placement range, that placed nothing would again.
    static struct {
        vec2 here{-1, -1}, ward{-1, -1};
        int site = -2, allied = -1;
    } looked;
    if (looked.here == here && looked.ward == memory.ward && looked.site == site && looked.allied == allied_near) return false;
    const int asked_site = site;
    if (start) {
        const vec2 drafted = site >= 0 ? map.drafted_ward(site) : vec2{-1, -1};
        if (!in_bounds(drafted) || dist(here, drafted) > ward_range() || !test(map.open_for_us, drafted) || test(allied, drafted)) return false;
    }
    const std::uint64_t least = start ? reveal_fuel_floor : end_reserve;
    const std::uint64_t floor = start ? std::max(least, fuel() - std::min<std::uint64_t>(fuel(), reveal_grow_fuel)) : end_reserve / 2;
    if (!fuel_ok(least + ward_site_cost + ward_candidate_cost)) {
        note_shortcut("ward-fuel");
        return false;
    }
    if ((bushes_in_ward_range(map, here) && !map.find_bush_clusters(here, ward_range(), floor))
        || (in_bounds(memory.ward) && test(map.bushes, memory.ward) && !map.find_bush_clusters(memory.ward, 0, floor))) {
        note_shortcut("ward-no-bushes-clusters");
        return false;
    }
    // Growth may have spent down to its floor.
    if (!fuel_ok(least + ward_site_cost + ward_candidate_cost)) {
        note_shortcut("ward-fuel");
        return false;
    }
    static bitboard site_near{cambc::uninitialized}, site_far{cambc::uninitialized};
    static int boards_site = -1;
    if (site >= 0 && site != boards_site) {
        boards_site = -1; // the boards are rewritten whether or not they finish
        // A stand tile's cluster still growing: here alone this time.
        if (ward_site_boards(map, site, floor, site_near, site_far)) boards_site = site;
        else note_shortcut("ward-no-site-clusters"), site = -1;
        if (!fuel_ok(least + 2 * ward_candidate_cost)) {
            note_shortcut("ward-fuel");
            return false;
        }
    }
    champion_sight_into(map, here, own);
    for (auto* b : {&near, &far}) {
        clear_board(*b);
        draw_square(*b, here, static_cast<float>(b == &near ? ability_range : ward_reach));
        *b &= map.open_for_them;
        drop(*b, own);
        if (site >= 0) *b |= b == &near ? site_near : site_far;
    }
    const int old = in_bounds(memory.ward) ? ward_value(map, memory.ward, near, far) : 0;
    const auto remember = [&] { looked = {here, memory.ward, asked_site, allied_near}; };
    // Every candidate sees within 8 of here at most: when that bound fails the margin, none passes.
    const int bound = static_cast<int>(2 * count_within(near, here, ward_reach) + count_within(far, here, ward_reach));
    if (static_cast<float>(bound) <= ward_replace_margin * static_cast<float>(old)) {
        if (site == asked_site) remember();
        return false;
    }
    // Never a wall, hole, altar, their spawn or a visible allied ward, ours included (wards.placement).
    tiles.clear();
    tiles.draw_chebyshev(here, cambc::constants::ward_placement_radius);
    tiles &= map.open_for_us;
    drop(tiles, allied);
    const vec2 drafted = site >= 0 ? map.drafted_ward(site) : vec2{-1, -1};
    // The turn start, where the strike search follows, weighs the draft's tile alone (as charybdis's
    // planned ward); the full search waits for the turn end, which runs on what the turn leaves.
    if (start) {
        if (!in_bounds(drafted) || !test(tiles, drafted)) return false;
        clear_board(tiles);
        set_tile(tiles, drafted);
    }
    Unwritten<std::pair<int, vec2>, 25> scratch;
    auto& order = scratch.a;
    int n = 0;
    bool cut = false;
    const Tiles<25> candidates{tiles};
    // A candidate costs under ward_candidate_cost, so with room for all of them no check before one fails.
    const bool room = fuel_ok(least + static_cast<std::uint64_t>(candidates.end() - candidates.begin() + 1) * ward_candidate_cost);
    for (auto p : candidates) {
        if (!room && !fuel_ok(least + ward_candidate_cost)) {
            cut = true;
            note_shortcut("ward-fuel");
            break;
        }
        const int v = ward_value(map, p, near, far);
        if (static_cast<float>(v) <= ward_replace_margin * static_cast<float>(old)) continue;
        // Ties go to the draft's tile.
        int i = n++;
        for (; i > 0 && (order[static_cast<std::size_t>(i - 1)].first < v || (order[static_cast<std::size_t>(i - 1)].first == v && p == drafted)); --i)
            order[static_cast<std::size_t>(i)] = order[static_cast<std::size_t>(i - 1)];
        order[static_cast<std::size_t>(i)] = {v, p};
    }
    if (!start && !cut && n == 0 && site == asked_site) remember();
    // A unit unseen on the tile (a teammate's ward in a bush) refuses it without an error.
    for (int i = 0; i < n; ++i)
        if (const vec2 p = order[static_cast<std::size_t>(i)].second; try_ward(p, memory)) {
            warded_round = world.round;
            debug_block({ std::printf("WARD %d %u %d %d %d %d\n", world.round, my_handle(), p.x, p.y, order[static_cast<std::size_t>(i)].first, old); });
            return true;
        }
    return false;
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
        reguard_willow(world, pathing, safety);
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
    // A siege or a Monolith crew at work stands in its target's fire, priced by its own heal trips: the
    // search counting it would step off the stand for the work to walk back to it next turn. Not on
    // the way home or to an altar, where that fire is the search's to price.
    if (memory.claim >= 0 && (memory.siege || memory.claim == memory.mono_group) && memory.camp_fled < 0 && !intent.to_altar)
        intent.own_fire = memory.claim;
    intent.aim = chase_aim(world, pathing, safety);
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

// yield_capture steps only off a cleared group's tile: most turns need none of its tests.
bool on_cleared_group(const World& world) {
    const vec2 here = my_position();
    if (!in_bounds(here)) return false;
    const int g = world.map().group_at(here);
    return g >= 0 && world.camps[g].state == CampState::cleared;
}

// The least fuel decide's goal steps (a bag, a shopping trip, a chase, a contest, a siege, the farm) and the siege and
// farm finish on: with less at their start the turn ran out 98% and 99.7% of the time (5,120 games at the real budget,
// research/ideas-2026-11-12/fightfuel).
inline constexpr std::uint64_t goal_least = 4000, farm_least = 6000;
void decide(World& world, Pathing& pathing, Safety& safety, Memory& memory) {
    comeback::cooked(world); // every turn: the cook's hysteresis reads each round's scores
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
    if (state.contains(cambc::champion_state::recalling) && continue_recall(world, pathing, safety, memory, home, recall_farm)) {
        recall_feint = false;
        return;
    }
    // A channel refuses a ward, so this is its first chance; its sight counts this turn
    // (probe-ward-sight). The reveal ward first: it answers a hidden attacker now, and either takes
    // the cooldown.
    if (reveal_ward(world, memory)) {
        see_again(world, pathing, safety);
        home.reset();
    }
    if (place_ward(world, memory, true)) {
        see_again(world, pathing, safety);
        home.reset();
    }

    // Shopping, heals and shields do not move us.
    const bool on_spawn = test(world.map().ally_spawn, my_position());
    if (shop(world, memory, on_spawn, on_spawn || world.me().facts().passive == Passive::remote_shop)) {
        world.reread_self();
        home.reset();
    }
    fixc_bush_threatened = false;
    if (!world.me().can_act(world.round)) return;
    fixc_bush_threatened = fixc_bush_threat(world, safety);
    if (const auto* ender = game_ender(world); ender && holds_hard_stop(world, *ender)) {
        stop_game_ender(world, pathing, memory, *ender);
        return;
    }
    const bool willow = support_healer(world.me());
    const bool prism = support_protected(world, world.me());
    // Healing needs a turn end on spawn; a recall arrives at turn start. Under an awake camp, only
    // while we miss more than it takes a round: else we would mend forever while it stays awake.
    const float missing = on_spawn ? my_max_health() - my_health() : 0.0f;
    const bool mend = missing > 0 && missing > (camps_reach_spawn(world) ? safety.camp_damage(my_position()) + 0.01f : 0.0f);
    bool leave = !mend && (home ? *home : want_home(world, pathing, safety, memory));
    if (leave && fixc_commit(world, pathing)) leave = false;
    // Willow at work heals first, and the work goes on without the strike search.
    const bool willow_free = willow && !mend && !leave;
    const bool working = willow_free && support_work(world, pathing, safety, memory);
    const bool strikes = !working && strike_possible(world);
    bool mate_eligible = false;
    // Out of a fight, with the mate not needing us, Willow works for the whole team.
    if (willow_free && !working && !strikes && !stunned_turn && !mate_needs_support(world) && willow_medic(world, pathing, safety, memory)) return;
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
        else mend_hit(world, memory);
        mend_step(world, pathing, safety, memory);
        return;
    }
    if (leave) {
        // Our kill bid outranks the retreat, but for tiles the step guard would leave at once.
        if (follow::binding(world) && strike_possible(world)) {
            guard_steps(world, pathing, safety);
            if (keep_bid(world, pathing, safety).attacked) see_stuns(world, safety), safety.refresh();
            pathing.set_guard(nullptr);
        }
        retreat(world, pathing, safety, memory);
        return;
    }

    guard_steps(world, pathing, safety);
    if (join_marcella_capture(world, pathing, safety, memory)) return;
    // Off a sole Prism's hold with an enemy in sight, the strike search still has our attack and casts.
    const bool yielded = on_cleared_group(world) && yield_capture(world, pathing, safety, memory);
    if (yielded && !yielded_in_sight()) return;
    if (yielded) guard_steps(world, pathing, safety);
    if (take_capture_handoff(world, pathing, safety, memory)) return;
    const bool contested = contesting(world);
    const bool holding = holding_capture(world, pathing) || contested;
    const bool attacked = strikes && search_strikes(world, pathing, safety, memory, holding, contested);
    decision = holding ? Branch::hold : attacked ? Branch::attack : decision;
    if (!cambc::self().is_alive() || (yielded && !holding)) return;
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
    if (my_can_move() || my_can_cast()) {
        // Off Monolith-only maps the steps keep out of an awake home Monolith's reach (home_reach_avoid):
        // home sieging keeps it awake, and its fire killed bodies walking out (spawncamp.md round 2).
        // Read once: most maps have no Monolith near our spawn, and their turns pay only this test.
        static const bool near = home_monolith_map(world);
        const bitboard* avoid = near ? home_reach_avoid(world, memory) : nullptr;
        // Nor do they end on a group Prism holds alone: at its payout they would split it.
        if (const bitboard* held = prism_hold_seen(world, false)) {
            static bitboard both{cambc::uninitialized};
            if (avoid) copy_into(*avoid, both), both |= *held, avoid = &both;
            else avoid = held;
        }
        guard_work(world, pathing, safety, memory.damage, avoid);
    }
    // A goal step that cannot finish is not started: it would run the turn out, which loses its posts and
    // next turn's read of this one, for nothing done.
    if (!fuel_ok(goal_least)) {
        note_shortcut("goal-short");
        return;
    }
    if (banks_bag(world, pathing)) {
        carry_bag(world, pathing, safety, memory, attacked, strike_guard);
        return;
    }
    // Banked inside a camp ring: the turn-end recall is the way out (continue_recall keeps it).
    if (sealed_in(world, pathing, my_position())) return;
    if (wake_ring(world, pathing, safety)) return;
    // After the search the goal takes only what the search left and could not price: its walk, camp
    // work, a travel dash (a dash the search plays only before a strike). A ranged attack spent the walk.
    if (my_can_move() && wants_shop(world, pathing, safety, memory)) {
        decision = Branch::shop;
        memory.claim = -1;
        step_safely(world, pathing, pathing.to_ally_spawn(), safety);
        return;
    }
    if (guard_turn(world, pathing, safety, memory, strike_guard)) return;
    if (chase_with_guard(world, pathing, safety, strike_guard)) return;
    if (contest_capture(world, pathing, memory)) {
        decision = Branch::contest;
        return;
    }
    decision = Branch::farm;
    if (!fuel_ok(farm_least)) {
        note_shortcut("goal-short");
        return;
    }
    if ((world.map().shared_gems && kite(world, pathing, memory)) || siege(world, pathing, safety, memory)) {
        decision = Branch::siege;
        return;
    }
    if (willow_follow(world, pathing, safety)) return;
    farm(world, pathing, safety, memory);
    if (on_cleared_group(world)) yield_capture(world, pathing, safety, memory, true);
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
        self_acted(), cambc::self().recall();
        recall_feint = true;
    } catch (const cambc::error&) {
    }
}

} // namespace

void prepare_next_turn(const World& world, Pathing& pathing, const Memory& memory, std::uint64_t fuel_floor) {
    // Next turn's walk, searched from where that turn starts: act() then finds it ready. Not for a
    // recall farm means to keep (recall_farm).
    if (const int g = memory.recall_farm < 0 ? walk_target(world, pathing, memory.farm_group) : -1; g >= 0)
        pathing.prepare_approach(g, walk_range(world, g), fuel_floor);
    // Next turn's farm loop starts from our choice: its order is made here when the fuel is spare,
    // rather than in the loop's turn.
    const auto& map = world.map();
    if (const int g = memory.farm_group; g >= 0 && !map.nearest_groups_ready(g) && fuel_ok(fuel_floor + 100 * map.groups.size() + 3000))
        map.nearest_groups(g);
    // The walk altar_access left unknown, so that the first camp change updates it rather than floods.
    if (altar_walk_pending && fuel_ok(fuel_floor + full_field_cost_estimate())) flood_altar_walk(world, pathing, altar_walk());
}

// Our casts as counted when made (turn_acts), and the basic attacks our state at the turn's end
// implies: each reset restored a spent attack, and a ranged walk spent the attack without one.
void count_use(const World& world, bool could_attack) {
    if (!world.me().alive) return;
    const auto& f = world.me().facts();
    int resets = 0;
    for (int s = 0; s < 2; ++s) {
        use.casts[s] += turn_acts.casts[s];
        if (f.abilities[s].kind == AbilityKind::attack_reset) resets += turn_acts.casts[s];
    }
    const bool walked = !f.walk_and_attack_independent() && turn_acts.walked;
    use.attacks += std::max(0, (could_attack && !my_can_attack()) + resets - walked);
}

// The turn's end after act()'s optional steps on its cheap path (the recall, the stun read, the kept turn
// order, the posts): 0.77k median, 1.0k at p99 (3.7k turns short of fuel, 96 games at the real budget).
// Each optional step's least cost when it does anything (below it, it only looks): 30k such turns.
inline constexpr std::uint64_t turn_end_cost = 1000;
inline constexpr std::uint64_t reveal_least = 1700, strike_least = 1400, cast_least = 350, ward_least = 400, habit_least = 850;
// Above this at the steps' start, the steps that only look (2.1k together at p99) leave the costliest one room: none is checked.
inline constexpr std::uint64_t turn_end_tight = turn_end_cost + reveal_least + 2300;
// Of the turn's end: the kept turn order, the intent and the posts (0.47k median, 0.59k at p99); the recall; the stun read.
inline constexpr std::uint64_t posts_cost = 600, recall_cost = 200, stuns_cost = 200;
// act() found the fuel short of its last steps (turn_end_tight): the turn's end checks its own.
bool end_tight = false;

// The turn's walk, hits and casts, and the free actions that end it.
void act(World& world, Pathing& pathing, Safety& safety, Memory& memory) {
    const vec2 start = world.me().pos;
    const bool could_attack = my_can_attack();
    // The walk to our farm choice is searched out to our tile: from where the turn starts, before
    // anything moves us. The turn end before has usually made it. Not while last turn's recall is
    // undecided: decide may keep it, and the strike search makes the walk only if it reads it (goal_field).
    if (!channelling())
        if (const int g = walk_target(world, pathing, memory.farm_group); g >= 0) pathing.approach(g, walk_range(world, g));
    const int claim = memory.claim;
    decide(world, pathing, safety, memory);
    if (decision != Branch::wait_altar) memory.wait_altar = -1;
    // A turn that takes Prism off its way withdraws the capture it carries (left_for_prism).
    if (world.me().facts().passive == Passive::gem_focus) {
        switch (decision) {
        case Branch::retreat: case Branch::bank: case Branch::wait_altar: case Branch::guard_altar: case Branch::tribute_kept:
        case Branch::recall_kept: case Branch::capture_recall: case Branch::mend: case Branch::shop: case Branch::prism_recovery:
            drop_carry_claim(memory);
            break;
        default: break;
        }
    // Posted, our claim on a cleared group we leave for Prism would keep it out of Prism's farm.
    } else if (world.me().alive && memory.claim >= 0 && memory.claim < static_cast<int>(world.map().groups.size())
             && world.camps[memory.claim].state == CampState::cleared && left_for_prism(world, pathing, memory.claim))
        memory.claim = -1;
    // A turn without siege() (a fight, a heal) keeps the siege while our claim stays on it; a chase
    // or a bag takes us away from it.
    if (!sieged && (memory.claim != claim || decision == Branch::chase || banks_bag(world, pathing))) {
        memory.siege = false;
        memory.staged_since = -1;
    }
    // Nearly out of fuel, a step below runs only if it could act and still leave the turn's end its
    // fuel: else it is idle or runs the turn out, which loses the steps after it, the posts, and the
    // next turn's start (29% of turns that ran out did so here, a third of them from under 2k).
    const bool tight = end_tight = !fuel_ok(turn_end_tight);
    // A skipped step that could have acted (`live`: its cheap tests) is the shortcut.
    bool cut = false;
    const auto room = [&](std::uint64_t least, auto&& live) __attribute__((always_inline)) {
        if (!tight || fuel_ok(turn_end_cost + least)) return true;
        cut = cut || live();
        return false;
    };
    const bool alive = world.me().alive;
    const auto strikes = [&] { return alive && (my_can_attack() || my_can_cast()); };
    if (room(reveal_least, strikes) && alive && see_revealed(world, pathing, safety)) search.chose = false;
    if (!support_owned && room(strike_least, strikes) && strike_after(world, pathing, safety).searched) note_search(true);
    pathing.set_guard(nullptr);
    if constexpr (debug_fights)
        if (world.me().alive && !test(world.map().ally_spawn, start) && fuel_ok(end_reserve + 15000))
            if (const auto t = safety.fight(start); t.enemies > 0) log_fight("FF", world, safety, start, t);
    // Nothing else takes the cast now. The search values a heal at what could hit the ally before
    // the slot is back, so a plan may leave one worth casting.
    if (!support_owned && room(cast_least, [&] { return alive && world.me().facts().heals() && my_can_cast(); }))
        heal_ally(world, safety); // allies in reach after walking
    if (!support_owned && !search_priced_end()
        && room(cast_least, [&] { return alive && world.me().facts().slot_of(AbilityKind::shield) >= 0 && my_can_cast(); }))
        shield_if_needed(world, safety, memory.claim);
    // where we end the turn
    end_ward = room(ward_least, [&] { return alive && !stunned_turn && world.round >= warded_round + static_cast<int>(cambc::constants::ward_cooldown); })
               && place_ward(world, memory);
    if (room(ward_least, [&] { return alive && !stunned_turn && carried_locks() > 0; })) place_lock(world);
    if (!support_owned && room(habit_least, [&] { return alive && !stunned_turn && my_gems() > 0; }))
        mite_tribute_habit(world, pathing, safety, memory);
    // The posts come before the recall: an ally reads our claim and bag, and next turn our health.
    if (!support_owned && (!tight || fuel_ok(posts_cost + recall_cost) || (cut = cut || (alive && !stunned_turn), false))) start_recall(world);
    count_use(world, could_attack);
    if (cut) note_shortcut("turn-end-short");
}

void play_turn(World& world, Pathing& pathing, Memory& memory) {
    Safety safety{world};
    pathing.use_safety(&safety);
    use_hold_safety(&safety);
    struct Unuse {
        Pathing& pathing;
        ~Unuse() { pathing.use_safety(nullptr), use_hold_safety(nullptr); }
    } unuse{pathing};
    const int live_claim = world.me().facts().has_dash() && memory.claim >= 0
                               && memory.claim < static_cast<int>(world.camps.size())
                               && world.camps[memory.claim].state == CampState::alive
                               && world.camps[memory.claim].state_round == world.round
                               ? memory.claim : -1;
    const auto* record = world.me().alive ? &my_record() : nullptr;
    const float health = record ? record->health : 0;
    memory.damage = memory.round == world.round - 1 ? std::max(0.0f, memory.health - health) : 0;
    // Home is reached on our spawn even where camp fire there keeps us below the health we fled at.
    if (!record || health > memory.camp_fled || (memory.camp_fled >= 0 && test(world.map().ally_spawn, world.me().pos))) memory.camp_fled = -1;
    decision = Branch::none;
    debug_block({ print_aim_counts(world); }); // the previous turn's
    sieged = false;
    search.chose = false;
    struck = searched = false;
    support_owned = support_requested = support_offered = support_retreat = end_ward = end_tight = false;
    comms::support_intent(world.round, false);
    siege_group() = -1;
    turn_acts = {};
    engaged_before = memory.round == world.round - 1 ? engaged : 0;
    engaged = 0;
    const int camp_hits_before = camp_hits();
    note_carriers(world);
    if (world.me().alive) note_upkeep(world, safety, memory.damage), note_income_start(world);
    stunned_turn = record && my_stunned(cambc::champion_state::from_bits_retain(record->state));
    // A failed act still posts the claim, the bag and the health that next turn's damage reads; a
    // stale turn abandons the rest. Caught here rather than in main's run(), a StaleTurn costs one
    // personality call and no second unwind (~1k).
    try {
        act(world, pathing, safety, memory);
    } catch (const StaleTurn&) {
        return;
    } catch (const std::exception& e) {
        std::printf("r%u act error: %s\n", cambc::round_number(), e.what());
    }
    try {
        // Only the turn order reads this turn's stuns, and this short it keeps its last rank.
        if (!world.is_stale() && (!end_tight || fuel_ok(posts_cost + stuns_cost))) see_stuns(world, safety);
        chase_role = {decision == Branch::retreat, decision == Branch::chase, engaged};
        set_turn_order(world, safety);
    } catch (const StaleTurn&) {
        return;
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
    comms::chasing(world.round, world.me().alive && decision == Branch::chase);
    if (!world.is_stale()) publish_turn_order(world, comms::priority_payload(world));
    memory.live_claim = live_claim;
    memory.round = world.round;
    memory.health = world.me().alive ? my_health() : 0;
    if (world.me().alive) note_income_end(world);
    upkeep.camp_turns += camp_hits() != camp_hits_before;
    debug_block({ std::printf("D %d %u %c %d %d\n", world.round, static_cast<std::uint32_t>(world.me().handle), static_cast<char>(decision), memory.farm_group, memory.claim); });
}

} // namespace aph
