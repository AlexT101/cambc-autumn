// Draft: dump map (once) then pick champions from a fixed list.
#include <cambc.h>
#include "draft.h"
#include "config.h"
#include <algorithm>
#include <iostream>
#include <string>

void dump_map() {
    using namespace cambc;
    const int w = map::width(), h = map::height();
    std::vector<std::string> g(h, std::string(w, '.'));
    for (int y = 0; y < h; ++y) for (int x = 0; x < w; ++x) {
        vec2 p{x, y};
        if (map::walls().is_set(p)) g[y][x] = '#';
        else if (map::holes().is_set(p)) g[y][x] = 'O';
        else if (map::bushes().is_set(p)) g[y][x] = '"';
        else if (map::altars().is_set(p)) g[y][x] = 'A';
        else if (map::spawn_region(team::ally).is_set(p)) g[y][x] = 'S';
        else if (map::spawn_region(team::enemy).is_set(p)) g[y][x] = 'E';
    }
    for (const auto& grp : map::camp_groups())
        for (const auto& c : grp) {
            const char ch = c.is_wolf() ? 'w' : c.is_elk() ? 'e' : c.is_gem_cluster() ? 'g' : c.is_gold_cluster() ? '$' : 'M';
            g[c.spawn_position().y][c.spawn_position().x] = ch;
        }
    std::cout << "MAP " << w << "x" << h << " team_size=" << draft::team_size() << '\n';
    for (int y = 0; y < h; ++y) std::cout << "MAP " << (y < 10 ? " " : "") << y << " " << g[y] << '\n';
}

void play_draft() {
    static bool dumped = false;
    if (!dumped && kDumpMap) { dumped = true; dump_map(); }
    const auto chosen = cambc::draft::current_draft(cambc::team::ally);
    for (auto pick : kPicks)
        if (std::find(chosen.begin(), chosen.end(), pick) == chosen.end()) { cambc::draft::pick(pick); return; }
}
