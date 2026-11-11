#pragma once
#include "path.h"
#include <algorithm>
#include <array>
#include <vector>

// Moving towards a goal: one tile, or a set of tiles (a bitboard), whichever is nearest.
//
//   dashing::init()        once, at the start of the game, after map_info::init() and
//                          move_manager::init()
//   walk_or_dash_to(out, goal)  this turn's best mix of walking and dashing towards `goal`; the
//                               moves go to `out` (actions::act makes them, actions::plan writes
//                               them down)
//   walk_to(out, goal)          the same without dashing this turn; mix the two freely
//
// Distances are measured to the roots: the goal tiles the champion could stand on now (not a wall,
// hole, altar or the enemy spawn, and no other unit on it in view). If there are none, the free
// tiles next to the goal tiles, so a blocked goal is reached by standing next to it, and stepped
// onto once it frees up. Ties go to the tile nearer the goal's centre of mass (up to 50 goal
// tiles; for more, the first one).
//
// A dash is up to 2 steps that may pass over holes, allies and altars but not walls, the enemy
// spawn, or visible enemies, camps and teleport reservations. It lands on a free walkable tile,
// uses the turn's one ability cast and recharges for 8 turns. Walking and dashing are separate
// allowances, so a turn can walk, dash, or both in either order (docs/ours/mechanics.md).
//
// Moves are scored by estimated turns to arrival, with `cooldown` turns left:
//   eta(t, cooldown) = min(walk[t], dash[t] + max(0, cooldown - to_hole[t]))
//   walk[t]     steps to the roots with holes blocked
//   dash[t]     steps with the crossable holes open: a crossing costs 2 steps, as a dash does
//   to_hole[t]  steps to the nearest crossable hole
// eta only chooses between moves; arriving is guaranteed by the plans in walk_or_dash_to.
namespace path {
    namespace dashing {
        constexpr i32 recharge = 8; // turns on cooldown after a dash (docs/ours/champions.md)
        constexpr u16 unreachable = cambc::distance_field::unreachable;

        inline cambc::bitboard over, open_holes, crossable, walkable, walk_at_[13], solid_at_[13],
            crossing, dash_blockers, dash_reach_here, dash_reach_after_step[8];
        inline cambc::distance_field hole_field;
        inline const u16* steps_to_hole = nullptr; // steps to the nearest crossable hole; null if none

        // The 16 pairs of a hole's neighbours that are 2 apart: where a dash over it starts and
        // lands. next: the straight offsets next to both ends; a walkable one makes it a walk of 2.
        // walk3: the walks of 3 between the ends that miss the hole, as the two tiles in between;
        // only diagonal and knight-shaped pairs have any, two each. Every offset has
        // |dx| + |dy| <= 2.
        struct pair_shape {
            vec2 p, q, next[2], walk3[2][2];
            i32 nexts, walks;
        };
        constexpr std::array<pair_shape, 16> pair_shapes = [] {
            auto cheb = [](vec2 a, vec2 b) {
                const i32 dx = a.x - b.x, dy = a.y - b.y;
                return std::max(dx < 0 ? -dx : dx, dy < 0 ? -dy : dy);
            };
            std::array<pair_shape, 16> shapes{};
            i32 n = 0;
            for (i32 i = 0; i < 8; ++i)
                for (i32 j = i + 1; j < 8; ++j) {
                    const vec2 p = DIRS[i], q = DIRS[j];
                    if (cheb(p, q) != 2)
                        continue;
                    pair_shape& s = shapes[n++];
                    s.p = p, s.q = q;
                    auto next_to_both = [&](vec2 c) { return cheb(c, p) == 1 && cheb(c, q) == 1; }; // the hole too
                    for (vec2 d : DIRS)
                        if (const vec2 c{p.x + d.x, p.y + d.y}; (c.x || c.y) && next_to_both(c))
                            s.next[s.nexts++] = c;
                    for (vec2 dc : DIRS)
                        for (vec2 dd : DIRS)
                            if (const vec2 c{p.x + dc.x, p.y + dc.y}, d{q.x + dd.x, q.y + dd.y};
                                !next_to_both(c) && !next_to_both(d) && cheb(c, d) == 1)
                                s.walk3[s.walks][0] = c, s.walk3[s.walks][1] = d, ++s.walks;
                }
            return shapes;
        }();

