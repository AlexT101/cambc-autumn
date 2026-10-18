#include "safety.h"
#include <algorithm>
#include <bit>
#include <cmath>
#include <limits>
#include <memory>
#include <vector>
#include "params.h"
#include "world.h"

namespace aph {

using namespace safety_params;

namespace {

constexpr int ability_cooldown = 8;
constexpr int max_fighters = 6; // one team's bodies

// What casting a slot adds to a turn's basic attack.
struct CastEffect {
    float value = 0; // the choice between ready slots: the most valuable, if any above 0
    float damage = 0, heal = 0;
    bool heals_self = false; // a shield; a heal goes to the weakest hurt ally
    bool stuns = false;
    int hits = 1;
    int duration = 0; // a shield's own turns
};

// Turns are counted per side from 0, so cooldowns and arrivals are turn indices rather than
// counters to tick down.
struct Fighter {
    const ChampionFacts* facts;
    float strength, focus;
    std::array<int, 2> ready_at; // own turn from which the slot can be cast
    int arrives_at = 0;          // own turns spent walking into reach first
    bool idle = false;           // never acts
    float health = 0, max_health = 0;
    float shield = 0;
    int shield_until = -1; // own turn at whose start the shield is lost
    float retaliation = 0; // Ren: damage back per hit taken
    int link = -1; // Cassi or Issac: the other body, which dies with this one
    std::array<CastEffect, 2> cast{};
    std::array<int, 2> preference{0, 1}; // slots by value, ties to slot 0
    int next_cast = 0; // own turn from which a slot worth casting is ready
};

// Fixed storage, as WASM heap work is costly; only the first `count` fighters are written, as the
// engine charges for every byte.
struct Side {
    union {
        std::array<Fighter, max_fighters> fighters;
    };
    int count = 0;
    int alive = 0; // members with health above 0; the fallen stay down
    int turn = 0; // own turns taken
    int self = -1; // our own fighter
    int stunned = 0; // members that lose their next turn
    float camp = 0;  // camp damage taken with each of the other side's turns

    Side() {}

