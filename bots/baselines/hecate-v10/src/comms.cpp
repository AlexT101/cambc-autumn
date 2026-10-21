#include "comms.h"
#include <algorithm>
#include "world.h"

namespace aph::comms {

namespace {

// Layout, least significant bit first:
//   [0, 7)    sighting x + 1, 0 = none
//   [7, 14)   sighting y
//   [14, 17)  enemy index
//   [17, 20)  its health in sevenths of its max, floored; 7 = full
//   [20, 21)  round parity
//   [21, 28)  bag in fours, rounded up
//   [28, 31)  carrying ally's index
//   [32, 40)  captured group + 1, 0 = none
//   [40, 48)  its respawn round mod 256
//   [48, 56)  claimed group + 1, 0 = none
//   [56, 59)  claiming ally's index
//   [59, 62)  sighting write count
//   [31, 32), [62, 64)  unused
// The write count makes a sighting rewritten unchanged, with the same parity, still read as new.
// A claim or a bag is a standing state, rewritten only when it changes or as a reminder.
struct BitField {
    int shift, width;
    constexpr std::uint64_t mask() const { return ((std::uint64_t{1} << width) - 1) << shift; }
    constexpr int get(std::uint64_t bits) const { return static_cast<int>((bits & mask()) >> shift); }
    constexpr void set(std::uint64_t& bits, int value) const {
        bits = (bits & ~mask()) | ((static_cast<std::uint64_t>(value) << shift) & mask());
    }
};

constexpr BitField sight_x{0, 7}, sight_y{7, 7}, sight_index{14, 3}, sight_health{17, 3}, sight_parity{20, 1};
constexpr BitField bag_fours{21, 7}, bag_body{28, 3};
constexpr BitField camp_group{32, 8}, camp_respawn{40, 8};
constexpr BitField claim_group{48, 8}, claim_body{56, 3};
constexpr BitField sight_count{59, 3};
constexpr int max_group = (1 << 8) - 1; // camp_group and claim_group hold the group + 1
constexpr std::uint64_t sighting_bits = sight_x.mask() | sight_y.mask() | sight_index.mask() | sight_health.mask() | sight_parity.mask()
                                        | sight_count.mask();
constexpr std::uint64_t bag_bits = bag_fours.mask() | bag_body.mask();
constexpr std::uint64_t camp_bits = camp_group.mask() | camp_respawn.mask();
constexpr std::uint64_t claim_bits = claim_group.mask() | claim_body.mask();
static_assert((sighting_bits & bag_bits) == 0 && ((sighting_bits | bag_bits) & camp_bits) == 0
              && ((sighting_bits | bag_bits | camp_bits) & claim_bits) == 0);

// The write count makes a sighting rewritten unchanged still read as new.
void put_sighting(std::uint64_t& bits, const ChampionBelief& e, int round) {
    sight_x.set(bits, e.pos.x + 1);
    sight_y.set(bits, e.pos.y);
    sight_index.set(bits, e.index);
    const float fraction = e.max_health > 0 ? e.health / e.max_health : 1.0f;
    sight_health.set(bits, fraction >= 1.0f ? 7 : std::clamp(static_cast<int>(fraction * 7.0f), 0, 6));
    sight_parity.set(bits, round & 1);
    sight_count.set(bits, sight_count.get(bits) + 1);
}

struct State {
    std::uint64_t last = 0; // the bits as we left them at the end of our previous turn
    std::uint64_t now = 0;  // this turn's, as receive() read them and send() leaves them
    int last_round = -1;
    std::uint64_t fresh = 0; // records written since then
    int posted_bag = -1;
    int posted = -1;
};
State state;

// Raw reads and writes: the SDK's checked ones cost several times more.
std::uint64_t read_bits() {
    std::uint64_t bits = 0;
    ok(cambc::detail::sdk_read_shared_memory(0, &bits, sizeof bits));
    return bits;
}

void write_bits(std::uint64_t bits, int round) {
    ok(cambc::detail::sdk_write_shared_memory(0, &bits, sizeof bits));
    state.last = state.now = bits;
    state.last_round = round;
}

std::uint64_t changes(std::uint64_t bits) {
    std::uint64_t fresh = 0;
    for (const auto mask : {sighting_bits, bag_bits, camp_bits, claim_bits})
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

[[gnu::flatten]] void expect(World& world) {
    world.expected_sighting = {};
    const auto bits = read_bits();
    if ((changes(bits) & sighting_bits) && sight_x.get(bits) != 0)
        world.expected_sighting = {sight_index.get(bits), {sight_x.get(bits) - 1, sight_y.get(bits)}, dated(sight_parity.get(bits))};
}

[[gnu::flatten]] void receive(World& world) {
    const auto bits = state.now = read_bits();
    const int round = world.round;
    state.fresh = changes(bits);
    if ((state.fresh & sighting_bits) && sight_x.get(bits) != 0) {
        const vec2 pos{sight_x.get(bits) - 1, sight_y.get(bits)};
        const int code = sight_health.get(bits);
        const float health = code == 7 ? 1.0f : (static_cast<float>(code) + 0.5f) / 7.0f;
        world.note_sighting(sight_index.get(bits), pos, dated(sight_parity.get(bits)), health);
    }
    if ((state.fresh & bag_bits) && bag_body.get(bits) != world.me().index) detail::posts.bags[bag_body.get(bits)] = 4 * bag_fours.get(bits);
    if ((state.fresh & claim_bits) && claim_body.get(bits) != world.me().index)
        detail::posts.claims[claim_body.get(bits)] = claim_group.get(bits) - 1;
    if ((state.fresh & camp_bits) && camp_group.get(bits) != 0) {
        const int after = std::max(state.last_round, 0);
        const int respawn = after + ((camp_respawn.get(bits) - after) & 255);
        world.note_capture(camp_group.get(bits) - 1, respawn);
    }
    state.last = bits;
    state.last_round = round;
}

// No teammate acts during our turn: the bits are still those receive() read.
void send(World& world, bool moved, bool refresh) {
    auto bits = state.now;
    const int round = world.round;
    const bool sighted = (state.fresh & sighting_bits) && sight_parity.get(bits) == (round & 1) && sight_x.get(bits) != 0;
    // A capture someone posted since our last turn stays up for the rest of the team.
    const bool camp_free = !(state.fresh & camp_bits);
    bool dirty = false;

    // Before anything is marked posted: an observe that runs out of fuel resumes a round late,
    // when these bits would overwrite what teammates wrote since.
    if (!sighted) {
        if (refresh) world.observe();
        else if (moved) note_shortcut("comms-stale-vision");
        if (world.is_stale()) return;
    }

    if (camp_free) {
        const auto& groups = world.map().groups;
        world.each_respawning([&](int g) {
            if (g >= max_group) return true;
            auto& c = world.camps[g];
            if (c.respawn_round <= round || c.told_respawn == c.respawn_round) return false;
            // Seen respawning, not inferred from a hold out of sight.
            if (c.state_round + groups[g].respawn < c.respawn_round) return false;
            camp_group.set(bits, g + 1);
            camp_respawn.set(bits, c.respawn_round & 255);
            c.told_respawn = c.respawn_round;
            dirty = true;
            return true;
        });
    }

    // A claim not yet read at our previous turn may not have reached every teammate: ours waits.
    // Turn order changes every round, so a teammate can miss a claim overwritten before its next
    // turn: each in turn re-posts its standing claim into a free slot.
    const int me = world.me().index;
    const bool claim_fresh = (state.fresh & claim_bits) && claim_body.get(bits) != me;
    const int team = static_cast<int>(world.allies.size());
    const bool reminder = round % team == me
                          && (claim_body.get(bits) != me || claim_group.get(bits) != detail::posts.mine + 1);
    if (!claim_fresh && (detail::posts.mine != state.posted || reminder)) {
        claim_group.set(bits, detail::posts.mine + 1);
        claim_body.set(bits, me);
        state.posted = detail::posts.mine;
        dirty = true;
    }

    // Bags change at captures, kills, deaths and tributes; the same rules as claims, one turn later
    // in the reminder cycle.
    const bool bag_fresh = (state.fresh & bag_bits) && bag_body.get(bits) != me;
    const int fours = std::min(127, (detail::posts.my_bag + 3) / 4);
    const bool bag_reminder = (round + 1) % team == me && (bag_body.get(bits) != me || bag_fours.get(bits) != fours);
    if (!bag_fresh && (fours != state.posted_bag || bag_reminder)) {
        bag_fours.set(bits, fours);
        bag_body.set(bits, me);
        state.posted_bag = fours;
        dirty = true;
    }

    if (!sighted) {
        const int n = static_cast<int>(world.enemies.size());
        const int start = sight_x.get(bits) != 0 ? sight_index.get(bits) + 1 : 0;
        for (int k = 0; k < n; ++k) {
            const auto& e = world.enemies[(start + k) % n];
            if (!e.visible) continue;
            put_sighting(bits, e, round);
            dirty = true;
            break;
        }
    }
    if (dirty) write_bits(bits, round);
}

void bag(int gems) { detail::posts.my_bag = gems; }

void claim(int group) { detail::posts.mine = group < max_group ? group : -1; }

} // namespace aph::comms
