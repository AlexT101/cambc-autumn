#pragma once
#include <cambc.h>

namespace aph::params {

// The fallback order: for pick counts without a table, and once every pick of the chosen draft is
// rejected (draft.cc ensure_picked).
inline constexpr cambc::champion_draft draft_preference[] = {
    cambc::champion_draft::prism,
    cambc::champion_draft::vendetta,
    cambc::champion_draft::cassi_and_issac,
    cambc::champion_draft::heart_of_ruin,
    cambc::champion_draft::marcella,
    cambc::champion_draft::ryth,
    cambc::champion_draft::stellar,
    cambc::champion_draft::willow,
    cambc::champion_draft::varg,
    cambc::champion_draft::ren,
    cambc::champion_draft::tavi,
};
// true: the draft comes from the draft lab's model of the map (draft.cc model_draft, data in
// draft_model.h). false, or where the model fails: the tables below.
constexpr bool map_model_draft = true;
// The draft off the model, by pick count, in pick order. Off the model Vesper Vale is never drafted
// (draft.cc vesper_allowed), and on 3-pick maps whose gold lies in pure-gold groups
// (MapEconomy::tavi_map) draft.cc choose_table_draft drafts Tavi instead.
inline constexpr cambc::champion_draft draft_three[] = {
    cambc::champion_draft::marcella,
    cambc::champion_draft::vendetta,
    cambc::champion_draft::heart_of_ruin,
};
inline constexpr cambc::champion_draft draft_four[] = {
    cambc::champion_draft::prism,
    cambc::champion_draft::vendetta,
    cambc::champion_draft::marcella,
    cambc::champion_draft::heart_of_ruin,
};
inline constexpr cambc::champion_draft draft_five[] = {
    cambc::champion_draft::prism,
    cambc::champion_draft::vendetta,
    cambc::champion_draft::marcella,
    cambc::champion_draft::willow,
    cambc::champion_draft::heart_of_ruin,
};
// Test copies only (tools/ab.py): draft a common ladder composition chosen by the map and side
// (draft.cc test_compositions) instead of the model or the tables.
constexpr bool test_draft = false;
// tools/draftlab/parity.py's copies only: print the model draft's features and team in draft round 0
// (debug builds), to compare with features.mjs and model.mjs.
constexpr bool draft_parity = false;

// Rounds out of sight after which an enemy could be anywhere.
inline constexpr int track_horizon = 10;

// Below this share of max health a champion goes home; camps may cost only the health above it.
// This is the line while an enemy threatens us (fight.cc recall_line); safe_recall_health_fraction otherwise.
inline constexpr float recall_health_fraction = 0.35f;
// The recall line while no enemy can credibly reach us within threat_radius steps.
inline constexpr float safe_recall_health_fraction = 0.18f;
// recall_line: steps past an enemy's reach within which it threatens us.
inline constexpr int threat_radius = 6;
// The draft's fixed recall line for usable health (draft.cc type_facts).
inline constexpr float draft_recall_health_fraction = 0.35f;
// Below this share of max health a champion, ours or an enemy, is hurt: ours retreat from smaller
// packs, no longer count their own ground as safe from pursuit, and are healed for any gain.
inline constexpr float hurt_health_fraction = 0.5f;
// Below the recall line, stay to finish a camp whose remaining damage is under this share of our health.
inline constexpr float finish_camp_health_fraction = 0.6f;
// Camp damage counted against the health we can spare when choosing a camp (below 1: bolder).
inline constexpr float camp_risk = 0.35f;
// Enemy-ground discount: a group's weight is min(1, 2 d_enemy / (d_ally + d_enemy)) to this power.
inline constexpr float home_power = 2.0f;
// An ally this near with no claim of its own can partner on a group too costly for us alone.
inline constexpr int partner_radius = 12;
// Help a struggling teammate clear its damaging group within this many steps.
inline constexpr int help_radius = 8;
// farm's pick_up: take over a group cleared this turn within this many tiles of its nearest member.
inline constexpr int pick_up_radius = 4;

// Chain another capture onto a bag (Cassi's and Issac's together) only below this.
inline constexpr int chain_bag_limit = 45;

// Early retreat (combat/guard.cc outmatched): enemies within two steps of their reach against
// allies this near. When hurt (under hurt_health_fraction, or carrying brake_bag gems or more),
// leave when their health times damage beats ours by hurt_retreat_ratio. Healthy outside our own
// half, no pack sends us back early.
inline constexpr int pack_ally_radius = 5;
inline constexpr float hurt_retreat_ratio = 2.5f;
// A bag this big (a tribute of two turns or more) is worth chasing: it counts as hurt above, and
// makes our own ground no refuge from pursuit.
inline constexpr int brake_bag = 11;
// In our own half, give way to packs at this ratio: an enemy pack there has come to fight.
inline constexpr float home_retreat_ratio = 2.0f;
// Leave before contact when the visible enemies within this many steps of their reach would win
// even if we struck first (Safety::stand). At most 3: Safety::late packs it in 2 bits.
inline constexpr int pursuit_steps = 3;
// Below this share of max health a sieger out of the besieged group's reach goes home to heal,
// and a caster stops staging at spell range.
inline constexpr float heal_trip_fraction = 0.6f;
// Turns ahead a tribute's safety is judged over, each turn of the channel.
inline constexpr int tribute_window = 6;
// Most rounds to wait at a camp for it to return.
inline constexpr int max_wait = 5;
// The weight on gold in farm choice of Cassi, and of Tavi on its gold maps (MapEconomy::tavi_map):
// they take the gold-only groups the others pass up.
inline constexpr float gold_farmer_weight = 4.0f;
// Gold's price in farm choices (prices().per_gold), scaled: we earn less gold than top teams. The learned
// emblems (economy/emblem_table.h) were learned at 1.5.
inline constexpr float gold_price_scale = 1.5f;

// Sieges (economy/siege.cc) of a Monolith on Monolith-only maps, of one the enemy is sieging, or of
// a group sealing the altars. The team goes once its output clears the group within siege_rounds
// and the hits it takes meanwhile, siege_hit_share of them landing (stuns, spells from out of
// reach), cost at most siege_pool_share of the team's max health (unchecked while the enemy is in
// the group's reach); a siege under way keeps going within siege_commit_slack of both.
inline constexpr int siege_rounds = 60;
inline constexpr float siege_hit_share = 0.75f;
inline constexpr float siege_pool_share = 0.6f;
inline constexpr float siege_commit_slack = 1.3f;
// Skip a siege target that returns later than this.
inline constexpr int siege_respawn_wait = 30;
// Off Monolith-only maps, a live Monolith the team clears within this many rounds at its known
// health is sieged too: one left alone that weak is the enemy's for a burst.
inline constexpr int burst_rounds = 20;
// Wait just out of reach until this share of the team's output has come, at most this long.
inline constexpr float siege_gather_share = 0.6f;
inline constexpr int siege_max_wait = 20;
// Big groups: at least this many gems, Monoliths aside. Maps whose only gems are big groups and
// Monoliths are kited (economy/siege.cc kite).
inline constexpr int big_gems = 55;
// Most holders a capture is split over (economy/capture.cc holders).
inline constexpr int big_holders = 3;
// Kiting: set out for a big group still respawning when it returns within this many rounds of our arrival.
inline constexpr int kite_early = 10;
// Keep the current siege target unless another is sooner by this many rounds.
inline constexpr int siege_stickiness = 20;

// Values in enemy health points: a champion's life over its health, each gem it carries, a stopped
// tribute (besides its gems) and a cancelled recall or teleport. turn_order.cc's rank codes fix
// them modulo 15 (static_assert there).
inline constexpr float life_value = 300;
inline constexpr float gem_value = 15;
inline constexpr float tribute_value = 100;
inline constexpr float recall_value = 60;
// Each point of damage short of a kill is worth this much of itself; the rest of the kill's worth
// comes as the target weakens (kill_distance).
inline constexpr float chip_value = 0.4f;

} // namespace aph::params
