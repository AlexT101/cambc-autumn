#pragma once
// Probe helpers: every logged value is read from the engine.
// Log format: PROBE <round> <champion> <key>=<value> ...
#include <cambc.h>
#include <functional>
#include <iostream>
#include <optional>
#include <sstream>
#include <string>
#include <type_traits>
#include <vector>

namespace probe {
using cambc::vec2;
using cambc::team;

inline std::string P(vec2 p) { return "(" + std::to_string(p.x) + "," + std::to_string(p.y) + ")"; }
inline std::string me_name() { return cambc::to_string(cambc::self().champion_name()); }

#define PROBE(x)                                                                                                  \
    do {                                                                                                          \
        std::ostringstream probe_os_;                                                                             \
        probe_os_ << x;                                                                                           \
        std::cout << "PROBE " << cambc::round_number() << ' ' << probe::me_name() << ' ' << probe_os_.str() << '\n'; \
    } while (0)

// Live allowance / cooldown snapshot of self.
inline std::string flags() {
    auto& me = cambc::self();
    auto ab = me.abilities();
    std::ostringstream os;
    os << "pos=" << P(me.position()) << " mv=" << me.can_move() << " atk=" << me.can_attack() << " cast=" << me.can_cast()
       << " cd0=" << ab[0].cooldown() << " cd1=" << ab[1].cooldown() << " rdy0=" << ab[0].is_ready()
       << " rdy1=" << ab[1].is_ready() << " rs=" << int(me.restrictions().bits()) << " hp=" << me.health();
    return os.str();
}

// Run one engine action, log success/return or the engine error, then the post-action snapshot.
template <class F> bool act(const std::string& label, F&& f) {
    std::string res;
    bool ok = false;
    try {
        if constexpr (std::is_void_v<decltype(f())>) {
            f();
            res = "OK";
        } else {
            res = std::string("OK ret=") + (f() ? "true" : "false");
        }
        ok = true;
    } catch (const cambc::error& e) {
        res = "ERR=" + cambc::to_string(e.code()) + " msg=\"" + e.message() + "\"";
    } catch (const std::exception& e) {
        res = std::string("EXC=\"") + e.what() + "\"";
    }
    PROBE("act=" << label << " " << res << " | " << flags());
    return ok;
}

inline std::string camp_hp(vec2 p) {
    try {
        auto c = cambc::map::camp(p);
        if (!c.is_visible()) return P(p) + "=hidden";
        return P(p) + "=" + std::to_string(int(c.health()));
    } catch (const std::exception& e) { return P(p) + "=EXC"; }
}

// A visible living gem/gold cluster within `range` of self, preferring `prefer`.
inline std::optional<cambc::camp> cluster_in_range(int range, std::optional<vec2> prefer = std::nullopt) {
    auto& me = cambc::self();
    std::optional<cambc::camp> best;
    for (const auto& c : cambc::vision::camps()) {
        if (!(c.is_gem_cluster() || c.is_gold_cluster()) || c.health() <= 0) continue;
        if (me.position().chebyshev_distance(c.position()) > range) continue;
        if (prefer && c.position() == *prefer) return c;
        if (!best) best = c;
    }
    return best;
}

// Basic-attack a cluster in attack range (or a specific camp spawn tile if given).
inline bool attack_cluster(std::optional<vec2> exact = std::nullopt) {
    auto& me = cambc::self();
    if (exact) {
        return act("attack" + P(*exact) + " " + camp_hp(*exact), [&] { me.attack(cambc::map::camp(*exact)); });
    }
    auto c = cluster_in_range(me.attack_range());
    if (!c) { PROBE("act=attack NO_TARGET | " << flags()); return false; }
    const auto p = c->position();
    return act("attack" + P(p) + " " + camp_hp(p), [&] { me.attack(*c); });
}

inline bool walk(int dx, int dy) {
    auto& me = cambc::self();
    return act("walk(" + std::to_string(dx) + "," + std::to_string(dy) + ")", [&] { return me.move(vec2{ dx, dy }); });
}
inline bool cast_self(int slot) {
    auto& me = cambc::self();
    return act("cast" + std::to_string(slot) + "_self", [&] { return me.abilities()[slot].use(); });
}
inline bool cast_ground(int slot, vec2 p, const std::string& note = "") {
    auto& me = cambc::self();
    return act("cast" + std::to_string(slot) + "_ground" + P(p) + note, [&] { return me.abilities()[slot].use(p); });
}
// Dash relative to current position.
inline bool dash(int slot, int dx, int dy, const std::string& note = "") {
    auto& me = cambc::self();
    const auto to = me.position() + vec2{ dx, dy };
    return act("dash(" + std::to_string(dx) + "," + std::to_string(dy) + ")->" + P(to) + note,
        [&] { return me.abilities()[slot].use(to); });
}
inline bool cast_camp(int slot, std::optional<vec2> exact = std::nullopt, int range = 4) {
    auto& me = cambc::self();
    std::optional<cambc::camp> c;
    if (exact) c = cambc::map::camp(*exact);
    else c = cluster_in_range(range);
    if (!c) { PROBE("act=cast" << slot << "_camp NO_TARGET | " << flags()); return false; }
    const auto p = c->spawn_position();
    return act("cast" + std::to_string(slot) + "_camp" + P(p) + " " + camp_hp(p), [&] { return me.abilities()[slot].use(*c); });
}

// Visible allied champion (not self) within range, optional type filter.
inline std::optional<cambc::champion> ally_in_range(int range, std::optional<cambc::champion_type> type = std::nullopt) {
    auto& me = cambc::self();
    for (const auto& c : cambc::vision::champions(team::ally)) {
        if (c == me) continue;
        if (type && c.champion_name() != *type) continue;
        if (me.position().chebyshev_distance(c.position()) <= range) return c;
    }
    return std::nullopt;
}

// Ordered scripted steps: travel to `pos`, wait for required slots (bit0 slot0, bit1 slot1) to be off
// cooldown, then run `fn` once in a single turn; `fn` returns true when the step is finished.
struct Step {
    std::string name;
    std::optional<vec2> pos;
    int need = 0;
    std::function<bool()> fn;
};

class Script {
public:
    std::vector<Step> steps;
    std::size_t index = 0;
    void add(std::string name, std::optional<vec2> pos, int need, std::function<bool()> fn) {
        steps.push_back(Step{ std::move(name), pos, need, std::move(fn) });
    }
    void run() {
        auto& me = cambc::self();
        PROBE("ST " << flags());
        if (index >= steps.size()) return;
        auto& s = steps[index];
        if (s.pos && me.position() != *s.pos) {
            bool moved = false;
            try { moved = me.move_towards(*s.pos); } catch (const std::exception& e) { PROBE("travel EXC " << e.what()); }
            PROBE("travel step=" << s.name << " to=" << P(*s.pos) << " moved=" << moved);
            return;
        }
        auto ab = me.abilities();
        if (((s.need & 1) && ab[0].cooldown() > 0) || ((s.need & 2) && ab[1].cooldown() > 0)) {
            PROBE("wait step=" << s.name);
            return;
        }
        PROBE("BEGIN step=" << s.name << " | " << flags());
        if (s.fn()) ++index;
    }
};
} // namespace probe
