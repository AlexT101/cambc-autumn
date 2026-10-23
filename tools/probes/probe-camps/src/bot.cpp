// probe-camps: scripted scenarios probing camp wake/sleep/attack/targeting.
// Each champion follows a list of Steps chosen by SCENARIO (scenario.h), its side (0 = team whose spawn
// contains the lowest tile, 1 = other) and its index within the team (ordered by champion type).
// Every turn each champion logs its own engine health/position; the logger (side 0, idx 0) also logs
// every visible camp. Damage is inferred from engine health deltas between turn starts.
#include <cambc.h>
#include "bot.h"
#include "scenario.h"
#include <algorithm>
#include <iostream>
#include <string>
#include <vector>

using cambc::vec2;
using cambc::team;

namespace {

std::string name(const cambc::champion& c) { return cambc::to_string(c.champion_name()); }
std::uint32_t cid(const cambc::champion& c) { return static_cast<std::uint32_t>(static_cast<cambc::handle_champion_t>(c)); }
std::uint32_t kid(const cambc::camp& c) { return static_cast<std::uint32_t>(static_cast<cambc::handle_camp_t>(c)); }

int my_side() {
    const auto a = cambc::map::spawn_region(team::ally).positions();
    const auto e = cambc::map::spawn_region(team::enemy).positions();
    const int s = (a.front().y * 1000 + a.front().x) < (e.front().y * 1000 + e.front().x) ? 0 : 1;
    return SIDE_FLIP ? 1 - s : s;
}

// Index of self among all allied champions sorted by champion type.
int my_index() {
    std::vector<int> types;
    for (const auto& c : cambc::vision::champions(team::ally)) types.push_back(static_cast<int>(c.champion_name()));
    std::sort(types.begin(), types.end());
    const int mine = static_cast<int>(cambc::self().champion_name());
    return static_cast<int>(std::find(types.begin(), types.end(), mine) - types.begin());
}

// Log visible camps within Chebyshev 6 (logging every camp costs too much fuel on busy maps).
void log_camps(int r, const std::string& who) {
    const auto me = cambc::self().position();
    for (const auto& c : cambc::vision::camps()) {
        const auto p = c.position();
        if (p.chebyshev_distance(me) > LOG_RADIUS) continue;
        std::cout << "PROBE " << r << " " << who << " camp=" << kid(c) << ":" << cambc::to_string(c.kind())
                  << " hp=" << c.health() << "/" << c.max_health() << " str=" << c.strength()
                  << " pos=" << p.x << "," << p.y;
        // Raw host record: besides stats it only holds two ability cooldowns (no awake/sleep flag).
        cambc::detail::camp_state raw{};
        cambc::detail::sdk_camp(kid(c), &raw);
        std::cout << " raw_cd=" << raw.cooldowns[0] << "," << raw.cooldowns[1] << '\n';
    }
}

} // namespace

void Bot::play_turn() {
    auto& me = cambc::self();
    const int r = static_cast<int>(cambc::round_number());
    const std::string who = name(me);
    if (side < 0) {
        side = my_side();
        idx = my_index();
        steps = script(side, idx);
        const auto s = me.base_stats();
        std::cout << "PROBE " << r << " " << who << " init id=" << cid(me) << " side=" << side << " idx=" << idx
                  << " range=" << me.attack_range() << " str=" << me.strength() << " focus=" << me.focus()
                  << " hp=" << me.max_health() << " move=" << s.base_move_speed << " vision=" << s.vision_radius
                  << " camp_sleep_time=" << cambc::constants::camp_sleep_time << '\n';
        bool seen[8] = {};
        if (side == 0 && idx == 0)
            for (const auto& g : cambc::map::camp_groups())
            for (const auto& c : g) {
                if (seen[static_cast<int>(c.kind())]) continue;
                seen[static_cast<int>(c.kind())] = true;
                const auto b = c.base_stats();
                std::cout << "PROBE " << r << " " << who << " campdesign " << cambc::to_string(c.kind()) << " range="
                          << c.attack_range() << " vision=" << b.vision_radius << " move=" << b.base_move_speed
                          << " str=" << b.base_strength << " hp=" << b.base_health << '\n';
            }
    }
    if (!me.is_alive()) { std::cout << "PROBE " << r << " " << who << " dead\n"; return; }
    const auto pos = me.position();
    std::cout << "PROBE " << r << " " << who << " self hp=" << me.health() << " pos=" << pos.x << "," << pos.y
              << " side=" << side << '\n';
    if ((side == 0 && idx == 0) || LOG_ALL_CAMPS) log_camps(r, who);

    // Execute steps; a finished step with wait==0 falls through to the next in the same turn.
    while (cur < steps.size()) {
        Step& st = steps[cur];
        if (me.position() != st.tile) {
            if (me.can_move()) {
                const bool moved = me.move_towards(st.tile);
                if (!moved) std::cout << "PROBE " << r << " " << who << " move_failed to=" << st.tile.x << "," << st.tile.y << '\n';
            }
            if (me.position() != st.tile) break;
        }
        if (arrived < 0) {
            arrived = r;
            std::cout << "PROBE " << r << " " << who << " arrived step=" << cur << " at=" << st.tile.x << "," << st.tile.y << '\n';
        }
        if (r < st.min_round) break;
        const bool do_attack = st.attack == 2 || (st.attack == 1 && !attacked_this_step);
        if (do_attack && st.cast) {
            // Cast the first ready camp-targeting ability on the target camp.
            for (const auto& c : cambc::vision::camps()) {
                if (c.spawn_position() != st.target || c.health() <= 0) continue;
                for (const auto& ab : me.abilities()) {
                    if (!ab.can_target_camps() || !ab.is_ready()) continue;
                    const float before = c.health();
                    const bool ok = ab.use(c);
                    if (ok) attacked_this_step = true;
                    std::cout << "PROBE " << r << " " << who << " cast slot=" << ab.slot() << " ok=" << ok << " camp=" << kid(c)
                              << " dist=" << me.position().chebyshev_distance(c.position()) << " before=" << before
                              << " after=" << c.health() << '\n';
                    if (ok) break;
                }
                break;
            }
        } else if (do_attack && me.can_attack()) {
            for (const auto& c : cambc::vision::camps()) {
                if (c.spawn_position() != st.target || c.health() <= 0) continue;
                if (!me.attack_tiles().is_set(c.position())) {
                    std::cout << "PROBE " << r << " " << who << " target_out_of_range camp=" << kid(c) << '\n';
                    break;
                }
                const float before = c.health();
                me.attack(c);
                attacked_this_step = true;
                std::cout << "PROBE " << r << " " << who << " attack camp=" << kid(c) << " before=" << before
                          << " after=" << c.health() << '\n';
                break;
            }
        }
        if (st.wait >= 0 && r - arrived >= st.wait) {
            ++cur; arrived = -1; attacked_this_step = false;
            continue;
        }
        break;
    }
    me.set_priority(PRIO_REVERSE ? PRIORITY_BASE + idx + 10 * side : PRIORITY_BASE - idx - 10 * side);
    if (LOG_PRIO) std::cout << "PROBE " << r << " " << who << " prio_now=" << me.prev_priority() << " prio_next=" << me.priority() << '\n';
    if (LOG_FUEL) std::cout << "PROBE " << r << " " << who << " fuel_left=" << cambc::fuel_remaining() << '\n';
}
