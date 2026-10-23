// probe-effects-b: passive scripted opponent for probe-effects (see that bot's header for the run command).
// Draft: Willow, Tavi, Vesper Vale, Ryth. Everyone stays on spawn except the 4th pick (Ryth, the "walker"),
// which acts last among odd-round turns. The walker parks at (11,21), just outside a radius-1 area centred
// on (11,19). When it sees the gem row (10..12,18) lose HP since its previous turn, it steps into (11,20)
// (inside that area), stays 4 turns, then returns to (11,21). It never attacks or casts.
// Logs every turn from round 28: own hp/buffs and the row's hp/buffs/cooldowns.
#include <cambc.h>
#include <algorithm>
#include <array>
#include <iomanip>
#include <iostream>
#include <map>
#include <sstream>
#include <string>

using namespace cambc;

namespace {
std::string P(vec2 p) { return "(" + std::to_string(p.x) + "," + std::to_string(p.y) + ")"; }
std::string F(float v) { std::ostringstream os; os << std::fixed << std::setprecision(2) << v; return os.str(); }
std::string buffs_str(const unit& u) {
    try {
        auto b = u.buffs();
        std::string s = "[";
        if (b.has(buff_types::shield)) s += "shield:d=" + std::to_string(b.get<buff_shield>().duration) + ",v=" + F(b.get<buff_shield>().value) + " ";
        if (b.has(buff_types::stun)) s += "stun:d=" + std::to_string(b.get<buff_stun>().duration) + " ";
        if (b.has(buff_types::enhanced_attack)) s += "enh:d=" + std::to_string(b.get<buff_enhanced_attack>().duration) + " ";
        return s + "]";
    } catch (const std::exception& e) { return std::string("[EXC ") + e.what() + "]"; }
}
std::map<std::pair<int, int>, camp> g_camps;
const std::array<vec2, 3> kRow{ vec2{ 10, 18 }, vec2{ 11, 18 }, vec2{ 12, 18 } };
float hp_of(vec2 p) {
    auto it = g_camps.find({ p.x, p.y });
    if (it == g_camps.end()) return -1;
    try { return it->second.is_visible() ? it->second.health() : -2; } catch (...) { return -3; }
}
std::string row_str() {
    std::string s;
    for (auto p : kRow) {
        auto it = g_camps.find({ p.x, p.y });
        detail::camp_state st{};
        const auto code = detail::sdk_camp(static_cast<std::uint32_t>(static_cast<handle_camp_t>(it->second)), &st);
        if (code != 0) { s += P(p) + "=code" + std::to_string(code) + " "; continue; }
        s += P(p) + "=" + F(st.health) + buffs_str(it->second) + "cd=" + std::to_string(st.cooldowns[0]) + "/" + std::to_string(st.cooldowns[1]) + " ";
    }
    return s;
}
void log(const std::string& what) {
    auto& me = self();
    std::cout << "PROBE " << round_number() << " B." << to_string(me.champion_name()) << " " << what << " pos=" << P(me.position())
              << " hp=" << F(me.health()) << " buffs=" << buffs_str(me) << " mv=" << me.can_move() << " | W " << row_str() << '\n';
}

bool g_init = false;
float g_prev = -1;  // summed row hp at the walker's previous turn
int g_in = -1;      // turns spent inside the area (-1 = watching)

void walker() {
    auto& me = self();
    const vec2 park{ 11, 21 }, inside{ 11, 20 };
    float sum = 0;
    for (auto p : kRow) sum += std::max(0.f, hp_of(p));
    if (g_in < 0 && me.position() != park) {
        if (me.can_move()) me.move_towards(park);
        g_prev = sum;
        return;
    }
    if (g_in < 0) {
        if (g_prev >= 0 && sum < g_prev) {
            log("enter_before");
            bool ok = false;
            try { ok = me.move_towards(inside); } catch (const std::exception& e) { log(std::string("enter_exc ") + e.what()); }
            log(std::string("enter_after ok=") + (ok ? "1" : "0"));
            g_in = 0;
        }
    } else if (++g_in >= 4) {
        bool ok = false;
        try { ok = me.move_towards(park); } catch (...) {}
        log(std::string("leave ok=") + (ok ? "1" : "0"));
        g_in = -1;
    }
    g_prev = sum;
}
} // namespace

int main() {
    constexpr std::array picks{ champion_draft::willow, champion_draft::tavi, champion_draft::vesper_vale, champion_draft::ryth };
    while (true) {
        try {
            if (is_draft()) {
                const auto chosen = draft::current_draft(team::ally);
                for (auto p : picks)
                    if (std::find(chosen.begin(), chosen.end(), p) == chosen.end()) { draft::pick(p); break; }
            } else {
                auto& me = self();
                if (!g_init) {
                    g_init = true;
                    for (const auto& grp : map::camp_groups())
                        for (const auto& c : grp) g_camps.emplace(std::pair{ c.spawn_position().x, c.spawn_position().y }, c);
                }
                if (me.is_alive() && me.champion_name() == champion_type::ryth) {
                    if (round_number() >= 28) log("ST");
                    walker();
                }
            }
        } catch (const std::exception& e) {
            std::cout << "PROBE B err " << e.what() << '\n';
        }
        end_turn();
    }
}
