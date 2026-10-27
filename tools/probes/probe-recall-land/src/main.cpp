// probe-recall-land: which own spawn tile does a recall land on, and what if it is occupied?
// Maps from makemap.mjs (open 30x30, 3x3 spawns, 5 picks): rot (A spawn (6..8,6..8)), rot-nw (A (6..8,20..22)), hor (horizontal symmetry).
// All coordinates are absolute. With c the own spawn's centre, Varg recalls from c+(5,5), c+(-5,5), c+(5,-5), c+(-5,0), c+(-5,-5),
// then from c+(-5,-5) four more times; before each of those, one more blocker (Vesper, Ryth, Stellar, Prism, parked off spawn)
// stands on the tile the previous recall landed on. Shared bytes: 0 = landings so far, 1-2 = the last landing tile.
//   node tools/probes/probe-recall-land/makemap.mjs <rot|rot-nw|hor>
//   cambc run tools/probes/probe-recall-land tools/probes/probe-recall-land \
//     --map tools/probes/probe-recall-land/recall-<variant>.map26a --rounds 200 --fuel 50000000 -o <dir>
// Result (2026-10-27, all three maps): the origin does not matter. Team A lands on the first free spawn tile in row order from
// (minX, minY): x rising, then y ((6,6) (7,6) (8,6) (6,7) (7,7)); not bitboard positions() order, which goes in 8x8 blocks.
// Team B uses the mirror image of A's order under the map's symmetry. The first pick starts on the first tile.
// An earlier version, whose start check let a blocker still be walking, landed on the tile free at arrival, not at the start.
#include <cambc.h>
#include <algorithm>
#include <cstdio>
#include <vector>

using cambc::vec2;
using cambc::team;
using D = cambc::champion_draft;
using CT = cambc::champion_type;
namespace M = cambc::map;
auto& mem = cambc::shared_memory;

namespace {

int R() { return (int)cambc::round_number(); }
vec2 centre() {
    const auto ps = M::spawn_region(team::ally).positions();
    return { (ps.front().x + ps.back().x) / 2, (ps.front().y + ps.back().y) / 2 };
}
char TEAM() { return centre().x < 15 ? 'A' : 'B'; }  // every variant puts A's spawn on x 6..8

void go(vec2 t) {
    auto& me = cambc::self();
    if (me.position() != t && me.can_move()) me.move_towards(t);
}

const vec2 OFF[] = { { 5, 5 }, { -5, 5 }, { 5, -5 }, { -5, 0 }, { -5, -5 }, { -5, -5 }, { -5, -5 }, { -5, -5 }, { -5, -5 } };
const int TRIALS = 9;
int trial = 0;
bool was_recalling = false;
std::vector<vec2> landed;

void varg() {
    auto& me = cambc::self();
    if (R() == 1) {
        std::printf("PROBE r%d %c spawn_order", R(), TEAM());
        for (vec2 p : M::spawn_region(team::ally).positions()) std::printf(" (%d,%d)", p.x, p.y);
        std::printf(" start=(%d,%d)\n", me.position().x, me.position().y);
    }
    if (me.is_recalling()) { was_recalling = true; return; }
    const vec2 from = centre() + OFF[std::min(trial, TRIALS - 1)];
    if (was_recalling) {
        was_recalling = false;
        const vec2 p = me.position();
        std::printf("PROBE r%d %c LANDED trial=%d from=(%d,%d) at=(%d,%d)\n", R(), TEAM(), trial, from.x, from.y, p.x, p.y);
        landed.push_back(p);
        mem[1] = (std::uint8_t)p.x;
        mem[2] = (std::uint8_t)p.y;
        mem[0] = (std::uint8_t)(trial + 1);
        ++trial;
        return;
    }
    if (trial >= TRIALS) return;
    go(from);
    if (me.position() != from) return;
    // Blockers stand exactly on landings 5.. (the earlier SW landings), nobody else on spawn.
    const auto allies = cambc::vision::champion_tiles(team::ally);
    const auto on_spawn = (allies & M::spawn_region(team::ally)).positions();
    if ((int)on_spawn.size() != std::max(0, trial - 4)) return;
    for (int i = 4; i < trial; ++i) if (!allies.is_set(landed[i])) return;
    me.recall();
    std::printf("PROBE r%d %c recall trial=%d from=(%d,%d) occupied:", R(), TEAM(), trial, from.x, from.y);
    for (vec2 p : on_spawn) std::printf(" (%d,%d)", p.x, p.y);
    std::printf("\n");
}

bool latched = false;
vec2 target;
void blocker(int k) {
    if (!latched && mem[0] == 4 + k) { latched = true; target = { (int)mem[1], (int)mem[2] }; }
    const vec2 c = centre();
    go(latched ? target : vec2{ c.x < 15 ? 15 : 14, c.y - 3 + 2 * k });
}

void play_draft() {
    const auto mine = cambc::draft::current_draft(team::ally);
    for (auto d : { D::varg, D::vesper_vale, D::ryth, D::stellar, D::prism })
        if (std::find(mine.begin(), mine.end(), d) == mine.end()) { cambc::draft::pick(d); return; }
}
} // namespace

int main() {
    while (true) {
        try {
            if (cambc::is_draft()) play_draft();
            else if (cambc::self().is_alive()) {
                switch (cambc::self().champion_name()) {
                case CT::varg: varg(); break;
                case CT::vesper_vale: blocker(1); break;
                case CT::ryth: blocker(2); break;
                case CT::stellar: blocker(3); break;
                case CT::prism: blocker(4); break;
                default: break;
                }
            }
        } catch (const cambc::error& e) {
            std::printf("PROBE r%d err %s\n", R(), e.message().c_str());
        }
        cambc::end_turn();
    }
}
