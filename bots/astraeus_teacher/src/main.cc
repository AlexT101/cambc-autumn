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
#include "model/enemy_reach.h"
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

struct Instance {
    aph::DraftState draft;
    std::unique_ptr<aph::World> world;
    std::unique_ptr<aph::Pathing> pathing;
    aph::Memory memory;

    void draft_turn() {
        run("draft", [&] { aph::play_draft(draft); });
        run("draft fallback", [&] { aph::ensure_picked(draft); });
    }

    // `late`: the turn before did not finish in its own round, or this is the first (aph::finish_late).
    [[gnu::flatten]] void play_turn(bool late) {
        aph::FuelMeter meter{"turn"};
        const bool updated = run("world", [&] {
            // Default-initialised: make_unique's value-initialisation zeroed it first (a fuel a byte,
            // ~630), and the arena's fresh memory is already zero.
            if (!world) world = std::unique_ptr<aph::World>(new aph::World);
            const bool first = !world->ready();
            world->update();
            // Until it is made, heal trips are priced by a crow-flies bound (home_gap), and which turn
            // made it hung on what each turn's reads cost: made once, first.
            if (first && world->ready()) (void)world->map().from_ally_spawn();
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

        if (world->is_stale()) return;
        run("turn end", [&] { world->note_turn_end(); });
        if (world->is_stale()) return;
        // Vision changes only if we moved. Off the map, we were killed this turn: nothing to re-read.
        const auto now = aph::my_position();
        const bool moved = world->me().alive && now.x >= 0 && now != world->me().pos;
        const bool refresh = moved;
        run("comms send", [&] { aph::comms::send(*world, moved, refresh); });
        run("debug", [&] { world->debug_output(); });
        aph::print_fuel_log();
    }
};

} // namespace

// Constant-initialized, so it costs no start-up fuel (on main's stack, zeroing it cost ~2.5k).
constinit Instance instance;

int main() {
    // The last turn did not finish in the round it began in. True for the first: a first decision
    // that runs out finishes in the next round rather than being replayed there, which on ~100-group
    // maps (~300k against 200k) costs a single budget ~170k and runs out again.
    bool late = true;
    aph::capture_draft_memory();
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
