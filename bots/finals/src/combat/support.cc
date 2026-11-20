// Willow's support of its protected mate (Prism, or Tavi on 3-pick maps without one): exposure, heal
// stations and views, and both sides of the pair's local support.
#include "../bot_parts.h"

namespace aph {

namespace {

Stations& stations_cache() {
    static Stations s;
    return s;
}

// Asleep members and ones a nearer ally draws count too: the group can wake, and the ally leave.
bool camp_may_hit(const World& world, vec2 p) {
    for (const int g : world.map().groups_near(p, world.map().max_camp_reach)) {
        const auto& group = world.map().groups[g];
        if (group.strength <= 0) continue;
        const auto& c = world.camps[g];
        const bool returning = c.state == CampState::respawning && c.respawn_round <= world.round + 1;
        if (!returning && c.state != CampState::alive) continue;
        for (std::size_t i = 0; i < group.members.size(); ++i) {
            const auto& m = group.members[i];
            if (m.strength > 0 && (returning || c.health[i] > 0) && dist(p, m.pos) <= m.reach) return true;
        }
    }
    return false;
}

// Willow holds no fight: a tile an enemy is likely to hit (want_home's test) or any camp member may
// hit is unsafe. `enemies`: false when no enemy can hit p, which spares their search.
SupportExposure exposure_at(const World& world, Safety& safety, vec2 p, bool enemies = true) {
    SupportExposure risk;
    risk.enemy = enemies && safety.threat_at(p);
    risk.camp = !risk.enemy && camp_may_hit(world, p);
    return risk;
}

// Camp exposure of the nine stations, with each nearby group read once.
unsigned camp_station_mask(const World& world, vec2 here) {
    unsigned mask = 0;
    for (const int g : world.map().groups_near(here, world.map().max_camp_reach + 1)) {
        const auto& group = world.map().groups[g];
        if (group.strength <= 0) continue;
        const auto& c = world.camps[g];
        const bool returning = c.state == CampState::respawning && c.respawn_round <= world.round + 1;
        if (!returning && c.state != CampState::alive) continue;
        for (std::size_t i = 0; i < group.members.size(); ++i) {
            const auto& m = group.members[i];
            if (m.strength <= 0 || (!returning && c.health[i] <= 0)) continue;
            const int dx = m.pos.x - here.x, dy = m.pos.y - here.y;
            const int lo = std::max(-1, dx - m.reach), hi = std::min(1, dx + m.reach);
            const int top = std::max(-1, dy - m.reach), bottom = std::min(1, dy + m.reach);
            if (lo > hi || top > bottom) continue;
            const unsigned row = ((1u << (hi - lo + 1)) - 1u) << (lo + 1);
            for (int y = top; y <= bottom; ++y) mask |= row << (3 * (y + 1));
            if (mask == 511u) return mask;
        }
    }
    return mask;
}

// Positions share the enemy bound, but a turn staying here need not price its neighbours.
const Station& station(const World& world, Safety& safety, vec2 here, int k, bool camps = true) {
    auto& s = stations_cache();
    if (s.observations != world.observations || s.origin != here) {
        world.throw_if_stale();
        s.origin = {-1, -1};
        clear_board(s.guard);
        s.known = s.camps_known = 0;
        s.camp_mask = -1;
        s.enemies = safety.credible_enemy_may_hit_within(here, 1);
        world.throw_if_stale();
        s.observations = world.observations;
        s.origin = here;
    }
    auto& tile = s.tiles[k];
    if (!(s.known >> k & 1)) {
        world.throw_if_stale();
        tile.p = k == 0 ? here : here + directions[k - 1];
        tile.open = in_bounds(tile.p) && test(world.map().open_for_us, tile.p);
        tile.risk = {tile.open && s.enemies && safety.threat_at(tile.p), false};
        if (tile.risk.enemy) set_tile(s.guard, tile.p);
        world.throw_if_stale();
        s.known |= 1u << k;
    }
    if (camps && !(s.camps_known >> k & 1)) {
        if (tile.open && !tile.risk.enemy) {
            if (s.camp_mask < 0) s.camp_mask = static_cast<int>(camp_station_mask(world, here));
            const int bit = 3 * (tile.p.y - here.y + 1) + tile.p.x - here.x + 1;
            tile.risk.camp = (static_cast<unsigned>(s.camp_mask) >> bit & 1) != 0;
        }
        world.throw_if_stale();
        s.camps_known |= 1u << k;
    }
    return tile;
}

const Stations& stations(const World& world, Safety& safety, vec2 here) {
    for (int k = 0; k < 9; ++k) station(world, safety, here, k, false);
    return stations_cache();
}

SupportExposure exposure_here(const World& world, Safety& safety) {
    return station(world, safety, my_position(), 0).risk;
}

// Early, healthy, with a visible ally within willow_stand_ally: the fight simulation, not the enemy's reach alone,
// sends Willow home.
bool willow_stands(const World& world) {
    if (!willow_early(world) || my_health() < params::hurt_health_fraction * my_max_health()) return false;
    const vec2 here = my_position();
    for (const auto& a : world.allies)
        if (!a.is_self && a.alive && a.visible && dist(a.pos, here) <= params::willow_stand_ally) return true;
    return false;
}

// Ours, or a free open tile a step reaches.
bool station_legal(Pathing& pathing, const Station& tile, vec2 here) {
    return tile.open && (tile.p == here || (my_can_move() && !test(pathing.blocked(), tile.p)));
}

SupportExposure support_exposure(const World& world, Safety& safety, vec2 p) {
    if (const vec2 here = my_position(); world.me().facts().heals() && dist(p, here) <= 1) {
        if (p == here) return station(world, safety, here, 0).risk;
        for (int k = 0; k < 8; ++k)
            if (p == here + directions[k]) return station(world, safety, here, k + 1).risk;
    }
    return exposure_at(world, safety, p);
}

// A camp support may hit where it stands: one that cannot strike back, or the work group once awake.
int attack_support_camp(const World& world, int work) {
    return attack_camp(world, [&](int g) {
        return world.map().groups[g].strength <= 0 || (g == work && world.camps[g].awake != Awake::asleep);
    });
}

// Willow with its heal cooling down: a basic attack, and the reset's, from where it stands.
bool stationary_support_output(const World& world, int work) {
    world.throw_if_stale();
    bool hit = attack_enemy(world);
    int camp = -1;
    if (!hit && my_can_attack()) camp = attack_support_camp(world, work);
    hit |= camp >= 0;
    // The reset takes the turn's cast: only while the heal could not.
    if (hit && my_cooldown(world.me().facts().slot_of(AbilityKind::heal)) > 0) {
        if (camp >= 0) reset_and_attack_camp(world, camp);
        else reset_and_attack_enemy(world);
    }
    return hit;
}

bool support_view(Reach::Window viewers, vec2 target, vec2 p) {
    const int x = p.x - target.x, y = p.y - target.y;
    return std::abs(x) <= Reach::Window::radius && std::abs(y) <= Reach::Window::radius
           && static_cast<bool>(viewers & Reach::Window::bit(Reach::Window::at(x, y)));
}

const ChampionBelief* support_endpoint(const World& world, bool healer) { return support_pair(world)[healer ? 1 : 0]; }

void close_recovery(Memory& memory, float health) {
    if (memory.recovery_start >= 0) {
        memory.recovery_closed_group = memory.recovery_group;
        memory.recovery_reentry = health >= 0;
    }
    if (health < 0) memory.recovery_reentry = false, memory.recovery_closed_group = -1;
    memory.recovery_start = -1;
    memory.recovery_turns = 0;
    memory.recovery_closed_health = health;
}

bool recovered_for_work(const World& world, Safety& safety, const Memory& memory) {
    const float health = my_health();
    if (health <= safety.damage_bound(my_position(), true, world.me().taken)) return false;
    const int g = memory.farm_group;
    if (g < 0 || g >= static_cast<int>(world.camps.size()) || world.camps[g].state != CampState::alive) return true;
    float rounds = 0;
    const int slot = world.me().facts().slot_of(AbilityKind::shield);
    const float ready_in = slot < 0 ? 0.0f : static_cast<float>(std::max(0, world.me().ready_round[slot] - world.round));
    const float damage = shielded_clear(camp_hit_factor() * min_camp_damage(world, g, camp_output(world.me()), &rounds), rounds,
                                        self_shield_amount(world.me()), ready_in);
    return params::camp_risk * damage <= health - recall_line(world, safety) * my_max_health();
}

int heal_range(const ChampionBelief& healer) {
    const auto& f = healer.facts();
    return f.abilities[f.slot_of(AbilityKind::heal)].range();
}

// The sight of `owner`'s ward, if we see it up: a unit an ally's own ward sees is in that ally's
// sight wherever it steps (wards.vision), so its heal reaches it (abilities.unit_target). Read per
// call: a ward can go down mid-turn without a re-observe (submit_here); its mask is cast again only
// when it moves.
const bitboard* ward_sight(const World& world, std::uint32_t owner) {
    static bitboard sight{cambc::uninitialized};
    static vec2 cast_at{-1, -1};
    static std::array<cambc::detail::ward_info, 16> raw;
    std::uint32_t k = 0;
    ok(cambc::detail::sdk_wards(raw.data(), static_cast<std::uint32_t>(raw.size()), &k));
    const auto own = static_cast<std::uint32_t>(world.map().team_a ? 0 : 1);
    for (std::uint32_t i = 0; i < k && i < raw.size(); ++i) {
        const auto& w = raw[i];
        if (w.team != own || w.owner != owner || w.disabled) continue;
        if (const vec2 at{w.x, w.y}; at != cast_at) ok(cambc::detail::sdk_ward_vision(at.x, at.y, sight.ptr())), cast_at = at;
        return &sight;
    }
    return nullptr;
}

bool own_ward_sees(const World& world, vec2 p) {
    const auto* sight = ward_sight(world, my_handle());
    return sight && test(*sight, p);
}

// Tiles within `range` of a visible ally from which we would see it, as a window around it:
// attack_viewers, plus our own tile, which sees it now even from a bush beyond a step; every tile
// when our ward sees it.
Reach::Window heal_viewers(const World& world, vec2 target, int range) {
    range = std::clamp(range, 0, Reach::Window::radius);
    Reach::Window w;
    if (own_ward_sees(world, target)) return window_square(range);
    w = attack_viewers(world, target, range);
    if (const vec2 here = my_position(); dist(here, target) <= range)
        w |= Reach::Window::bit(Reach::Window::at(here.x - target.x, here.y - target.y));
    return w;
}

struct HealView {
    HealTarget target;
    Reach::Window viewers; // tiles that see it within heal range
};

// heal_target's allies within a step of our heal range of p: worth the step, and the cast once there.
int heal_views(const World& world, Safety& safety, vec2 p, float amount, std::array<HealView, 8>& out) {
    const int range = heal_range(world.me());
    HealGate gate(world, safety, p, range + 1, amount);
    int n = 0;
    for (const auto& a : world.allies)
        if (dist(p, a.pos) <= range + 1)
            if (const auto t = heal_target(world, a, amount, &gate, true)) out[n++] = {*t, heal_viewers(world, t->pos, range)};
    return n;
}

// One is in heal range of p: heal_ally casts from there without a step.
bool heal_lands_from(const World& world, vec2 p, const std::array<HealView, 8>& views, int n) {
    const int range = heal_range(world.me());
    for (int t = 0; t < n; ++t)
        if (dist(p, views[t].target.pos) <= range) return true;
    return false;
}

// The neighbouring station `ok` accepts from which a heal lands best (heal_before), then the least
// `cost`. `here` if none.
template <class Ok, class Cost>
vec2 heal_station(const World& world, Pathing& pathing, Safety& safety, vec2 here, const std::array<HealView, 8>& views,
                  int n, Ok&& ok, Cost&& cost) {
    vec2 best = here;
    const HealTarget* best_target = nullptr;
    int best_cost = unreachable;
    const auto mate = heal_mate(world);
    for (int k = 1; k < 9; ++k) {
        const auto& tile = station(world, safety, here, k);
        if (!station_legal(pathing, tile, here) || !ok(tile)) continue;
        const int g = world.map().group_at(tile.p);
        if (g >= 0 && world.camps[g].state == CampState::cleared) continue;
        const int c = cost(tile);
        for (int t = 0; t < n; ++t) {
            const auto& target = views[t].target;
            if (!support_view(views[t].viewers, target.pos, tile.p)) continue;
            if (!best_target || heal_before(target, *best_target, mate) || (!heal_before(*best_target, target, mate) && c < best_cost))
                best = tile.p, best_target = &target, best_cost = c;
        }
    }
    return best;
}

bool willow_bank_heal_step(World& world, Pathing& pathing, Safety& safety, const Field& field) {
    if (!world.me().facts().heals() || !my_can_move() || winning_bag(world)
        || closing(world, pathing) || holding_capture(world, pathing) || contesting(world)) return false;
    float amount = 0;
    if (!heal_ready(world, world.me(), amount)) return false;
    const vec2 here = my_position();
    const int here_steps = field.at(here);
    if (here_steps == unreachable) return false;
    std::array<HealView, 8> views;
    const int n = heal_views(world, safety, here, amount, views);
    if (n == 0 || heal_lands_from(world, here, views, n)) return false;
    world.throw_if_stale();
    guard_steps(world, pathing, safety);
    if (!station(world, safety, here, 0).risk.safe()) return false;
    // An equal-distance step gives up a turn of progress for the heal.
    const vec2 best = heal_station(world, pathing, safety, here, views, n, [&](const Station& tile) {
        const int steps = field.at(tile.p);
        return tile.risk.safe() && steps != unreachable && steps <= here_steps;
    }, [&](const Station& tile) { return field.at(tile.p); });
    world.throw_if_stale();
    if (best == here) return false;
    if (!pathing.try_move(best)) {
        see_again(world, pathing, safety); // a hidden unit refused it, unseen by see_revealed
        world.throw_if_stale();
        return false;
    }
    see_revealed(world, pathing, safety);
    heal_ally(world, safety);
    return true;
}

// The camps Willow's turn goes on to hit if it does not step: groups that cannot strike back, and
// its farm's own, which the farm may wake on purpose.
bool hit_if_staying(const World& world, int g, int farm_group) {
    return world.map().groups[g].strength <= 0 || g == farm_group;
}

bool camp_to_hit(const World& world, vec2 here, int range, int farm_group) {
    const auto& live = live_camp_tiles();
    for (const int g : world.map().groups_near(here, range)) {
        if (!hit_if_staying(world, g, farm_group)) continue;
        for (const auto& m : world.map().groups[g].members)
            if (dist(here, m.pos) <= range && test(live, m.pos)) return true;
    }
    return false;
}

bool immediate_camp_finish(const World& world, vec2 here, float basic, bool reset_ready, int farm_group) {
    const int range = world.me().facts().attack_range();
    for (const int g : world.map().groups_near(here, range)) {
        if (!hit_if_staying(world, g, farm_group)) continue;
        const auto& c = world.camps[g];
        const auto& members = world.map().groups[g].members;
        for (std::size_t i = 0; i < members.size(); ++i) {
            if (dist(here, members[i].pos) > range || !test(world.visible, members[i].pos)) continue;
            if (c.state_round != world.round) return true;
            if (c.state != CampState::alive) continue;
            // Any member this turn's basics may finish, or whose health is unread.
            if (c.health_round[i] != world.round) return true;
            if (c.health[i] > 0 && c.health[i] <= (reset_ready ? 2.0f : 1.0f) * basic) return true;
        }
    }
    return false;
}

bool willow_independent_heal_step(World& world, Pathing& pathing, Safety& safety, int farm_group) {
    if (stunned_turn || !my_can_move()) return false;
    const vec2 here = my_position();
    if (test(world.map().ally_spawn, here)) return false;
    float amount = 0;
    if (!heal_ready(world, world.me(), amount)) return false;
    guard_steps(world, pathing, safety);
    const auto quiet = [&](const SupportExposure& risk, vec2 p) {
        if (!risk.safe()) return false;
        const auto b = safety.bound(p, world.me().taken);
        return !b.stuns && b.doubled == 0;
    };
    std::array<HealView, 8> views;
    int n = heal_views(world, safety, here, amount, views);
    if (n == 0 || heal_lands_from(world, here, views, n)) return false;
    // The basics the step gives up: a ranged walk spends the attack and the heal takes the turn's
    // cast, so with a camp in reach the attack and the ready reset's; and a possible return step's.
    const auto& f = world.me().facts();
    const int reset = f.slot_of(AbilityKind::attack_reset);
    const bool reset_ready = reset >= 0 && world.me().ability_ready(reset, world.round) && my_cooldown(reset) == 0;
    const int forgone = 1 + (camp_to_hit(world, here, f.attack_range(), farm_group) ? 1 + reset_ready : 0);
    const float basic = my_strength() * camp_dealt_factor();
    n = static_cast<int>(std::remove_if(views.begin(), views.begin() + n,
                                        [&](const HealView& v) { return !(v.target.gain > forgone * basic); }) - views.begin());
    if (n == 0 || immediate_camp_finish(world, here, basic, reset_ready, farm_group)) return false;
    if (!quiet(station(world, safety, here, 0).risk, here)) return false;
    const vec2 best = heal_station(world, pathing, safety, here, views, n, [&](const Station& tile) { return quiet(tile.risk, tile.p); },
                                   [](const Station&) { return 0; });
    world.throw_if_stale();
    if (best == here) return false;
    debug_block({
        std::printf("WIH %d %u from %d,%d to %d,%d basic %.1f\n", world.round,
            static_cast<std::uint32_t>(world.me().handle), here.x, here.y, best.x, best.y, basic);
    });
    if (!pathing.try_move(best)) {
        see_again(world, pathing, safety); // a hidden unit refused it, unseen by see_revealed
        world.throw_if_stale();
        support_retreat = !support_exposure(world, safety, my_position()).safe();
        return false;
    }
    support_owned = true;
    see_revealed(world, pathing, safety);
    const bool healed = heal_ally(world, safety);
    debug_block({ std::printf("WIH-DONE %d %u moved 1 healed %d\n", world.round,
        static_cast<std::uint32_t>(world.me().handle), healed); });
    decision = Branch::willow_support;
    return true;
}

// Farm turns: a healer walks back within 2 of the ally with the most allies within 4 of it (ties: the
// nearest) when it is farther; within 2, it hits that ally's claimed group from where it stands.
// The ally's tile when seen within 2 rounds, else as it posted it (comms_ally) within 6, else the centre
// of the group it posts as its claim.
bool willow_follow(World& world, Pathing& pathing, Safety& safety) {
    constexpr int follow_dist = 2, crowd_radius = 4;
    if (!world.me().facts().heals() || !my_can_move() || stunned_turn) return false;
    const vec2 here = my_position();
    const auto known = [&](const ChampionBelief& a, vec2& at) {
        if (a.visible || (a.pos_round >= world.round - 2 && a.pos.x >= 0)) return at = a.pos, true;
        if (int told = -1; params::comms_ally && comms::told_ally(a.index, at, told) && told >= world.round - 6 && told > a.pos_round) return true;
        const int g = comms::claim_of(world, a.index);
        if (g >= 0 && g < static_cast<int>(world.map().groups.size())) return at = world.map().groups[g].centre, true;
        return false;
    };
    const ChampionBelief* target = nullptr;
    vec2 at{-1, -1};
    int best = -1, best_d = unreachable;
    std::array<vec2, 8> pos;
    std::array<bool, 8> has{};
    for (const auto& a : world.allies)
        if (!a.is_self && a.alive && a.index < 8) has[a.index] = known(a, pos[a.index]);
    for (const auto& a : world.allies) {
        if (a.is_self || !a.alive || a.index >= 8 || !has[a.index]) continue;
        int crowd = 0;
        for (const auto& b : world.allies)
            if (!b.is_self && b.alive && b.index < 8 && has[b.index] && dist(pos[b.index], pos[a.index]) <= crowd_radius) ++crowd;
        const int d = dist(here, pos[a.index]);
        if (crowd > best || (crowd == best && d < best_d)) best = crowd, best_d = d, target = &a, at = pos[a.index];
    }
    if (!target || test(world.map().ally_spawn, at)) return false;
    if (dist(here, at) <= follow_dist) {
        const int g = comms::claim_of(world, target->index);
        if (g >= 0 && my_can_attack() && attack_camp(world, [&](int h) { return h == g && world.camps[h].awake != Awake::asleep; }) >= 0) {
            // Early, the reset's hit unless the heal lands.
            if (willow_early(world) && !my_can_attack() && !heal_ally(world, safety)) reset_and_attack_camp(world, g);
            decision = Branch::willow_support;
            return true;
        }
        return false;
    }
    const bitboard goals = within(world.map().open_for_us, at, follow_dist);
    if (board_empty(goals)) return false;
    world.throw_if_stale();
    if (!pathing.step_towards(goals)) return false;
    see_revealed(world, pathing, safety);
    heal_ally(world, safety);
    decision = Branch::willow_support;
    return true;
}

void drop_claim(Memory& memory);

// We see the mate hurt, or an enemy in sight that could reach it within the recall line's threat
// radius. Not while it heals on spawn or channels: local_support leaves it alone then.
bool mate_in_danger(const World& world, const ChampionBelief& mate) {
    if (!mate.alive || !mate.visible || test(world.map().ally_spawn, mate.pos) || mate.channel == Channel::tribute
        || mate.channel == Channel::teleport || real_recall(mate))
        return false;
    if (mate.health < params::hurt_health_fraction * mate.max_health) return true;
    for (const auto& e : world.enemies)
        if (e.alive && e.visible && enemy_reach::within(world, e, enemy_reach::origin(e), mate.pos, Strike::max_reach + params::threat_radius))
            return true;
    return false;
}

// The pair's support binds Willow to its mate: the mate asks for a heal, or is in danger as we see it.
bool mate_needs_support(const World& world) {
    const auto* mate = support_endpoint(world, false);
    if (!mate || !mate->alive || !support_healer(world.me())) return false;
    return comms::support_request(world) || mate_in_danger(world, *mate);
}

// Willow as the team's medic: the ally whose next heal saves the most rounds of farm, net of our
// walk there. An ally's heal is priced as heal_value prices it (the trip home it replaces) at the
// health it will have when the heal can land: the later of our cooldown and our walk into range,
// its missing health growing by the camp fire it stands in. An ally out of sight counts only while
// it works the live group it claims (where its told tile or last sighting puts it), at its last
// sighting's health less the fire since. The horizon is a walk that ends within one cooldown of
// heal range: farther, the walk costs heal time the cooldown would not.
struct MedicTarget {
    const ChampionBelief* ally = nullptr;
    vec2 pos{-1, -1};
    float net = 0;
    bool urgent = false;
};

MedicTarget medic_target(const World& world, Safety& safety, vec2 here, int range, float amount, int cooldown) {
    const int horizon = range + ability_cooldown;
    const auto& groups = world.map().groups;
    HealGate gate(world, safety, here, horizon, amount);
    MedicTarget best;
    for (const auto& a : world.allies) {
        if (a.is_self || !a.alive || a.facts().heals()) continue;
        vec2 pos = a.pos;
        float health = a.health, max_health = a.max_health;
        int since = 0;
        if (a.visible) {
            const auto* live = visible_record(a.handle);
            if (!live || kept_recall(a.handle, a.recall_turns())) continue;
            pos = {live->x, live->y}, health = live->health, max_health = live->max_health;
        } else {
            const int g = comms::claim_of(world, a.index);
            if (g < 0 || g >= static_cast<int>(groups.size()) || world.camps[g].state != CampState::alive || real_recall(a)) continue;
            vec2 at;
            int told = -1;
            if (params::comms_ally && comms::told_ally(a.index, at, told) && told > a.pos_round && told >= world.round - ability_cooldown) pos = at;
            else if (a.pos_round < world.round - ability_cooldown || a.pos.x < 0) continue;
            if (dist(pos, groups[g].centre) > groups[g].threat_radius()) continue;
            // A sighting older than a cooldown says little of its health now.
            if (a.pos_round >= world.round - ability_cooldown) since = world.round - a.pos_round;
            else health = max_health;
        }
        if (max_health <= 0 || !in_bounds(pos) || test(world.map().ally_spawn, pos)) continue;
        const int d = dist(here, pos);
        if (d > horizon) continue;
        const int walk = std::max(0, d - range), lands = std::max(walk, cooldown);
        float fire = ally_camp_fire(world, a, pos);
        // Working its claim wakes it: count the fire its members in reach will give it there.
        if (const int g = comms::claim_of(world, a.index); g >= 0 && g < static_cast<int>(groups.size())
                                                            && world.camps[g].state == CampState::alive && world.camps[g].awake != Awake::awake) {
            float claimed = 0;
            for (std::size_t i = 0; i < groups[g].members.size(); ++i) {
                const auto& m = groups[g].members[i];
                if (world.camps[g].health[i] > 0 && m.strength > 0 && dist(pos, m.pos) <= m.reach) claimed += m.strength;
            }
            fire = std::max(fire, claimed * a.camp_taken);
        }
        const float at_heal = health - fire * static_cast<float>(since + lands);
        const bool urgent = a.visible && lands == 0 && gate.urgent(a, pos, health);
        // Below the line it goes home (or falls) before the heal lands.
        if (!urgent && at_heal <= params::safe_recall_health_fraction * max_health) continue;
        const float gain = std::min(amount, max_health - std::max(0.0f, at_heal));
        if (!worth_healing(amount, gain, std::max(0.0f, at_heal) / max_health)) continue;
        const float net = heal_value(world, a, pos, gain, max_health) - static_cast<float>(walk);
        if (!urgent && net <= 0) continue;
        if (!best.ally || urgent > best.urgent || (urgent == best.urgent && net > best.net)) best = {&a, pos, net, urgent};
    }
    return best;
}

// With no fight to join and the mate not needing us (mate_needs_support): the heal now if one is
// worth it, then a hold in heal range of the best target out of every camp's fire, hitting only
// what support may hit, or a step towards such a tile. False when no heal is worth our walk: the
// support formation, the crowd and the farm take the turn.
bool willow_medic(World& world, Pathing& pathing, Safety& safety, Memory& memory) {
    const auto& f = world.me().facts();
    if (!f.heals() || stunned_turn || !my_can_move()) return false;
    const int slot = f.slot_of(AbilityKind::heal);
    if (slot < 0) return false;
    const vec2 here = my_position();
    const int range = f.abilities[slot].range();
    const float amount = my_heal(slot);
    const int cooldown = my_can_cast() ? my_cooldown(slot) : ability_cooldown;
    auto target = medic_target(world, safety, here, range, amount, cooldown);
    if (!target.ally) return false;
    world.throw_if_stale();
    guard_steps(world, pathing, safety);
    bool healed = false;
    if (cooldown == 0) {
        healed = heal_ally(world, safety);
        if (healed) {
            // The walk is still ours: towards the next heal, else to the rest of the turn.
            target = medic_target(world, safety, here, range, amount, ability_cooldown);
            if (!target.ally) return false;
        }
    }
    const int walk = std::max(0, dist(here, target.pos) - range), left = healed ? ability_cooldown : cooldown;
    const int work = comms::claim_of(world, target.ally->index);
    debug_block({
        std::printf("MED %d %u t%u d%d cd%d net%.1f u%d healed%d\n", world.round, my_handle(),
                    static_cast<std::uint32_t>(target.ally->handle), dist(here, target.pos), left, target.net, target.urgent, healed);
    });
    if (walk == 0) {
        // Holding in reach of the heal: off camp tiles (a respawn waits for them, a hold's payout is
        // split), an enemy's likely hit and every awake camp's fire (a sleeping member does not wake
        // for standing near it). While the heal cools, only if we hit something from here; else the
        // turn is the formation's, the crowd's or the farm's. A told tile out of sight is off by a cell.
        if (!target.ally->visible || test(world.map().camp_tiles, here) || station(world, safety, here, 0, false).risk.enemy
            || test(safety.camp_area(), here))
            return false;
        if (!stationary_support_output(world, work) && left > 0) return false;
        // Our claim would count us in a crew we are not working.
        drop_claim(memory);
        decision = Branch::willow_support;
        return true;
    }
    // Out early only for a heal back within the walk, or one that may save a life now.
    if (!target.urgent && left > walk) return false;
    static bitboard goals{cambc::uninitialized};
    copy_into(within(world.map().open_for_us, target.pos, range), goals);
    drop(goals, world.map().camp_tiles);
    static bitboard fire_free{cambc::uninitialized};
    copy_into(goals, fire_free);
    drop(fire_free, safety.camp_area());
    const bitboard& to = board_empty(fire_free) ? goals : fire_free;
    if (board_empty(to)) return false;
    // Each step ends a turn: off camp tiles and awake camps' fire on the way, unless no route keeps off them.
    static bitboard avoid{cambc::uninitialized};
    or_into(world.map().camp_tiles, safety.camp_area(), avoid);
    world.throw_if_stale();
    const int cap = 2 * (range + ability_cooldown);
    if (!pathing.step_towards(to, &avoid, cap) && !pathing.step_towards(to, nullptr, cap)) return false;
    drop_claim(memory);
    see_revealed(world, pathing, safety);
    if (!healed) heal_ally(world, safety);
    decision = Branch::willow_support;
    return true;
}

// The heal a visible Willow brings us soon, as health we may count on: camps only (none while an
// enemy may reach us), within one cooldown (her cooldown, or her walk into heal range), what it can
// restore of our missing health and the camp fire here until it lands, while that fire leaves us
// above our recall line. Only for the ally she heals first, by one order every ally reads the same:
// the most missing health, then the nearest her, then the lowest index; none while her mate is in
// danger, which binds her to it. Memoised for the turn's tile, health and vision.
float medic_credit(const World& world, Safety& safety) {
    const auto& self = world.me();
    if (!self.alive || self.facts().heals()) return 0;
    const vec2 here = my_position();
    const float health = my_health(), max_health = my_max_health();
    static struct {
        int round = -1;
        std::uint32_t observations = 0;
        vec2 p{-1, -1};
        float health = -1, max_health = -1, credit = 0;
    } memo;
    if (memo.round == world.round && memo.observations == world.observations && memo.p == here && memo.health == health
        && memo.max_health == max_health)
        return memo.credit;
    float credit = 0;
    const float missing = max_health - health;
    int bound = -1;
    for (const auto& w : world.allies) {
        if (test(world.map().ally_spawn, here)) break;
        if (w.is_self || !w.alive || !w.facts().heals() || !w.visible || !w.can_act(world.round) || w.stun_pending) continue;
        const auto* live = visible_record(w.handle);
        if (!live) continue;
        const auto state = cambc::champion_state::from_bits_retain(live->state);
        const vec2 at{live->x, live->y};
        const float focus = live->focus;
        if (state.contains(cambc::champion_state::submitting_gems) || state.contains(cambc::champion_state::teleporting)
            || (state.contains(cambc::champion_state::recalling) && kept_recall(w.handle, w.recall_turns())))
            continue;
        const int slot = w.facts().slot_of(AbilityKind::heal);
        if (slot < 0) continue;
        std::int32_t cooldown = 0;
        ok(cambc::detail::sdk_champion_cooldown(static_cast<std::uint32_t>(w.handle), slot, &cooldown));
        const int range = w.facts().abilities[slot].range();
        const auto lands_on = [&](vec2 p) { return std::max<int>(cooldown, std::max(0, dist(at, p) - range)); };
        const int lands = lands_on(here), d = dist(at, here);
        if (lands > ability_cooldown) continue;
        // A mate's danger binds only a healer that could otherwise bring us a heal.
        if (bound < 0) {
            const auto* mate = support_endpoint(world, false);
            bound = mate && mate != &self && mate_in_danger(world, *mate);
        }
        if (bound) break;
        bool first = true;
        for (const auto& o : world.allies) {
            if (o.is_self || !o.alive || !o.visible || o.facts().heals() || test(world.map().ally_spawn, o.pos) || lands_on(o.pos) > ability_cooldown
                || o.recall_kept)
                continue;
            const float m = o.max_health - o.health;
            const int od = dist(at, o.pos);
            if (m > missing || (m == missing && (od < d || (od == d && o.index < self.index)))) { first = false; break; }
        }
        if (!first) continue;
        const float line = recall_line(world, safety);
        if (line > params::safe_recall_health_fraction) break;
        const float fire = safety.camp_damage(here);
        if (health - fire * static_cast<float>(lands + 1) <= line * max_health) continue;
        const float gain = std::min(w.facts().abilities[slot].multiplier * focus, missing + fire * static_cast<float>(lands));
        credit = std::max(credit, gain);
    }
    memo = {world.round, world.observations, here, health, max_health, credit};
    return credit;
}

float medic_credit_now(const World& world) { return hold_safety ? medic_credit(world, *hold_safety) : 0.0f; }

// Work the support formation must not interrupt: a capture, a bag to bank, a trip to shop.
bool support_work(const World& world, Pathing& pathing, Safety& safety, const Memory& memory) {
    return holding_capture(world, pathing) || contesting(world)
           || banks_bag(world, pathing) || wants_shop(world, pathing, safety, memory);
}

// The most turns Prism holds a recovery in a row, and Willow a formation; hers keep counting
// through turns the mate is out of sight (tuned).
constexpr int support_turns = 4;

void drop_claim(Memory& memory) {
    memory.claim = -1;
    memory.crew = false;
    memory.siege = false;
}

// One pass over our tile and its neighbours, for either side of the pair. Willow (neither wanting
// home nor at work: decide) holds a formation in heal view of its mate; Prism (or Tavi) waits in
// Willow's view to be healed rather than recall: a recovery. True when it took the turn.
bool local_support(World& world, Pathing& pathing, Safety& safety, Memory& memory, bool leave, bool& mate_eligible) {
    mate_eligible = false;
    const bool willow = support_healer(world.me());
    const bool prism = support_protected(world, world.me());
    if ((!willow && !prism) || stunned_turn) return false;
    std::optional<bool> protects;
    const auto protected_work = [&] {
        if (!protects) protects = prism && support_work(world, pathing, safety, memory);
        return *protects;
    };
    const auto* mate = support_endpoint(world, !willow);
    const vec2 here = my_position();
    const float health = my_health();
    const auto abandon_recovery = [&] {
        if (prism && memory.recovery_start >= 0) {
            close_recovery(memory, health);
            support_retreat = !recovered_for_work(world, safety, memory);
        }
        return false;
    };
    if (!world.me().alive || world.me().respawned_round == world.round || memory.round < 0) {
        close_recovery(memory, -1);
        memory.formation_start = -1;
        memory.formation_turns = 0;
    } else if (memory.round != world.round - 1) {
        close_recovery(memory, health);
        memory.formation_start = world.round - support_turns;
        memory.formation_turns = support_turns;
    }
    if (prism && memory.recovery_reentry) {
        if (memory.recovery_closed_group < 0 || memory.farm_group != memory.recovery_closed_group
            || test(world.map().ally_spawn, here) || recovered_for_work(world, safety, memory))
            memory.recovery_reentry = false;
        else {
            if (leave || !holding_capture(world, pathing)) support_retreat = true;
            return false;
        }
    }
    if (prism && memory.farm_group != memory.recovery_closed_group) memory.recovery_closed_health = -1;
    if (!mate || !mate->alive || !mate->visible || !mate->can_act(world.round) || !visible_record(mate->handle)) {
        abandon_recovery();
        memory.formation_start = -1;
        return false;
    }
    const bool observed_channel = mate->channel == Channel::tribute || mate->channel == Channel::teleport
                                  || (mate->channel == Channel::recall
                                      && kept_recall(mate->handle, mate->recall_turns()));
    mate_eligible = !observed_channel;
    if (observed_channel || protected_work() || test(world.map().ally_spawn, here)) {
        if (memory.recovery_start >= 0) close_recovery(memory, health);
        if (prism && observed_channel && !protected_work()) support_retreat = !recovered_for_work(world, safety, memory);
        return false;
    }

    std::array<HealView, 8> views;
    int view_count = 0;
    float amount = 0;
    const auto& healer = willow ? world.me() : *mate;
    const bool ready = heal_ready(world, healer, amount);
    if (willow && ready) view_count = heal_views(world, safety, here, amount, views);
    Reach::Window formation_view;
    if (prism) {
        if (memory.recovery_start >= 0 && (health > memory.recovery_health || !ready)) {
            close_recovery(memory, health);
            support_retreat = !recovered_for_work(world, safety, memory);
            return false;
        }
        const float gain = std::min(amount, my_max_health() - health);
        if (!ready || !worth_healing(amount, gain, health / my_max_health()) || !support_exposure(world, safety, mate->pos).safe())
            return abandon_recovery();
        if (memory.recovery_start < 0 && memory.recovery_closed_health >= 0 && health >= memory.recovery_closed_health) return false;
        // Willow must see us. In a bush her own cluster is clear to her as well: the tiles that see her
        // stand in for what she sees. Her ward's sight counts too, when we see it.
        const int range = std::clamp(heal_range(healer), 0, Reach::Window::radius);
        formation_view = test(world.map().bushes, mate->pos) ? attack_viewers(world, mate->pos, range)
                                                              : seen_from(world, mate->pos, range);
        if (const auto* sight = ward_sight(world, static_cast<std::uint32_t>(mate->handle)))
            formation_view |= board_window(world, *sight, mate->pos) & window_square(range);
        const float usable = my_max_health() * (1 - params::recall_health_fraction);
        const float out = static_cast<float>(world.map().from_ally_spawn().at(here));
        const float saved = gain / usable * heal_trip(world, out, out);
        const int detour = support_view(formation_view, mate->pos, here) ? 0 : 1;
        const int wait = mate->acted ? 1 : 0;
        if (!leave && saved <= static_cast<float>(detour + wait + 1)) return false;
        // At most one recovery turn a round: recovery_turns never outgrows the rounds since its start.
        if (memory.recovery_start >= 0 && world.round - memory.recovery_start >= support_turns) {
            close_recovery(memory, health);
            support_retreat = !recovered_for_work(world, safety, memory);
            return false;
        }
    }
    const auto here_risk = support_exposure(world, safety, here);
    const int work = willow ? comms::claim_of(world, mate->index) : memory.farm_group;
    // Willow staying on a group Prism holds alone splits its payout: the formation only steps off it.
    const int here_group = world.map().group_at(here);
    const bitboard* held = willow && here_group >= 0 && world.camps[here_group].state == CampState::cleared
                              ? prism_hold_seen(world, true) : nullptr;
    const bool on_held = held && test(*held, here);
    if (willow && !ready && here_risk.safe() && !on_held && stationary_support_output(world, work)) {
        support_owned = true;
        drop_claim(memory);
        memory.formation_start = -1;
        memory.formation_turns = 0;
        decision = Branch::willow_support;
        return true;
    }
    if (willow) formation_view = heal_viewers(world, mate->pos, heal_range(healer));
    const Field* work_route = nullptr;
    if (willow && !ready && work >= 0 && work < static_cast<int>(world.map().groups.size())
        && memory.farm_group == work && pathing.approach_ready(work, walk_range(world, work)))
        work_route = pathing.approach(work, walk_range(world, work));
    const bool formation_expired = memory.formation_turns >= support_turns
                                   || (memory.formation_start >= 0 && world.round - memory.formation_start >= support_turns);
    const bool active_clear = willow && memory.claim >= 0 && memory.claim == memory.farm_group
                              && memory.claim < static_cast<int>(world.camps.size())
                              && world.camps[memory.claim].state == CampState::alive
                              && world.camps[memory.claim].awake != Awake::asleep;
    const auto& blocked = pathing.blocked();
    const bool can_step = my_can_move();
    vec2 best = here;
    int best_gap = unreachable, best_home = unreachable;
    const HealTarget* best_target = nullptr;
    const auto heal_mate_now = heal_mate(world);
    bool found = false;
    for (int k = -1; k < 8; ++k) {
        const vec2 p = k < 0 ? here : here + directions[k];
        if (!in_bounds(p) || (p != here && (!can_step || !test(world.map().open_for_us, p) || test(blocked, p)))) continue;
        const int camp = world.map().group_at(p);
        if (willow && (p != here || on_held) && camp >= 0 && world.camps[camp].state == CampState::cleared) continue;
        const bool in_range = support_view(formation_view, mate->pos, p);
        const int gap = in_range ? 0 : dist(p, mate->pos);
        if (prism) {
            if (!in_range || (p == here && memory.recovery_turns > 0 && !comms::support_available(world))) continue;
        }
        int target = -1;
        for (int t = 0; t < view_count; ++t) {
            const auto& v = views[t].target;
            if (!support_view(views[t].viewers, v.pos, p)) continue;
            if (target < 0 || heal_before(v, views[target].target, heal_mate_now)) target = t;
        }
        const HealTarget* chosen = target >= 0 ? &views[target].target : nullptr;
        const float gain = chosen ? chosen->gain : 0;
        if (willow && !ready) {
            if (p == here || !work_route || work_route->at(p) >= work_route->at(here)
                || (!in_range && dist(p, mate->pos) >= dist(here, mate->pos))) continue;
        } else if (willow && gain <= 0 && (active_clear || formation_expired
                                          || (!in_range && dist(p, mate->pos) >= dist(here, mate->pos)))) continue;
        // A tile that cannot win the formation's ranking needs no safety query.
        const bool better = chosen && (!best_target || heal_before(*chosen, *best_target, heal_mate_now));
        const bool tie = chosen ? best_target && !heal_before(*best_target, *chosen, heal_mate_now) : !best_target;
        int home = -1;
        if (found && !better) {
            if (!tie || gap > best_gap || (gap == best_gap && best == here)) continue;
            if (gap == best_gap) {
                home = pathing.to_ally_spawn().at(p);
                if (home >= best_home) continue;
            }
        }
        if (!(p == here ? here_risk : support_exposure(world, safety, p)).safe()) continue;
        if (home < 0) home = pathing.to_ally_spawn().at(p);
        found = true, best = p, best_target = chosen, best_gap = gap, best_home = home;
    }
    if (!found) return abandon_recovery();
    const auto commit_support = [&] {
        support_owned = true;
        if (prism) {
            if (memory.recovery_start < 0) memory.recovery_start = world.round, memory.recovery_group = memory.farm_group;
            ++memory.recovery_turns;
            memory.recovery_health = health;
        } else {
            drop_claim(memory);
            if (memory.formation_start < 0) memory.formation_start = world.round;
            ++memory.formation_turns;
        }
    };
    bool healed_before = false;
    if (best != here) {
        if (willow && !here_risk.safe()) healed_before = heal_ally(world, safety);
        world.throw_if_stale();
        if (!pathing.try_move(best)) {
            see_again(world, pathing, safety);
            abandon_recovery();
            support_retreat = support_retreat || !support_exposure(world, safety, my_position()).safe();
            return false;
        }
        commit_support();
        see_revealed(world, pathing, safety);
        if (!(willow ? exposure_here(world, safety) : support_exposure(world, safety, my_position())).safe()) {
            // The heal we stepped for costs no walk; healed_before means the cast is spent.
            if (willow && !healed_before) heal_ally(world, safety);
            memory.claim = -1;
            memory.crew = false;
            if (prism) close_recovery(memory, health);
            return true;
        }
    } else commit_support();
    world.throw_if_stale();
    if (prism) {
        support_requested = true;
        decision = Branch::prism_recovery;
        // Waiting in place spends no walk, and the tile is out of every reach: a basic attack is free,
        // where a cast would spend a cooldown. Only camps whose whole group cannot strike back.
        if (best == here && !attack_enemy(world) && my_can_attack())
            attack_camp(world, [&](int g) { return world.map().groups[g].strength <= 0; });
        return true;
    }
    bool productive = healed_before || heal_ally(world, safety);
    // Staying chose a safe tile.
    if (best == here) {
        productive |= attack_enemy(world);
        if (my_can_attack()) productive |= attack_support_camp(world, work) >= 0;
    }
    const bool route_progress = best != here && (work_route ? work_route->at(best) < work_route->at(here)
                                : work >= 0 && work < static_cast<int>(world.map().groups.size())
                                  && memory.farm_group == work
                                  && dist(best, world.map().groups[work].centre) < dist(here, world.map().groups[work].centre));
    if (productive || route_progress) memory.formation_start = -1, memory.formation_turns = 0;
    float offered = 0;
    support_offered = heal_ready(world, world.me(), offered) && exposure_here(world, safety).safe();
    decision = Branch::willow_support;
    return true;
}

} // namespace

} // namespace aph
