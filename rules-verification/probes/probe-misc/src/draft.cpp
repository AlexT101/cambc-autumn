// Draft: survey once, then pick the scenario's champions in order (fallback: first unpicked).
#include <cambc.h>
#include <algorithm>
#include <iostream>
#include "bot.h"
#include "draft.h"

static void dump_tiles(const char* key, const cambc::bitboard& b) {
    std::cout << "PROBE 0 survey " << key << "=";
    for (auto p : b.positions()) std::cout << "(" << p.x << "," << p.y << ")";
    std::cout << '\n';
}

static void survey() {
    std::cout << "PROBE 0 survey map=" << cambc::map::width() << "x" << cambc::map::height()
              << " team_size=" << cambc::draft::team_size() << " sleep=" << cambc::constants::camp_sleep_time
              << " lock_hits=" << cambc::constants::altar_lock_hits << '\n';
    dump_tiles("ally_spawn", cambc::map::spawn_region(cambc::team::ally));
    dump_tiles("enemy_spawn", cambc::map::spawn_region(cambc::team::enemy));
    dump_tiles("altars", cambc::map::altars());
    // ASCII map, north (high y) first: # wall, O hole, " bush, A altar, c camp, S ally spawn, E enemy spawn
    cambc::bitboard camps; camps.clear();
    for (const auto& g : cambc::map::camp_groups()) for (const auto& m : g) camps.set(m.spawn_position());
    for (int y = cambc::map::height() - 1; y >= 0; --y) {
        std::cout << "PROBE 0 survey row" << (y < 10 ? "0" : "") << y << " ";
        for (int x = 0; x < cambc::map::width(); ++x) {
            cambc::vec2 p{x, y};
            char ch = '.';
            if (cambc::map::walls().is_set(p)) ch = '#';
            else if (cambc::map::holes().is_set(p)) ch = 'O';
            else if (cambc::map::altars().is_set(p)) ch = 'A';
            else if (camps.is_set(p)) ch = 'c';
            else if (cambc::map::spawn_region(cambc::team::ally).is_set(p)) ch = 'S';
            else if (cambc::map::spawn_region(cambc::team::enemy).is_set(p)) ch = 'E';
            else if (cambc::map::bushes().is_set(p)) ch = '"';
            std::cout << ch;
        }
        std::cout << '\n';
    }
    for (const auto& g : cambc::map::camp_groups()) {
        std::cout << "PROBE 0 survey group=" << static_cast<unsigned>(static_cast<cambc::handle_camp_group_t>(g))
                  << " gold=" << g.gold_value() << " gems=" << g.gem_value() << " members=";
        for (const auto& m : g) std::cout << cambc::to_string(m.kind()) << "@(" << m.spawn_position().x << "," << m.spawn_position().y << ")";
        std::cout << '\n';
    }
}

void play_draft() {
    static bool surveyed = false;
    if (!surveyed) { survey(); surveyed = true; }
    const auto chosen = cambc::draft::current_draft(cambc::team::ally);
    for (auto p : scenario_draft())
        if (std::find(chosen.begin(), chosen.end(), p) == chosen.end()) { cambc::draft::pick(p); return; }
    for (int i = 0; i < 11; ++i) {
        auto pick = static_cast<cambc::champion_draft>(i);
        if (std::find(chosen.begin(), chosen.end(), pick) == chosen.end()) { cambc::draft::pick(pick); return; }
    }
}