    void add(const Fighter& f) {
        if (count < max_fighters) fighters[count++] = f, alive += f.health > 0;
    }
    void join(const ChampionBelief& c, int turn_round);
    float health() const {
        float total = 0;
        for (int i = 0; i < count; ++i) total += std::max(0.0f, fighters[i].health);
        return total;
    }
    // The living member with the least health and shield, or -1.
    int weakest() const {
        int best = -1;
        for (int i = 0; i < count; ++i)
            if (fighters[i].health > 0
                && (best < 0 || fighters[i].health + fighters[i].shield < fighters[best].health + fighters[best].shield))
                best = i;
        return best;
    }
    // A heal's target: the living member below max health with the least, other than `caster`.
    int weakest_hurt(int caster) const {
        int best = -1;
        for (int i = 0; i < count; ++i)
            if (i != caster && fighters[i].health > 0 && fighters[i].health < fighters[i].max_health
                && (best < 0 || fighters[i].health < fighters[best].health))
                best = i;
        return best;
    }
    // Focused on the weakest, shields first, the excess spilling over to the next. `first`:
    // weakest(), when the caller has it.
    void hurt(float damage, int first = -2) {
        for (int i = damage <= 0 ? -1 : first >= -1 ? first : weakest(); i >= 0; i = damage > 0 ? weakest() : -1) {
            auto& f = fighters[i];
            const float absorbed = std::min(damage, f.shield);
            f.shield -= absorbed;
            damage -= absorbed;
            const float taken = std::min(damage, f.health);
            f.health -= taken;
            damage -= taken;
            if (f.health > 0) continue;
            --alive;
            if (f.link >= 0) {
                alive -= fighters[f.link].health > 0;
                fighters[f.link].health = 0;
            }
        }
    }
};

Fighter fighter(const ChampionBelief& c, int turn_round) {
    Fighter f{&c.facts(), c.strength, c.focus, {}};
    for (int s = 0; s < 2; ++s)
        f.ready_at[s] = c.cooldowns_uncertain() ? 0 : std::max(0, c.ready_round[s] - turn_round);
    return f;
}

void Side::join(const ChampionBelief& c, int turn_round) {
    auto f = fighter(c, turn_round);
    f.health = c.health;
    f.max_health = c.max_health;
    f.retaliation = c.retaliation();
    if (f.facts->passive == Passive::linked_pair)
        for (int i = 0; i < count; ++i)
            if (fighters[i].facts->passive == Passive::linked_pair) f.link = i, fighters[i].link = count;
    add(f);
}

int next_cast(const Fighter& f) {
    int turn = std::numeric_limits<int>::max();
    for (int s = 0; s < 2; ++s)
        if (f.cast[s].value > 0) turn = std::min(turn, f.ready_at[s]);
    return turn;
}

// Each cast's value and effect is fixed for a simulation: work it out once.
void prepare(Side& side) {
    for (int i = 0; i < side.count; ++i) {
        auto& f = side.fighters[i];
        for (int s = 0; s < 2; ++s) {
            const auto& a = f.facts->abilities[s];
            auto& c = f.cast[s];
            c = {};
            c.value = a.stuns ? f.strength : 0;
            switch (a.kind) {
            case AbilityKind::attack_reset: c.value += f.strength; break;
            case AbilityKind::damage:
            case AbilityKind::shield: c.value += a.multiplier * f.focus; break;
            case AbilityKind::heal: c.value += side.count > 1 ? a.multiplier * f.focus : 0; break;
            default: break;
            }
            c.stuns = a.stuns;
            if (a.kind == AbilityKind::shield || a.kind == AbilityKind::heal) c.heal = a.multiplier * f.focus;
            c.heals_self = a.kind == AbilityKind::shield;
            if (a.kind == AbilityKind::attack_reset) c.damage = f.strength;
            if (a.kind == AbilityKind::damage) c.damage = a.multiplier * f.focus;
            c.hits = a.kind == AbilityKind::attack_reset || a.kind == AbilityKind::damage ? 2 : 1;
            c.duration = a.duration;
        }
        f.preference = f.cast[1].value > f.cast[0].value ? std::array<int, 2>{1, 0} : std::array<int, 2>{0, 1};
        f.next_cast = next_cast(f);
    }
}

// A fighter's basic attack and its most valuable ready cast (one a turn); returns hits landed.
int attack(Fighter& f, int turn, Side& self, Side& other, float& damage) {
    damage += f.strength;
    if (turn < f.next_cast) return 1;
    for (const int s : f.preference) {
        const auto& c = f.cast[s];
        if (f.ready_at[s] > turn || c.value <= 0) continue;
        const bool heals_ally = c.heal != 0 && !c.heals_self;
        const int target = heals_ally ? self.weakest_hurt(static_cast<int>(&f - self.fighters.data())) : -1;
        if (heals_ally && target < 0) continue;
        f.ready_at[s] = turn + ability_cooldown;
        f.next_cast = next_cast(f);
        if (c.stuns) ++other.stunned;
        if (c.heals_self) f.shield = c.heal, f.shield_until = turn + c.duration;
        if (heals_ally) {
            auto& t = self.fighters[target];
            t.health = std::min(t.max_health, t.health + c.heal);
        }
        if (c.damage != 0) damage += c.damage;
        return c.hits;
    }
    return 1;
}

// One side's turn: stunned members (the strongest first) skip it.
float act(Side& self, Side& other) {
    unsigned skip = 0; // bit i: fighters[i]
    for (int k = 0; k < self.stunned; ++k) {
        int best = -1;
        for (int i = 0; i < self.count; ++i)
            if (!(skip >> i & 1) && self.fighters[i].health > 0 && self.fighters[i].facts->passive != Passive::stun_immune
                && (best < 0 || self.fighters[i].strength > self.fighters[best].strength))
                best = i;
        if (best < 0) break;
        skip |= 1u << best;
    }
    self.stunned = 0;
    float damage = 0;
    int hits = 0;
    const int turn = self.turn++;
    for (int i = 0; i < self.count; ++i) {
        auto& f = self.fighters[i];
        if (f.shield_until >= 0 && f.shield_until <= turn) f.shield = 0, f.shield_until = -1;
        if (f.health > 0 && f.arrives_at <= turn && !f.idle && !(skip >> i & 1)) hits += attack(f, turn, self, other, damage);
    }
    const int target = other.weakest();
    const float back = target >= 0 ? other.fighters[target].retaliation : 0.0f;
    other.hurt(damage, target);
    if (back > 0) self.hurt(static_cast<float>(hits) * back);
    return damage;
}

// Turns each side needs to empty the other's pool, within `horizon` turns each, playing the fight
// out on the sides given. `self_falls`: whether our own fighter dies before their side does.
// `dealt`, for debug_fights: their first turn's damage, ours, then their first five turns', ours.
// {-1, -1} if the fuel left fell below `fuel_floor` first.
std::pair<int, int> simulate(Side& us, Side& them, bool they_first, bool* self_falls = nullptr, int horizon = 24,
                             std::array<float, 4>* dealt = nullptr, std::uint64_t fuel_floor = 0) {
    prepare(us);
    prepare(them);
    int ours = 0, theirs = 0;
    for (int t = 0; t < 2 * horizon; ++t) {
        if (fuel_floor && t % 8 == 7 && fuel() < fuel_floor) return {-1, -1};
        const bool their_turn = (t % 2 == 0) == they_first;
        if (their_turn) {
            const float d = act(them, us);
            if (dealt && theirs < 5) (*dealt)[2] += d, (*dealt)[0] += theirs == 0 ? d : 0;
            if (us.camp > 0) us.hurt(us.camp);
            ++theirs;
            if (self_falls && us.self >= 0 && us.fighters[us.self].health <= 0) *self_falls = true;
            if (us.alive == 0) return {0, theirs};
        } else {
            const float d = act(us, them);
            if (dealt && ours < 5) (*dealt)[3] += d, (*dealt)[1] += ours == 0 ? d : 0;
            ++ours;
            if (them.count > 0 && them.alive == 0) return {ours, 0};
        }
    }
    return {0, 0};
}

// Only the order where they strike first: `lost` is all callers need.
// Plays the fight out on the sides given, which callers discard: copying them is costly.
Trade trade(Side& us, Side& them, std::uint64_t fuel_floor = 0, bool they_first = true) {
    Trade t;
    t.allies = us.count;
    t.enemies = them.count;
    t.our_health = us.health();
    t.their_health = them.health();
    if (them.count == 0) return t;
    const auto [we_kill, they_kill] = simulate(us, them, they_first, &t.self_falls, 24, debug_fights ? &t.dealt : nullptr, fuel_floor);
    if (we_kill < 0) {
        t.cut = t.lost = t.self_falls = true;
        return t;
    }
    t.turns_to_kill_them = we_kill;
    t.turns_to_kill_us = they_kill;
    t.lost = they_kill > 0;
    return t;
}

} // namespace

int next_turn_round(const World& world, const ChampionBelief& c) {
    // Read for those in sight; ranks are a guess when priorities change unseen.
    if (c.visible && !c.is_self) return c.acted ? world.round + 1 : world.round;
    return world.slot(c, world.round) > world.slot(world.me(), world.round) ? world.round : world.round + 1;
}

namespace {

// Slot bit i: ability i counts.
Strike compute_strike(const ChampionFacts& f, float s, float focus, unsigned slots) {
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
        if (!(slots >> slot & 1)) continue;
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
        case AbilityKind::stun: add(a.reach() + (a.excludes_walking ? 0 : 1), 0, true); break;
        default: break;
        }
    }
    return out;
}

} // namespace

