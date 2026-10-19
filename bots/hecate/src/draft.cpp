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
    std::array<cambc::champion_draft, static_cast<std::size_t>(cambc::champion_draft::tavi) + 1> all{};
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
    int attack_group = 0, attack_member = 0, attack_bit = 0;
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

// Each part checks its fuel first; a part not done is retried next draft turn.
void analyse(DraftPlan& plan) {
    auto& a = analysis();
    const auto afford = [](std::uint64_t cost) { return fuel_ok(draft_reserve + cost); };
    if (a.done) return;
    if (!a.map) {
        if (!afford(150000)) return;
        a.map = StaticMap::build();
        const auto groups = a.map->groups.size();
        const auto spawn = a.map->ally_spawn_tiles.size();
        if (groups > 255 || groups * DraftPlan::group_bytes > plan.data.size() || spawn == 0) {
            a.done = true;
            return;
        }
        a.steps.resize(groups);
        a.spawn_steps.resize(spawn <= DraftPlan::max_spawn_tiles ? groups : 0);
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
    if (!plan.steps) {
        plan.width = static_cast<std::uint8_t>(map.width);
        plan.height = static_cast<std::uint8_t>(map.height);
        plan.groups = static_cast<std::uint8_t>(map.groups.size());
        plan.spawn_x = static_cast<std::uint8_t>(map.ally_spawn_tiles[0].x);
        plan.spawn_y = static_cast<std::uint8_t>(map.ally_spawn_tiles[0].y);
        bool offsets_fit = spawn_fields > 0;
        for (std::size_t g = 0; g < map.groups.size(); ++g) {
            auto* entry = plan.data.data() + g * DraftPlan::group_bytes;
            std::memcpy(entry, a.steps[g].data(), 3 * sizeof(std::uint16_t));
            for (int i = 0; offsets_fit && i < spawn_fields; ++i) {
                const int base = a.steps[g][0], steps = a.spawn_steps[g][i];
                const int over = base == unreachable ? 0 : steps - base;
                offsets_fit = over >= 0 && over <= 3 && (base != unreachable || steps == unreachable);
                if (offsets_fit) entry[6 + i / 4] |= static_cast<std::uint8_t>(over << (2 * (i % 4)));
            }
        }
        plan.spawn_tiles = static_cast<std::uint8_t>(offsets_fit ? spawn_fields : 0);
        a.attack_bit = static_cast<int>(map.groups.size()) * DraftPlan::group_bytes * 8;
        plan.steps = 1;
    }
    const auto stride = cambc::detail::layout().chunk_stride;
    const int capacity = static_cast<int>(plan.data.size()) * 8;
    for (; a.attack_group < static_cast<int>(map.groups.size()); ++a.attack_group, a.attack_member = 0) {
        const auto& members = map.groups[a.attack_group].members;
        if (a.attack_member == 0 && a.attack_bit + static_cast<int>(members.size()) * DraftPlan::member_bits > capacity) break;
        for (; a.attack_member < static_cast<int>(members.size()); ++a.attack_member) {
            const vec2 p = members[a.attack_member].pos;
            if (!afford(20000) || !map.find_bush_clusters(p, DraftPlan::attack_ranges[0], draft_reserve + 20000)) return;
            for (const int r : DraftPlan::attack_ranges) {
                auto tiles = map.viewers(p, r);
                tiles &= map.open_for_us;
                const std::uint64_t* words = tiles.ptr();
                for (int y = p.y - r; y <= p.y + r; ++y)
                    for (int x = p.x - r; x <= p.x + r; ++x, ++a.attack_bit)
                        if (x >= 0 && y >= 0 && x < map.width && y < map.height
                            && (words[(y >> 3) * stride + (x >> 3)] >> ((y & 7) * 8 + (x & 7)) & 1))
                            plan.data[a.attack_bit >> 3] |= static_cast<std::uint8_t>(1u << (a.attack_bit & 7));
            }
        }
        plan.attack_groups = static_cast<std::uint8_t>(a.attack_group + 1);
    }
    a.done = true;
}

void write_plan(DraftState& state) {
    state.plan.version = DraftPlan::current_version;
    cambc::draft_memory = std::span<const std::byte>{reinterpret_cast<const std::byte*>(&state.plan), sizeof(DraftPlan)};
}

} // namespace

const DraftPlan* read_draft_plan() {
    const auto* bytes = cambc::draft_memory.data();
    if (cambc::draft_memory.size() < sizeof(DraftPlan) || reinterpret_cast<std::uintptr_t>(bytes) % alignof(DraftPlan) != 0)
        return nullptr;
    const auto* plan = reinterpret_cast<const DraftPlan*>(bytes);
    return plan->version == DraftPlan::current_version ? plan : nullptr;
}

void play_draft(DraftState& state) {
    // Write before picking: a pick ends the draft turn's actions (later writes fail with error 18),
    // and the draft bot may not run again after its last pick.
    try {
        analyse(state.plan);
    } catch (const std::exception&) {
        analysis().done = true; // a member's tiles may be half written: only finished groups count
    }
    state.plan.field_layers = static_cast<std::uint16_t>(max_field_layers());
    write_plan(state);
    pick_first_available(state, params::draft_preference);
}

void ensure_picked(DraftState& state) {
    if (state.picked_round == draft_round()) return;
    pick_first_available(state, all_champions());
}

} // namespace aph
