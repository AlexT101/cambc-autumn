// Each instance is the draft bot or one champion; Cassi and Issac are two.
#include <cambc.h>
#include <algorithm>
#include <bit>
#include <cstddef>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <memory>
#include <new>
#include <utility>
#include <vector>
#include "bot.h"
#include "combat/plan.h"
#include "draft/draft.h"
#include "model/comms.h"
#include "model/pathing.h"
#include "model/world.h"
#include "util.h"

// Every operator new, bitboards' aligned one included, takes from a bump arena that is never
// freed, then from malloc once it is full: malloc and free cost a few hundred fuel a pair, and a
// first turn makes ~300 allocations (play turns ~0.2).
namespace {

constexpr std::size_t arena_bytes = std::size_t{2} << 20;
constexpr std::size_t arena_align = 16; // __STDCPP_DEFAULT_NEW_ALIGNMENT__
alignas(arena_align) std::byte arena[arena_bytes];
std::size_t arena_used = 0; // a multiple of arena_align

[[gnu::always_inline]] inline void* arena_take(std::size_t n) {
    // The space left is a multiple of arena_align, so the rounded size fits exactly when n is below
    // it; testing n first keeps a huge n from wrapping. (n | 1): a zero-byte allocation still takes
    // a unique address.
    if (n >= arena_bytes - arena_used) return nullptr;
    const std::size_t size = ((n | 1) + arena_align - 1) & ~(arena_align - 1);
    void* const p = arena + arena_used;
    arena_used += size;
    return p;
}

[[gnu::always_inline]] inline bool in_arena(const void* p) {
    return reinterpret_cast<std::uintptr_t>(p) - reinterpret_cast<std::uintptr_t>(arena) < arena_bytes;
}

// Null on failure. Alignments up to arena_align are malloc's own.
[[gnu::noinline]] void* heap_take(std::size_t n, std::size_t align) noexcept {
    return align <= arena_align   ? std::malloc(n ? n : 1)
           : n <= SIZE_MAX - align ? std::aligned_alloc(align, (n + align - 1) / align * align)
                                   : nullptr;
}

[[gnu::always_inline]] inline void* try_take(std::size_t n) noexcept {
    if (void* p = arena_take(n)) return p;
    return heap_take(n, arena_align);
}

[[gnu::always_inline]] inline void* try_take(std::size_t n, std::align_val_t a) noexcept {
    const auto align = static_cast<std::size_t>(a);
    if (align <= arena_align)
        if (void* p = arena_take(n)) return p;
    return heap_take(n, align);
}

[[gnu::noinline, noreturn]] void out_of_memory() { throw std::bad_alloc(); }

[[gnu::always_inline]] inline void* or_throw(void* p) {
    if (!p) [[unlikely]] out_of_memory();
    return p;
}

[[gnu::always_inline]] inline void give(void* p) {
    if (!in_arena(p)) std::free(p);
}

} // namespace

void* operator new(std::size_t n) { return or_throw(try_take(n)); }
void* operator new[](std::size_t n) { return or_throw(try_take(n)); }
void* operator new(std::size_t n, std::align_val_t a) { return or_throw(try_take(n, a)); }
void* operator new[](std::size_t n, std::align_val_t a) { return or_throw(try_take(n, a)); }
void* operator new(std::size_t n, const std::nothrow_t&) noexcept { return try_take(n); }
void* operator new[](std::size_t n, const std::nothrow_t&) noexcept { return try_take(n); }
void* operator new(std::size_t n, std::align_val_t a, const std::nothrow_t&) noexcept { return try_take(n, a); }
void* operator new[](std::size_t n, std::align_val_t a, const std::nothrow_t&) noexcept { return try_take(n, a); }
void operator delete(void* p) noexcept { give(p); }
void operator delete[](void* p) noexcept { give(p); }
void operator delete(void* p, std::size_t) noexcept { give(p); }
void operator delete[](void* p, std::size_t) noexcept { give(p); }
void operator delete(void* p, std::align_val_t) noexcept { give(p); }
void operator delete[](void* p, std::align_val_t) noexcept { give(p); }
void operator delete(void* p, std::size_t, std::align_val_t) noexcept { give(p); }
void operator delete[](void* p, std::size_t, std::align_val_t) noexcept { give(p); }
void operator delete(void* p, const std::nothrow_t&) noexcept { give(p); }
void operator delete[](void* p, const std::nothrow_t&) noexcept { give(p); }
void operator delete(void* p, std::align_val_t, const std::nothrow_t&) noexcept { give(p); }
void operator delete[](void* p, std::align_val_t, const std::nothrow_t&) noexcept { give(p); }

