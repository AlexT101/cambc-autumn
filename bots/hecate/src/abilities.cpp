#include "abilities.h"
#include <algorithm>
#include <array>
#include <optional>
#include <utility>
#include <vector>
#include "safety.h"
#include "params.h"
#include "world.h"

namespace aph {

namespace {

// Values are in enemy health points.
constexpr float stun_value = 80;
constexpr float winning_tribute_value = 5000; // a stun that stops the enemy's game-winning tribute
constexpr float min_value = 40;
constexpr float keep_walk_value = 250;
constexpr float min_camp_value = 50;
constexpr int max_unseen_tiles = 9; // unseen enemies spread over more tiles are not aimed at
constexpr int hold_range = 6;       // camp casts wait while a visible enemy is this close
std::uint64_t enemy_cast_cost(int visible, int unseen) {
    return 12000 + 2500 * static_cast<std::uint64_t>(visible) + 1000 * static_cast<std::uint64_t>(unseen);
}
std::uint64_t camp_cast_cost(std::size_t members, bool ground) { return 2000 + 800 * members + (ground ? 8000 : 0); }

bool walked(const World& world) { return cambc::self().position() != world.me().pos; }

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

    void offer(const Cast& other) {
        if (other.slot >= 0 && other.value > value) *this = other;
    }
    bool execute() const {
        if (slot < 0) return false;
        const auto ability = cambc::self().abilities()[slot];
        try {
            if (champion) return ability.use(*champion);
            if (camp) return ability.use(*camp);
            return ability.use(tile);
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

// `damaging`: the hit's worth already counts a cancelled recall.
float stun_worth(const World& world, const ChampionBelief& e, bool damaging) {
    if (e.facts().passive == Passive::stun_immune) return 0;
    float v = stun_value;
    if (e.channel == Channel::tribute) v += params::tribute_value + params::gem_value * static_cast<float>(e.gems);
    if (e.channel == Channel::tribute && enemy_tribute_wins(world, e)) v += winning_tribute_value;
    if (!damaging && kept_recall(e)) v += params::recall_value;
    return v;
}

struct Target {
    vec2 pos;
    float weight; // chance the enemy is on this tile
    float worth;  // if hit
};

// The scratch vectors and boards here are kept across calls: allocating costs more than the work.

void draw_alive_members(const World& world, int g, bitboard& out) {
    const auto& members = world.map().groups[g].members;
    for (std::size_t i = 0; i < members.size(); ++i)
        if (world.camps[g].health[i] > 0) out.draw_chebyshev(members[i].pos, 1);
}

// Ground centres to skip: their 3x3 would hit a member of a sleeping group, which wakes whole,
// with a monster near us, or of a sleeping Monolith group other than the siege target. In a
// scratch board valid until the next call.
const bitboard& wake_risk(const World& world, vec2 here, int reach) {
    const auto& groups = world.map().groups;
    static bitboard risk{cambc::uninitialized};
    risk.clear();
    for (int g : world.map().groups_near(here, reach)) {
        const auto& c = world.camps[g];
        if (c.state != CampState::alive || c.awake == Awake::awake || groups[g].strength <= 0) continue;
        bool near = groups[g].has_monolith && g != siege_group();
        for (std::size_t i = 0; i < groups[g].members.size() && !near; ++i)
            near = c.health[i] > 0 && groups[g].members[i].strength > 0
                   && dist(here, groups[g].members[i].pos) <= camp_attack_range;
        if (near) draw_alive_members(world, g, risk);
    }
    return risk;
}

// Centres within `range` of `here`, off `skip`.
Cast best_ground(int slot, float min_weight_value, const std::vector<Target>& targets, vec2 here, int range,
                 const bitboard& skip) {
    constexpr int max_range = 5; // ability ranges are 4
    Cast best;
    if (targets.empty()) return best;
    range = std::min(range, max_range);
    const int side = 2 * range + 1;
    std::array<float, (2 * max_range + 1) * (2 * max_range + 1)> value;
    std::fill_n(value.begin(), side * side, 0.0f);
    static bitboard centres{cambc::uninitialized};
    centres.clear();
    for (const auto& t : targets) {
        centres.draw_chebyshev(t.pos, 1);
        for (int dy = -1; dy <= 1; ++dy)
            for (int dx = -1; dx <= 1; ++dx) {
                const int x = t.pos.x + dx - here.x + range, y = t.pos.y + dy - here.y + range;
                if (x >= 0 && x < side && y >= 0 && y < side) value[y * side + x] += t.weight * t.worth;
            }
    }
    static bitboard box{cambc::uninitialized};
    box.clear();
    box.draw_chebyshev(here, static_cast<float>(range));
    centres &= box;
    box.clear();
    box |= centres;
    box &= skip;
    centres ^= box;
    // In board order, which breaks ties.
    for (auto c : Tiles<17 * 17>{centres}) {
        const float v = value[(c.y - here.y + range) * side + (c.x - here.x + range)];
        if (v > best.value && v >= min_weight_value) best.slot = slot, best.value = v, best.tile = c;
    }
    return best;
}

Cast enemy_cast(const World& world, bool keep_walk, const ChampionBelief* hold) {
    auto& me = cambc::self();
    Cast best;
    if (!me.can_cast()) return best;
    const vec2 here = me.position();
    const auto& f = world.me().facts();
    // Most turns no enemy is in reach: skip the engine reads below.
    int reach = -1;
    bool ground = false;
    for (const auto& a : f.abilities)
        if (a.hits_enemies()) reach = std::max(reach, a.reach()), ground |= a.target == Targeting::ground;
    int visible = 0, unseen = 0;
    for (const auto& e : world.enemies) {
        if (!e.alive) continue;
        if (e.visible) visible += dist(here, e.pos) <= reach;
        else unseen += ground && e.tracked;
    }
    if (visible + unseen == 0) return best;
    if (!fuel_ok(enemy_cast_cost(visible, unseen))) {
        note_shortcut("enemy-cast");
        return best;
    }
    const auto& enemy_spawn = world.map().enemy_spawn;
    keep_walk = keep_walk && me.can_move();
    // A stun takes its target's walk as the cast takes ours: with every visible enemy that could
    // reach us next turn stunned, keeping the walk gains nothing. `free_stun`: centres that do so.
    std::vector<const ChampionBelief*> reaching;
    bool unstoppable = false;
    if (keep_walk)
        for (const auto& e : world.enemies) {
            if (!e.alive || !e.visible || !strike(e, next_turn_round(world, e)).hits(dist(here, e.pos))) continue;
            const auto c = e.live();
            if (!c.is_visible() || c.buffs().has_stun()) continue;
            unstoppable |= e.facts().passive == Passive::stun_immune;
            reaching.push_back(&e);
        }
    const bool walk_matters = reaching.empty() || unstoppable;
    static bitboard not_free{cambc::uninitialized}; // ~free_stun
    if (!walk_matters) {
        static bitboard free_stun{cambc::uninitialized};
        free_stun.fill();
        for (const auto* e : reaching) free_stun &= square(e->pos, 1);
        not_free.fill();
        not_free ^= free_stun;
    }
    const bitboard* risk = nullptr;
    for (int s = 0; s < 2; ++s) {
        if (!castable(world, s)) continue;
        const auto& a = f.abilities[s];
        const float threshold = a.excludes_walking && keep_walk ? keep_walk_value : min_value;
        const float raw = raw_damage(s);
        const auto suicidal = [&](const ChampionBelief& e) { return raw > 0 && e.retaliation() >= me.health(); };
        const auto spared = [&](const ChampionBelief& e, float damage, float health) { return &e == hold && damage < health - 0.01f; };
        if (a.target == Targeting::unit) {
            for (const auto& e : world.enemies) {
                if (!e.alive || !e.visible || dist(here, e.pos) > a.range() || suicidal(e)) continue;
                const auto c = e.live();
                if (!c.is_visible()) continue;
                const float damage = damage_to(s, c, raw);
                if (spared(e, damage, c.health())) continue;
                float v = hit_worth(world, e, damage, c.health(), enemy_spawn.is_set(e.pos));
                if (a.stuns && !c.buffs().has_stun()) v += stun_worth(world, e, raw > 0);
                const bool free = a.stuns && !walk_matters && reaching.size() == 1 && reaching[0] == &e;
                if (v >= (free ? min_value : threshold) && v > best.value) best = Cast{s, v, c, std::nullopt, {}};
            }
        } else if (a.target == Targeting::ground) {
            static std::vector<Target> targets;
            targets.clear();
            // The area hits every enemy in it, unseen too: keep it off a Ren whose retaliation kills
            // us and off a held tributer it does not kill.
            static bitboard off{cambc::uninitialized};
            off.clear();
            for (const auto& e : world.enemies) {
                if (!e.alive) continue;
                if (e.visible) {
                    if (dist(here, e.pos) > a.reach()) continue;
                    if (suicidal(e)) {
                        off.draw_chebyshev(e.pos, 1);
                        continue;
                    }
                    const auto c = e.live();
                    if (!c.is_visible()) continue;
                    const float damage = damage_to(s, c, raw);
                    if (spared(e, damage, c.health())) {
                        off.draw_chebyshev(e.pos, 1);
                        continue;
                    }
                    const float stun = a.stuns && !c.buffs().has_stun() ? stun_worth(world, e, raw > 0) : 0;
                    const float hit = hit_worth(world, e, damage, c.health(), enemy_spawn.is_set(e.pos));
                    targets.push_back({e.pos, 1, hit + stun});
                } else if (e.tracked && !e.possible.is_empty()) {
                    const int n = static_cast<int>(e.possible.count());
                    if (n > max_unseen_tiles) continue;
                    const auto near = positions_within(e.possible, here, a.reach());
                    if (near.empty()) continue;
                    if (suicidal(e)) {
                        for (auto p : near) off.draw_chebyshev(p, 1);
                        continue;
                    }
                    const float health = e.health > 0 ? e.health : e.max_health;
                    const float hit = std::min(raw, health);
                    const float stun = a.stuns ? stun_worth(world, e, raw > 0) : 0;
                    for (auto p : near)
                        targets.push_back({p, 1.0f / static_cast<float>(n),
                                           hit_worth(world, e, hit, health, enemy_spawn.is_set(p)) + stun});
                }
            }
            if (targets.empty()) continue;
            if (!risk) risk = &wake_risk(world, here, a.reach());
            static bitboard skip{cambc::uninitialized};
            skip.clear();
            skip |= *risk;
            skip |= off;
            best.offer(best_ground(s, threshold, targets, here, a.range(), skip));
            if (a.stuns && threshold > min_value && !walk_matters) {
                skip |= not_free;
                best.offer(best_ground(s, min_value, targets, here, a.range(), skip));
            }
        }
    }
    return best;
}

Cast camp_cast(const World& world, int group, bool attackers_only, bool any_value) {
    auto& me = cambc::self();
    if (!me.can_cast()) return {};
    const auto& f = world.me().facts();
    const std::array<bool, 2> ready{castable(world, 0), castable(world, 1)};
    if (!ready[0] && !ready[1]) return {};
    const bool stuns = (ready[0] && f.abilities[0].stuns) || (ready[1] && f.abilities[1].stuns);
    const vec2 here = me.position();
    const auto& g = world.map().groups[group];
    if ((g.has_monolith && group != siege_group()) || world.camps[group].state != CampState::alive) return {};
    if (enemy_within(world, here, hold_range)) return {};
    const bool ground =
        (ready[0] && f.abilities[0].target == Targeting::ground) || (ready[1] && f.abilities[1].target == Targeting::ground);
    if (!fuel_ok(camp_cast_cost(g.members.size(), ground))) {
        note_shortcut("camp-cast");
        return {};
    }

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
        bool exposed = dist(here, g.members[i].pos) <= camp_attack_range;
        // At a Monolith, a stun spares whichever of us it would hit.
        for (const auto& a : world.allies)
            exposed |= g.has_monolith && !exposed && a.alive && a.visible && dist(a.pos, g.members[i].pos) <= camp_attack_range;
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
            for (const auto& m : members) targets.push_back({m.pos, 1, std::min(raw, m.health) + (a.stuns ? m.stun : 0)});
            static bitboard skip{cambc::uninitialized};
            skip.clear();
            for (int other : world.map().groups_near(here, a.reach()))
                if (other != group && world.camps[other].state == CampState::alive) draw_alive_members(world, other, skip);
            best.offer(best_ground(s, any_value ? 1.0f : min_camp_value, targets, here, a.range(), skip));
        }
    }
    return best;
}

} // namespace

bool enemy_tribute_wins(const World& world, const ChampionBelief& e) {
    return e.alive && e.visible && e.channel == Channel::tribute
           && world.score.enemy + e.gems >= static_cast<int>(cambc::constants::winning_gems);
}

bool cast_at_enemies(const World& world, bool keep_walk, const ChampionBelief* hold) {
    try {
        return enemy_cast(world, keep_walk, hold).execute();
    } catch (const cambc::error&) {
        return false;
    }
}

Cast& chosen_cast() {
    static Cast chosen;
    return chosen;
}

float enemy_cast_value(const World& world, bool keep_walk, const ChampionBelief* hold, bool& exclusive) {
    auto& chosen = chosen_cast();
    try {
        chosen = enemy_cast(world, keep_walk, hold);
    } catch (const cambc::error&) {
        chosen = {};
    }
    exclusive = chosen.slot >= 0 && world.me().facts().abilities[chosen.slot].excludes_walking;
    return chosen.slot >= 0 ? chosen.value : 0.0f;
}

bool cast_chosen() {
    const Cast cast = std::exchange(chosen_cast(), Cast{});
    try {
        return cast.execute();
    } catch (const cambc::error&) {
        return false;
    }
}

bool cast_at_camp(const World& world, int group, bool attackers_only, bool any_value) {
    try {
        return camp_cast(world, group, attackers_only, any_value).execute();
    } catch (const cambc::error&) {
        return false;
    }
}

} // namespace aph
