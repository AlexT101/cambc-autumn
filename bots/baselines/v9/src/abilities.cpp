#include "abilities.h"
#include <algorithm>
#include <optional>
#include <vector>
#include "world.h"

namespace aph {

namespace {

// Values are in enemy health points.
constexpr float kill_bonus = 300;
constexpr float gem_value = 15;
constexpr float stun_value = 80;
constexpr float tribute_stun_bonus = 100;
constexpr float recall_cancel_value = 60;
constexpr float min_value = 40;
constexpr float keep_walk_value = 250;
constexpr float min_camp_value = 50;
constexpr int max_unseen_tiles = 9; // unseen enemies spread over more tiles are not aimed at
constexpr int hold_range = 6;       // camp casts wait while a visible enemy is this close
constexpr int camp_attack_range = 3;
constexpr std::uint64_t fuel_needed = 18000; // measured: mean ~1k, max 16k

cambc::champion live(const ChampionBelief& b) { return cambc::detail::handle_access::make_champion(b.handle); }

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

// A kill takes the bag, both bags for Cassi and Issac, who die together. Other damage to an
// enemy on its spawn heals at its turn end.
float hit_worth(const World& world, const ChampionBelief& e, float damage, float health, bool on_spawn) {
    if (health > 0 && damage >= health - 0.01f) {
        int gems = e.gems;
        if (e.facts().passive == Passive::linked_pair)
            for (const auto& o : world.enemies)
                if (&o != &e && o.alive && o.facts().passive == Passive::linked_pair) gems += o.gems;
        return health + kill_bonus + gem_value * static_cast<float>(gems);
    }
    if (on_spawn || damage <= 0) return 0;
    return damage + (e.channel == Channel::recall ? recall_cancel_value : 0);
}

// `damaging`: the hit's worth already counts a cancelled recall.
float stun_worth(const ChampionBelief& e, bool damaging) {
    if (e.facts().passive == Passive::stun_immune) return 0;
    float v = stun_value;
    if (e.channel == Channel::tribute) v += tribute_stun_bonus + gem_value * static_cast<float>(e.gems);
    if (e.channel == Channel::recall && !damaging) v += recall_cancel_value;
    return v;
}

struct Target {
    vec2 pos;
    float weight; // chance the enemy is on this tile
    float worth;  // if hit
};

// Groups with a camp tile within `radius`, by the map, seen or not.
std::vector<int> groups_near(const World& world, vec2 p, int radius) {
    const auto& map = world.map();
    std::vector<int> out;
    for (auto tile : (map.camp_tiles & square(p, radius)).positions()) {
        const int g = map.group_at(tile);
        if (g >= 0 && std::find(out.begin(), out.end(), g) == out.end()) out.push_back(g);
    }
    return out;
}

void draw_alive_members(const World& world, int g, bitboard& out) {
    const auto& members = world.map().groups[g].members;
    for (std::size_t i = 0; i < members.size(); ++i)
        if (world.camps[g].health[i] > 0) out.draw_chebyshev(members[i].pos, 1);
}

// Ground centres to skip: their 3x3 would hit a member of a sleeping group, which wakes whole,
// with a monster near us; or a monolith's group.
bitboard wake_risk(const World& world, vec2 here, int reach) {
    const auto& groups = world.map().groups;
    bitboard risk;
    for (int g : groups_near(world, here, reach)) {
        const auto& c = world.camps[g];
        if (c.state != CampState::alive || c.awake == Awake::awake || groups[g].strength <= 0) continue;
        bool near = groups[g].has_monolith;
        for (std::size_t i = 0; i < groups[g].members.size() && !near; ++i)
            near = c.health[i] > 0 && groups[g].members[i].strength > 0
                   && dist(here, groups[g].members[i].pos) <= camp_attack_range;
        if (near) draw_alive_members(world, g, risk);
    }
    return risk;
}

Cast best_ground(int slot, float min_weight_value, const std::vector<Target>& targets, const bitboard& reach,
                 const bitboard& skip) {
    Cast best;
    if (targets.empty()) return best;
    bitboard centres;
    for (const auto& t : targets) centres.draw_chebyshev(t.pos, 1);
    centres &= reach;
    centres &= ~skip;
    for (auto c : centres.positions()) {
        float v = 0;
        for (const auto& t : targets)
            if (dist(c, t.pos) <= 1) v += t.weight * t.worth;
        if (v > best.value && v >= min_weight_value) best.slot = slot, best.value = v, best.tile = c;
    }
    return best;
}

Cast enemy_cast(const World& world, bool keep_walk) {
    auto& me = cambc::self();
    Cast best;
    if (!me.can_cast() || !fuel_ok(fuel_needed)) return best;
    const vec2 here = me.position();
    const auto& f = world.me().facts();
    const auto& enemy_spawn = world.map().enemy_spawn;
    keep_walk = keep_walk && me.can_move();
    std::optional<bitboard> risk;
    for (int s = 0; s < 2; ++s) {
        if (!castable(world, s)) continue;
        const auto& a = f.abilities[s];
        const float threshold = a.excludes_walking && keep_walk ? keep_walk_value : min_value;
        const float raw = raw_damage(s);
        const auto suicidal = [&](const ChampionBelief& e) { return raw > 0 && e.retaliation() >= me.health(); };
        if (a.target == Targeting::unit) {
            for (const auto& e : world.enemies) {
                if (!e.alive || !e.visible || dist(here, e.pos) > a.range() || suicidal(e)) continue;
                const auto c = live(e);
                if (!c.is_visible()) continue;
                float v = hit_worth(world, e, damage_to(s, c, raw), c.health(), enemy_spawn.is_set(e.pos));
                if (a.stuns && !c.buffs().has_stun()) v += stun_worth(e, raw > 0);
                if (v >= threshold && v > best.value) best = Cast{s, v, c, std::nullopt, {}};
            }
        } else if (a.target == Targeting::ground) {
            std::vector<Target> targets;
            bitboard ren; // the area hits unseen enemies too: keep it off a Ren whose retaliation kills us
            for (const auto& e : world.enemies) {
                if (!e.alive) continue;
                const float stun = a.stuns ? stun_worth(e, raw > 0) : 0;
                if (e.visible) {
                    if (dist(here, e.pos) > a.reach()) continue;
                    if (suicidal(e)) {
                        ren.draw_chebyshev(e.pos, 1);
                        continue;
                    }
                    const auto c = live(e);
                    if (!c.is_visible()) continue;
                    const float stunned = a.stuns && c.buffs().has_stun() ? stun : 0;
                    const float hit = hit_worth(world, e, damage_to(s, c, raw), c.health(), enemy_spawn.is_set(e.pos));
                    targets.push_back({e.pos, 1, hit + stun - stunned});
                } else if (e.tracked && !e.possible.is_empty()) {
                    const auto near = e.possible & square(here, a.reach());
                    if (near.is_empty()) continue;
                    const int n = static_cast<int>(e.possible.count());
                    if (n > max_unseen_tiles) continue;
                    if (suicidal(e)) {
                        for (auto p : near.positions()) ren.draw_chebyshev(p, 1);
                        continue;
                    }
                    const float health = e.health > 0 ? e.health : e.max_health;
                    const float hit = std::min(raw, health);
                    for (auto p : near.positions())
                        targets.push_back({p, 1.0f / static_cast<float>(n),
                                           hit_worth(world, e, hit, health, enemy_spawn.is_set(p)) + stun});
                }
            }
            if (targets.empty()) continue;
            if (!risk) risk = wake_risk(world, here, a.reach());
            best.offer(best_ground(s, threshold, targets, square(here, a.range()), *risk | ren));
        }
    }
    return best;
}

Cast camp_cast(const World& world, int group) {
    auto& me = cambc::self();
    if (!me.can_cast() || !fuel_ok(fuel_needed)) return {};
    const vec2 here = me.position();
    const auto& map = world.map();
    const auto& f = world.me().facts();
    if (group < 0) {
        for (auto p : (cambc::vision::camp_tiles() & square(here, f.attack_range())).positions()) {
            const int g = map.group_at(p);
            if (g >= 0 && !map.groups[g].has_monolith) {
                group = g;
                break;
            }
        }
        if (group < 0) return {};
    }
    const auto& g = map.groups[group];
    if (g.has_monolith || world.camps[group].state != CampState::alive) return {};
    for (const auto& e : world.enemies)
        if (e.alive && e.visible && dist(here, e.pos) <= hold_range) return {};

    struct Member {
        cambc::camp camp;
        vec2 pos;
        float health, stun;
    };
    std::vector<Member> members;
    for (int i = 0; i < static_cast<int>(g.members.size()); ++i) {
        if (world.camps[group].health[i] <= 0 || !cambc::vision::has_camp(g.members[i].pos)) continue;
        auto c = g.camp(i);
        if (!c.is_visible()) continue;
        const float health = c.health();
        if (health <= 0) continue;
        // A stunned monster skips its next attack, which goes to the nearest champion: likely us.
        const float stun = dist(here, g.members[i].pos) <= camp_attack_range && !c.buffs().has_stun() ? g.members[i].strength : 0;
        members.push_back({c, g.members[i].pos, health, stun});
    }
    if (members.empty()) return {};

    Cast best;
    for (int s = 0; s < 2; ++s) {
        if (!castable(world, s)) continue;
        const auto& a = f.abilities[s];
        const float raw = raw_damage(s);
        if (a.target == Targeting::unit) {
            for (const auto& m : members) {
                if (dist(here, m.pos) > a.range()) continue;
                const float v = std::min(raw, m.health) + (a.stuns ? m.stun : 0);
                if (v >= min_camp_value && v > best.value) best = Cast{s, v, std::nullopt, m.camp, {}};
            }
        } else if (a.target == Targeting::ground) {
            std::vector<Target> targets;
            for (const auto& m : members) targets.push_back({m.pos, 1, std::min(raw, m.health) + (a.stuns ? m.stun : 0)});
            bitboard skip;
            for (int other : groups_near(world, here, a.reach()))
                if (other != group && world.camps[other].state == CampState::alive) draw_alive_members(world, other, skip);
            best.offer(best_ground(s, min_camp_value, targets, square(here, a.range()), skip));
        }
    }
    return best;
}

} // namespace

bool cast_at_enemies(const World& world, bool keep_walk) {
    try {
        return enemy_cast(world, keep_walk).execute();
    } catch (const cambc::error&) {
        return false;
    }
}

bool cast_at_camp(const World& world, int group) {
    try {
        return camp_cast(world, group).execute();
    } catch (const cambc::error&) {
        return false;
    }
}

} // namespace aph