// Called many times a turn for the same few champions: the last result per champion is kept,
// keyed by everything it depends on.
Strike strike(const ChampionBelief& c, int turn_round) {
    struct Memo {
        cambc::champion_type type;
        std::uint32_t strength, focus;
        unsigned slots = 4; // never a key
        Strike value;
    };
    static std::array<Memo, 16> memo;
    const bool uncertain = c.cooldowns_uncertain();
    const unsigned slots =
        (uncertain || c.ability_ready(0, turn_round) ? 1u : 0u) | (uncertain || c.ability_ready(1, turn_round) ? 2u : 0u);
    const auto s = std::bit_cast<std::uint32_t>(c.strength), focus = std::bit_cast<std::uint32_t>(c.focus);
    auto& m = memo[(c.side == team::enemy ? 8u : 0u) + (static_cast<unsigned>(c.index) & 7u)];
    if (m.slots != slots || m.type != c.type || m.strength != s || m.focus != focus)
        m = {c.type, s, focus, slots, compute_strike(c.facts(), c.strength, c.focus, slots)};
    return m.value;
}

int turns_before_ours(const World& world, const ChampionBelief& c) {
    const auto& me = world.me();
    const bool now = c.visible ? !c.acted : world.slot(c, world.round) > world.slot(me, world.round);
    return (now ? 1 : 0) + (world.slot(c, world.round + 1) < world.slot(me, world.round + 1) ? 1 : 0);
}

