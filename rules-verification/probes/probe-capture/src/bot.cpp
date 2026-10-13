// Scripted probe champion: executes its scenario steps and logs engine state every turn.
#include <cambc.h>
#include "bot.h"
#include <iostream>
#include <string>
#include <variant>

using cambc::vec2;
using cambc::team;

static cambc::bitboard around(vec2 p, int r) { cambc::bitboard b; b.clear(); b.draw_chebyshev(p, r); return b; }

static cambc::bitboard blocked_tiles() {
    auto blocked = cambc::map::walls() | cambc::map::holes() | cambc::map::altars()
        | cambc::map::spawn_region(team::enemy) | cambc::vision::champion_tiles()
        | cambc::vision::camp_tiles() | cambc::vision::teleport_tiles();
    blocked.set(cambc::self().position(), false);
    return blocked;
}

// Step toward the nearest free goal tile (starter-bot distance-field pathing).
static bool move_towards_closest(cambc::bitboard goals) {
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

static std::string group_state(int g) {
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

static int group_of(vec2 tile) {
    return static_cast<int>(static_cast<cambc::handle_camp_group_t>(cambc::map::camp(tile).camp_group()));
}

static void prefix(const char* what) {
    auto& me = cambc::self();
    std::cout << "PROBE " << cambc::round_number() << " " << cambc::to_string(me.champion_name()) << " " << what;
}

void Bot::log_turn() {
    auto& me = cambc::self();
    auto pos = me.position();
    auto items = me.item_count();
    unsigned shards = items[cambc::item_type::treasure_shard_of_strength];
    prefix("turn");
    std::cout << " id=" << static_cast<unsigned>(static_cast<cambc::handle_champion_t>(me))
              << " pos=(" << pos.x << "," << pos.y << ") gold=" << me.gold_count() << " gems=" << me.gem_count()
              << " subA=" << cambc::global_submitted_gems(team::ally) << " subE=" << cambc::global_submitted_gems(team::enemy)
              << " step=" << idx << " watch=" << watch_group << ":" << group_state(watch_group)
              << " tshards=" << shards << " temblem=" << items[cambc::item_type::treasure_emblem_of_strength]
              << " submitting=" << me.is_submitting_gems();
    if (me.is_submitting_gems()) std::cout << " channel=" << me.remaining_channel_time();
    std::cout << '\n';
}

bool Bot::run_step(const Step& s) {
    auto& me = cambc::self();
    switch (s.op) {
    case Op::kill: {
        watch_group = group_of(s.tile);
        if (group_state(watch_group) == "reward_available") return true;
        // Attack any visible member of the group in range, else approach the nearest living one.
        cambc::bitboard goals; goals.clear();
        for (const auto& c : cambc::vision::camps()) {
            if (static_cast<int>(static_cast<cambc::handle_camp_group_t>(c.camp_group())) != watch_group) continue;
            if (me.can_attack() && me.attack_tiles().is_set(c.position())) { me.attack(c); return false; }
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
    case Op::wait_reward:
        if (me.gold_count() != gold0 || me.gem_count() != gems0) {
            prefix("reward");
            std::cout << " dgold=" << static_cast<int>(me.gold_count()) - static_cast<int>(gold0)
                      << " dgems=" << static_cast<int>(me.gem_count()) - static_cast<int>(gems0)
                      << " turns_waited=" << turns_in_step << '\n';
            return true;
        }
        return turns_in_step >= (s.n ? s.n : 40);
    case Op::buy_treasure: {
        if (!cambc::map::spawn_region(team::ally).is_set(me.position())) {
            move_towards_closest(cambc::map::spawn_region(team::ally));
            return false;
        }
        for (int i = 0; i < s.n; ++i) {
            bool ok = me.can_buy(cambc::item_type::treasure_shard_of_strength);
            prefix("buy");
            std::cout << " can_buy=" << ok << " gold=" << me.gold_count() << '\n';
            if (ok) me.buy(cambc::item_type::treasure_shard_of_strength);
        }
        return true;
    }
    case Op::tribute: {
        if (me.is_submitting_gems()) return false;
        if (turns_in_step > 0 && me.gem_count() == 0) return true;
        if (me.position().chebyshev_distance(s.tile) <= cambc::constants::submit_gems_range) {
            if (me.gem_count() > 0) {
                prefix("tribute_start");
                std::cout << " gems=" << me.gem_count() << '\n';
                me.submit_gems(s.tile);
                prefix("after_start");
                std::cout << " submitting=" << me.is_submitting_gems() << " channel=" << me.remaining_channel_time()
                          << " gems=" << me.gem_count() << " subA=" << cambc::global_submitted_gems(team::ally) << '\n';
            }
            return false;
        }
        move_towards_closest(around(s.tile, 1));
        return false;
    }
    case Op::wait_alive: return group_state(watch_group) == "alive" || turns_in_step >= (s.n ? s.n : 200);
    case Op::idle: return false;
    }
    return true;
}

void Bot::play_turn() {
    auto& me = cambc::self();
    if (!init) { script = scenario_script(me.champion_name()); init = true; gold0 = me.gold_count(); gems0 = me.gem_count(); }
    log_turn();
    if (!me.is_alive()) return;
    // Execute steps; a finished step hands the rest of the turn to the next one.
    for (int guard = 0; guard < 4 && idx < script.size(); ++guard) {
        bool done = run_step(script[idx]);
        if (!done) { ++turns_in_step; break; }
        prefix("step_done");
        std::cout << " step=" << idx << " pos=(" << me.position().x << "," << me.position().y << ")\n";
        ++idx; turns_in_step = 0; gold0 = me.gold_count(); gems0 = me.gem_count();
        if (!me.can_move() && !me.can_attack()) break;
    }
}
