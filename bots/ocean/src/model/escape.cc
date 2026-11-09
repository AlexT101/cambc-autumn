#include "escape.h"
#include <algorithm>
#include <bit>
#include <cstdlib>
#include <cstring>
#include <utility>
#ifdef __wasm_simd128__
#include <wasm_simd128.h>
#endif
#include "enemy_reach.h"
#include "pathing.h"
#include "safety.h"
#include "world.h"

namespace aph {

namespace escape {

namespace {

// Lanes hold side bits; the second vector's lanes from row `side` on are past the window.
constexpr std::uint16_t lane = (1u << side) - 1;
constexpr std::uint16_t lane_of(int y) { return y < side ? lane : std::uint16_t{0}; }
constexpr Lanes full{lane, lane, lane, lane, lane, lane, lane, lane};
constexpr Lanes last{lane_of(8), lane_of(9), lane_of(10), lane_of(11), lane_of(12), lane_of(13), lane_of(14), lane_of(15)};
constexpr Lanes zero{};

[[gnu::always_inline]] inline std::uint32_t get(const Rows& a, int y) { return a.v[y >> 3][y & 7]; }
[[gnu::always_inline]] inline void put(Rows& a, int y, std::uint32_t bits) { a.v[y >> 3][y & 7] |= static_cast<std::uint16_t>(bits); }

[[gnu::always_inline]] inline Rows operator&(const Rows& a, const Rows& b) { return {{a.v[0] & b.v[0], a.v[1] & b.v[1]}}; }
[[gnu::always_inline]] inline Rows operator|(const Rows& a, const Rows& b) { return {{a.v[0] | b.v[0], a.v[1] | b.v[1]}}; }
[[gnu::always_inline]] inline Rows operator~(const Rows& a) { return {{~a.v[0] & full, ~a.v[1] & last}}; } // within the rows
[[gnu::always_inline]] inline void operator&=(Rows& a, const Rows& b) { a = a & b; }
[[gnu::always_inline]] inline void operator|=(Rows& a, const Rows& b) { a = a | b; }
[[gnu::always_inline]] inline bool none_set(const Rows& a) {
    const Lanes v = a.v[0] | a.v[1];
#ifdef __wasm_simd128__
    return !wasm_v128_any_true(reinterpret_cast<v128_t>(v));
#else
    std::uint16_t o = 0;
    for (int i = 0; i < 8; ++i) o |= v[i];
    return o == 0;
#endif
}

// Rows' neighbours S above and S below or'd in, unmasked: a lane shuffle across the two vectors.
template <int S, int... I>
[[gnu::always_inline]] inline Rows spread_by(const Rows& h, std::integer_sequence<int, I...>) {
    const Lanes a = h.v[0], b = h.v[1];
    const Lanes up0 = __builtin_shufflevector(zero, a, (8 - S + I)...), up1 = __builtin_shufflevector(a, b, (8 - S + I)...);
    const Lanes down0 = __builtin_shufflevector(a, b, (S + I)...), down1 = __builtin_shufflevector(b, zero, (S + I)...);
    return {{a | up0 | down0, b | up1 | down1}};
}
template <int S> [[gnu::always_inline]] inline Rows spread_by(const Rows& h) { return spread_by<S>(h, std::make_integer_sequence<int, 8>{}); }
[[gnu::always_inline]] inline Rows spread_raw(const Rows& h) { return spread_by<1>(h); }

[[gnu::always_inline]] inline Rows sideways(const Rows& h, int s) {
    return {{h.v[0] | h.v[0] << s | h.v[0] >> s, h.v[1] | h.v[1] << s | h.v[1] >> s}};
}

// Within 1, staying included. Bits pushed past a row's side (or into the row past the window) only
// reach tiles the dilation covers anyway, so one mask at the end clears them all.
[[gnu::always_inline]] inline Rows grow(const Rows& a) {
    const Rows o = spread_raw(sideways(a, 1));
    return {{o.v[0] & full, o.v[1] & last}};
}

// Within r >= 1 of a set, from `h`, the tiles within 1 of it (as grow gives them, or unmasked): by
// doubling, steps of 1, 2, then what is left.
[[gnu::noinline]] Rows widen(Rows h, int r) {
    if (r >= 3) h = spread_by<2>(sideways(h, 2));
    else if (r == 2) h = spread_by<1>(sideways(h, 1));
    switch (r) {
    case 4: h = spread_by<1>(sideways(h, 1)); break;
    case 5: h = spread_by<2>(sideways(h, 2)); break;
    case 6: h = spread_by<3>(sideways(h, 3)); break;
    case 7: h = spread_by<4>(sideways(h, 4)); break;
    default: break;
    }
    for (int c = 7; c < r; ++c) h = spread_raw(sideways(h, 1));
    return {{h.v[0] & full, h.v[1] & last}};
}
inline Rows grow_by(const Rows& a, int r) { return r <= 0 ? a : widen(spread_raw(sideways(a, 1)), r); }

// A board's tiles packed a bit each in row-major order (export_linear_buffer), read a window row at a time.
struct Packed {
    std::array<std::uint8_t, 100 * 100 / 8 + 8> bytes;
};

struct Statics {
    bool tried = false, ok = false;
    int width = 0, height = 0;
    // Tiles off the map read as closed: walking and landing are on `passable` and dash paths on
    // `unwalled`, each off the other team's spawn, read only where the window meets that spawn's box.
    Packed passable, unwalled, bushes, ally_spawn, enemy_spawn;
    GrowBox ally_box, enemy_box;
};
Statics statics;
Packed camps_packed, scratch_packed;
std::uint32_t camps_flips = ~0u;
// Our home fields are on static walls (Pathing::to_ally_spawn), one for dashers and one not: each
// exported once a game.
std::array<std::uint16_t, 100 * 100 + 16> home_steps[2]; // padded for 16-column reads
bool home_ready[2] = {false, false};

bool export_board(const bitboard& b, Packed& out) {
    const std::size_t size = bitboard::linear_buffer_size();
    if (size + 8 > out.bytes.size()) return false;
    try {
        b.export_linear_buffer({out.bytes.data(), size});
    } catch (const cambc::error&) {
        return false;
    }
    return true;
}

bool bit(const Packed& p, int i) { return p.bytes[static_cast<std::size_t>(i >> 3)] >> (i & 7) & 1; }

// Where the window lies in the packed boards: its rows y0..y1-1 are on the map, and bit k of such a row
// y is the tile (origin.x + k, origin.y + y), bit `first` + (y - y0) * width of a board for k >= lo.
struct Span {
    int y0 = 0, y1 = 0, first = 0, lo = 0;
    std::uint64_t mask = 0; // the row's tiles on the map, from lo
};
Span span_of(vec2 origin) {
    Span s;
    const int lo = std::max(0, -origin.x), hi = std::min(side, statics.width - origin.x);
    s.y0 = std::max(0, -origin.y), s.y1 = std::max(s.y0, std::min(side, statics.height - origin.y));
    if (lo >= hi) s.y1 = s.y0;
    else s.lo = lo, s.mask = (std::uint64_t{1} << (hi - lo)) - 1, s.first = origin.x + lo + (origin.y + s.y0) * statics.width;
    return s;
}
// The window's rows y0..y1-1 of each board, the rest 0: boards read together share the row arithmetic.
template <std::size_t N>
[[gnu::always_inline]] inline std::array<Rows, N> rows_of(const std::array<const Packed*, N>& p, const Span& at, int y0 = 0, int y1 = side) {
    alignas(16) std::uint16_t t[N][16] = {};
    const int from = std::max(y0, at.y0), to = std::min(y1, at.y1);
    for (int y = from, i = at.first + (from - at.y0) * statics.width; y < to; ++y, i += statics.width) {
        const auto byte = static_cast<std::size_t>(i >> 3);
        for (std::size_t b = 0; b < N; ++b) {
            std::uint64_t word;
            std::memcpy(&word, &p[b]->bytes[byte], sizeof word);
            t[b][y] = static_cast<std::uint16_t>(((word >> (i & 7)) & at.mask) << at.lo);
        }
    }
    std::array<Rows, N> r;
    std::memcpy(&r, t, sizeof r);
    return r;
}
[[gnu::always_inline]] inline Rows rows_of(const Packed& p, const Span& at, int y0 = 0, int y1 = side) {
    return rows_of<1>({&p}, at, y0, y1)[0];
}

// The static boards, once a game; the bit order is checked on a set tile, as Safety's terrain is.
bool ready_statics(const World& world) {
    if (statics.tried) return statics.ok;
    statics.tried = true;
    const auto& map = world.map();
    statics.width = map.width, statics.height = map.height;
    if (statics.width * statics.height + 16 > static_cast<int>(home_steps[0].size())) return false;
    if (!export_board(map.ally_spawn, statics.ally_spawn)) return false;
    const vec2 probe = first_tile(map.ally_spawn);
    if (!in_bounds(probe) || !bit(statics.ally_spawn, probe.x + probe.y * statics.width)) return false;
    if (!export_board(map.passable, statics.passable) || !export_board(~map.walls, statics.unwalled)
        || !export_board(map.enemy_spawn, statics.enemy_spawn) || !export_board(map.bushes, statics.bushes))
        return false;
    for (const vec2 t : map.ally_spawn_tiles) statics.ally_box.add(t);
    statics.enemy_box = map.enemy_spawn_box;
    statics.ok = true;
    return true;
}

// The tiles a dash of at most 2 king steps from a set can land on, given `one` = grow() of the set: the
// first step anywhere within 1, the second only from a tile the path may cross (`path`), landing on `land`.
[[gnu::always_inline]] inline Rows dash_landings(const Rows& one, const Rows& path, const Rows& land) {
    return (grow(one & path) | one) & land;
}

// Farthest tile a hitting spell (or a dash's landing) reaches this turn, walk included; 0 if none.
// Ground casts and landings hit unseen tiles, so bushes don't hide from them.
int burst_reach(const ChampionFacts& f, bool& blind) {
    int r = 0;
    blind = false;
    for (const auto& a : f.abilities) {
        if (!a.hits_enemies()) continue;
        const int walk = a.excludes_walking ? 0 : 1;
        const int v = a.kind == AbilityKind::dash ? (f.ranged ? 0 : 1) + a.reach() : a.reach() + walk;
        if (v > r) r = v;
        if (a.target != Targeting::unit) blind = true;
    }
    return r;
}

// A pursuer class: enemies alike in how they reach (a union of walkers stays a union of walkers).
struct Pursuers {
    bool ranged = false;
    int reach = 1;
    int dash_turn = 0;  // first of its turns (1..horizon) a dash may fall in, 0: none
    int burst = 0;      // burst_reach, 0: none
    int burst_turn = 0; // first of its turns its burst is ready, 0: not within the plan
    bool blind = false; // the burst ignores bushes
    int delay = 0;      // its turns before it stands on `start`: one beyond the window enters at its edge
    Rows start{};
};

} // namespace

void Plan::build(const World& world, Pathing& pathing, Safety& safety) {
    const Field& home = pathing.to_ally_spawn();
    active_ = dash_ = dash_now_ = false;
    pass_[0].ready = pass_[1].ready = false;
    const auto& self = world.me();
    if (!self.alive || fuel() < params::escape::min_fuel || !ready_statics(world)) return;
    const std::uint64_t start_fuel = fuel();
    const vec2 here = my_position();
    const int steps = home.at(here);
    if (steps == unreachable || steps == 0) return;
    origin_ = {here.x - radius, here.y - radius};
    const Span at = span_of(origin_);

    // The pursuers, merged by kind.
    std::array<Pursuers, 8> kinds;
    int n = 0;
    const auto add = [&](const ChampionBelief& e, int out) -> Rows* {
        const auto& f = e.facts();
        // Its k-th turn from now falls in this round if it has yet to act; unseen, assume it has.
        const int offset = e.visible && !e.acted ? 1 : 0;
        const auto ready_turn = [&](int slot) {
            const int k = std::max(1, e.ready_round[static_cast<std::size_t>(slot)] - world.round + offset);
            return k > horizon ? 0 : k;
        };
        Pursuers kind{f.ranged, f.basic_reach(), 0, 0, 0, false, out, {}};
        if (const int slot = f.slot_of(AbilityKind::dash); slot >= 0) kind.dash_turn = ready_turn(slot);
        // Its dash, once ready, brings it in dash_range tiles sooner.
        if (kind.dash_turn > 0) kind.delay = std::min(kind.delay, std::max(kind.dash_turn, kind.delay - dash_range));
        if (kind.delay >= horizon) return nullptr;
        kind.burst = burst_reach(f, kind.blind);
        if (kind.burst > 0)
            for (int s = 0; s < 2; ++s)
                if (f.abilities[s].hits_enemies())
                    if (const int k = ready_turn(s); k > 0 && (kind.burst_turn == 0 || k < kind.burst_turn)) kind.burst_turn = k;
        if (kind.burst_turn == 0) kind.burst = 0, kind.blind = false;
        for (int i = 0; i < n; ++i) {
            const auto& o = kinds[i];
            if (o.ranged == kind.ranged && o.reach == kind.reach && o.dash_turn == kind.dash_turn && o.burst == kind.burst
                && o.burst_turn == kind.burst_turn && o.blind == kind.blind && o.delay == kind.delay)
                return &kinds[i].start;
        }
        if (n == static_cast<int>(kinds.size())) return nullptr;
        kinds[n] = kind;
        return &kinds[n++].start;
    };
    for (const auto& e : world.enemies) {
        if (!e.alive) continue;
        if (e.visible) {
            const vec2 o = enemy_reach::origin(e);
            const int x = std::clamp(o.x - origin_.x, 0, side - 1), y = std::clamp(o.y - origin_.y, 0, side - 1);
            if (auto* rows = add(e, std::max(std::abs(o.x - origin_.x - x), std::abs(o.y - origin_.y - y))))
                put(*rows, y, std::uint32_t{1} << x);
        } else if (e.tracked && e.pos_round >= world.round - params::escape::unseen_rounds && safety.credible_unseen(e)) {
            if (!export_board(e.possible, scratch_packed)) continue;
            const Rows tiles = rows_of(scratch_packed, at);
            if (none_set(tiles)) continue;
            if (auto* rows = add(e, 0)) *rows |= tiles;
        }
    }
    if (n == 0) return;

    // Terrain in the window. Live camps change rarely: exported again only when they do.
    const auto& camps = pathing.live_camps();
    if (camps_flips != pathing.live_flips() || camps_flips == ~0u) {
        if (!export_board(camps, camps_packed)) return;
        camps_flips = pathing.live_flips();
    }
    const auto spawn_rows = [&](const Packed& p, const GrowBox& b) {
        const bool meets = b.x0 < origin_.x + side && b.x1 >= origin_.x && b.y0 < origin_.y + side && b.y1 >= origin_.y;
        return meets ? rows_of(p, at, std::max(0, b.y0 - origin_.y), std::min(side, b.y1 - origin_.y + 1)) : Rows{};
    };
    const auto terrain = rows_of<4>({&camps_packed, &statics.passable, &statics.unwalled, &statics.bushes}, at);
    const Rows bush = terrain[3], spawn = spawn_rows(statics.ally_spawn, statics.ally_box);
    const Rows uncamped = ~terrain[0], walkable = terrain[1] & uncamped, crossable = terrain[2] & uncamped;
    const Rows ours = ~spawn_rows(statics.enemy_spawn, statics.enemy_box), theirs = ~spawn;
    walk_ = walkable & ours, path_ = crossable & ours;
    const Rows walk_them = walkable & theirs, path_them = crossable & theirs;
    const bool bushes = !none_set(bush);

    // Where each turn ends hit.
    for (auto& h : hit_) h = Rows{};
    const Rows open = ~bush;
    for (int c = 0; c < n; ++c) {
        const auto& kind = kinds[c];
        // `near`: grow(from), which the walk reuses.
        const auto strike = [&](int k, const Rows& from, const Rows& near, int reach, bool blind) {
            const Rows reached = widen(near, reach);
            if (!bushes || blind) {
                hit_[k] |= reached;
                return;
            }
            // Off bushes from anywhere it stands; a bush tile only from a bush tile.
            hit_[k] |= reached & open;
            if (const Rows hidden = from & bush; !none_set(hidden)) hit_[k] |= grow_by(hidden, reach) & bush;
        };
        // `moved`: where it may stand, dash spent or not; `walked`: dash unspent. They are equal until its
        // first dash turn, and from then on its dash landings hold `walked`, so a ranged pursuer's dash
        // from an undashed tile and its shot after it are in `moved` from the turn after.
        Rows walked, moved, near_moved, near_walked; // near_*: grow() of each, when known
        bool known = false, split = false;
        // Nothing stands anywhere before its first turn on `start`.
        for (int k = kind.delay + 1; k <= horizon; ++k) {
            const bool dash = kind.dash_turn > 0 && k >= kind.dash_turn;
            if (k == kind.delay + 1) walked |= kind.start, moved |= kind.start;
            if (!known) near_moved = grow(moved);
            if (!split) near_walked = near_moved;
            // A spell is cast once, but on whichever turn suits it: its first two ready turns count.
            if (kind.burst > 0 && (k == kind.burst_turn || k == kind.burst_turn + 1)) strike(k, moved, near_moved, kind.burst, kind.blind);
            // A ranged pursuer shoots from where it stood, or after a dash from an undashed tile.
            if (kind.ranged) {
                if (dash && !split) {
                    const Rows shooters = moved | dash_landings(near_walked, path_them, walk_them);
                    strike(k, shooters, grow(shooters), kind.reach, false);
                } else {
                    strike(k, moved, near_moved, kind.reach, false);
                }
            }
            walked = near_walked & walk_them, moved = near_moved & walk_them;
            if (dash) {
                near_walked = grow(walked), split = true;
                moved |= dash_landings(near_walked, path_them, walk_them);
            }
            known = !kind.ranged;
            if (known) {
                near_moved = grow(moved);
                strike(k, moved, near_moved, kind.reach, false);
            }
        }
    }
    for (int k = 1; k <= horizon; ++k) hit_[k] &= ~spawn;

    // Our dash: the turn it may first fall in after this one, if within the plan.
    if (const int slot = self.facts().slot_of(AbilityKind::dash); slot >= 0) {
        const int cool = my_cooldown(slot);
        dash_now_ = cool <= 0 && my_can_cast();
        dash_turn_ = std::max(2, cool + 1);
        dash_ = dash_turn_ <= horizon;
    }

    // The goals.
    const int which = self.facts().has_dash() ? 1 : 0;
    if (!home_ready[which]) {
        try {
            home.steps.export_linear_buffer({home_steps[which].data(), static_cast<std::size_t>(statics.width * statics.height)});
        } catch (const cambc::error&) {
            return;
        }
        home_ready[which] = true;
    }
    const int near = std::max(0, steps - horizon), slack = near + params::escape::slack_steps;
    alignas(16) std::uint16_t walks[16], goals[16] = {}, slacks[16] = {};
    std::memcpy(walks, &walk_, sizeof walks);
    const int lo = std::max(0, -origin_.x); // the window's first column on the map
    for (int y = 0; y < side; ++y) {
        const std::uint32_t walk = walks[y];
        if (!walk) continue;
        // 16 columns from the window's first on the map: past its row, masked by `walk`.
        const std::uint16_t* line = &home_steps[which][static_cast<std::size_t>((origin_.y + y) * statics.width + origin_.x + lo)];
        std::uint32_t near_bits = 0, slack_bits = 0;
#ifdef __wasm_simd128__
        const v128_t a = wasm_v128_load(line), b = wasm_v128_load(line + 8);
        const v128_t n8 = wasm_i16x8_splat(static_cast<std::int16_t>(near)), s8 = wasm_i16x8_splat(static_cast<std::int16_t>(slack));
        near_bits = wasm_i16x8_bitmask(wasm_u16x8_le(a, n8)) | wasm_i16x8_bitmask(wasm_u16x8_le(b, n8)) << 8;
        slack_bits = wasm_i16x8_bitmask(wasm_u16x8_le(a, s8)) | wasm_i16x8_bitmask(wasm_u16x8_le(b, s8)) << 8;
#else
        for (int x = 0; x < 16; ++x) {
            near_bits |= std::uint32_t{line[x] <= near} << x;
            slack_bits |= std::uint32_t{line[x] <= slack} << x;
        }
#endif
        slacks[y] = static_cast<std::uint16_t>(slack_bits << lo & walk);
        goals[y] = static_cast<std::uint16_t>(near_bits << lo & walk);
    }
    Rows goal;
    std::memcpy(&goal, goals, sizeof goal);
    std::memcpy(&slack_goal_, slacks, sizeof slack_goal_);
    run(goal, pass_[0]);
    active_ = true;
    debug_block({
        std::printf("ESC %d %u kinds %d dash %d/%d fuel %llu\n", world.round, my_handle(), n, dash_ ? dash_turn_ : 0, dash_now_ ? 1 : 0,
                    static_cast<unsigned long long>(start_fuel - fuel()));
    });
}

// Backward over the turns: S_H is the goal; a turn k ending on a tile costs a hit there if hit_[k]
// holds it; S_{k-1} is where a turn-k move (a walk, and with the dash kept and ready, a dash before
// or after it: approximated as a walk then a dash) reaches T_k, the tiles S_k leaves room for.
// s<j><d>: by hits allowed j and dash kept d (with Dash only; else d reads as 0).
template <bool Dash>
[[gnu::always_inline]] inline void run_pass(const Rows& goal, const Rows& walk, const Rows& path, const std::array<Rows, horizon + 1>& hits,
                                            int dash_turn, Plan::Pass& out) {
    Rows s00 = goal, s10 = goal, s01 = goal, s11 = goal; // the goal holds walk tiles only
    for (int k = horizon; k >= 2; --k) {
        const Rows hit = hits[k], clear = ~hit;
        const Rows g0 = grow(s00 & clear), g1 = grow((s10 & clear) | (s00 & hit));
        if constexpr (Dash) {
            Rows k0 = s01 & clear, k1 = (s11 & clear) | (s01 & hit);
            if (k >= dash_turn) {
                // The tiles a dash from lands in T (dash spent), stood on after this turn's walk.
                k0 |= dash_landings(g0, path, walk);
                k1 |= dash_landings(g1, path, walk);
            }
            s01 = grow(k0) & walk, s11 = grow(k1) & walk;
        }
        s00 = g0 & walk, s10 = g1 & walk;
    }
    if constexpr (!Dash) s01 = s00, s11 = s10;
    out.after[0][0] = s00, out.after[1][0] = s10, out.after[0][1] = s01, out.after[1][1] = s11;
    const Rows hit = hits[1], clear = ~hit;
    out.dashed[0] = grow(s00 & clear) & walk;
    out.dashed[1] = grow((s10 & clear) | (s00 & hit)) & walk;
    out.kept[0] = grow(s01 & clear) & walk;
    out.kept[1] = grow((s11 & clear) | (s01 & hit)) & walk;
    out.ready = true;
}

void Plan::run(const Rows& goal, Pass& out) const {
    if (dash_) run_pass<true>(goal, walk_, path_, hit_, dash_turn_, out);
    else run_pass<false>(goal, walk_, path_, hit_, dash_turn_, out);
}

void Plan::want_slack() {
    if (active_ && !pass_[1].ready && fuel() >= params::escape::slack_fuel) run(slack_goal_, pass_[1]);
}

int Plan::value(const Rows& none, const Rows& one, vec2 p) const {
    const int x = p.x - origin_.x, y = p.y - origin_.y;
    if (x < 0 || y < 0 || x >= side || y >= side) return many;
    const std::uint32_t b = std::uint32_t{1} << x;
    return get(none, y) & b ? 0 : get(one, y) & b ? 1 : many;
}

int Plan::after_walk(vec2 p, bool slack) const {
    const auto& ps = pass(slack);
    const int d = dash_ ? 1 : 0;
    return value(ps.after[0][d], ps.after[1][d], p);
}

int Plan::after_dash(vec2 p, bool slack) const { return value(pass(slack).dashed[0], pass(slack).dashed[1], p); }

int Plan::keep_dash(bool slack) const { return value(pass(slack).kept[0], pass(slack).kept[1], at); }

Plan& plan(const World& world, Pathing& pathing, Safety& safety) {
    static Plan p;
    const vec2 here = my_position();
    const auto me = static_cast<std::uint32_t>(world.me().handle);
    if (p.round != world.round || p.handle != me || p.at != here || p.observations != world.observations) {
        p.round = world.round, p.handle = me, p.at = here, p.observations = world.observations;
        p.build(world, pathing, safety);
    }
    return p;
}

} // namespace escape

} // namespace aph