        // If this champion has a dash, builds `open_holes`: `fixed` with the holes and altars a
        // dash crosses opened (`over`: a dash passes over both and lands on neither; "hole" below
        // means either). A dash crosses hole h between two walkable neighbours of h that are 2
        // apart (pair_shapes). h is opened when walking between such a pair takes 4 steps or more,
        // so a path through h costs the dash's 2. Smaller savings (corner cuts) are left to the
        // planner's look 3 tiles around: opening those holes would let the field step from one
        // opened hole to the next, which no dash can (docs/ours/compute.md). About 200 board calls
        // on any map, and one field to the opened holes.
        inline void init() {
            using namespace cambc;
            if (!move_manager::dash_ability)
                return;
            bb::or_into(map_info::holes, map_info::altars, over);
            bb::copy_into(fixed, open_holes);
            crossable.clear();
            if (!over.is_empty()) {
                // walk_at(o): the tiles t whose t + o is walkable, for the 8 neighbours and the 4
                // straight offsets 2 away. solid_at(o): those whose t + o is not, off the map
                // included, for the 8 straight offsets.
                // the 13 offsets with |dx| + |dy| <= 2, row by row
                auto at = [](vec2 o) { constexpr i32 row[5] = {0, 2, 6, 10, 12}; return row[o.y + 2] + o.x; };
                auto walk_at = [&](vec2 o) -> bitboard& { return walk_at_[at(o)]; };
                auto solid_at = [&](vec2 o) -> bitboard& { return solid_at_[at(o)]; };
                constexpr vec2 straight[8] = {{1, 0}, {-1, 0}, {0, 1}, {0, -1}, {2, 0}, {-2, 0}, {0, 2}, {0, -2}};
                bb::not_into(fixed, walkable);
                for (i32 dx = -2; dx <= 2; ++dx) {
                    bitboard& column = dx ? walk_at({dx, 0}) : walkable; // shifted across once
                    if (dx)
                        walkable.shift_right_into(-dx, column);
                    for (i32 dy = -2; dy <= 2; ++dy)
                        if (dy && std::abs(dx) + std::abs(dy) <= 2)
                            column.shift_up_into(-dy, walk_at({dx, dy}));
                }
                for (vec2 o : straight)
                    bb::not_into(walk_at(o), solid_at(o));
                for (const pair_shape& shape : pair_shapes) {
                    // The holes h with both ends walkable and nothing else next to both,
                    bb::and_into(over, walk_at(shape.p), crossing), crossing &= walk_at(shape.q);
                    for (i32 k = 0; k < shape.nexts; ++k)
                        crossing &= solid_at(shape.next[k]);
                    // and no walk of 3 between them.
                    for (i32 k = 0; k < shape.walks; ++k)
                        bb::and_into(walk_at(shape.walk3[k][0]), walk_at(shape.walk3[k][1]), scratch), scratch &= crossing,
                            crossing ^= scratch;
                    crossable |= crossing;
                }
            }
            if (!crossable.is_empty()) {
                open_holes ^= crossable; // crossable holes are in `fixed`, so this opens them
                hole_field.compute(open_holes, crossable, visited, recharge);
                steps_to_hole = values(hole_field);
            }
        }

        // Distance fields to one set of roots, read in place with cell(). A field holds the exact
        // distance of every tile nearer the roots than its limit; farther tiles read unreachable
        // or exact. walk == dash when one search served both.
        struct route {
            cambc::bitboard roots;
            vec2 tile{-1, -1}; // the one root, when there is one: then routes match by it
            cambc::distance_field walk_field, dash_field;
            const u16 *walk = nullptr, *dash = nullptr;
            u32 walk_limit = 0, dash_limit = 0, used = 0;
        };
        inline route routes[6]; // the roots asked for last
        inline u32 clock = 0;

