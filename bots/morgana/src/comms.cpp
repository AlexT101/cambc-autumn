#include "comms.h"
#include <algorithm>
#include <array>
#include <span>
#include "world.h"

namespace aph::comms {

namespace {

// Layout, least significant bit first:
//   [0, 7)    sighting x + 1, 0 = none
//   [7, 14)   sighting y
//   [14, 17)  enemy index
//   [17, 20)  its health in sevenths of its max, floored; 7 = full
//   [20, 21)  round parity
//   [21, 23)  sighting write count
//   [23, 29)  rally x / 2 + 1, 0 = none
//   [29, 35)  rally y / 2
//   [35, 36)  round parity
//   [36, 37)  rally write count
//   [37, 43)  captured group + 1, 0 = none
//   [43, 50)  its respawn round / 2, rounded up, mod 128
//   [50, 56)  claimed group + 1, 0 = none
//   [56, 59)  claiming ally's index
//   [59, 64)  its bag in eights, rounded, at most 31
// The write counts make a record rewritten unchanged, with the same parity, still read as new.
// A claim and its bag are a standing state, rewritten only when either changes.
struct Field {
    int shift, width;
    constexpr std::uint64_t mask() const { return ((std::uint64_t{1} << width) - 1) << shift; }
    constexpr int get(std::uint64_t bits) const { return static_cast<int>((bits & mask()) >> shift); }
    constexpr void set(std::uint64_t& bits, int value) const {
        bits = (bits & ~mask()) | ((static_cast<std::uint64_t>(value) << shift) & mask());
    }
};

constexpr Field sight_x{0, 7}, sight_y{7, 7}, sight_index{14, 3}, sight_health{17, 3}, sight_parity{20, 1};
constexpr Field sight_count{21, 2};
constexpr Field rally_x{23, 6}, rally_y{29, 6}, rally_parity{35, 1}, rally_count{36, 1};
constexpr Field camp_group{37, 6}, camp_respawn{43, 7};
constexpr Field claim_group{50, 6}, claim_body{56, 3}, claim_bag{59, 5};
constexpr std::uint64_t sighting_bits = sight_x.mask() | sight_y.mask() | sight_index.mask() | sight_health.mask() | sight_parity.mask()
                                        | sight_count.mask();
constexpr std::uint64_t rally_bits = rally_x.mask() | rally_y.mask() | rally_parity.mask() | rally_count.mask();
constexpr std::uint64_t camp_bits = camp_group.mask() | camp_respawn.mask();
constexpr std::uint64_t claim_bits = claim_group.mask() | claim_body.mask() | claim_bag.mask();

static_assert((sighting_bits & rally_bits) == 0 && ((sighting_bits | rally_bits) & camp_bits) == 0
              && ((sighting_bits | rally_bits | camp_bits) & claim_bits) == 0);

void count_write(std::uint64_t& bits, Field count) { count.set(bits, count.get(bits) + 1); }

int bag_code(int gems) { return std::min(31, (gems + 4) / 8); }

struct State {
    std::uint64_t last = 0; // the bits as we left them at the end of our previous turn
    int last_round = -1;
    std::uint64_t fresh = 0; // records written since then
    std::optional<Rally> rally;
    std::array<int, 8> claims{-1, -1, -1, -1, -1, -1, -1, -1}; // by ally index
    std::array<int, 8> bags{};                                 // by ally index
    int mine = -1, posted = -1;
    int my_bag = 0, posted_bag = -1;
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
    for (const auto mask : {sighting_bits, rally_bits, camp_bits, claim_bits})
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
        const int code = sight_health.get(bits);
        const float health = code == 7 ? 1.0f : (static_cast<float>(code) + 0.5f) / 7.0f;
        world.note_sighting(sight_index.get(bits), pos, dated(sight_parity.get(bits)), health);
    }
    if ((state.fresh & rally_bits) && rally_x.get(bits) != 0)
        state.rally = Rally{dated(rally_parity.get(bits)), {2 * (rally_x.get(bits) - 1), 2 * rally_y.get(bits)}};
    if ((state.fresh & claim_bits) && claim_body.get(bits) != world.me().index) {
        state.claims[claim_body.get(bits)] = claim_group.get(bits) - 1;
        state.bags[claim_body.get(bits)] = 8 * claim_bag.get(bits);
    }
    if ((state.fresh & camp_bits) && camp_group.get(bits) != 0) {
        const int after = (std::max(state.last_round, 0) + 1) / 2;
        const int respawn = 2 * (after + ((camp_respawn.get(bits) - after) & 127));
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
            if (c.state != CampState::respawning || c.respawn_round <= round || c.told_respawn == c.respawn_round) continue;
            // Seen respawning, not inferred from a hold out of sight.
            if (c.state_round + groups[g].respawn < c.respawn_round) continue;
            camp_group.set(bits, static_cast<int>(g) + 1);
            camp_respawn.set(bits, ((c.respawn_round + 1) / 2) & 127);
            c.told_respawn = c.respawn_round;
            dirty = true;
            break;
        }
    }

    // A claim not yet read at our previous turn may not have reached every teammate: ours waits.
    // Turn order changes every round, so a teammate can miss a claim overwritten before its next
    // turn: each in turn re-posts its standing claim into a free slot.
    const int me = world.me().index;
    const bool claim_fresh = (state.fresh & claim_bits) && claim_body.get(bits) != me;
    const int team = static_cast<int>(world.allies.size());
    const int bag = bag_code(state.my_bag);
    const bool reminder = round % team == me
                          && (claim_body.get(bits) != me || claim_group.get(bits) != state.mine + 1 || claim_bag.get(bits) != bag);
    if (!claim_fresh && (state.mine != state.posted || bag != state.posted_bag || reminder)) {
        claim_group.set(bits, state.mine + 1);
        claim_body.set(bits, me);
        claim_bag.set(bits, bag);
        state.posted = state.mine;
        state.posted_bag = bag;
        dirty = true;
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
            sight_health.set(bits, fraction >= 1.0f ? 7 : std::clamp(static_cast<int>(fraction * 7.0f), 0, 6));
            sight_parity.set(bits, round & 1);
            count_write(bits, sight_count);
            dirty = true;
            break;
        }
    }
    if (dirty) write_bits(bits, round);
}

void post_rally(int round, vec2 pos) {
    auto bits = read_bits();
    rally_x.set(bits, pos.x / 2 + 1);
    rally_y.set(bits, pos.y / 2);
    rally_parity.set(bits, round & 1);
    count_write(bits, rally_count);
    write_bits(bits, round);
}

std::optional<Rally> rally() { return state.rally; }

void claim(int group) { state.mine = group < 63 ? group : -1; }

void bag(int gems) { state.my_bag = gems; }

int bag_of(const World& world, int ally) {
    const auto& a = world.allies[ally];
    if (a.is_self) return state.my_bag;
    if (!a.alive) return 0;
    return a.visible ? a.gems : state.bags[ally];
}

int claim_of(const World& world, int ally) {
    const auto& a = world.allies[ally];
    if (a.is_self) return state.mine;
    return a.alive ? state.claims[ally] : -1;
}

} // namespace aph::comms
