// Each instance is the draft bot or one champion; Cassi and Issac are two.
#include <cambc.h>
#include <iostream>
#include <memory>
#include "bot.h"
#include "champions.h"
#include "comms.h"
#include "draft.h"
#include "params.h"
#include "pathing.h"
#include "util.h"
#include "world.h"

namespace {

using aph::params::end_reserve;

template <class F> bool run(const char* phase, F&& f) {
    try {
        f();
        return true;
    } catch (const std::exception& e) {
        std::cout << "r" << cambc::round_number() << ' ' << phase << " error: " << e.what() << std::endl;
    } catch (...) {
        std::cout << "r" << cambc::round_number() << ' ' << phase << " error: unknown exception" << std::endl;
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
                std::cout << "map " << m.width << 'x' << m.height << ' ' << cambc::to_string(m.symmetry) << " groups "
                          << m.groups.size() << " altars " << m.altars.size()
                          << " plan " << (world->plan ? "ok" : "missing") << '\n';
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
        // Only comms reads vision again, and it changes only if we moved.
        const bool refresh = cambc::self().position() != world->me().pos
                             && aph::fuel_ok(world->observe_cost_estimate() + end_reserve);
        run("comms send", [&] { aph::comms::send(*world, refresh); });
        run("debug", [&] { world->debug_output(); });
        if (!warmed_up)
            run("warm up", [&] {
                aph::FuelMeter meter{"warm_up"};
                map_warmed_up = map_warmed_up || world->map().warm_up(end_reserve);
                warmed_up = map_warmed_up && pathing->warm_up(world->me().facts().attack_range(), end_reserve);
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
        if (const auto now = cambc::round_number(); now != round)
            std::cout << "r" << round << " turn ran out of fuel, finished in r" << now << std::endl;
        cambc::end_turn();
    }
}
