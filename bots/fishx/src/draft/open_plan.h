#pragma once
// The opening plan (research/draftfarm-2026-11-08): solved in the draft's first turn for the team we expect, it
// names each body's first groups to clear, in order, up to params::open_plan::horizon. Its model: the team farms
// our half alone from full health at spawn; a group's monsters hit the first champion to arrive until a melee
// arrives; a body past its usable health walks home; a capture pays its holder (the attendee with the best gold
// bonus) capture_time after the clear. Plans are lists per body, searched for the most value paid by the horizon.
#include <array>
#include <cstdint>
#include <vector>

namespace aph::open_plan {

inline constexpr int max_bodies = 6, max_steps = 6, max_cands = 24, max_members = 12;
inline constexpr int step_bits = 8; // group + 1, 0 for none

struct Body {
    float dps = 0;     // camp damage a round (ChampionFacts::raw_output at base stats)
    int range = 1;     // attack range
    float usable = 0;  // camp damage taken before a trip home
    float health = 0;  // camp damage that kills
    float bonus = 1;   // gold multiplier on its capture shares
    bool melee = false;
    std::array<std::uint16_t, max_cands> from_spawn{}; // walking steps from its start tile to each candidate
};

struct Cand {
    int group = -1;
    float gems = 0, gold = 0;
    int respawn = 0, home = 0; // rounds from payout to return; walking steps to our spawn
    int members = 0;
    float total = 0, total_strength = 0;
    std::array<float, max_members> hp{}, strength{}; // deadliest first; the rest merged into the last
};

struct Problem {
    int bodies = 0, cands = 0, horizon = 0;
    float per_gold = 0.3f;
    std::array<Body, max_bodies> body;
    std::array<Cand, max_cands> cand;
    std::array<std::array<std::uint16_t, max_cands>, max_cands> steps{}; // centre to centre
};

using Lists = std::array<std::array<std::int8_t, max_steps>, max_bodies>; // candidate indices, -1 ends

// Value paid by the horizon; `attended`, when given, gets each body's groups it worked, in order (-1 ends).
float simulate(const Problem& p, const Lists& plan, Lists* attended = nullptr);
// The best plan found within `fuel_floor`; its value into `value`.
Lists solve(const Problem& p, std::uint64_t fuel_floor, float& value, int& iterations);

} // namespace aph::open_plan
