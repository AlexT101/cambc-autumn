// probe-allowances: scripted experiments on per-turn action allowances.
// Run 1 (PROBE_RUN=1, default): Vesper Vale, Stellar, Cassi, Issac, Willow. Run 2: Tavi, Vendetta, Ryth, Varg.
// Select the run in config.h (PROBE_RUN). Map interlock, opponent probe-allowances-b:
//   cambc run probe-allowances probe-allowances-b --map interlock --rounds 330 --fuel 50000000 -o <dir>
// Each champion walks to a station, then runs its Script steps (see probe.h). Targets are harmless
// gem/gold clusters: gold pair (19,2)/(19,3), gem rows (10..12,18) and (27..29,21).
// Late steps use an enemy Varg that probe-allowances-b parks in the bush at (13,22) (hidden target).
#include <cambc.h>
#include "bot.h"
#include "config.h"
#include "probe.h"

using namespace probe;
using cambc::champion_type;

namespace {

// Attack every enemy handle (including those outside vision) and log engine responses.
bool attack_enemies() {
    auto& me = cambc::self();
    for (const auto& e : cambc::champions(team::enemy)) {
        bool vis = e.is_visible();
        act(std::string("attack_enemy vis=") + (vis ? "1" : "0") + (vis ? " at=" + P(e.position()) : std::string()),
            [&] { me.attack(e); });
    }
    return true;
}
bool cast_enemies(int slot) {
    auto& me = cambc::self();
    for (const auto& e : cambc::champions(team::enemy)) {
        bool vis = e.is_visible();
        act("cast" + std::to_string(slot) + "_enemy vis=" + (vis ? "1" : "0"), [&] { return me.abilities()[slot].use(e); });
    }
    return true;
}
std::string hp3(vec2 a, vec2 b, vec2 c) { return camp_hp(a) + " " + camp_hp(b) + " " + camp_hp(c); }

// ---------------------------------------------------------------- Vesper Vale (ranged; 0 reset, 1 dash)
void vesper(Script& s) {
    const vec2 V{ 16, 2 };  // gold pair at (19,2),(19,3) is 3 tiles east
    s.add("atk_then_walk", V, 0, [] { attack_cluster(); walk(0, 1); return true; });
    s.add("walk_then_atk", V, 0, [] { walk(0, 1); attack_cluster(); return true; });
    s.add("atk_reset_atk_walk", V, 1, [] { attack_cluster(); cast_self(0); attack_cluster(); walk(0, 1); return true; });
    s.add("atk_reset_walk_atk", V, 1, [] { attack_cluster(); cast_self(0); walk(0, 1); attack_cluster(); return true; });
    s.add("reset_atk_atk_walk", V, 1, [] { cast_self(0); attack_cluster(); attack_cluster(); walk(0, 1); return true; });
    s.add("walk_reset_atk", V, 1, [] { walk(0, 1); cast_self(0); attack_cluster(); return true; });
    // One successful cast per turn across slots: dash (slot1) then attack+reset (slot0).
    // (Reset can only be cast once the attack is spent, hence the attack first.)
    s.add("two_casts_same_turn", V, 3, [] { dash(1, 0, 2); attack_cluster(); cast_self(0); return true; });
    // Q1: slot1 was cast last step; try a 1-tile dash every turn until it succeeds (ST lines log cd1 each turn).
    s.add("cd_probe", std::nullopt, 0, [] {
        auto& me = cambc::self();
        const int dy = me.position().y >= 4 ? -1 : 1;
        return act("cd_probe_dash(0," + std::to_string(dy) + ")", [&] { return me.abilities()[1].use(me.position() + vec2{ 0, dy }); });
    });
    s.add("walk_dash_atk", V, 2, [] { walk(0, 1); dash(1, 0, -2); attack_cluster(); return true; });
    s.add("atk_dash_walk", V, 2, [] { attack_cluster(); dash(1, 0, 2); walk(0, -1); return true; });
    s.add("dash_then_walk", V, 2, [] { dash(1, 2, 0); walk(0, 1); return true; });
    s.add("walk_then_dash", V, 2, [] { walk(0, 1); dash(1, 2, 0); return true; });
    s.add("dash_then_atk", vec2{ 14, 2 }, 2, [] { dash(1, 2, 0); attack_cluster(); walk(0, 1); return true; });
    s.add("atk_then_dash", V, 2, [] { attack_cluster(); dash(1, -2, 0); return true; });
    s.add("dash_knight", V, 2, [] { dash(1, 2, 1); return true; });
    s.add("dash_1step", V, 2, [] { dash(1, 1, 0); return true; });
    s.add("dash_diag22", V, 2, [] { dash(1, -2, 2); return true; });
    s.add("dash_3_then_valid", V, 2, [] { dash(1, -3, 0); dash(1, 0, 2); return true; });
    s.add("dash_over_camp_diag", vec2{ 18, 1 }, 2, [] { dash(1, 2, 2, " only_mid=(19,2)camp"); return true; });
    s.add("atk_range_33", vec2{ 16, 0 }, 0, [] { attack_cluster(vec2{ 19, 3 }); return true; });
    s.add("atk_range_4", vec2{ 15, 0 }, 0, [] { attack_cluster(vec2{ 19, 3 }); attack_cluster(vec2{ 19, 2 }); return true; });
    // Cassi parks at (10,22) from ~round 63; (11,21) is adjacent to her.
    s.add("atk_ally", vec2{ 11, 21 }, 0, [] {
        auto a = ally_in_range(3);
        if (!a) { PROBE("act=attack_ally NO_ALLY"); return false; }
        auto& me = cambc::self();
        act("attack_ally at=" + P(a->position()), [&] { me.attack(*a); });
        return true;
    });
    s.add("hidden_enemy_ranged", vec2{ 11, 22 }, 0, [] {
        if (cambc::round_number() < kHiddenRound) { PROBE("wait hidden"); return false; }
        return attack_enemies();
    });
}

// ---------------------------------------------------------------- Issac (melee; 0 reset, 1 dash)
void issac(Script& s) {
    const vec2 I{ 11, 17 }, T{ 11, 18 };
    s.add("walk_then_atk", I, 0, [=] { walk(1, 0); attack_cluster(T); return true; });
    s.add("atk_then_walk", vec2{ 12, 17 }, 0, [=] { attack_cluster(T); walk(-1, 0); return true; });
    s.add("atk_reset_atk_walk", I, 1, [=] { attack_cluster(T); cast_self(0); attack_cluster(T); walk(1, 0); return true; });
    s.add("reset_atk_atk", I, 1, [=] { cast_self(0); attack_cluster(T); attack_cluster(T); return true; });
    s.add("walk_reset_atk_atk", I, 1, [=] { walk(1, 0); cast_self(0); attack_cluster(T); attack_cluster(T); return true; });
    s.add("atk_dist2", vec2{ 11, 16 }, 0, [] { attack_cluster(vec2{ 11, 18 }); attack_cluster(vec2{ 12, 18 }); return true; });
    s.add("dash_over_camp", I, 2, [] { dash(1, 0, 2, " over_camp(11,18)"); return true; });
    s.add("dash_then_walk", I, 2, [] { dash(1, -2, 0); walk(1, 0); return true; });
    s.add("walk_then_dash", I, 2, [] { walk(-1, 0); dash(1, 2, 0); return true; });
    s.add("dash_then_atk", vec2{ 11, 15 }, 2, [=] { dash(1, 0, 2); attack_cluster(T); return true; });
    s.add("atk_then_dash", I, 2, [=] { attack_cluster(T); dash(1, 0, -2); return true; });
    s.add("dash_onto_camp_then_1step", I, 2, [] { dash(1, 0, 1, " onto_camp"); dash(1, -1, 0, " 1step"); return true; });
    s.add("dash_over_wall", vec2{ 14, 9 }, 2, [] { dash(1, 2, 0, " over_wall(15,9)"); return true; });
    s.add("dash_knight_both_blocked", vec2{ 14, 14 }, 2,
        [] { dash(1, 2, 1, " mids(15,14)(15,15)=wall"); dash(1, 0, 2, " fallback"); return true; });
    s.add("dash_knight_one_blocked", vec2{ 14, 15 }, 2, [] { dash(1, 2, 1, " mids(15,15)=wall,(15,16)=free"); return true; });
    s.add("dash_onto_hole_then_valid", vec2{ 16, 18 }, 2,
        [] { dash(1, 0, 2, " onto_hole(16,20)"); dash(1, -2, 0, " fallback"); return true; });
    s.add("dash_over_hole_diag", vec2{ 15, 19 }, 2, [] { dash(1, 2, 2, " over_hole(16,20)"); return true; });
    s.add("dash_over_altar", vec2{ 18, 16 }, 2, [] { dash(1, 2, 0, " over_altar(19,16)"); return true; });
    s.add("dash_onto_then_over_ally", vec2{ 10, 21 }, 2, [] {
        if (cambc::round_number() < kHiddenRound) { PROBE("wait ally"); return false; }
        auto a = ally_in_range(2);
        PROBE("ally_near=" << (a ? P(a->position()) + " " + cambc::to_string(a->champion_name()) : std::string("none")));
        dash(1, 0, 1, " onto_ally?(10,22)");
        dash(1, 0, 2, " over_ally?(10,22)");
        return true;
    });
    s.add("dash_over_altar_diag", vec2{ 18, 15 }, 2, [] { dash(1, 2, 2, " only_mid=(19,16)altar"); return true; });
    s.add("dash_over_ally_diag", vec2{ 9, 21 }, 2, [] {
        auto a = ally_in_range(1);
        PROBE("ally_near=" << (a ? P(a->position()) + " " + cambc::to_string(a->champion_name()) : std::string("none")));
        dash(1, 2, 2, " only_mid=(10,22)");
        return true;
    });
    s.add("dash_over_hidden_enemy_diag", vec2{ 12, 21 }, 2, [] { dash(1, 2, 2, " only_mid=(13,22)bush_enemy"); return true; });
    s.add("hidden_enemy_melee", vec2{ 12, 22 }, 0, [] { return attack_enemies(); });
}

// ---------------------------------------------------------------- Cassi (ranged; 0 dmg excl, 1 stun compat)
void cassi(Script& s) {
    const vec2 C{ 13, 16 };
    s.add("stun_then_walk", C, 2, [] { cast_camp(1); walk(1, 0); return true; });
    s.add("stun_then_atk_walk", C, 2, [] { cast_camp(1); attack_cluster(); walk(1, 0); return true; });
    s.add("walk_then_stun_atk", C, 2, [] { walk(1, 0); cast_camp(1); attack_cluster(); return true; });
    s.add("dmg_then_walk_atk", C, 1, [] { cast_camp(0); walk(1, 0); attack_cluster(); return true; });
    s.add("dmg_then_atk_walk", C, 1, [] { cast_camp(0); attack_cluster(); walk(1, 0); return true; });
    s.add("walk_then_dmg", C, 1, [] { walk(1, 0); cast_camp(0); return true; });
    s.add("atk_then_dmg_walk", C, 1, [] { attack_cluster(); cast_camp(0); walk(1, 0); return true; });
    s.add("atk_then_stun_walk", C, 2, [] { attack_cluster(); cast_camp(1); walk(1, 0); return true; });
    s.add("hidden_enemy_spells", vec2{ 10, 22 }, 3, [] {
        if (cambc::round_number() < kHiddenRound) { PROBE("wait hidden"); return false; }
        cast_enemies(1);
        cast_enemies(0);
        return true;
    });
}

// ---------------------------------------------------------------- Stellar (ranged; 0 dmg excl, 1 aoe excl)
void stellar(Script& s) {
    const vec2 S{ 28, 24 }, A{ 27, 21 }, B{ 28, 21 }, C{ 29, 21 };
    s.add("walk_then_dmg", S, 1, [] { walk(1, 0); cast_camp(0); attack_cluster(); return true; });
    s.add("dmg_then_walk_atk", S, 1, [] { cast_camp(0); walk(1, 0); attack_cluster(); return true; });
    s.add("dmg_then_atk_walk", S, 1, [] { cast_camp(0); attack_cluster(); walk(1, 0); return true; });
    s.add("atk_then_dmg_walk", S, 1, [] { attack_cluster(); cast_camp(0); walk(1, 0); return true; });
    s.add("walk_then_aoe", S, 2, [=] {
        walk(1, 0);
        PROBE("before " << hp3(A, B, C));
        cast_ground(1, vec2{ 30, 22 });
        PROBE("after " << hp3(A, B, C));
        return true;
    });
    s.add("aoe_then_walk_atk", S, 2, [=] {
        PROBE("before " << hp3(A, B, C));
        cast_ground(1, vec2{ 30, 22 }, " diag_of(29,21)");
        PROBE("after " << hp3(A, B, C));
        walk(1, 0);
        attack_cluster();
        return true;
    });
    s.add("aoe_then_atk_walk", S, 2, [=] {
        PROBE("before " << hp3(A, B, C));
        cast_ground(1, vec2{ 31, 21 }, " dist2_of(29,21)");
        PROBE("after " << hp3(A, B, C));
        attack_cluster();
        walk(1, 0);
        return true;
    });
    s.add("atk_then_aoe", S, 2, [=] {
        attack_cluster();
        PROBE("before " << hp3(A, B, C));
        cast_ground(1, vec2{ 28, 20 }, " above_middle");
        PROBE("after " << hp3(A, B, C));
        return true;
    });
    s.add("aoe_dist5_then_diag44", S, 2, [] {
        cast_ground(1, vec2{ 33, 24 }, " dist5");
        cast_ground(1, vec2{ 32, 20 }, " diag(4,4)");
        return true;
    });
    s.add("aoe_wall_tile", vec2{ 26, 26 }, 2, [] {
        auto& me = cambc::self();
        const auto vis = cambc::vision::visible_tiles();
        for (int d = 1; d <= 4; ++d)
            for (int dy = -d; dy <= d; ++dy)
                for (int dx = -d; dx <= d; ++dx) {
                    vec2 p = me.position() + vec2{ dx, dy };
                    if (std::max(std::abs(dx), std::abs(dy)) != d || !cambc::map::is_in_bounds(p)) continue;
                    if (cambc::map::walls().is_set(p)) {
                        cast_ground(1, p, std::string(" wall vis=") + (vis.is_set(p) ? "1" : "0"));
                        return true;
                    }
                }
        PROBE("no wall in range");
        return true;
    });
    s.add("aoe_hidden_tile", vec2{ 26, 26 }, 2, [] {
        auto& me = cambc::self();
        const auto vis = cambc::vision::visible_tiles();
        for (int d = 1; d <= 4; ++d)
            for (int dy = -d; dy <= d; ++dy)
                for (int dx = -d; dx <= d; ++dx) {
                    vec2 p = me.position() + vec2{ dx, dy };
                    if (std::max(std::abs(dx), std::abs(dy)) != d || !cambc::map::is_in_bounds(p)) continue;
                    if (!vis.is_set(p) && !cambc::map::walls().is_set(p)) {
                        cast_ground(1, p, " not_visible_floor");
                        return true;
                    }
                }
        PROBE("no hidden tile in range");
        return true;
    });
    s.add("aoe_hole_tile", vec2{ 25, 22 }, 2, [] { cast_ground(1, vec2{ 22, 19 }, " hole"); return true; });
    s.add("aoe_on_ally", S, 2, [] {
        auto a = ally_in_range(4);
        if (!a) { PROBE("no ally"); return false; }
        const auto p = a->position();
        PROBE("ally " << cambc::to_string(a->champion_name()) << " at=" << P(p) << " hp_before=" << a->health());
        cast_ground(1, p, " ally_tile");
        PROBE("ally hp_after=" << a->health());
        return true;
    });
    s.add("dmg_on_ally", S, 1, [] {
        auto a = ally_in_range(4);
        if (!a) { PROBE("no ally"); return false; }
        auto& me = cambc::self();
        act("cast0_ally", [&] { return me.abilities()[0].use(*a); });
        return true;
    });
    // Ground AOE onto the bush tile hiding the enemy Varg (probe-allowances-b logs Varg's HP every 10 rounds).
    s.add("aoe_hidden_enemy", vec2{ 11, 25 }, 3, [] {
        if (cambc::round_number() < kHiddenRound) { PROBE("wait hidden"); return false; }
        const vec2 bush{ 13, 22 };
        PROBE("bush (13,22) visible=" << cambc::vision::visible_tiles().is_set(bush));
        cast_enemies(0);
        cast_ground(1, bush, " hidden_enemy_tile");
        return true;
    });
}

// ---------------------------------------------------------------- Willow (ranged; 0 heal compat, 1 reset)
bool heal_ally() {
    auto a = ally_in_range(4);
    if (!a) { PROBE("act=heal NO_ALLY | " << flags()); return false; }
    auto& me = cambc::self();
    return act("cast0_heal " + cambc::to_string(a->champion_name()) + " hp=" + std::to_string(int(a->health())),
        [&] { return me.abilities()[0].use(*a); });
}
void willow(Script& s) {
    const vec2 W{ 30, 24 };
    s.add("heal_then_walk", W, 1, [] { heal_ally(); walk(1, 0); return true; });
    s.add("heal_then_atk_walk", W, 1, [] { heal_ally(); attack_cluster(); walk(1, 0); return true; });
    s.add("walk_then_heal", W, 1, [] { walk(1, 0); heal_ally(); return true; });
    s.add("atk_then_heal_walk", W, 1, [] { attack_cluster(); heal_ally(); walk(1, 0); return true; });
    s.add("atk_reset_walk_atk", W, 2, [] { attack_cluster(); cast_self(1); walk(1, 0); attack_cluster(); return true; });
    s.add("atk_reset_atk_walk", W, 2, [] { attack_cluster(); cast_self(1); attack_cluster(); walk(1, 0); return true; });
    s.add("reset_atk_atk", W, 2, [] { cast_self(1); attack_cluster(); attack_cluster(); return true; });
    s.add("heal_self_then_ally", W, 1, [] {
        auto& me = cambc::self();
        act("cast0_self_target", [&] { return me.abilities()[0].use(me); });
        heal_ally();
        return true;
    });
}

// ================================================================ Run 2 champions (kRun == 2)
// ---------------------------------------------------------------- Tavi (ranged; 0 reset, 1 dmg+stun excl)
void tavi(Script& s) {
    const vec2 V{ 16, 2 };  // gold pair 3 tiles east
    s.add("walk_then_dmg", V, 2, [] { walk(0, 1); cast_camp(1); attack_cluster(); return true; });
    s.add("dmg_then_walk_atk", V, 2, [] { cast_camp(1); walk(0, 1); attack_cluster(); return true; });
    s.add("dmg_then_atk_walk", V, 2, [] { cast_camp(1); attack_cluster(); walk(0, 1); return true; });
    s.add("atk_then_dmg", V, 2, [] { attack_cluster(); cast_camp(1); walk(0, 1); return true; });
    s.add("atk_reset_atk_walk", V, 1, [] { attack_cluster(); cast_self(0); attack_cluster(); walk(0, 1); return true; });
    s.add("walk_reset_atk_atk", V, 1, [] { walk(0, 1); cast_self(0); attack_cluster(); attack_cluster(); return true; });
    s.add("atk_reset_dmg", V, 3, [] { attack_cluster(); cast_self(0); cast_camp(1); attack_cluster(); return true; });
}

// ---------------------------------------------------------------- Vendetta (melee; 0 reset, 1 dash)
void vendetta(Script& s) {
    const vec2 I{ 11, 17 }, T{ 11, 18 };
    s.add("walk_then_atk", I, 0, [=] { walk(1, 0); attack_cluster(T); return true; });
    s.add("atk_then_walk", vec2{ 12, 17 }, 0, [=] { attack_cluster(T); walk(-1, 0); return true; });
    s.add("atk_reset_atk_walk", I, 1, [=] { attack_cluster(T); cast_self(0); attack_cluster(T); walk(1, 0); return true; });
    s.add("walk_atk_reset_atk", I, 1, [=] { walk(1, 0); attack_cluster(T); cast_self(0); attack_cluster(T); return true; });
    s.add("dash_walk_atk", I, 2, [=] { dash(1, 2, 0); walk(-1, 0); attack_cluster(T); return true; });
    s.add("atk_walk_dash", I, 2, [=] { attack_cluster(T); walk(1, 0); dash(1, -2, 0); return true; });
    s.add("dash_3_then_2", I, 2, [] { dash(1, 3, 0, " dist3"); dash(1, 2, -2, " diag22"); return true; });
}

// ---------------------------------------------------------------- Ryth (melee; 0 ground area stun excl, 1 reset)
void ryth(Script& s) {
    const vec2 R{ 28, 22 };  // adjacent to clusters (27,21),(28,21),(29,21)
    const vec2 A{ 27, 21 }, B{ 28, 21 }, C{ 29, 21 };
    s.add("walk_then_aoe", R, 1, [=] { walk(0, 1); cast_ground(0, vec2{ 28, 20 }); return true; });
    s.add("aoe_then_walk_atk", R, 1, [=] {
        PROBE("before " << hp3(A, B, C));
        cast_ground(0, vec2{ 28, 20 }, " above_middle");
        PROBE("after " << hp3(A, B, C));
        walk(0, 1);
        attack_cluster();
        return true;
    });
    s.add("atk_then_aoe", R, 1, [=] { attack_cluster(); cast_ground(0, vec2{ 26, 20 }, " diag_of(27,21)"); return true; });
    s.add("atk_reset_atk_walk", R, 2, [=] { attack_cluster(); cast_self(1); attack_cluster(); walk(0, 1); return true; });
    s.add("aoe_on_ally", R, 1, [] {
        auto a = ally_in_range(4, champion_type::varg);
        if (!a) { PROBE("no varg"); return false; }
        const auto p = a->position();
        const vec2 t = p + vec2{ 1, 1 };  // 3x3 around t covers Varg's tile (diagonal), not Ryth or clusters
        PROBE("ally varg at=" << P(p) << " hp_before=" << a->health() << " rs_before=" << int(a->restrictions().bits()));
        cast_ground(0, t, " ally_diag");
        PROBE("ally varg hp_after=" << a->health() << " rs_after=" << int(a->restrictions().bits())
                                    << " stun=" << a->buffs().has(cambc::buff_types::stun));
        return true;
    });
    s.add("aoe_self_tile", R, 1, [] {
        auto& me = cambc::self();
        cast_ground(0, me.position(), " own_tile");
        PROBE("self after hp=" << me.health() << " stun=" << me.buffs().has(cambc::buff_types::stun));
        return true;
    });
    s.add("aoe_wall", vec2{ 26, 26 }, 1, [] { cast_ground(0, vec2{ 24, 24 }, " wall"); return true; });
}

// ---------------------------------------------------------------- Varg (melee; 0 reset, 1 shield self)
void varg(Script& s) {
    const vec2 G{ 30, 22 };  // adjacent to (29,21)
    s.add("shield_then_walk_atk", G, 2, [] { cast_self(1); walk(0, 1); attack_cluster(); return true; });
    s.add("atk_walk_reset_atk", G, 1, [] { attack_cluster(); walk(0, 1); cast_self(0); attack_cluster(); return true; });
    s.add("sit", G, 0, [] {
        auto& me = cambc::self();
        PROBE("varg sit hp=" << me.health() << " stun=" << me.buffs().has(cambc::buff_types::stun));
        return cambc::round_number() > 200;
    });
}

} // namespace

