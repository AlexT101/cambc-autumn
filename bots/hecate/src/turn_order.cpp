#include "turn_order.h"
#include <algorithm>
#include <array>
#include <vector>
#include "params.h"
#include "safety.h"
#include "world.h"

namespace aph {

namespace {

// Allies sort by band, then by value within it: a kill or a cancelled channel outranks saving a
// life, which outranks being near a fight. Each needs us to act before some enemy next round.
enum Band : int { idle, engaged, protect, kill };
constexpr int band_width = 10000;

// An enemy yet to act this round moves before our next turn anyway: acting before its turn next
// round denies it only a second one.
constexpr float unacted_share = 0.5f;
struct Wish {
    int band = idle;
    float value = 0;

    void offer(int b, float v) {
        if (b > band || (b == band && v > value)) band = b, value = v;
    }
    int priority() const { return band * band_width + std::clamp(static_cast<int>(value), 0, band_width - 1); }
};

struct Enemy {
    const ChampionBelief* belief;
    float health;
};

// Visible enemies still alive after our turn, with their health now. One raw read each: every
// SDK accessor reads the whole record again.
const std::vector<Enemy>& live_enemies(const World& world) {
    static std::vector<Enemy> out; // kept across turns: growing it reallocates
    out.clear();
    for (const auto& e : world.enemies) {
        if (!e.alive || !e.visible) continue;
        cambc::detail::champion_info info{};
        // A dead champion reads as off the map.
        if (cambc::detail::sdk_champion(static_cast<std::uint32_t>(e.handle), &info) != 0 || info.x < 0 || info.y < 0) continue;
        out.push_back({&e, info.health});
    }
    return out;
}

// Ourselves as we end the turn: moved, cooldowns restarted by casts. The fields read here only:
// copying a belief copies its bitboards.
const ChampionBelief& live_self(const World& world) {
    static ChampionBelief b;
    const auto& now = world.me();
    b.handle = now.handle;
    b.type = now.type;
    b.side = now.side;
    b.index = now.index;
    b.is_self = true;
    b.alive = now.alive;
    b.visible = now.visible;
    b.max_health = now.max_health;
    const auto& info = my_record();
    b.pos = {info.x, info.y};
    b.health = info.health;
    b.strength = info.strength;
    b.focus = info.focus;
    b.gems = static_cast<int>(my_gems());
    for (std::uint32_t s = 0; s < 2; ++s) {
        std::int32_t cooldown{};
        ok(cambc::detail::sdk_champion_cooldown(my_handle(), s, &cooldown));
        b.ready_round[s] = world.round + std::max(0, static_cast<int>(cooldown));
    }
    return b;
}

bool we_start(const World& world, int round) { return world.map().team_a == (round % 2 == 1); }

// We can act before `e` next round unless its team starts and it is their first champion. Its
// priority for next round is final once it has acted, or if its team never changes priority.
bool can_act_before(const World& world, const ChampionBelief& e) {
    if (we_start(world, world.round + 1) || (world.enemy_priorities_change && !e.acted)) return true;
    for (const auto& o : world.enemies)
        if (&o != &e && (o.next_priority > e.next_priority || (o.next_priority == e.next_priority && o.handle < e.handle)))
            return true;
    return false;
}

// Strikes for next round, by index, each worked out on first use. Slots not used are left
// unwritten: the engine charges for every byte.
struct Strikes {
    unsigned known = 0;
    union {
        std::array<Strike, 8> by_index;
    };
    Strikes() {}
};

const Strike& next_strike(const World& world, const ChampionBelief& c, Strikes& cache) {
    auto& s = cache.by_index[static_cast<std::size_t>(c.index)];
    if (!(cache.known >> c.index & 1)) cache.known |= 1u << c.index, s = strike(c, world.round + 1);
    return s;
}

// Damage our next turn and those of the allies we see could deal to a tile, each walking first.
float side_damage(const World& world, const ChampionBelief& self, const Strike& ours, vec2 p, Strikes& allies) {
    float total = ours.at(dist(self.pos, p));
    for (const auto& a : world.allies)
        if (!a.is_self && a.alive && a.visible) total += next_strike(world, a, allies).at(dist(a.pos, p));
    return total;
}

// Killing or cancelling a channel needs us to act before its owner.
void offer_kills(const World& world, const ChampionBelief& self, const Strike& ours, const std::vector<Enemy>& enemies,
                 Wish& wish) {
    const auto& enemy_spawn = world.map().enemy_spawn;
    Strikes allies;
    for (const auto& [e, health] : enemies) {
        const int d = dist(self.pos, e->pos);
        if (!ours.hits(d) || enemy_spawn.is_set(e->pos) || !can_act_before(world, *e)) continue;
        if (side_damage(world, self, ours, e->pos, allies) >= health) {
            const float value = params::life_value + params::gem_value * static_cast<float>(pair_gems(world, *e));
            wish.offer(kill, e->acted ? value : unacted_share * value);
        }
        // A channel completes at its owner's turn start: here, its next.
        if (e->channel_end_round != world.round + 1) continue;
        if (e->channel == Channel::tribute && ours.stuns[d] && e->facts().passive != Passive::stun_immune)
            wish.offer(kill, params::tribute_value + params::gem_value * static_cast<float>(e->gems));
        if (e->channel == Channel::recall && ours.at(d) > 0) wish.offer(kill, params::recall_value);
    }
}

bool channel_ending() {
    using cambc::champion_state;
    const auto state = my_state();
    return (state.contains(champion_state::recalling) || state.contains(champion_state::submitting_gems)
            || state.contains(champion_state::teleporting))
           && my_channel_time() == 1;
}

// Our channel ends at our next turn's start, unless an enemy acting first cancels it: any damage
// cancels a recall, only a stun a tribute or a teleport.
void offer_channel(const ChampionBelief& self, Safety& safety, Wish& wish) {
    using cambc::champion_state;
    const auto state = my_state();
    const bool recall = state.contains(champion_state::recalling), tribute = state.contains(champion_state::submitting_gems);
    if (!(recall || tribute || state.contains(champion_state::teleporting)) || my_channel_time() != 1) return;
    std::array<Safety::ThreatAt, 16> threats;
    const int n = safety.threats_at(self.pos, threats);
    for (int i = 0; i < n; ++i) {
        const auto& b = threats[i].blow;
        if (!b.hits || !(recall || b.stuns)) continue;
        const float gems = params::gem_value * static_cast<float>(self.gems);
        wish.offer(protect, (tribute ? params::tribute_value : params::recall_value) + gems);
        return;
    }
}

// Enemies yet to act this round strike before our next turn whatever the order; acting first
// next round denies the second strike of those, and the only one of the others.
void offer_escape(const World& world, const ChampionBelief& self, Safety& safety, Wish& wish) {
    if (world.map().ally_spawn.is_set(self.pos) || safety.damage_ceiling(self.pos, true) < self.health
        || safety.damage_bound(self.pos, true) < self.health)
        return;
    float damage = safety.camp_damage(self.pos);
    bool enemy = false;
    std::array<Safety::ThreatAt, 16> threats;
    const int n = safety.threats_at(self.pos, threats);
    for (int i = 0; i < n; ++i) {
        const auto& t = threats[i];
        if (!t.blow.hits) continue;
        enemy = true;
        const auto& e = world.enemies[t.enemy];
        damage += t.blow.damage * (e.visible && !e.acted ? 2.0f : 1.0f);
    }
    if (enemy && damage >= self.health) wish.offer(protect, params::life_value + params::gem_value * static_cast<float>(self.gems));
}

// A heal before the enemies' turns keeps an ally alive whom they would otherwise kill.
void offer_heal(const World& world, const ChampionBelief& self, const std::vector<Enemy>& enemies, Wish& wish) {
    const int slot = self.facts().slot_of(AbilityKind::heal);
    if (slot < 0 || !self.ability_ready(slot, world.round + 1)) return;
    const auto& a = self.facts().abilities[slot];
    const float heal = a.multiplier * self.focus;
    const auto& spawn = world.map().ally_spawn;
    Strikes strikes;
    for (const auto& ally : world.allies) {
        if (ally.is_self || !ally.alive || !ally.visible || spawn.is_set(ally.pos) || dist(self.pos, ally.pos) > a.range() + 1)
            continue;
        float damage = 0;
        for (const auto& [e, health] : enemies) damage += next_strike(world, *e, strikes).at(dist(e->pos, ally.pos));
        if (damage >= ally.health && damage < ally.health + heal)
            wish.offer(protect, params::life_value + params::gem_value * static_cast<float>(ally.gems));
    }
}

// Fights go to the first hit, and a stun before the enemy's turn removes it: the ally nearest a
// visible enemy acts first.
void offer_engaged(const ChampionBelief& self, const std::vector<Enemy>& enemies, Wish& wish) {
    int nearest = vision_radius + 1;
    for (const auto& [e, health] : enemies) nearest = std::min(nearest, dist(self.pos, e->pos));
    if (nearest <= vision_radius) wish.offer(engaged, static_cast<float>(vision_radius + 1 - nearest));
}

} // namespace

void set_turn_order(const World& world, Safety& safety) {
    world.throw_if_stale();
    auto& me = cambc::self();
    Wish wish;
    if (world.me().alive && !fuel_ok(end_reserve)) {
        note_shortcut("turn-order");
        return;
    }
    if (world.me().alive) {
        const auto& self = live_self(world);
        const auto& enemies = live_enemies(world);
        offer_engaged(self, enemies, wish);
        const Strike ours = strike(self, world.round + 1);
        offer_kills(world, self, ours, enemies, wish);
        offer_heal(world, self, enemies, wish);
        // With no enemy in sight our turn only removed camp members, so the threats before a refresh
        // overstate those after: when they cannot kill us and no channel ends, nothing needs it.
        if (channel_ending() || enemy_seen(world)
            || !(world.map().ally_spawn.is_set(self.pos) || safety.damage_ceiling(self.pos, true) < self.health)) {
            safety.refresh();
            offer_channel(self, safety, wish);
            offer_escape(world, self, safety, wish);
        }
    }
    try {
        if (wish.priority() != me.priority()) me.set_priority(wish.priority());
    } catch (const cambc::error&) {
    }
}

} // namespace aph
