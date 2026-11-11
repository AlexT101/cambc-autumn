
namespace {

// fishcal (cal-dbg): the verdict with our side's health and max health x s.
bool cal_verdict(const Side& us0, const Side& them0, bool they_first, bool falls, float s) {
    Side us = us0, them = them0;
    for (int i = 0; i < us.count; ++i) us.fighters[i].health *= s, us.fighters[i].max_health *= s;
    us.weak = -2;
    const Trade t = trade(us, them, they_first, true, false);
    return t.lost || (falls && t.self_falls);
}

// Positive: lost, won with 2^m our health; negative: won, still won down to 2^m. Capped at +-3.
float cal_margin(const Side& us, const Side& them, bool they_first, bool falls, bool& v1) {
    v1 = cal_verdict(us, them, they_first, falls, 1);
    if (v1) {
        if (cal_verdict(us, them, they_first, falls, 8)) return 3;
        float lo = 0, hi = 3;
        for (int k = 0; k < 7; ++k) {
            const float mid = 0.5f * (lo + hi);
            (cal_verdict(us, them, they_first, falls, std::exp2(mid)) ? lo : hi) = mid;
        }
        return hi;
    }
    if (!cal_verdict(us, them, they_first, falls, 0.125f)) return -3;
    float lo = -3, hi = 0;
    for (int k = 0; k < 7; ++k) {
        const float mid = 0.5f * (lo + hi);
        (cal_verdict(us, them, they_first, falls, std::exp2(mid)) ? lo : hi) = mid;
    }
    return lo;
}

std::size_t cal_bytes = 0;
constexpr std::size_t cal_cap = 3000000;

void cal_print(const char* head, const World& world, vec2 p, const Side& us, const Side& them, std::uint32_t allies, std::uint32_t enemies,
               bool they_first, bool falls, const Trade& t, int target, int flags, float camp, float boost) {
    if (cal_bytes > cal_cap) return;
    bool v1 = false;
    const float m = cal_margin(us, them, they_first, falls, v1);
    const auto& me = world.me();
    std::array<float, 4> dealt{};
    {
        Side u = us, e = them;
        bool f = false;
        simulate<true>(u, e, they_first, &f, fight_horizon, &dealt);
    }
    int n = std::printf("%s %d %u %d %d %d %d %d %d %d %d %d %d %d %d %d %d %d %d %d %d %d %d |", head, world.round, static_cast<unsigned>(me.handle), p.x, p.y,
                        static_cast<int>(me.health), static_cast<int>(me.max_health), target, flags, static_cast<int>(falls), static_cast<int>(t.lost),
                        static_cast<int>(t.self_falls), t.turns_to_kill_us, t.turns_to_kill_them, static_cast<int>(std::lround(100 * m)),
                        static_cast<int>(v1), static_cast<int>(camp), static_cast<int>(100 * boost), static_cast<int>(they_first),
                        static_cast<int>(dealt[0]), static_cast<int>(dealt[1]), static_cast<int>(dealt[2]), static_cast<int>(dealt[3]));
    int k = 0;
    for (auto left = allies; left && k < us.count; left &= left - 1, ++k) {
        const auto& a = world.allies[static_cast<std::size_t>(std::countr_zero(left))];
        const auto& f = us.fighters[k];
        n += std::printf(" %u:%d:%d", static_cast<unsigned>(a.handle), f.arrives_at == never ? 99 : f.arrives_at, static_cast<int>(f.health));
    }
    n += std::printf(" |");
    k = 0;
    for (auto left = enemies; left && k < them.count; left &= left - 1, ++k) {
        const auto& e = world.enemies[static_cast<std::size_t>(std::countr_zero(left))];
        const auto& f = them.fighters[k];
        n += std::printf(" %u:%d:%d:%d:%d", static_cast<unsigned>(e.handle), static_cast<int>(e.visible), f.arrives_at == never ? 99 : f.arrives_at,
                         e.visible ? dist(p, e.pos) : -1, static_cast<int>(f.health));
    }
    n += std::printf("\n");
    cal_bytes += static_cast<std::size_t>(std::max(0, n));
    if (cal_bytes > cal_cap) std::printf("CAL-CAP %d %u\n", world.round, static_cast<unsigned>(me.handle));
}

} // namespace

void Safety::cal_stand(vec2 p, const StandRoster& r, bool falls, const Trade& t, int flags) {
    if (r.key == no_fight || cal_bytes > cal_cap) return;
    const auto saved = made_;
    const auto key = r.key;
    const std::uint32_t enemies = (key >> 16 & threat_mask_) | r.walking;
    Side us, them;
    fill(us, world_, world_.allies, key & 0xFFFFu, made_);
    fill(them, world_, world_.enemies, enemies, made_);
    int k = 0;
    for (auto left = enemies; left && k < them.count; left &= left - 1, ++k)
        if (const int i = std::countr_zero(left); r.walking >> i & 1) them.fighters[k].arrives_at = r.walks[static_cast<std::size_t>(i)];
    walk_allies_in(world_, us, key & 0xFFFFu, enemies);
    us.camp = r.camp / world_.me().taken;
    cal_print("CS", world_, p, us, them, key & 0xFFFFu, enemies, (key >> 16) != 0, falls, t, -1, flags, r.camp, 0);
    made_ = saved;
}

void Safety::cal_chase(vec2 p, std::uint32_t key, std::uint32_t delayed, const std::array<int, 2>& self_cooldowns, bool can_cast, bool falls,
                       std::uint32_t late, float boost, const Trade& t, int target, int flags) {
    if (key == no_fight || cal_bytes > cal_cap) return;
    const auto saved = made_;
    Side us, them;
    fill(us, world_, world_.allies, key & 0xFFFFu, made_);
    int at = 0;
    for (auto left = key & 0xFFFFu; left && at < us.count; left &= left - 1, ++at) {
        const int i = std::countr_zero(left);
        auto& f = us.fighters[at];
        if ((delayed >> i & 1) && f.arrives_at < 1) f.arrives_at = 1;
        if (!world_.allies[static_cast<std::size_t>(i)].is_self) continue;
        for (int s = 0; s < 2; ++s) f.ready_at[s] = f.kit->cast[s].value <= 0 ? never : std::max(can_cast ? 0 : 1, self_cooldowns[s]);
        f.next_cast = next_cast(f);
    }
    const auto enemies = (key >> 16 | late_mask(late)) & threat_mask_;
    fill(them, world_, world_.enemies, enemies, made_);
    if (late) join_late(them, enemies, late);
    walk_allies_in(world_, us, key & 0xFFFFu, enemies);
    cal_print("CC", world_, p, us, them, key & 0xFFFFu, enemies, true, falls, t, target, flags, 0, boost);
    made_ = saved;
}