        // Searches out from `roots` over tiles not in `walls` and stops once the champion's tile
        // (cell `here`) is reached: a search costs a layer per step (docs/ours/compute.md), so this
        // pays for the steps to the champion, not to the far end of the map. Returns the limit.
        inline u32 search_to_champion(cambc::distance_field& f, const cambc::bitboard& walls,
                                      const cambc::bitboard& roots, i32 here) {
            stop_at.clear(), stop_at.set(g::my_pos);
            f.compute_to(walls, roots, stop_at, visited);
            const u16 d = values(f)[here];
            return d == unreachable ? 1u << 16 : d + 1u;
        }

        // The same out to `depth` steps, wherever the champion is.
        inline u32 search_upto(cambc::distance_field& f, const cambc::bitboard& walls,
                               const cambc::bitboard& roots, u16 depth) {
            return f.compute_with_expansion_count(walls, roots, visited, depth) < depth ? 1u << 16 : depth + 1u;
        }

        // Makes r.walk, and with `dashing` r.dash, exact out to the champion (cell `here`). The
        // dash field is searched first; if that search got to the champion without touching an
        // opened hole, it found what walking would and is the walking field too. Otherwise the
        // walking field only matters where walking can beat the dash route: up to the longest wait
        // for the dash and one turn's move past the champion's dash distance, which stays enough
        // as the dash distance falls.
        inline void fields_for(route& r, i32 here, bool dashing) {
            auto exact = [here](const u16* f, u32 limit) { return f && f[here] < limit; };
            if (dashing && steps_to_hole) {
                if (!exact(r.dash, r.dash_limit)) {
                    if (r.walk == r.dash)
                        r.walk = nullptr;
                    r.dash_limit = search_to_champion(r.dash_field, open_holes, r.roots, here);
                    r.dash = values(r.dash_field);
                    bb::and_into(visited, crossable, scratch);
                    if (scratch.is_empty() && !exact(r.walk, r.walk_limit))
                        r.walk = r.dash, r.walk_limit = r.dash_limit;
                }
                if (r.dash[here] == unreachable) { // no way there at all, walking included
                    r.walk = r.dash, r.walk_limit = r.dash_limit;
                    return;
                }
                const u32 depth = r.dash[here] + recharge + 3u;
                if (!exact(r.walk, r.walk_limit) && !(r.walk && r.walk_limit > depth))
                    r.walk_limit = search_upto(r.walk_field, fixed, r.roots, u16(std::min<u32>(depth, unreachable - 1))),
                    r.walk = values(r.walk_field);
                return;
            }
            if (!exact(r.walk, r.walk_limit))
                r.walk_limit = search_to_champion(r.walk_field, fixed, r.roots, here), r.walk = values(r.walk_field);
            if (!steps_to_hole)
                r.dash = r.walk, r.dash_limit = r.walk_limit;
        }

        // Estimated turns from tile `index` (cell()) to the roots with `cooldown` turns left.
        inline i32 eta(const u16* walk, const u16* dash, i32 index, i32 cooldown) {
            i32 best = walk[index]; // 65535 when unreachable: very far
            if (dash != walk && dash[index] != unreachable)
                best = std::min(best, dash[index] + std::max(0, cooldown - i32(steps_to_hole[index])));
            return best;
        }

        // Walkable with no unit in view: a tile we could walk or dash onto now.
        inline bool vacant(vec2 tile) {
            return polyfill::is_in_bounds(tile) && !polyfill::is_set(fixed, tile) &&
                   !polyfill::has_champion(tile) && !polyfill::has_camp(tile) &&
                   !polyfill::has_teleport(tile);
        }

        inline cambc::bitboard spread;

        // `b` and every tile next to it, into `out` (not scratch or spread).
        inline void grow_into(const cambc::bitboard& b, cambc::bitboard& out) {
            b.shift_right_into(1, scratch), bb::or_into(b, scratch, out);
            b.shift_right_into(-1, scratch), out |= scratch;
            out.shift_up_into(1, scratch), out.shift_up_into(-1, spread), out |= scratch, out |= spread;
        }