Strike threat_strike(const World& world, const ChampionBelief& c) {
    const auto s = strike(c, next_turn_round(world, c));
    if (s.reach < 0 || turns_before_ours(world, c) < 2) return s;
    const auto& f = c.facts();
    const int basic_reach = f.attack_range() + (f.ranged ? 0 : 1);
    Strike out;
    for (int d = 0; d <= Strike::max_reach; ++d) {
        const float walked = s.at(std::max(0, d - 1));
        const float twice = s.hits(d) ? s.at(d) + (d <= basic_reach ? c.strength : 0.0f) : 0.0f;
        out.damage[d] = std::max(walked, twice);
        out.stuns[d] = (d <= s.reach + 1 && s.stuns[std::min(std::max(0, d - 1), Strike::max_reach)]) || (s.hits(d) && s.stuns[d]);
    }
    out.reach = std::min(Strike::max_reach, s.reach + 1);
    return out;
}

// An unseen enemy's best chance to be in reach of a tile, or 0 if too slight to count.
float unseen_weight(int reach, int tiles) {
    const float weight = std::min(1.0f, static_cast<float>((2 * reach + 1) * (2 * reach + 1)) / static_cast<float>(tiles));
    return tiles == 0 || weight < credible_weight ? 0.0f : weight;
}

// Next to a compact possible set of side ~sqrt(tiles), the chance of being in reach falls by about
// 1 / sqrt(tiles) per step out; keep the tiles still near the cutoff.
int unseen_radius(int reach, int tiles) {
    return std::clamp(static_cast<int>(static_cast<float>(reach) + 1.5f - credible_weight * std::sqrt(static_cast<float>(tiles))), 0, reach);
}

int Threat::distance(vec2 p) const {
    if (visible) return dist(p, pos);
    return steps ? steps->get(p) : unreachable;
}

namespace {

std::vector<Threat>& threat_pool() {
    static std::vector<Threat> pool;
    return pool;
}

} // namespace

std::vector<Safety::CampHit>& Safety::member_pool() {
    static std::vector<CampHit> pool;
    return pool;
}

Safety::Safety(const World& world) : world_{world}, threats_{threat_pool()}, members_{member_pool()} {}