namespace {

// What the turn's last phases need on their cheap paths.
constexpr std::uint64_t late_floor = 1500;
constexpr std::uint64_t turn_fuel = 100000; // twice it on a champion's first turn

template <class F> bool run(const char* phase, F&& f) {
    debug_block({ aph::fuel_phase() = phase; });
    try {
        f();
        return true;
    } catch (const aph::StaleTurn&) {
    } catch (const std::exception& e) {
        std::printf("r%u %s error: %s\n", cambc::round_number(), phase, e.what());
    } catch (...) {
        std::printf("r%u %s error: unknown exception\n", cambc::round_number(), phase);
    }
    return false;
}

// Spare fuel fills caches, in order: the terrain-only tables a fight reads around visible enemies,
// next turn's walk, the map-wide work (spawn field and group hops, then centre, altar and hop
// fields, attack tiles, bush clusters), then the same tables around us (wider while dead). Never
// changes play: every reader makes what it needs when it is missing. Bound by the fuel spent this
// turn against the real budget, so it fills the same at any budget.
struct TurnEndQueue {
    static constexpr std::uint64_t tile_reserve = 6000; // a tile's tables on 100x100, with margin
    // Filled tiles (or walls) as bits by row and by column, 2 words each: a ring's sides are 4 spans.
    std::vector<std::uint64_t> rows, cols;
    std::vector<std::uint8_t> rings; // by tile: rings around it all done, + 1
    bool map_warmed_up = false, warmed_up = false;
    bool logged_centres = false; // debug_block only

    // The first clear bit in [lo, hi] of a 2-word line, or -1.
    static int first_clear(const std::uint64_t* line, int lo, int hi) {
        for (int w = lo >> 6; w <= hi >> 6; ++w) {
            const int a = std::max(lo, w * 64) - w * 64, b = std::min(hi, w * 64 + 63) - w * 64;
            const std::uint64_t span = (b == 63 ? ~std::uint64_t{0} : (std::uint64_t{2} << b) - 1) & (~std::uint64_t{0} << a);
            if (const std::uint64_t m = ~line[w] & span) return w * 64 + std::countr_zero(m);
        }
        return -1;
    }

    // `start`: the fuel left when the turn began.
    void run(aph::World& world, aph::Pathing& pathing, const aph::Memory& memory, std::uint64_t start) {
        const auto& map = world.map();
        const int W = map.width, H = map.height;
        // Above the real budget the floor rises by the excess: what is left above it is what the
        // budget would leave.
        const auto budget = world.round == world.first_round ? 2 * turn_fuel : turn_fuel;
        const auto floor = aph::end_reserve + (start > budget ? start - budget : 0);
        const auto room = [&] { return aph::fuel_ok(floor + tile_reserve); };
        if (!room()) return;
        if (rings.empty()) {
            rows.assign(static_cast<std::size_t>(2 * H), 0), cols.assign(static_cast<std::size_t>(2 * W), 0);
            rings.assign(static_cast<std::size_t>(W * H), 0);
        }
        const auto fill = [&](int x, int y) {
            if (!room()) return false;
            if (!aph::test(map.walls, {x, y})) aph::warm_tile(world, {x, y});
            rows[static_cast<std::size_t>(2 * y + (x >> 6))] |= std::uint64_t{1} << (x & 63);
            cols[static_cast<std::size_t>(2 * x + (y >> 6))] |= std::uint64_t{1} << (y & 63);
            return true;
        };
        const auto around = [&](aph::vec2 c, int radius) {
            auto& done = rings[static_cast<std::size_t>(c.x + c.y * W)];
            for (int r = done; r <= radius; ++r) {
                const int x0 = std::max(0, c.x - r), x1 = std::min(W - 1, c.x + r);
                const int y0 = std::max(0, c.y - r + 1), y1 = std::min(H - 1, c.y + r - 1);
                while (true) {
                    int x = -1, y = -1;
                    for (const int row : {c.y - r, c.y + r})
                        if (x < 0 && row >= 0 && row < H) {
                            x = first_clear(&rows[static_cast<std::size_t>(2 * row)], x0, x1);
                            y = row;
                        }
                    for (const int col : {c.x - r, c.x + r})
                        if (x < 0 && col >= 0 && col < W && y0 <= y1) {
                            y = first_clear(&cols[static_cast<std::size_t>(2 * col)], y0, y1);
                            x = y < 0 ? -1 : col;
                        }
                    if (x < 0) break;
                    if (!fill(x, y)) return false;
                }
                done = static_cast<std::uint8_t>(r + 1);
            }
            return true;
        };
        const auto& me = world.me();
        if (me.alive)
            for (const auto& e : world.enemies)
                if (e.alive && e.visible && !around(e.pos, 2)) return;
        // Next turn's farm weighs nearly every group, and the first turn read only a few groups' enemy steps.
        if (world.round == world.first_round) map.warm_enemy_steps(floor);
        // Only a turn-end ward reads it, and until it is made that tests a square around us instead.
        if (!map.near_bushes_ready() && room()) (void)map.near_bushes();
        // ward_bushes' clusters, here and a walk on, which its own floor rarely leaves fuel for in the
        // first rounds.
        if (const auto here = aph::my_position(); !warmed_up && me.alive && here.x >= 0 && room()
            && map.find_bush_clusters(here, aph::ward_range() + 1, floor) && aph::in_bounds(memory.ward)
            && aph::test(map.bushes, memory.ward))
            (void)map.find_bush_clusters(memory.ward, 0, floor);
        aph::prepare_next_turn(world, pathing, memory, floor);
        if (world.is_stale()) return;
        map.warm_drafted_steps(floor);
        aph::FuelMeter meter{"warm_up"};
        // Field costs are estimated from the deepest field so far; on the first turn none is
        // measured yet, so an estimate can miss by a whole field.
        const auto reserve = floor + (world.round == world.first_round ? aph::field_cost_estimate() : 0);
        // The spawn field and group hops first: from the second turn every turn reads them.
        map_warmed_up = map_warmed_up || map.warm_up(reserve);
        if (!map_warmed_up) return;
        // The map-wide fields before the tables around us: a walk exposes new tiles every step, so
        // the ring rarely completes, and a decision missing a centre field builds it (~26k).
        if (!warmed_up) {
            const bool centres = pathing.warm_centres(reserve, memory.farm_group);
            warmed_up = centres && pathing.warm_up(me.facts().attack_range(), reserve) && map.find_all_bush_clusters(reserve);
            debug_block({
                if (centres && !logged_centres) std::printf("WARM %u centres\n", cambc::round_number()), logged_centres = true;
                if (warmed_up) std::printf("WARM %u done\n", cambc::round_number());
            });
            if (!warmed_up) return;
        }
        if (me.pos.x >= 0) around(me.pos, me.alive ? aph::vision_radius : 20);
    }
};

struct Instance {
    TurnEndQueue queue;
    aph::DraftState draft;
    std::unique_ptr<aph::World> world;
    std::unique_ptr<aph::Pathing> pathing;
    aph::Memory memory;

