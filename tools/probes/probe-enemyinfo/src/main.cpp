// probe-enemyinfo: what a champion can read about enemies and the draft during play.
// Q1: does draft::current_draft(enemy) work in play (gives enemy types before they are seen)?
// Q2: are a visible enemy's ability cooldowns, buffs, items, gems and channel time readable?
// Run: cambc run tools/probes/probe-enemyinfo tools/probes/probe-enemyinfo --map collision --rounds 200 --fuel 50000000
#include <cambc.h>
#include <algorithm>
#include <iostream>
#include <string>

using cambc::team;
using cambc::vec2;

static std::string P() {
    return "PROBE " + std::to_string(cambc::round_number()) + " " +
           (cambc::is_draft() ? std::string("draft") : cambc::to_string(cambc::self().champion_name())) + " ";
}

template <class F> static std::string T(F f) {
    try { return f(); } catch (const std::exception& e) { return std::string("ERR(") + e.what() + ")"; }
}

static void dump_draft() {
    std::cout << P() << "team_size=" << T([] { return std::to_string(cambc::draft::team_size()); });
    for (auto side : {team::ally, team::enemy}) {
        std::cout << " " << cambc::to_string(side) << "=" << T([&] {
            std::string s;
            for (auto p : cambc::draft::current_draft(side)) s += cambc::to_string(p) + ",";
            return s;
        });
    }
    std::cout << '\n';
}

static void play_draft() {
    dump_draft();
    const cambc::champion_draft order[] = {cambc::champion_draft::vesper_vale, cambc::champion_draft::ryth,
                                           cambc::champion_draft::stellar, cambc::champion_draft::tavi,
                                           cambc::champion_draft::varg};
    const auto mine = cambc::draft::current_draft(team::ally);
    for (auto p : order)
        if (std::find(mine.begin(), mine.end(), p) == mine.end()) { cambc::draft::pick(p); return; }
}

static int turns = 0;

static void play_turn() {
    auto& me = cambc::self();
    ++turns;
    if (turns == 1) {
        std::cout << P() << "map=" << cambc::map::width() << "x" << cambc::map::height() << " self_handle="
                  << static_cast<std::uint32_t>(static_cast<cambc::handle_champion_t>(me)) << " enemies=";
        for (auto& e : cambc::champions(team::enemy)) std::cout << static_cast<std::uint32_t>(static_cast<cambc::handle_champion_t>(e)) << ",";
        std::cout << " allies=";
        for (auto& a : cambc::champions(team::ally)) std::cout << static_cast<std::uint32_t>(static_cast<cambc::handle_champion_t>(a)) << ",";
        std::cout << '\n';
        dump_draft();
    }
    if (!me.is_alive()) return;

    // Read every visible enemy.
    for (auto& e : cambc::champions(team::enemy)) {
        const auto h = static_cast<std::uint32_t>(static_cast<cambc::handle_champion_t>(e));
        if (!e.is_visible()) {
            if (turns % 50 == 1) std::cout << P() << "enemy h=" << h << " hidden alive=" << T([&] { return std::to_string(e.is_alive()); })
                                           << " name=" << T([&] { return cambc::to_string(e.champion_name()); }) << '\n';
            continue;
        }
        std::cout << P() << "enemy h=" << h << " name=" << T([&] { return cambc::to_string(e.champion_name()); })
                  << " pos=" << cambc::to_string(e.position())
                  << " cd0=" << T([&] { return std::to_string(e.abilities()[0].cooldown()); })
                  << " cd1=" << T([&] { return std::to_string(e.abilities()[1].cooldown()); })
                  << " kind0=" << T([&] { return std::string(e.abilities()[0].info() ? "ok" : "none"); })
                  << " gems=" << T([&] { return std::to_string(e.gem_count()); })
                  << " items=" << T([&] { auto m = e.item_count(); unsigned n = 0; for (auto v : m) n += v; return std::to_string(n); })
                  << " buffs=" << T([&] { return std::to_string(e.buffs().size()); })
                  << " restr=" << T([&] { return std::to_string(e.restrictions().bits()); })
                  << " state=" << T([&] { return std::to_string(e.state().bits()); })
                  << " chan=" << T([&] { return std::to_string(e.remaining_channel_time()); })
                  << " prio=" << T([&] { return std::to_string(e.priority()); })
                  << '\n';
    }

    // Cast whatever we can so the other side sees cooldowns tick.
    const auto abilities = me.abilities();
    for (const auto& a : abilities) {
        if (!a.info() || a.cooldown() > 0) continue;
        try {
            bool ok = false;
            if (a.is_dash()) {
                for (vec2 d : {vec2{2, 0}, vec2{-2, 0}, vec2{0, 2}, vec2{0, -2}, vec2{1, 1}})
                    if (cambc::map::is_in_bounds(me.position() + d)) { try { ok = a.use(me.position() + d); if (ok) break; } catch (...) {} }
            } else if (a.can_target_ground()) {
                vec2 t = me.position();
                for (auto& e : cambc::vision::champions(team::enemy)) t = e.position();
                ok = a.use(t);
            } else if (a.can_target_enemies()) {
                for (auto& e : cambc::vision::champions(team::enemy)) { ok = a.use(e); break; }
            }
            if (ok) std::cout << P() << "cast slot=" << a.slot() << '\n';
        } catch (const std::exception&) {}
    }

    // Walk to the map centre.
    const vec2 centre{cambc::map::width() / 2, cambc::map::height() / 2};
    if (me.can_move()) {
        try { if (!me.move_towards(centre)) for (vec2 d : {vec2::north, vec2::east, vec2::south, vec2::west}) { try { if (me.move(d)) break; } catch (...) {} } } catch (...) {}
    }
}

int main() {
    while (true) {
        try {
            if (cambc::is_draft()) play_draft();
            else play_turn();
        } catch (const std::exception& e) {
            std::cout << "bot error: " << e.what() << std::endl;
        }
        cambc::end_turn();
    }
}
