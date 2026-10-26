#pragma once
#include <cambc.h>
#include <algorithm>
#include <array>
#include <cstdint>
#include <cstdlib>
#include <cstdio>
#include <memory>
#include <vector>

namespace aph {

using cambc::bitboard;
using cambc::team;
using cambc::vec2;

// A stdout line costs about 1.3k fuel and each team's output is capped at 1 MiB; indicator dots
// and lines are cheaper.
inline constexpr bool debug_log = false;    // map summary on the first turn
inline constexpr bool debug_draw = false;   // world beliefs as indicator dots and lines
inline constexpr bool debug_fuel = false;   // fuel used by each phase of the turn
// Belief dump for tools/replay/audit_beliefs.py: a "BD" stdout line per champion every period
// rounds (and in rounds 1-3), self-limited to a share of the team's 1 MiB output.
inline constexpr bool debug_beliefs = false;
inline constexpr int debug_beliefs_period = 10;
// Fight-model calibration: an "FF" stdout line per turn in reach of an enemy, "FC" per chase.
inline constexpr bool debug_fights = false;

// A choice made worse to save fuel: one "SHORTCUT round champion what" stdout line. debug_block
// spends no fuel in local (non-release) builds and is compiled out of release ones.
inline void note_shortcut(const char* what) {
    debug_block({
        if (!cambc::is_draft())
            std::printf("SHORTCUT %d %u %s\n", cambc::round_number(),
                        static_cast<unsigned>(static_cast<cambc::handle_champion_t>(cambc::self())), what);
    });
}

// Turns in which we damaged a camp (attack_camp, cast_at_camp, reset_and_attack_camp): the share of
// time spent clearing, which emblems price.
inline int& camp_hits() {
    static int hits = 0;
    return hits;
}

// Dashes cast outside Pathing (Heart of Ruin's landings): Pathing reads our tile again after one.
inline unsigned& outside_dashes() {
    static unsigned dashes = 0;
    return dashes;
}

// The phase running, for locating out-of-fuel turns: set and read only inside debug_block.
inline const char*& fuel_phase() {
    static const char* phase = "start";
    return phase;
}

// The group the team is besieging this turn, a Monolith or a group sealing the altars (seals()),
// or -1: camp actions skip every other Monolith.
inline int& siege_group() {
    static int g = -1;
    return g;
}

// cambc::detail::check() out of line costs a call and a stack frame per host call; it throws only for
// a nonzero code.
[[gnu::always_inline]] inline void ok(std::int32_t code) {
    if (code != 0) [[unlikely]] cambc::detail::check(code);
}

// Our own champion, read raw. The SDK's accessors build and copy a whole record for each field
// (position() ~85 fuel, item_count() ~225); a raw read into static storage costs ~25. Each call
// reads the engine again, as the SDK's do.
// Read once at start-up, after the SDK's own; 0 in the draft, which has no champion.
inline const std::uint32_t my_handle_value =
    cambc::detail::cached_self ? static_cast<std::uint32_t>(static_cast<cambc::handle_champion_t>(*cambc::detail::cached_self)) : 0;
inline std::uint32_t my_handle() { return my_handle_value; }
[[gnu::always_inline]] inline const cambc::detail::champion_info& my_record() {
    static cambc::detail::champion_info record;
    ok(cambc::detail::sdk_champion(my_handle(), &record));
    return record;
}
[[gnu::always_inline]] inline vec2 my_position() {
    const auto& r = my_record();
    return {r.x, r.y};
}
[[gnu::always_inline]] inline float my_health() { return my_record().health; }
[[gnu::always_inline]] inline float my_max_health() { return my_record().max_health; }
[[gnu::always_inline]] inline float my_strength() { return my_record().strength; }
[[gnu::always_inline]] inline cambc::champion_state my_state() { return cambc::champion_state::from_bits_retain(my_record().state); }
[[gnu::always_inline]] inline bool my_can_move() { return my_state().contains(cambc::champion_state::can_move); }
[[gnu::always_inline]] inline bool my_can_attack() { return my_state().contains(cambc::champion_state::can_attack); }
[[gnu::always_inline]] inline bool my_can_cast() { return my_state().contains(cambc::champion_state::can_cast); }
[[gnu::always_inline]] inline std::uint32_t my_gems() {
    static std::uint32_t gems;
    ok(cambc::detail::sdk_champion_gems(my_handle(), &gems));
    return gems;
}
[[gnu::always_inline]] inline std::uint32_t my_gold() {
    static std::uint32_t gold;
    ok(cambc::detail::sdk_champion_gold(my_handle(), &gold));
    return gold;
}
inline const cambc::enum_map<cambc::item_type>& my_items() {
    static cambc::enum_map<cambc::item_type> items;
    ok(cambc::detail::sdk_champion_items(my_handle(), items.ptr()));
    return items;
}
// Camps hit a Jungle emblem's owner 30% softer, and a Durability emblem's 10%.
float camp_hit_factor();
// A Monster emblem's owner hits camps 15% harder, a Collectors one 1% per emblem family owned.
float camp_dealt_factor();

// Other champions read raw too: building a cambc::champion reads both its ability records (two
// host calls), each accessor reads a whole record again, and buffs() allocates. Failures throw
// the SDK's own errors, so callers catch what they caught before.
// c.info(), valid until the next call: throws if hidden.
[[gnu::always_inline]] inline const cambc::detail::champion_info& record_of(cambc::handle_champion_t c) {
    static cambc::detail::champion_info record;
    ok(cambc::detail::sdk_champion(static_cast<std::uint32_t>(c), &record));
    return record;
}
// c.is_visible(), keeping the record it read: null if hidden or dead. Valid until the next call.
[[gnu::always_inline]] inline const cambc::detail::champion_info* visible_record(cambc::handle_champion_t c) {
    static cambc::detail::champion_info record;
    const auto code = cambc::detail::sdk_champion(static_cast<std::uint32_t>(c), &record);
    if (code == static_cast<std::int32_t>(cambc::error_code::api_not_in_vision)) return nullptr;
    ok(code);
    return record.x >= 0 && record.y >= 0 ? &record : nullptr;
}
inline bool is_alive(cambc::handle_champion_t c) {
    static std::int32_t value;
    ok(cambc::detail::sdk_champion_is_alive(static_cast<std::uint32_t>(c), &value));
    return value != 0;
}
// Readable for hidden and dead champions too.
inline const cambc::detail::champion_identity& identity_of(cambc::handle_champion_t c) {
    static cambc::detail::champion_identity identity;
    ok(cambc::detail::sdk_champion_identity(static_cast<std::uint32_t>(c), &identity));
    return identity;
}
inline bool has_stun(cambc::handle_champion_t c) {
    static std::array<cambc::detail::buff_data, static_cast<std::size_t>(cambc::buff_types::count)> buffs;
    std::uint32_t n = 0;
    ok(cambc::detail::sdk_champion_buff_data(static_cast<std::uint32_t>(c), buffs.data(), static_cast<std::uint32_t>(buffs.size()), &n));
    for (std::uint32_t i = 0; i < n && i < buffs.size(); ++i)
        if (buffs[i].type == static_cast<std::uint32_t>(cambc::buff_types::stun)) return true;
    return false;
}
// A champion in sight has a stun that will take its next turn. One at 0 turn ends left has already
// taken a turn and expires at the next one's start.
inline bool stun_pending(cambc::handle_champion_t c) {
    static std::array<cambc::detail::buff_data, static_cast<std::size_t>(cambc::buff_types::count)> buffs;
    std::uint32_t n = 0;
    ok(cambc::detail::sdk_champion_buff_data(static_cast<std::uint32_t>(c), buffs.data(), static_cast<std::uint32_t>(buffs.size()), &n));
    for (std::uint32_t i = 0; i < n && i < buffs.size(); ++i)
        if (buffs[i].type == static_cast<std::uint32_t>(cambc::buff_types::stun)) return buffs[i].data.stun.duration > 0;
    return false;
}
// A camp in sight skips its next attack. A stun's buff stays listed at timer 0 after the camp phase it
// skipped, until the next one (probe-campstun). False out of sight, without a throw.
inline bool camp_stunned(std::uint32_t camp) {
    static std::array<cambc::detail::camp_buff_data, static_cast<std::size_t>(cambc::buff_types::count)> buffs;
    std::uint32_t n = 0;
    if (cambc::detail::sdk_camp_buffs(camp, buffs.data(), static_cast<std::uint32_t>(buffs.size()), &n) != 0) return false;
    for (std::uint32_t i = 0; i < n && i < buffs.size(); ++i)
        if (buffs[i].type == static_cast<std::uint32_t>(cambc::buff_types::stun)) return buffs[i].timer > 0;
    return false;
}
// The active shield's value, 0 if none.
inline float shield_value(cambc::handle_champion_t c) {
    static std::array<cambc::detail::buff_data, static_cast<std::size_t>(cambc::buff_types::count)> buffs;
    std::uint32_t n = 0;
    ok(cambc::detail::sdk_champion_buff_data(static_cast<std::uint32_t>(c), buffs.data(), static_cast<std::uint32_t>(buffs.size()), &n));
    for (std::uint32_t i = 0; i < n && i < buffs.size(); ++i)
        if (buffs[i].type == static_cast<std::uint32_t>(cambc::buff_types::shield)) return buffs[i].data.shield.value;
    return 0;
}
// The champion cambc::vision::champion_at(p) views: throws if none is visible there.
inline cambc::handle_champion_t champion_at(vec2 p) {
    static std::uint32_t c;
    ok(cambc::detail::sdk_champion_at(p.x, p.y, &c));
    return static_cast<cambc::handle_champion_t>(c);
}

// From our state at turn start: later, a turn that has walked, attacked and cast shows the same bits.
inline bool my_stunned(cambc::champion_state state) {
    using cambc::champion_state;
    // A stun cancels channels.
    if (state.contains(champion_state::can_move) || state.contains(champion_state::can_attack) || state.contains(champion_state::can_cast)
        || state.contains(champion_state::recalling) || state.contains(champion_state::submitting_gems)
        || state.contains(champion_state::teleporting))
        return false;
    return has_stun(static_cast<cambc::handle_champion_t>(my_handle()));
}

// cambc::self().abilities()[slot] copies both our abilities: one slot's reads and casts, raw.
[[gnu::always_inline]] inline float my_damage(int slot) {
    static float value;
    ok(cambc::detail::sdk_champion_ability_damage(my_handle(), static_cast<std::uint32_t>(slot), &value));
    return value;
}
// After the target's mitigation and shields, capped at its health; it must be visible.
[[gnu::always_inline]] inline float my_damage_to(int slot, cambc::handle_champion_t target) {
    static float value;
    ok(cambc::detail::sdk_champion_ability_damage_against(my_handle(), static_cast<std::uint32_t>(slot),
                                                          static_cast<std::uint32_t>(target), &value));
    return value;
}
inline float my_heal(int slot) {
    static float value;
    ok(cambc::detail::sdk_champion_ability_heal(my_handle(), static_cast<std::uint32_t>(slot), &value));
    return value;
}
inline float my_shield(int slot) {
    static float value;
    ok(cambc::detail::sdk_champion_ability_shield(my_handle(), static_cast<std::uint32_t>(slot), &value));
    return value;
}
inline int my_cooldown(int slot) {
    static std::int32_t value;
    ok(cambc::detail::sdk_champion_cooldown(my_handle(), static_cast<std::uint32_t>(slot), &value));
    return value;
}
inline std::uint32_t round_now() {
    static std::uint32_t round;
    round = 0;
    (void)cambc::detail::sdk_bc_round_number(&round);
    return round;
}
// A turn that ran out of fuel resumes in the next round, a round old: it is abandoned at the next
// check, so that the round's own turn, played next on what fuel is left, does not run out in turn.
struct StaleTurn {};
inline std::uint32_t& turn_round() { // the round the turn began in (World::update)
    static std::uint32_t round = 0;
    return round;
}
// ~18 fuel: worth it in a loop whose pass costs a few hundred or more. Every action calls it first:
// the resumed tail runs on last round's beliefs, and the fresh turn after it plans as if nothing
// had acted (a second recall start or an exclusive cast after a walk is an engine error).
inline void throw_if_stale() {
    if (round_now() != turn_round()) throw StaleTurn{};
}
// ability.use(): at `tile`, or {-1, -1} for none. False for a newly revealed hidden blocker.
inline bool cast_slot(int slot, vec2 tile = {-1, -1}) {
    throw_if_stale();
    static std::int32_t cast;
    ok(cambc::detail::sdk_cast(static_cast<std::uint32_t>(slot), 0, 0, tile.x, tile.y, &cast));
    return cast != 0;
}
inline bool cast_slot_on(int slot, cambc::handle_champion_t target) {
    throw_if_stale();
    static std::int32_t cast;
    ok(cambc::detail::sdk_cast(static_cast<std::uint32_t>(slot), static_cast<std::uint32_t>(cambc::detail::entity_kind::champion),
                               static_cast<std::uint32_t>(target), -1, -1, &cast));
    return cast != 0;
}
inline bool cast_slot_on(int slot, cambc::handle_camp_t target) {
    throw_if_stale();
    static std::int32_t cast;
    ok(cambc::detail::sdk_cast(static_cast<std::uint32_t>(slot), static_cast<std::uint32_t>(cambc::detail::entity_kind::camp),
                               static_cast<std::uint32_t>(target), -1, -1, &cast));
    return cast != 0;
}
// cambc::self().attack(c), without building c.
inline void attack_champion(cambc::handle_champion_t target) {
    throw_if_stale();
    ok(cambc::detail::sdk_attack(static_cast<std::uint32_t>(cambc::detail::entity_kind::champion), static_cast<std::uint32_t>(target)));
}
// Turn ends left of our channel.
inline std::int32_t my_channel_time() {
    static std::int32_t turns;
    ok(cambc::detail::sdk_champion_channel_time(my_handle(), &turns));
    return turns;
}

// In 32 bits: the SDK's chebyshev_distance works in 64.
inline int dist(vec2 a, vec2 b) { return std::max(std::abs(a.x - b.x), std::abs(a.y - b.y)); }

inline bool in_bounds(vec2 p) { return cambc::map::is_in_bounds(p); }

inline int tile_index(vec2 p) { return p.x + p.y * cambc::map::width(); }

// The 8 king-step directions, north first and clockwise.
inline constexpr vec2 directions[8] = {vec2::north, vec2::north_east, vec2::east, vec2::south_east,
                                       vec2::south, vec2::south_west, vec2::west, vec2::north_west};

// b.is_set(p) without check()'s call and a stack slot.
[[gnu::always_inline]] inline bool test(const bitboard& b, vec2 p) {
    static std::int32_t value;
    ok(cambc::detail::sdk_Bitboard_Test(b.ptr(), p.x, p.y, &value));
    return value != 0;
}

// The SDK's bitboard calls without check()'s call and a stack slot for the result.
[[gnu::always_inline]] inline void clear_board(bitboard& b) { ok(cambc::detail::sdk_Bitboard_Zero(b.ptr())); }
[[gnu::always_inline]] inline void set_tile(bitboard& b, vec2 p, bool value = true) {
    ok(cambc::detail::sdk_Bitboard_Set(b.ptr(), p.x, p.y, value));
}
[[gnu::always_inline]] inline void draw_square(bitboard& b, vec2 centre, float radius) {
    ok(cambc::detail::sdk_Bitboard_DrawChebyshev(b.ptr(), centre.x, centre.y, radius));
}
[[gnu::always_inline]] inline bool board_empty(const bitboard& b) {
    static std::int32_t value;
    ok(cambc::detail::sdk_Bitboard_IsZero(b.ptr(), &value));
    return value != 0;
}
[[gnu::always_inline]] inline bool boards_equal(const bitboard& a, const bitboard& b) {
    static std::int32_t value;
    ok(cambc::detail::sdk_Bitboard_IsEqual(a.ptr(), b.ptr(), &value));
    return value != 0;
}
[[gnu::always_inline]] inline std::uint32_t board_count(const bitboard& b) {
    static std::uint32_t value;
    ok(cambc::detail::sdk_Bitboard_NumSetBits(b.ptr(), &value));
    return value;
}
[[gnu::always_inline]] inline std::uint32_t positions_into(const bitboard& b, vec2* out, std::uint32_t size) {
    static std::uint32_t count;
    ok(cambc::detail::sdk_Bitboard_GetSetBits(b.ptr(), out, size, &count));
    return count;
}

// cambc::vision's occupancy reads, without check()'s call.
[[gnu::always_inline]] inline void occupancy_into(team side, bitboard& out) {
    ok(side == team::ally ? cambc::detail::sdk_ally_occupancy(out.ptr()) : cambc::detail::sdk_enemy_occupancy(out.ptr()));
}
[[gnu::always_inline]] inline void camps_into(bitboard& out) { ok(cambc::detail::sdk_camp_occupancy(out.ptr())); }
[[gnu::always_inline]] inline void teleports_into(bitboard& out) { ok(cambc::detail::sdk_teleport_occupancy(out.ptr())); }
[[gnu::always_inline]] inline void vision_into(bitboard& out) { ok(cambc::detail::sdk_vision(out.ptr())); }

inline bitboard single(vec2 p) {
    bitboard b;
    set_tile(b, p);
    return b;
}

inline bitboard square(vec2 p, int r) {
    bitboard b;
    draw_square(b, p, static_cast<float>(r));
    return b;
}

// bitboard::positions() into a fixed buffer, without its count call and heap allocation (~300
// fuel). The caller bounds the set to N tiles.
template <std::size_t N> class Tiles {
public:
    explicit Tiles(const bitboard& b) : count_{std::min<std::uint32_t>(positions_into(b, tiles_, N), N)} {}
    const vec2* begin() const { return tiles_; }
    const vec2* end() const { return tiles_ + count_; }
    bool empty() const { return count_ == 0; }

private:
    union {
        vec2 tiles_[N]; // left uninitialised for the host to fill
    };
    std::uint32_t count_;
};

// The first set tile in board order; b must not be empty.
inline vec2 first_tile(const bitboard& b) {
    vec2 p;
    (void)positions_into(b, &p, 1);
    return p;
}

// out = a | b, a & b, a ^ b, ~a: one host call each, where the operators allocate a result (~130) or
// take two calls to copy (clear and |=). out may be a or b.
inline void or_into(const bitboard& a, const bitboard& b, bitboard& out) {
    ok(cambc::detail::sdk_Bitboard_Union(a.ptr(), b.ptr(), out.ptr()));
}
inline void and_into(const bitboard& a, const bitboard& b, bitboard& out) {
    ok(cambc::detail::sdk_Bitboard_Intersect(a.ptr(), b.ptr(), out.ptr()));
}
inline void xor_into(const bitboard& a, const bitboard& b, bitboard& out) {
    ok(cambc::detail::sdk_Bitboard_Xor(a.ptr(), b.ptr(), out.ptr()));
}
inline void not_into(const bitboard& a, bitboard& out) {
    ok(cambc::detail::sdk_Bitboard_Not(a.ptr(), out.ptr()));
}
inline void copy_into(const bitboard& a, bitboard& out) { or_into(a, a, out); }
// out &= ~tiles without a new board.
inline void drop(bitboard& out, const bitboard& tiles) {
    or_into(out, tiles, out);
    xor_into(out, tiles, out);
}

// The helpers below work in scratch boards: allocating a board (~300 fuel) costs more than the
// host operations on it (~120).

// `tiles` within Chebyshev r of p, in a scratch board valid until the next call. The square is
// kept for the next call with the same p and r.
inline const bitboard& within(const bitboard& tiles, vec2 p, int r) {
    static bitboard square{cambc::uninitialized}, box{cambc::uninitialized};
    static vec2 square_at{-1, -1};
    static int square_r = -1;
    if (p != square_at || r != square_r) {
        clear_board(square);
        draw_square(square, p, static_cast<float>(r));
        square_at = p, square_r = r;
    }
    and_into(square, tiles, box);
    return box;
}

// r <= 8.
inline Tiles<17 * 17> positions_within(const bitboard& tiles, vec2 p, int r) { return Tiles<17 * 17>{within(tiles, p, r)}; }
inline bool any_within(const bitboard& tiles, vec2 p, int r) { return !board_empty(within(tiles, p, r)); }
inline std::uint32_t count_within(const bitboard& tiles, vec2 p, int r) { return board_count(within(tiles, p, r)); }

// Live occupancy, each in its own scratch board, valid until its next read.
inline const bitboard& live_champion_tiles(team side) {
    static bitboard ally{cambc::uninitialized}, enemy{cambc::uninitialized};
    auto& b = side == team::ally ? ally : enemy;
    occupancy_into(side, b);
    return b;
}

inline const bitboard& live_camp_tiles() {
    static bitboard b{cambc::uninitialized};
    camps_into(b);
    return b;
}

inline constexpr std::uint16_t unreachable = cambc::distance_field::unreachable;

// field.get(p) without check()'s call and a stack slot.
[[gnu::always_inline]] inline int steps_at(const cambc::distance_field& field, vec2 p) {
    static std::uint16_t result;
    ok(cambc::detail::sdk_DistanceField_Get(field.ptr(), p.x, p.y, &result));
    return result;
}

struct Field {
    cambc::distance_field steps;
    bitboard goals;
    int at(vec2 p) const { return steps_at(steps, p); } // `unreachable` if cut off
};

// A host search costs about 1.5k + (20 + layers) per 8x8 chunk of the map.
inline std::uint64_t search_chunks() {
    return static_cast<std::uint64_t>((cambc::map::width() + 7) / 8 * ((cambc::map::height() + 7) / 8));
}

inline int& max_field_layers() {
    static int layers = 0;
    return layers;
}

// The most an uncapped field has cost so far, 0 before the first.
inline std::uint64_t& costliest_field() {
    static std::uint64_t cost = 0;
    return cost;
}

inline Field make_field(const bitboard& walls, const bitboard& goals) {
    static bitboard visited{cambc::uninitialized};
    const auto before = cambc::fuel_remaining();
    Field f;
    not_into(walls, f.goals);
    f.goals &= goals;
    max_field_layers() = std::max<int>(max_field_layers(), f.steps.compute_with_expansion_count(walls, f.goals, visited));
    if (const auto after = cambc::fuel_remaining(); after < before) costliest_field() = std::max(costliest_field(), before - after);
    return f;
}

// Costs at most search_cost_estimate(max_layers). Null if cut short: a complete field's layer
// count is one over its deepest step, so one below the cap proves it whole.
inline std::unique_ptr<Field> make_field(const bitboard& walls, const bitboard& goals, int max_layers) {
    static bitboard visited{cambc::uninitialized};
    auto f = std::make_unique<Field>();
    not_into(walls, f->goals);
    f->goals &= goals;
    const int layers = f->steps.compute_with_expansion_count(walls, f->goals, visited, static_cast<std::uint16_t>(max_layers));
    if (layers >= max_layers) return nullptr;
    max_field_layers() = std::max(max_field_layers(), layers);
    return f;
}

// The imports read raw: the SDK's wrappers add checks for failures only an ABI mismatch could cause.
inline std::uint64_t fuel() { return static_cast<std::uint64_t>(cambc::detail::sdk_fuel_remaining()); }
// cambc::round_number() without check()'s call and a stack slot.
inline std::uint32_t checked_round() {
    static std::uint32_t round;
    ok(cambc::detail::sdk_bc_round_number(&round));
    return round;
}

inline std::uint64_t search_cost_estimate(int layers) {
    return 4000 + search_chunks() * (20 + static_cast<std::uint64_t>(layers));
}

// Layers: a quarter over the deepest full field so far, or width + height before the first.
inline std::uint64_t field_cost_estimate() {
    const int seen = max_field_layers();
    return search_cost_estimate(seen ? seen + seen / 4 : cambc::map::width() + cambc::map::height()) - 1000;
}
// An uncapped field from anywhere: a quarter over the costliest so far, once one is measured.
inline std::uint64_t full_field_cost_estimate() {
    const auto seen = costliest_field();
    return seen ? seen + seen / 4 : field_cost_estimate();
}
inline constexpr std::uint64_t small_cost_estimate = 5000;

inline bool fuel_ok(std::uint64_t needed) { return fuel() >= needed; }

// Storage left unwritten until used: vec2 and std::pair initialise their members.
template <typename T, std::size_t N> union Unwritten {
    Unwritten() {}
    std::array<T, N> a;
};

// Left for the rest of the turn after optional work.
inline constexpr std::uint64_t end_reserve = 10000;
// Left by the fight evaluations before acting: the strikes, the goal's walk and the turn's end.
inline constexpr std::uint64_t act_reserve = 2 * end_reserve;
// Left after work whose cost is bounded, at the end of the turn: little runs after warm-up.
inline constexpr std::uint64_t last_reserve = 2000;
// Layers a capped centre field may run past the farther spawn's steps to it; a field cut short
// is redone at twice the cap.
inline constexpr int centre_depth_margin = 24;

inline void draw_dot(vec2 p, std::uint32_t rgb) {
    if constexpr (debug_draw) cambc::debug::draw_dot(p, rgb);
}

inline void draw_line(vec2 a, vec2 b, std::uint32_t rgb) {
    if constexpr (debug_draw) cambc::debug::draw_line(a, b, rgb);
}

// Samples print together at the end of the turn, so printing does not skew them.
struct FuelSample {
    const char* label;
    std::uint32_t round;
    std::uint64_t used;
    bool spilled;
};

inline std::vector<FuelSample>& fuel_log() {
    static std::vector<FuelSample> log;
    return log;
}

class FuelMeter {
public:
    explicit FuelMeter(const char* label) : label_{label} {
        if constexpr (debug_fuel) {
            start_ = fuel();
            round_ = cambc::round_number();
        }
    }
    ~FuelMeter() {
        if constexpr (debug_fuel) {
            const auto now = fuel();
            const bool spilled = cambc::round_number() != round_;
            fuel_log().push_back({label_, round_, spilled ? 0 : start_ - now, spilled});
        }
    }
    FuelMeter(const FuelMeter&) = delete;
    FuelMeter& operator=(const FuelMeter&) = delete;

private:
    const char* label_;
    std::uint64_t start_ = 0;
    std::uint32_t round_ = 0;
};

// A meter still open when this runs is reported on the next line. Free in local builds, where
// debug_block spends no fuel; release builds print nothing.
inline void print_fuel_log() {
    if constexpr (debug_fuel) {
        debug_block({
            std::printf("fuel r%u c%d", cambc::round_number(),
                        cambc::is_draft() ? -1 : static_cast<int>(static_cast<cambc::handle_champion_t>(cambc::self())));
            auto& log = fuel_log();
            for (std::size_t i = 0; i < log.size(); ++i) {
                if (!log[i].label) continue;
                std::printf(" %s=", log[i].label);
                if (log[i].spilled) {
                    std::printf("SPILLED(r%u)", log[i].round);
                    continue;
                }
                std::uint64_t total = log[i].used;
                int count = 1;
                for (std::size_t j = i + 1; j < log.size(); ++j)
                    if (log[j].label == log[i].label && !log[j].spilled) total += log[j].used, ++count, log[j].label = nullptr;
                std::printf("%llu", static_cast<unsigned long long>(total));
                if (count > 1) std::printf("/%d", count);
            }
            std::printf(" left=%llu\n", static_cast<unsigned long long>(fuel()));
        });
        fuel_log().clear();
    }
}

} // namespace aph
