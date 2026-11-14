// Function bodies; src/unity.cpp includes this after every header.

namespace aph {
namespace {
teacher_priority::Unit priority_self(const World& world)
{
    teacher_priority::Unit self;
    self.type = static_cast<int>(world.me().type);
    self.alive = world.me().alive && is_alive(world.me().handle);
    if (!self.alive) return self;
    const auto& info = my_record();
    self.x = info.x;
    self.y = info.y;
    self.health = info.health;
    self.max_health = info.max_health;
    self.strength = info.strength;
    self.focus = info.focus;
    self.shield = shield_value(world.me().handle);
    for (std::uint32_t slot = 0; slot < 2; ++slot) {
        static std::int32_t cooldown;
        ok(cambc::detail::sdk_champion_cooldown(my_handle(), slot, &cooldown));
        self.cooldowns[slot] = cooldown;
    }
    return self;
}

void Wish::offer(int b, float v)
{
        if (b > band || (b == band && v > value)) band = b, value = v;
    }

int Wish::priority() const
{ return band * band_width + std::clamp(static_cast<int>(value), 0, band_width - 1); }

bool dodge_camp_hits(const World& world, Safety& safety)
{
    const vec2 here = my_position();
    if (safety.camp_damage(here, true, true) <= 0) return false;
    const int next = world.round + 1, ours = world.slot(world.me(), next);
    std::array<bool, 16> takes{}; // by ally index
    bool any = false;
    for (const auto& m : safety.awake_members()) {
        // m.reach already counts nearer champions and ties to those acting first: within it, we are its target.
        const int d = dist(here, m.pos);
        if (d > m.reach || m.stunned) continue;
        // Acting last, the tie goes to the first of the allies as near.
        const ChampionBelief* to = nullptr;
        for (const auto& a : world.allies)
            if (!a.is_self && a.alive && a.visible && a.index < static_cast<int>(takes.size()) && dist(a.pos, m.pos) == d
                && world.slot(a, next) > ours && (!to || world.slot(a, next) < world.slot(*to, next)))
                to = &a;
        if (to) takes[static_cast<std::size_t>(to->index)] = true, any = true;
    }
    if (!any) return false;
    const float share = my_health() / my_max_health();
    for (const auto& a : world.allies)
        if (a.index < static_cast<int>(takes.size()) && takes[static_cast<std::size_t>(a.index)] && !(a.health / a.max_health > share))
            return false;
    return true;
}

std::int32_t packed_priority(int raw, int index, std::uint32_t payload)
{
    if (raw == 0) return 0;
    const int rank = (rank_code(raw) - rank_code(0)) * 8 + (7 - index);
    return rank * (1 << priority_payload_bits) + static_cast<std::int32_t>(payload);
}

const std::vector<Enemy>& live_enemies(const World& world)
{
    static std::vector<Enemy> out; // kept across turns: growing it reallocates
    out.clear();
    if (!world.enemy_seen()) return out;
    static cambc::detail::champion_info info;
    for (const auto& e : world.enemies) {
        if (!e.alive || !e.visible) continue;
        // A dead champion reads as off the map.
        if (cambc::detail::sdk_champion(static_cast<std::uint32_t>(e.handle), &info) != 0 || info.x < 0 || info.y < 0) continue;
        out.push_back({&e, info.health + (e.shield > 0 ? shield_value(e.handle) : 0.0f)});
    }
    return out;
}

const teacher_priority::Enemies& live_start_enemies(const World& world)
{
    static teacher_priority::Enemies out;
    const auto& start = world.priority_start_enemies;
    out.count = 0;
    for (int i = 0; i < start.count; ++i) {
        static std::int32_t alive;
        const auto h = static_cast<std::uint32_t>(world.priority_start_handles[static_cast<std::size_t>(i)]);
        if (cambc::detail::sdk_champion_is_alive(h, &alive) == 0 && alive == 0) continue;
        out.units[static_cast<std::size_t>(out.count++)] = start.units[static_cast<std::size_t>(i)];
    }
    return out;
}

ChampionBelief& live_self(const World& world, cambc::champion_state& state)
{
    static ChampionBelief b;
    const auto& now = world.me();
    b.handle = now.handle;
    b.type = now.type;
    b.side = now.side;
    b.index = now.index;
    b.is_self = true;
    b.visible = now.visible;
    const auto& info = my_record();
    state = cambc::champion_state::from_bits_retain(info.state);
    // Ren's reflected damage can kill us in our own turn: dead, we read as off the map.
    b.alive = now.alive && info.x >= 0;
    b.max_health = info.max_health;
    b.pos = {info.x, info.y};
    b.health = info.health;
    b.strength = info.strength;
    b.focus = info.focus;
    // Absorbed before our health by every blow before our next turn: it expires only at its start.
    b.shield = now.shield_slot >= 0 ? shield_value(now.handle) : 0.0f;
    return b;
}

void read_strike(const World& world, ChampionBelief& b)
{
    b.gems = static_cast<int>(my_gems());
    b.scale = damage_scale(b.facts().passive, b.health, b.max_health);
    for (std::uint32_t s = 0; s < 2; ++s) {
        static std::int32_t cooldown;
        ok(cambc::detail::sdk_champion_cooldown(my_handle(), s, &cooldown));
        b.ready_round[s] = world.round + std::max(0, static_cast<int>(cooldown));
    }
}

bool we_start(const World& world, int round)
{ return world.map().team_a == (round % 2 == 1); }

bool can_act_before(const World& world, const ChampionBelief& e)
{
    if (we_start(world, world.round + 1)) return true;
    // Read this round after its turn: one first seen after our move keeps an older read.
    const auto settled = [&](const ChampionBelief& c) {
        return !world.enemy_priorities_change || (c.visible && c.acted && c.priority_round == world.round);
    };
    if (!settled(e)) return false;
    for (const auto& o : world.enemies)
        if (&o != &e && settled(o)
            && (o.next_priority > e.next_priority || (o.next_priority == e.next_priority && o.handle < e.handle)))
            return true;
    return false;
}

Strikes::Strikes()
{}

const Strike& next_strike(const World& world, const ChampionBelief& c, Strikes& cache)
{
    auto& s = cache.by_index[static_cast<std::size_t>(c.index)];
    if (!(cache.known >> c.index & 1)) cache.known |= 1u << c.index, s = strike(c, world.round + 1);
    return s;
}

float side_damage(const World& world, const ChampionBelief& self, const Strike& ours, vec2 p, Strikes& allies)
{
    float total = ours.at(dist(self.pos, p));
    for (const auto& a : world.allies)
        if (!a.is_self && a.alive && a.visible) total += next_strike(world, a, allies).at(dist(a.pos, p));
    return total;
}

void offer_kills(const World& world, const ChampionBelief& self, const Strike& ours, const std::vector<Enemy>& enemies,
                 Wish& wish)
{
    const auto& enemy_spawn = world.map().enemy_spawn;
    Strikes allies;
    for (const auto& [e, health] : enemies) {
        const int d = dist(self.pos, e->pos);
        if (!ours.hits(d) || test(enemy_spawn, e->pos) || !can_act_before(world, *e)) continue;
        if (side_damage(world, self, ours, e->pos, allies) * e->taken >= health) {
            const float value = params::life_value + params::gem_value * static_cast<float>(pair_gems(world, *e));
            wish.offer(kill, e->acted ? value : unacted_share * value);
        }
        // A channel completes at its owner's turn start: here, its next.
        if (e->channel_end_round != world.round + 1) continue;
        if (e->channel == Channel::tribute && ours.stuns[d] && e->facts().passive != Passive::stun_immune)
            wish.offer(kill, params::tribute_value + params::gem_value * static_cast<float>(e->gems));
        if (e->channel == Channel::recall && (ours.at(d) > 0 || ours.stuns[d])) wish.offer(kill, params::recall_value);
        if (e->channel == Channel::teleport && ours.stuns[d] && e->facts().passive != Passive::stun_immune)
            wish.offer(kill, params::recall_value);
    }
}

bool channel_ending(cambc::champion_state state)
{
    using cambc::champion_state;
    return (state.contains(champion_state::recalling) || state.contains(champion_state::submitting_gems)
            || state.contains(champion_state::teleporting))
           && my_channel_time() == 1;
}

void offer_channel(const ChampionBelief& self, cambc::champion_state state, Safety& safety, Wish& wish)
{
    using cambc::champion_state;
    const bool recall = state.contains(champion_state::recalling), tribute = state.contains(champion_state::submitting_gems);
    if (!recall && self.facts().passive == Passive::stun_immune) return;
    std::array<Safety::ThreatAt, 16> threats;
    const int n = safety.threats_at(self.pos, threats);
    for (int i = 0; i < n; ++i) {
        const auto& b = threats[i].blow;
        if (!b.hits || !(recall || b.stuns)) continue;
        const float gems = params::gem_value * static_cast<float>(my_gems());
        wish.offer(protect, (tribute ? params::tribute_value : params::recall_value) + gems);
        return;
    }
}

bool may_escape(const World& world, const ChampionBelief& self, Safety& safety, bool seen)
{
    // With none in sight the ceiling places nothing, and its unseen strikes cost less.
    if (!seen) return safety.damage_ceiling(self.pos) >= self.health + self.shield;
    float damage = safety.camp_damage(self.pos, true, true);
    bool hit = false;
    for (const auto& e : world.enemies) {
        if (!e.alive || !(e.visible || e.tracked_recently(world.round))) continue;
        const auto& s = safety.strike_of(e);
        const int d = e.visible ? dist(self.pos, e.pos) : 0;
        if (!s.hits(d)) continue;
        hit = true;
        damage += s.damage[static_cast<std::size_t>(d)] * (e.visible && !e.acted && !turn_lost(e) && turns_before_ours(world, e) < 2 ? 2.0f : 1.0f);
    }
    return hit && damage >= self.health + self.shield;
}

void offer_escape(const World& world, const ChampionBelief& self, Safety& safety, Wish& wish)
{
    float damage = safety.camp_damage(self.pos, true, true);
    bool enemy = false;
    std::array<Safety::ThreatAt, 16> threats;
    const int n = safety.threats_at(self.pos, threats);
    for (int i = 0; i < n; ++i) {
        const auto& t = threats[i];
        if (!t.blow.hits) continue;
        enemy = true;
        const auto& e = world.enemies[t.enemy];
        // With two turns before ours, the blow already covers both.
        damage += t.blow.damage * (e.visible && !e.acted && !turn_lost(e) && turns_before_ours(world, e) < 2 ? 2.0f : 1.0f);
    }
    if (enemy && damage >= self.health + self.shield) wish.offer(protect, params::life_value + params::gem_value * static_cast<float>(my_gems()));
}

void offer_heal(const World& world, const ChampionBelief& self, const std::vector<Enemy>& enemies, Wish& wish)
{
    const int slot = self.facts().slot_of(AbilityKind::heal);
    if (slot < 0 || !self.ability_ready(slot, world.round + 1)) return;
    const auto& a = self.facts().abilities[slot];
    const float heal = a.multiplier * self.focus;
    const auto& spawn = world.map().ally_spawn;
    Strikes strikes;
    for (const auto& ally : world.allies) {
        if (ally.is_self || !ally.alive || !ally.visible || test(spawn, ally.pos) || dist(self.pos, ally.pos) > a.range() + 1)
            continue;
        float damage = 0;
        for (const auto& [e, health] : enemies) damage += next_strike(world, *e, strikes).at(dist(e->pos, ally.pos));
        if (damage >= ally.health && damage < std::min(ally.health + heal, ally.max_health))
            wish.offer(protect, params::life_value + params::gem_value * static_cast<float>(ally.gems));
    }
}

}
}
namespace aph {
void set_turn_order(const World& world, Safety& safety)
{
    world.throw_if_stale();
    Wish wish;
    if (world.me().alive && !fuel_ok(end_reserve)) {
        note_shortcut("turn-order");
        return;
    }
    if (world.me().alive && teacher_priority::role(static_cast<int>(world.me().type)) < 0) {
        cambc::champion_state state{};
        auto& self = live_self(world, state);
        if (self.alive) {
            const auto& enemies = live_enemies(world);
            if (!enemies.empty()) {
                read_strike(world, self);
                offer_kills(world, self, strike(self, world.round + 1), enemies, wish);
                offer_heal(world, self, enemies, wish);
            }
            const bool ending = channel_ending(state);
            const bool seen = enemy_seen(world);
            int visible = 0;
            if (seen)
                for (const auto& e : world.enemies) visible += e.alive && e.visible;
            // Out of sight now also reads as off the map.
            const bool died = static_cast<int>(enemies.size()) < visible;
            bool refreshed = false;
            const auto refresh = [&] {
                using cambc::champion_state;
                // Only our attacks and casts kill.
                if (!refreshed && !(state.contains(champion_state::can_attack) && state.contains(champion_state::can_cast)))
                    refreshed = true, safety.refresh();
            };
            if (died) refresh();
            if (ending) {
                refresh();
                offer_channel(self, state, safety, wish);
            }
            if (!test(world.map().ally_spawn, self.pos) && may_escape(world, self, safety, seen)) {
                refresh();
                offer_escape(world, self, safety, wish);
            }
        }
    }
    int raw;
    if (wish.band != no_band) {
        raw = wish.priority();
    } else {
        const auto self = priority_self(world);
        raw = teacher_priority::priority(self, live_start_enemies(world), self.alive ? static_cast<int>(my_gems()) : 0);
        world.throw_if_stale();
        if (self.alive && dodge_camp_hits(world, safety)) raw = dodge_rank;
    }
    turn_rank = raw;
}

void publish_turn_order(const World& world, std::uint32_t payload)
{
    const std::int32_t priority = packed_priority(turn_rank, world.me().index, payload);
    try {
        static std::int32_t next;
        ok(cambc::detail::sdk_bc_champion_priority(my_handle(), 1, &next));
        if (priority != next) throw_if_stale(), cambc::self().set_priority(priority);
    } catch (const cambc::error&) {
    }
}

}