void Bot::play_turn() {
    auto& me = cambc::self();
    if (!built) {
        built = true;
        switch (me.champion_name()) {
        case champion_type::vesper_vale: vesper(script); break;
        case champion_type::issac: issac(script); break;
        case champion_type::cassi: cassi(script); break;
        case champion_type::stellar: stellar(script); break;
        case champion_type::willow: willow(script); break;
        case champion_type::tavi: tavi(script); break;
        case champion_type::vendetta: vendetta(script); break;
        case champion_type::ryth: ryth(script); break;
        case champion_type::varg: varg(script); break;
        default: break;
        }
        auto ab = me.abilities();
        for (int i = 0; i < 2; ++i) {
            std::string kind = "none";
            bool excl = false;
            int maxcd = -1;
            if (const auto& info = ab[i].info()) {
                std::visit([&](const auto& v) { kind = cambc::to_string(v.kind); excl = v.exclusive_with_movement; maxcd = v.max_cooldown; }, *info);
            }
            PROBE("ability slot=" << i << " kind=" << kind << " excl_move=" << excl << " max_cd=" << maxcd
                                  << " targets=" << ab[i].valid_targets().bits());
        }
        PROBE("attack_range=" << me.attack_range());
    }
    if (!me.is_alive()) return;
    script.run();
}
