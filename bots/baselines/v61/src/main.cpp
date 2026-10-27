// Each instance is the draft bot or one champion; Cassi and Issac are two.
#include <cambc.h>
#include <cstdio>
#include <memory>
#include "bot.h"
#include "champions.h"
#include "comms.h"
#include "draft.h"
#include "pathing.h"
#include "plan.h"
#include "safety.h"
#include "util.h"
#include "world.h"

namespace {

using aph::end_reserve;
// What the turn's last phases need on their cheap paths.
constexpr std::uint64_t late_floor = 1500;
// The rules' budget a turn; a champion's first turn gets twice it.
constexpr std::uint64_t turn_fuel = 100000;

template <class F> bool run(const char* phase, F&& f) {
    debug_block({ aph::fuel_phase() = phase; });
    try {
        f();
        return true;
    } catch (const aph::StaleTurn&) {
    } catch (const std::exception& e) {
        std::printf("r%u %s error: %s\n", cambc::round_number(), phase, e.what());
    } catch (...) {
        std::printf("r%u %s error: unknown exception\n", cambc::round_number(), phase);
    }
    return false;
}

// Spare fuel fills the terrain-only tables a fight reads, nearest tiles first: around visible
// enemies, then around us (wider while dead). Never changes play: each fills as a miss would. Bound
// by the fuel spent this turn against the real budget, so it fills the same at any budget.
struct TableQueue {
    static constexpr std::uint64_t tile_reserve = 6000; // a tile's tables on 100x100, with margin
    // Filled tiles (or walls) as bits by row and by column, 2 words each: a ring's sides are 4 spans.
    std::vector<std::uint64_t> rows, cols;
    std::vector<std::uint8_t> rings; // by tile: rings around it all done, + 1

    // The first clear bit in [lo, hi] of a 2-word line, or -1.
    static int first_clear(const std::uint64_t* line, int lo, int hi) {
        for (int w = lo >> 6; w <= hi >> 6; ++w) {
            const int a = std::max(lo, w * 64) - w * 64, b = std::min(hi, w * 64 + 63) - w * 64;
            const std::uint64_t span = (b == 63 ? ~std::uint64_t{0} : (std::uint64_t{2} << b) - 1) & (~std::uint64_t{0} << a);
            if (const std::uint64_t m = ~line[w] & span) return w * 64 + std::countr_zero(m);
        }
        return -1;
    }

    void run(const aph::World& world, std::uint64_t start, std::uint64_t budget) {
        const auto& map = world.map();
        const int W = map.width, H = map.height;
        const auto room = [&] {
            const auto left = aph::fuel();
            return left >= aph::end_reserve + tile_reserve && start - left + aph::end_reserve + tile_reserve <= budget;
        };
        if (!room()) return;
        if (rings.empty()) {
            rows.assign(static_cast<std::size_t>(2 * H), 0), cols.assign(static_cast<std::size_t>(2 * W), 0);
            rings.assign(static_cast<std::size_t>(W * H), 0);
        }
        const auto fill = [&](int x, int y) {
            if (!room()) return false;
            if (!aph::test(map.walls, {x, y})) aph::warm_tile(world, {x, y});
            rows[static_cast<std::size_t>(2 * y + (x >> 6))] |= std::uint64_t{1} << (x & 63);
            cols[static_cast<std::size_t>(2 * x + (y >> 6))] |= std::uint64_t{1} << (y & 63);
            return true;
        };
        const auto around = [&](aph::vec2 c, int radius) {
            auto& done = rings[static_cast<std::size_t>(c.x + c.y * W)];
            for (int r = done; r <= radius; ++r) {
                const int x0 = std::max(0, c.x - r), x1 = std::min(W - 1, c.x + r);
                const int y0 = std::max(0, c.y - r + 1), y1 = std::min(H - 1, c.y + r - 1);
                while (true) {
                    int x = -1, y = -1;
                    for (const int row : {c.y - r, c.y + r})
                        if (x < 0 && row >= 0 && row < H) {
                            x = first_clear(&rows[static_cast<std::size_t>(2 * row)], x0, x1);
                            y = row;
                        }
                    for (const int col : {c.x - r, c.x + r})
                        if (x < 0 && col >= 0 && col < W && y0 <= y1) {
                            y = first_clear(&cols[static_cast<std::size_t>(2 * col)], y0, y1);
                            x = y < 0 ? -1 : col;
                        }
                    if (x < 0) break;
                    if (!fill(x, y)) return false;
                }
                done = static_cast<std::uint8_t>(r + 1);
            }
            return true;
        };
        const auto& me = world.me();
        if (me.alive)
            for (const auto& e : world.enemies)
                if (e.alive && e.visible && !around(e.pos, 2)) return;
        if (me.pos.x >= 0) around(me.pos, me.alive ? 8 : 20);
    }
};

struct Instance {
    TableQueue tables;
    aph::DraftState draft;
    std::unique_ptr<aph::World> world;
    std::unique_ptr<aph::Pathing> pathing;
    aph::Memory memory;
    bool map_warmed_up = false, warmed_up = false;
    bool logged_centres = false; // debug_block only

