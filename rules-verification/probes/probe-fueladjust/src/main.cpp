// probe-fueladjust: the debug-build import sdk_fuel_adjust(delta), as tools/fuel/cap_variant.py uses it.
// Scenario 0: a negative delta charges |delta|, but never takes the turn's spending past one --fuel
// budget (a 2x/10x first turn cannot be brought below 1x); a positive one refunds, up to the turn's
// budget; a call costs 2 (adjust_cost: reads around adjust(0), minus two back-to-back reads).
// Scenario 1: no lifetime ceiling at the real budget. Each turn one team spins down to ~5k left and
// the other charges the same through fuel_adjust; both log every 100 rounds and at each main() start
// (a second start means the engine restarted the instance after a trap).
// Scenario 2: ~30k of real work, then a charge down to ~5k left. At --fuel 100000000 every instance
// traps ("all fuel consumed") near round 1000 and restarts; at 100k-30M none does in 2000 rounds.
// Charges alone (no work), with or without a debug_block, do not trap at 100M.
// Run: cambc run rules-verification/probes/probe-fueladjust rules-verification/probes/probe-fueladjust --map 00interlock --rounds 3 --fuel 250000
//      (scenario 1: --rounds 2000, default --fuel; scenario 2: --rounds 1100 --fuel 100000000; stderr shows the traps)
#include <cambc.h>
#include <cstdio>

using cambc::detail::sdk_fuel_adjust;
using cambc::detail::sdk_fuel_remaining;

constexpr int scenario = 0;

void spin_to(std::int64_t left) {
    volatile int spin = 0;
    while (sdk_fuel_remaining() > left)
        for (int i = 0; i < 100; ++i) spin = spin + 1;
}

int main() {
    const int team = cambc::detail::sdk_my_team();
    std::printf("PROBE main start r%u team=%d draft=%d left=%lld\n", cambc::round_number(), team,
                cambc::is_draft() ? 1 : 0, (long long)sdk_fuel_remaining());
    while (true) {
        if (scenario == 0) {
            const auto a = sdk_fuel_remaining();
            const auto b = sdk_fuel_remaining();
            sdk_fuel_adjust(0);
            const auto c = sdk_fuel_remaining();
            sdk_fuel_adjust(-50000);
            const auto d = sdk_fuel_remaining();
            sdk_fuel_adjust(30000);
            const auto e = sdk_fuel_remaining();
            sdk_fuel_adjust(1000000000);
            const auto f = sdk_fuel_remaining();
            std::printf("PROBE r%u draft=%d start=%lld read_cost=%lld adjust_cost=%lld after-50000=%lld after+30000=%lld after+1e9=%lld\n",
                        cambc::round_number(), cambc::is_draft() ? 1 : 0, (long long)a, (long long)(a - b),
                        (long long)(b - c - (a - b)), (long long)d, (long long)e, (long long)f);
        } else if (!cambc::is_draft()) {
            if (cambc::round_number() % 100 == 0)
                std::printf("PROBE r%u team=%d start=%lld\n", cambc::round_number(), team, (long long)sdk_fuel_remaining());
            if (scenario == 2) spin_to(sdk_fuel_remaining() - 30000);
            if (scenario == 1 && team == 0)
                spin_to(5000);
            else
                sdk_fuel_adjust(-(sdk_fuel_remaining() - 5000));
        }
        cambc::end_turn();
    }
}
