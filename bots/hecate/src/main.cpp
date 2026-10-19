// Each instance is the draft bot or one champion; Cassi and Issac are two.
#include <cambc.h>
#include <cstdio>
#include <memory>
#include "bot.h"
#include "champions.h"
#include "comms.h"
#include "draft.h"
#include "pathing.h"
#include "util.h"
#include "world.h"

namespace {

using aph::end_reserve;

template <class F> bool run(const char* phase, F&& f) {
    try {
        f();
        return true;
    } catch (const std::exception& e) {
        std::printf("r%u %s error: %s\n", cambc::round_number(), phase, e.what());
    } catch (...) {
        std::printf("r%u %s error: unknown exception\n", cambc::round_number(), phase);
    }
    return false;
}

struct Instance {
    aph::DraftState draft;
    std::unique_ptr<aph::World> world;
    std::unique_ptr<aph::Pathing> pathing;
    aph::Memory memory;
    bool map_warmed_up = false, warmed_up = false;

    void draft_turn() {
        run("draft", [&] { aph::play_draft(draft); });
        run("draft fallback", [&] { aph::ensure_picked(draft); });
    }

    void play_turn() {
        aph::FuelMeter meter{"turn"};
        const bool updated = run("world", [&] {
            if (!world) world = std::make_unique<aph::World>();
            const bool first = !world->ready();
            world->update();
            if (!pathing) pathing = std::make_unique<aph::Pathing>(*world);
            pathing->begin_turn();
            if (first && aph::debug_log) {
                const auto& m = world->map();
                std::printf("map %dx%d %s groups %zu altars %zu plan %s\n", m.width, m.height,
                            cambc::to_string(m.symmetry).c_str(), m.groups.size(), m.altars.size(),
                            m.drafted() ? "ok" : "missing");
                aph::check_facts_against_engine();
            }
        });
        if (!updated || !world->ready()) return;

        run("comms receive", [&] { aph::comms::receive(*world); });
        run("decide", [&] {
            aph::FuelMeter meter{"decide"};
            aph::play_turn(*world, *pathing, memory);
        });

        if (world->is_stale()) return;
        run("turn end", [&] { world->note_turn_end(); });
        // Only comms reads vision again, and it changes only if we moved.
        const bool moved = world->me().alive && cambc::self().position() != world->me().pos;
        const bool refresh = moved && aph::fuel_ok(world->observe_cost_estimate() + end_reserve);
        if (moved && !refresh) aph::note_shortcut("comms-stale-vision");
        run("comms send", [&] { aph::comms::send(*world, refresh); });
        run("debug", [&] { world->debug_output(); });
        run("prepare", [&] { aph::prepare_next_turn(*world, *pathing, memory); });
        // Field costs are estimated from the deepest field so far; on the first turn none is
        // measured yet, so an estimate can miss by a whole field.
        if (!warmed_up)
            run("warm up", [&] {
                aph::FuelMeter meter{"warm_up"};
                const auto reserve = end_reserve + (world->round == world->first_round ? aph::field_cost_estimate() : 0);
                const bool centres = pathing->warm_centres(reserve);
                map_warmed_up = map_warmed_up || (centres && world->map().warm_up(reserve));
                warmed_up = map_warmed_up && pathing->warm_up(world->me().facts().attack_range(), reserve);
            });
        aph::print_fuel_log();
    }
};

} // namespace

int main() {
    Instance instance;
    while (true) {
        const auto round = cambc::round_number();
        if (cambc::is_draft())
            instance.draft_turn();
        else
            instance.play_turn();
        // Out of fuel, we resumed as this round's turn with a fresh budget: play it rather than end it.
        if (const auto now = cambc::round_number(); now != round) {
            std::printf("r%u turn ran out of fuel, finished in r%u\n", round, now);
            aph::note_shortcut("out-of-fuel");
            continue;
        }
        cambc::end_turn();
    }
}
