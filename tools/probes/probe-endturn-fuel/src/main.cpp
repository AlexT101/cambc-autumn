// probe-endturn-fuel: a turn that runs out of fuel inside end_turn.
// Run at the default fuel:
//   cambc run tools/probes/probe-endturn-fuel tools/probes/probe-endturn-fuel --map 00ambush --rounds 12 -o DIR
// The ally with the lowest id (S) logs every turn start ("PROBE <round> S start"). In round 5 it burns
// fuel until fewer than LEFT remain, then calls end_turn. The next ally (C) logs every turn as a control.
#include <cambc.h>
#include <algorithm>
#include <cstdint>
#include <cstdio>
#include <vector>

#ifndef LEFT
#define LEFT 3
#endif

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
                if (k <= 1) std::printf("PROBE %u %s start\n", r, k == 0 ? "S" : "C");
                if (k == 0 && r == 5) {
                    volatile std::uint64_t x = 0;
                    std::uint32_t now = r;
                    while (cambc::detail::sdk_fuel_remaining() >= LEFT && now == r) {
                        x = x * 6364136223846793005ULL + 1;
                        cambc::detail::sdk_bc_round_number(&now);
                    }
                    if (now != r) std::printf("PROBE %u S ran_out_in_loop\n", now);
                }
            } catch (const cambc::error&) {
                std::printf("PROBE error\n");
            }
        }
        cambc::end_turn();
    }
}
