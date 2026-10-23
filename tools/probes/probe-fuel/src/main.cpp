// probe-fuel: measures the fuel budget per turn and what happens on fuel exhaustion.
// Run: cambc run probe-fuel probe-fuel --map corners --rounds 20 -o <dir>   (optionally --fuel N)
// Every PROBE value is read from the engine (fuel_remaining, round_number, position, can_move).
// bot.cpp / draft.cpp from the template are unused.
#include <cambc.h>
#include <cstdint>
#include <iostream>
#include <string>

using cambc::vec2;

static std::uint64_t F() { return cambc::fuel_remaining(); }
static std::string P(vec2 p) { return "(" + std::to_string(p.x) + "," + std::to_string(p.y) + ")"; }
static std::string me_name() {
    if (cambc::is_draft()) return "draft";
    return cambc::to_string(cambc::self().champion_name());
}

// Tiles one step away that a basic move could land on (based on what we can see).
static cambc::bitboard free_neighbours() {
    auto& me = cambc::self();
    auto blocked = cambc::map::walls() | cambc::map::holes() | cambc::map::altars()
        | cambc::map::spawn_region(cambc::team::enemy) | cambc::vision::champion_tiles()
        | cambc::vision::camp_tiles() | cambc::vision::teleport_tiles();
    blocked.set(me.position(), false);
    auto r = blocked.reachable_tiles(me.position(), 1);
    r.set(me.position(), false);
    return r;
}

static bool try_step(const char* tag) {
    auto& me = cambc::self();
    auto opts = free_neighbours().positions();
    vec2 before = me.position();
    bool can = me.can_move();
    bool ok = false;
    std::string err;
    if (!opts.empty()) {
        try { ok = me.move_absolute(opts[0]); } catch (const std::exception& e) { err = e.what(); }
    }
    std::cout << "PROBE " << cambc::round_number() << " " << me_name() << " " << tag
              << " can_move_before=" << can << " from=" << P(before)
              << " to=" << (opts.empty() ? std::string("none") : P(opts[0])) << " ok=" << ok
              << " err=[" << err << "] pos_after=" << P(me.position())
              << " can_move_after=" << me.can_move() << " fuel=" << F() << '\n';
    return ok;
}

// Burn fuel; print a marker every `every` iterations. Stop once round_number() has advanced
// by `rounds_to_cross` relative to the start (i.e. we were suspended and resumed).
static void burn(std::uint32_t rounds_to_cross, int every) {
    const std::uint32_t r0 = cambc::round_number();
    volatile std::uint64_t x = 0;
    std::uint64_t last_f = F();
    for (std::uint64_t i = 0;; ++i) {
        x = x * 6364136223846793005ULL + 1;
        if (i % every == 0) {
            std::uint64_t f = F();
            std::uint32_t r = cambc::round_number();
            // Print every marker near the edges of a budget, plus a coarse trace otherwise.
            if (f < 4000 || f > last_f || i % (every * 20) == 0)
                std::cout << "PROBE " << r << " " << me_name() << " burn i=" << i << " fuel=" << f << '\n';
            last_f = f;
            if (r >= r0 + rounds_to_cross) {
                std::cout << "PROBE " << r << " " << me_name() << " burn_done i=" << i << " start_round=" << r0
                          << " fuel=" << F() << '\n';
                return;
            }
        }
    }
}

