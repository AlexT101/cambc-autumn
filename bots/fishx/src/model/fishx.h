#pragma once
// The Fish exploiter (research/ideas-2026-11-09/oppmodel/fish.md): on while the classifier's Fish share is high.
#include "opp_class.h"
#include "../params.h"
namespace aph::fishx {
inline constexpr float fish_on = 0.8f;
inline bool on(const World& world) {
    return (params::opp_fish_stub >= 0 ? params::opp_fish_stub : opp::posterior(world).fish) >= fish_on;
}
} // namespace aph::fishx
