#pragma once
#include <cambc.h>
#include <cstdint>
#include "util.h"

namespace aph::params {

inline constexpr cambc::champion_draft draft_preference[] = {
    cambc::champion_draft::ren, cambc::champion_draft::stellar, cambc::champion_draft::cassi_and_issac,
    cambc::champion_draft::ryth, cambc::champion_draft::varg, cambc::champion_draft::prism,
    cambc::champion_draft::vesper_vale, cambc::champion_draft::vendetta, cambc::champion_draft::marcella,
    cambc::champion_draft::willow, cambc::champion_draft::tavi,
};

// Rounds out of sight after which an enemy could be anywhere.
inline constexpr int track_horizon = 10;

inline constexpr float recall_health_fraction = 0.35f;
// Below the recall line, stay to finish a camp whose remaining damage is under this share of our health.
inline constexpr float finish_camp_health_fraction = 0.6f;
// Camp damage counted against the health we can spare when choosing a camp (below 1: bolder).
inline constexpr float camp_risk = 0.35f;
// Enemy-ground discount: a group's weight is min(1, 2 d_enemy / (d_ally + d_enemy)) to this power.
inline constexpr float home_power = 2.0f;
inline constexpr int ward_period = 20;
// An ally this near with no claim of its own can partner on a group too costly for us alone.
inline constexpr int rally_radius = 12;
// Help a struggling teammate clear its damaging group within this many steps.
inline constexpr int help_radius = 8;

// Chain another capture onto a bag (Cassi's and Issac's together) only below this.
inline constexpr int chain_bag_limit = 80;
// Closing (bot.cpp closing): bank when our score and the team's bags come within close_margin of
// the win, or the enemy's score within enemy_close.
inline constexpr int close_margin = 60;
inline constexpr int enemy_close = 100;

// Early retreat (outmatched): enemies within two steps of their reach against allies this near;
// leave when their health times damage beats ours by this ratio. Above half health and carrying
// under brake_bag gems, the ratio is too high to trigger.
inline constexpr int pack_ally_radius = 5;
inline constexpr float retreat_ratio = 100.0f;
inline constexpr float hurt_retreat_ratio = 2.5f;
inline constexpr int brake_bag = 30;
// In our own half, give way to packs at this ratio: an enemy pack there has come to fight.
inline constexpr float home_retreat_ratio = 2.0f;
// Leave before contact when the visible enemies within this many steps of their reach would win
// even if we struck first (Safety::pursuit).
inline constexpr int pursuit_steps = 3;
// A capture recall still pays when hurt if it costs at most this many more rounds to an altar.
inline constexpr int recall_heal_bonus = 6;
// Below this health a shopping trip also heals, and goes whatever the emblem is worth.
inline constexpr float shop_heal_fraction = 0.6f;
// Turns ahead a tribute's safety is judged over, each turn of the channel.
inline constexpr int tribute_window = 6;
// Most rounds to wait at a camp for it to return.
inline constexpr int max_wait = 5;
// Share of champion-rounds spent attacking camps: the part of the game a shard's speed-up counts for.
inline constexpr float clear_share = 0.15f;
// Cassi's weight on gold in farm choice: it takes the gold-only groups the others pass up.
inline constexpr float gold_farmer_weight = 4.0f;

// Monolith sieges (bot.cpp siege), only on maps whose only gems are Monoliths: the team goes once
// its output clears the Monolith within this many rounds and the hits, by this share after stuns
// and spells from out of reach, cost at most this share of the team's health; a siege under way
// keeps going within the slack.
inline constexpr int siege_rounds = 60;
inline constexpr float siege_hit_share = 0.75f;
inline constexpr float siege_pool_share = 0.6f;
inline constexpr float siege_commit_slack = 1.3f;
inline constexpr int siege_respawn_wait = 30;
// Wait just out of reach until this share of the team's output has come, at most this long.
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
// A Monolith's 200 gems split over this many holders: one bag takes a 20-turn tribute.
inline constexpr int monolith_holders = 2;
// On maps whose only gems are big groups (bot.cpp kite): set out for one still respawning when
// it returns within this many rounds of our arrival.
inline constexpr int kite_early = 10;
// Groups worth stepping onto to stop an enemy capture (bot.cpp contest_capture).
inline constexpr int contest_gems = 40;
// Keep the current siege target unless another is sooner by this many rounds (bot.cpp siege_candidate).
inline constexpr int siege_stickiness = 20;
// Escorts (bot.cpp await_escort, escort): a bag (Cassi's and Issac's together) of at least
// escort_bag gems sets out for an altar, and tributes, only with escort_count allies within
// escort_radius, waiting for them at most escort_max_wait rounds a bag. Allies within escort_reach,
// seen within escort_horizon rounds, come to it.
inline constexpr int escort_bag = 150;
inline constexpr int escort_count = 2;
inline constexpr int escort_radius = 5;
inline constexpr int escort_reach = 18;
inline constexpr int escort_horizon = 20;
inline constexpr int escort_max_wait = 20;

} // namespace aph::params
