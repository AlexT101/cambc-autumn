// Shared probe helpers (identical copy in probe-stun and probe-stun-b).
// Every logged value is read from the engine; failures log as E:<error_code>.
#pragma once
#include <cambc.h>
#include <iostream>
#include <sstream>
#include <string>

using namespace cambc;

inline const char* cname(champion_type t) {
    static const char* n[] = {"ryth","vesper","vendetta","cassi","issac","stellar","prism","marcella","willow","ren","varg","tavi"};
    auto i = static_cast<int>(t);
    return (i >= 0 && i < 12) ? n[i] : "?";
}

// Evaluate f() and stringify the result, or the error it throws.
template <class F> std::string q(F f) {
    try { std::ostringstream o; o << f(); return o.str(); }
    catch (const cambc::error& e) { return "E:" + to_string(e.code()); }
    catch (const std::exception& e) { return std::string("X:") + e.what(); }
}
// Run an action; "ok"/"false" or the error it throws.
template <class F> std::string act(F f) {
    try {
        if constexpr (std::is_same_v<decltype(f()), bool>) return f() ? "ok" : "false";
        else { f(); return "ok"; }
    }
    catch (const cambc::error& e) { return "E:" + to_string(e.code()); }
    catch (const std::exception& e) { return std::string("X:") + e.what(); }
}

inline std::string pos_s(vec2 p) { return std::to_string(p.x) + "," + std::to_string(p.y); }

// Compact state of any champion view (self or visible).
inline std::string desc(const champion& c) {
    std::ostringstream o;
    o << "alive=" << q([&] { return c.is_alive(); }) << " vis=" << q([&] { return c.is_visible(); })
      << " pos=" << q([&] { return pos_s(c.position()); }) << " hp=" << q([&] { return c.health(); })
      << "/" << q([&] { return c.max_health(); })
      << " st=0x" << q([&] { std::ostringstream h; h << std::hex << c.state().bits(); return h.str(); })
      << " restr=" << q([&] { return (int)c.restrictions().bits(); })
      << " stun=" << q([&] { auto b = c.buffs(); return b.has_stun() ? std::to_string(b.get<buff_stun>().duration) : std::string("-"); })
      << " mv=" << q([&] { return c.can_move(); }) << " at=" << q([&] { return c.can_attack(); })
      << " cs=" << q([&] { return c.can_cast(); }) << " done=" << q([&] { return c.has_completed_turn(); })
      << " rec=" << q([&] { return c.is_recalling(); }) << " tp=" << q([&] { return c.is_teleporting(); })
      << " ch=" << q([&] { return c.remaining_channel_time(); });
    return o.str();
}

// Extra self-only fields.
inline std::string self_desc() {
    auto& me = self();
    std::ostringstream o;
    o << desc(me) << " gold=" << q([&] { return me.gold_count(); }) << " gems=" << q([&] { return me.gem_count(); })
      << " cd0=" << q([&] { return me.abilities()[0].cooldown(); }) << " cd1=" << q([&] { return me.abilities()[1].cooldown(); })
      << " items=" << q([&] { int n = 0; for (auto v : me.item_count()) n += v; return n; })
      << " tpc=" << q([&] { return me.consumables()[consumable_type::tp_crystal].count(); })
      << " prio=" << q([&] { return me.prev_priority(); });
    return o.str();
}

inline void log(const std::string& s) {
    std::cout << "PROBE " << round_number() << " " << cname(self().champion_name()) << " " << s << '\n';
}

// First visible enemy champion of the given type, if any.
inline std::optional<champion> find_enemy(champion_type t) {
    for (auto& c : vision::champions(team::enemy))
        if (c.champion_name() == t) return c;
    return std::nullopt;
}
inline std::optional<champion> find_ally(champion_type t) {
    for (auto& c : vision::champions(team::ally))
        if (c.champion_name() == t) return c;
    return std::nullopt;
}

// Walk one step toward goal if not there (returns description of attempt).
inline void walk_to(vec2 goal) {
    auto& me = self();
    if (me.position() != goal && me.can_move()) { try { me.move_towards(goal); } catch (...) {} }
}

// Raw engine shop permission for self (independent of gold): items or consumables.
inline std::string can_shop(bool consumable) {
    return q([&] { std::int32_t r{}; detail::check(detail::sdk_champion_can_shop(static_cast<std::uint32_t>(static_cast<handle_champion_t>(self())), consumable, &r)); return r; });
}

// Free tile within Chebyshev `range` of `target` closest to self (self tile counts as free).
inline vec2 approach_tile(vec2 target, int range) {
    auto& me = self();
    const auto blocked = map::walls() | map::holes() | map::altars() | map::spawn_region(team::enemy)
        | vision::champion_tiles() | vision::camp_tiles();
    vec2 best = me.position(); int bd = 1 << 30;
    for (int dx = -range; dx <= range; ++dx) for (int dy = -range; dy <= range; ++dy) {
        vec2 p{target.x + dx, target.y + dy};
        if (!map::is_in_bounds(p) || (blocked.is_set(p) && p != me.position())) continue;
        int d = static_cast<int>(p.chebyshev_distance(me.position()));
        if (d < bd) { bd = d; best = p; }
    }
    return best;
}