const std::vector<Safety::CampHit>& Safety::awake_members() {
    if (!members_known_) {
        members_known_ = true;
        members_.clear();
        // Each monster attacks the nearest champion within range, ties to the one acting first in
        // the round of the next camp phase.
        struct Other {
            vec2 pos;
            bool first;
        };
        union Others { // the first n only: the engine charges for every byte written
            std::array<Other, 2 * max_fighters> at;
            Others() {}
        } others;
        int n = -1;
        const int next = world_.round + 1, self_slot = world_.slot(world_.me(), next);
        static bitboard seen{cambc::uninitialized}, camps{cambc::uninitialized};
        bool reread = false;
        const auto& groups = world_.map().groups;
        for (std::size_t g = 0; g < groups.size(); ++g) {
            const auto& c = world_.camps[g];
            if (c.state != CampState::alive || c.awake == Awake::asleep) continue;
            if (n < 0) {
                n = 0;
                for (const auto* side : {&world_.allies, &world_.enemies})
                    for (const auto& o : *side)
                        if (n < static_cast<int>(others.at.size()) && o.alive && o.visible && !o.is_self && !gone(o))
                            others.at[n++] = {o.pos, world_.slot(o, next) < self_slot};
                if (refresh_) {
                    reread = true;
                    cambc::vision::visible_tiles_into(seen);
                    cambc::vision::camp_tiles_into(camps);
                }
            }
            const float w = c.awake == Awake::awake ? 1.0f : unknown_camp_weight;
            for (std::size_t i = 0; i < groups[g].members.size(); ++i) {
                const auto& m = groups[g].members[i];
                if (c.health[i] <= 0 || m.strength <= 0 || (reread && seen.is_set(m.pos) && !camps.is_set(m.pos))) continue;
                int reach = camp_attack_range;
                for (int k = 0; k < n; ++k)
                    reach = std::min(reach, dist(others.at[k].pos, m.pos) - (others.at[k].first ? 1 : 0));
                if (reach >= 0) members_.push_back({m.pos, m.strength, w, reach});
            }
        }
    }
    return members_;
}

bool Safety::gone(const ChampionBelief& c) {
    if (!refresh_ || c.side != team::enemy || !c.visible || c.index >= static_cast<int>(gone_.size())) return false;
    auto& known = gone_[static_cast<std::size_t>(c.index)];
    if (known == 0) {
        std::int32_t alive{};
        cambc::detail::check(cambc::detail::sdk_champion_is_alive(static_cast<std::uint32_t>(c.handle), &alive));
        known = alive != 0 ? 1 : 2;
    }
    return known == 2;
}

void Safety::invalidate() {
    built_ = false;
    refresh_ = true;
    threat_count_ = 0;
    members_known_ = false;
    camp_area_.reset();
    enemy_area_.reset();
    fight_count_ = 0;
    gone_.fill(0);
}

void Safety::refresh() {
    refresh_ = true;
    gone_.fill(0);
    if (!built_ && !members_known_) return;
    bool changed = false;
    for (const auto& e : world_.enemies) changed |= e.alive && gone(e);
    if (!changed && members_known_ && !members_.empty()) {
        static bitboard seen{cambc::uninitialized}, camps{cambc::uninitialized};
        cambc::vision::visible_tiles_into(seen);
        cambc::vision::camp_tiles_into(camps);
        for (const auto& m : members_) changed |= seen.is_set(m.pos) && !camps.is_set(m.pos);
    }
    if (changed) invalidate();
}

Safety::Foe& Safety::foe(const ChampionBelief& e) {
    auto& x = foes_[static_cast<std::size_t>(e.index)];
    if (!(known_ >> e.index & 1)) {
        known_ |= static_cast<std::uint16_t>(1u << e.index);
        x.strike = threat_strike(world_, e);
        x.tiles = 0;
        x.weight = 0;
        x.asked = {-1, -1};
        if (!e.visible && x.strike.reach >= 0) {
            x.tiles = static_cast<int>(e.possible.count());
            x.weight = unseen_weight(x.strike.reach, x.tiles);
        }
    }
    return x;
}

