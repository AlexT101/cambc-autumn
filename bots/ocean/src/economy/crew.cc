// Crews on strong camp groups: who takes the camps' hits, the trips home that health costs, and
// the crew farm expects when it proposes an operation.
#include "../bot_parts.h"

namespace aph {

namespace {

// Camp damage taken per point a camp deals, as far as we can read it (Jungle, Durability).
float crew_taken(const ChampionBelief& a) { return a.is_self ? camp_hit_factor() : a.camp_taken; }

// Camp damage a champion can take before `line`, and per trip home, over crew_trip_risk.
float crew_budget(float health, float max_health, float line) { return std::max(0.0f, health - line * max_health) / params::crew_trip_risk; }
float crew_usable(float max_health, float line) { return max_health * (1.0f - line) / params::crew_trip_risk; }

int extra_trips(float damage, float budget, float usable) {
    if (damage <= budget) return 0;
    if (usable <= 0) return 99;
    return static_cast<int>(std::min(99.0f, std::ceil((damage - budget) / usable)));
}

// Rounds until a champion's basic attack reaches the group's nearest member, as the crow flies.
int crew_arrival(const World& world, const ChampionBelief& a, int g, vec2 p) {
    // steps_to walks every member, and each pricing asks it again for the same tiles: kept per
    // group and body by tile (zero: none kept).
    static std::array<std::array<std::pair<int, int>, 8>, 256> kept;
    const int key = ((p.x + 1) << 8 | (p.y + 1)) + 1;
    if (static_cast<std::size_t>(g) >= kept.size() || static_cast<std::size_t>(a.index) >= kept[0].size())
        return std::max(0, steps_to(world.map().groups[g], p) - a.facts().attack_range());
    auto& k = kept[static_cast<std::size_t>(g)][static_cast<std::size_t>(a.index)];
    if (k.first != key) k = {key, steps_to(world.map().groups[g], p)};
    return std::max(0, k.second - a.facts().attack_range());
}

// The box around all of g's members (steps_to's), read once a group.
std::pair<vec2, vec2> crew_box(const World& world, int g) {
    const auto& G = world.map().groups[g];
    const auto read = [&] {
        vec2 lo = G.members[0].pos, hi = lo;
        for (const auto& m : G.members) lo = {std::min(lo.x, m.pos.x), std::min(lo.y, m.pos.y)}, hi = {std::max(hi.x, m.pos.x), std::max(hi.y, m.pos.y)};
        return std::pair{lo, hi};
    };
    // Plain ints (a vec2 would give the table a run-time initialiser); hi.x + 1 is 0 until read.
    static std::array<std::array<std::int16_t, 4>, 256> boxes;
    if (static_cast<std::size_t>(g) >= boxes.size()) return read();
    auto& box = boxes[static_cast<std::size_t>(g)];
    if (box[2] == 0) {
        const auto [lo, hi] = read();
        box = {static_cast<std::int16_t>(lo.x), static_cast<std::int16_t>(lo.y), static_cast<std::int16_t>(hi.x + 1), static_cast<std::int16_t>(hi.y)};
    }
    return {{box[0], box[1]}, {box[2] - 1, box[3]}};
}

bool crew_in_reach(const World& world, int g, vec2 p, int range) {
    const auto& G = world.map().groups[g];
    const auto& c = world.camps[g];
    for (std::size_t i = 0; i < G.members.size(); ++i)
        if ((c.state == CampState::respawning || c.health[i] > 0) && dist(p, G.members[i].pos) <= std::max(range, G.members[i].reach))
            return true;
    return false;
}

bool crew_member(const World& world, const ChampionBelief& a, int g, std::span<const int> extra) {
    if (a.is_self) return true;
    if (!a.alive) return false;
    // Extras are counted in by the caller's rules (the first turn's unseen allies included).
    if (std::find(extra.begin(), extra.end(), a.index) != extra.end()) return true;
    return a.visible && comms::claim_of(world, a.index) == g;
}

// The tank's score: health above the line per camp damage taken, melee preferred (it stands
// nearest, so the camps' nearest-champion hits find it anyway). A fixed line, so that every
// member names the same tank whatever enemies it sees.
float tank_score(const ChampionBelief& a) {
    const float health = a.is_self ? my_health() : a.health, max_health = a.is_self ? my_max_health() : a.max_health;
    const float score = (health - params::crew_tank_line * max_health) / std::max(0.01f, crew_taken(a));
    return a.facts().walk_and_attack_independent() ? score * 1.5f : score;
}

const ChampionBelief* crew_tank(const World& world, int group, std::span<const int> extra) {
    const ChampionBelief* best = nullptr;
    float best_score = 0;
    // Allies are in index order: ties stay with the lower index.
    for (const auto& a : world.allies) {
        if (!crew_member(world, a, group, extra)) continue;
        if (const float s = tank_score(a); !best || s > best_score) best = &a, best_score = s;
    }
    return best;
}

// Farm's gold farmers (farm_turn's gold_farmer): they take the gold-only groups whatever a crew offers.
bool farms_gold(const World& world, const ChampionBelief& a) {
    return economy_three(world) && a.facts().passive == Passive::remote_shop && map_economy(world.map()).tavi_map();
}

float crew_output(const CrewAllies::Ally& a) {
    if (!a.has_output) a.output_ = camp_output(*a.a), a.has_output = true;
    return a.output_;
}

namespace {

void read_avail(const World& world, const CrewAllies& allies, const CrewAllies::Ally& x) {
    x.has_avail = true;
    x.avail = 0, x.harmless_claim = x.on_cleared = false;
    const auto& a = *x.a;
    if (a.is_self || !a.alive || farms_gold(world, a)) return;
    const auto& map = world.map();
    if (world.round == world.first_round && x.claim < 0) {
        x.avail = 1;
        return;
    }
    if (!a.visible) return;
    const int n = static_cast<int>(map.groups.size());
    const bool harmless = x.claim < 0 || (x.claim < n && map.groups[x.claim].strength <= 0);
    if (harmless && dist(a.pos, allies.here) <= params::crew_available_radius) {
        x.avail = 1;
        return;
    }
    x.avail = 2;
    if (x.claim >= 0 && harmless) x.harmless_claim = true, x.claim_centre = map.groups[x.claim].centre;
    if (const int on = map.group_at(a.pos); on >= 0 && world.camps[on].state == CampState::cleared)
        x.on_cleared = true, x.on_centre = map.groups[on].centre;
}

void read_pool(const CrewAllies& allies, const CrewAllies::Ally& x) {
    x.has_pool = true;
    const auto& a = *x.a;
    const float health = a.is_self ? allies.my_hp : a.health, max_health = a.is_self ? allies.my_max : a.max_health;
    x.weight = a.facts().walk_and_attack_independent() ? 1.5f : 1.0f;
    x.taken = crew_taken(a);
    x.score = (health - allies.line * max_health) / std::max(0.01f, x.taken) * x.weight;
    x.budget = crew_budget(health, max_health, allies.line), x.usable = crew_usable(max_health, allies.line);
}

} // namespace

// An ally free to join an operation on g: in sight within crew_available_radius of its centre and
// claiming nothing, a harmless group nearby, or holding a cleared group nearby. On the first turn
// everyone starts on spawn: any living ally with no claim yet. Also one in sight within
// crew_available_radius of us claiming nothing or a harmless group: it arrives about when we do
// (on spawn after a heal, most often). Never a gold farmer.
bool crew_available(const World& world, const CrewAllies& allies, const CrewAllies::Ally& a, int g) {
    if (!a.has_avail) read_avail(world, allies, a);
    if (a.avail == 0 || a.claim == g) return false;
    if (a.avail == 1) return true;
    const vec2 centre = world.map().groups[g].centre;
    if (dist(a.a->pos, centre) > params::crew_available_radius) return false;
    if (a.claim < 0) return true;
    if (a.harmless_claim && dist(a.claim_centre, centre) <= params::crew_near_radius) return true;
    return a.on_cleared && dist(a.on_centre, centre) <= params::crew_near_radius;
}

void crew_allies(const World& world, float line, CrewAllies& out) {
    // One read of our own record: each accessor reads the engine again.
    const auto& me = my_record();
    out.here = {me.x, me.y};
    out.world = &world;
    out.my_hp = me.health, out.my_max = me.max_health;
    out.line = line, out.n = 0, out.n_claiming = 0, out.self_slot = -1;
    out.n_joinable = -1, out.avail_group = -1;
    for (const auto& a : world.allies) {
        if (out.n == static_cast<int>(out.at.size())) break;
        auto& x = out.at[static_cast<std::size_t>(out.n)];
        x.a = &a;
        x.claim = comms::claim_of(world, a.index);
        x.seen = !a.is_self && a.alive && (a.visible || a.pos_round >= world.round - params::crew_seen_rounds);
        x.has_output = x.has_avail = x.has_pool = false;
        if (a.is_self) out.self_slot = out.n;
        else if (a.alive && x.claim >= 0) out.claiming[static_cast<std::size_t>(out.n_claiming++)] = static_cast<std::uint8_t>(out.n);
        ++out.n;
    }
}

std::uint32_t crew_claimer_bits(const CrewAllies& allies, int g) {
    std::uint32_t bits = 0;
    for (int k = 0; k < allies.n_claiming; ++k)
        if (const int i = allies.claiming[static_cast<std::size_t>(k)]; allies.at[static_cast<std::size_t>(i)].claim == g) {
            const auto& x = allies.at[static_cast<std::size_t>(i)];
            bool counts = x.seen;
            // Out of sight, the tile it posts (comms_slots) says whether it is at the group.
            if (vec2 at{-1, -1}; !counts && params::comms_slots) {
                if (int told = -1; comms::told_ally(x.a->index, at, told)) {
                    const vec2 centre = allies.world->map().groups[g].centre;
                    counts = std::max(0, dist(at, centre) - x.a->facts().attack_range())
                             <= std::max(0, dist(allies.here, centre) - allies.world->me().facts().attack_range()) + 2;
                }
            }
            if (counts) bits |= 1u << i;
        }
    return bits;
}

std::uint32_t crew_available_bits(const World& world, const CrewAllies& allies, int g) {
    if (allies.avail_group == g) return allies.avail_bits;
    if (allies.n_joinable < 0) {
        allies.n_joinable = 0;
        for (int i = 0; i < allies.n; ++i) {
            const auto& a = allies.at[static_cast<std::size_t>(i)];
            if (!a.has_avail) read_avail(world, allies, a);
            if (a.avail != 0) allies.joinable[static_cast<std::size_t>(allies.n_joinable++)] = static_cast<std::uint8_t>(i);
        }
    }
    std::uint32_t bits = 0;
    for (int k = 0; k < allies.n_joinable; ++k)
        if (const int i = allies.joinable[static_cast<std::size_t>(k)]; crew_available(world, allies, allies.at[static_cast<std::size_t>(i)], g)) bits |= 1u << i;
    allies.avail_group = g, allies.avail_bits = bits;
    return bits;
}

// The camps hit whoever tanks at the time, and the tank is the member with the best tank_score, so
// over a clear the hits level the members' scores (water filling): each member absorbs its score
// above the final level, over its melee weight (pre-emblem damage). The pool is us and the members
// in reach no later than 2 rounds after us; a later one cannot take the first hits.
// `pool`: its members in ally order (std::sort's input order, so ties fall as they always did).
void share_damage(const CrewAllies::Ally* const* members, int n, CrewPlan& p) {
    std::array<const CrewAllies::Ally*, 16> pool;
    std::copy_n(members, n, pool.begin());
    std::sort(pool.begin(), pool.begin() + n, [](const CrewAllies::Ally* x, const CrewAllies::Ally* y) { return x->score > y->score; });
    // The level L where the top j absorb the damage: sum over them of (s - L) / w = damage.
    float a_sum = 0, b_sum = 0, level = 0;
    for (int j = 0; j < n; ++j) {
        a_sum += pool[j]->score / pool[j]->weight, b_sum += 1.0f / pool[j]->weight;
        level = (a_sum - p.damage) / b_sum;
        if (j + 1 == n || level >= pool[j + 1]->score) break;
    }
    p.trips = 0, p.my_damage = 0;
    for (int j = 0; j < n; ++j) {
        const auto& m = *pool[j];
        const float absorbed = std::max(0.0f, (m.score - level) / m.weight);
        if (m.a->is_self) p.my_damage = absorbed;
        p.trips += extra_trips(absorbed * m.taken, m.budget, m.usable);
    }
}

CrewPlan plan_crew(const World& world, const CrewAllies& allies, int g, float my_output, bool expect, int cap) {
    CrewPlan plan;
    plan.output = my_output;
    // A claimer long out of sight may be healing or banking anywhere: it is not counted on.
    // Members hit from spawn stands are priced free only while the crew's least sturdy body outlasts their
    // fire. The stands stay ours: the crew's shortest range would reprice every clear, not only spawn stands.
    float survivable = home_survivable(world.me());
    for (std::uint32_t b = crew_claimer_bits(allies, g); b; b &= b - 1) {
        const auto& a = allies.at[static_cast<std::size_t>(std::countr_zero(b))];
        plan.output += crew_output(a), ++plan.claimers;
        survivable = std::min(survivable, home_survivable(*a.a));
    }
    // share_damage's pool: us and the claimers in sight, in ally order, less those arriving later
    // than 2 rounds after us; expected allies join it in their ally order (`joins`). Claimers out of
    // sight add output only: their health and arrival are unknown.
    // crew_arrival lies between the walk to the members' box and to the centre (a member), less the
    // range: most tests are settled by those, without either exact arrival.
    const auto& G = world.map().groups[g];
    const auto [box_lo, box_hi] = crew_box(world, g);
    const auto arrival_lo = [&](vec2 p, int range) {
        return std::max({0, box_lo.x - p.x - range, p.x - box_hi.x - range, box_lo.y - p.y - range, p.y - box_hi.y - range});
    };
    const auto arrival_hi = [&](vec2 p, int range) { return std::max(0, dist(p, G.centre) - range); };
    const int my_range = world.me().facts().attack_range();
    const int mine_lo = arrival_lo(allies.here, my_range), mine_hi = arrival_hi(allies.here, my_range);
    int mine = -1;
    const auto late = [&](const ChampionBelief& b) {
        const int range = b.facts().attack_range();
        if (arrival_hi(b.pos, range) <= mine_lo + 2) return false;
        if (arrival_lo(b.pos, range) > mine_hi + 2) return true;
        if (mine < 0) mine = crew_arrival(world, world.me(), g, allies.here);
        return crew_arrival(world, b, g, b.pos) > mine + 2;
    };
    const auto in_time = [&](const CrewAllies::Ally& a) {
        const auto& b = *a.a;
        if (!b.is_self && (b.visible || in_bounds(b.pos)) && late(b)) return false;
        if (!a.has_pool) read_pool(allies, a);
        return true;
    };
    std::array<const CrewAllies::Ally*, 16> base;
    std::array<int, 16> base_slot;
    int n_base = 0;
    const auto take = [&](int i) {
        if (const auto& a = allies.at[static_cast<std::size_t>(i)]; in_time(a)) base_slot[n_base] = i, base[n_base++] = &a;
    };
    int self = allies.self_slot;
    for (int k = 0; k < allies.n_claiming; ++k) {
        const int i = allies.claiming[static_cast<std::size_t>(k)];
        if (self >= 0 && self < i) take(self), self = -1;
        if (const auto& a = allies.at[static_cast<std::size_t>(i)]; a.a->visible && a.claim == g) take(i);
    }
    if (self >= 0) take(self);
    // Expected allies in the pool, by slot bit.
    std::uint32_t joins = 0;
    const auto price = [&](CrewPlan& p) {
        float h = survivable;
        for (int k = 0; k < p.n_expected; ++k) h = std::min(h, home_survivable(*allies.at[static_cast<std::size_t>(p.expected[k])].a));
        p.damage = min_camp_damage(world, g, p.output, &p.rounds, 0, -1, h);
        // Only the traces read the tank.
        debug_block({ p.tank = crew_tank(world, g, {p.expected.data(), static_cast<std::size_t>(p.n_expected)}); });
        if (joins == 0) return share_damage(base.data(), n_base, p);
        std::array<const CrewAllies::Ally*, 16> pool;
        int n = 0, j = 0;
        for (std::uint32_t b = joins; b; b &= b - 1) {
            const int i = std::countr_zero(b);
            while (j < n_base && base_slot[j] < i) pool[n++] = base[j++];
            pool[n++] = &allies.at[static_cast<std::size_t>(i)];
        }
        while (j < n_base) pool[n++] = base[j++];
        share_damage(pool.data(), n, p);
    };
    price(plan);
    if (!expect || plan.trips == 0) return plan;
    // Nearest first, while each one more still saves the crew a trip.
    std::array<std::pair<int, int>, 16> free{};
    int n_free = 0;
    const vec2 centre = world.map().groups[g].centre;
    for (std::uint32_t b = crew_available_bits(world, allies, g); b; b &= b - 1) {
        const auto& a = allies.at[static_cast<std::size_t>(std::countr_zero(b))];
        free[n_free++] = {dist(a.a->pos, centre), a.a->index};
    }
    std::sort(free.begin(), free.begin() + n_free);
    for (int i = 0; i < n_free && 1 + plan.claimers + plan.n_expected < cap && plan.trips > 0; ++i) {
        CrewPlan more = plan;
        const int slot = free[i].second;
        more.expected[more.n_expected++] = slot;
        const auto& a = allies.at[static_cast<std::size_t>(slot)];
        more.output += crew_output(a);
        if (a.a->alive && in_time(a)) joins |= 1u << slot;
        price(more);
        if (more.trips >= plan.trips) break;
        plan = more;
    }
    return plan;
}

bool farm_monolith(const World& world, int g) {
    const auto& map = world.map();
    return g >= 0 && g < static_cast<int>(map.groups.size()) && map.groups[g].has_monolith && !map.monolith_only;
}

// We are hit while no nearer than the nearest covering member: stepping out a tile a turn, that is
// its distance less ours, and one more hit to spare.
int mono_trapped(const World& world, Pathing& pathing, Safety& safety, const Memory& memory, float health) {
    const int g = memory.claim;
    if (memory.siege || !farm_monolith(world, g) || world.camps[g].state != CampState::alive) return -1;
    const auto& G = world.map().groups[g];
    const auto& c = world.camps[g];
    const vec2 here = my_position();
    if (!test(G.threat(), here)) return -1;
    const auto striker_dist = [&](vec2 p) {
        int d = unreachable;
        for (std::size_t i = 0; i < G.members.size(); ++i)
            if (G.members[i].strength > 0 && c.health[i] > 0) d = std::min(d, dist(p, G.members[i].pos));
        return d;
    };
    int cover = unreachable;
    for (const auto& a : world.allies)
        if (!a.is_self && a.alive && a.visible && a.channel != Channel::teleport && !real_recall(a) && test(G.threat(), a.pos))
            cover = std::min(cover, striker_dist(a.pos));
    const int mine = striker_dist(here);
    if (cover == unreachable || mine == unreachable) return -1;
    const float dps = safety.camp_damage(here);
    // Or on our spawn sooner, where the turn end heals: the phases at the tiles before it.
    const int out = std::max(0, cover - mine) + 1;
    const int phases = std::min(out, std::max(1, home_exit_steps(world, pathing, safety, here, out)));
    return health + my_live_shield(world) <= dps * static_cast<float>(phases);
}

} // namespace

} // namespace aph
