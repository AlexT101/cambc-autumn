#pragma once
#include <cambc.h>
#include <cstdint>
#include "util.h"

namespace aph::params {

// Random picks keep the bot tested with and against every champion; forced-draft variants turn it off.
inline constexpr bool random_draft = false;

inline constexpr cambc::champion_draft draft_preference[] = {
    cambc::champion_draft::cassi_and_issac, cambc::champion_draft::varg, cambc::champion_draft::stellar,
    cambc::champion_draft::ryth, cambc::champion_draft::tavi, cambc::champion_draft::ren,
    cambc::champion_draft::prism, cambc::champion_draft::vesper_vale, cambc::champion_draft::vendetta,
    cambc::champion_draft::marcella, cambc::champion_draft::willow,
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
// Camp damage counted against the health we can spare when choosing a camp (below 1: bolder).
inline constexpr float camp_risk = 0.35f;
// Enemy-ground discount: a group's weight is min(1, 2 d_enemy / (d_ally + d_enemy)) to this power.
inline constexpr float home_power = 2.0f;
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
// Closing (bot.cpp closing): bank when our score and the team's bags come within close_margin of
// the win, or the enemy's score within enemy_close.
inline constexpr int close_margin = 60;
inline constexpr int enemy_close = 100;
// Lock any altar where an enemy is tributing (a lock cancels every tribute at its altar).
inline constexpr bool lock_tributers = true;

// Early retreat (outmatched): enemies this near against allies this near; leave when their health
// times damage beats ours by this ratio. Top teams ignore the numbers unless below half health or
// carrying brake_bag gems, so the healthy, light ratio never triggers.
inline constexpr int pack_radius = 7;
inline constexpr int pack_ally_radius = 5;
inline constexpr float retreat_ratio = 100.0f;
inline constexpr float hurt_retreat_ratio = 1.3f;
inline constexpr int brake_bag = 30;
// A capture recall still pays when hurt if it costs at most this many more rounds to an altar.
inline constexpr int recall_heal_bonus = 6;
// Ladder teams wait at a camp about to return (2-3% of their time), never for long.
inline constexpr int max_wait = 10;
// Share of champion-rounds spent attacking camps (top ladder teams: about 25%).
inline constexpr float clear_share = 0.15f;

// Monolith sieges (bot.cpp siege): the team goes once its output clears the Monolith within this
// many rounds (siege_rounds_only on maps whose only gems are Monoliths; elsewhere none, as top teams
// leave the monolith map's alone) and the hits, by this share after stuns and spells from out of
// reach, cost at most this share of its health; a siege under way keeps going within the slack.
inline constexpr int siege_rounds = 0;
inline constexpr int siege_rounds_only = 60;
inline constexpr float siege_hit_share = 0.75f;
inline constexpr float siege_pool_share = 0.6f;
inline constexpr float siege_commit_slack = 1.3f;
inline constexpr int siege_respawn_wait = 30;
// Wait out of its reach until this share of the team's output has come, at most this long.
inline constexpr float siege_gather_share = 0.6f;
inline constexpr int siege_max_wait = 20;
// Below this health a champion out of the Monolith's reach recalls to heal.
inline constexpr float siege_heal_fraction = 0.6f;
// Big groups (a shared block of elk and gem clusters) go the same way: at least this many gems,
// cleared within this many rounds, waited for through a respawn this long, split over this many
// holders.
inline constexpr int big_gems = 150;
inline constexpr int big_rounds = 50;
inline constexpr int big_respawn_wait = 60;
inline constexpr int big_holders = 3;

} // namespace aph::params
