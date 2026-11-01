// Scripted probe champion: executes its scenario steps and logs its gold, gems and channel every turn.
#include <cambc.h>
#include "bot.h"
#include <cstdio>
#include <string>
#include <variant>

using cambc::vec2;
using cambc::team;

int my_side() {
    const auto a = cambc::map::spawn_region(team::ally).positions();
    const auto e = cambc::map::spawn_region(team::enemy).positions();
    return (a.front().y * 1000 + a.front().x) < (e.front().y * 1000 + e.front().x) ? 0 : 1;
}

static cambc::bitboard around(vec2 p, int r) { cambc::bitboard b; b.clear(); b.draw_chebyshev(p, r); return b; }

static const cambc::bitboard& all_camp_tiles() {
    static bool done = false;
    static cambc::bitboard b;
    if (!done) {
        b.clear();
        for (const auto& g : cambc::map::camp_groups())
            for (const auto& m : g) b.set(m.spawn_position());
        done = true;
    }
    return b;
}

// Camp tiles other than the goals are blocked, so no one wanders onto a capture tile and takes a share.
static cambc::bitboard blocked_tiles(const cambc::bitboard& goals) {
    auto blocked = cambc::map::walls() | cambc::map::holes() | cambc::map::altars()
        | cambc::map::spawn_region(team::enemy) | cambc::vision::champion_tiles()
        | cambc::vision::camp_tiles() | cambc::vision::teleport_tiles() | (all_camp_tiles() & ~goals);
    blocked.set(cambc::self().position(), false);
    return blocked;
}

static bool move_towards_closest(cambc::bitboard goals) {
    auto& me = cambc::self();
    if (!me.can_move() || goals.is_set(me.position())) return false;
    const auto blocked = blocked_tiles(goals);
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
    std::printf("PROBE %u %s %s", static_cast<unsigned>(cambc::round_number()),
                cambc::to_string(cambc::self().champion_name()).data(), what);
}

void Bot::log_state(const char* what) {
    auto& me = cambc::self();
    auto pos = me.position();
    auto items = me.item_count();
    prefix(what);
    std::printf(" pos=(%d,%d) gold=%u gems=%u subA=%u step=%zu tshards=%u temblem=%u submitting=%d",
                pos.x, pos.y, me.gold_count(), me.gem_count(), cambc::global_submitted_gems(team::ally), idx,
                static_cast<unsigned>(items[cambc::item_type::treasure_shard_of_strength]),
                static_cast<unsigned>(items[cambc::item_type::treasure_emblem_of_strength]),
                static_cast<int>(me.is_submitting_gems()));
    if (me.is_submitting_gems()) std::printf(" channel=%u", static_cast<unsigned>(me.remaining_channel_time()));
    std::printf("\n");
}

// The raw gold import on every other champion, teammates and enemies: the vision code (sdk_champion; 97 = out of
// vision), gold's code and the value it wrote (12345 = untouched). gold_count() refuses anyone but self client-side.
static void log_gold_reads() {
    using namespace cambc::detail;
    const std::uint32_t me = static_cast<std::uint32_t>(sdk_my_champion());
    for (const bool enemies : {false, true}) {
        std::uint32_t handles[16]{}, n = 0;
        check(enemies ? sdk_enemies(handles, 16, &n) : sdk_allies(handles, 16, &n));
        for (std::uint32_t i = 0; i < n; ++i) {
            if (handles[i] == me) continue;
            champion_info info{};
            std::uint32_t gold = 12345;
            const int seen = sdk_champion(handles[i], &info);
            const int code = sdk_champion_gold(handles[i], &gold);
            prefix("goldread");
            std::printf(" %s %u champion=%d gold_code=%d gold=%u\n", enemies ? "enemy" : "ally", handles[i], seen, code, gold);
        }
    }
}

bool Bot::run_step(const Step& s) {
    auto& me = cambc::self();
    switch (s.op) {
    case Op::kill: {
        const int g = group_of(s.tile);
        if (group_state(g) == "reward_available") return true;
        cambc::bitboard goals; goals.clear();
        for (const auto& c : cambc::vision::camps()) {
            if (static_cast<int>(static_cast<cambc::handle_camp_group_t>(c.camp_group())) != g) continue;
            if (me.can_attack() && me.attack_tiles().is_set(c.position())) { me.attack(c); return false; }
            goals |= around(c.position(), me.attack_range());
        }
        if (goals.is_empty()) goals = around(s.tile, me.attack_range());
        move_towards_closest(goals & ~all_camp_tiles());
        return false;
    }
    case Op::go: {
        if (me.position() == s.tile) return true;
        cambc::bitboard g; g.clear(); g.set(s.tile);
        move_towards_closest(g);
        return me.position() == s.tile;
    }
    case Op::wait_reward:
        if (me.gold_count() != gold0 || me.gem_count() != gems0) {
            prefix("reward");
            std::printf(" dgold=%d dgems=%d turns_waited=%d\n", static_cast<int>(me.gold_count()) - static_cast<int>(gold0),
                        static_cast<int>(me.gem_count()) - static_cast<int>(gems0), turns_in_step);
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
            std::printf(" can_buy=%d gold=%u\n", static_cast<int>(ok), me.gold_count());
            if (ok) me.buy(cambc::item_type::treasure_shard_of_strength);
        }
        log_state("after_buy");
        return true;
    }
    case Op::tribute: {
        if (me.is_submitting_gems()) return false;
        if (turns_in_step > 0 && me.gem_count() == 0) return true;
        if (me.position().chebyshev_distance(s.tile) <= cambc::constants::submit_gems_range) {
            if (me.gem_count() > 0) {
                log_state("tribute_start");
                me.submit_gems(s.tile);
                log_state("after_start");
            }
            return false;
        }
        move_towards_closest(around(s.tile, 1));
        return false;
    }
    case Op::wait_alive:
        if (group_state(group_of(s.tile)) == "alive") return true;
        move_towards_closest(around(s.tile, 2) & ~all_camp_tiles());
        return turns_in_step >= (s.n ? s.n : 300);
    case Op::idle: return false;
    }
    return true;
}

void Bot::play_turn() {
    auto& me = cambc::self();
    if (!init) {
        init = true;
        active = my_side() == 0;
        script = scenario_script(me.champion_name());
        gold0 = me.gold_count(); gems0 = me.gem_count();
    }
    if (!active) return;
    log_state("turn");
    log_gold_reads();
    if (!me.is_alive()) return;
    // A finished step hands the rest of the turn to the next one.
    for (int guard = 0; guard < 4 && idx < script.size(); ++guard) {
        bool done = run_step(script[idx]);
        if (!done) { ++turns_in_step; break; }
        prefix("step_done");
        std::printf(" step=%zu pos=(%d,%d)\n", idx, me.position().x, me.position().y);
        ++idx; turns_in_step = 0; gold0 = me.gold_count(); gems0 = me.gem_count();
        if (!me.can_move() && !me.can_attack()) break;
    }
    log_state("end");
}
