// Ablation switches for A/B diagnosis of the Fish chunks (research/fish-bot-2026-11-06/LOG.md).
#pragma once
#ifndef FISH_PRIORITY
#define FISH_PRIORITY 1
#endif
namespace aph::fish {
inline constexpr bool use_draft = true, use_shop = true, use_locks = true, use_recall = true, use_tribute = true;
// Round 2, agent D: Fish's combat (fish/combat_turn.cc) and wards.
inline constexpr bool use_combat = true, use_wards = true;
// Its parts, for ablation: the contact turn, near_turn (camp hits stop within 4, momentum), the step
// guard (route progress iff h > 0.5), the step order (danger, then bush), Willow's heal rule with no
// Willow-Prism support code, Heart of Ruin's shield rule, late contagion, after_goal in place of
// strike_after. Off (measured worse, LOG.md round 2 D): want_home cut to Fish's (use_home), the strike
// search on turns the contact rules leave free (use_free_search: +120% out-of-fuel turns), the
// contact rules in place of want_home's retreat (use_contact_first).
inline constexpr bool use_contact = use_combat && true, use_near = use_combat && true, use_guard = use_combat && true,
                      use_home = false, use_steps = use_combat && true;
inline constexpr bool use_support = use_combat && true, use_shield = use_combat && true, use_late = use_combat && true,
                      use_free_search = false,
                      use_after = use_contact && true, use_contact_first = false;
} // namespace aph::fish
