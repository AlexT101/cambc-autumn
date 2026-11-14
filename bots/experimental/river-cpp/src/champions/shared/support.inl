// Function bodies; src/unity.cpp includes this after every header.

namespace aph {
namespace {
bool SupportExposure::safe() const
{ return !enemy && !camp; }

Stations& stations_cache()
{
    static Stations s;
    return s;
}

SupportExposure exposure_at(const World& world, Safety& safety, vec2 p, bool enemies)
{
    SupportExposure risk;
    if (enemies) {
        const auto b = safety.bound(p);
        risk.damage = b.damage, risk.imminent = b.doubled, risk.enemy = b.threat, risk.stun = b.stuns;
    } else {
        risk.damage = risk.imminent = safety.camp_damage(p, true, true);
    }
    each_camp_striker(world, p, [&](int g, std::size_t i, const CampMember&) {
        const auto& c = world.camps[g];
        const bool returning = c.state == CampState::respawning && c.respawn_round <= world.round + 1;
        // Asleep too: a tank may leave before the next camp phase, and no ally's protection is borrowed.
        risk.camp = returning || (c.state == CampState::alive && c.health[i] > 0);
        return !risk.camp;
    });
    return risk;
}

const Stations& stations(const World& world, Safety& safety, vec2 here)
{
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

SupportExposure exposure_here(const World& world, Safety& safety)
{
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

bool station_legal(Pathing& pathing, const Station& tile, vec2 here)
{
    return tile.open && (tile.p == here || (my_can_move() && !test(pathing.blocked(), tile.p)));
}

SupportExposure support_exposure(const World& world, Safety& safety, vec2 p)
{
    if (const vec2 here = my_position(); world.me().type == cambc::champion_type::willow && dist(p, here) <= 1)
        for (const auto& tile : stations(world, safety, here).tiles)
            if (tile.p == p) return tile.risk;
    return exposure_at(world, safety, p);
}

bool stationary_support_output(const World& world, int work)
{
    world.throw_if_stale();
    bool hit = attack_enemy(world);
    int camp = -1;
    if (!hit && my_can_attack())
        camp = attack_camp(world, [&](int g) {
            return world.map().groups[g].strength <= 0 || (g == work && world.camps[g].awake != Awake::asleep);
        });
    hit |= camp >= 0;
    if (hit && my_cooldown(0) > 0) {
        if (camp >= 0) reset_and_attack_camp(world, camp);
        else reset_and_attack_enemy(world);
    }
    return hit;
}

bool support_view(Reach::Window viewers, vec2 target, vec2 p)
{
    const int x = p.x - target.x, y = p.y - target.y;
    return std::abs(x) <= 4 && std::abs(y) <= 4
           && static_cast<bool>(viewers & Reach::Window::bit(9 * (y + 4) + x + 4));
}

const ChampionBelief* support_endpoint(const World& world, cambc::champion_type type)
{
    for (const auto& a : world.allies)
        if (a.type == type) return &a;
    return nullptr;
}

bool recovered_for_work(const World& world, Safety& safety, const Aims& aims)
{
    const float health = my_health();
    if (health <= safety.damage_bound(my_position(), true)) return false;
    const int g = aims.farm_group;
    if (g < 0 || g >= static_cast<int>(world.camps.size()) || world.camps[g].state != CampState::alive) return true;
    float rounds = 0;
    const float damage = camp_hit_factor() * min_camp_damage(world, g, floored_output(world.me()), &rounds);
    return params::camp_risk * damage <= health - params::recall_health_fraction * my_max_health();
}

int heal_range(const ChampionBelief& healer)
{
    const auto& f = healer.facts();
    return f.abilities[f.slot_of(AbilityKind::heal)].range();
}

bool own_ward_sees(const World& world, vec2 p)
{
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

Reach::Window heal_viewers(const World& world, vec2 target, int range)
{
    range = std::clamp(range, 0, 4); // the window's radius
    Reach::Window w;
    if (own_ward_sees(world, target)) {
        for (int y = -range; y <= range; ++y)
            for (int x = -range; x <= range; ++x) w |= Reach::Window::bit(9 * (y + 4) + x + 4);
        return w;
    }
    w = attack_viewers(world, target, range);
    if (const vec2 here = my_position(); dist(here, target) <= range)
        w |= Reach::Window::bit(9 * (here.y - target.y + 4) + here.x - target.x + 4);
    return w;
}

int heal_views(const World& world, vec2 p, float amount, std::array<HealView, 8>& out)
{
    const int range = heal_range(world.me());
    int n = 0;
    for (const auto& a : world.allies)
        if (dist(p, a.pos) <= range + 1)
            if (const auto t = heal_target(world, a, amount)) out[n++] = {*t, heal_viewers(world, t->pos, range)};
    return n;
}

bool heal_lands_from(const World& world, vec2 p, const std::array<HealView, 8>& views, int n)
{
    for (int t = 0; t < n; ++t)
        if (dist(p, views[t].target.pos) <= heal_range(world.me())) return true;
    return false;
}

bool willow_bank_heal_step(World& world, Pathing& pathing, Safety& safety, const Field& field)
{
    if (world.me().type != cambc::champion_type::willow || !my_can_move() || winning_bag(world)
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
    const vec2 best = heal_station(world, pathing, safety, here, views, n, [&](const Station& tile) {
        const int steps = field.at(tile.p);
        return tile.risk.safe() && steps != unreachable && steps <= here_steps;
    }, [&](const Station& tile) { return field.at(tile.p); });
    world.throw_if_stale();
    if (best == here) return false;
    // Equal-distance banking may spend one progress turn for a heal available after this step.
    if (!pathing.try_move(best)) {
        see_again(world, pathing, safety); // a hidden unit refused it, unseen by see_revealed
        world.throw_if_stale();
        return false;
    }
    see_revealed(world, pathing, safety);
    heal_ally(world);
    return true;
}

bool immediate_camp_finish(const World& world, vec2 here, float basic)
{
    const int range = world.me().facts().attack_range();
    for (const int g : world.map().groups_near(here, range)) {
        const auto& c = world.camps[g];
        const auto& members = world.map().groups[g].members;
        for (std::size_t i = 0; i < members.size(); ++i) {
            if (dist(here, members[i].pos) > range || !test(world.visible, members[i].pos)) continue;
            if (c.state_round != world.round) return true;
            if (c.state != CampState::alive) continue;
            // Preserve even an individual member finish, with a ready-reset upper bound.
            if (c.health_round[i] != world.round) return true;
            if (!(c.health[i] > 0)) continue; // dead: nothing left to finish
            if (c.health[i] <= 2 * basic) return true;
        }
    }
    return false;
}

bool willow_independent_heal_step(World& world, Pathing& pathing, Safety& safety)
{
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
    // Two present basics and a possible return step's basic, even when reset is cooling down.
    const float basic = my_strength() * (has_family(my_items(), monster) ? 1.15f : 1.0f);
    n = static_cast<int>(std::remove_if(views.begin(), views.begin() + n,
                                        [&](const HealView& v) { return !(v.target.gain > 3 * basic); }) - views.begin());
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

bool support_work(const World& world, Pathing& pathing, Safety& safety, const Aims& aims)
{
    return holding_capture(world, pathing) || contesting(world)
           || (bankable_bag(world, pathing) > 0 && !retaining_gems(world, pathing)) || wants_shop(world, pathing, safety, aims);
}

bool local_support(World& world, Pathing& pathing, Safety& safety, Aims& aims, bool leave, bool& mate_eligible)
{
    mate_eligible = false;
    const bool willow = world.me().type == cambc::champion_type::willow;
    const bool prism = world.me().type == cambc::champion_type::prism;
    if ((!willow && !prism) || stunned_turn) return false;
    std::optional<bool> protects;
    const auto protected_work = [&] {
        if (!protects) protects = prism && support_work(world, pathing, safety, aims);
        return *protects;
    };
    const auto* mate = support_endpoint(world, willow ? cambc::champion_type::prism : cambc::champion_type::willow);
    const vec2 here = my_position();
    const float health = my_health();
    // Each turn decides afresh (nothing is kept): a Prism recovers while a heal is worth its walk.
    if (!world.me().alive) return false;
    if (!mate || !mate->alive || !mate->visible || !mate->can_act(world.round) || !visible_record(mate->handle)) return false;
    const bool observed_channel = mate->channel == Channel::tribute || mate->channel == Channel::teleport
                                  || (mate->channel == Channel::recall
                                      && kept_recall(mate->handle, mate->fast_recall ? home_recall_time
                                                                                 : static_cast<int>(cambc::constants::recall_time)));
    mate_eligible = !observed_channel;
    if (observed_channel || protected_work() || test(world.map().ally_spawn, here)) {
        if (prism && observed_channel && !protected_work()) support_retreat = !recovered_for_work(world, safety, aims);
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
        const float gain = std::min(amount, my_max_health() - health);
        if (!ready || !worth_healing(amount, gain, health / my_max_health()) || !support_exposure(world, safety, mate->pos).safe())
            return false;
        formation_view = attack_viewers(world, mate->pos, heal_range(healer));
        const float usable = my_max_health() * (1 - params::recall_health_fraction);
        const float out = static_cast<float>(world.map().from_ally_spawn().at(here));
        const float saved = gain / usable * (static_cast<float>(recall_turns(world)) + out);
        const int detour = support_view(formation_view, mate->pos, here) ? 0 : 1;
        const int wait = mate->acted ? 1 : 0;
        if (!leave && saved <= static_cast<float>(detour + wait + 1)) return false;
    } else {
        formation_view = heal_viewers(world, mate->pos, heal_range(healer));
    }
    const auto here_risk = support_exposure(world, safety, here);
    const int work = willow ? claims::of(world, mate->index) : aims.farm_group;
    if (willow && !ready && here_risk.safe() && stationary_support_output(world, work)) {
        support_owned = true;
        aims.claim = -1;
        aims.crew = false;
        aims.siege = false;
        decision = 'h';
        return true;
    }
    const Field* work_route = nullptr;
    if (willow && !ready && work >= 0 && work < static_cast<int>(world.map().groups.size())
        && aims.farm_group == work && pathing.approach_ready(work, walk_range(world, work)))
        work_route = pathing.approach(work, walk_range(world, work));
    // Formation (staying in reach of the Prism with nothing to heal) only while it may need a heal.
    const bool formation_expired = mate->health >= mate->max_health;
    const bool active_clear = willow && aims.claim >= 0 && aims.claim == aims.farm_group
                              && aims.claim < static_cast<int>(world.camps.size())
                              && world.camps[aims.claim].state == CampState::alive
                              && world.camps[aims.claim].awake != Awake::asleep;
    const auto& blocked = pathing.blocked();
    vec2 best = here;
    int best_gap = unreachable, best_home = unreachable;
    float best_gain = -1;
    bool found = false;
    for (int k = -1; k < 8; ++k) {
        const vec2 p = k < 0 ? here : here + directions[k];
        if (!in_bounds(p) || (p != here && (!my_can_move() || !test(world.map().standable, p) || test(blocked, p)))) continue;
        const int camp = world.map().group_at(p);
        if (willow && p != here && camp >= 0 && world.camps[camp].state == CampState::cleared) continue;
        const bool in_range = support_view(formation_view, mate->pos, p);
        const int gap = in_range ? 0 : dist(p, mate->pos);
        if (prism) {
            if (!in_range) continue;
        }
        int target = -1;
        for (int t = 0; t < view_count; ++t) {
            const auto& v = views[t].target;
            if (!support_view(views[t].viewers, v.pos, p)) continue;
            const auto* best = target >= 0 ? &views[target].target : nullptr;
            if (!best || v.gain > best->gain || (v.gain == best->gain && v.fraction < best->fraction)
                || (v.gain == best->gain && v.fraction == best->fraction && v.ally == mate && comms::support_request(world)))
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
        if (!found || gain > best_gain || (gain == best_gain && gap < best_gap)
            || (gain == best_gain && gap == best_gap && (p == here || (best != here && home < best_home))))
            found = true, best = p, best_gain = gain, best_gap = gap, best_home = home;
    }
    if (!found) return false;
    const auto commit_support = [&] {
        support_owned = true;
        if (!prism) {
            aims.claim = -1;
            aims.crew = false;
            aims.siege = false;
        }
    };
    bool healed_before = false;
    if (best != here) {
        if (willow && !here_risk.safe()) healed_before = heal_ally(world);
        world.throw_if_stale();
        if (!pathing.try_move(best)) {
            see_again(world, pathing, safety);
            support_retreat = support_retreat || !support_exposure(world, safety, my_position()).safe();
            return false;
        }
        commit_support();
        see_revealed(world, pathing, safety);
        if (!(willow ? exposure_here(world, safety) : support_exposure(world, safety, my_position())).safe()) {
            // The heal we stepped for costs no walk; healed_before means the cast is spent.
            if (willow && !healed_before) heal_ally(world);
            support_owned = true;
            aims.claim = -1;
            aims.crew = false;
            return true;
        }
    } else commit_support();
    world.throw_if_stale();
    support_owned = true;
    if (prism) {
        support_requested = true;
        decision = 'r';
        // Waiting in place spends no walk, and the tile is out of every reach: a basic attack is free.
        // Casts keep their cooldowns for the search. Only camps whose whole group cannot strike back.
        if (best == here && !attack_enemy(world) && my_can_attack())
            attack_camp(world, [&](int g) { return world.map().groups[g].strength <= 0; });
        return true;
    }
    aims.claim = -1;
    aims.crew = false;
    aims.siege = false;
    bool productive = heal_ally(world) || healed_before;
    if (best == here && support_exposure(world, safety, my_position()).safe()) {
        productive |= attack_enemy(world);
        if (my_can_attack())
            productive |= attack_camp(world, [&](int g) {
                return world.map().groups[g].strength <= 0
                       || (g == work && world.camps[g].awake != Awake::asleep);
            }) >= 0;
    }
    (void)productive;
    float offered = 0;
    support_offered = heal_ready(world, world.me(), offered) && exposure_here(world, safety).safe();
    decision = 'h';
    return true;
}

}
}
