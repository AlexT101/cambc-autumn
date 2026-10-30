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
inline constexpr int count = 25;
inline constexpr const char* names[count] = {
    "area", "reach_frac", "spawn_dist", "detour", "choke_rel", "openness", "bushes", "holes", "altars", "altar_ratio",
    "altar_centre", "gems_side", "gold_side", "big_share", "cluster_share", "contested_share", "big_camp_share",
    "dash_short", "camp_near", "dash_gain", "narrow", "spawn_ring", "max_group", "camp_altar", "sight_gap"};
inline constexpr std::uint32_t every = (1u << count) - 1;

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

// Raw (untransformed) feature values in `names` order; NaN where the JS has null. Features from dash_gain on are
// measured only when their bit is in `want` (NaN otherwise); the first 19 always are. Throws on bad input or
// unconnected spawns, and without `crystals` on spawns joined only by dash or crystal (metrics' last fallback: two
// crystal travels, more than the first draft turn pays on a large map).
std::array<double, count> compute(const Input& in, WalkField walk = nullptr, bool crystals = true, std::uint32_t want = every);

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
