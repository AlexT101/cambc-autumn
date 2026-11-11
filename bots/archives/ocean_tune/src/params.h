#pragma once
#include <cambc.h>
#include "tune.h"

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
inline const int& track_horizon = diana_tune.i[23];

// Below this share of max health a champion goes home; camps may cost only the health above it.
// This is the line while an enemy threatens us (fight.cc recall_line); safe_recall_health_fraction otherwise.
inline const float& recall_health_fraction = diana_tune.f[0];
// The recall line while no enemy can credibly reach us within threat_radius steps.
inline const float& safe_recall_health_fraction = diana_tune.f[1];
// recall_line: steps past an enemy's reach within which it threatens us.
inline const int& threat_radius = diana_tune.i[0];
// The draft's fixed recall line for usable health (draft.cc type_facts).
inline const float& draft_recall_health_fraction = diana_tune.f[2];
// Below this share of max health a champion, ours or an enemy, is hurt: ours retreat from smaller
// packs, no longer count their own ground as safe from pursuit, and are healed for any gain.
inline const float& hurt_health_fraction = diana_tune.f[3];
// Below the recall line, stay to finish a camp whose remaining damage is under this share of our health.
inline const float& finish_camp_health_fraction = diana_tune.f[4];
// Camp damage counted against the health we can spare when choosing a camp (below 1: bolder).
inline const float& camp_risk = diana_tune.f[5];
// Enemy-ground discount: a group's weight is min(1, 2 d_enemy / (d_ally + d_enemy)) to this power.
inline const float& home_power = diana_tune.f[6];
// An ally this near with no claim of its own can partner on a group too costly for us alone.
inline const int& partner_radius = diana_tune.i[1];
// Crews on strong groups (economy/crew.cc): allies in sight this near a group's centre, free or on
// harmless or cleared groups within crew_near_radius of it, are expected to join an operation on it;
// crews of at most crew_cap. Each member scores as tank by its health above crew_tank_line.
inline const int& crew_available_radius = diana_tune.i[2];
inline const int& crew_near_radius = diana_tune.i[3];
inline const int& crew_cap = diana_tune.i[24];
inline const float& crew_tank_line = diana_tune.f[27];
// Camp damage counted against the health that prices trips home (farm, crew.cc), camp_risk's
// boldness. With share_damage's spread, 0.45 and 0.6 smoked level with it (2026-10-31).
inline const float& crew_trip_risk = diana_tune.f[7];
// A strong group's crew value while we claim it, over farm's stickiness; a fresh proposal's while an
// ally's operation on another strong group is under way.
inline const float& crew_stickiness = diana_tune.f[8];
inline const float& crew_rival_factor = diana_tune.f[9];
// An operation fails when, this many rounds after its proposer came within reach, no ally claims
// it or stands in reach; it is then not proposed again for crew_ban_rounds.
inline const int& crew_wait_rounds = diana_tune.i[4];
// A claimer counts in a crew while in sight or seen within this many rounds.
inline const int& crew_seen_rounds = diana_tune.i[5];
// No allies are expected on a group with an enemy in sight this near its centre.
inline const int& crew_enemy_radius = diana_tune.i[6];
inline const int& crew_ban_rounds = diana_tune.i[7];
// Monoliths off Monolith-only maps are farm's crew operations (farm.cc, crew.cc). Members wait just
// out of reach of a sleeping one until this share of the crew's output has come, at most this long.
inline const float& mono_gather_share = diana_tune.f[10];
inline const int& mono_max_wait = diana_tune.i[8];
// crew_stickiness for a Monolith operation.
inline const float& mono_stickiness = diana_tune.f[11];
// Help a struggling teammate clear its damaging group within this many steps.
inline const int& help_radius = diana_tune.i[9];
// farm's pick_up: take over a group cleared this turn within this many tiles of its nearest member.
inline const int& pick_up_radius = diana_tune.i[10];

// Chain another capture onto a bag (Cassi's and Issac's together) only below this.
inline const int& chain_bag_limit = diana_tune.i[11];

// Cassi's or Issac's hold is worth this share of another ally's in the holder choice
// (economy/capture.cc hold_shy): the pair hands captures to the rest of the team.
inline const float& pair_hold_share = diana_tune.f[12];

