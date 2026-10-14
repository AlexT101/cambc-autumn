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
constexpr float min_value = 40;
constexpr float keep_walk_value = 250;
constexpr float min_camp_value = 50;
constexpr int max_unseen_tiles = 9; // unseen enemies spread over more tiles are not aimed at
constexpr int hold_range = 6;       // camp casts wait while a visible enemy is this close
constexpr int camp_attack_range = 3;
constexpr std::uint64_t fuel_needed = 25000;

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

float hit_worth(const ChampionBelief& e, float damage, float health) {
    if (health > 0 && damage >= health - 0.01f) return health + kill_bonus + gem_value * static_cast<float>(e.gems);
    return damage;
}

float stun_worth(const ChampionBelief& e) {
    if (e.facts().passive == Passive::stun_immune) return 0;
    float v = stun_value;
    if (e.channel == Channel::tribute) v += tribute_stun_bonus + gem_value * static_cast<float>(e.gems);
    return v;
}

struct Target {
    vec2 pos;
    float weight; // chance the enemy is on this tile
    float worth;  // if hit
};

// Ground centres to skip: their 3x3 would wake a sleeping group next to us, or a monolith.
bitboard wake_risk(const World& world, vec2 here) {
    const auto& map = world.map();
    bitboard risk;
    for (auto p : (cambc::vision::camp_tiles() & square(here, 5)).positions()) {
        const int g = map.group_at(p);
        if (g < 0 || world.camps[g].awake == Awake::awake) continue;
        if (map.groups[g].has_monolith || dist(here, p) <= camp_attack_range) risk.draw_chebyshev(p, 1);
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
                float v = hit_worth(e, damage_to(s, c, raw), c.health());
                if (a.stuns && !c.buffs().has_stun()) v += stun_worth(e);
                if (v >= threshold && v > best.value) best = Cast{s, v, c, std::nullopt, {}};
            }
        } else if (a.target == Targeting::ground) {
            std::vector<Target> targets;
            for (const auto& e : world.enemies) {
                if (!e.alive || suicidal(e)) continue;
                const float stun = a.stuns ? stun_worth(e) : 0;
                if (e.visible) {
                    if (dist(here, e.pos) > a.reach()) continue;
                    const auto c = live(e);
                    if (!c.is_visible()) continue;
                    const float stunned = a.stuns && c.buffs().has_stun() ? stun : 0;
                    targets.push_back({e.pos, 1, hit_worth(e, damage_to(s, c, raw), c.health()) + stun - stunned});
                } else if (e.tracked && !e.possible.is_empty()) {
                    const auto near = e.possible & square(here, a.reach());
                    if (near.is_empty()) continue;
                    const int n = static_cast<int>(e.possible.count());
                    if (n > max_unseen_tiles) continue;
                    const float health = e.health > 0 ? e.health : e.max_health;
                    const float worth = hit_worth(e, std::min(raw, health), health) + stun;
                    for (auto p : near.positions()) targets.push_back({p, 1.0f / static_cast<float>(n), worth});
                }
            }
            if (targets.empty()) continue;
            if (!risk) risk = wake_risk(world, here);
            best.offer(best_ground(s, threshold, targets, square(here, a.range()), *risk));
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
            for (auto p : (cambc::vision::camp_tiles() & ~g.tiles() & square(here, a.reach() + 1)).positions())
                skip.draw_chebyshev(p, 1);
            best.offer(best_ground(s, min_camp_value, targets, square(here, a.range()), skip));
        }
    }
    return best;
}

} // namespace

bool exclusive_cast_ready(const World& world) {
    if (!cambc::self().can_cast()) return false;
    const auto& f = world.me().facts();
    for (int s = 0; s < 2; ++s)
        if (f.abilities[s].excludes_walking && castable(world, s)) return true;
    return false;
}

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
