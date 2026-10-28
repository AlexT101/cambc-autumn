// Willow's support of its protected mate (Prism, or Tavi on 3-pick maps without one): exposure, heal
// stations and views, and both sides of the pair's local support.
#include "../bot_parts.h"

namespace aph {

namespace {

Stations& stations_cache() {
    static Stations s;
    return s;
}

// Each camp member whose strike reaches p, as f(group, member index, member), in groups_near order;
// stops at the first f that returns false.
template <class F>
bool each_camp_striker(const World& world, vec2 p, F&& f) {
    for (const int g : world.map().groups_near(p, world.map().max_camp_reach)) {
        const auto& members = world.map().groups[g].members;
        for (std::size_t i = 0; i < members.size(); ++i)
            if (members[i].strength > 0 && dist(p, members[i].pos) <= members[i].reach && !f(g, i, members[i])) return false;
    }
    return true;
}

// Willow holds no fight: a tile an enemy is likely to hit (want_home's test) or any camp member may
// hit is unsafe. `enemies`: false when no enemy can hit p, which spares their search.
SupportExposure exposure_at(const World& world, Safety& safety, vec2 p, bool enemies = true) {
    SupportExposure risk;
    if (enemies) {
        const auto b = safety.bound(p, world.me().taken);
        risk.damage = b.damage, risk.imminent = b.doubled, risk.enemy = b.threat, risk.stun = b.stuns;
    } else {
        risk.damage = risk.imminent = safety.camp_damage(p, true, true);
    }
    each_camp_striker(world, p, [&](int g, std::size_t i, const CampMember&) {
        const auto& c = world.camps[g];
        const bool returning = c.state == CampState::respawning && c.respawn_round <= world.round + 1;
        // Asleep members and ones a nearer ally draws count too: the group can wake, and the ally leave.
        risk.camp = returning || (c.state == CampState::alive && c.health[i] > 0);
        return !risk.camp;
    });
    return risk;
}

// Worked out on first need after we move or see again. Its guard board stays at one address: a
// guard Pathing holds reads the latest.
const Stations& stations(const World& world, Safety& safety, vec2 here) {
    auto& s = stations_cache();
    if (s.observations == world.observations && s.origin == here) return s;
    world.throw_if_stale();
    // Keyed only once complete: a read that throws part-way leaves nothing to reuse.
    s.origin = {-1, -1};
    clear_board(s.guard);
    const bool enemies = safety.credible_enemy_may_hit_within(here, 1);
    for (int k = 0; k < 9; ++k) {
        auto& tile = s.tiles[k];
        tile.p = k == 0 ? here : here + directions[k - 1];
        tile.open = in_bounds(tile.p) && test(world.map().open_for_us, tile.p);
        // Ranged threats shadowcast from the candidate; an opaque origin is invalid.
        tile.risk = tile.open ? exposure_at(world, safety, tile.p, enemies) : SupportExposure{};
        if (tile.risk.enemy) set_tile(s.guard, tile.p);
    }
    world.throw_if_stale();
    s.observations = world.observations;
    s.origin = here;
    return s;
}

// stations(here).tiles[0].risk alone, for when no step or guard read follows this turn: after
// Willow's walk, or at the turn's end.
SupportExposure exposure_here(const World& world, Safety& safety) {
    const vec2 here = my_position();
    if (const auto& s = stations_cache(); s.observations == world.observations && s.origin == here) return s.tiles[0].risk;
    static struct {
        std::uint32_t observations = 0;
        vec2 p{-1, -1};
        SupportExposure risk;
    } memo;
    if (memo.observations != world.observations || memo.p != here) {
        const bool open = in_bounds(here) && test(world.map().open_for_us, here);
        memo.risk = open ? exposure_at(world, safety, here, safety.credible_enemy_may_hit_within(here, 1)) : SupportExposure{};
        memo.observations = world.observations, memo.p = here;
    }
    return memo.risk;
}

// Ours, or a free open tile a step reaches.
bool station_legal(Pathing& pathing, const Station& tile, vec2 here) {
    return tile.open && (tile.p == here || (my_can_move() && !test(pathing.blocked(), tile.p)));
}

SupportExposure support_exposure(const World& world, Safety& safety, vec2 p) {
    if (const vec2 here = my_position(); world.me().facts().heals() && dist(p, here) <= 1)
        for (const auto& tile : stations(world, safety, here).tiles)
            if (tile.p == p) return tile.risk;
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

const ChampionBelief* support_endpoint(const World& world, bool healer) {
    for (const auto& a : world.allies)
        if (healer ? support_healer(a) : support_protected(world, a)) return &a;
    return nullptr;
}

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
    const float damage = shielded_clear(camp_hit_factor() * min_camp_damage(world, g, camp_output(world.me()), &rounds), rounds,
                                        self_shield_amount(world.me()));
    return params::camp_risk * damage <= health - params::recall_health_fraction * my_max_health();
}

int heal_range(const ChampionBelief& healer) {
    const auto& f = healer.facts();
    return f.abilities[f.slot_of(AbilityKind::heal)].range();
}

// A unit our own ward sees stays visible to us wherever we step (wards.vision). Read per call: a
// ward can go down mid-turn without a re-observe (submit_here); its mask is cast again only when it moves.
bool own_ward_sees(const World& world, vec2 p) {
    static bitboard sight{cambc::uninitialized};
    static vec2 cast_at{-1, -1};
    static std::array<cambc::detail::ward_info, 16> raw;
    std::uint32_t k = 0;
    ok(cambc::detail::sdk_wards(raw.data(), static_cast<std::uint32_t>(raw.size()), &k));
    const auto own = static_cast<std::uint32_t>(world.map().team_a ? 0 : 1);
    for (std::uint32_t i = 0; i < k && i < raw.size(); ++i) {
        const auto& w = raw[i];
        if (w.team != own || w.owner != my_handle() || w.disabled) continue;
        if (const vec2 at{w.x, w.y}; at != cast_at) ok(cambc::detail::sdk_ward_vision(at.x, at.y, sight.ptr())), cast_at = at;
        return test(sight, p);
    }
    return false;
}

// Tiles within `range` of a visible ally from which we would see it, as a window around it:
// attack_viewers, plus our own tile, which sees it now even from a bush beyond a step; every tile
// when our ward sees it.
Reach::Window heal_viewers(const World& world, vec2 target, int range) {
    range = std::clamp(range, 0, Reach::Window::radius);
    Reach::Window w;
    if (own_ward_sees(world, target)) {
        for (int y = -range; y <= range; ++y)
            for (int x = -range; x <= range; ++x) w |= Reach::Window::bit(Reach::Window::at(x, y));
        return w;
    }
    w = attack_viewers(world, target, range);
    if (const vec2 here = my_position(); dist(here, target) <= range)
        w |= Reach::Window::bit(Reach::Window::at(here.x - target.x, here.y - target.y));
    return w;
}

struct HealView {
    HealTarget target;
    Reach::Window viewers; // tiles that see it within heal range
};

// heal_target's allies within a step of our heal range of p.
int heal_views(const World& world, vec2 p, float amount, std::array<HealView, 8>& out) {
    const int range = heal_range(world.me());
    int n = 0;
    for (const auto& a : world.allies)
        if (dist(p, a.pos) <= range + 1)
            if (const auto t = heal_target(world, a, amount)) out[n++] = {*t, heal_viewers(world, t->pos, range)};
    return n;
}

// One is in heal range of p: heal_ally casts from there without a step.
bool heal_lands_from(const World& world, vec2 p, const std::array<HealView, 8>& views, int n) {
    const int range = heal_range(world.me());
    for (int t = 0; t < n; ++t)
        if (dist(p, views[t].target.pos) <= range) return true;
    return false;
}

// The neighbouring station `ok` accepts from which a heal lands best: the most restored, then on
// the lowest ally, then the least `cost`. `here` if none.
template <class Ok, class Cost>
vec2 heal_station(const World& world, Pathing& pathing, Safety& safety, vec2 here, const std::array<HealView, 8>& views,
                  int n, Ok&& ok, Cost&& cost) {
    vec2 best = here;
    float best_gain = 0, best_fraction = 0;
    int best_cost = unreachable;
    const auto& tiles = stations(world, safety, here).tiles;
    for (int k = 1; k < 9; ++k) {
        const auto& tile = tiles[k];
        if (!station_legal(pathing, tile, here) || !ok(tile)) continue;
        const int g = world.map().group_at(tile.p);
        if (g >= 0 && world.camps[g].state == CampState::cleared) continue;
        const int c = cost(tile);
        for (int t = 0; t < n; ++t) {
            const auto& target = views[t].target;
            if (!support_view(views[t].viewers, target.pos, tile.p)) continue;
            if (target.gain != best_gain ? target.gain > best_gain
                : target.fraction != best_fraction ? target.fraction < best_fraction : c < best_cost)
                best = tile.p, best_gain = target.gain, best_fraction = target.fraction, best_cost = c;
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
    const int n = heal_views(world, here, amount, views);
    if (n == 0 || heal_lands_from(world, here, views, n)) return false;
    world.throw_if_stale();
    guard_steps(world, pathing, safety);
    if (!stations(world, safety, here).tiles[0].risk.safe()) return false;
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
    heal_ally(world);
    return true;
}

bool immediate_camp_finish(const World& world, vec2 here, float basic) {
    const int range = world.me().facts().attack_range();
    for (const int g : world.map().groups_near(here, range)) {
        const auto& c = world.camps[g];
        const auto& members = world.map().groups[g].members;
        for (std::size_t i = 0; i < members.size(); ++i) {
            if (dist(here, members[i].pos) > range || !test(world.visible, members[i].pos)) continue;
            if (c.state_round != world.round) return true;
            if (c.state != CampState::alive) continue;
            // Any member two basics may finish (as if the reset were ready), or whose health is unread.
            if (c.health_round[i] != world.round) return true;
            if (c.health[i] > 0 && c.health[i] <= 2 * basic) return true;
        }
    }
    return false;
}

bool willow_independent_heal_step(World& world, Pathing& pathing, Safety& safety) {
    if (stunned_turn || !my_can_move()) return false;
    const vec2 here = my_position();
    if (test(world.map().ally_spawn, here)) return false;
    float amount = 0;
    if (!heal_ready(world, world.me(), amount)) return false;
    guard_steps(world, pathing, safety);
    const auto quiet = [](const SupportExposure& risk) {
        return risk.safe() && !risk.stun && risk.imminent == 0;
    };
    std::array<HealView, 8> views;
    int n = heal_views(world, here, amount, views);
    if (n == 0 || heal_lands_from(world, here, views, n)) return false;
    // The basics the step gives up: a ranged walk spends the attack and the heal takes the turn's
    // cast, so with a camp in reach the attack and the ready reset's; and a possible return step's.
    const auto& f = world.me().facts();
    const int reset = f.slot_of(AbilityKind::attack_reset);
    const bool reset_ready = reset >= 0 && world.me().ability_ready(reset, world.round) && my_cooldown(reset) == 0;
    const int forgone = 1 + (any_within(live_camp_tiles(), here, f.attack_range()) ? 1 + reset_ready : 0);
    const float basic = my_strength() * camp_dealt_factor();
    n = static_cast<int>(std::remove_if(views.begin(), views.begin() + n,
                                        [&](const HealView& v) { return !(v.target.gain > forgone * basic); }) - views.begin());
    if (n == 0 || immediate_camp_finish(world, here, basic)) return false;
    if (!quiet(stations(world, safety, here).tiles[0].risk)) return false;
    const vec2 best = heal_station(world, pathing, safety, here, views, n, [&](const Station& tile) { return quiet(tile.risk); },
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
    const bool healed = heal_ally(world);
    debug_block({ std::printf("WIH-DONE %d %u moved 1 healed %d\n", world.round,
        static_cast<std::uint32_t>(world.me().handle), healed); });
    decision = 'h';
    return true;
}

// Work the support formation must not interrupt: a capture, a bag to bank, a trip to shop.
bool support_work(const World& world, Pathing& pathing, Safety& safety, const Memory& memory) {
    return holding_capture(world, pathing) || contesting(world)
           || (bankable_bag(world, pathing) > 0 && !retaining_gems(world, pathing)) || wants_shop(world, pathing, safety, memory);
}

// The most turns Willow holds a formation, and Prism a recovery, in a row (tuned).
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
    if (willow && ready) view_count = heal_views(world, here, amount, views);
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
        formation_view = attack_viewers(world, mate->pos, heal_range(healer));
        const float usable = my_max_health() * (1 - params::recall_health_fraction);
        const float out = static_cast<float>(world.map().from_ally_spawn().at(here));
        const float saved = gain / usable * (static_cast<float>(recall_turns(world)) + out);
        const int detour = support_view(formation_view, mate->pos, here) ? 0 : 1;
        const int wait = mate->acted ? 1 : 0;
        if (!leave && saved <= static_cast<float>(detour + wait + 1)) return false;
        // At most one recovery turn a round: recovery_turns never outgrows the rounds since its start.
        if (memory.recovery_start >= 0 && world.round - memory.recovery_start >= support_turns) {
            close_recovery(memory, health);
            support_retreat = !recovered_for_work(world, safety, memory);
            return false;
        }
    } else {
        formation_view = heal_viewers(world, mate->pos, heal_range(healer));
    }
    const auto here_risk = support_exposure(world, safety, here);
    const int work = willow ? comms::claim_of(world, mate->index) : memory.farm_group;
    if (willow && !ready && here_risk.safe() && stationary_support_output(world, work)) {
        support_owned = true;
        drop_claim(memory);
        memory.formation_start = -1;
        memory.formation_turns = 0;
        decision = 'h';
        return true;
    }
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
    float best_gain = -1;
    bool found = false;
    for (int k = -1; k < 8; ++k) {
        const vec2 p = k < 0 ? here : here + directions[k];
        if (!in_bounds(p) || (p != here && (!can_step || !test(world.map().standable, p) || test(blocked, p)))) continue;
        const int camp = world.map().group_at(p);
        if (willow && p != here && camp >= 0 && world.camps[camp].state == CampState::cleared) continue;
        const bool in_range = support_view(formation_view, mate->pos, p);
        const int gap = in_range ? 0 : dist(p, mate->pos);
        if (prism) {
            if (!in_range || (p == here && memory.recovery_turns > 0 && !comms::support_available(world))) continue;
        }
        int target = -1;
        for (int t = 0; t < view_count; ++t) {
            const auto& v = views[t].target;
            if (!support_view(views[t].viewers, v.pos, p)) continue;
            const auto* chosen = target >= 0 ? &views[target].target : nullptr;
            if (!chosen || (v.gain != chosen->gain ? v.gain > chosen->gain
                            : v.fraction != chosen->fraction ? v.fraction < chosen->fraction
                            : v.ally == mate && comms::support_request(world)))
                target = t;
        }
        const float gain = target >= 0 ? views[target].target.gain : 0;
        if (willow && !ready) {
            if (p == here || !work_route || work_route->at(p) >= work_route->at(here)
                || (!in_range && dist(p, mate->pos) >= dist(here, mate->pos))) continue;
        } else if (willow && gain <= 0 && (active_clear || formation_expired
                                          || (!in_range && dist(p, mate->pos) >= dist(here, mate->pos)))) continue;
        if (!(p == here ? here_risk : support_exposure(world, safety, p)).safe()) continue;
        const int home = dist(p, world.map().ally_spawn_centre);
        // Staying, tried first, keeps ties; between steps, the one nearer home wins.
        if (!found || gain > best_gain || (gain == best_gain && gap < best_gap)
            || (gain == best_gain && gap == best_gap && best != here && home < best_home))
            found = true, best = p, best_gain = gain, best_gap = gap, best_home = home;
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
        if (willow && !here_risk.safe()) healed_before = heal_ally(world);
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
            if (willow && !healed_before) heal_ally(world);
            memory.claim = -1;
            memory.crew = false;
            if (prism) close_recovery(memory, health);
            return true;
        }
    } else commit_support();
    world.throw_if_stale();
    if (prism) {
        support_requested = true;
        decision = 'r';
        // Waiting in place spends no walk, and the tile is out of every reach: a basic attack is free,
        // where a cast would spend a cooldown. Only camps whose whole group cannot strike back.
        if (best == here && !attack_enemy(world) && my_can_attack())
            attack_camp(world, [&](int g) { return world.map().groups[g].strength <= 0; });
        return true;
    }
    bool productive = healed_before || heal_ally(world);
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
    decision = 'h';
    return true;
}

} // namespace

} // namespace aph
