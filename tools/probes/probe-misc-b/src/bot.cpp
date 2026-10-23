// Scripted probe champion: executes its scenario steps and logs engine state every turn.
#include <cambc.h>
#include "bot.h"
#include <iomanip>
#include <iostream>
#include <string>
#include <variant>

using cambc::vec2;
using cambc::team;

cambc::bitboard around(vec2 p, int r) { cambc::bitboard b; b.clear(); b.draw_chebyshev(p, r); return b; }

static cambc::bitboard blocked_tiles() {
    auto blocked = cambc::map::walls() | cambc::map::holes() | cambc::map::altars()
        | cambc::map::spawn_region(team::enemy) | cambc::vision::champion_tiles()
        | cambc::vision::camp_tiles() | cambc::vision::teleport_tiles();
    blocked.set(cambc::self().position(), false);
    return blocked;
}

// Step toward the nearest free goal tile (starter-bot distance-field pathing).
bool move_towards_closest(cambc::bitboard goals) {
    auto& me = cambc::self();
    if (!me.can_move() || goals.is_set(me.position())) return false;
    const auto blocked = blocked_tiles();
    goals &= ~blocked;
    if (goals.is_empty()) return false;
    cambc::distance_field field;
    cambc::bitboard visited;
    field.compute_to(blocked & ~goals, goals, around(me.position(), 0), visited);
    auto step = me.position();
    for (auto tile : blocked.reachable_tiles(step, me.base_stats().base_move_speed).positions())
        if (field.get(tile) < field.get(step)) step = tile;
    return step != me.position() && me.move_absolute(step);
}

std::string group_state(int g) {
    if (g < 0) return "-";
    try {
        for (const auto& grp : cambc::map::camp_groups()) {
            if (static_cast<int>(static_cast<cambc::handle_camp_group_t>(grp)) != g) continue;
            auto st = grp.state();
            if (std::holds_alternative<cambc::map::camp_group_alive>(st)) return "alive";
            if (std::holds_alternative<cambc::map::camp_group_reward_available>(st)) return "reward_available";
            return "respawning:" + std::to_string(std::get<cambc::map::camp_group_respawning>(st).timer);
        }
    } catch (const std::exception&) { return "unseen"; }
    return "?";
}

int group_of(vec2 tile) {
    return static_cast<int>(static_cast<cambc::handle_camp_group_t>(cambc::map::camp(tile).camp_group()));
}

void probe_prefix(const char* what) {
    auto& me = cambc::self();
    std::cout << "PROBE " << cambc::round_number() << " " << cambc::to_string(me.champion_name()) << " " << what;
}

std::string err_str(const std::exception& e) {
    if (auto ce = dynamic_cast<const cambc::error*>(&e))
        return std::to_string(static_cast<int>(ce->code())) + ":" + cambc::to_string(ce->code());
    return e.what();
}

void log_camps_near(vec2 p, int r) {
    for (const auto& c : cambc::vision::camps()) {
        if (c.position().chebyshev_distance(p) > r) continue;
        std::cout << " " << cambc::to_string(c.kind()) << "@(" << c.position().x << "," << c.position().y << ")hp=" << c.health();
    }
}

void log_locks() {
    for (const auto& l : cambc::vision::altar_locks())
        std::cout << " lock@(" << l.position().x << "," << l.position().y << ")" << (l.is_ally() ? "ally" : "enemy")
                  << ":hits=" << l.hits_remaining();
}