// Rough fuel cost of common calls (measured with fuel_remaining before/after).
static void measure_costs1() {
    const char* n = "cost";
    std::uint64_t a, b;
    a = F(); b = F();
    std::cout << "PROBE " << cambc::round_number() << " " << me_name() << " " << n << " fuel_remaining_x1=" << (a - b) << '\n';
    a = F(); for (int i = 0; i < 100; ++i) (void)F(); b = F();
    std::cout << "PROBE " << cambc::round_number() << " " << me_name() << " " << n << " fuel_remaining_x100=" << (a - b) << '\n';
    a = F(); { volatile auto r = cambc::round_number(); (void)r; } b = F();
    std::cout << "PROBE " << cambc::round_number() << " " << me_name() << " " << n << " round_number=" << (a - b) << '\n';
    a = F(); { volatile auto p = cambc::self().position().x; (void)p; } b = F();
    std::cout << "PROBE " << cambc::round_number() << " " << me_name() << " " << n << " self_position=" << (a - b) << '\n';
    a = F(); { volatile bool c = cambc::self().can_move(); (void)c; } b = F();
    std::cout << "PROBE " << cambc::round_number() << " " << me_name() << " " << n << " self_can_move=" << (a - b) << '\n';
    a = F(); { auto v = cambc::vision::visible_tiles(); volatile auto c = v.is_empty(); (void)c; } b = F();
    std::cout << "PROBE " << cambc::round_number() << " " << me_name() << " " << n << " visible_tiles=" << (a - b) << '\n';
    a = F(); { auto v = cambc::map::walls(); volatile auto c = v.is_empty(); (void)c; } b = F();
    std::cout << "PROBE " << cambc::round_number() << " " << me_name() << " " << n << " map_walls=" << (a - b) << '\n';
    auto w = cambc::map::walls(); auto h = cambc::map::holes();
    a = F(); { auto v = w | h; volatile auto c = v.is_empty(); (void)c; } b = F();
    std::cout << "PROBE " << cambc::round_number() << " " << me_name() << " " << n << " bitboard_or_plus_is_empty=" << (a - b) << '\n';
    a = F(); { volatile auto c = w.count(); (void)c; } b = F();
    std::cout << "PROBE " << cambc::round_number() << " " << me_name() << " " << n << " bitboard_count=" << (a - b) << '\n';
    a = F(); { auto v = cambc::map::walls().positions(); volatile auto c = v.size(); (void)c; } b = F();
    std::cout << "PROBE " << cambc::round_number() << " " << me_name() << " " << n << " walls_positions_vector=" << (a - b) << " nwalls=" << w.count() << '\n';
    a = F(); { auto v = cambc::vision::champions(cambc::team::enemy); volatile auto c = v.size(); (void)c; } b = F();
    std::cout << "PROBE " << cambc::round_number() << " " << me_name() << " " << n << " vision_champions_enemy=" << (a - b) << '\n';
}
static void measure_costs2() {
    const char* n = "cost"; std::uint64_t a, b;
    a = F(); { auto v = cambc::map::camp_groups(); volatile auto c = v.size(); (void)c; } b = F();
    std::cout << "PROBE " << cambc::round_number() << " " << me_name() << " " << n << " map_camp_groups=" << (a - b) << '\n';
    a = F(); { auto v = free_neighbours(); volatile auto c = v.is_empty(); (void)c; } b = F();
    std::cout << "PROBE " << cambc::round_number() << " " << me_name() << " " << n << " blocked_mask_plus_reachable=" << (a - b) << '\n';
    a = F(); std::cout << "PROBE 0 x cost_line_dummy abcdefghijklmnopqrstuvwxyz0123456789\n"; b = F();
    std::cout << "PROBE " << cambc::round_number() << " " << me_name() << " " << n << " cout_short_line=" << (a - b) << '\n';
    a = F(); std::cout << std::flush; b = F();
    std::cout << "PROBE " << cambc::round_number() << " " << me_name() << " " << n << " cout_flush_after_1_line=" << (a - b) << '\n';
    a = F(); for (int i = 0; i < 20; ++i) std::cout << "PROBE 0 x cost_filler " << i << '\n'; b = F();
    std::cout << "PROBE " << cambc::round_number() << " " << me_name() << " " << n << " cout_20_lines=" << (a - b) << '\n';
    a = F(); std::cout << std::flush; b = F();
    std::cout << "PROBE " << cambc::round_number() << " " << me_name() << " " << n << " cout_flush_after_21_lines=" << (a - b) << '\n';
    a = F(); { volatile std::uint64_t s = 0; for (int i = 0; i < 1000; ++i) s = s + i; } b = F();
    std::cout << "PROBE " << cambc::round_number() << " " << me_name() << " " << n << " volatile_add_loop_1000=" << (a - b) << '\n';
}

static int turn_index = 0;
static int draft_turn = 0;

static void play_turn() {
    auto& me = cambc::self();
    const std::uint32_t r = cambc::round_number();
    ++turn_index;
    const auto name = me_name();
    // Only one champion per team (the first-picked one) runs the heavy experiments.
    const auto picks = cambc::draft::current_draft(cambc::team::ally);
    const bool experimenter = !picks.empty() && cambc::to_string(picks[0]) == cambc::to_string(me.champion_name());

    if (!experimenter) return;
    if (turn_index == 2) std::cout << "PROBE " << r << " " << name << " idle_turn_end fuel=" << F() << '\n';
    if (turn_index == 3) measure_costs1();
    if (turn_index == 4) measure_costs2();
    if (turn_index == 5) {
        // Q2/Q3: move, exhaust fuel, see where we resume, then try to move again.
        try_step("pre_burn_move");
        burn(1, 500);
        try_step("post_resume_move");
        try_step("post_resume_move2");
    }
    if (turn_index == 8) {
        // Burn across two round boundaries (needs >1 extra budget).
        burn(2, 500);
        try_step("post_resume2_move");
    }
    (void)r; (void)name;
}

static void draft_turn_fn() {
    ++draft_turn;
    const auto ally = cambc::draft::current_draft(cambc::team::ally);
    const auto enemy = cambc::draft::current_draft(cambc::team::enemy);
    std::cout << "PROBE " << cambc::round_number() << " draft draft_turn=" << draft_turn
              << " ally_picks=" << ally.size() << " enemy_picks=" << enemy.size();
    for (auto p : enemy) std::cout << " enemy:" << cambc::to_string(p);
    std::cout << " team_size=" << cambc::draft::team_size() << " fuel=" << F() << '\n';
    // Pick the first champion we have not yet picked.
    for (int i = 0; i < 11; ++i) {
        auto pick = static_cast<cambc::champion_draft>(i);
        bool taken = false;
        for (auto a : ally) taken |= a == pick;
        if (!taken) { cambc::draft::pick(pick); break; }
    }
    std::cout << "PROBE " << cambc::round_number() << " draft after_pick fuel=" << F() << '\n';
}

int main() {
    // Fuel at the very start of the program (first turn, before any of our logic).
    std::uint64_t f0 = F();
    std::cout << "PROBE 0 " << me_name() << " main_entry fuel=" << f0 << '\n';
    while (true) {
        const std::uint64_t f = F();
        try {
            if (cambc::is_draft()) {
                std::cout << "PROBE " << cambc::round_number() << " draft turn_start fuel=" << f << '\n';
                draft_turn_fn();
            } else {
                std::cout << "PROBE " << cambc::round_number() << " " << me_name() << " turn_start fuel=" << f
                          << " pos=" << P(cambc::self().position()) << " can_move=" << cambc::self().can_move() << '\n';
                play_turn();
            }
        } catch (const std::exception& e) {
            std::cout << "PROBE " << "err " << e.what() << '\n';
        }
        cambc::end_turn();
    }
}
