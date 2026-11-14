// Function bodies; src/unity.cpp includes this after every header.

namespace aph::claims {
const std::uint16_t* centre_steps(const World& world, int g)
{
    auto& table = _centre_steps[static_cast<std::size_t>(g)];
    if (!table) {
        const Field* field = _pathing->from_centre(g);
        if (!field) return nullptr;
        const auto tiles = static_cast<std::size_t>(world.map().width * world.map().height);
        table.reset(new std::uint16_t[tiles]); // not zeroed: the copy fills it
        field->steps.export_linear_buffer(std::span<std::uint16_t>(table.get(), tiles));
    }
    return table.get();
}

void work_out(const World& world)
{
    if (_round == world.round) return;
    _round = world.round;
    _claim.fill(-1);
    if constexpr (!enabled) return;
    const auto& groups = world.map().groups;
    const int n = static_cast<int>(groups.size()), padded = (n + 7) & ~7, width = world.map().width;
    if (n == 0) return;
    const bool walking = _pathing && _pathing->centres_ready();
    // Field tables by group, null for a group without one (no reward: never claimable).
    static std::vector<const std::uint16_t*> tables;
    if (walking && tables.empty()) {
        _centre_steps.resize(static_cast<std::size_t>(n));
        tables.resize(static_cast<std::size_t>(n));
        for (int g = 0; g < n; ++g) tables[static_cast<std::size_t>(g)] = centre_steps(world, g);
    }
    // Rows before the fields are ready: as the crow flies, worked out each round (scratch per ally).
    static std::vector<std::uint16_t> crow;
    // A row's place in crow or _rows (built rows only grow _rows: places stay valid, pointers may not).
    const auto row = [&](int i, vec2 p) -> std::size_t {
        if (!walking) {
            crow.resize(static_cast<std::size_t>(8 * padded));
            std::uint16_t* out = crow.data() + i * padded;
            for (int g = 0; g < padded; ++g) out[g] = g < n ? static_cast<std::uint16_t>(dist(p, groups[g].centre)) : 0xffff;
            return static_cast<std::size_t>(i * padded);
        }
        auto& at = _row_at[static_cast<std::size_t>(p.y * width + p.x)];
        if (at == 0) {
            at = static_cast<std::uint32_t>(_rows.size()) + 1;
            _rows.resize(_rows.size() + static_cast<std::size_t>(padded));
            std::uint16_t* out = _rows.data() + (at - 1);
            const int tile = p.y * width + p.x;
            for (int g = 0; g < n; ++g) {
                const std::uint16_t* table = tables[static_cast<std::size_t>(g)];
                const int d = table ? table[tile] : unreachable;
                out[g] = static_cast<std::uint16_t>(d != unreachable ? d : (table ? 32768 : 0) + dist(p, groups[g].centre));
            }
            for (int g = n; g < padded; ++g) out[g] = 0xffff;
        }
        return static_cast<std::size_t>(at - 1);
    };
    std::array<int, 8> who;
    int k = 0;
    for (const auto& a : world.allies)
        if (placed(world, a)) who[k++] = a.index;
    if (k == 0) return;
    std::array<std::size_t, 8> place;
    for (int i = 0; i < k; ++i) place[i] = row(i, world.allies[who[i]].pos);
    const std::uint16_t* base = walking ? _rows.data() : crow.data();
    std::array<const std::uint16_t*, 8> steps;
    for (int i = 0; i < k; ++i) steps[i] = base + place[i];
    // Per group the nearest ally and whether another is as near, eight groups at a time; then each ally's
    // nearest group it owns, ties to the lower group.
    std::array<int, 8> best_steps;
    best_steps.fill(1 << 30);
    alignas(16) std::uint16_t nearest[8], owner[8];
    for (int g0 = 0; g0 < padded; g0 += 8) {
        v128_t m = wasm_v128_load(steps[0] + g0), own = wasm_i16x8_splat(0), tie = wasm_i16x8_splat(0);
        for (int i = 1; i < k; ++i) {
            const v128_t d = wasm_v128_load(steps[i] + g0);
            const v128_t lt = wasm_u16x8_lt(d, m), eq = wasm_i16x8_eq(d, m);
            tie = wasm_v128_or(wasm_v128_andnot(tie, lt), eq);
            own = wasm_v128_bitselect(wasm_i16x8_splat(static_cast<std::int16_t>(i)), own, lt);
            m = wasm_u16x8_min(m, d);
        }
        std::uint32_t lanes = ~wasm_i16x8_bitmask(tie) & 0xffu;
        if (g0 + 8 > n) lanes &= (1u << (n - g0)) - 1;
        if (!lanes) continue;
        wasm_v128_store(nearest, m), wasm_v128_store(owner, own);
        for (; lanes; lanes &= lanes - 1) {
            const int l = __builtin_ctz(lanes), g = g0 + l, o = owner[l];
            if (nearest[l] >= best_steps[o] || !claimable(world, g)) continue;
            best_steps[o] = nearest[l], _claim[who[o]] = g;
        }
    }
}

}
