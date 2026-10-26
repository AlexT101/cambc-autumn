// probe-memory: the engine's WASM linear-memory cap, and whether a bot with 2 MiB more static
// memory (astraeus's allocation arena) starts. Run:
//   cambc run tools/probes/probe-memory tools/probes/probe-memory --map 00corners --rounds 3 --fuel 50000000 -o <dir>
// Round 1 prints the initial memory (64 KiB pages, the 2 MiB array included), then grows a page at
// a time until memory.grow fails or 65536 pages (4 GiB) are reached, and prints the last size and
// the fuel a grow costs. Round 2 checks the grown memory is still there.
#include <cambc.h>
#include <cstddef>
#include <cstdint>
#include <cstdio>

namespace {
alignas(16) std::byte arena[std::size_t{2} << 20];
std::size_t top_pages = 0;

void grow_all() {
    const std::size_t start = __builtin_wasm_memory_size(0);
    arena[0] = std::byte{1};
    arena[sizeof(arena) - 1] = std::byte{2};
    std::printf("PROBE %u start pages=%zu bytes=%zu arena_end=%zu\n", cambc::round_number(), start, start * 65536,
                reinterpret_cast<std::size_t>(arena) + sizeof(arena));
    std::uint64_t fuel_first = 0, fuel_total = 0;
    std::size_t grows = 0;
    while (__builtin_wasm_memory_size(0) < 65536) {
        const auto a = cambc::fuel_remaining();
        const auto r = __builtin_wasm_memory_grow(0, 16); // 1 MiB a step
        const auto b = cambc::fuel_remaining();
        if (r == static_cast<std::size_t>(-1)) break;
        if (grows == 0) fuel_first = a - b;
        fuel_total += a - b;
        ++grows;
    }
    top_pages = __builtin_wasm_memory_size(0);
    std::printf("PROBE %u top pages=%zu MiB=%zu grows=%zu fuel_first=%llu fuel_mean=%.1f\n", cambc::round_number(), top_pages,
                top_pages / 16, grows, static_cast<unsigned long long>(fuel_first),
                grows ? static_cast<double>(fuel_total) / static_cast<double>(grows) : 0.0);
    // Touch the last page.
    auto* last = reinterpret_cast<volatile std::uint8_t*>(top_pages * 65536 - 1);
    *last = 7;
}

void draft_turn() {
    const auto ally = cambc::draft::current_draft(cambc::team::ally);
    for (int i = 0; i < 11; ++i) {
        const auto pick = static_cast<cambc::champion_draft>(i);
        bool taken = false;
        for (auto a : ally) taken |= a == pick;
        if (!taken) {
            cambc::draft::pick(pick);
            return;
        }
    }
}
} // namespace

int main() {
    while (true) {
        try {
            if (cambc::is_draft()) draft_turn();
            else if (cambc::round_number() <= 1 && top_pages == 0) grow_all();
            else if (top_pages != 0)
                std::printf("PROBE %u still pages=%zu last=%u arena0=%d\n", cambc::round_number(), static_cast<std::size_t>(__builtin_wasm_memory_size(0)),
                            static_cast<unsigned>(*reinterpret_cast<volatile std::uint8_t*>(top_pages * 65536 - 1)), static_cast<int>(arena[0])), top_pages = 0;
        } catch (const std::exception& e) {
            std::printf("PROBE err %s\n", e.what());
        }
        cambc::end_turn();
    }
}