void Bot::log_turn() {
    auto& me = cambc::self();
    probe_prefix("turn");
    std::cout << std::fixed << std::setprecision(3);
    std::cout << " id=" << static_cast<unsigned>(static_cast<cambc::handle_champion_t>(me)) << " alive=" << me.is_alive();
    if (me.is_alive()) {
        auto pos = me.position();
        std::cout << " pos=(" << pos.x << "," << pos.y << ") hp=" << me.health() << "/" << me.max_health()
                  << " str=" << me.strength() << " foc=" << me.focus();
    } else {
        try { std::cout << " hp=" << me.health() << "/" << me.max_health() << " str=" << me.strength(); } catch (...) { std::cout << " hp=?"; }
    }
    std::cout << " gold=" << me.gold_count() << " gems=" << me.gem_count() << " step=" << idx
              << " watch=" << watch_group << ":" << group_state(watch_group)
              << " lockinv=" << me.consumables()[cambc::consumable_type::altar_lock].count()
              << " subA=" << cambc::global_submitted_gems(team::ally) << " subE=" << cambc::global_submitted_gems(team::enemy);
    if (me.is_submitting_gems()) std::cout << " SUBMITTING ch=" << me.remaining_channel_time();
    if (me.is_recalling()) std::cout << " RECALLING ch=" << me.remaining_channel_time();
    std::cout << " items=";
    auto items = me.item_count();
    for (std::uint32_t i = 0; i < static_cast<std::uint32_t>(cambc::item_type::count); ++i)
        if (items[cambc::item_type{i}]) std::cout << cambc::to_string(cambc::item_type{i}) << "x" << items[cambc::item_type{i}] << ",";
    if (me.is_alive()) log_camps_near(me.position(), 4);
    log_locks();
    std::cout << '\n';
}

