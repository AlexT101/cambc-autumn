#pragma once
// The draft lab's map features (tools/draftlab/features.mjs: mapgen's metrics() plus extras()) and its
// model's team (model.mjs deployedTeam, data in draft_model.h). No SDK here, so
// tools/draftlab/native.mjs can compile it natively and check it against the JS on map files.
#include <array>
#include <cstdint>
#include <vector>

namespace aph::mapfeat {

enum Tile : std::uint8_t { ground, wall, hole, bush, altar };
enum Sym : int { horizontal, vertical, rotational };
// Every feature compute() measures, in tools/draftlab/model.mjs FEATURES order; draft_model.h names the ones its
// model uses (model_team finds them by name).
// The first base_count are measured by compute()'s passes (from dash_gain on only when asked); from monoliths on
// (draftfeat, 2026-11-06) mapgen metrics left out before and derived values (tools/draftlab/derived.mjs: one_altar,
// sq_a = T(a)^2, pr_a__b = T(a) T(b)), always computed: a derived feature asks for its components instead.
inline constexpr int base_count = 25, count = 92;
inline constexpr const char* names[count] = {
    "area", "reach_frac", "spawn_dist", "detour", "choke_rel", "openness", "bushes", "holes", "altars", "altar_ratio",
    "altar_centre", "gems_side", "gold_side", "big_share", "cluster_share", "contested_share", "big_camp_share",
    "dash_short", "camp_near", "dash_gain", "narrow", "spawn_ring", "max_group", "camp_altar", "sight_gap",
    "monoliths", "golems", "camps_side", "walls", "shared_groups", "one_altar", "sq_area", "sq_reach_frac",
    "sq_spawn_dist", "sq_detour", "sq_choke_rel", "sq_openness", "sq_bushes", "sq_holes", "sq_altars",
    "sq_altar_ratio", "sq_altar_centre", "sq_gems_side", "sq_gold_side", "sq_big_share", "sq_cluster_share",
    "sq_contested_share", "sq_big_camp_share", "sq_dash_short", "sq_camp_near", "sq_dash_gain", "sq_narrow",
    "sq_spawn_ring", "sq_max_group", "sq_camp_altar", "sq_sight_gap", "pr_area__openness", "pr_area__altar_centre",
    "pr_area__gems_side", "pr_area__gold_side", "pr_area__contested_share", "pr_reach_frac__gems_side",
    "pr_reach_frac__gold_side", "pr_spawn_dist__altars", "pr_spawn_dist__altar_ratio", "pr_spawn_dist__dash_short",
    "pr_spawn_dist__dash_gain", "pr_detour__altar_ratio", "pr_choke_rel__dash_short", "pr_choke_rel__dash_gain",
    "pr_altars__gold_side", "pr_altar_ratio__gold_side", "pr_altar_ratio__big_camp_share",
    "pr_altar_centre__gems_side", "pr_altar_centre__gold_side", "pr_altar_centre__big_camp_share",
    "pr_altar_centre__dash_gain", "pr_altar_centre__camp_altar", "pr_gems_side__gold_side", "pr_gems_side__big_share",
    "pr_gems_side__cluster_share", "pr_gems_side__max_group", "pr_gold_side__big_share", "pr_gold_side__cluster_share",
    "pr_gold_side__contested_share", "pr_gold_side__big_camp_share", "pr_gold_side__max_group",
    "pr_big_share__cluster_share", "pr_big_share__big_camp_share", "pr_big_share__max_group",
    "pr_cluster_share__max_group", "pr_dash_short__dash_gain"};
inline constexpr std::uint32_t every = (1u << base_count) - 1;

struct Camp {
    int type, x, y; // type in cambc::camp_type order (mapgen CAMP_TYPES)
};

struct Input {
    int W = 0, H = 0, sym = rotational;
    std::vector<std::uint8_t> t; // Tile, row-major (y * W + x)
    // Team A's spawn (absolute team 0, mapgen's g.spawn): [sx, sx + sw) x [sy, sy + sh).
    int sx = 0, sy = 0, sw = 0, sh = 0;
    // Every camp of both teams, a self-mirrored one once: mapgen's Grid.allCamps().
    std::vector<Camp> camps;
};

// Walking distances (mapgen spawnFields(g, blockers, 0)): from team `side`'s spawn over ground and
// bush, the other spawn blocked, and the camps blocked when `camps_block`; -1 unreached. The bot
// fills this with the engine's distance fields; null uses our own BFS.
using WalkField = void (*)(const Input& in, int side, bool camps_block, std::vector<int>& out);

// Raw (untransformed) feature values in `names` order; NaN where the JS has null. Base features from dash_gain on
// are measured only when their bit is in `want` (NaN otherwise); the first 19 and those past base_count always are
// (a derived one is NaN when a component is). Throws on bad input or
// unconnected spawns, and without `crystals` on spawns joined only by dash or crystal (metrics' last fallback, a
// crystal travel field: up to ~6M fuel on lattice and split maps).
// clearance_sum: metrics' openness summed over the tiles `walked` marks (a byte a tile, 8 bytes of slack). The bot
// fills this with bitboard host calls; null uses our own BFS.
using ClearanceSum = int (*)(const Input& in, const std::uint8_t* walked);

// The map's geometry that sets compute()'s cost, for the draft's structural budget (draft.cc work_budget): the
// sight_gap sources, and per travel field (dash; the crystal fallback, 0 unless needed) the leaping tiles walked to
// and the tiles brought nearer than walking.
struct Work {
    int sight_sources = 0, sight_steps = 0; // sources, and BFS steps over them
    int dash[2] = {}, crystal[2] = {};
};

std::array<double, count> compute(const Input& in, WalkField walk = nullptr, bool crystals = true, std::uint32_t want = every,
                                  ClearanceSum clear = nullptr, Work* work = nullptr);

// The `want` bits of draft_model.h's features: the bot measures only what its model reads.
std::uint32_t model_features();

// features.mjs mapKey (tools/draftlab/trainer.h map_key): the lab's key for this map.
std::uint64_t map_key(const Input& in);

// The model's team for `picks` (3-5) as champion_draft ids in pick order, holding `ours` (our picks so far, in
// pick order, first) and scored against `theirs` (the opponent's revealed picks) and the prior for the rest; empty
// for other counts.
std::vector<int> model_team(const std::array<double, count>& raw, int picks, const std::vector<int>& ours = {},
                            const std::vector<int>& theirs = {});

} // namespace aph::mapfeat