// Early retreat (combat/guard.cc outmatched): enemies within two steps of their reach against
// allies this near. When hurt (under hurt_health_fraction, or carrying brake_bag gems or more),
// leave when their health times damage beats ours by hurt_retreat_ratio. Healthy outside our own
// half, no pack sends us back early.
inline const int& pack_ally_radius = diana_tune.i[12];
inline const float& hurt_retreat_ratio = diana_tune.f[13];
// A bag this big (a tribute of two turns or more) is worth chasing: it counts as hurt above, and
// makes our own ground no refuge from pursuit.
inline const int& brake_bag = diana_tune.i[13];
// In our own half, give way to packs at this ratio: an enemy pack there has come to fight.
inline const float& home_retreat_ratio = diana_tune.f[14];
// Leave before contact when the visible enemies within this many steps of their reach would win
// even if we struck first (stand_lost_at). At most 3: Safety::late packs it in 2 bits.
inline const int& pursuit_steps = diana_tune.i[25];
// Below this share of max health a sieger out of the besieged group's reach goes home to heal,
// and a caster stops staging at spell range.
inline const float& heal_trip_fraction = diana_tune.f[15];
// Turns ahead a tribute's safety is judged over, each turn of the channel.
inline const int& tribute_window = diana_tune.i[14];
// Most rounds to wait at a camp for it to return. Also bounds the wait after a recall out to farm.
inline const int& max_wait = diana_tune.i[15];
// The weight on gold in farm choice of Tavi on its gold maps (MapEconomy::tavi_map):
// they take the gold-only groups the others pass up.
inline const float& gold_farmer_weight = diana_tune.f[16];
// Gold's price in farm choices (prices().per_gold), scaled: we earn less gold than top teams. The learned
// emblems (economy/emblem_table.h) were learned at 1.5.
inline const float& gold_price_scale = diana_tune.f[17];

// Sieges (economy/siege.cc) of a Monolith on Monolith-only maps, of one the enemy is sieging, or of
// a group sealing the altars. The team goes once its output clears the group within siege_rounds
// and the hits it takes meanwhile, siege_hit_share of them landing (stuns, spells from out of
// reach), cost at most siege_pool_share of the team's max health (unchecked while the enemy is in
// the group's reach); a siege under way keeps going within siege_commit_slack of both.
inline const int& siege_rounds = diana_tune.i[16];
inline const float& siege_hit_share = diana_tune.f[18];
inline const float& siege_pool_share = diana_tune.f[19];
inline const float& siege_commit_slack = diana_tune.f[20];
// Skip a siege target that returns later than this.
inline const int& siege_respawn_wait = diana_tune.i[17];
// Off Monolith-only maps, a live Monolith the team clears within this many rounds at its known
// health is sieged too: one left alone that weak is the enemy's for a burst.
inline const int& burst_rounds = diana_tune.i[18];
// Wait just out of reach until this share of the team's output has come, at most this long.
inline const float& siege_gather_share = diana_tune.f[21];
inline const int& siege_max_wait = diana_tune.i[19];
// Big groups: at least this many gems, Monoliths aside. Maps whose only gems are big groups and
// Monoliths are kited (economy/siege.cc kite).
inline const int& big_gems = diana_tune.i[26];
// Most holders a capture is split over (economy/capture.cc holders).
inline const int& big_holders = diana_tune.i[27];
// Kiting: set out for a big group still respawning when it returns within this many rounds of our arrival.
inline const int& kite_early = diana_tune.i[20];
// Keep the current siege target unless another is sooner by this many rounds.
inline const int& siege_stickiness = diana_tune.i[21];

// Middle-band pricing (economy/farm.cc): a group whose share of the walks from the two spawns,
// d_enemy / (d_ally + d_enemy), lies between mid_low_share and own_ground_share is worth up to
// mid_exposure of itself, easing in over mid_edge either side of each bound (half weight on the
// bound itself). The bounds that take a group's weight as at most 1 scale by max_exposure.
inline const float& own_ground_share = diana_tune.f[22];
inline const float& mid_low_share = diana_tune.f[23];
inline const float& mid_exposure = diana_tune.f[24];
inline const float& mid_edge = diana_tune.f[25];
inline const float& max_exposure = diana_tune.f[28];

// Values in enemy health points: a champion's life over its health, each gem it carries, a stopped
// tribute (besides its gems) and a cancelled recall or teleport. turn_order.cc's rank codes fix
// them modulo 15 (static_assert there).
inline const float& life_value = diana_tune.f[29];
inline const float& gem_value = diana_tune.f[30];
inline const float& tribute_value = diana_tune.f[31];
inline const float& recall_value = diana_tune.f[32];
// turn_order.cc's copies, fixed: its rank codes need them modulo 15 (static_assert there).
inline constexpr float turn_life_value = 300;
inline constexpr float turn_gem_value = 15;
inline constexpr float turn_tribute_value = 100;
inline constexpr float turn_recall_value = 60;
// stun_worth prices a tributing enemy's bag by the rounds a stun puts off its tribute: the whole
// bag at this many (untuned).
inline constexpr float stun_tribute_horizon = 10;
// Each point of damage short of a kill is worth this much of itself; the rest of the kill's worth
// comes as the target weakens (kill_distance).
inline const float& chip_value = diana_tune.f[26];

// The ostrich (turn_order.cc engaged): an enemy in reach takes us to the danger band's early seats
// only once we or an enemy near us lost health within this many rounds.
inline const int& ostrich_rounds = diana_tune.i[22];

} // namespace aph::params
