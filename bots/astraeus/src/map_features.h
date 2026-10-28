#pragma once
// The draft lab's map features (tools/draftlab/features.mjs: mapgen's metrics() plus extras()) and its
// model's team (model.mjs rankTeams + pickOrder, data in draft_model.h). No SDK here, so
// tools/draftlab/native.mjs can compile it natively and check it against the JS on map files.
#include <array>
#include <cstdint>
#include <vector>

namespace aph::mapfeat {

enum Tile : std::uint8_t { ground, wall, hole, bush, altar };
enum Sym : int { horizontal, vertical, rotational };
inline constexpr int count = 19;

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

// Raw (untransformed) feature values in draft_model.h's order; NaN where the JS has null. Without
// `crystals`, spawns joined only by dash or crystal (metrics' last fallback, two crystal travels:
// more than the bot's first draft turn can pay on a large map) throw instead.
std::array<double, count> compute(const Input& in, WalkField walk = nullptr, bool crystals = true);

// features.mjs mapKey (tools/draftlab/trainer.h map_key): the lab's key for this map.
std::uint64_t map_key(const Input& in);

// The model's team for `picks` (3-5) in pick order, as champion_draft ids; empty for other counts.
std::vector<int> model_team(const std::array<double, count>& raw, int picks);

} // namespace aph::mapfeat
