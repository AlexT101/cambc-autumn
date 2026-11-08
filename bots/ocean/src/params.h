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
// Debug builds only: measure the map facts in play too, and print whether the draft's match (FACTCHECK).
constexpr bool check_draft_facts = false;

// Rounds out of sight after which an enemy could be anywhere.
inline constexpr int track_horizon = 3;

// Below this share of max health a champion goes home; camps may cost only the health above it.
// This is the line while an enemy threatens us (fight.cc recall_line); safe_recall_health_fraction otherwise.
// Set per map on a champion's first turn (draft.cc condition_on_map); this is the value without map features.
inline float recall_health_fraction = 0.31549114f;
// The recall line while no enemy can credibly reach us within threat_radius steps.
inline constexpr float safe_recall_health_fraction = 0.10935836f;
// recall_line: steps past an enemy's reach within which it threatens us.
inline constexpr int threat_radius = 8;
// The draft's fixed recall line for usable health (draft.cc type_facts).
inline constexpr float draft_recall_health_fraction = 0.22716701f;
// Below this share of max health a champion, ours or an enemy, is hurt: ours retreat from smaller
// packs, no longer count their own ground as safe from pursuit, and are healed for any gain.
inline constexpr float hurt_health_fraction = 0.4532513f;
// Below the recall line, stay to finish a camp whose remaining damage is under this share of our health.
inline constexpr float finish_camp_health_fraction = 0.6881714f;
// Camp damage counted against the health we can spare when choosing a camp (below 1: bolder).
inline constexpr float camp_risk = 0.45716766f;
// Enemy-ground discount: a group's weight is min(1, 2 d_enemy / (d_ally + d_enemy)) to this power.
inline constexpr float home_power = 1.8913636f;
// An ally this near with no claim of its own can partner on a group too costly for us alone.
inline constexpr int partner_radius = 13;
// Crews on strong groups (economy/crew.cc): allies in sight this near a group's centre, free or on
// harmless or cleared groups within crew_near_radius of it, are expected to join an operation on it;
// crews of at most crew_cap. Each member scores as tank by its health above crew_tank_line.
inline constexpr int crew_available_radius = 11;
inline constexpr int crew_near_radius = 9;
inline constexpr int crew_cap = 5;
inline constexpr float crew_tank_line = 0.32032415f;
// Camp damage counted against the health that prices trips home (farm, crew.cc), camp_risk's
// boldness. With share_damage's spread, 0.45 and 0.6 smoked level with it (2026-10-31).
inline constexpr float crew_trip_risk = 0.795274f;
// A strong group's crew value while we claim it, over farm's stickiness; a fresh proposal's while an
// ally's operation on another strong group is under way.
inline constexpr float crew_stickiness = 1.4112711f;
inline constexpr float crew_rival_factor = 0.90085506f;
// An operation fails when, this many rounds after its proposer came within reach, no ally claims
// it or stands in reach; it is then not proposed again for crew_ban_rounds.
inline constexpr int crew_wait_rounds = 4;
// A claimer counts in a crew while in sight or seen within this many rounds.
inline constexpr int crew_seen_rounds = 12;
// No allies are expected on a group with an enemy in sight this near its centre.
inline constexpr int crew_enemy_radius = 12;
inline constexpr int crew_ban_rounds = 26;
// Monoliths off Monolith-only maps are farm's crew operations (farm.cc, crew.cc). Members wait just
// out of reach of a sleeping one until this share of the crew's output has come, at most this long.
inline constexpr float mono_gather_share = 0.62638295f;
inline constexpr int mono_max_wait = 12;
// crew_stickiness for a Monolith operation.
inline constexpr float mono_stickiness = 1.6830473f;
// Help a struggling teammate clear its damaging group within this many steps.
inline constexpr int help_radius = 6;
// farm's pick_up: take over a group cleared this turn within this many tiles of its nearest member.
inline constexpr int pick_up_radius = 7;

// Chain another capture onto a bag (Cassi's and Issac's together) only below this.
inline constexpr int chain_bag_limit = 26;
// A bag under this many gems is not banked (economy/bank.cc bankable_bag), but for a winning bag or a
// closing game: Fish banks 25-50 at a time (research/ideas-2026-11-07/behaviour-gaps.md).
inline constexpr int min_bank = 25;

// Cassi's or Issac's hold is worth this share of another ally's in the holder choice
// (economy/capture.cc hold_shy): the pair hands captures to the rest of the team.
inline constexpr float pair_hold_share = 0.54980224f;