        // The goal, the plan for it (see walk_or_dash_to), and where it stands.
        enum class plan : u8 { dash, walk, levels };
        inline cambc::bitboard plan_goals, occupied, roots_now;
        inline vec2 plan_tile{-1, -1};  // the goal tile, when the goal came as one tile
        inline vec2 root_tile{-1, -1};  // roots_now's one tile, when it is that goal tile
        inline vec2 aim{-1, -1};        // ties go nearer it (aim_for)
        inline vec2 settled_at{-1, -1}; // where the last turn found the champion there, or no way
        inline bool beside_unit = false; // units, not only fixed ground, put the roots beside the goal
        inline route* current = nullptr;
        inline plan mode = plan::dash;
        inline i32 stuck_turns = 0, held_turns = 0;

        // Whether one could stand on `tile` now: not fixed, and no unit on it in view but us.
        inline bool standable(vec2 tile) {
            return !polyfill::is_set(fixed, tile) &&
                   (tile == g::my_pos || (!polyfill::has_champion(tile) && !polyfill::has_camp(tile) &&
                                          !polyfill::has_teleport(tile)));
        }

        // roots_now for the goal tile `goal`: itself if one could stand on it, else the free tiles
        // next to it. A few lookups, where a goal set needs board calls.
        inline void roots_for_tile(vec2 goal) {
            using namespace cambc;
            roots_now.clear(), root_tile = {-1, -1}, beside_unit = false;
            if (standable(goal)) {
                roots_now.set(goal), root_tile = goal;
                return;
            }
            beside_unit = !fixed.is_set(goal);
            for (vec2 direction : DIRS)
                if (const vec2 beside = goal + direction; polyfill::is_in_bounds(beside) && standable(beside))
                    roots_now.set(beside);
        }

        // roots_now for `goals`: the goal tiles not fixed and with no unit in view but us; if none,
        // the free tiles next to them.
        inline void roots_for_set(const cambc::bitboard& goals) {
            using namespace cambc;
            vision::champion_tiles_into(team::ally, occupied), occupied |= fixed;
            vision::champion_tiles_into(team::enemy, scratch), occupied |= scratch;
            vision::camp_tiles_into(scratch), occupied |= scratch;
            vision::teleport_tiles_into(scratch), occupied |= scratch;
            occupied.set(g::my_pos, false);
            bb::and_into(goals, occupied, scratch), bb::xor_into(goals, scratch, roots_now);
            root_tile = {-1, -1}, beside_unit = false;
            if (!roots_now.is_empty())
                return;
            bb::and_into(goals, fixed, blocked);
            beside_unit = !(blocked == goals);
            grow_into(goals, roots_now);
            bb::and_into(roots_now, occupied, scratch), roots_now ^= scratch;
        }

        // `current` for roots_now: the cached route with these roots, or the least recently used
        // one, emptied for them.
        inline void take_route() {
            route* pick = &routes[0];
            for (route& r : routes) {
                if (r.walk && (root_tile.x >= 0 ? r.tile == root_tile : r.tile.x < 0 && r.roots == roots_now)) {
                    current = &r, r.used = ++clock;
                    return;
                }
                if (r.used < pick->used)
                    pick = &r;
            }
            bb::copy_into(roots_now, pick->roots), pick->tile = root_tile;
            pick->walk = pick->dash = nullptr, pick->walk_limit = pick->dash_limit = 0, pick->used = ++clock;
            current = pick;
        }

