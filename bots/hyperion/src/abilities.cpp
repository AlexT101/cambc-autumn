#include "abilities.h"
#include <algorithm>
#include <array>
#include <optional>
#include <vector>
#include "params.h"
#include "pathing.h"
#include "world.h"

namespace aph {

namespace {

// Values are in enemy health points.
constexpr float stun_value = 80;
constexpr float winning_tribute_value = 5000; // a stun that stops the enemy's game-winning tribute
constexpr float min_value = 40;
constexpr float min_landing_value = 250; // a landing moves us off the goal's way
constexpr float min_camp_value = 50;
constexpr int hold_range = 6;       // camp casts wait while a visible enemy is this close
constexpr int max_unseen_tiles = 9; // unseen enemies spread over more tiles are not kept off

bool walked(const World& world) { return my_position() != world.me().pos; }

bool castable(const World& world, int slot) {
    const auto& a = world.me().facts().abilities[slot];
    return a.hits_enemies() && !(a.excludes_walking && walked(world)) && world.me().ability_ready(slot, world.round);
}

struct Cast {
    int slot = -1;
    float value = 0;
    std::optional<cambc::champion> champion;
    std::optional<cambc::camp> camp;
    vec2 tile{-1, -1};
    bool dash = false; // a landing on `tile`

    void offer(const Cast& other) {
        if (other.slot >= 0 && other.value > value) *this = other;
    }
    bool execute() const {
        if (slot < 0) return false;
        const auto ability = cambc::self().abilities()[slot];
        try {
            if (champion) return ability.use(*champion);
            if (camp) return ability.use(*camp);
            const bool cast = ability.use(tile);
            outside_dashes() += cast && dash;
            return cast;
        } catch (const cambc::error&) {
            return false;
        }
    }
};

float raw_damage(int slot) {
    try {
        return cambc::self().abilities()[slot].damage_amount();
    } catch (const cambc::error&) {
        return 0;
    }
}

// Health lost after mitigation and shields, capped at health.
float damage_to(int slot, const cambc::champion& target, float raw) {
    if (raw <= 0) return 0;
    try {
        return cambc::self().abilities()[slot].damage_amount(target);
    } catch (const cambc::error&) {
        return std::min(raw, target.health());
    }
}

bool kept_recall(const ChampionBelief& e) {
    return e.channel == Channel::recall && e.visible
           && aph::kept_recall(e.live(), e.fast_recall ? home_recall_time : static_cast<int>(cambc::constants::recall_time));
}

// A kill takes the bag, both bags for Cassi and Issac, who die together. Other damage to an
// enemy on its spawn heals at its turn end, and damage to the healthier of Cassi and Issac only
// counts once it takes that body below the other.
float hit_worth(const World& world, const ChampionBelief& e, float damage, float health, bool on_spawn) {
    if (health > 0 && damage >= health - 0.01f) {
        return health + params::life_value + params::gem_value * static_cast<float>(pair_gems(world, e));
    }
    if (on_spawn || damage <= 0) return 0;
    return useful_damage(damage, health, linked_partner_health(world, e)) + (kept_recall(e) ? params::recall_value : 0);
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
        const auto& c = world.camps[g];
        if (c.state != CampState::alive || c.fully_awake() || groups[g].strength <= 0 || g == siege_group()) continue;
        for (std::size_t i = 0; i < groups[g].members.size(); ++i)
            if (c.health[i] > 0 && dist(p, groups[g].members[i].pos) <= radius) return true;
    }
    return false;
}

int unseen_retaliators(const World& world, vec2 here, int reach, float raw, vec2* out, int size) {
    int n = 0;
    if (raw <= 0) return n;
    for (const auto& e : world.enemies) {
        if (!e.alive || e.visible || !e.tracked || e.retaliation() < my_health() || board_empty(e.possible)) continue;
        if (board_count(e.possible) > max_unseen_tiles) continue;
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
        const auto& c = world.camps[g];
        if (c.state != CampState::alive || c.fully_awake() || groups[g].strength <= 0) continue;
        bool near = groups[g].has_monolith && g != siege_group();
        for (std::size_t i = 0; i < groups[g].members.size() && !near; ++i)
            near = c.health[i] > 0 && groups[g].members[i].strength > 0 && c.maybe_asleep(i)
                   && dist(here, groups[g].members[i].pos) <= groups[g].members[i].reach;
        if (near) draw_alive_members(world, g, risk);
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

// The landing that `keep` accepts whose `radius` around it hits most, nearest `here` on ties.
template <class Keep>
Cast best_landing(int slot, float min_value, const std::vector<Target>& targets, const bitboard& landings, vec2 here,
                  int radius, Keep keep) {
    Cast best;
    if (targets.empty()) return best;
    int best_dist = 0;
    for (auto p : Tiles<5 * 5>{landings}) {
        float v = 0;
        for (const auto& t : targets)
            if (dist(p, t.pos) <= radius) v += t.worth;
        const int d = dist(p, here);
        if (v < min_value || v < best.value || (v == best.value && d >= best_dist) || !keep(p)) continue;
        best.slot = slot, best.value = v, best.tile = p, best.dash = true, best_dist = d;
    }
    return best;
}

Cast enemy_cast(const World& world, float walk, bool landings) {
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
    const auto& enemy_spawn = world.map().enemy_spawn;
    if (!my_can_move()) walk = 0;
    const bitboard* risk = nullptr;
    const auto keep_off_unseen = [&](const AbilityFacts& a, float raw, int radius, bitboard& off) {
        // Ren alone retaliates and picks are unique: one enemy's tiles at most.
        std::array<vec2, max_unseen_tiles> unseen;
        const int n = unseen_retaliators(world, here, a.reach(), raw, unseen.data(), max_unseen_tiles);
        for (int k = 0; k < n; ++k) draw_square(off, unseen[k], static_cast<float>(radius));
    };
    for (int s = 0; s < 2; ++s) {
        if (!castable(world, s)) continue;
        const auto& a = f.abilities[s];
        const float threshold = min_value + (a.excludes_walking ? walk : 0.0f);
        const float raw = raw_damage(s);
        const auto suicidal = [&](const ChampionBelief& e) { return raw > 0 && e.retaliation() >= my_health(); };
        if (a.lands()) {
            if (!landings) continue;
            // It moves us: worth only what an excludes-walking cast must be worth to keep the walk.
            static std::vector<Target> targets;
            targets.clear();
            static bitboard off{cambc::uninitialized};
            clear_board(off);
            for (const auto& e : world.enemies) {
                if (!e.alive || !e.visible || dist(here, e.pos) > a.reach()) continue;
                const auto c = e.live();
                if (!c.is_visible()) continue;
                const float damage = damage_to(s, c, raw);
                if (suicidal(e)) {
                    draw_square(off, e.pos, static_cast<float>(a.radius));
                    continue;
                }
                const float stun = a.stuns && !c.buffs().has_stun() ? stun_worth(world, e, raw > 0) : 0;
                targets.push_back({e.pos, hit_worth(world, e, damage, c.health(), test(enemy_spawn, e.pos)) + stun});
            }
            if (targets.empty()) continue;
            keep_off_unseen(a, raw, a.radius, off);
            best.offer(best_landing(s, min_landing_value, targets, dash_landings_from(world.map(), here, &off), here, a.radius,
                                    [&](vec2 p) { return !landing_wakes(world, p, a.radius); }));
        } else if (a.target == Targeting::unit) {
            for (const auto& e : world.enemies) {
                if (!e.alive || !e.visible || dist(here, e.pos) > a.range() || suicidal(e)) continue;
                const auto c = e.live();
                if (!c.is_visible()) continue;
                float v = hit_worth(world, e, damage_to(s, c, raw), c.health(), test(enemy_spawn, e.pos));
                if (a.stuns && !c.buffs().has_stun()) v += stun_worth(world, e, raw > 0);
                if (v >= threshold && v > best.value) best = Cast{s, v, c, std::nullopt, {}};
            }
        } else if (a.target == Targeting::ground) {
            static std::vector<Target> targets;
            targets.clear();
            // The area hits every enemy in it, unseen too: keep it off a Ren whose retaliation kills us.
            static bitboard off{cambc::uninitialized};
            clear_board(off);
            for (const auto& e : world.enemies) {
                if (!e.alive || !e.visible || dist(here, e.pos) > a.reach()) continue;
                if (suicidal(e)) {
                    draw_square(off, e.pos, 1);
                    continue;
                }
                const auto c = e.live();
                if (!c.is_visible()) continue;
                const float stun = a.stuns && !c.buffs().has_stun() ? stun_worth(world, e, raw > 0) : 0;
                const float hit = hit_worth(world, e, damage_to(s, c, raw), c.health(), test(enemy_spawn, e.pos));
                targets.push_back({e.pos, hit + stun});
            }
            if (targets.empty()) continue;
            keep_off_unseen(a, raw, 1, off);
            if (!risk) risk = &wake_risk(world, here, a.reach());
            static bitboard skip{cambc::uninitialized};
            or_into(*risk, off, skip);
            best.offer(best_ground(s, threshold, targets, here, a.range(), skip));
        }
    }
    return best;
}

Cast camp_cast(const World& world, int group, bool attackers_only, bool any_value) {
    if (!my_can_cast()) return {};
    const auto& f = world.me().facts();
    const std::array<bool, 2> ready{castable(world, 0), castable(world, 1)};
    if (!ready[0] && !ready[1]) return {};
    const bool stuns = (ready[0] && f.abilities[0].stuns) || (ready[1] && f.abilities[1].stuns);
    const vec2 here = my_position();
    const auto& g = world.map().groups[group];
    if ((g.has_monolith && group != siege_group()) || world.camps[group].state != CampState::alive) return {};
    if (enemy_within(world, here, hold_range)) return {};

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
        if (!c.is_visible()) continue;
        const float health = c.health();
        if (health <= 0) continue;
        // A stunned monster skips its next attack, which goes to the nearest champion: one of us
        // when we are in its reach, enemies being held off above.
        bool exposed = dist(here, g.members[i].pos) <= g.members[i].reach;
        // At a Monolith, a stun spares whichever of us it would hit.
        for (const auto& a : world.allies)
            exposed |= g.has_monolith && !exposed && a.alive && a.visible && dist(a.pos, g.members[i].pos) <= g.members[i].reach;
        const float stun = stuns && exposed && !c.buffs().has_stun() ? g.members[i].strength : 0;
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
            best.offer(best_landing(s, any_value ? 1.0f : min_camp_value, targets, dash_landings_from(world.map(), here, &skip),
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

bool cast_at_enemies(const World& world, float walk) {
    Phase phase{"cast_at_enemies"};
    world.throw_if_stale();
    try {
        return enemy_cast(world, walk, true).execute();
    } catch (const cambc::error&) {
        return false;
    }
}

bool cast_at_camp(const World& world, int group, bool attackers_only, bool any_value) {
    world.throw_if_stale();
    try {
        const bool cast = camp_cast(world, group, attackers_only, any_value).execute();
        camp_hits() += cast;
        return cast;
    } catch (const cambc::error&) {
        return false;
    }
}

} // namespace aph
