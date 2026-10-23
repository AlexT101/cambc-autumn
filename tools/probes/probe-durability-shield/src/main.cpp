// probe-durability-shield: with a Durability emblem and Varg's shield up, does the -10% apply before the shield absorbs
// (health loss = max(0, 0.9D - S)) or after (0.9 max(0, D - S))?
// Map durshield.map26a (makemap.mjs). Team A's Varg kills the 160-gold cluster block next to spawn, captures it, buys
// 5 Durability shards of Health on spawn, then hits the golem (120 damage) and shields (250). Team B and the other picks idle.
// Logs hp / shield every turn start and after each action.
//   node tools/probes/probe-durability-shield/makemap.mjs
//   cambc run tools/probes/probe-durability-shield tools/probes/probe-durability-shield \
//     --map tools/probes/probe-durability-shield/durshield.map26a --rounds 45 --fuel 50000000 -o <dir>
#include <cambc.h>
#include <algorithm>
#include <cstdio>
#include <optional>
#include <vector>

using cambc::vec2;
using cambc::team;
using D = cambc::champion_draft;

namespace {

const vec2 GOLEM{ 12, 8 }, GOLEM_ADJ{ 11, 7 }, HOLD{ 4, 0 };

int phase = 0;
int shield_round = -1;

bool team_a() { return cambc::map::spawn_region(team::ally).is_set({ 0, 0 }); }
bool is_gold_tile(vec2 p) { return p.x >= 4 && p.x <= 5 && p.y >= 0 && p.y <= 3; }

void log_self(const char* tag) {
    auto& me = cambc::self();
    const auto b = me.buffs();
    const float sh = b.has_shield() ? b.get<cambc::buff_shield>().value : 0.f;
    const int shd = b.has_shield() ? b.get<cambc::buff_shield>().duration : -1;
    std::printf("PROBE %d %s pos=(%d,%d) hp=%.3f maxhp=%.3f shield=%.3f shield_dur=%d gold=%u focus=%.2f\n",
                (int)cambc::round_number(), tag, me.position().x, me.position().y, me.health(), me.max_health(), sh, shd,
                me.gold_count(), me.focus());
}

bool step_to(cambc::bitboard goal) {
    auto& me = cambc::self();
    if (goal.is_set(me.position())) return true;
    if (!me.can_move()) return false;
    auto blocked = cambc::map::walls() | cambc::map::holes() | cambc::map::altars() | cambc::map::spawn_region(team::enemy)
        | cambc::vision::champion_tiles();
    for (const auto& c : cambc::vision::camps()) if (c.is_alive()) blocked.set(c.position());
    blocked.set(me.position(), false);
    goal &= ~blocked;
    cambc::bitboard src; src.clear(); src.set(me.position());
    cambc::distance_field field;
    cambc::bitboard visited;
    field.compute_to(blocked, goal, src, visited);
    auto step = me.position();
    for (auto tile : blocked.reachable_tiles(step, me.base_stats().base_move_speed).positions())
        if (field.get(tile) < field.get(step)) step = tile;
    if (step != me.position()) me.move_absolute(step);
    return goal.is_set(me.position());
}

bool step_to(vec2 t) { cambc::bitboard g; g.clear(); g.set(t); return step_to(g); }
cambc::bitboard home() { return cambc::map::spawn_region(team::ally); }

void attack_twice(const cambc::camp& c) {
    auto& me = cambc::self();
    if (me.can_attack()) me.attack(c);
    if (!me.can_attack() && c.is_alive() && me.abilities()[0].is_ready()) {
        me.abilities()[0].use();
        if (me.can_attack()) me.attack(c);
    }
}

void play_turn() {
    auto& me = cambc::self();
    if (!me.is_alive() || !team_a() || me.champion_name() != cambc::champion_type::varg) return;
    const int r = (int)cambc::round_number();
    if (phase >= 3) log_self("start");

    if (phase == 0) {  // kill the gold block
        std::optional<cambc::camp> target;
        int alive = 0;
        for (const auto& c : cambc::vision::camps())
            if (is_gold_tile(c.position()) && c.is_alive()) {
                ++alive;
                if (!target || c.position().chebyshev_distance(me.position()) < target->position().chebyshev_distance(me.position()))
                    target = c;
            }
        if (!alive) { phase = 1; std::printf("PROBE %d gold_block_dead\n", r); }
        else {
            if (target->position().chebyshev_distance(me.position()) > 1) {
                cambc::bitboard adj; adj.clear(); adj.draw_chebyshev(target->position(), 1);
                for (int x = 4; x <= 5; ++x) for (int y = 0; y <= 3; ++y) adj.set({ x, y }, false);
                vec2 best = me.position(); int bd = 1 << 20;
                for (auto p : adj.positions()) {
                    int d = p.chebyshev_distance(me.position());
                    if (d < bd && !cambc::vision::champion_tiles().is_set(p)) { bd = d; best = p; }
                }
                step_to(best);
            }
            if (target->position().chebyshev_distance(me.position()) <= 1) attack_twice(*target);
            return;
        }
    }
    if (phase == 1) {  // hold a camp tile until paid
        step_to(HOLD);
        if (me.gold_count() >= 150) { phase = 2; log_self("paid"); }
        return;
    }
    if (phase == 2) {  // buy the emblem on spawn
        if (!cambc::map::spawn_region(team::ally).is_set(me.position())) { step_to(home()); }
        if (cambc::map::spawn_region(team::ally).is_set(me.position())) {
            log_self("before_buy");
            me.buy(cambc::item_type::durability_shard_of_health, 5);
            log_self("after_buy");
            phase = 3;
        }
        return;
    }
    if (phase == 3) {  // walk to the golem, wake it and shield
        if (!step_to(GOLEM_ADJ)) return;
        for (const auto& c : cambc::vision::camps())
            if (c.position() == GOLEM && me.can_attack()) {
                me.attack(c);
                std::printf("PROBE %d hit_golem golem_hp=%.2f\n", r, c.health());
            }
        log_self("before_shield");
        me.abilities()[1].use();
        log_self("after_shield");
        shield_round = r;
        phase = 4;
        return;
    }
    if (phase == 4) {  // stay through the shield and one unshielded hit, then leave
        if (r >= shield_round + 7 || me.health() < me.max_health() * 0.5f) phase = 5;
        return;
    }
    if (phase == 5) step_to(home());
}

void play_draft() {
    const auto mine = cambc::draft::current_draft(team::ally);
    const auto theirs = cambc::draft::current_draft(team::enemy);
    auto taken = [&](D d) { return std::find(mine.begin(), mine.end(), d) != mine.end() || std::find(theirs.begin(), theirs.end(), d) != theirs.end(); };
    const std::vector<D> a{ D::varg, D::stellar, D::prism, D::marcella, D::vendetta, D::willow };
    const std::vector<D> b{ D::ryth, D::vendetta, D::stellar, D::prism, D::marcella, D::vesper_vale };
    for (auto d : team_a() ? a : b) if (!taken(d)) { cambc::draft::pick(d); return; }
}
} // namespace

int main() {
    while (true) {
        try {
            if (cambc::is_draft()) play_draft();
            else play_turn();
        } catch (const cambc::error& e) {
            std::printf("PROBE %d err %s\n", (int)cambc::round_number(), e.message().c_str());
        } catch (const std::exception& e) { std::printf("PROBE err %s\n", e.what()); }
        cambc::end_turn();
    }
}