    void draft_turn() {
        run("draft", [&] { aph::play_draft(draft); });
        run("draft fallback", [&] { aph::ensure_picked(draft); });
    }

    [[gnu::flatten]] void play_turn() {
        const auto start = aph::fuel();
        aph::FuelMeter meter{"turn"};
        const bool updated = run("world", [&] {
            if (!world) world = std::make_unique<aph::World>();
            const bool first = !world->ready();
            if (!first) aph::comms::expect(*world);
            world->update();
            if (!pathing) pathing = std::make_unique<aph::Pathing>(*world);
            pathing->begin_turn();
            if (first && aph::debug_log) {
                const auto& m = world->map();
                std::printf("map %dx%d %s groups %zu altars %zu plan %s\n", m.width, m.height,
                            cambc::to_string(m.symmetry).c_str(), m.groups.size(), m.altars.size(),
                            m.drafted() ? "ok" : "missing");
            }
        });
        if (!updated || !world->ready() || world->is_stale()) return;

        run("comms receive", [&] { aph::comms::receive(*world); });
        run("decide", [&] {
            aph::FuelMeter meter{"decide"};
            aph::play_turn(*world, *pathing, memory);
        });

        // A turn that runs out of fuel costs the next one: the rest is skipped when short.
        if (world->is_stale() || !aph::fuel_ok(late_floor)) return;
        run("turn end", [&] { world->note_turn_end(); });
        if (world->is_stale() || !aph::fuel_ok(late_floor)) return;
        // Vision changes only if we moved. Off the map, we were killed this turn: nothing to re-read.
        const auto now = aph::my_position();
        const bool moved = world->me().alive && now.x >= 0 && now != world->me().pos;
        const bool refresh = moved && aph::fuel_ok(world->observe_cost_estimate() + end_reserve);
        run("comms send", [&] { aph::comms::send(*world, moved, refresh); });
        run("debug", [&] { world->debug_output(); });
        if (!aph::fuel_ok(late_floor)) return;
        run("prepare", [&] { aph::prepare_next_turn(*world, *pathing, memory); });
        // Below its floor plus a static window warm_reach does nothing, but its loops still cost.
        if (!world->is_stale() && aph::fuel_ok(end_reserve + 8000)) run("warm reach", [&] { aph::warm_reach(*world, end_reserve); });
        // Field costs are estimated from the deepest field so far; on the first turn none is
        // measured yet, so an estimate can miss by a whole field.
        if (!warmed_up && !world->is_stale() && aph::fuel_ok(end_reserve))
            run("warm up", [&] {
                aph::FuelMeter meter{"warm_up"};
                const auto reserve = end_reserve + (world->round == world->first_round ? aph::field_cost_estimate() : 0);
                const bool centres = pathing->warm_centres(reserve);
                map_warmed_up = map_warmed_up || (centres && world->map().warm_up(reserve));
                warmed_up = map_warmed_up && pathing->warm_up(world->me().facts().attack_range(), reserve)
                            && world->map().find_all_bush_clusters(reserve);
                debug_block({
                    if (centres && !logged_centres) std::printf("WARM %u centres\n", cambc::round_number()), logged_centres = true;
                    if (warmed_up) std::printf("WARM %u done\n", cambc::round_number());
                });
            });
        if (!world->is_stale())
            run("warm tables", [&] { tables.run(*world, start, world->round == world->first_round ? 2 * turn_fuel : turn_fuel); });
        aph::print_fuel_log();
    }
};

} // namespace

int main() {
    Instance instance;
    while (true) {
        const auto round = aph::checked_round();
        if (cambc::is_draft())
            instance.draft_turn();
        else
            instance.play_turn();
        // Out of fuel, we resumed as this round's turn with a fresh budget: play it rather than end it.
        if (const auto now = aph::checked_round(); now != round) {
            // A release-build line would cost the resumed turn ~2.5k.
            debug_block({
                std::printf("r%u turn ran out of fuel, finished in r%u\n", round, now);
                std::printf("OOF %u %s\n", round, aph::fuel_phase());
            });
            aph::note_shortcut("out-of-fuel");
            continue;
        }
        cambc::end_turn();
    }
}
