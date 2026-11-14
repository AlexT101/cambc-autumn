#pragma once
// Which known priority encoding a visible enemy's value matches (no SDK use: a native test builds it).
#include <algorithm>
#include <cmath>
#include <cstdint>
#include <cstdlib>

namespace aph::opp {

enum Token { zero, fish_quiet, fish_contact, fish_mod, res_same, mite_quiet, mite_near, mite_chan, mite_contact, mite_offset, other };

// n: enemy bodies; rank: Fish's rank of this one (2 + place by base health); res0: residue of its
// first counted nonzero value, -1 none; tank: Heart of Ruin or Marcella.
inline Token token(std::int32_t v, int n, int rank, int res0, bool tank, double hp, double max_hp, double shield, int gems) {
    if (v == 0) return zero;
    const std::int64_t n1 = n + 1;
    const std::int64_t res = ((-static_cast<std::int64_t>(v)) % n1 + n1) % n1;
    const bool fish = res == rank % n1;
    if (fish) {
        // Fish: v = -rank - (N+1) * level, so this divides.
        const std::int64_t level = (-static_cast<std::int64_t>(v) - rank) / n1;
        double h = max_hp > 0 ? std::fmin(1.0, (hp + shield) / max_hp) : 1.0;
        if (gems > 0) h *= 0.65;
        const std::int64_t band = std::max<std::int64_t>(0, static_cast<std::int64_t>(std::floor(4 * (1 - h))));
        // Health read after the write can be lower (one band up) than when Fish wrote it.
        if (level >= 0 && ((band - 1 <= level && level <= band) || (band + 4 <= level && level <= band + 5))) return fish_quiet;
        if ((99 <= level && level <= 116) || (-117 <= level && level <= -101)) return fish_contact;
    }
    const double f = max_hp > 0 ? hp / max_hp : 1.0;
    const std::int64_t q1 = 1000 + static_cast<std::int64_t>(std::floor(20 * f));
    const std::int64_t q2 = tank ? 1025 + static_cast<std::int64_t>(std::floor(24 * f)) : q1;
    if (v == q1 || v == q2) return mite_quiet;
    if (v == 18965) return mite_chan;
    if (1000 <= v && v <= 1049 && (std::llabs(v - q1) <= 2 || std::llabs(v - q2) <= 2)) return mite_near;
    if (90 <= v && v <= 100) return mite_contact;
    for (const std::int64_t off : {2000, 3000, 5000, 6460, 7460, 9460})
        if (90 <= v - off && v - off <= 100) return mite_offset;
    if (fish) return fish_mod;
    if (res0 >= 0 && res == res0 && res != 0) return res_same;
    return other;
}

} // namespace aph::opp
