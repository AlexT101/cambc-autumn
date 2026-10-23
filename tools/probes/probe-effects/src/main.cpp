// probe-effects: lingering area effects, stuns on camps, Varg shield/splash, Marcella enhanced attack,
// Ren retaliation, Prism gem Focus, Vendetta kill reset. Opponent: probe-effects-b (passive; its 4th pick,
// Ryth, walks to (11,21) and steps into (11,20) after it sees the gem row (10..12,18) lose HP).
// Select the run with RUN below (1, 2 or 3), rebuild, then:
//   cambc build probe-effects && cambc build probe-effects-b
//   cambc run probe-effects probe-effects-b --map interlock --rounds 140 --fuel 50000000 -o <dir>
// RUN 1: Ryth/Stellar/Prism area casts at (11,19) on rounds 41/61/81 (nobody attacks the row before 86),
//        Varg splash on row (27..29,21), then the row is killed and Prism captures it (Focus vs gems).
// RUN 2: Varg shield vs wolf (5,8); Marcella enhanced attack vs wolf (5,14); Ren retaliation vs wolf (5,21);
//        Vendetta kill-reset on gold pair (19,2)/(19,3).
// RUN 3: stuns on woken wolves: Ryth area (5,8), Cassi stun (5,14), Prism dmg+stun (5,21).
#ifndef RUN
#define RUN 1
#endif
#include <cambc.h>
#include <algorithm>
#include <array>
#include <functional>
#include <iomanip>
#include <iostream>
#include <map>
#include <optional>
#include <sstream>
#include <string>
#include <type_traits>
#include <variant>
#include <vector>

using cambc::vec2;
using cambc::team;
using cambc::champion_type;
using cambc::buff_types;

