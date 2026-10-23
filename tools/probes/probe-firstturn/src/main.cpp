// probe-firstturn: when does a champion's first play turn end, by fuel?
// Run: cambc run tools/probes/probe-firstturn tools/probes/probe-firstturn --map expanse --rounds 4
// Every champion burns fuel on its first turn, logging fuel_remaining and round_number at each
// change of round and every 20k fuel, until the round has advanced twice or 400k fuel is gone.
#include <cambc.h>
#include <algorithm>
#include <cstdint>
#include <iostream>

namespace {

std::uint64_t F() { return cambc::fuel_remaining(); }

void burn_first_turn() {
    const auto r0 = cambc::round_number();
    auto last_round = r0;
    std::uint64_t last_f = F(), used = 0, mark = 0;
    std::cout << "PROBE first_turn_start r" << r0 << " fuel=" << last_f << std::endl;
    volatile std::uint64_t x = 0;
    for (std::uint64_t i = 0; used < 400000; ++i) {
        x = x * 6364136223846793005ULL + 1;
        if (i % 200) continue;
        const auto f = F();
        const auto r = cambc::round_number();
        used += f <= last_f ? last_f - f : 0;
        if (r != last_round || f > last_f) {
            std::cout << "PROBE round_change r" << last_round << "->r" << r << " fuel_before=" << last_f << " fuel_now=" << f
                      << " used_since_start=" << used << std::endl;
            if (r >= r0 + 2) return;
            last_round = r;
        }
        if (used >= mark) {
            std::cout << "PROBE burn r" << r << " fuel=" << f << " used=" << used << std::endl;
            mark += 20000;
        }
        last_f = f;
    }
}

int turn = 0;

} // namespace

int main() {
    while (true) {
        if (cambc::is_draft()) {
            const auto ours = cambc::draft::current_draft(cambc::team::ally);
            for (int i = 0; i < 11; ++i) {
                const auto pick = static_cast<cambc::champion_draft>(i);
                if (pick == cambc::champion_draft::cassi_and_issac || std::find(ours.begin(), ours.end(), pick) != ours.end()) continue;
                try {
                    cambc::draft::pick(pick);
                    break;
                } catch (const cambc::error&) {
                }
            }
        } else if (++turn == 1) {
            std::cout << "PROBE " << cambc::to_string(cambc::self().champion_name()) << std::endl;
            burn_first_turn();
        } else {
            std::cout << "PROBE turn r" << cambc::round_number() << " fuel=" << F() << std::endl;
        }
        cambc::end_turn();
    }
}
