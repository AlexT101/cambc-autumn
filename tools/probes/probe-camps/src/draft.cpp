// Deterministic draft for the camps probe; on the first pick, dumps the map as ASCII.
#include <cambc.h>
#include "draft.h"
#include "scenario.h"
#include <algorithm>
#include <iostream>
#include <string>

static void dump_map() {
    const int w = cambc::map::width(), h = cambc::map::height();
    std::vector<std::string> rows(h, std::string(w, '.'));
    auto put = [&](const cambc::bitboard& b, char c) { for (auto p : b.positions()) rows[p.y][p.x] = c; };
    put(cambc::map::bushes(), ',');
    put(cambc::map::walls(), '#');
    put(cambc::map::holes(), 'o');
    put(cambc::map::altars(), 'A');
    put(cambc::map::spawn_region(cambc::team::ally), 'S');
    put(cambc::map::spawn_region(cambc::team::enemy), 'E');
    std::cout << "PROBE 0 map w=" << w << " h=" << h << " team_size=" << cambc::draft::team_size() << '\n';
    for (const auto& g : cambc::map::camp_groups()) {
        std::cout << "PROBE 0 group id=" << static_cast<std::uint32_t>(static_cast<cambc::handle_camp_group_t>(g))
                  << " gold=" << g.gold_value() << " gems=" << g.gem_value();
        for (const auto& c : g) {
            const char ch = "WKGCM"[static_cast<int>(c.kind())];
            rows[c.spawn_position().y][c.spawn_position().x] = ch;
            std::cout << " camp=" << static_cast<std::uint32_t>(static_cast<cambc::handle_camp_t>(c)) << ":"
                      << cambc::to_string(c.kind()) << "@" << c.spawn_position().x << "," << c.spawn_position().y;
        }
        std::cout << '\n';
    }
    for (int y = 0; y < h; ++y) std::cout << "PROBE 0 row " << (y < 10 ? "0" : "") << y << " " << rows[y] << '\n';
}

void play_draft() {
    const auto chosen = cambc::draft::current_draft(cambc::team::ally);
    if (chosen.empty() && DUMP_MAP) dump_map();
    // Pick scenario-chosen champions in order, then fill with lowest unpicked.
    for (auto pick : PICKS)
        if (std::find(chosen.begin(), chosen.end(), pick) == chosen.end()) { cambc::draft::pick(pick); return; }
    for (int i = 0; i < 11; ++i) {
        auto pick = static_cast<cambc::champion_draft>(i);
        if (std::find(chosen.begin(), chosen.end(), pick) == chosen.end()) { cambc::draft::pick(pick); return; }
    }
}
