// The turn loop. Each instance is either the draft bot or one champion (Cassi and Issac are two).
// Every phase is isolated so a failure still yields the turn.
#include <cambc.h>
#include <iostream>
#include <memory>
#include "bot.h"
#include "champions.h"
#include "comms.h"
#include "draft.h"
#include "pathing.h"
#include "util.h"
#include "world.h"

namespace {

// Fuel reserved for the end-of-turn phases, and the floor for spare-fuel precompute.
constexpr std::uint64_t observe_reserve = 20000;
// Printing the debug fuel log at the end of the turn costs a few thousand more.
constexpr std::uint64_t warm_up_floor = aph::debug_fuel ? 25000 : 10000;

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
    bool warmed_up = false;

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

        // If fuel ran out mid-turn we resumed in a later round: skip the extras, start afresh next turn.
        if (world->is_stale()) return;
        if (aph::fuel_ok(observe_reserve)) run("observe", [&] { world->observe(); });
        run("comms send", [&] { aph::comms::send(*world); });
        run("debug", [&] { world->debug_output(); });
        // Spend spare fuel on precompute until everything is cached.
        if (!warmed_up)
            run("warm up", [&] {
                aph::FuelMeter meter{"warm_up"};
                warmed_up = world->map().warm_up(warm_up_floor)
                            && pathing->warm_up(world->me().facts().attack_range(), warm_up_floor);
            });
        aph::print_fuel_log();
    }
};

} // namespace

int main() {
    Instance instance;
    while (true) {
        if (cambc::is_draft())
            instance.draft_turn();
        else
            instance.play_turn();
        cambc::end_turn();
    }
}
