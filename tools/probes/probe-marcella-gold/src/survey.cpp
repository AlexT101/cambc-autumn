// Survey: dumps engine settings, spawn/altar tiles and every camp group, as PROBE lines.
#include <cambc.h>
#include <iostream>
#include "survey.h"

static void dump_tiles(const char* key, const cambc::bitboard& b) {
    std::cout << "PROBE 0 survey " << key << "=";
    for (auto p : b.positions()) std::cout << "(" << p.x << "," << p.y << ")";
    std::cout << '\n';
}

void survey() {
    namespace c = cambc::constants;
    std::cout << "PROBE 0 survey map=" << cambc::map::width() << "x" << cambc::map::height()
              << " team_size=" << cambc::draft::team_size() << " capture_time=" << c::capture_time
              << " respawn_time=" << c::respawn_time << " passive_gold=" << c::passive_gold
              << " kill_gold=" << c::kill_gold << " assist_gold=" << c::assist_gold
              << " submit_mult=" << c::submit_gem_duration_multiplier << " submit_base=" << c::submit_gem_base_duration
              << " submit_min=" << c::submit_gem_minimum_duration << " submit_range=" << c::submit_gems_range
              << " max_rounds=" << c::max_rounds << " winning_gems=" << c::winning_gems << '\n';
    dump_tiles("ally_spawn", cambc::map::spawn_region(cambc::team::ally));
    dump_tiles("enemy_spawn", cambc::map::spawn_region(cambc::team::enemy));
    dump_tiles("altars", cambc::map::altars());
    for (const auto& g : cambc::map::camp_groups()) {
        std::cout << "PROBE 0 survey group=" << static_cast<unsigned>(static_cast<cambc::handle_camp_group_t>(g))
                  << " gold=" << g.gold_value() << " gems=" << g.gem_value() << " respawn=" << g.max_respawn_timer() << " members=";
        for (const auto& m : g) std::cout << cambc::to_string(m.kind()) << "@(" << m.spawn_position().x << "," << m.spawn_position().y << ")";
        std::cout << '\n';
    }
}