        // Where ties lean for `tiles`: the centre of mass of up to 50 tiles (listed, about 20 fuel
        // each), else the first tile, found in the board's words: one per 8x8 chunk, a tile at bit
        // (y % 8) * 8 + x % 8 (docs/ours/compute.md).
        inline vec2 aim_for(const cambc::bitboard& tiles) {
            const i64 n = tiles.count();
            if (n == 0)
                return g::my_pos;
            if (n <= 50) {
                i64 x = 0, y = 0;
                for (const vec2 tile : tiles.positions())
                    x += tile.x, y += tile.y;
                return {i32((x + n / 2) / n), i32((y + n / 2) / n)};
            }
            const cambc::detail::metadata& layout = cambc::detail::layout();
            const u64* words = tiles.ptr();
            for (u32 cy = 0; cy < layout.chunked_height; ++cy)
                for (u32 cx = 0; cx < layout.chunked_width; ++cx)
                    if (const u64 w = words[cy * layout.chunk_stride + cx]) {
                        const i32 bit = __builtin_ctzll(w);
                        return {i32(cx * 8 + (bit & 7)), i32(cy * 8 + (bit >> 3))};
                    }
            return g::my_pos;
        }

        // A new goal, its roots found: its route and a fresh plan.
        inline void start_plan() {
            take_route();
            mode = move_manager::dash_ability ? plan::dash : plan::walk;
            stuck_turns = held_turns = 0, settled_at = {-1, -1};
        }

        // The levels plan's map for the current roots. Level j: the tiles that need j dashes to get
        // there, walking in between; any hole or altar can be dashed over. A launch tile is one from
        // which a dash reaches the level below (on level 0, a root). to_launch: steps from each tile
        // to the nearest launch tile, always on its own level, since walking never changes level.
        // One flood per level.
        inline std::vector<cambc::bitboard> level_tiles; // [j]: the tiles j dashes from the roots
        inline cambc::distance_field launch_field;
        inline const u16* to_launch = nullptr;
        inline cambc::bitboard levels_roots, reached, grown, landing, launches;

        inline void build_levels() {
            using namespace cambc;
            bb::copy_into(current->roots, levels_roots);
            level_tiles.clear();
            bb::copy_into(levels_roots, landing), bb::copy_into(levels_roots, launches);
            reached.clear();
            while (!landing.is_empty()) {
                bb::or_into(fixed, reached, blocked);
                field.compute(blocked, landing, visited); // the level: walkable from its landings
                level_tiles.push_back(visited);
                reached |= visited;
                // The next level's launch tiles: ground not yet reached, next to a hole or altar
                // that is next to this level.
                grow_into(visited, grown), grown &= over;
                grow_into(grown, landing);
                bb::or_into(fixed, reached, blocked);
                bb::and_into(landing, blocked, scratch), landing ^= scratch;
                launches |= landing;
            }
            launch_field.compute(fixed, launches, visited);
            to_launch = values(launch_field);
        }

        // Units in the way of every move that lowers walk[]: a step round them, along a search in
        // which the units in view are walls.
        template <class Out>
        bool detour(Out& out, vec2 from, i32 here) {
            using namespace cambc;
            vision::champion_tiles_into(team::ally, blocked), blocked |= fixed;
            vision::champion_tiles_into(team::enemy, scratch), blocked |= scratch;
            vision::camp_tiles_into(scratch), blocked |= scratch;
            vision::teleport_tiles_into(scratch), blocked |= scratch;
            blocked.set(from, false);
            stop_at.clear(), stop_at.set(from);
            field.compute_to(blocked, current->roots, stop_at, visited);
            const u16* steps = values(field);
            const u16 steps_here = steps[here];
            return steps_here != unreachable &&
                   step_nearest(
                       out, from, aim,
                       [&](vec2 next) {
                           return polyfill::is_in_bounds(next) && !blocked.is_set(next) && steps[cell(next)] < steps_here;
                       },
                       [](vec2) { return true; });
        }