    void draft_turn() {
        run("draft", [&] { aph::play_draft(draft); });
        run("draft fallback", [&] { aph::ensure_picked(draft); });
    }

    // `late`: the turn before did not finish in its own round (aph::finish_late).
    [[gnu::flatten]] void play_turn(bool late) {
        const auto start = aph::fuel();
        aph::FuelMeter meter{"turn"};
        const bool updated = run("world", [&] {
            if (!world) world = std::make_unique<aph::World>();
            const bool first = !world->ready();
            if (!first) aph::comms::expect(*world);
            world->update();
            if (!pathing) pathing = std::make_unique<aph::Pathing>(*world);
            pathing->begin_turn();
            if (first && aph::debug_log) {
                const auto& m = world->map();
                std::printf("map %dx%d %s groups %zu altars %zu plan %s\n", m.width, m.height,
                            cambc::to_string(m.symmetry).c_str(), m.groups.size(), m.altars.size(),
                            m.drafted() ? "ok" : "missing");
            }
        });
        if (!updated || !world->ready() || world->is_stale()) return;

        run("comms receive", [&] { aph::comms::receive(*world); });
        aph::finish_late() = late;
        run("decide", [&] {
            aph::FuelMeter meter{"decide"};
            aph::play_turn(*world, *pathing, memory);
        });
        // Decided in its own round, the turn end is abandoned as usual if it runs out.
        aph::finish_late() = late && world->resumed();

        // A turn that runs out of fuel costs the next one: the rest is skipped when short.
        if (world->is_stale() || !aph::fuel_ok(late_floor)) return;
        run("turn end", [&] { world->note_turn_end(); });
        if (world->is_stale() || !aph::fuel_ok(late_floor)) return;
        // Vision changes only if we moved. Off the map, we were killed this turn: nothing to re-read.
        const auto now = aph::my_position();
        const bool moved = world->me().alive && now.x >= 0 && now != world->me().pos;
        // Observe and send cost at most ~6.3k: the reserve covers them.
        const bool refresh = moved && aph::fuel_ok(aph::end_reserve);
        run("comms send", [&] { aph::comms::send(*world, moved, refresh); });
        run("debug", [&] { world->debug_output(); });
        if (!aph::fuel_ok(late_floor)) return;
        if (!world->is_stale())
            run("queue", [&] { queue.run(*world, *pathing, memory, start); });
        aph::print_fuel_log();
    }
};

} // namespace

int main() {
    Instance instance;
    bool late = false; // the last turn did not finish in the round it began in
    while (true) {
        const auto round = aph::round_now();
        if (cambc::is_draft())
            instance.draft_turn();
        else
            instance.play_turn(late);
        const bool finished_late = std::exchange(aph::finish_late(), false);
        const auto now = aph::round_now();
        late = now != round;
        // Out of fuel, we resumed as this round's turn with a fresh budget: play it rather than end
        // it, unless the resumed turn finished its decision in it.
        if (late) {
            // A release-build line would cost the resumed turn ~2.5k.
            debug_block({
                std::printf("r%u turn ran out of fuel, finished in r%u\n", round, now);
                std::printf("OOF %u %s\n", round, aph::fuel_phase());
            });
            aph::note_shortcut("out-of-fuel");
            if (!finished_late) continue;
        }
        cambc::end_turn();
    }
}