namespace {

Threat& next_threat(std::vector<Threat>& pool, int& count) {
    if (count == static_cast<int>(pool.size())) pool.emplace_back();
    return pool[static_cast<std::size_t>(count++)];
}

} // namespace

void Safety::build() {
    if (built_) return;
    built_ = true;
    FuelMeter meter{"safety"};
    static const bitboard no_walls;
    // One per enemy, reused between builds: a new field allocates and clears ~13k bytes.
    static std::vector<std::unique_ptr<cambc::distance_field>> fields;
    for (const auto& e : world_.enemies) {
        if (!e.alive || (!e.visible && !e.tracked) || gone(e)) continue;
        const auto& x = foe(e);
        const auto& s = x.strike;
        const int reach = s.reach;
        if (reach < 0) continue;
        if (e.visible) {
            auto& t = next_threat(threats_, threat_count_);
            t.enemy = e.index;
            t.strike = s;
            t.visible = true;
            t.pos = e.pos;
            t.tiles = 1;
            t.weight = 1;
            t.steps = nullptr;
            t.area.clear();
            t.area.draw_chebyshev(e.pos, static_cast<float>(reach));
            continue;
        }
        const int tiles = x.tiles;
        const float weight = x.weight;
        if (weight == 0) continue;
        auto& t = next_threat(threats_, threat_count_);
        t.enemy = e.index;
        t.strike = s;
        t.visible = false;
        t.pos = {-1, -1};
        t.tiles = tiles;
        t.weight = weight;
        const int radius = unseen_radius(reach, tiles);
        if (fields.size() <= static_cast<std::size_t>(e.index)) fields.resize(e.index + 1);
        auto& field = fields[e.index];
        if (!field) field = std::make_unique<cambc::distance_field>();
        t.area.clear();
        field->compute(no_walls, e.possible, t.area, static_cast<std::uint16_t>(radius));
        t.steps = field.get();
    }
}

std::span<const Threat> Safety::threats() {
    build();
    return {threats_.data(), static_cast<std::size_t>(threat_count_)};
}

// f(enemy, strike, d) for each enemy build() makes a threat of, d at most its distance from p:
// exact if visible; if unseen, 0 when a tile it could be on is within its reach of p, else past
// the reach, as its field is wall-free and capped within the reach. Strikes only weaken with
// distance, so this bounds the threats' damage and hits at p without building them.
template <class F> void Safety::each_threat(vec2 p, F&& f) {
    for (const auto& e : world_.enemies) {
        if (!e.alive || (!e.visible && !e.tracked) || gone(e)) continue;
        auto& x = foe(e);
        const auto& s = x.strike;
        if (s.reach < 0) continue;
        if (e.visible) f(e, s, dist(p, e.pos));
        else if (x.weight > 0) {
            if (x.asked != p) x.asked = p, x.near = any_within(e.possible, p, s.reach);
            f(e, s, x.near ? 0 : s.reach + 1);
        }
    }
}

bool Safety::any_threat() {
    if (built_) return threat_count_ > 0;
    bool any = false;
    each_threat({0, 0}, [&](const ChampionBelief&, const Strike&, int) { any = true; });
    return any;
}

float Safety::damage_bound(vec2 p, bool double_unacted) {
    float total = camp_damage(p);
    each_threat(p, [&](const ChampionBelief& e, const Strike& s, int d) {
        total += s.at(d) * (double_unacted && e.visible && !e.acted ? 2.0f : 1.0f);
    });
    return total;
}

bool Safety::may_be_hit(vec2 p) {
    bool hit = false;
    each_threat(p, [&](const ChampionBelief&, const Strike& s, int d) { hit |= s.hits(d); });
    return hit;
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
    const auto near = count_within(possible, p, t.strike.reach);
    return std::min(1.0f, static_cast<float>(near) / static_cast<float>(t.tiles));
}