        // One turn of walk_or_dash_to. fresh: a goal other than the last one, already started.
        template <class Out>
        bool turn_towards(Out& out, bool fresh, bool may_dash) {
            using namespace cambc;
            const vec2 from = g::my_pos;
            if (!fresh && from == settled_at && !beside_unit)
                return false; // as last turn: there already, or no way there
            const bool has_dash = move_manager::dash_ability.has_value();
            const champion_state state = channel::state();
            const bool can_walk = state.contains(champion_state::can_move);
            const bool can_cast = state.contains(champion_state::can_cast);
            const i32 cooldown = has_dash ? i32(move_manager::dash_ability->cooldown()) : recharge;
            const bool can_dash = has_dash && may_dash && cooldown == 0 && can_cast;
            const i32 here = cell(from);
            if (const u16* near = mode == plan::walk ? current->walk : current->dash;
                !fresh && (beside_unit || (near && near[here] <= 3))) {
                // Within a turn of the roots, or beside units: who stands on the goal now?
                if (plan_tile.x >= 0) {
                    if (standable(plan_tile) != (current->tile == plan_tile))
                        roots_for_tile(plan_tile), take_route(), settled_at = {-1, -1};
                } else if (roots_for_set(plan_goals), !(roots_now == current->roots))
                    take_route(), settled_at = {-1, -1};
            }

            // The fields a plan reads: walk reads only walk[], levels neither. The walking distance
            // itself, when a decision needs it: walk[] may reach only as far as walking could beat
            // the dash route.
            const u16 *walk = nullptr, *dash = nullptr;
            auto walking_here = [&] { return fields_for(*current, here, false), current->walk[here]; };
            const bool walk_from_start = fresh && !(has_dash && may_dash) && walking_here() != unreachable;
            if (walk_from_start)
                mode = plan::walk;
            if (fresh || mode != plan::levels) {
                const bool dashing = has_dash && !walk_from_start && (fresh || mode == plan::dash);
                fields_for(*current, here, dashing);
                walk = current->walk, dash = dashing ? current->dash : walk;
                const i32 eta_here = eta(walk, dash, here, cooldown);
                if (eta_here == 0 || eta_here == unreachable)
                    return settled_at = from, false; // there, or no way there at all
                if (fresh && !walk_from_start)
                    mode = walk[here] <= eta_here ? plan::walk : plan::dash;
                if (mode == plan::dash && eta_here == walk[here])
                    mode = plan::walk;
            }

            // vacant(tile) for tiles within 3 of us, looked up once each; -1: not yet.
            i8 vacancy[7][7];
            std::fill(&vacancy[0][0], &vacancy[0][0] + 49, i8(-1));
            auto is_vacant = [&](vec2 tile) {
                i8& known = vacancy[tile.y - from.y + 3][tile.x - from.x + 3];
                if (known < 0)
                    known = vacant(tile);
                return known == 1;
            };

            // Where a dash can get to: 2 steps around walls, the enemy spawn, and the visible
            // enemies, camps and teleport reservations; holes, altars and allies do not block it.
            auto add_seen_units = [] {
                vision::champion_tiles_into(team::enemy, scratch), dash_blockers |= scratch;
                vision::camp_tiles_into(scratch), dash_blockers |= scratch;
                vision::teleport_tiles_into(scratch), dash_blockers |= scratch;
            };
            bool reach_ready = false;
            auto reach_from_here = [&]() -> const bitboard& {
                if (!reach_ready) {
                    bb::or_into(map_info::walls, map_info::enemy_spawn, dash_blockers);
                    add_seen_units();
                    dash_blockers.reachable_tiles_into(from, 2, dash_reach_here);
                    reach_ready = true;
                }
                return dash_reach_here;
            };

            // Takes the best move whose end tile `lowers` accepts, by score(cell, dashed): the
            // plan's measure after the move, lower first, a walk before a dash on a tie, then nearer
            // `aim` (both get the end tile's cell()). wait_score >= 0 adds standing still, which
            // loses ties with walking. Moves that units or allowances rule out are skipped.
            enum class turn : u8 { moved, waits, nothing };
            auto take_best = [&](auto lowers, auto score, i32 wait_score, bool dashes) -> turn {
                struct option {
                    vec2 tile;
                    i64 key;
                    bool dashed;
                };
                option options[57];
                i32 count = 0;
                auto key = [&](vec2 tile, i32 at, bool dashed) {
                    return i64(score(at, dashed)) << 21 | i64(dashed) << 20 | (aim - tile).length_squared();
                };
                if (wait_score >= 0)
                    options[count++] = {from, i64(wait_score) << 21 | 0xfffff, false};
                if (can_walk)
                    for (vec2 direction : DIRS)
                        if (const vec2 next = from + direction; polyfill::is_in_bounds(next))
                            if (const i32 at = cell(next); lowers(at))
                                options[count++] = {next, key(next, at, false), false};
                if (can_dash && dashes)
                    for (i32 dy = -3; dy <= 3; ++dy)
                        for (i32 dx = -3; dx <= 3; ++dx)
                            if (const vec2 end{from.x + dx, from.y + dy}; (dx || dy) && polyfill::is_in_bounds(end))
                                if (const i32 at = cell(end); lowers(at))
                                    options[count++] = {end, key(end, at, true), true};
                u32 after_step_ready = 0; // bit k: dash_reach_after_step[k] holds a dash from from + DIRS[k]
                while (count > 0) {
                    i32 best = 0;
                    for (i32 i = 1; i < count; ++i)
                        if (options[i].key < options[best].key)
                            best = i;
                    const option o = options[best];
                    options[best] = options[--count];
                    const vec2 end = o.tile;
                    if (end == from)
                        return turn::waits;
                    if (!is_vacant(end))
                        continue;
                    if (!o.dashed)
                        return out.walk(end) ? turn::moved : turn::nothing;
                    // Dash straight there.
                    if (end.chebyshev_distance(from) <= 2 && reach_from_here().is_set(end))
                        return out.dash(end) ? turn::moved : turn::nothing;
                    if (!can_walk)
                        continue;
                    // Dash, then walk the last step if the landing showed nobody on it (vacant(),
                    // not the cache: a landing in a bush sees who else is in it).
                    for (vec2 direction : DIRS)
                        if (const vec2 landing = end + direction;
                            landing.chebyshev_distance(from) <= 2 && polyfill::is_in_bounds(landing) &&
                            reach_from_here().is_set(landing) && is_vacant(landing)) {
                            if (!out.dash(landing))
                                return turn::nothing;
                            if (vacant(end))
                                out.walk(end);
                            return turn::moved;
                        }
                    // Walk, then dash.
                    for (i32 k = 0; k < 8; ++k) {
                        const vec2 step = from + DIRS[k];
                        if (step.chebyshev_distance(end) > 2 || !is_vacant(step))
                            continue;
                        reach_from_here(); // dash_blockers
                        if (!(after_step_ready >> k & 1))
                            dash_blockers.reachable_tiles_into(step, 2, dash_reach_after_step[k]),
                                after_step_ready |= 1u << k;
                        if (dash_reach_after_step[k].is_set(end)) {
                            if (!out.walk(step))
                                return turn::nothing;
                            // The step can show units the plan did not see (in a bush, round a
                            // wall): plan the dash again from what is seen now.
                            add_seen_units();
                            dash_blockers.reachable_tiles_into(step, 2, dash_reach_here);
                            if (dash_reach_here.is_set(end) && vacant(end))
                                out.dash(end);
                            return turn::moved;
                        }
                    }
                }
                return turn::nothing;
            };

            if (mode == plan::dash) {
                const turn result = take_best(
                    [&](i32 at) { return dash[at] < dash[here]; },
                    [&](i32 at, bool dashed) {
                        return eta(walk, dash, at, dashed ? recharge : std::max(0, cooldown - 1));
                    },
                    cooldown > 0 ? eta(walk, dash, here, cooldown - 1) : -1, true);
                if (result == turn::moved)
                    return stuck_turns = held_turns = 0, true;
                if (result == turn::nothing && can_walk && can_cast) {
                    if (may_dash) {
                        if (++stuck_turns >= 2)
                            mode = walking_here() != unreachable ? plan::walk : plan::levels;
                    } else if (++held_turns >= recharge && walking_here() != unreachable)
                        mode = plan::walk; // the dash keeps being held back where only it would do
                }
                return false;
            }
            if (mode == plan::walk) {
                const turn result = take_best([&](i32 at) { return walk[at] < walk[here]; },
                                              [&](i32 at, bool) { return i32(walk[at]); }, -1, true);
                if (result != turn::nothing)
                    return result == turn::moved;
                return can_walk && detour(out, from, here);
            }

            // Levels: walk to this level's nearest launch tile, then dash down a level.
            if (!(levels_roots == current->roots))
                build_levels();
            i32 level = -1;
            for (i32 j = 0; j < i32(level_tiles.size()) && level < 0; ++j)
                if (level_tiles[j].is_set(from))
                    level = j;
            if (level < 0)
                return settled_at = from, false; // no way there at all
            if (const u16 left = to_launch[here]; left > 0)
                return take_best([&](i32 at) { return to_launch[at] < left; },
                                 [&](i32 at, bool) { return i32(to_launch[at]); }, -1, false) == turn::moved;
            if (level == 0 || !can_dash)
                return false; // on a root, or waiting for the dash
            vec2 best_landing = from;
            for (i32 dy = -2; dy <= 2; ++dy)
                for (i32 dx = -2; dx <= 2; ++dx)
                    if (const vec2 end{from.x + dx, from.y + dy};
                        polyfill::is_in_bounds(end) && level_tiles[level - 1].is_set(end) && reach_from_here().is_set(end) &&
                        is_vacant(end) && (best_landing == from || to_launch[cell(end)] < to_launch[cell(best_landing)]))
                        best_landing = end;
            return best_landing != from && out.dash(best_landing);
        }
    } // namespace dashing

