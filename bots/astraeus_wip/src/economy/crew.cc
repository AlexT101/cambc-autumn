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

// Walking steps round static terrain to the standable tiles within `range` of a member that see it
// (sight is symmetric; off bushes, as stand_reach reads stands): the same for every ally. One field
// per group and range (melee or ranged), kept.
const Field& crew_stand_field(const StaticMap& map, int g, int range) {
    static std::vector<std::array<std::optional<Field>, 2>> fields;
    if (fields.size() < map.groups.size()) fields.resize(map.groups.size());
    auto& f = fields[static_cast<std::size_t>(g)][range > 1];
    if (!f) {
        bitboard goals;
        static bitboard seen{cambc::uninitialized};
        for (const auto& m : map.groups[g].members) {
            map.sight_off_bushes_into(m.pos, range, seen);
            goals |= seen;
        }
        goals &= map.standable;
        f = make_field(map.blocked_for_us, goals);
    }
    return *f;
}

// Rounds until a champion's basic attack reaches the group, by the walk to a tile in its attack
// range that sees a member (crew_stand_field: allies are ranked against us alike); with none, the
// walk onto its camp tiles less the range.
int crew_arrival(const World& world, Pathing& pathing, const ChampionBelief& a, int g, vec2 p) {
    if (const int s = crew_stand_field(world.map(), g, a.facts().attack_range()).at(p); s != unreachable) return s;
    // Each pricing asks again for the same tiles, and the walk is over static walls: kept per group
    // and body by tile (zero: none kept).
    static std::array<std::array<std::pair<int, int>, 8>, 256> kept;
    const int key = ((p.x + 1) << 8 | (p.y + 1)) + 1;
    if (static_cast<std::size_t>(g) >= kept.size() || static_cast<std::size_t>(a.index) >= kept[0].size())
        return std::max(0, team_walk_to(world, pathing, g, p) - a.facts().attack_range());
    auto& k = kept[static_cast<std::size_t>(g)][static_cast<std::size_t>(a.index)];
    if (k.first != key) k = {key, team_walk_to(world, pathing, g, p)};
    return std::max(0, k.second - a.facts().attack_range());
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
    const auto& f = a.facts();
    return economy_three(world) && f.passive == Passive::remote_shop && map_economy(world.map()).tavi_map();
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
    out.my_hp = me.health, out.my_max = me.max_health;
    out.line = line, out.n = 0;
    for (const auto& a : world.allies) {
        if (out.n == static_cast<int>(out.at.size())) break;
        auto& x = out.at[static_cast<std::size_t>(out.n++)];
        x.a = &a;
        x.claim = comms::claim_of(world, a.index);
        x.seen = !a.is_self && a.alive && (a.visible || a.pos_round >= world.round - params::crew_seen_rounds);
        x.has_output = x.has_avail = x.has_pool = false;
    }
}

// The camps hit whoever tanks at the time, and the tank is the member with the best tank_score, so
// over a clear the hits level the members' scores (water filling): each member absorbs its score
// above the final level, over its melee weight (pre-emblem damage). The pool is us and the members
// in reach no later than 2 rounds after us; a later one cannot take the first hits.
void share_damage(const World& world, Pathing& pathing, const CrewAllies& allies, int g, CrewPlan& p) {
    std::array<const CrewAllies::Ally*, 16> pool;
    int n = 0;
    const int mine = crew_arrival(world, pathing, world.me(), g, allies.here);
    const auto add = [&](const CrewAllies::Ally& a) {
        if (n == static_cast<int>(pool.size())) return;
        const auto& b = *a.a;
        if (!b.is_self && (b.visible || in_bounds(b.pos)) && crew_arrival(world, pathing, b, g, b.pos) > mine + 2) return;
        if (!a.has_pool) read_pool(allies, a);
        pool[n++] = &a;
    };
    const auto expected_end = p.expected.begin() + p.n_expected;
    for (int i = 0; i < allies.n; ++i) {
        const auto& a = allies.at[i];
        const auto& b = *a.a;
        if (b.is_self) {
            add(a);
            continue;
        }
        // Claimers out of sight add output only: their health and arrival are unknown.
        if (b.alive && ((b.visible && a.claim == g) || std::find(p.expected.begin(), expected_end, b.index) != expected_end))
            add(a);
    }
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

CrewPlan plan_crew(const World& world, Pathing& pathing, const CrewAllies& allies, int g, float my_output, bool expect, int cap) {
    CrewPlan plan;
    plan.output = my_output;
    // A claimer long out of sight may be healing or banking anywhere: it is not counted on.
    for (int i = 0; i < allies.n; ++i)
        if (const auto& a = allies.at[i]; a.seen && a.claim == g) plan.output += crew_output(a), ++plan.claimers;
    // Members hit from spawn stands are priced free only while the crew's least sturdy body outlasts their
    // fire. The stands stay ours: the crew's shortest range would reprice every clear, not only spawn stands.
    float survivable = home_survivable(world.me());
    for (int i = 0; i < allies.n; ++i)
        if (const auto& a = allies.at[i]; a.seen && a.claim == g) survivable = std::min(survivable, home_survivable(*a.a));
    // An awake group nobody engages yet hits whoever comes first before the crew's first hit: priced at
    // our walk, as the clear's stands are ours.
    const auto& c = world.camps[g];
    const bool arrives_awake = c.state == CampState::alive && c.awake != Awake::asleep && !ally_engaged(world, g);
    const int mine = arrives_awake ? crew_arrival(world, pathing, world.me(), g, allies.here) : 0;
    const auto price = [&](CrewPlan& p) {
        float h = survivable;
        for (int k = 0; k < p.n_expected; ++k) h = std::min(h, home_survivable(*allies.at[static_cast<std::size_t>(p.expected[k])].a));
        int first = -1;
        p.damage = min_camp_damage(world, g, p.output, &p.rounds, 0, -1, h, &first);
        if (arrives_awake) p.damage += awake_arrival_fire(world, g, -1, first, mine, false);
        // Only the traces read the tank.
        debug_block({ p.tank = crew_tank(world, g, {p.expected.data(), static_cast<std::size_t>(p.n_expected)}); });
        share_damage(world, pathing, allies, g, p);
    };
    price(plan);
    if (!expect || plan.trips == 0) return plan;
    // Soonest in reach first (crew_arrival), each joining if it saves the crew a trip.
    std::array<std::pair<int, int>, 16> free{};
    int n_free = 0;
    for (int i = 0; i < allies.n; ++i)
        if (const auto& a = allies.at[i]; n_free < static_cast<int>(free.size()) && crew_available(world, allies, a, g))
            free[n_free++] = {crew_arrival(world, pathing, *a.a, g, a.a->pos), a.a->index};
    std::sort(free.begin(), free.begin() + n_free);
    for (int i = 0; i < n_free && 1 + plan.claimers + plan.n_expected < cap && plan.trips > 0; ++i) {
        CrewPlan more = plan;
        more.expected[more.n_expected++] = free[i].second;
        more.output += crew_output(allies.at[static_cast<std::size_t>(free[i].second)]);
        price(more);
        if (more.trips < plan.trips) plan = more;
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