float Safety::camp_damage(vec2 p, bool worst) {
    float total = 0;
    for (const auto& m : awake_members())
        if (dist(p, m.pos) <= m.reach) total += worst ? m.strength : m.strength * m.weight;
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

// The chance of being hit only grows with each factor, so the answer is settled as soon as it
// reaches the line: often by a camp, before the threats are built.
bool Safety::threatened(vec2 p) {
    float safe = 1;
    for (const auto& m : awake_members())
        if (dist(p, m.pos) <= m.reach && 1 - (safe *= 1 - m.weight) >= recall_risk) return true;
    if (!built_ && !may_be_hit(p)) return false;
    for (const auto& t : threats())
        if (t.strike.hits(t.distance(p)) && 1 - (safe *= 1 - chance_in_reach(t, p) * hit_given_reach) >= recall_risk)
            return true;
    return false;
}

const bitboard& Safety::camp_area() {
    if (!camp_area_) {
        bitboard b;
        for (const auto& m : awake_members())
            if (m.reach > 0) b.draw_chebyshev(m.pos, static_cast<float>(m.reach));
        camp_area_ = std::move(b);
    }
    return *camp_area_;
}

const bitboard& Safety::enemy_area() {
    if (!enemy_area_) {
        bitboard any;
        for (const auto& t : threats())
            if (t.credible()) any |= t.area;
        enemy_area_ = std::move(any);
    }
    return *enemy_area_;
}

bitboard Safety::avoid() { return camp_area() | enemy_area(); }

// Every unseen threat is credible: unseen_weight() drops the rest. Its area is `possible` grown by
// its radius, so it comes within r of p exactly when `possible` comes within radius + r.
bool Safety::avoid_within(vec2 p, int r) {
    for (const auto& m : awake_members())
        if (m.reach > 0 && dist(p, m.pos) <= m.reach + r) return true;
    if (built_) return any_within(enemy_area(), p, r);
    for (const auto& e : world_.enemies) {
        if (!e.alive || (!e.visible && !e.tracked) || gone(e)) continue;
        const auto& x = foe(e);
        const int reach = x.strike.reach;
        if (reach < 0) continue;
        if (e.visible) {
            if (dist(p, e.pos) <= reach + r) return true;
            continue;
        }
        if (x.weight > 0 && any_within(e.possible, p, unseen_radius(reach, x.tiles) + r)) return true;
    }
    return false;
}

std::uint32_t Safety::fight_key(vec2 p, int exclude) {
    std::uint32_t key = 0;
    bool hit = false;
    for (const auto& t : threats()) {
        if (t.enemy == exclude || !t.strike.hits(t.distance(p))) continue;
        hit = true;
        if (t.credible()) key |= 1u << (16 + t.enemy);
    }
    if (!hit) return no_fight;
    for (std::size_t i = 0; i < world_.allies.size(); ++i) {
        const auto& a = world_.allies[i];
        if (a.alive && (a.is_self || (a.visible && dist(p, a.pos) <= fight_ally_radius))) key |= 1u << i;
    }
    return key;
}

const Trade* Safety::memo(std::uint32_t key) const {
    for (int i = 0; i < std::min(fight_count_, max_fights); ++i)
        if (fights_[i].key == key) return &fights_[i].trade;
    return nullptr;
}

const Trade* Safety::known_fight(vec2 p) {
    const auto key = fight_key(p, -1);
    if (key == no_fight) {
        static const Trade none{};
        return &none;
    }
    return memo(key);
}

Trade Safety::fight(vec2 p, int exclude) {
    const auto key = fight_key(p, exclude);
    if (key == no_fight) return {};
    if (const auto* t = memo(key)) return *t;
    Side us, them;
    for (std::size_t i = 0; i < world_.allies.size(); ++i) {
        const auto& a = world_.allies[i];
        if (!(key >> i & 1)) continue;
        if (a.is_self) us.self = us.count;
        us.join(a, a.is_self ? world_.round : next_turn_round(world_, a));
    }
    for (const auto& t : threats()) {
        const auto& e = world_.enemies[t.enemy];
        if (key >> (16 + t.enemy) & 1) them.join(e, next_turn_round(world_, e));
    }
    const auto before = fuel();
    auto& slot = fights_[fight_count_++ % max_fights];
    slot = {key, trade(us, them, end_reserve)};
    if (const auto after = fuel(); after < before) costliest_fight_ = std::max(costliest_fight_, before - after);
    return slot.trade;
}

std::uint64_t Safety::fight_cost_estimate() {
    std::uint64_t champions = 0;
    for (const auto& a : world_.allies) champions += a.alive && (a.is_self || a.visible);
    for (const auto& e : world_.enemies) champions += e.alive && e.visible;
    const auto simulation = std::max({std::uint64_t{10000}, 2000 + 2000 * champions, costliest_fight_ + costliest_fight_ / 4});
    return simulation + build_cost_estimate();
}

std::uint64_t Safety::build_cost_estimate() {
    if (built_) return 0;
    std::uint64_t cost = 2000;
    for (const auto& e : world_.enemies) {
        if (!e.alive || (!e.visible && !e.tracked) || gone(e)) continue;
        if (e.visible) cost += 1000;
        else cost += foe(e).weight > 0 ? 3000 + 25 * search_chunks() : 500;
    }
    return cost;
}

Trade Safety::duel(int enemy) {
    const auto& e = world_.enemies[enemy];
    Side us, them;
    us.join(world_.me(), world_.round);
    them.join(e, next_turn_round(world_, e));
    return trade(us, them);
}

Trade Safety::pursuit(vec2 p, int approach) {
    Side us, them;
    const auto& spawn = world_.map().near_enemy_spawn;
    for (const auto& e : world_.enemies) {
        if (!e.alive || !e.visible || gone(e) || spawn.is_set(e.pos)) continue;
        const auto& s = foe(e).strike;
        if (s.reach < 0) continue;
        const int walk = std::max(0, dist(p, e.pos) - s.reach);
        if (walk > approach) continue;
        const int k = them.count;
        them.join(e, next_turn_round(world_, e));
        if (them.count > k) them.fighters[k].arrives_at = walk;
    }
    if (them.count == 0) return {};
    for (const auto& a : world_.allies) {
        if (!a.alive || !(a.is_self || (a.visible && dist(p, a.pos) <= fight_ally_radius))) continue;
        if (a.is_self) us.self = us.count;
        us.join(a, a.is_self ? world_.round : next_turn_round(world_, a));
    }
    us.camp = camp_damage(p, false);
    return trade(us, them, end_reserve, false);
}

int Safety::turns_to_kill_idle(vec2 p, int horizon) {
    Side us, them;
    us.join(world_.me(), world_.round);
    us.fighters[0].idle = true;
    us.camp = camp_damage(p, false);
    for (const auto& e : world_.enemies) {
        if (!e.alive || !e.visible || gone(e)) continue;
        const auto& s = foe(e).strike;
        if (s.reach < 0) continue;
        const int walk = std::max(0, dist(p, e.pos) - s.reach);
        if (walk >= horizon) continue;
        auto f = fighter(e, next_turn_round(world_, e));
        f.arrives_at = walk;
        f.health = e.health;
        them.add(f);
    }
    if (them.count == 0 && us.camp <= 0) return 0;
    return simulate(us, them, true, nullptr, horizon).second;
}

bool Safety::lethal(vec2 p) {
    const float health = world_.me().health;
    // Most turns no enemy is near enough; skip the threat build then.
    if (!built_ && damage_bound(p) < health) return false;
    return worst_damage(p) >= health;
}

bool Safety::should_retreat() {
    const auto& me = world_.me();
    const vec2 here = cambc::self().position();
    if (world_.map().ally_spawn.is_set(here)) return false;
    return me.health < params::recall_health_fraction * me.max_health || (lethal(here) && fight(here).lost);
}

} // namespace aph
