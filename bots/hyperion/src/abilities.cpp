#include "abilities.h"
#include <algorithm>
#include <array>
#include <cstdio>
#include <optional>
#include <vector>
#include "params.h"
#include "pathing.h"
#include "plan.h"
#include "safety.h"
#include "world.h"

namespace aph {

namespace {

// Values are in enemy health points.
constexpr float stun_value = 80;
constexpr float winning_tribute_value = 5000; // a stun that stops the enemy's game-winning tribute
constexpr float min_value = 40;
constexpr float min_landing_value = 250; // a landing moves us off the goal's way
constexpr float min_camp_value = 50;

bool walked(const World& world) { return my_position() != world.me().pos; }

bool castable(const World& world, int slot) {
    const auto& a = world.me().facts().abilities[slot];
    return a.hits_enemies() && !(a.excludes_walking && walked(world)) && world.me().ability_ready(slot, world.round);
}

struct Cast {
    int slot = -1;
    float value = 0;
    std::optional<cambc::handle_champion_t> champion;
    std::optional<cambc::camp> camp;
    vec2 tile{-1, -1};
    bool dash = false; // a landing on `tile`

    void offer(const Cast& other) {
        if (other.slot >= 0 && other.value > value) *this = other;
    }
    bool execute() const {
        if (slot < 0) return false;
        try {
            if (champion) return cast_slot_on(slot, *champion);
            if (camp) return cast_slot_on(slot, static_cast<cambc::handle_camp_t>(*camp));
            const bool cast = cast_slot(slot, tile);
            outside_dashes() += cast && dash;
            return cast;
        } catch (const cambc::error&) {
            return false;
        }
    }
};

float raw_damage(int slot) {
    try {
        return my_damage(slot);
    } catch (const cambc::error&) {
        return 0;
    }
}

// Health lost after mitigation and shields, capped at health.
float damage_to(int slot, cambc::handle_champion_t target, float raw) {
    if (raw <= 0) return 0;
    try {
        return my_damage_to(slot, target);
    } catch (const cambc::error&) {
        return std::min(raw, record_of(target).health);
    }
}

bool kept_recall(const ChampionBelief& e) {
    return e.channel == Channel::recall && e.visible
           && aph::kept_recall(e.handle, e.fast_recall ? home_recall_time : static_cast<int>(cambc::constants::recall_time));
}

} // namespace

float stun_worth(const World& world, const ChampionBelief& e, bool damaging) {
    if (e.facts().passive == Passive::stun_immune) return 0;
    float v = stun_value;
    if (e.channel == Channel::tribute) v += params::tribute_value + params::gem_value * static_cast<float>(e.gems);
    if (e.channel == Channel::tribute && enemy_tribute_wins(world, e)) v += winning_tribute_value;
    if (!damaging && kept_recall(e)) v += params::recall_value;
    return v;
}

bool landing_wakes(const World& world, vec2 p, int radius) {
    const auto& groups = world.map().groups;
    for (int g : world.map().groups_near(p, radius)) {
        if (g == siege_group() || !hit_wakes(world, g)) continue;
        for (std::size_t i = 0; i < groups[g].members.size(); ++i)
            if (world.camps[g].health[i] > 0 && dist(p, groups[g].members[i].pos) <= radius) return true;
    }
    return false;
}

int unseen_retaliators(const World& world, vec2 here, int reach, float raw, float health, vec2* out, int size) {
    int n = 0;
    if (raw <= 0) return n;
    for (const auto& e : world.enemies) {
        if (!e.alive || e.visible || !e.tracked || !retaliation_kills(raw, e.retaliation(), health)) continue;
        if (const auto count = board_count(e.possible); count == 0 || count > max_unseen_tiles) continue;
        for (auto p : positions_within(e.possible, here, reach)) {
            if (n == size) return n;
            out[n++] = p;
        }
    }
    return n;
}

namespace {

struct Target {
    vec2 pos;
    float worth; // if hit
};

// The scratch vectors and boards here are kept across calls: allocating costs more than the work.

void draw_alive_members(const World& world, int g, bitboard& out, int radius = 1) {
    const auto& members = world.map().groups[g].members;
    for (std::size_t i = 0; i < members.size(); ++i)
        if (world.camps[g].health[i] > 0) draw_square(out, members[i].pos, static_cast<float>(radius));
}

// Ground centres to skip: their 3x3 would hit a member of a sleeping group, which wakes whole,
// with a monster near us, or of a sleeping Monolith group other than the siege target. In a
// scratch board valid until the next call.
const bitboard& wake_risk(const World& world, vec2 here, int reach) {
    const auto& groups = world.map().groups;
    static bitboard risk{cambc::uninitialized};
    clear_board(risk);
    for (int g : world.map().groups_near(here, reach)) {
        const bool monolith = groups[g].has_monolith && g != siege_group();
        if (monolith ? hit_wakes(world, g) : hit_wakes(world, g, here)) draw_alive_members(world, g, risk);
    }
    return risk;
}

// Centres within `range` of `here`, off `skip`.
Cast best_ground(int slot, float min_value, const std::vector<Target>& targets, vec2 here, int range,
                 const bitboard& skip) {
    constexpr int max_range = 5; // ability ranges are 4
    Cast best;
    if (targets.empty()) return best;
    range = std::min(range, max_range);
    const int side = 2 * range + 1;
    std::array<float, (2 * max_range + 1) * (2 * max_range + 1)> value;
    // Only the cells around a target are read: clear those alone when fewer.
    const auto around = [&](const Target& t, auto&& f) {
        for (int dy = -1; dy <= 1; ++dy)
            for (int dx = -1; dx <= 1; ++dx) {
                const int x = t.pos.x + dx - here.x + range, y = t.pos.y + dy - here.y + range;
                if (x >= 0 && x < side && y >= 0 && y < side) f(value[static_cast<std::size_t>(y * side + x)]);
            }
    };
    if (9 * targets.size() < static_cast<std::size_t>(side * side))
        for (const auto& t : targets) around(t, [](float& v) { v = 0; });
    else
        std::fill_n(value.begin(), side * side, 0.0f);
    static bitboard centres{cambc::uninitialized};
    clear_board(centres);
    for (const auto& t : targets) {
        draw_square(centres, t.pos, 1);
        around(t, [&](float& v) { v += t.worth; });
    }
    static bitboard box{cambc::uninitialized};
    clear_board(box);
    draw_square(box, here, static_cast<float>(range));
    and_into(centres, box, centres);
    and_into(centres, skip, box);
    xor_into(centres, box, centres);
    // In board order, which breaks ties.
    for (auto c : Tiles<17 * 17>{centres}) {
        const float v = value[(c.y - here.y + range) * side + (c.x - here.x + range)];
        if (v > best.value && v >= min_value) best.slot = slot, best.value = v, best.tile = c;
    }
    return best;
}

// The landing that `keep` and pathing.landing_clear() accept whose `radius` around it hits most, then
// the least in danger (tile().worst()), then nearest `here`. Both are asked in that order, only until
// one passes; landing_clear() asks and tile() reads stop at max_asks each.
template <class Keep>
Cast best_landing(Pathing& pathing, int slot, float min_value, const std::vector<Target>& targets, const bitboard& landings, vec2 here,
                  int radius, Keep keep) {
    Cast best;
    if (targets.empty()) return best;
    struct Option {
        vec2 p;
        float value, worst; // worst: -1 until read
        int dist;
    };
    constexpr int max_asks = 6;
    std::array<Option, 5 * 5> left, tied;
    int n = 0;
    for (auto p : Tiles<5 * 5>{landings}) {
        float v = 0;
        for (const auto& t : targets)
            if (dist(p, t.pos) <= radius) v += t.worth;
        if (v >= min_value) left[n++] = {p, v, -1, dist(p, here)};
    }
    const int options = n;
    auto* safety = pathing.safety();
    const auto safer = [](const Option& a, const Option& b) { return a.worst >= 0 && (b.worst < 0 || a.worst < b.worst); };
    int asks = 0, reads = 0, banned = 0;
    float chosen = -1;
    while (n > 0 && asks < max_asks && best.slot < 0) {
        // The best value left moves to `tied`, nearest first.
        float top = left[0].value;
        for (int i = 1; i < n; ++i) top = std::max(top, left[i].value);
        int run = 0, rest = 0;
        for (int i = 0; i < n; ++i) {
            if (left[i].value != top) {
                left[rest++] = left[i];
                continue;
            }
            int j = run++;
            for (; j > 0 && left[i].dist < tied[j - 1].dist; --j) tied[j] = tied[j - 1];
            tied[j] = left[i];
        }
        n = rest;
        // Danger orders only ties: the nearest are read first, and unread ones stay last.
        if (safety && run > 1) {
            for (int i = 0; i < run && reads < max_asks; ++i, ++reads) tied[i].worst = safety->tile(tied[i].p).worst();
            for (int i = 1; i < run; ++i)
                for (int j = i; j > 0 && safer(tied[j], tied[j - 1]); --j) std::swap(tied[j], tied[j - 1]);
        }
        for (int i = 0; i < run && asks < max_asks; ++i) {
            if (!keep(tied[i].p)) continue;
            ++asks;
            if (!pathing.landing_clear(tied[i].p)) {
                ++banned;
                continue;
            }
            best.slot = slot, best.value = top, best.tile = tied[i].p, best.dash = true, chosen = tied[i].worst;
            break;
        }
    }
    debug_block({
        if (options > 0)
            std::printf("LANDING %u %c %d %d %.0f %d\n", cambc::round_number(), min_value == min_landing_value ? 'e' : 'c', best.tile.x,
                        best.tile.y, chosen, banned);
    });
    return best;
}

Cast enemy_cast(const World& world, Pathing& pathing, float walk, bool landings) {
    Cast best;
    if (!my_can_cast()) return best;
    const vec2 here = my_position();
    const auto& f = world.me().facts();
    // Most turns no enemy is in reach: skip the engine reads below.
    int reach = -1;
    for (const auto& a : f.abilities)
        if (a.hits_enemies() && (landings || !a.lands())) reach = std::max(reach, a.reach());
    int visible = 0;
    for (const auto& e : world.enemies) visible += e.alive && e.visible && dist(here, e.pos) <= reach;
    if (visible == 0) return best;
    const float health = my_health();
    const auto& enemy_spawn = world.map().enemy_spawn;
    if (!my_can_move()) walk = 0;
    // The one target loop: each visible enemy in reach, its retaliation and live reads shared by the
    // slots, read from the engine when a slot first aims at it.
    struct Foe {
        const ChampionBelief* e;
        float back;
        float health = 0;
        bool read = false, seen = false;
        std::int8_t stunned = -1; // read when a stun is first priced
    };
    static std::vector<Foe> foes;
    foes.clear();
    for (const auto& e : world.enemies)
        if (e.alive && e.visible && dist(here, e.pos) <= reach) foes.push_back({&e, e.retaliation()});
    const auto seen = [&](Foe& x) {
        if (!x.read) {
            x.read = true;
            const auto* live = visible_record(x.e->handle);
            x.seen = live != nullptr;
            if (x.seen) x.health = live->health;
        }
        return x.seen;
    };
    const bitboard* risk = nullptr;
    for (int s = 0; s < 2; ++s) {
        if (!castable(world, s)) continue;
        const auto& a = f.abilities[s];
        const float threshold = min_value + (a.excludes_walking ? walk : 0.0f);
        const float raw = raw_damage(s);
        // A kill takes the bag, both for Cassi and Issac; a cancelled recall counts only if damaged.
        const auto worth = [&](Foe& x) {
            const auto& e = *x.e;
            const float damage = damage_to(s, e.handle, raw);
            float stun = 0;
            if (a.stuns && e.facts().passive != Passive::stun_immune) {
                if (x.stunned < 0) x.stunned = has_stun(e.handle);
                if (!x.stunned) stun = stun_worth(world, e, raw > 0);
            }
            const float bag = params::gem_value * static_cast<float>(pair_gems(world, e));
            const float recall = damage > 0 && kept_recall(e) ? params::recall_value : 0.0f;
            return hit_worth(damage, x.health, test(enemy_spawn, e.pos), bag, linked_partner_health(world, e), recall) + stun;
        };
        if (a.lands() || a.target == Targeting::ground) {
            if (a.lands() && !landings) continue;
            // A landing moves us: worth only what an excludes-walking cast must be worth to keep the walk.
            const int radius = a.lands() ? a.radius : 1;
            static std::vector<Target> targets;
            targets.clear();
            // The area hits every enemy in it, unseen too: keep it off a Ren whose retaliation kills us.
            static bitboard off{cambc::uninitialized};
            clear_board(off);
            for (auto& x : foes) {
                if (dist(here, x.e->pos) > a.reach()) continue;
                // Before the sight check: after a walk the area still hits a Ren seen at turn start.
                if (retaliation_kills(raw, x.back, health)) {
                    draw_square(off, x.e->pos, static_cast<float>(radius));
                    continue;
                }
                if (seen(x)) targets.push_back({x.e->pos, worth(x)});
            }
            if (targets.empty()) continue;
            // Ren alone retaliates and picks are unique: one enemy's tiles at most.
            std::array<vec2, max_unseen_tiles> unseen;
            const int n = unseen_retaliators(world, here, a.reach(), raw, health, unseen.data(), max_unseen_tiles);
            for (int k = 0; k < n; ++k) draw_square(off, unseen[k], static_cast<float>(radius));
            if (a.lands()) {
                best.offer(best_landing(pathing, s, min_landing_value, targets, dash_landings_from(world.map(), here, &off), here, a.radius,
                                        [&](vec2 p) { return !landing_wakes(world, p, a.radius); }));
            } else {
                if (!risk) risk = &wake_risk(world, here, a.reach());
                static bitboard skip{cambc::uninitialized};
                or_into(*risk, off, skip);
                best.offer(best_ground(s, threshold, targets, here, a.range(), skip));
            }
        } else if (a.target == Targeting::unit) {
            for (auto& x : foes) {
                if (dist(here, x.e->pos) > a.range() || retaliation_kills(raw, x.back, health) || !seen(x)) continue;
                const float v = worth(x);
                if (v >= threshold && v > best.value) best = Cast{s, v, x.e->handle, std::nullopt, {}};
            }
        }
    }
    return best;
}

// Camp casts wait while a visible enemy could strike us here within a turn's walk.
bool camp_cast_held(const World& world, Pathing& pathing, vec2 here) {
    auto* safety = pathing.safety();
    const bool held = safety && safety->engaged_within(here, 1);
    debug_block({
        static int last = -1;
        if (const bool old = enemy_within(world, here, 6); old != held && last != world.round) {
            last = world.round;
            std::printf("HOLD-MISMATCH %d cast %d %d\n", world.round, old ? 1 : 0, held ? 1 : 0);
        }
    });
    return held;
}

Cast camp_cast(const World& world, Pathing& pathing, int group, bool attackers_only, bool any_value) {
    if (!my_can_cast()) return {};
    const auto& f = world.me().facts();
    const std::array<bool, 2> ready{castable(world, 0), castable(world, 1)};
    if (!ready[0] && !ready[1]) return {};
    const bool stuns = (ready[0] && f.abilities[0].stuns) || (ready[1] && f.abilities[1].stuns);
    const vec2 here = my_position();
    const auto& g = world.map().groups[group];
    if ((g.has_monolith && group != siege_group()) || world.camps[group].state != CampState::alive) return {};
    if (camp_cast_held(world, pathing, here)) return {};

    struct Member {
        cambc::camp camp;
        vec2 pos;
        float health, stun;
    };
    static std::vector<Member> members;
    members.clear();
    for (int i = 0; i < static_cast<int>(g.members.size()); ++i) {
        if (world.camps[group].health[i] <= 0 || (attackers_only && g.members[i].strength <= 0)
            || !cambc::vision::has_camp(g.members[i].pos))
            continue;
        auto c = g.camp(i);
        const auto* live = visible_camp(c);
        if (!live) continue;
        const float health = live->health;
        if (health <= 0) continue;
        // A stunned monster skips its next attack, which goes to the nearest champion: one of us
        // when we are in its reach, enemies being held off above.
        bool exposed = dist(here, g.members[i].pos) <= g.members[i].reach;
        // At a Monolith, a stun spares whichever of us it would hit.
        for (const auto& a : world.allies)
            exposed |= g.has_monolith && !exposed && a.alive && a.visible && dist(a.pos, g.members[i].pos) <= g.members[i].reach;
        const float stun = stuns && exposed && !camp_has_stun(c) ? g.members[i].strength : 0;
        members.push_back({c, g.members[i].pos, health, stun});
    }
    if (members.empty()) return {};

    Cast best;
    for (int s = 0; s < 2; ++s) {
        if (!ready[s]) continue;
        const auto& a = f.abilities[s];
        const float raw = raw_damage(s);
        // A stun that deals nothing and keeps the walk costs only its cooldown.
        const float floor = any_value || (g.has_monolith && a.stuns && raw <= 0 && !a.excludes_walking) ? 1.0f : min_camp_value;
        if (a.target == Targeting::unit) {
            for (const auto& m : members) {
                if (dist(here, m.pos) > a.range()) continue;
                const float v = std::min(raw, m.health) + (a.stuns ? m.stun : 0);
                if (v >= floor && v > best.value) best = Cast{s, v, std::nullopt, m.camp, {}};
            }
        } else if (a.target == Targeting::ground) {
            static std::vector<Target> targets;
            targets.clear();
            for (const auto& m : members) targets.push_back({m.pos, std::min(raw, m.health) + (a.stuns ? m.stun : 0)});
            static bitboard skip{cambc::uninitialized};
            clear_board(skip);
            for (int other : world.map().groups_near(here, a.reach()))
                if (other != group && world.camps[other].state == CampState::alive) draw_alive_members(world, other, skip);
            best.offer(best_ground(s, any_value ? 1.0f : min_camp_value, targets, here, a.range(), skip));
        } else if (a.lands()) {
            // A dash off a cleared group gives up its capture.
            if (const int at = world.map().group_at(here); at >= 0 && world.camps[at].state == CampState::cleared) continue;
            static std::vector<Target> targets;
            targets.clear();
            for (const auto& m : members) targets.push_back({m.pos, std::min(raw, m.health) + (a.stuns ? m.stun : 0)});
            static bitboard skip{cambc::uninitialized};
            clear_board(skip);
            for (int other : world.map().groups_near(here, a.reach()))
                if (other != group && world.camps[other].state == CampState::alive) draw_alive_members(world, other, skip, a.radius);
            // Not into the reach of another group's monsters.
            const auto keep = [&](vec2 p) {
                for (int other : world.map().groups_near(p, world.map().max_camp_reach)) {
                    if (other == group || world.camps[other].state != CampState::alive) continue;
                    const auto& ms = world.map().groups[other].members;
                    for (std::size_t i = 0; i < ms.size(); ++i)
                        if (world.camps[other].health[i] > 0 && ms[i].strength > 0 && dist(p, ms[i].pos) <= ms[i].reach
                            && dist(here, ms[i].pos) > ms[i].reach)
                            return false;
                }
                return true;
            };
            best.offer(best_landing(pathing, s, any_value ? 1.0f : min_camp_value, targets, dash_landings_from(world.map(), here, &skip),
                                    here, a.radius, keep));
        }
    }
    return best;
}

} // namespace

bool enemy_tribute_wins(const World& world, const ChampionBelief& e) {
    return e.alive && e.visible && e.channel == Channel::tribute
           && world.score.enemy + e.gems >= static_cast<int>(cambc::constants::winning_gems);
}

bool cast_at_enemies(const World& world, Pathing& pathing, float walk) {
    Phase phase{"cast_at_enemies"};
    world.throw_if_stale();
    if (my_can_cast() && casts_searched(world)) {
        debug_block({ std::printf("CAST-WASTED %d %u\n", world.round, static_cast<unsigned>(world.me().handle)); });
        return false;
    }
    try {
        return enemy_cast(world, pathing, walk, true).execute();
    } catch (const cambc::error&) {
        return false;
    }
}

// A kill takes the bag; other damage on its spawn heals at its turn end.
float hit_worth(float damage, float health, bool spawn, float bag, float partner, float recall) {
    if (health <= 0) return 0;
    if (damage >= health - 0.01f) return health + params::life_value + bag;
    if (spawn) return 0;
    return useful_damage(damage, health, partner) + recall;
}

bool cast_at_camp(const World& world, Pathing& pathing, int group, bool attackers_only, bool any_value) {
    Phase phase{"cast_at_camp"};
    world.throw_if_stale();
    try {
        const bool cast = camp_cast(world, pathing, group, attackers_only, any_value).execute();
        camp_hits() += cast;
        return cast;
    } catch (const cambc::error&) {
        return false;
    }
}

} // namespace aph
