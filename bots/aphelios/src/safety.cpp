#include "safety.h"
#include <algorithm>
#include <cmath>
#include "params.h"
#include "world.h"

namespace aph {

using namespace safety_params;

namespace {

constexpr int ability_cooldown = 8;

struct Fighter {
    const ChampionFacts* facts;
    float strength, focus;
    std::array<int, 2> ready_in; // own turns until the slot can be cast
    int arrives_in = 0;          // own turns spent walking into reach first
};

struct Side {
    std::vector<Fighter> fighters;
    float health = 0;
    int stunned = 0;       // members that lose their next turn
    float retaliation = 0; // Ren: damage back per hit taken, spread over the side
};

Fighter fighter(const ChampionBelief& c, int turn_round) {
    Fighter f{&c.facts(), c.strength, c.focus, {}};
    for (int s = 0; s < 2; ++s)
        f.ready_in[s] = c.cooldowns_uncertain() ? 0 : std::max(0, c.ready_round[s] - turn_round);
    return f;
}

// A fighter's basic attack and its most valuable ready cast (one a turn); returns hits landed.
int attack(Fighter& f, Side& self, Side& other, float& damage) {
    damage += f.strength;
    int cast = -1;
    float best = 0;
    for (int s = 0; s < 2; ++s) {
        if (f.ready_in[s] > 0) continue;
        const auto& a = f.facts->abilities[s];
        float value = a.stuns ? f.strength : 0;
        switch (a.kind) {
        case AbilityKind::attack_reset: value += f.strength; break;
        case AbilityKind::damage:
        case AbilityKind::shield: value += a.multiplier * f.focus; break;
        case AbilityKind::heal: value += self.fighters.size() > 1 ? a.multiplier * f.focus : 0; break;
        default: break;
        }
        if (value > best) best = value, cast = s;
    }
    if (cast < 0) return 1;
    const auto& a = f.facts->abilities[cast];
    f.ready_in[cast] = ability_cooldown;
    if (a.stuns) ++other.stunned;
    if (a.kind == AbilityKind::shield || a.kind == AbilityKind::heal) self.health += a.multiplier * f.focus;
    if (a.kind == AbilityKind::attack_reset) damage += f.strength;
    if (a.kind == AbilityKind::damage) damage += a.multiplier * f.focus;
    return a.kind == AbilityKind::attack_reset || a.kind == AbilityKind::damage ? 2 : 1;
}

// One side's turn: stunned members (the strongest first) skip it.
void act(Side& self, Side& other) {
    std::array<bool, 8> skip{};
    for (int k = 0; k < self.stunned; ++k) {
        int best = -1;
        for (int i = 0; i < static_cast<int>(self.fighters.size()); ++i)
            if (!skip[i] && self.fighters[i].facts->passive != Passive::stun_immune
                && (best < 0 || self.fighters[i].strength > self.fighters[best].strength))
                best = i;
        if (best >= 0 && best < static_cast<int>(skip.size())) skip[best] = true;
    }
    self.stunned = 0;
    float damage = 0;
    int hits = 0;
    for (std::size_t i = 0; i < self.fighters.size(); ++i) {
        auto& f = self.fighters[i];
        if (f.arrives_in > 0)
            --f.arrives_in;
        else if (i >= skip.size() || !skip[i])
            hits += attack(f, self, other, damage);
        for (auto& r : f.ready_in) r = std::max(0, r - 1);
    }
    other.health -= damage;
    self.health -= static_cast<float>(hits) * other.retaliation;
}

Side side(const std::vector<const ChampionBelief*>& members, const std::vector<int>& turn_rounds) {
    Side s;
    for (std::size_t i = 0; i < members.size(); ++i) {
        s.fighters.push_back(fighter(*members[i], turn_rounds[i]));
        s.health += members[i]->health;
        if (members[i]->facts().passive == Passive::retaliation) s.retaliation += 0.2f * members[i]->focus;
    }
    if (!members.empty()) s.retaliation /= static_cast<float>(members.size());
    return s;
}

// Turns each side needs to empty the other's pool, within `horizon` turns each.
std::pair<int, int> simulate(Side us, Side them, bool they_first) {
    constexpr int horizon = 24;
    int ours = 0, theirs = 0;
    for (int t = 0; t < 2 * horizon; ++t) {
        const bool their_turn = (t % 2 == 0) == they_first;
        if (their_turn) {
            act(them, us);
            ++theirs;
            if (us.health <= 0) return {0, theirs};
        } else {
            act(us, them);
            ++ours;
            if (them.health <= 0) return {ours, 0};
        }
    }
    return {0, 0};
}

Trade trade(const std::vector<const ChampionBelief*>& ours, const std::vector<int>& our_rounds,
            const std::vector<const ChampionBelief*>& theirs, const std::vector<int>& their_rounds) {
    Trade t;
    t.allies = static_cast<int>(ours.size());
    t.enemies = static_cast<int>(theirs.size());
    const auto us = side(ours, our_rounds), them = side(theirs, their_rounds);
    t.our_health = us.health;
    t.their_health = them.health;
    if (theirs.empty()) return t;
    const auto [we_kill, they_kill] = simulate(us, them, true);
    t.turns_to_kill_them = we_kill;
    t.turns_to_kill_us = they_kill;
    t.lost = they_kill > 0;
    t.lost_anyway = simulate(us, them, false).second > 0;
    return t;
}

} // namespace

int next_turn_round(const World& world, const ChampionBelief& c) {
    return world.slot(c, world.round) > world.slot(world.me(), world.round) ? world.round : world.round + 1;
}

Strike strike(const ChampionBelief& c, int turn_round) {
    const auto& f = c.facts();
    const float s = c.strength, focus = c.focus;
    const int range = f.attack_range();
    const int walk = f.ranged ? 0 : 1; // a ranged champion's walk spends its attack
    Strike out;
    const auto add = [&](int reach, float damage, bool stuns) {
        reach = std::min(reach, Strike::max_reach);
        for (int d = 0; d <= reach; ++d) {
            out.damage[d] = std::max(out.damage[d], damage);
            out.stuns[d] = out.stuns[d] || stuns;
        }
        out.reach = std::max(out.reach, reach);
    };
    add(range + walk, s, false);
    for (int slot = 0; slot < 2; ++slot) {
        if (!c.ability_ready(slot, turn_round) && !c.cooldowns_uncertain()) continue;
        const auto& a = f.abilities[slot];
        switch (a.kind) {
        case AbilityKind::attack_reset:
            add(range + walk, 2 * s, a.stuns);
            if (f.ranged) add(range + 1, s, a.stuns); // walk, reset, attack
            break;
        case AbilityKind::dash: add(range + walk + 2, s, false); break;
        case AbilityKind::damage:
            // Excludes walking but not the basic attack.
            add(a.reach(), a.multiplier * focus, a.stuns);
            add(range, a.multiplier * focus + s, a.stuns);
            break;
        case AbilityKind::stun: add(a.reach(), 0, true); break;
        default: break;
        }
    }
    return out;
}

int Threat::distance(vec2 p) const {
    if (visible) return dist(p, pos);
    return steps ? steps->get(p) : unreachable;
}

Safety::Safety(const World& world) : world_{world} {}

const std::vector<Safety::CampHit>& Safety::awake_members() {
    if (!members_) {
        members_.emplace();
        const auto& groups = world_.map().groups;
        for (std::size_t g = 0; g < groups.size(); ++g) {
            const auto& c = world_.camps[g];
            if (c.state != CampState::alive || c.awake == Awake::asleep) continue;
            const float w = c.awake == Awake::awake ? 1.0f : unknown_camp_weight;
            for (std::size_t i = 0; i < groups[g].members.size(); ++i)
                if (c.health[i] > 0 && groups[g].members[i].strength > 0)
                    members_->push_back({groups[g].members[i].pos, groups[g].members[i].strength, w});
        }
    }
    return *members_;
}

void Safety::build() {
    if (built_) return;
    built_ = true;
    FuelMeter meter{"safety"};
    std::optional<bitboard> no_walls;
    threats_.reserve(world_.enemies.size());
    for (const auto& e : world_.enemies) {
        if (!e.alive || (!e.visible && !e.tracked)) continue;
        const auto s = strike(e, next_turn_round(world_, e));
        const int reach = s.reach;
        if (reach < 0) continue;
        if (e.visible) {
            auto& t = threats_.emplace_back();
            t.enemy = e.index;
            t.strike = s;
            t.visible = true;
            t.pos = e.pos;
            t.area = square(e.pos, reach);
            continue;
        }
        const int tiles = static_cast<int>(e.possible.count());
        const float weight = std::min(1.0f, static_cast<float>((2 * reach + 1) * (2 * reach + 1)) / static_cast<float>(tiles));
        if (tiles == 0 || weight < credible_weight) continue;
        auto& t = threats_.emplace_back();
        t.enemy = e.index;
        t.strike = s;
        t.tiles = tiles;
        t.weight = weight;
        // Next to a compact possible set of side ~sqrt(tiles), the chance of being in reach
        // falls by about 1 / sqrt(tiles) per step out; keep the tiles still near the cutoff.
        const int radius = std::clamp(
            static_cast<int>(static_cast<float>(reach) + 1.5f - credible_weight * std::sqrt(static_cast<float>(tiles))), 0, reach);
        if (!no_walls) no_walls.emplace();
        t.steps.emplace();
        t.steps->compute(*no_walls, e.possible, t.area, static_cast<std::uint16_t>(radius));
    }
}

const std::vector<Threat>& Safety::threats() {
    build();
    return threats_;
}

const Threat* Safety::threat(int enemy) {
    for (const auto& t : threats())
        if (t.enemy == enemy) return &t;
    return nullptr;
}

float Safety::chance_in_reach(const Threat& t, vec2 p) {
    if (t.visible) return t.strike.hits(dist(p, t.pos)) ? 1.0f : 0.0f;
    if (!t.area.is_set(p)) return 0.0f;
    const auto& possible = world_.enemies[t.enemy].possible;
    const auto near = (square(p, t.strike.reach) & possible).count();
    return std::min(1.0f, static_cast<float>(near) / static_cast<float>(t.tiles));
}

float Safety::camp_damage(vec2 p, bool worst) {
    float total = 0;
    for (const auto& m : awake_members())
        if (dist(p, m.pos) <= camp_attack_range) total += worst ? m.strength : m.strength * m.weight;
    return total;
}

float Safety::worst_damage(vec2 p) {
    float total = camp_damage(p, true);
    for (const auto& t : threats())
        if (t.credible()) total += t.strike.at(t.distance(p));
    return total;
}

float Safety::expected_damage(vec2 p) {
    float total = camp_damage(p, false);
    for (const auto& t : threats()) {
        const int d = t.distance(p);
        if (t.strike.hits(d)) total += chance_in_reach(t, p) * hit_given_reach * t.strike.at(d);
    }
    return total;
}

float Safety::hit_chance(vec2 p) {
    float safe = 1;
    for (const auto& m : awake_members())
        if (dist(p, m.pos) <= camp_attack_range) safe *= 1 - m.weight;
    for (const auto& t : threats())
        if (t.strike.hits(t.distance(p))) safe *= 1 - chance_in_reach(t, p) * hit_given_reach;
    return 1 - safe;
}

const bitboard& Safety::camp_area() {
    if (!camp_area_) {
        bitboard b;
        for (const auto& m : awake_members()) b.draw_chebyshev(m.pos, camp_attack_range);
        camp_area_ = std::move(b);
    }
    return *camp_area_;
}

const bitboard& Safety::enemy_area() {
    if (!enemy_area_) {
        bitboard any, several;
        for (const auto& t : threats()) {
            if (!t.credible()) continue;
            several |= any & t.area;
            any |= t.area;
        }
        enemy_area_ = std::move(any);
        contested_area_ = std::move(several);
    }
    return *enemy_area_;
}

const bitboard& Safety::contested_area() {
    enemy_area();
    return *contested_area_;
}

bitboard Safety::avoid() {
    auto b = camp_area() | enemy_area();
    b.set(cambc::self().position(), false);
    return b;
}

Trade Safety::fight(vec2 p) {
    if (std::none_of(threats().begin(), threats().end(), [&](const Threat& t) { return t.strike.hits(t.distance(p)); })) return {};
    std::vector<const ChampionBelief*> ours, theirs;
    std::vector<int> our_rounds, their_rounds;
    for (const auto& a : world_.allies)
        if (a.alive && (a.is_self || (a.visible && dist(p, a.pos) <= fight_ally_radius))) {
            ours.push_back(&a);
            our_rounds.push_back(a.is_self ? world_.round : next_turn_round(world_, a));
        }
    for (const auto& t : threats()) {
        if (!t.credible() || !t.strike.hits(t.distance(p))) continue;
        theirs.push_back(&world_.enemies[t.enemy]);
        their_rounds.push_back(next_turn_round(world_, world_.enemies[t.enemy]));
    }
    return trade(ours, our_rounds, theirs, their_rounds);
}

Trade Safety::duel(int enemy) {
    const auto& e = world_.enemies[enemy];
    return trade({&world_.me()}, {world_.round}, {&e}, {next_turn_round(world_, e)});
}

int Safety::turns_to_kill_idle(vec2 p, int horizon) {
    Side us, them;
    us.health = world_.me().health;
    for (const auto& e : world_.enemies) {
        if (!e.alive || !e.visible) continue;
        const auto s = strike(e, next_turn_round(world_, e));
        if (s.reach < 0) continue;
        const int walk = std::max(0, dist(p, e.pos) - s.reach);
        if (walk >= horizon) continue;
        auto f = fighter(e, next_turn_round(world_, e));
        f.arrives_in = walk;
        them.fighters.push_back(f);
    }
    if (them.fighters.empty()) return 0;
    return simulate(us, them, true).second;
}

bool Safety::lethal(vec2 p) {
    const float health = world_.me().health;
    // Most turns every enemy's best strike falls short together; skip the threat build then.
    if (!built_) {
        constexpr float max_area = (2 * Strike::max_reach + 1) * (2 * Strike::max_reach + 1);
        float bound = camp_damage(p);
        for (const auto& e : world_.enemies)
            if (e.alive && (e.visible || (e.tracked && static_cast<float>(e.possible.count()) * credible_weight <= max_area)))
                bound += strike(e, next_turn_round(world_, e)).damage[0];
        if (bound < health) return false;
    }
    return worst_damage(p) >= health;
}

bool Safety::should_retreat() {
    const auto& me = world_.me();
    const vec2 here = cambc::self().position();
    if (world_.map().ally_spawn.is_set(here)) return false;
    return me.health < params::recall_health_fraction * me.max_health || (lethal(here) && fight(here).lost);
}

} // namespace aph
