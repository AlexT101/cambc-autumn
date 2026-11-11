// A singleton has no healing target or choice of weakest member. Keep the same
// hit order and float operations, without maintaining team targeting caches.
std::pair<int, int> simulate_duel(Side& us, Side& them, bool they_first, bool* self_falls, int horizon, bool* lost_unknown) {
    auto& u = us.fighters[0];
    auto& e = them.fighters[0];
    const bool watched = self_falls && us.self == 0;
    const auto hurt = [](Fighter& f, float damage) __attribute__((always_inline)) {
        if (damage <= 0 || f.health <= 0) return;
        float d = damage * f.taken;
        if (f.shield == 0 && d < f.health) { f.health -= d; return; }
        if (f.shield != 0) {
            const float absorbed = std::min(d, f.shield);
            f.shield -= absorbed;
            d -= absorbed;
        }
        f.health -= std::min(d, f.health);
    };
    int ours = 0, theirs = 0;
    for (int t = 0; t < 2 * horizon; ++t) {
        if (t % 8 == 7) throw_if_stale();
        const bool their_turn = (t % 2 == 0) == they_first;
        Side& side = their_turn ? them : us;
        Side& other = their_turn ? us : them;
        Fighter& f = their_turn ? e : u;
        Fighter& target = their_turn ? u : e;
        const int turn = side.turn++;
        if (!side.plain && f.shield_until <= turn) f.shield = 0, f.shield_until = never;
        const bool skipped = side.stunned > 0 && !f.stun_immune;
        side.stunned = 0;
        float damage = 0;
        int hits = 0;
        if (f.arrives_at <= turn && !skipped) {
            damage = f.strength;
            hits = 1;
            if (f.next_cast <= turn)
                for (const int s : f.kit->preference) {
                    const auto& c = f.kit->cast[s];
                    if (f.ready_at[s] > turn || c.heals_ally) continue;
                    f.ready_at[s] = turn + ability_cooldown;
                    f.next_cast = next_cast(f);
                    other.stunned += c.stuns;
                    if (c.heals_self) f.shield = c.heal, f.shield_until = turn + c.duration;
                    damage += c.damage;
                    hits = c.hits;
                    break;
                }
        }
        hurt(target, damage);
        if (target.retaliation > 0 && hits > 0) hurt(f, static_cast<float>(hits) * target.retaliation);
        if (their_turn) {
            if (us.camp > 0) hurt(u, us.camp);
            ++theirs;
        } else ++ours;
        if (watched && u.health <= 0) {
            *self_falls = true;
            if (e.health > 0) return {0, std::max(1, theirs)};
            if (lost_unknown) { *lost_unknown = true; return {0, 0}; }
        }
        if (u.health <= 0) return {0, std::max(1, theirs)};
        if (e.health <= 0) return {std::max(1, ours), 0};
    }
    return {0, 0};
}