    // This turn's move towards `goals` (see the top of this file for what counts as there): a
    // walk, a dash, or both in either order, scored by eta. True if the champion moved.
    // may_dash false keeps the dash, and the turn's one ability cast, for something else
    // (walk_to); the plan stays the same, so mixing the two calls never sends the champion back
    // and forth. A champion without a dash walks.
    //
    // A reachable goal is always reached (with no units in the way): each goal gets a plan, and
    // every plan has a measure that falls each turn, or the champion waits a bounded time.
    //   dash    dash[] falls, or the dash is recharging and the champion may wait for it. eta
    //           chooses among those moves.
    //   walk    walk[] falls; a dash is taken only if it lands lower.
    //   levels  the fallback (build_levels): the level falls, or the steps to a launch tile do,
    //           or the champion waits at a launch tile for the dash.
    // A goal starts on walk if eta says walking is as quick, or if it is first asked for without
    // the dash and walking gets there; else on dash. Dash turns into walk when walking becomes as
    // quick, or after `recharge` turns in a row in which only a held-back dash would have moved
    // the champion; into walk or levels after two turns in which nothing lowers dash[] (opened
    // holes that touch can make the field promise a way that no move takes). No plan comes back,
    // so the champion arrives within about 9 turns per step of dash[] at the start plus the steps
    // of the plan it ends on; held-back dashes add their turns, and a goal only a dash reaches
    // waits for one.
    template <class Out>
    bool walk_or_dash_to(Out& out, const cambc::bitboard& goals, bool may_dash = true) {
        using namespace dashing;
        const bool fresh = !current || plan_tile.x >= 0 || !(goals == plan_goals);
        if (fresh) {
            bb::copy_into(goals, plan_goals), plan_tile = {-1, -1}, aim = aim_for(goals);
            roots_for_set(goals), start_plan();
        }
        return turn_towards(out, fresh, may_dash);
    }
    template <class Out>
    bool walk_or_dash_to(Out& out, vec2 target, bool may_dash = true) {
        using namespace dashing;
        const bool fresh = !current || target != plan_tile;
        if (fresh)
            plan_tile = aim = target, roots_for_tile(target), start_plan();
        return turn_towards(out, fresh, may_dash);
    }

    // One turn towards the goal without dashing: walk_or_dash_to with the dash held back.
    template <class Out>
    bool walk_to(Out& out, const cambc::bitboard& goals) {
        return walk_or_dash_to(out, goals, false);
    }
    template <class Out>
    bool walk_to(Out& out, vec2 target) {
        return walk_or_dash_to(out, target, false);
    }
} // namespace path
