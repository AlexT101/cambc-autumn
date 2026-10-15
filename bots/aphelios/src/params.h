#pragma once
#include <cambc.h>
#include <cstdint>
#include "util.h"

namespace aph::params {

// Random picks keep the bot tested with and against every champion; forced-draft variants turn it off.
inline constexpr bool random_draft = true;

inline constexpr cambc::champion_draft draft_preference[] = {
    cambc::champion_draft::cassi_and_issac, cambc::champion_draft::stellar, cambc::champion_draft::varg,
    cambc::champion_draft::ryth, cambc::champion_draft::ren, cambc::champion_draft::prism,
    cambc::champion_draft::tavi, cambc::champion_draft::marcella, cambc::champion_draft::vesper_vale,
    cambc::champion_draft::vendetta, cambc::champion_draft::willow,
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
// Bush tiles this near can hide an attacker that reaches us: ranged attacks 3, abilities 4.
inline constexpr int bush_watch_radius = 4;
// Gold for which a champion with no gems recalls to shop: one emblem.
inline constexpr unsigned shop_trip_gold = 150;
// Champion vision: enemies farther off are seen only through wards and are rarely caught.
inline constexpr int chase_radius = 8;
// Fights last about 5 rounds (local engagements: median 4-6), so allies more than a few steps
// outside vision of one arrive after it.
inline constexpr int rally_radius = 12;
// Allies within this many steps of a damaging group a teammate attacks join it: wider pulls lost.
inline constexpr int help_radius = 8;

// Chain another capture onto a bag only below this: about one capture's worth (wolf 22, gem pair
// 48), so a chain at most roughly doubles what a death would lose.
inline constexpr int chain_bag_limit = 50;

} // namespace aph::params
