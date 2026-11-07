#pragma once
// The combat lab's control block (copied into a bot by tools/combatlab/labify.py). The scenario
// runner finds it by its magic in linear memory and reads and writes it between turns, at no fuel
// to the bot. With flags 0 and no inputs (rounds -1) the bot plays as the unpatched one.
#include <cambc.h>
#include <cstddef>
#include <cstdint>

struct LabCand {
    std::int16_t x, y;       // end tile
    std::uint16_t removed;   // enemies (by index) out of the end tile's danger
    std::int8_t keep, entry; // the cast kept for the shield; its entry in the tile's frontier
    // raw: hits less cast prices and wakes, plus a heal and an unused walk; price: the casts' and
    // dash's prices raw took (Vendetta's refund not counted); danger: the expected damage at the end
    // tile; shield: the kept shield's worth there; camp: awake camps' fire there; gain: the goal's
    // progress. total = raw + shield - danger + gain - camp.
    float raw, price, danger, shield, camp, gain, total;
    char ops[8]; // w walk, a attack, r reset, d dash, c cast, h heal, s shield
};
struct LabPlan {
    std::int32_t round;
    char site;           // S strike search, K keep_bid, P strike_after
    std::int8_t status;  // 0 returned before searching, 1 chose a candidate, 2 searched and chose none
    std::int8_t early;   // strike_free's verdict (0 nothing to strike, 2 search, 1/3/4 its shortcuts)
    std::int8_t capped;  // the exact-pricing cap cut the search short
    std::int16_t tiles, exact_tiles, exact_cands, queries, banned, replanned;
    LabCand c;
};
struct LabBan {
    std::int16_t x, y;
    std::uint16_t removed;
    std::int8_t keep, pad;
};
struct LabStand {
    // verdict -1 not asked; reason 1 nobody to fight, 2 a paying hold keeps us, 3 no roster, 4 traded
    std::int8_t verdict, reason, lost, self_falls, falls, pad;
    std::int16_t turns_to_kill_us, turns_to_kill_them;
};

struct LabBlock {
    char magic[16];
    std::uint32_t version, size;
    // Inputs.
    std::uint32_t flags;    // bit 0: warm start; bit 1: record decision outputs
    std::uint32_t warm_pre; // the fuel a normal turn spends before the warm point; 0: as this turn spent it
    std::int32_t ban_round, ban_call, n_bans; // plan_strikes call `ban_call` (-1 any) of round `ban_round`
    LabBan bans[16];
    std::int32_t home_round, home_force, chase_round, chase_force; // force -1 none, else the verdict
    // Outputs of the warm start, once.
    std::int32_t warm_round;
    std::uint32_t pre_fuel; // this turn's fuel before the warm point (world update, map conditioning)
    std::uint64_t warm_fuel, warm_pre_used, warm_offset;
    // Outputs of the last turn.
    std::int32_t round;
    char decision;
    std::int8_t home, home_impl, chase; // -1 not asked; home_impl is want_home's own verdict
    std::uint32_t chase_target;
    LabStand stand;
    std::int32_t n_plans;
    std::int32_t warm_radius; // input: the warm start fills the tables around us to this radius (0: as the turn end does)
    LabPlan plans[4];
};
static_assert(sizeof(LabCand) == 44 && sizeof(LabPlan) == 64 && sizeof(LabBlock) == 512);
// The runner reads and writes these offsets (tools/fastengine/runner/src/scenario.rs, mod lb).
static_assert(offsetof(LabBlock, flags) == 24 && offsetof(LabBlock, ban_round) == 32 && offsetof(LabBlock, bans) == 44
              && offsetof(LabBlock, home_round) == 172 && offsetof(LabBlock, warm_round) == 188 && offsetof(LabBlock, warm_fuel) == 200
              && offsetof(LabBlock, round) == 224 && offsetof(LabBlock, chase_target) == 232 && offsetof(LabBlock, stand) == 236
              && offsetof(LabBlock, n_plans) == 248 && offsetof(LabBlock, plans) == 256 && offsetof(LabPlan, c) == 20
              && offsetof(LabCand, raw) == 8 && offsetof(LabCand, ops) == 36 && offsetof(LabStand, turns_to_kill_us) == 6);

extern "C" {
[[gnu::used, gnu::visibility("default")]] inline LabBlock cambc_lab = {
    "CAMBC-LAB-BLK-1", 1, sizeof(LabBlock), 0, 0, -1, -1, 0, {}, -1, -1, -1, -1, -1, 0, 0, 0, 0, -1, 0, -1, -1, -1, 0, {}, 0, 0, {}};
}

inline LabPlan lab_spare_plan;
inline int lab_calls = 0;    // plan_strikes calls this turn
inline char lab_site = 'S';  // the next plan_strikes call's site, unless keep_bid's

inline bool lab_on() { return cambc_lab.flags != 0; }

// Subtracted from the fuel the bot reads (aph::fuel) for the rest of a warm start's turn: it then sees what a
// normal turn has, while the host budget stays large, so the instance's cold first decision cannot run out.
inline std::uint64_t lab_fuel_offset = 0;

inline void lab_begin_turn() {
    if (!lab_on()) return;
    auto& b = cambc_lab;
    b.round = -1;
    b.decision = 0;
    b.home = b.home_impl = b.chase = -1;
    b.chase_target = 0;
    b.stand.verdict = -1;
    b.n_plans = 0;
    lab_calls = 0;
}

inline LabPlan& lab_plan_begin(int round, char site) {
    if (!lab_on()) return lab_spare_plan;
    const int k = lab_calls++;
    auto& p = k < 4 ? cambc_lab.plans[k] : lab_spare_plan;
    if (k < 4) cambc_lab.n_plans = k + 1;
    p = {};
    p.round = round;
    p.site = site;
    p.early = -1;
    return p;
}

inline bool lab_bans_on(int round) {
    const auto& b = cambc_lab;
    return b.n_bans > 0 && b.ban_round == round && (b.ban_call < 0 || b.ban_call == lab_calls - 1);
}

inline bool lab_banned(int x, int y, bool keep, std::uint16_t removed) {
    const auto& b = cambc_lab;
    for (int i = 0; i < b.n_bans && i < 16; ++i)
        if (b.bans[i].x == x && b.bans[i].y == y && (b.bans[i].keep != 0) == keep && b.bans[i].removed == removed) return true;
    return false;
}

inline bool lab_stand(int reason, bool verdict) {
    if (lab_on()) cambc_lab.stand = {static_cast<std::int8_t>(verdict), static_cast<std::int8_t>(reason), 0, 0, 0, 0, 0, 0};
    return verdict;
}