// Early retreat (combat/guard.cc outmatched): enemies within two steps of their reach against
// allies this near. When hurt (under hurt_health_fraction, or carrying brake_bag gems or more),
// leave when their health times damage beats ours by hurt_retreat_ratio. Healthy outside our own
// half, no pack sends us back early.
inline constexpr int pack_ally_radius = 6;
inline constexpr float hurt_retreat_ratio = 3.3350472f;
// A bag this big (a tribute of two turns or more) is worth chasing: it counts as hurt above, and
// makes our own ground no refuge from pursuit.
inline constexpr int brake_bag = 19;
// In our own half, give way to packs at this ratio: an enemy pack there has come to fight.
inline constexpr float home_retreat_ratio = 2.1740904f;
// Leave before contact when the visible enemies within this many steps of their reach would win
// even if we struck first (stand_lost_at). At most 3: Safety::late packs it in 2 bits.
inline constexpr int pursuit_steps = 2;
// Below this share of max health a sieger out of the besieged group's reach goes home to heal,
// and a caster stops staging at spell range.
inline constexpr float heal_trip_fraction = 0.5362846f;
// Turns ahead a tribute's safety is judged over, each turn of the channel.
inline constexpr int tribute_window = 11;
// Most rounds to wait at a camp for it to return. Also bounds the wait after a recall out to farm.
inline constexpr int max_wait = 2;
// The weight on gold in farm choice of Tavi on its gold maps (MapEconomy::tavi_map):
// they take the gold-only groups the others pass up.
inline constexpr float gold_farmer_weight = 3.8296325f;
// Gold's price in farm choices (prices().per_gold), scaled: we earn less gold than top teams. The learned
// emblems (economy/emblem_table.h) were learned at 1.5.
// Set per map on a champion's first turn (draft.cc condition_on_map); this is the value without map features.
inline float gold_price_scale = 1.3209833f;
// condition_on_map: the share of oc5's fitted map-feature shifts taken (EXPERIMENTS "oc-mapcond2").
inline constexpr double mapcond_shrink = 0.25;

// Sieges (economy/siege.cc) of a Monolith on Monolith-only maps, of one the enemy is sieging, or of
// a group sealing the altars. The team goes once its output clears the group within siege_rounds
// and the hits it takes meanwhile, siege_hit_share of them landing (stuns, spells from out of
// reach), cost at most siege_pool_share of the team's max health (unchecked while the enemy is in
// the group's reach); a siege under way keeps going within siege_commit_slack of both.
inline constexpr int siege_rounds = 76;
inline constexpr float siege_hit_share = 0.8934753f;
inline constexpr float siege_pool_share = 0.40265793f;
inline constexpr float siege_commit_slack = 1.3968046f;
// Skip a siege target that returns later than this.
inline constexpr int siege_respawn_wait = 30;
// Off Monolith-only maps, a live Monolith the team clears within this many rounds at its known
// health is sieged too: one left alone that weak is the enemy's for a burst.
inline constexpr int burst_rounds = 13;
// A Monolith group whose live strikers all fire on spawn stands the sturdiest of us outlasts
// (siege.cc home_siege) is sieged once the team, at the output those stands hold, clears it within
// this many rounds: from there it costs time, not health.
inline constexpr int home_siege_rounds = 512;
// Wait just out of reach until this share of the team's output has come, at most this long.
inline constexpr float siege_gather_share = 0.60775375f;
inline constexpr int siege_max_wait = 20;
// Big groups: at least this many gems, Monoliths aside. Maps whose only gems are big groups and
// Monoliths are kited (economy/siege.cc kite).
inline constexpr int big_gems = 70;
// Most holders a capture is split over (economy/capture.cc holders).
inline constexpr int big_holders = 3;
// Kiting: set out for a big group still respawning when it returns within this many rounds of our arrival.
inline constexpr int kite_early = 10;
// Keep the current siege target unless another is sooner by this many rounds.
inline constexpr int siege_stickiness = 20;

// Middle-band pricing (economy/farm.cc): a group whose share of the walks from the two spawns,
// d_enemy / (d_ally + d_enemy), lies between mid_low_share and own_ground_share is worth up to
// mid_exposure of itself, easing in over mid_edge either side of each bound (half weight on the
// bound itself). The pre-facts prunes that take a group's weight as at most 1 scale by max_exposure,
// tuned apart and below mid_exposure (farm.cc exposure_most bounds exposure() for the exact bounds).
inline constexpr float own_ground_share = 0.6832753f;
inline constexpr float mid_low_share = 0.25452974f;
inline constexpr float mid_exposure = 1.3611484f;
inline constexpr float mid_edge = 0.055977345f;
inline constexpr float max_exposure = 1.2148346f;

