// probe-hostcall-fuel: where a turn stops when a host call spends the last of its fuel.
// Run at the default fuel:
//   cambc run tools/probes/probe-hostcall-fuel tools/probes/probe-hostcall-fuel --map 00ambush --rounds 10 -o DIR
// The ally with the lowest id (S) logs every turn start. In round 5 it burns fuel until fewer than LEFT remain,
// then makes one host call priced above LEFT (a radius-8 shadow cast), then, with no wasm function entry or loop
// in between, raw imports only: round_number ("before_round"), the move, round_number ("move_round"). Its next
// log prints those rounds, the fuel left before the crossing step (f0), the move's result and its position.
// MODE 1 instead crosses the budget in straight-line guest code (no host call) before those imports.
// Round 4 prints the prices.
#include <cambc.h>
#include <algorithm>
#include <cstdint>
#include <cstdio>
#include <vector>

#ifndef LEFT
#define LEFT 100
#endif
#ifndef MODE
#define MODE 0
#endif

static volatile std::uint32_t g_before_round = 0, g_move_round = 0;
static volatile std::int32_t g_move_ok = -1, g_move_status = -1;
static volatile std::int64_t g_f0 = 0;

int main() {
    while (true) {
        if (!cambc::is_draft()) {
            try {
                auto& me = cambc::self();
                std::vector<unsigned> ids;
                for (auto& c : cambc::champions(cambc::team::ally)) ids.push_back(static_cast<unsigned>(static_cast<cambc::handle_champion_t>(c)));
                std::sort(ids.begin(), ids.end());
                const unsigned id = static_cast<unsigned>(static_cast<cambc::handle_champion_t>(me));
                const int k = static_cast<int>(std::find(ids.begin(), ids.end(), id) - ids.begin());
                const auto r = cambc::round_number();
                const auto p = me.position();
                if (k == 0) {
                    std::printf("PROBE %u S start pos=%d,%d fuel=%lld f0=%lld before_round=%u move_round=%u ok=%d status=%d\n", r,
                                p.x, p.y, static_cast<long long>(cambc::detail::sdk_fuel_remaining()),
                                static_cast<long long>(g_f0), g_before_round, g_move_round, static_cast<int>(g_move_ok),
                                static_cast<int>(g_move_status));
                }
                if (k == 0 && r == 4) {
                    // Prices: each difference includes one fuel_remaining() call.
                    cambc::bitboard walls = cambc::map::walls();
                    cambc::bitboard sight;
                    volatile std::uint64_t x = 0;
                    std::uint32_t now = 0;
                    const std::int64_t a0 = cambc::detail::sdk_fuel_remaining();
                    cambc::detail::sdk_Bitboard_ShadowCast(walls.ptr(), p.x, p.y, sight.ptr(), 8);
                    const std::int64_t a1 = cambc::detail::sdk_fuel_remaining();
                    cambc::detail::sdk_bc_round_number(&now);
                    const std::int64_t a2 = cambc::detail::sdk_fuel_remaining();
#define R4 x = x * 3 + 1; x = x * 3 + 1; x = x * 3 + 1; x = x * 3 + 1;
#define R16 R4 R4 R4 R4
#define R64 R16 R16 R16 R16
                    R64 R64 R64 R64
                    const std::int64_t a3 = cambc::detail::sdk_fuel_remaining();
                    std::printf("PROBE %u S price shadow_cast=%lld round_number=%lld block=%lld\n", r,
                                static_cast<long long>(a0 - a1), static_cast<long long>(a1 - a2),
                                static_cast<long long>(a2 - a3));
                }
                if (k == 0 && r == 5) {
                    // A free neighbour off spawn is not needed: walking within spawn is allowed. Pick any tile the SDK accepts.
                    cambc::vec2 dst = p;
                    const cambc::vec2 deltas[8] = {{1, 0}, {-1, 0}, {0, 1}, {0, -1}, {1, 1}, {-1, -1}, {1, -1}, {-1, 1}};
                    for (auto d : deltas) {
                        const cambc::vec2 q = p + d;
                        if (q.x < 0 || q.y < 0 || q.x >= cambc::map::width() || q.y >= cambc::map::height()) continue;
                        if (cambc::map::walls().is_set(q) || cambc::map::holes().is_set(q)) continue;
                        if (cambc::map::altars().is_set(q)) continue;
                        bool occupied = false;
                        for (auto& c : cambc::champions(cambc::team::ally))
                            if (c.position() == q) occupied = true;
                        if (occupied) continue;
                        dst = q;
                        break;
                    }
                    std::printf("PROBE %u S target=%d,%d\n", r, dst.x, dst.y);
                    cambc::bitboard walls = cambc::map::walls();
                    cambc::bitboard sight;
                    volatile std::uint64_t x = 0;
                    std::int32_t ok = 0;
                    std::uint32_t now = 0;
#if MODE == 0
                    while ((g_f0 = cambc::detail::sdk_fuel_remaining()) >= LEFT) x = x * 6364136223846793005ULL + 1;
                    cambc::detail::sdk_Bitboard_ShadowCast(walls.ptr(), p.x, p.y, sight.ptr(), 8);
#else
                    while ((g_f0 = cambc::detail::sdk_fuel_remaining()) >= 200) x = x * 6364136223846793005ULL + 1;
                    // Straight-line guest code with no call or loop, priced in round 4's "block": crosses the budget.
                    R64 R64 R64 R64
#endif
                    cambc::detail::sdk_bc_round_number(&now);
                    g_before_round = now;
                    const std::int32_t st = cambc::detail::sdk_move_to(dst.x, dst.y, &ok);
                    cambc::detail::sdk_bc_round_number(&now);
                    g_move_status = st;
                    g_move_ok = ok;
                    g_move_round = now;
                }
            } catch (const cambc::error&) {
                std::printf("PROBE error\n");
            }
        }
        cambc::end_turn();
    }
}