namespace {

std::string P(vec2 p) { return "(" + std::to_string(p.x) + "," + std::to_string(p.y) + ")"; }
std::string me_name() { return cambc::to_string(cambc::self().champion_name()); }

#define PROBE(x)                                                                                                  \
    do {                                                                                                          \
        std::ostringstream probe_os_;                                                                             \
        probe_os_ << std::fixed << std::setprecision(2) << x;                                                     \
        std::cout << "PROBE " << cambc::round_number() << ' ' << me_name() << ' ' << probe_os_.str() << '\n';    \
    } while (0)

std::string F(float v) { std::ostringstream os; os << std::fixed << std::setprecision(2) << v; return os.str(); }

std::string buffs_str(const cambc::unit& u) {
    try {
        auto b = u.buffs();
        std::string s = "[";
        if (b.has(buff_types::shield)) {
            auto v = b.get<cambc::buff_shield>();
            s += "shield:d=" + std::to_string(v.duration) + ",v=" + F(v.value) + " ";
        }
        if (b.has(buff_types::stun)) s += "stun:d=" + std::to_string(b.get<cambc::buff_stun>().duration) + " ";
        if (b.has(buff_types::enhanced_attack))
            s += "enh:d=" + std::to_string(b.get<cambc::buff_enhanced_attack>().duration) + " ";
        return s + "]";
    } catch (const std::exception& e) { return std::string("[EXC ") + e.what() + "]"; }
}

// Cached camps by spawn tile (map::camp() costs a full camp_groups() scan).
std::map<std::pair<int, int>, cambc::camp> g_camps;
void cache_camps() {
    for (const auto& grp : cambc::map::camp_groups())
        for (const auto& c : grp) g_camps.emplace(std::pair{ c.spawn_position().x, c.spawn_position().y }, c);
}
std::optional<cambc::camp> camp_at(vec2 p) {
    auto it = g_camps.find({ p.x, p.y });
    if (it == g_camps.end()) return std::nullopt;
    return it->second;
}
// "(x,y)=hp{buffs}cd=a/b" or hidden/dead.
std::string camp_str(vec2 p) {
    auto c = camp_at(p);
    if (!c) return P(p) + "=none";
    cambc::detail::camp_state st{};
    const auto code = cambc::detail::sdk_camp(static_cast<std::uint32_t>(static_cast<cambc::handle_camp_t>(*c)), &st);
    if (code != 0) return P(p) + "=code" + std::to_string(code);
    return P(p) + "=" + F(st.health) + buffs_str(*c) + "cd=" + std::to_string(st.cooldowns[0]) + "/" + std::to_string(st.cooldowns[1]);
}
float camp_hp(vec2 p) {
    auto c = camp_at(p);
    if (!c) return -1;
    try { return c->is_visible() ? c->health() : -2; } catch (...) { return -3; }
}

std::string self_str() {
    auto& me = cambc::self();
    auto ab = me.abilities();
    std::ostringstream os;
    os << std::fixed << std::setprecision(2) << "pos=" << P(me.position()) << " hp=" << me.health() << " foc=" << me.focus()
       << " str=" << me.strength() << " gems=" << me.gem_count() << " cd0=" << ab[0].cooldown() << " cd1=" << ab[1].cooldown()
       << " atk=" << me.can_attack() << " mv=" << me.can_move() << " cast=" << me.can_cast() << " buffs=" << buffs_str(me);
    return os.str();
}

std::vector<vec2> g_watch;
std::string watch_str() {
    std::string s;
    for (auto p : g_watch) s += camp_str(p) + " ";
    return s;
}
// Visible enemy champions with hp/buffs.
std::string enemies_str() {
    std::string s;
    for (const auto& e : cambc::champions(team::enemy)) {
        try {
            if (!e.is_visible()) continue;
            s += cambc::to_string(e.champion_name()) + "@" + P(e.position()) + "=" + F(e.health()) + buffs_str(e) + " ";
        } catch (...) {}
    }
    return s;
}

template <class F> bool act(const std::string& label, F&& f) {
    std::string res;
    bool ok = false;
    try {
        if constexpr (std::is_void_v<decltype(f())>) { f(); res = "OK"; }
        else res = std::string("OK ret=") + (f() ? "true" : "false");
        ok = true;
    } catch (const cambc::error& e) {
        res = "ERR=" + cambc::to_string(e.code()) + " msg=\"" + e.message() + "\"";
    } catch (const std::exception& e) { res = std::string("EXC=\"") + e.what() + "\""; }
    PROBE("act=" << label << " " << res << " | " << self_str() << " | W " << watch_str());
    return ok;
}
bool attack_camp(vec2 p) {
    auto c = camp_at(p);
    return act("attack" + P(p), [&] { cambc::self().attack(*c); });
}
bool cast_self(int slot) { return act("cast" + std::to_string(slot) + "_self", [&] { return cambc::self().abilities()[slot].use(); }); }
bool cast_ground(int slot, vec2 p) {
    return act("cast" + std::to_string(slot) + "_ground" + P(p), [&] { return cambc::self().abilities()[slot].use(p); });
}
bool cast_camp(int slot, vec2 p) {
    auto c = camp_at(p);
    return act("cast" + std::to_string(slot) + "_camp" + P(p), [&] { return cambc::self().abilities()[slot].use(*c); });
}
bool dash_to(int slot, vec2 p) {
    return act("dash->" + P(p), [&] { return cambc::self().abilities()[slot].use(p); });
}

// Scripted steps: travel to pos, then run fn once per turn until it returns true.
struct Step { std::string name; std::optional<vec2> pos; std::function<bool(int)> fn; };
struct Script {
    std::vector<Step> steps;
    std::size_t idx = 0;
    int turns = 0;  // turns spent in the current step (fn's argument)
    void add(std::string n, std::optional<vec2> p, std::function<bool(int)> f) { steps.push_back({ std::move(n), p, std::move(f) }); }
    void run() {
        auto& me = cambc::self();
        if (idx >= steps.size()) return;
        auto& s = steps[idx];
        if (s.pos && me.position() != *s.pos) {
            try { me.move_towards(*s.pos); } catch (const std::exception& e) { PROBE("travel EXC " << e.what()); }
            return;
        }
        bool done = s.fn(turns);
        ++turns;
        if (done) { PROBE("step_done " << s.name); ++idx; turns = 0; }
    }
};
auto wait_round(int r) { return [r](int) { return cambc::round_number() >= r; }; }
auto idle() { return [](int) { return false; }; }

const vec2 R1{ 10, 18 }, R2{ 11, 18 }, R3{ 12, 18 };       // gem row group A
const vec2 Q1{ 27, 21 }, Q2{ 28, 21 }, Q3{ 29, 21 };       // gem row group B
const vec2 W1{ 5, 8 }, W2{ 5, 14 }, W3{ 5, 21 };           // wolves
const vec2 G1{ 19, 2 }, G2{ 19, 3 };                        // gold pair

// ======================================================================== RUN 1
std::optional<vec2> row_alive() {
    for (auto p : { R2, R1, R3 }) if (camp_hp(p) > 0) return p;
    return std::nullopt;
}
bool attack_row() {
    auto& me = cambc::self();
    for (auto p : { R2, R1, R3 }) {
        if (camp_hp(p) <= 0) continue;
        if (me.position().chebyshev_distance(p) > me.attack_range()) continue;
        if (me.can_attack()) return attack_camp(p);
    }
    return false;
}
void build_run1(Script& s, champion_type who) {
    g_watch = { R1, R2, R3, Q1, Q2, Q3 };
    const vec2 C{ 11, 19 };
    switch (who) {
    case champion_type::ryth:
        s.add("ryth_cast", vec2{ 14, 18 }, [=](int) {
            if (cambc::round_number() < 41) return false;
            cast_ground(0, C);  // no attack this turn
            return true;
        });
        s.add("wait86", std::nullopt, wait_round(86));
        // Replays the old allowances sequence: area cast then basic attack in the same turn.
        s.add("ryth_cast_then_attack", vec2{ 11, 17 }, [=](int) {
            if (!cambc::self().abilities()[0].is_ready()) return false;
            cast_ground(0, C);
            attack_camp(R2);
            return true;
        });
        s.add("kill_row", vec2{ 11, 17 }, [](int) { attack_row(); return !row_alive(); });
        s.add("idle", std::nullopt, idle());
        break;
    case champion_type::stellar:
        s.add("stellar_cast", vec2{ 14, 22 }, [=](int) {
            if (cambc::round_number() < 61) return false;
            cast_ground(1, C);
            return true;
        });
        s.add("wait86", std::nullopt, wait_round(86));
        s.add("kill_row", vec2{ 12, 21 }, [](int) { attack_row(); return !row_alive(); });
        s.add("idle", std::nullopt, idle());
        break;
    case champion_type::prism:
        s.add("prism_cast", vec2{ 9, 23 }, [=](int) {
            if (cambc::round_number() < 81) return false;
            cast_ground(1, C);
            return true;
        });
        s.add("wait86", std::nullopt, wait_round(86));
        s.add("kill_row", vec2{ 9, 21 }, [](int) { attack_row(); return !row_alive(); });
        s.add("capture", vec2{ 11, 18 }, [](int t) { return cambc::self().gem_count() > 0 && t > 3; });
        s.add("idle", std::nullopt, idle());
        break;
    case champion_type::varg:
        s.add("splash_mid", vec2{ 28, 20 }, [](int) {
            if (cambc::round_number() < 45) return false;
            attack_camp(Q2);
            return true;
        });
        s.add("splash_edge", std::nullopt, [](int) { attack_camp(Q1); return true; });
        s.add("idle", std::nullopt, idle());
        break;
    default: break;
    }
}

// ======================================================================== RUN 2
void build_run2(Script& s, champion_type who) {
    g_watch = { W1, W2, W3, G1, G2 };
    switch (who) {
    case champion_type::varg:
        s.add("wake", vec2{ 5, 9 }, [](int) { if (cambc::round_number() < 30) return false; attack_camp(W1); return true; });
        s.add("baseline", std::nullopt, [](int t) { attack_camp(W1); return t >= 1; });
        s.add("shield", std::nullopt, [](int) { cast_self(1); attack_camp(W1); return true; });
        s.add("hit_under_shield", std::nullopt, [](int t) { attack_camp(W1); return t >= 9; });
        s.add("sit_no_attack", std::nullopt, [](int t) { return t >= 5; });
        s.add("home", vec2{ 1, 1 }, idle());
        break;
    case champion_type::marcella:
        s.add("wake", vec2{ 5, 13 }, [](int) { if (cambc::round_number() < 30) return false; attack_camp(W2); return true; });
        s.add("baseline", std::nullopt, [](int t) { attack_camp(W2); return t >= 1; });
        s.add("enhanced_now", std::nullopt, [](int) { attack_camp(W2); cast_self(0); attack_camp(W2); return true; });
        s.add("attack_on", std::nullopt, [](int) { attack_camp(W2); return cambc::self().abilities()[0].is_ready(); });
        s.add("enh_unused", std::nullopt, [](int t) {
            if (t == 0) { attack_camp(W2); cast_self(0); return false; }   // reset, keep the enhanced attack
            const bool has = cambc::self().buffs().has(buff_types::enhanced_attack);
            if (!has || t >= 8) { attack_camp(W2); return true; }  // gone or timeout: attack once
            return false;
        });
        s.add("after", std::nullopt, [](int t) { attack_camp(W2); return t >= 3; });
        s.add("home", vec2{ 1, 1 }, idle());
        break;
    case champion_type::ren:
        s.add("wake", vec2{ 5, 20 }, [](int) { if (cambc::round_number() < 30) return false; attack_camp(W3); return true; });
        s.add("sit", std::nullopt, [](int t) { return t >= 7; });
        s.add("stun", std::nullopt, [](int) { cast_camp(0, W3); return true; });
        s.add("sit2", std::nullopt, [](int t) { return t >= 6; });
        s.add("home", vec2{ 1, 1 }, idle());
        break;
    case champion_type::vendetta:
        s.add("kill_g1", vec2{ 18, 2 }, [](int) {
            auto& me = cambc::self();
            float hp = camp_hp(G1);
            if (hp <= 0) return true;
            if (hp > 140) { attack_camp(G1); return false; }
            if (hp > 70) {
                dash_to(1, me.position() == vec2{ 18, 2 } ? vec2{ 18, 3 } : vec2{ 18, 2 });
                attack_camp(G1);
                return false;
            }
            PROBE("pre_kill " << self_str());
            attack_camp(G1);
            PROBE("post_kill " << self_str());
            return true;
        });
        s.add("kill_g2", std::nullopt, [](int) {
            float hp = camp_hp(G2);
            if (hp <= 0) return true;
            if (hp > 140) { attack_camp(G2); return false; }
            attack_camp(G2);
            cast_self(0);
            PROBE("pre_kill " << self_str());
            attack_camp(G2);
            PROBE("post_kill " << self_str());
            return true;
        });
        s.add("idle", std::nullopt, idle());
        break;
    default: break;
    }
}

// ======================================================================== RUN 3
void build_run3(Script& s, champion_type who) {
    g_watch = { W1, W2, W3 };
    switch (who) {
    case champion_type::ryth:
        s.add("wake", vec2{ 5, 9 }, [](int) { if (cambc::round_number() < 30) return false; attack_camp(W1); return true; });
        s.add("baseline", std::nullopt, [](int t) { attack_camp(W1); return t >= 1; });
        s.add("area_stun", std::nullopt, [](int) { cast_ground(0, vec2{ 5, 7 }); attack_camp(W1); return true; });
        s.add("after", std::nullopt, [](int t) { attack_camp(W1); return t >= 6; });
        s.add("home", vec2{ 1, 1 }, idle());
        break;
    case champion_type::cassi:
        s.add("wake", vec2{ 5, 12 }, [](int) { if (cambc::round_number() < 30) return false; attack_camp(W2); return true; });
        s.add("baseline", std::nullopt, [](int t) { attack_camp(W2); return t >= 1; });
        s.add("stun", std::nullopt, [](int) { cast_camp(1, W2); attack_camp(W2); return true; });
        s.add("after", std::nullopt, [](int t) { attack_camp(W2); return t >= 6; });
        s.add("home", vec2{ 1, 1 }, idle());
        break;
    case champion_type::prism:
        s.add("wake", vec2{ 5, 18 }, [](int) { if (cambc::round_number() < 30) return false; attack_camp(W3); return true; });
        s.add("baseline", std::nullopt, [](int t) { attack_camp(W3); return t >= 1; });
        s.add("stun", std::nullopt, [](int) { cast_camp(0, W3); attack_camp(W3); return true; });
        s.add("after", std::nullopt, [](int t) { attack_camp(W3); return t >= 6; });
        s.add("home", vec2{ 1, 1 }, idle());
        break;
    default: break;
    }
}

constexpr std::array<cambc::champion_draft, 4> picks() {
    using D = cambc::champion_draft;
    if (RUN == 1) return { D::ryth, D::stellar, D::prism, D::varg };
    if (RUN == 2) return { D::varg, D::marcella, D::ren, D::vendetta };
    return { D::ryth, D::cassi_and_issac, D::prism, D::stellar };
}

Script g_script;
bool g_built = false;

void play_turn() {
    auto& me = cambc::self();
    if (!g_built) {
        g_built = true;
        cache_camps();
        if (RUN == 1) build_run1(g_script, me.champion_name());
        else if (RUN == 2) build_run2(g_script, me.champion_name());
        else build_run3(g_script, me.champion_name());
        auto ab = me.abilities();
        for (int i = 0; i < 2; ++i) {
            std::string desc = "none";
            if (const auto& info = ab[i].info())
                std::visit([&](const auto& v) {
                    std::ostringstream os;
                    os << cambc::to_string(v.kind) << " maxcd=" << v.max_cooldown;
                    using T = std::decay_t<decltype(v)>;
                    if constexpr (std::is_same_v<T, cambc::ability_aoe_damage>)
                        os << " range=" << v.range << " mod=" << v.modifier << " radius=" << v.radius << " duration=" << v.duration;
                    if constexpr (std::is_same_v<T, cambc::ability_cc> || std::is_same_v<T, cambc::ability_shield>)
                        os << " range=" << v.range << " mod=" << v.modifier << " duration=" << v.duration;
                    if constexpr (std::is_same_v<T, cambc::ability_damage>) os << " range=" << v.range << " mod=" << v.modifier;
                    if constexpr (std::is_same_v<T, cambc::ability_attack_reset>) os << " enhanced=" << v.enhanced_attack;
                    desc = os.str();
                }, *info);
            PROBE("ability slot=" << i << " " << desc);
        }
    }
    if (!me.is_alive()) { PROBE("dead"); return; }
    const bool verbose = cambc::round_number() >= 28;
    if (verbose) PROBE("ST " << self_str() << " | W " << watch_str() << "| E " << enemies_str());
    g_script.run();
    if (verbose) PROBE("END " << self_str() << " | W " << watch_str());
}

void play_draft() {
    const auto chosen = cambc::draft::current_draft(team::ally);
    for (auto p : picks())
        if (std::find(chosen.begin(), chosen.end(), p) == chosen.end()) { cambc::draft::pick(p); return; }
}
} // namespace

int main() {
    while (true) {
        try {
            if (cambc::is_draft()) play_draft();
            else play_turn();
        } catch (const std::exception& e) {
            std::cout << "PROBE err " << e.what() << '\n';
        } catch (...) { std::cout << "PROBE err unknown\n"; }
        cambc::end_turn();
    }
}
