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
        if (const int i = allies.claiming[static_cast<std::size_t>(k)]; allies.at[static_cast<std::size_t>(i)].seen && allies.at[static_cast<std::size_t>(i)].claim == g)
            bits |= 1u << i;
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
    const int mine = crew_arrival(world, world.me(), g, allies.here);
    const auto in_time = [&](const CrewAllies::Ally& a) {
        const auto& b = *a.a;
        if (!b.is_self && (b.visible || in_bounds(b.pos)) && crew_arrival(world, b, g, b.pos) > mine + 2) return false;
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

