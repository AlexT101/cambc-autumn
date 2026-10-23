#pragma once
// probe-introspect: dumps engine-reported constants, designs and map layout.
// Every value printed comes from the engine (raw detail:: imports where the
// public wrapper hides a field). Lines: PROBE <round> <who> <key>=<value> ...
#include <cambc.h>
#include <cstdint>
#include <cstring>
#include <iomanip>
#include <iostream>
#include <string>

namespace probe {

inline std::string P(const std::string& who) {
    std::uint32_t r = 0;
    int code = cambc::detail::sdk_bc_round_number(&r);
    return "PROBE " + (code == 0 ? std::to_string(r) : "err" + std::to_string(code)) + " " + who + " ";
}

inline std::string pos(cambc::vec2 v) { return std::to_string(v.x) + "," + std::to_string(v.y); }

inline std::string hexu(std::uint32_t v) {
    char b[16];
    std::snprintf(b, sizeof b, "0x%x", v);
    return b;
}

// 1. Raw Game_Settings record, every field including unexposed ones.
inline void dump_settings(const std::string& w) {
    const auto& s = cambc::detail::cached_game_settings;
    std::cout << P(w) << "settings capture_time=" << s.capture_time << " camp_sleep_time=" << s.camp_sleep_time
              << " respawn_time=" << s.respawn_time << " recall_time=" << s.recall_time
              << " submit_gem_duration_multiplier=" << s.submit_gem_duration_multiplier
              << " submit_gem_base_duration=" << s.submit_gem_base_duration
              << " submit_gem_minimum_duration=" << s.submit_gem_minimum_duration
              << " submit_gems_range=" << s.submit_gems_range << '\n';
    std::cout << P(w) << "settings max_rounds=" << s.max_rounds << " winning_gems=" << s.winning_gems
              << " kill_gold=" << s.kill_gold << " assist_gold=" << s.assist_gold << " passive_gold=" << s.passive_gold
              << " spawn_healing=" << s.spawn_healing << " active_wards=" << s.active_wards
              << " ward_charges=" << s.ward_charges << " shared_memory_bytes=" << s.shared_memory_bytes
              << " draft_memory_bytes=" << s.draft_memory_bytes << " tile_reveal_rounds=" << s.tile_reveal_rounds << '\n';
    std::cout << P(w) << "settings ward_cooldown=" << s.ward_cooldown << " ward_lifetime=" << s.ward_lifetime
              << " ward_vision_radius=" << s.ward_vision_radius << " ward_placement_radius=" << s.ward_placement_radius
              << " control_ward_vision_radius=" << s.control_ward_vision_radius
              << " control_ward_placement_radius=" << s.control_ward_placement_radius
              << " altar_lock_hits=" << s.altar_lock_hits << " tp_scroll_time=" << s.tp_scroll_time
              << " tp_crystal_time=" << s.tp_crystal_time << " reserved=" << s.reserved << '\n';
    std::uint32_t sm = 0, dm = 0;
    int c1 = cambc::detail::sdk_shared_memory_size(&sm);
    int c2 = cambc::detail::sdk_draft_memory_size(&dm);
    std::cout << P(w) << "memsize shared=" << sm << " code=" << c1 << " draft=" << dm << " code=" << c2 << '\n';
}

// 2. Items (raw Game_ItemInfo incl. combine_cost) and consumables (raw ids 0..4).
inline void dump_items(const std::string& w) {
    for (std::uint32_t i = 0; i <= static_cast<std::uint32_t>(cambc::item_type::count); ++i) {
        cambc::detail::item_info d{};
        int code = cambc::detail::sdk_item_info(i, &d);
        std::cout << P(w) << "item id=" << i << " name=" << cambc::to_string(cambc::item_type{i}) << " code=" << code;
        if (code == 0)
            std::cout << " cost=" << d.cost << " purchasable=" << d.purchasable << " hp=" << d.health_points
                      << " str=" << d.strength_points << " foc=" << d.focus_points << " passive=" << d.passive
                      << " passive_mag=" << d.passive_magnitude << " combine_count=" << d.combine_count
                      << " result=" << d.result << "(" << cambc::to_string(cambc::item_type{d.result}) << ")"
                      << " combine_cost=" << d.combine_cost;
        std::cout << '\n';
    }
    for (std::uint32_t i = 0; i < 5; ++i) {
        cambc::detail::consumable_info d{};
        int code = cambc::detail::sdk_consumable_info(i, &d);
        std::cout << P(w) << "consumable raw_id=" << i << " code=" << code << " cost=" << d.cost
                  << " carry_limit=" << d.carry_limit << '\n';
    }
    for (std::uint32_t i = 0; i < 2; ++i) {
        cambc::consumable_type t{i};
        std::cout << P(w) << "consumable_wrapper " << cambc::to_string(t) << " cost=" << t.cost()
                  << " carry_limit=" << t.carry_limit() << '\n';
    }
}

inline void dump_ability(const std::string& w, const std::string& owner, int slot, const cambc::detail::ability_props& a) {
    std::cout << P(w) << "ability owner=" << owner << " slot=" << slot << " kind=" << a.kind << " cooldown=" << a.cooldown
              << " max_charges=" << a.max_charges << " targets=" << hexu(a.targets) << " attributes=" << hexu(a.attributes);
    const auto& p = a.payload;
    switch (a.kind) {
    case 1: std::cout << " type=attack_reset enhanced=" << p.enhanced_attack; break;
    case 2: std::cout << " type=damage range=" << p.damage.range << " modifier=" << p.damage.modifier; break;
    case 3: std::cout << " type=aoe_damage range=" << p.aoe_damage.range << " radius=" << p.aoe_damage.radius
                      << " modifier=" << p.aoe_damage.modifier << " duration=" << p.aoe_damage.duration; break;
    case 4: std::cout << " type=cc range=" << p.cc.range << " modifier=" << p.cc.modifier << " duration=" << p.cc.duration; break;
    case 5: std::cout << " type=heal range=" << p.heal.range << " modifier=" << p.heal.modifier; break;
    case 6: std::cout << " type=dash range=" << p.dash_range; break;
    case 7: std::cout << " type=shield range=" << p.shield.range << " modifier=" << p.shield.modifier
                      << " duration=" << p.shield.duration; break;
    default: std::cout << " type=none"; break;
    }
    std::uint32_t raw[4];
    std::memcpy(raw, &p, sizeof raw);
    std::cout << " raw=" << hexu(raw[0]) << "/" << hexu(raw[1]) << "/" << hexu(raw[2]) << "/" << hexu(raw[3]) << '\n';
}

inline void dump_def(const std::string& w, const std::string& owner, const cambc::detail::unit_definition& d) {
    std::cout << P(w) << "def owner=" << owner << " type=" << d.type << " vision_type=" << d.vision_type
              << " passive_type=" << int(d.passive_type) << "("
              << cambc::to_string(static_cast<cambc::passive_type>(d.passive_type)) << ") attack_type=" << int(d.attack_type)
              << '\n';
    for (int s = 0; s < 2; ++s) dump_ability(w, owner, s, d.abilities[s]);
}

// 3. Champion designs for champion_type 0..12 (12 should be invalid).
inline void dump_champion_designs(const std::string& w) {
    for (int t = 0; t <= 12; ++t) {
        cambc::detail::champion_design d{};
        int code = cambc::detail::sdk_champion_design(t, &d);
        std::string name = cambc::to_string(static_cast<cambc::champion_type>(t));
        std::cout << P(w) << "champ_design id=" << t << " name=" << name << " code=" << code;
        if (code != 0) { std::cout << '\n'; continue; }
        const auto& b = d.base_stats;
        std::cout << " vision=" << b.vision_radius << " move=" << b.base_move_speed << " range=" << b.base_attack_range
                  << " hp=" << b.base_health << " hp_g=" << b.health_growth << " str=" << b.base_strength
                  << " str_g=" << b.strength_growth << " foc=" << b.base_focus << " foc_g=" << b.focus_growth
                  << " camp_dmg_mult=" << b.camp_damage_multiplier << '\n';
        dump_def(w, name, d.definition);
    }
}

// 4. Camp designs for camp_type 0..5 (5 should be invalid).
inline void dump_camp_designs(const std::string& w) {
    for (int t = 0; t <= 5; ++t) {
        cambc::detail::camp_design d{};
        int code = cambc::detail::sdk_camp_design(t, &d);
        std::string name = cambc::to_string(static_cast<cambc::camp_type>(t));
        std::cout << P(w) << "camp_design id=" << t << " name=" << name << " code=" << code;
        if (code != 0) { std::cout << '\n'; continue; }
        const auto& b = d.base_stats;
        std::cout << " vision=" << b.vision_radius << " move=" << b.base_move_speed << " range=" << b.base_attack_range
                  << " hp=" << b.base_health << " hp_g=" << b.health_growth << " str=" << b.base_strength
                  << " str_g=" << b.strength_growth << " foc=" << b.base_focus << " foc_g=" << b.focus_growth << '\n';
        dump_def(w, name, d.definition);
    }
}

// 5. Compile-time passive constants in the SDK header.
inline void dump_passives(const std::string& w) {
    namespace pa = cambc::constants::passive_abilities;
    std::cout << P(w) << "passive_consts prism_focus_per_gem=" << pa::prism_focus_per_gem
              << " varg_splash_radius=" << pa::varg_splash_radius
              << " vesper_vale_bonus_gold_percent=" << pa::vesper_vale_bonus_gold_percent
              << " ryth_health_strength_ratio=" << pa::ryth_health_strength_ratio
              << " ren_retaliation_focus_ratio=" << pa::ren_retaliation_focus_ratio << '\n';
}

inline std::string list(const cambc::bitboard& b, std::size_t max = 400) {
    std::string out;
    std::size_t n = 0;
    for (auto p : b.positions()) {
        if (n++ >= max) { out += "..."; break; }
        out += pos(p) + ";";
    }
    return out;
}

// Static spawn tile of a camp (camp::position() needs a running game, not the draft).
inline cambc::vec2 camp_pos(const cambc::camp& c) {
    cambc::detail::camp_info ci{};
    cambc::detail::check(cambc::detail::sdk_map_camp_info(static_cast<std::uint32_t>(static_cast<cambc::handle_camp_t>(c)), &ci));
    return {ci.x, ci.y};
}

inline const char* eq(const cambc::bitboard& a, const cambc::bitboard& b) { return a == b ? "Y" : "n"; }

// 6/7. Map layout, spawn regions, camps, symmetry checks, coordinate layout.
inline void dump_map(const std::string& w) {
    const auto& m = cambc::detail::layout();
    std::cout << P(w) << "map width=" << m.width << " height=" << m.height << " chunked_w=" << m.chunked_width
              << " chunked_h=" << m.chunked_height << " stride=" << m.chunk_stride << " board_bytes=" << m.board_bytes
              << " field_bytes=" << m.field_bytes << " symmetry=" << cambc::to_string(cambc::map::symmetry())
              << " my_team_abs=" << cambc::detail::sdk_my_team() << " team_size=" << cambc::draft::team_size() << '\n';
    for (int t = 0; t < 2; ++t) {
        cambc::detail::aabb a{};
        int code = cambc::detail::sdk_spawn_region(t, &a);
        std::cout << P(w) << "spawn_abs team=" << t << " code=" << code << " min=" << a.min_x << "," << a.min_y
                  << " max_excl=" << a.max_x << "," << a.max_y << '\n';
    }
    const auto& ally = cambc::map::spawn_region(cambc::team::ally);
    const auto& enemy = cambc::map::spawn_region(cambc::team::enemy);
    std::cout << P(w) << "spawn ally=" << list(ally) << " enemy=" << list(enemy) << '\n';
    const auto& walls = cambc::map::walls();
    const auto& holes = cambc::map::holes();
    const auto& bushes = cambc::map::bushes();
    const auto& altars = cambc::map::altars();
    std::cout << P(w) << "terrain walls=" << walls.count() << " holes=" << holes.count() << " bushes=" << bushes.count()
              << " altars=" << altars.count() << " altar_tiles=" << list(altars) << '\n';
    cambc::bitboard camps;
    camps.clear();
    for (const auto& g : cambc::map::camp_groups()) {
        std::cout << P(w) << "camp_group handle=" << static_cast<std::uint32_t>(static_cast<cambc::handle_camp_group_t>(g))
                  << " gold=" << g.gold_value() << " gems=" << g.gem_value() << " respawn=" << g.max_respawn_timer() << " camps=";
        for (const auto& c : g.camps()) {
            std::cout << cambc::to_string(c.kind()) << "@" << pos(camp_pos(c)) << "#"
                      << static_cast<std::uint32_t>(static_cast<cambc::handle_camp_t>(c)) << ";";
            camps.set(camp_pos(c));
        }
        std::cout << '\n';
    }
    // Which reflection maps each feature onto itself / ally spawn onto enemy spawn.
    using S = cambc::symmetry;
    for (auto s : {S::horizontal, S::vertical, S::rotational180}) {
        std::cout << P(w) << "symcheck " << cambc::to_string(s) << " ally->enemy=" << eq(ally.reflect(s), enemy)
                  << " walls=" << eq(walls.reflect(s), walls) << " holes=" << eq(holes.reflect(s), holes)
                  << " bushes=" << eq(bushes.reflect(s), bushes) << " altars=" << eq(altars.reflect(s), altars)
                  << " camps=" << eq(camps.reflect(s), camps) << '\n';
    }
    for (cambc::vec2 p : {cambc::vec2{0, 0}, cambc::vec2{1, 2}}) {
        std::cout << P(w) << "reflect_pos p=" << pos(p) << " h=" << pos(cambc::map::reflect_horizontal(p))
                  << " v=" << pos(cambc::map::reflect_vertical(p)) << " r180=" << pos(cambc::map::rotate_180(p)) << '\n';
    }
}

// Coordinate conventions: vec2 constants, linear-buffer index of (1,0)/(0,1),
// shift_up/shift_right direction, and an ASCII rendering of the terrain.
inline void dump_layout(const std::string& w, bool ascii) {
    using V = cambc::vec2;
    std::cout << P(w) << "vec2 N=" << pos(V::north) << " NE=" << pos(V::north_east) << " E=" << pos(V::east)
              << " SE=" << pos(V::south_east) << " S=" << pos(V::south) << " SW=" << pos(V::south_west)
              << " W=" << pos(V::west) << " NW=" << pos(V::north_west) << '\n';
    for (V p : {V{1, 0}, V{0, 1}}) {
        cambc::bitboard b;
        b.clear();
        b.set(p);
        auto lin = b.export_linear_buffer();
        int idx = -1;
        for (std::size_t i = 0; i < lin.size(); ++i) if (lin[i]) idx = int(i);
        auto up = b.shift_up(1).positions();
        auto right = b.shift_right(1).positions();
        std::cout << P(w) << "linear set=" << pos(p) << " index=" << idx << " size=" << lin.size()
                  << " shift_up1=" << (up.empty() ? "none" : pos(up[0]))
                  << " shift_right1=" << (right.empty() ? "none" : pos(right[0])) << '\n';
    }
    // Engine print of a board with (0,0) and (3,1) set, to see its row orientation.
    {
        cambc::bitboard b;
        b.clear();
        b.set(V{0, 0});
        b.set(V{3, 1});
        std::cout << P(w) << "engine_print_begin set=0,0;3,1" << std::endl;
        std::cout.flush();
        b.print();
        std::fflush(nullptr);
        std::cout << P(w) << "engine_print_end" << std::endl;
    }
    if (!ascii) return;
    // Rows printed y = height-1 .. 0; W wall, H hole, B bush, A altar, a/e spawn, C camp.
    cambc::bitboard camps;
    camps.clear();
    for (const auto& g : cambc::map::camp_groups())
        for (const auto& c : g.camps()) camps.set(camp_pos(c));
    const int W = cambc::map::width(), H = cambc::map::height();
    for (int y = H - 1; y >= 0; --y) {
        std::string row;
        for (int x = 0; x < W; ++x) {
            V p{x, y};
            char ch = '.';
            if (cambc::map::walls().is_set(p)) ch = 'W';
            else if (cambc::map::holes().is_set(p)) ch = 'H';
            else if (cambc::map::altars().is_set(p)) ch = 'A';
            else if (camps.is_set(p)) ch = 'C';
            else if (cambc::map::spawn_region(cambc::team::ally).is_set(p)) ch = 'a';
            else if (cambc::map::spawn_region(cambc::team::enemy).is_set(p)) ch = 'e';
            else if (cambc::map::bushes().is_set(p)) ch = 'B';
            row += ch;
        }
        std::cout << P(w) << "row y=" << (y < 10 ? "0" : "") << y << " " << row << '\n';
    }
}

// 8. Draft view: raw draft_get per team/slot (absolute teams).
inline void dump_draft_state(const std::string& w) {
    std::uint8_t n = 0;
    int c = cambc::detail::sdk_draft_num_rounds(&n);
    std::cout << P(w) << "draft_state num_rounds=" << int(n) << " code=" << c << " fuel=" << cambc::fuel_remaining();
    for (int t = 0; t < 2; ++t) {
        std::cout << " abs" << t << "=[";
        for (std::uint32_t r = 0; r < n; ++r) {
            std::int32_t pick = -99;
            int code = cambc::detail::sdk_draft_get(t, r, &pick);
            std::cout << (code == 0 ? std::to_string(pick) : "c" + std::to_string(code)) << (r + 1 < n ? "," : "");
        }
        std::cout << "]";
    }
    std::cout << " ally_list=";
    for (auto p : cambc::draft::current_draft(cambc::team::ally)) std::cout << int(p) << ";";
    std::cout << " enemy_list=";
    for (auto p : cambc::draft::current_draft(cambc::team::enemy)) std::cout << int(p) << ";";
    std::cout << '\n';
}

} // namespace probe
