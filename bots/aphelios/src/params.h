#pragma once
#include <cambc.h>
#include <cstdint>
#include "util.h"

namespace aph::params {

inline constexpr cambc::champion_draft draft_preference[] = {
    cambc::champion_draft::vesper_vale, cambc::champion_draft::varg, cambc::champion_draft::tavi,
    cambc::champion_draft::ryth, cambc::champion_draft::stellar, cambc::champion_draft::ren,
    cambc::champion_draft::vendetta, cambc::champion_draft::willow, cambc::champion_draft::prism,
    cambc::champion_draft::marcella, cambc::champion_draft::cassi_and_issac,
};

// Left for the rest of the turn after optional work. Printing the debug fuel log can cost ~30k.
inline constexpr std::uint64_t end_reserve = debug_fuel ? 40000 : 10000;

// Rounds out of sight after which an enemy could be anywhere.
inline constexpr int track_horizon = 10;

// Extra steps a live route may take over the static walking distance.
inline constexpr int max_detour = 16;

inline constexpr float recall_health_fraction = 0.35f;
// Below the recall line, stay to finish a camp whose remaining damage is under this share of our health.
inline constexpr float finish_camp_health_fraction = 0.6f;
inline constexpr int ward_period = 20;

} // namespace aph::params
