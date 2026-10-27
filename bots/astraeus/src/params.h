#pragma once
#include <cambc.h>

namespace aph::params {

inline constexpr cambc::champion_draft draft_preference[] = {
    cambc::champion_draft::prism,
    cambc::champion_draft::vesper_vale,
    cambc::champion_draft::heart_of_ruin,
    cambc::champion_draft::marcella,
    cambc::champion_draft::ryth,
    cambc::champion_draft::stellar,
    cambc::champion_draft::willow,
    cambc::champion_draft::cassi_and_issac,
    cambc::champion_draft::varg,
    cambc::champion_draft::ren,
    cambc::champion_draft::vendetta,
    cambc::champion_draft::tavi,
};
// The draft on maps of each pick count, in pick order; draft_preference fills in after a rejected pick.
inline constexpr cambc::champion_draft draft_three[] = {
    cambc::champion_draft::marcella,
    cambc::champion_draft::vendetta,
    cambc::champion_draft::heart_of_ruin,
};
inline constexpr cambc::champion_draft draft_four[] = {
    cambc::champion_draft::prism,
    cambc::champion_draft::vesper_vale,
    cambc::champion_draft::marcella,
    cambc::champion_draft::heart_of_ruin,
};
inline constexpr cambc::champion_draft draft_five[] = {
    cambc::champion_draft::prism,
    cambc::champion_draft::vesper_vale,
    cambc::champion_draft::marcella,
    cambc::champion_draft::willow,
    cambc::champion_draft::heart_of_ruin,
};
// Test copies only (tools/ab.py): draft a common ladder composition chosen by the map and side
// (draft.cpp test_compositions) instead of the tables above.
constexpr bool test_draft = false;

// Rounds out of sight after which an enemy could be anywhere.
inline constexpr int track_horizon = 10;

inline constexpr float recall_health_fraction = 0.35f;
// Below this share of max health a champion is hurt: it retreats from smaller packs, and on its
// own ground it still checks whether a pursuit would catch it.
inline constexpr float hurt_health_fraction = 0.5f;
// Below the recall line, stay to finish a camp whose remaining damage is under this share of our health.
inline constexpr float finish_camp_health_fraction = 0.6f;
// Camp damage counted against the health we can spare when choosing a camp (below 1: bolder).
// Unrelated to recall_health_fraction, though both are 0.35.
inline constexpr float camp_risk = 0.35f;
// Enemy-ground discount: a group's weight is min(1, 2 d_enemy / (d_ally + d_enemy)) to this power.
inline constexpr float home_power = 2.0f;
// An ally this near with no claim of its own can partner on a group too costly for us alone.
inline constexpr int partner_radius = 12;
// Help a struggling teammate clear its damaging group within this many steps.
inline constexpr int help_radius = 8;

// Chain another capture onto a bag (Cassi's and Issac's together) only below this.
inline constexpr int chain_bag_limit = 45;

// Early retreat (outmatched): enemies within two steps of their reach against allies this near;
// when hurt (below half health, or carrying brake_bag gems or more), leave when their health times
// damage beats ours by this ratio. Healthy outside our own half, no pack sends us back early.
inline constexpr int pack_ally_radius = 5;
inline constexpr float hurt_retreat_ratio = 2.5f;
inline constexpr int brake_bag = 11;
// In our own half, give way to packs at this ratio: an enemy pack there has come to fight.
inline constexpr float home_retreat_ratio = 2.0f;
// Leave before contact when the visible enemies within this many steps of their reach would win
// even if we struck first (Safety::stand).
inline constexpr int pursuit_steps = 3;
// Below this health a sieger out of the besieged group's reach recalls, and a caster stages farther.
inline constexpr float heal_trip_fraction = 0.6f;
// Turns ahead a tribute's safety is judged over, each turn of the channel.
inline constexpr int tribute_window = 6;
// Most rounds to wait at a camp for it to return.
inline constexpr int max_wait = 5;
// Cassi's weight on gold in farm choice: it takes the gold-only groups the others pass up.
inline constexpr float gold_farmer_weight = 4.0f;

// Sieges (bot.cpp siege) of a Monolith on maps whose only gems are Monoliths, of one the enemy is
// sieging (no health-pool check while they are in its reach), or of a group sealing
// the altars: the team goes once its output clears the group within this many rounds and the hits, by this share after stuns
// and spells from out of reach, cost at most this share of the team's health; a siege under way
// keeps going within the slack.
inline constexpr int siege_rounds = 60;
inline constexpr float siege_hit_share = 0.75f;
inline constexpr float siege_pool_share = 0.6f;
inline constexpr float siege_commit_slack = 1.3f;
inline constexpr int siege_respawn_wait = 30;
// Off Monolith-only maps, a live Monolith the team clears within this many rounds at its known
// health is sieged (about one ladder solo chip visit): below it, a Monolith left alone is the
// enemy's for a burst.
inline constexpr int burst_rounds = 20;
// Wait just out of reach until this share of the team's output has come, at most this long.
inline constexpr float siege_gather_share = 0.6f;
inline constexpr int siege_max_wait = 20;
// Big groups: at least this many gems. Maps whose only gems are big groups and Monoliths are kited
// (bot.cpp kite).
inline constexpr int big_gems = 55;
// Most holders a capture is split over (bot.cpp holders).
inline constexpr int big_holders = 3;
// On maps whose only gems are big groups (bot.cpp kite): set out for one still respawning when
// it returns within this many rounds of our arrival.
inline constexpr int kite_early = 10;
// Keep the current siege target unless another is sooner by this many rounds (bot.cpp siege_candidate).
inline constexpr int siege_stickiness = 20;

// Values in enemy health points: a champion's life over its health, each gem it carries, a stopped
// tribute (besides its gems) and a cancelled recall.
inline constexpr float life_value = 300;
inline constexpr float gem_value = 15;
inline constexpr float tribute_value = 100;
inline constexpr float recall_value = 60;
// Each point of damage short of a kill is worth this much of itself; the rest of the kill's worth
// comes as the target weakens (kill_distance).
inline constexpr float chip_value = 0.4f;

} // namespace aph::params