// Values in enemy health points: a champion's life over its health, each gem it carries, a stopped
// tribute (besides its gems) and a cancelled recall or teleport.
inline constexpr float life_value = 276.60016f;
inline constexpr float gem_value = 17.52141f;
inline constexpr float tribute_value = 83.167366f;
inline constexpr float recall_value = 66.34215f;
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
inline constexpr float chip_value = 0.24669105f;

// The ostrich (turn_order.cc engaged): an enemy in reach takes us to the danger band's early seats
// only once we or an enemy near us lost health within this many rounds.
inline constexpr int ostrich_rounds = 2;

// Altar control (economy/altar_guard.cc) on one-altar maps: guarding starts at enemy tributed >=
// altar_enemy_min and enemy - ours >= altar_gap, and stops below altar_gap_off; it also holds while a body
// of ours carries a winning bag. The altar_guards strongest bodies guard, leaving at least
// altar_farmers_min farming, on stand tiles within altar_stand_radius of the altar, and fight enemies
// within altar_leash of it.
inline constexpr int altar_enemy_min = 600, altar_gap = 200, altar_gap_off = 100;
inline constexpr int altar_guards = 3;
inline constexpr int altar_stand_radius = 2;
inline constexpr int altar_leash = 6;
inline constexpr int altar_farmers_min = 1;

// An emblem's fight value (shop.cc fight_saved): this weight x the share of the damage we take that comes
// from champions, with fight_camp_prior camp damage as a prior, x the fight power it adds (output x effective health).
inline constexpr float fight_weight = 0.6882139f;
inline constexpr float fight_camp_prior = 490.12277f;
// wants_shop: a shopping trip goes when shop_gain_scale x the purchase's saving (plus the heal) beats the trip.
inline constexpr float shop_gain_scale = 0.75106156f;
// safety_params::hit_given_reach and recall_risk (model/safety.h), tunable here.
inline constexpr float hit_given_reach = 0.2338928f;
inline constexpr float recall_risk = 0.20703878f;

// The reveal ward (bot.cc reveal_ward): the least share of an unseen enemy's possible tiles a bush cluster must hold,
// and the weight of one last seen in or beside the cluster (it most likely ran into it).
inline constexpr float reveal_mass = 0.23420754f;
inline constexpr float reveal_prior = 1.6499189f;

// The timed lock (fight.cc lock_plan_wait): the nearest a body waits to the altar's lock tiles, in steps (up to 3 more).
inline constexpr int lock_stage_steps = 8;
// channel_to_deny: the least visible enemy tribute bag it stops.
inline constexpr int deny_gems = 112;
// relative_efficiency: holders and farm's gold weigh (gold efficiency / the team's mean)^efficiency_power.
inline constexpr float efficiency_power = 1.4653788f;

// Cooked comebacks (economy/comeback.cc, research/ideas-2026-11-05/comeback.md): while the enemy has at least
// enemy_min tributed and leads by gap (cooked until the lead falls below gap_off), farm's mirror pull counts a
// group's walk as steps - pull_lam * max(0, steps - pull_c * mirror_steps), mirror_steps from the mirror of our
// tile; enemy-side groups' worth weighs 1 + deny_w; and a lost chase is taken against a carrier of bar_bag or more
// while we last bar turns, with the other allies (up to two) within pack_radius.
namespace comeback {
inline constexpr int enemy_min = 400, gap = 150, gap_off = 100;
inline constexpr float pull_c = 1.0f, pull_lam = 1.0f;
inline constexpr float deny_w = 0.5f;
inline constexpr float bar = 2;
inline constexpr int bar_bag = 40;
inline constexpr int pack_radius = 4;
} // namespace comeback
// research/ladder-scrims-2026-11-06/fix-combat.md.
namespace fixc {
// A bag at stake this big: the pack zone outmatches us at bag_ratio.
inline constexpr int bag_big = 100;
inline constexpr float bag_ratio = 2.0f;
// Path first steps and retreat ties take a hidden bush first; within a visible enemy's ready strike reach +
// bush_threat, the bush rank goes ahead of pull, aim and steps, and a hidden bush step is let off bush_margin x
// our health and shield of retreat damage.
inline constexpr int bush_threat = 2;
inline constexpr float bush_margin = 0.1f;
} // namespace fixc
// Willow's early fights (research/ideas-2026-11-07/willow.md, "Early aggression"): before round willow_fight_until,
// a healthy Willow with an ally within willow_stand_ally stands in an enemy's reach (the fight simulation decides,
// as for the other types), chases as they do, and after a follow hit takes the reset unless the heal lands.
inline constexpr int willow_fight_until = 250;
inline constexpr int willow_stand_ally = 2;
// The reactive Tribute emblem (shop.cc reactive_tribute) prices from a bag of this many gems.
inline constexpr int trib_min_bag = 100;

} // namespace aph::params