bool Bot::run_step(const Step& s) {
    auto& me = cambc::self();
    switch (s.op) {
    case Op::kill: {
        watch_group = group_of(s.tile);
        if (group_state(watch_group) == "reward_available") return true;
        cambc::bitboard goals; goals.clear();
        for (const auto& c : cambc::vision::camps()) {
            if (static_cast<int>(static_cast<cambc::handle_camp_group_t>(c.camp_group())) != watch_group) continue;
            if (me.can_attack() && me.attack_tiles().is_set(c.position())) {
                float before = c.health();
                const vec2 cp = c.position();
                me.attack(c);
                probe_prefix("hit");
                std::cout << " target=" << cambc::to_string(c.kind()) << "@(" << cp.x << "," << cp.y
                          << ") str=" << me.strength() << " before=" << before << " after=" << (c.is_visible() ? c.health() : -1.0f)
                          << " dmg=" << before - (c.is_visible() ? c.health() : 0.0f) << '\n';
                return false;
            }
            goals |= around(c.position(), me.attack_range());
        }
        if (goals.is_empty()) goals = around(s.tile, me.attack_range());
        move_towards_closest(goals);
        return false;
    }
    case Op::go: {
        if (me.position() == s.tile) return true;
        cambc::bitboard g; g.clear(); g.set(s.tile);
        move_towards_closest(g);
        return me.position() == s.tile;
    }
    case Op::wait: return turns_in_step >= s.n;
    case Op::until: return static_cast<int>(cambc::round_number()) >= s.n;
    case Op::wait_reward:
        if (me.gold_count() != gold0 || me.gem_count() != gems0) {
            probe_prefix("reward");
            std::cout << " dgold=" << static_cast<int>(me.gold_count()) - static_cast<int>(gold0)
                      << " dgems=" << static_cast<int>(me.gem_count()) - static_cast<int>(gems0)
                      << " turns_waited=" << turns_in_step << '\n';
            return true;
        }
        return turns_in_step >= (s.n ? s.n : 40);
    case Op::buy: {
        if (s.n2 != 1 && me.is_alive() && !cambc::map::spawn_region(team::ally).is_set(me.position())) {
            move_towards_closest(cambc::map::spawn_region(team::ally));
            if (!cambc::map::spawn_region(team::ally).is_set(me.position())) return false;  // else buy in the arrival turn
        }
        cambc::item_type it{static_cast<std::uint32_t>(s.item)};
        for (int i = 0; i < s.n; ++i) {
            bool ok = me.can_buy(it);
            float hp0 = me.health(), mhp0 = me.max_health(), st0 = me.strength();
            std::string res = "ok";
            try { me.buy(it); } catch (const std::exception& e) { res = err_str(e); }
            probe_prefix("buy");
            std::cout << " item=" << cambc::to_string(it) << " can_buy=" << ok << " res=" << res << " gold=" << me.gold_count()
                      << " hp " << hp0 << "/" << mhp0 << " -> " << me.health() << "/" << me.max_health()
                      << " str " << st0 << " -> " << me.strength() << '\n';
        }
        return true;
    }
    case Op::buy_lock: {
        if (me.is_alive() && !cambc::map::spawn_region(team::ally).is_set(me.position())) {
            move_towards_closest(cambc::map::spawn_region(team::ally));
            if (!cambc::map::spawn_region(team::ally).is_set(me.position())) return false;
        }
        for (int i = 0; i < (s.n ? s.n : 1); ++i) {
            bool ok = me.can_buy(cambc::consumable_type::altar_lock);
            std::string res = "ok";
            try { me.buy(cambc::consumable_type::altar_lock); } catch (const std::exception& e) { res = err_str(e); }
            probe_prefix("buy_lock");
            std::cout << " can_buy=" << ok << " res=" << res << " gold=" << me.gold_count()
                      << " inv=" << me.consumables()[cambc::consumable_type::altar_lock].count() << '\n';
        }
        return true;
    }
    case Op::tribute: {
        if (me.is_submitting_gems()) return false;
        if (turns_in_step > 0 && me.gem_count() == 0) return true;
        if (me.position().chebyshev_distance(s.tile) <= cambc::constants::submit_gems_range) {
            if (me.gem_count() > 0) {
                probe_prefix("tribute_start");
                std::cout << " gems=" << me.gem_count() << " can_attack=" << me.can_attack();
                std::string res = "ok";
                try { me.submit_gems(s.tile); } catch (const std::exception& e) { res = err_str(e); }
                std::cout << " res=" << res << " submitting=" << me.is_submitting_gems()
                          << " can_attack_after=" << me.can_attack() << " gems_after=" << me.gem_count();
                log_locks();
                std::cout << '\n';
                if (s.n && turns_in_step >= s.n) return true;  // give up after n turns
            }
            return false;
        }
        move_towards_closest(around(s.tile, 1));
        return false;
    }
    case Op::place_lock: {
        std::string res = "ok";
        bool ret = false;
        try { ret = me.consumables()[cambc::consumable_type::altar_lock].use(s.tile); } catch (const std::exception& e) { res = err_str(e); }
        probe_prefix("place_lock");
        std::cout << " altar=(" << s.tile.x << "," << s.tile.y << ") from=(" << me.position().x << "," << me.position().y
                  << ") res=" << res << " ret=" << ret << " inv=" << me.consumables()[cambc::consumable_type::altar_lock].count();
        log_locks();
        std::cout << '\n';
        return true;
    }
    case Op::recall:
        if (turns_in_step == 0) {
            try { me.recall(); } catch (const std::exception& e) { probe_prefix("recall_err"); std::cout << " " << err_str(e) << '\n'; return true; }
            return false;
        }
        return !me.is_recalling();
    case Op::fn: return s.f(turns_in_step);
    case Op::idle: return false;
    }
    return true;
}

void Bot::play_turn() {
    auto& me = cambc::self();
    if (!init) { script = scenario_script(me.champion_name()); init = true; gold0 = me.gold_count(); gems0 = me.gem_count(); }
    log_turn();
    // Dead champions may still shop: only buy/buy_lock/fn steps run while dead.
    if (!me.is_alive() && (idx >= script.size() || (script[idx].op != Op::buy && script[idx].op != Op::buy_lock && script[idx].op != Op::fn))) return;
    for (int guard = 0; guard < 6 && idx < script.size(); ++guard) {
        bool done = run_step(script[idx]);
        if (!done) { ++turns_in_step; break; }
        probe_prefix("step_done");
        std::cout << " step=" << idx << '\n';
        ++idx; turns_in_step = 0; gold0 = me.gold_count(); gems0 = me.gem_count();
        if (me.is_alive() && !me.can_move() && !me.can_attack()) break;
    }
}
