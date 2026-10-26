#include "draft.h"
#include <algorithm>
#include <array>
#include <cstring>
#include <span>
#include <vector>
#include "params.h"
#include "util.h"
#include "world.h"

namespace aph {

namespace {

int draft_round() { return static_cast<int>(cambc::round_number()); }

constexpr auto all_champions() {
    std::array<cambc::champion_draft, static_cast<std::size_t>(cambc::champion_draft::heart_of_ruin) + 1> all{};
    for (std::size_t i = 0; i < all.size(); ++i) all[i] = static_cast<cambc::champion_draft>(i);
    return all;
}

// A rejected pick does not spend the turn, so trying the next candidate is always safe.
bool pick_first_available(DraftState& state, std::span<const cambc::champion_draft> order) {
    const auto ours = cambc::draft::current_draft(team::ally);
    for (const auto pick : order) {
        if (std::find(ours.begin(), ours.end(), pick) != ours.end()) continue;
        try {
            cambc::draft::pick(pick);
            state.picked_round = draft_round();
            return true;
        } catch (const cambc::error&) {
        }
    }
    return false;
}

// The static map analysis every champion would repeat, carried over draft turns while fuel lasts.
// A draft turn keeps `draft_reserve` for the plan's write and the pick.
constexpr std::uint64_t draft_reserve = 40000;

struct Analysis {
    std::unique_ptr<StaticMap> map;
    std::vector<std::array<std::uint16_t, 3>> steps; // per group: from our spawn, theirs, the altars
    std::vector<std::array<std::uint16_t, DraftPlan::max_spawn_tiles>> spawn_steps; // per group, per ally spawn tile
    int fields = 0; // of those 3 and the spawn tiles', done
    int attack_group = 0, attack_member = 0;
    int attack_index = 0, attack_at = 0; // members done; the next bush bit's place in the plan
    int attack_start = 0;                // the attack tiles' first bit
    bool done = false;
};

Analysis& analysis() {
    static Analysis a;
    return a;
}

void set_steps(const StaticMap& map, const Field& field, int which, Analysis& a) {
    for (std::size_t g = 0; g < map.groups.size(); ++g) {
        const auto steps = static_cast<std::uint16_t>(field.at(map.groups[g].centre));
        if (which < 3) a.steps[g][which] = steps;
        else a.spawn_steps[g][which - 3] = steps;
    }
}

std::uint32_t zigzag(int v) { return v >= 0 ? 2u * static_cast<std::uint32_t>(v) : 2u * static_cast<std::uint32_t>(-v) - 1; }
int unzigzag(std::uint32_t z) { return z & 1 ? -static_cast<int>((z + 1) / 2) : static_cast<int>(z / 2); }

vec2 mirror(const StaticMap& map, vec2 p) {
    switch (map.symmetry) {
    case cambc::symmetry::horizontal: return {map.width - 1 - p.x, p.y};
    case cambc::symmetry::vertical: return {p.x, map.height - 1 - p.y};
    default: return {map.width - 1 - p.x, map.height - 1 - p.y};
    }
}

// The group entries; false if they do not fit or would not decode to these steps.
bool write_steps(const StaticMap& map, Analysis& a, int spawn_fields, DraftPlan& plan, PlanHeader& header) {
    const int n = static_cast<int>(map.groups.size());
    const auto ally = TileBox::of(map.ally_spawn_tiles), enemy = TileBox::of(map.enemy_spawn.positions());
    header.mirrored = true;
    for (int g = 0; g < n && header.mirrored; ++g) header.mirrored = map.group_at(mirror(map, map.groups[g].centre)) >= 0;
    std::array<std::vector<std::uint32_t>, 3> codes;
    for (int which = 0; which < 3; ++which) {
        for (int g = 0; g < n; ++g) {
            if (which == 1 && header.mirrored) {
                const int m = map.group_at(mirror(map, map.groups[g].centre));
                codes[which].push_back(zigzag(a.steps[g][1] - a.steps[m][0]));
                continue;
            }
            const int steps = a.steps[g][which], bound = steps_bound(ally, enemy, map.groups[g].centre, which);
            if (steps != unreachable && steps < bound) return false;
            codes[which].push_back(steps == unreachable ? 0 : static_cast<std::uint32_t>(steps - bound + 1));
        }
        int best = 1 << 30;
        for (int k = 0; k <= PlanHeader::max_rice; ++k) {
            int bits = 0;
            for (const auto c : codes[which]) bits += PlanWriter::rice_bits(c, k);
            if (bits < best) best = bits, header.rice[which] = static_cast<std::uint8_t>(k);
        }
    }
    PlanWriter w{plan, PlanHeader::bits};
    for (int which = 0; which < 3; ++which)
        for (const auto c : codes[which])
            if (!w.put_rice(c, header.rice[which])) return false;
    bool offsets_fit = spawn_fields > 0;
    std::vector<std::uint32_t> offsets(n);
    for (int g = 0; g < n && offsets_fit; ++g)
        for (int i = 0; offsets_fit && i < spawn_fields; ++i) {
            const int base = a.steps[g][0], steps = a.spawn_steps[g][i];
            const int over = base == unreachable ? 0 : steps - base;
            offsets_fit = over >= 0 && over <= 3 && (base != unreachable || steps == unreachable);
            offsets[g] |= static_cast<std::uint32_t>(over) << (2 * i);
        }
    header.spawn_offsets = offsets_fit;
    const auto offset = [&](const DraftSteps& d, int g, int i) {
        return d.predicted[g] ? static_cast<std::uint32_t>(spawn_offset(ally, map.ally_spawn_tiles[i], map.groups[g].centre))
                              : d.offsets[g] >> (2 * i) & 3;
    };
    for (int g = 0; g < n && offsets_fit; ++g) {
        if (a.steps[g][0] == unreachable) continue;
        bool predicted = true;
        for (int i = 0; i < spawn_fields; ++i)
            predicted &= (offsets[g] >> (2 * i) & 3) == static_cast<std::uint32_t>(spawn_offset(ally, map.ally_spawn_tiles[i], map.groups[g].centre));
        if (!w.put(predicted, 1) || (!predicted && !w.put(offsets[g], 2 * spawn_fields))) return false;
    }
    DraftSteps check;
    if (!decode_steps(plan, header, map, check) || check.end != w.at()) return false;
    for (int g = 0; g < n; ++g) {
        if (check.ally[g] != a.steps[g][0] || check.enemy[g] != a.steps[g][1] || check.altar[g] != a.steps[g][2]) return false;
        if (!header.spawn_offsets || check.ally[g] == unreachable) continue;
        for (int i = 0; i < spawn_fields; ++i)
            if (check.ally[g] + offset(check, g, i) != a.spawn_steps[g][i]) return false;
    }
    a.attack_start = w.at();
    return true;
}

// One member's attack tiles; false, writing nothing, if they do not fit or champions could not
// decode them.
bool write_attack_tiles(const StaticMap& map, vec2 p, Analysis& a, DraftPlan& plan) {
    static std::array<bitboard, DraftPlan::attack_ranges.size()> tiles{};
    static bitboard off{cambc::uninitialized};
    for (std::size_t k = 0; k < tiles.size(); ++k) {
        const int r = DraftPlan::attack_ranges[k];
        tiles[k] = map.viewers(p, r);
        tiles[k] &= map.open_for_us;
        copy_into(tiles[k], off);
        drop(off, map.open_bushes());
        if (!boards_equal(off, map.sight_off_bushes(p, r))) return false;
    }
    // Bits go only over bush_range's square; each range's bush tiles must be those within it.
    const auto& sent = tiles[0];
    bool any = false, exact = true;
    int bits = 0;
    each_in_square(map.open_bushes(), p, DraftPlan::bush_range, [&](vec2 t) {
        ++bits;
        const bool in = test(sent, t);
        any = any || in;
        for (std::size_t k = 1; k < tiles.size(); ++k)
            if (dist(t, p) <= DraftPlan::attack_ranges[k]) exact = exact && test(tiles[k], t) == in;
    });
    if (!exact) return false;
    PlanWriter w{plan, a.attack_at};
    if (!w.fits(any ? bits : 0)) return false;
    if (any) {
        PlanWriter{plan, a.attack_start + a.attack_index}.put(1, 1);
        each_in_square(map.open_bushes(), p, DraftPlan::bush_range, [&](vec2 t) { w.put(test(sent, t), 1); });
    }
    a.attack_at = w.at();
    ++a.attack_index;
    return true;
}

// Each part checks its fuel first; a part not done is retried next draft turn.
void analyse(DraftState& state) {
    auto& plan = state.plan;
    auto& header = state.header;
    auto& a = analysis();
    const auto afford = [](std::uint64_t cost) { return fuel_ok(draft_reserve + cost); };
    if (a.done) return;
    if (!a.map) {
        if (!afford(150000)) return;
        a.map = StaticMap::build();
        const auto groups = a.map->groups.size();
        const auto spawn = a.map->ally_spawn_tiles.size();
        if (groups > 255 || spawn == 0) {
            a.done = true;
            return;
        }
        a.steps.resize(groups);
        a.spawn_steps.resize(spawn <= DraftPlan::max_spawn_tiles ? groups : 0);
        header.check = plan_check(*a.map);
    }
    const auto& map = *a.map;
    const int spawn_fields = a.spawn_steps.empty() ? 0 : static_cast<int>(map.ally_spawn_tiles.size());
    for (; a.fields < 3 + spawn_fields; ++a.fields) {
        if (!afford(2 * field_cost_estimate())) return;
        if (a.fields == 0) set_steps(map, map.from_ally_spawn(), 0, a);
        else if (a.fields == 1) set_steps(map, map.from_enemy_spawn(), 1, a);
        else if (a.fields == 2) {
            bitboard goals;
            for (const auto& altar : map.altars) goals |= altar.tribute_tiles();
            set_steps(map, make_field(map.blocked_for_us, goals), 2, a);
        } else {
            set_steps(map, make_field(map.blocked_for_us, single(map.ally_spawn_tiles[a.fields - 3])), a.fields, a);
        }
    }
    if (!header.steps) {
        if (!write_steps(map, a, spawn_fields, plan, header)) {
            a.done = true;
            return;
        }
        a.attack_at = a.attack_start;
        for (const auto& group : map.groups) a.attack_at += static_cast<int>(group.members.size()); // the flags
        header.steps = true;
    }
    for (; a.attack_group < static_cast<int>(map.groups.size()); ++a.attack_group, a.attack_member = 0) {
        const auto& members = map.groups[a.attack_group].members;
        for (; a.attack_member < static_cast<int>(members.size()); ++a.attack_member) {
            const vec2 p = members[a.attack_member].pos;
            if (!afford(20000) || !map.find_bush_clusters(p, DraftPlan::attack_ranges[0], draft_reserve + 20000)) return;
            if (!write_attack_tiles(map, p, a, plan)) {
                a.done = true;
                return;
            }
        }
        header.attack_groups = static_cast<std::uint8_t>(a.attack_group + 1);
    }
    a.done = true;
}

} // namespace

int spawn_offset(const TileBox& spawn, vec2 tile, vec2 centre) { return std::clamp(dist(tile, centre) - spawn.dist(centre), 0, 3); }

bool decode_steps(const DraftPlan& plan, const PlanHeader& header, const StaticMap& map, DraftSteps& out) {
    const int n = static_cast<int>(map.groups.size());
    const auto ally = TileBox::of(map.ally_spawn_tiles);
    const auto enemy = header.mirrored ? TileBox{} : TileBox::of(map.enemy_spawn.positions());
    out.spawn = ally;
    PlanReader bits{plan, PlanHeader::bits};
    const auto read = [&](std::vector<std::uint16_t>& steps, int which) {
        steps.resize(n);
        for (int g = 0; g < n; ++g) {
            const auto c = bits.get_rice(header.rice[which]);
            steps[g] = static_cast<std::uint16_t>(c == 0 ? unreachable : c - 1 + steps_bound(ally, enemy, map.groups[g].centre, which));
        }
    };
    read(out.ally, 0);
    if (header.mirrored) {
        out.enemy.resize(n);
        for (int g = 0; g < n; ++g) {
            const int m = map.group_at(mirror(map, map.groups[g].centre));
            if (m < 0) return false;
            out.enemy[g] = static_cast<std::uint16_t>(out.ally[m] + unzigzag(bits.get_rice(header.rice[1])));
        }
    } else {
        read(out.enemy, 1);
    }
    read(out.altar, 2);
    out.offsets.assign(n, 0);
    out.predicted.assign(n, 0);
    if (header.spawn_offsets)
        for (int g = 0; g < n; ++g) {
            if (out.ally[g] == unreachable) continue;
            if (bits.get(1)) out.predicted[g] = 1;
            else out.offsets[g] = bits.get(2 * static_cast<int>(map.ally_spawn_tiles.size()));
        }
    out.end = bits.at();
    return bits.ok();
}

std::uint16_t plan_check(const StaticMap& map) {
    const vec2 spawn = map.ally_spawn_tiles[0];
    std::uint32_t h = DraftPlan::current_version;
    for (const int v : {map.width, map.height, static_cast<int>(map.groups.size()), spawn.x, spawn.y})
        h = (h ^ static_cast<std::uint32_t>(v)) * 0x9E3779B1u;
    h ^= h >> 16;
    return static_cast<std::uint16_t>(h & 0xffffu ? h : 1);
}

void PlanHeader::write(DraftPlan& plan) const {
    PlanWriter w{plan};
    w.put(check, check_bits);
    w.put(field_layers, layer_bits);
    w.put(steps, 1), w.put(mirrored, 1), w.put(spawn_offsets, 1);
    for (const auto k : rice) w.put(k, rice_bits);
    w.put(attack_groups, group_bits), w.put(distances_at, at_bits), w.put(schedule_at, at_bits);
}

PlanHeader PlanHeader::read(const DraftPlan& plan) {
    static_assert(bits <= 128);
    // Two words and constant shifts: PlanReader's window costs ~15 fuel a field.
    std::array<std::uint64_t, 2> w;
    std::memcpy(w.data(), plan.bytes.data(), sizeof w);
    int at = 0;
    const auto get = [&](int n) __attribute__((always_inline)) {
        const std::uint64_t v = at >= 64 ? w[1] >> (at - 64) : at == 0 ? w[0] : w[0] >> at | w[1] << (64 - at);
        at += n;
        return v & ((std::uint64_t{1} << n) - 1);
    };
    PlanHeader h;
    h.check = static_cast<std::uint16_t>(get(check_bits));
    h.field_layers = static_cast<std::uint16_t>(get(layer_bits));
    h.steps = get(1), h.mirrored = get(1), h.spawn_offsets = get(1);
    for (auto& k : h.rice) k = static_cast<std::uint8_t>(get(rice_bits));
    h.attack_groups = static_cast<std::uint8_t>(get(group_bits));
    h.distances_at = static_cast<std::uint16_t>(get(at_bits));
    h.schedule_at = static_cast<std::uint16_t>(get(at_bits));
    return h;
}

namespace {

// params::test_draft: the 10 most common compositions per pick count among the ladder's top 10
// teams (research/hyperion/DRAFT.md), each in its most common pick order.
namespace test_compositions {
using C = cambc::champion_draft;
constexpr C three[][3] = {
    {C::stellar, C::heart_of_ruin, C::ren},
    {C::heart_of_ruin, C::ren, C::ryth},
    {C::marcella, C::heart_of_ruin, C::stellar},
    {C::heart_of_ruin, C::vendetta, C::ren},
    {C::heart_of_ruin, C::marcella, C::vesper_vale},
    {C::heart_of_ruin, C::varg, C::stellar},
    {C::heart_of_ruin, C::marcella, C::ren},
    {C::heart_of_ruin, C::ryth, C::vesper_vale},
    {C::stellar, C::heart_of_ruin, C::cassi_and_issac},
    {C::heart_of_ruin, C::varg, C::cassi_and_issac},
};
constexpr C four[][4] = {
    {C::heart_of_ruin, C::ren, C::stellar, C::ryth},
    {C::heart_of_ruin, C::vendetta, C::ren, C::vesper_vale},
    {C::marcella, C::heart_of_ruin, C::stellar, C::ren},
    {C::stellar, C::heart_of_ruin, C::ren, C::cassi_and_issac},
    {C::heart_of_ruin, C::marcella, C::vesper_vale, C::ryth},
    {C::heart_of_ruin, C::varg, C::cassi_and_issac, C::ryth},
    {C::vesper_vale, C::cassi_and_issac, C::varg, C::stellar},
    {C::marcella, C::ryth, C::stellar, C::heart_of_ruin},
    {C::heart_of_ruin, C::ren, C::ryth, C::tavi},
    {C::marcella, C::ren, C::stellar, C::ryth},
};
constexpr C five[][5] = {
    {C::heart_of_ruin, C::ren, C::stellar, C::ryth, C::varg},
    {C::marcella, C::heart_of_ruin, C::stellar, C::ren, C::ryth},
    {C::heart_of_ruin, C::ren, C::ryth, C::stellar, C::tavi},
    {C::stellar, C::heart_of_ruin, C::ren, C::cassi_and_issac, C::ryth},
    {C::heart_of_ruin, C::marcella, C::vesper_vale, C::ryth, C::stellar},
    {C::heart_of_ruin, C::vendetta, C::ren, C::vesper_vale, C::varg},
    {C::heart_of_ruin, C::varg, C::cassi_and_issac, C::ryth, C::stellar},
    {C::stellar, C::heart_of_ruin, C::prism, C::marcella, C::ren},
    {C::stellar, C::heart_of_ruin, C::cassi_and_issac, C::marcella, C::willow},
    {C::vesper_vale, C::cassi_and_issac, C::varg, C::vendetta, C::stellar},
};

std::uint64_t mix(std::uint64_t h, std::uint64_t w) {
    h = (h ^ w) * 0x9E3779B97F4A7C15ull;
    return h ^ (h >> 29);
}

std::uint64_t mix_board(std::uint64_t h, const bitboard& board) {
    const auto words = cambc::detail::layout().board_bytes / 8;
    for (std::uint32_t i = 0; i < words; ++i) h = mix(h, board.ptr()[i]);
    return h;
}

// Both sides see the same map, so the side-swapped game repeats each side's draft.
std::uint64_t map_hash() {
    std::uint64_t h = mix(0, static_cast<std::uint64_t>(cambc::detail::sdk_my_team()));
    h = mix(h, static_cast<std::uint64_t>(cambc::map::width()) << 32 | static_cast<std::uint32_t>(cambc::map::height()));
    for (const auto* board : {&cambc::map::walls(), &cambc::map::bushes(), &cambc::map::holes(), &cambc::map::altars(),
                              &cambc::map::spawn_region(team::ally), &cambc::map::spawn_region(team::enemy)})
        h = mix_board(h, *board);
    static std::array<std::uint32_t, 4096> camps;
    std::uint32_t count{};
    cambc::detail::check(cambc::detail::sdk_map_camp_layout(camps.data(), static_cast<std::uint32_t>(camps.size()), &count));
    h = mix(h, count);
    for (std::uint32_t i = 0; i < std::min<std::uint32_t>(count, camps.size()); ++i) h = mix(h, camps[i]);
    return mix(h, 0);
}

std::span<const C> choose() {
    const auto picks = cambc::draft::team_size();
    const auto pick = [&](const auto& table) -> std::span<const C> { return table[map_hash() % std::size(table)]; };
    if (picks == 3) return pick(three);
    if (picks == 4) return pick(four);
    if (picks == 5) return pick(five);
    return params::draft_preference;
}
} // namespace test_compositions

std::span<const cambc::champion_draft> table_draft() {
    switch (cambc::draft::team_size()) {
    case 3: return params::draft_three;
    case 4: return params::draft_four;
    case 5: return params::draft_five;
    }
    return params::draft_preference;
}

// Re-read each draft round: a counter rule depends on the enemy picks seen so far.
std::vector<cambc::champion_draft> draft_order() {
    if constexpr (params::test_draft) {
        static const auto chosen = test_compositions::choose();
        return {chosen.begin(), chosen.end()};
    }
    const auto table = table_draft();
    std::vector<cambc::champion_draft> order;
    const auto picks = static_cast<int>(cambc::draft::team_size());
    const int round = draft_round();
    for (const auto& rule : params::draft_counters) {
        if (rule.picks != picks || rule.round != round) continue;
        const auto seen = cambc::draft::current_draft(team::enemy);
        if (std::find(seen.begin(), seen.end(), rule.seen) == seen.end()) continue;
        order.push_back(rule.instead);
        break;
    }
    order.insert(order.end(), table.begin(), table.end());
    return order;
}

void write_plan(DraftState& state) {
    state.header.field_layers = static_cast<std::uint16_t>(std::min(max_field_layers(), (1 << PlanHeader::layer_bits) - 1));
    state.header.write(state.plan);
    cambc::draft_memory = std::span<const std::byte>{reinterpret_cast<const std::byte*>(&state.plan), sizeof(DraftPlan)};
}

} // namespace

const DraftPlan* read_draft_plan() {
    const auto* bytes = cambc::draft_memory.data();
    if (cambc::draft_memory.size() < sizeof(DraftPlan) || reinterpret_cast<std::uintptr_t>(bytes) % alignof(DraftPlan) != 0)
        return nullptr;
    return reinterpret_cast<const DraftPlan*>(bytes);
}

void play_draft(DraftState& state) {
    // Write before picking: a pick ends the draft turn's actions (later writes fail with error 18),
    // and the draft bot may not run again after its last pick.
    draft_order(); // caches test_draft's selection before the first turn's expensive analysis
    try {
        analyse(state);
    } catch (const std::exception&) {
        analysis().done = true; // a member's tiles may be half written: only finished groups count
    }
    write_plan(state);
    pick_first_available(state, draft_order());
}

void ensure_picked(DraftState& state) {
    if (state.picked_round == draft_round()) return;
    // draft_order() may be what threw in play_draft.
    try {
        if (pick_first_available(state, draft_order())) return;
    } catch (const std::exception&) {
    }
    if (pick_first_available(state, params::draft_preference)) return;
    pick_first_available(state, all_champions());
}

} // namespace aph
