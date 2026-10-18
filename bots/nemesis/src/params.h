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
// Maps with 3, 4 or 5 picks draft their own order first, then fall back to draft_preference.
inline constexpr cambc::champion_draft draft_3[] = {
    cambc::champion_draft::cassi_and_issac, cambc::champion_draft::varg, cambc::champion_draft::stellar};
inline constexpr cambc::champion_draft draft_4[] = {
    cambc::champion_draft::cassi_and_issac, cambc::champion_draft::varg, cambc::champion_draft::stellar,
    cambc::champion_draft::ryth};
inline constexpr cambc::champion_draft draft_5[] = {
    cambc::champion_draft::cassi_and_issac, cambc::champion_draft::varg, cambc::champion_draft::stellar,
    cambc::champion_draft::ryth, cambc::champion_draft::tavi};

// Left for the rest of the turn after optional work.
inline constexpr std::uint64_t end_reserve = 10000;
// Left after work whose cost is bounded, at the end of the turn: little runs after warm-up.
inline constexpr std::uint64_t last_reserve = 2000;
// Layers a capped centre field may run past the farther spawn's steps to it. Measured on 194
// maps: 15% run deeper, and the cut field is redone at twice the cap.
inline constexpr int centre_depth_margin = 24;
// A walk not prepared last turn is searched for first, leaving at least this for the turn.
inline constexpr std::uint64_t walk_first_floor = 40000;

// Rounds out of sight after which an enemy could be anywhere.
inline constexpr int track_horizon = 10;

// Extra steps a live route may take over the static walking distance.
inline constexpr int max_detour = 16;

inline constexpr float recall_health_fraction = 0.35f;
// Leave awake camps while the health still covers the walk out of their reach (bot.cpp camp_trapped).
inline constexpr bool camp_trap = true;
// Pick the camp member to hit by damage removed per hit, and Varg's by splash (bot.cpp attack_camp).
inline constexpr bool camp_targeting = true;
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
// Recall from a capture as it pays when the gold then buys an emblem, keeping the bag.
inline constexpr bool shop_recall = true;
// Champion vision: enemies farther off are seen only through wards and are rarely caught.
inline constexpr int chase_radius = 8;
// Fights last about 5 rounds (local engagements: median 4-6), so allies more than a few steps
// outside vision of one arrive after it.
inline constexpr int rally_radius = 12;
// Allies within this many steps of a damaging group a teammate attacks join it: wider pulls lost.
inline constexpr int help_radius = 8;

// Chain another capture onto a bag only below this. Top ladder teams bank bags of 66 (median) and
// our sparring partners seldom hunt carriers, so a bag can grow past one capture's worth.
inline constexpr int chain_bag_limit = 80;
// Closing (bot.cpp closing): bank when our score and the team's bags come within close_margin of
// the win, or the enemy's score within enemy_close.
inline constexpr int close_margin = 60;
inline constexpr int enemy_close = 100;
// Lock any altar where an enemy is tributing (a lock cancels every tribute at its altar).
inline constexpr bool lock_tributers = true;
// Stun an enemy tribute that would win them the game at once, cancelling ours if need be.
inline constexpr bool stop_winning_tribute = true;

// Early retreat (outmatched): enemies this near against allies this near; leave when their health
// times damage beats ours by this ratio. Top teams ignore the numbers unless below half health or
// carrying brake_bag gems, so the healthy, light ratio never triggers.
inline constexpr int pack_radius = 7;
inline constexpr int pack_ally_radius = 5;
inline constexpr float retreat_ratio = 100.0f;
inline constexpr float hurt_retreat_ratio = 2.5f;
inline constexpr int brake_bag = 30;
// In our own half, give way to packs at this ratio: an enemy pack there has come to fight, and met
// piecemeal it won most fights (small maps against aphelios: 74% -> 82% of games).
inline constexpr bool home_retreat = true;
inline constexpr float home_retreat_ratio = 2.0f;
// A capture recall still pays when hurt if it costs at most this many more rounds to an altar.
inline constexpr int recall_heal_bonus = 6;
// Ladder teams wait at a camp about to return (2-3% of their time), never for long. Waits of 6-10
// rounds lost 4-5% of games to going elsewhere (2026-10-17, 712 games against rival).
inline constexpr int max_wait = 5;
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
// Wait this near (out of its reach) until this share of the team's output has come, at most this long.
inline constexpr int siege_stage_radius = 5;
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
// Choose the siege target by walk and respawn wait, keeping the current one unless another is
// sooner by this many rounds (bot.cpp siege_candidate).
inline constexpr bool siege_sticky = true;
inline constexpr int siege_stickiness = 20;

} // namespace aph::params
