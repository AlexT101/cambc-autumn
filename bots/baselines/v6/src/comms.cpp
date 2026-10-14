#include "comms.h"
#include <algorithm>
#include <span>
#include "world.h"

namespace aph::comms {

namespace {

// Layout, least significant bit first:
//   [0, 7)    sighting x + 1, 0 = none
//   [7, 14)   sighting y
//   [14, 17)  enemy index
//   [17, 20)  its health in eighths of its max
//   [20, 21)  round parity
//   [21, 28)  rally x + 1, 0 = none
//   [28, 35)  rally y
//   [35, 36)  round parity
//   [36, 42)  captured group + 1, 0 = none
//   [42, 50)  its respawn round mod 256
//   [50, 56)  help group + 1, 0 = none
//   [56, 57)  round parity
//   [57, 64)  unused
struct Field {
    int shift, width;
    constexpr std::uint64_t mask() const { return ((std::uint64_t{1} << width) - 1) << shift; }
    constexpr int get(std::uint64_t bits) const { return static_cast<int>((bits & mask()) >> shift); }
    constexpr void set(std::uint64_t& bits, int value) const {
        bits = (bits & ~mask()) | ((static_cast<std::uint64_t>(value) << shift) & mask());
    }
};

constexpr Field sight_x{0, 7}, sight_y{7, 7}, sight_index{14, 3}, sight_health{17, 3}, sight_parity{20, 1};
constexpr Field rally_x{21, 7}, rally_y{28, 7}, rally_parity{35, 1};
constexpr Field camp_group{36, 6}, camp_respawn{42, 8};
constexpr Field help_group{50, 6}, help_parity{56, 1};
constexpr std::uint64_t sighting_bits = sight_x.mask() | sight_y.mask() | sight_index.mask() | sight_health.mask() | sight_parity.mask();
constexpr std::uint64_t rally_bits = rally_x.mask() | rally_y.mask() | rally_parity.mask();
constexpr std::uint64_t camp_bits = camp_group.mask() | camp_respawn.mask();
constexpr std::uint64_t help_bits = help_group.mask() | help_parity.mask();

struct State {
    std::uint64_t last = 0; // the bits as we left them at the end of our previous turn
    int last_round = -1;
    std::uint64_t fresh = 0; // records written since then
    std::optional<Rally> rally;
    std::optional<Help> help;
};
State state;

std::uint64_t read_bits() {
    std::uint64_t bits = 0;
    cambc::shared_memory.read(0, std::span{&bits, 1});
    return bits;
}

void write_bits(std::uint64_t bits, int round) {
    cambc::shared_memory.write(0, std::span{&bits, 1});
    state.last = bits;
    state.last_round = round;
}

std::uint64_t changes(std::uint64_t bits) {
    std::uint64_t fresh = 0;
    for (const auto mask : {sighting_bits, rally_bits, camp_bits, help_bits})
        if ((bits ^ state.last) & mask) fresh |= mask;
    return fresh;
}

// A changed record was written after our previous turn, normally last round or this one; after
// missed turns (out of fuel), take the earliest round that fits.
int dated(int parity) {
    const int after = std::max(state.last_round, 0);
    return (after & 1) == parity ? after : after + 1;
}

} // namespace

void receive(World& world) {
    const auto bits = read_bits();
    const int round = world.round;
    state.fresh = changes(bits);
    if ((state.fresh & sighting_bits) && sight_x.get(bits) != 0) {
        const vec2 pos{sight_x.get(bits) - 1, sight_y.get(bits)};
        const float health = (static_cast<float>(sight_health.get(bits)) + 0.5f) / 8.0f;
        world.note_sighting(sight_index.get(bits), pos, dated(sight_parity.get(bits)), health);
    }
    if ((state.fresh & rally_bits) && rally_x.get(bits) != 0)
        state.rally = Rally{dated(rally_parity.get(bits)), {rally_x.get(bits) - 1, rally_y.get(bits)}};
    if ((state.fresh & help_bits) && help_group.get(bits) != 0)
        state.help = Help{dated(help_parity.get(bits)), help_group.get(bits) - 1};
    if ((state.fresh & camp_bits) && camp_group.get(bits) != 0) {
        const int after = std::max(state.last_round, 0);
        const int respawn = after + ((camp_respawn.get(bits) - after) & 255);
        world.note_capture(camp_group.get(bits) - 1, respawn);
    }
    state.last = bits;
    state.last_round = round;
}

void send(World& world, bool refresh) {
    auto bits = read_bits();
    const int round = world.round;
    const bool sighted = (state.fresh & sighting_bits) && sight_parity.get(bits) == (round & 1) && sight_x.get(bits) != 0;
    // A capture someone posted since our last turn stays up for the rest of the team.
    const bool camp_free = !(state.fresh & camp_bits);
    bool dirty = false;

    if (camp_free) {
        const auto& groups = world.map().groups;
        for (std::size_t g = 0; g < groups.size() && g < 63; ++g) {
            auto& c = world.camps[g];
            if (c.state != CampState::respawning || c.state_round != round || c.told_respawn == c.respawn_round) continue;
            camp_group.set(bits, static_cast<int>(g) + 1);
            camp_respawn.set(bits, c.respawn_round & 255);
            c.told_respawn = c.respawn_round;
            dirty = true;
            break;
        }
    }

    if (!sighted) {
        if (refresh) world.observe();
        const int n = static_cast<int>(world.enemies.size());
        const int start = sight_x.get(bits) != 0 ? sight_index.get(bits) + 1 : 0;
        for (int k = 0; k < n; ++k) {
            const auto& e = world.enemies[(start + k) % n];
            if (!e.visible) continue;
            sight_x.set(bits, e.pos.x + 1);
            sight_y.set(bits, e.pos.y);
            sight_index.set(bits, e.index);
            const float fraction = e.max_health > 0 ? e.health / e.max_health : 1.0f;
            sight_health.set(bits, std::clamp(static_cast<int>(fraction * 8.0f), 0, 7));
            sight_parity.set(bits, round & 1);
            dirty = true;
            break;
        }
    }
    if (dirty) write_bits(bits, round);
}

void post_rally(int round, vec2 pos) {
    auto bits = read_bits();
    rally_x.set(bits, pos.x + 1);
    rally_y.set(bits, pos.y);
    rally_parity.set(bits, round & 1);
    write_bits(bits, round);
    state.rally = Rally{round, pos};
}

std::optional<Rally> rally() { return state.rally; }

void post_help(int round, int group) {
    auto bits = read_bits();
    help_group.set(bits, group + 1);
    help_parity.set(bits, round & 1);
    write_bits(bits, round);
    state.help = Help{round, group};
}

std::optional<Help> help() { return state.help; }

} // namespace aph::comms
