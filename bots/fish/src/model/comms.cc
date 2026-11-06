#include "../fish/switches.h"
#if !FISH_PRIORITY
#include "comms_astraeus.inc"
#else
#include "comms.h"
#include <algorithm>
#include <bit>
#include <utility>
#include <vector>
#include "support_mailbox.h"
#include "turn_order.h"
#include "world.h"
#include "../fish/farm_memory.h"

namespace aph::comms {

namespace {

// Each record sits in its own bits, as narrow as the map and the team size allow, so every
// teammate derives the same layout. Least significant first:
//   bag       bag in fours, rounded up, * team + carrying ally's index
//   records   as many as fit (3 for 6 bodies on 255 groups): group + 1 (0 = none), Fish's state
//             (alive, empty, respawning) and a round mod 256: the sighting round for alive and
//             empty, the return round for respawning (FISH_MODEL 7.2's team-union camp memory)
// (bots/fish) Nothing rides in priorities: Fish's encoding uses every bit (turn_order.cc), and
// Fish has no claims: claim_of reads -1 for allies.
// A record slot is rewritten only once every teammate has read it: two rounds after we saw it change.
struct BitField {
    int shift = 0;
    std::uint64_t mask = 0;
    std::uint64_t get(std::uint64_t bits) const { return (bits & mask) >> shift; }
    void set(std::uint64_t& bits, std::uint64_t value) const { bits = (bits & ~mask) | ((value << shift) & mask); }
};

constexpr int max_group = (1 << 8) - 1; // groups from here on are never posted
constexpr int max_records = 4;
// A posted return round lies at most this far behind (a reader that missed turns) or ahead of the reading.
constexpr int respawn_behind = 100;

struct Layout {
    bool ready = false;
    int team = 1, records = 0, group_width = 0;
    BitField bag;
    std::array<BitField, max_records> record{};
    std::uint64_t bag_bits = 0;
};

Layout layout_;

[[gnu::noinline]] void lay_out(const World& world) {
    auto& L = layout_;
    const auto& map = world.map();
    L.team = std::clamp(static_cast<int>(world.allies.size()), 1, 8);
    const int groups = std::min(static_cast<int>(map.groups.size()), max_group);
    const auto width_of = [](std::uint64_t states) { return static_cast<int>(std::bit_width(states - 1)); };
    int shift = 0;
    const auto field = [&](int width) {
        const BitField f{shift, ((std::uint64_t{1} << width) - 1) << shift};
        shift += width;
        return f;
    };
    L.bag = field(width_of(128 * static_cast<std::uint64_t>(L.team)));
    L.group_width = width_of(static_cast<std::uint64_t>(groups) + 1);
    const int width = L.group_width + 2 + 8;
    L.records = std::min(max_records, (64 - shift) / width);
    for (int i = 0; i < L.records; ++i) L.record[static_cast<std::size_t>(i)] = field(width);
    L.bag_bits = L.bag.mask;
    L.ready = true;
}

const Layout& layout(const World& world) {
    if (!layout_.ready) lay_out(world);
    return layout_;
}

int bag_body(const Layout& L, std::uint64_t bits) { return static_cast<int>(L.bag.get(bits) % static_cast<std::uint64_t>(L.team)); }
int bag_fours(const Layout& L, std::uint64_t bits) { return static_cast<int>(L.bag.get(bits) / static_cast<std::uint64_t>(L.team)); }

struct State {
    std::uint64_t last = 0; // the bits as we left them at the end of our previous turn
    std::uint64_t now = 0;  // this turn's, as receive() read them and send() leaves them
    int now_round = -1;
    int last_round = -1;
    std::uint64_t fresh = 0; // records written since then
    int posted_bag = -1;
    std::array<int, max_records> changed{}; // by slot: the round we saw it change
};
State state;

support_mailbox::State support;
int support_intent_round = -1;
bool support_intent_value = false;

static_assert(support_mailbox::protected_mate == 0 && support_mailbox::healer == 1); // support_pair's order

// Fish's priorities carry no payload: the support mailbox never hears anything.
std::int64_t payload_of(const World&, const ChampionBelief&) { return -1; }

// Only the pair reads the mailbox.
void receive_support(const World& world) {
    const auto pair = support_pair(world);
    if (!pair[0] || !pair[1] || (!pair[0]->is_self && !pair[1]->is_self)) return;
    std::array<support_mailbox::Endpoint, 2> endpoint;
    for (int i = 0; i < 2; ++i) endpoint[i] = {pair[i]->alive, pair[i]->is_self};
    const int other = pair[0]->is_self ? 1 : 0;
    support.receive(world.round, endpoint, other, payload_of(world, *pair[other]));
}

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

std::uint64_t changes(const Layout& L, std::uint64_t bits) {
    const auto x = bits ^ state.last;
    std::uint64_t out = (x & L.bag_bits) ? L.bag_bits : 0;
    for (int i = 0; i < L.records; ++i)
        if (x & L.record[static_cast<std::size_t>(i)].mask) out |= L.record[static_cast<std::size_t>(i)].mask;
    return out;
}

std::uint64_t encode(const Layout& L, int g, int fish_state, int round) {
    return static_cast<std::uint64_t>(g + 1) | static_cast<std::uint64_t>(fish_state - 1) << L.group_width
           | static_cast<std::uint64_t>(round & 255) << (L.group_width + 2);
}

void decode(World& world, const Layout& L, std::uint64_t record, int now) {
    const int g = static_cast<int>(record & ((std::uint64_t{1} << L.group_width) - 1)) - 1;
    if (g < 0 || g >= static_cast<int>(world.camps.size())) return;
    const int code = static_cast<int>(record >> L.group_width & 3) + 1;
    const int residue = static_cast<int>(record >> (L.group_width + 2) & 255);
    if (code == fish::st_respawning) {
        const int base = now - respawn_behind;
        const int respawn = base + (((residue - base) % 256) + 256) % 256;
        fish::note_team_sighting(world, g, fish::st_respawning, now, respawn);
        if (respawn > now) world.note_capture(g, respawn);
        world.camps[static_cast<std::size_t>(g)].told_respawn = respawn;
    } else if (code == fish::st_alive || code == fish::st_empty) {
        const int round = now - ((((now - residue) % 256) + 256) % 256);
        fish::note_team_sighting(world, g, static_cast<std::uint8_t>(code), round, -1);
    }
}

} // namespace

[[gnu::flatten]] void receive(World& world) {
    world.throw_if_stale();
    const auto& L = layout(world);
    const auto bits = state.now = read_bits();
    const int round = state.now_round = world.round;
    receive_support(world);
    state.fresh = changes(L, bits);
    if (state.fresh & L.bag_bits)
        if (const int body = bag_body(L, bits); body != world.me().index) detail::posts.bags[body] = 4 * bag_fours(L, bits);
    for (int i = 0; i < L.records; ++i) {
        const auto& f = L.record[static_cast<std::size_t>(i)];
        if (!(state.fresh & f.mask)) continue;
        state.changed[static_cast<std::size_t>(i)] = round;
        if (const auto record = f.get(bits); record != 0) decode(world, L, record, round);
    }
    state.last = bits;
    state.last_round = round;
}

// No teammate acts during our turn: the bits are still those receive() read, if it read them this
// round. Older bits would overwrite what teammates wrote since, as would a turn finishing late.
void send(World& world, bool moved, bool refresh) {
    if (state.now_round != world.round || (finish_late() && world.resumed())) return;
    const auto& L = layout(world);
    auto bits = state.now;
    const int round = world.round;
    bool dirty = false;

    // Before anything is marked posted: an observe that runs out of fuel resumes a round late,
    // when these bits would overwrite what teammates wrote since.
    if (refresh) world.observe();
    else if (moved) note_shortcut("comms-stale-vision");
    if (world.resumed()) return;

    // Our sightings the team's memory lacks, most telling first: a return round, an empty group,
    // then a group seen alive again that the team holds empty or returning. Into the slots every
    // teammate has read, oldest change first.
    if (L.records > 0) {
        fish::observe_camps(world);
        auto& m = fish::memory_of(world);
        std::array<int, max_records> free{};
        int n_free = 0;
        for (int i = 0; i < L.records; ++i)
            if (round - state.changed[static_cast<std::size_t>(i)] >= 2) free[static_cast<std::size_t>(n_free++)] = i;
        std::sort(free.begin(), free.begin() + n_free, [](int a, int b) { return state.changed[static_cast<std::size_t>(a)] < state.changed[static_cast<std::size_t>(b)]; });
        const int groups = std::min(static_cast<int>(m.own.size()), max_group);
        int used = 0;
        for (int want = fish::st_respawning; want >= fish::st_alive && used < n_free; --want) {
            for (int g = 0; g < groups && used < n_free; ++g) {
                const auto& own = m.own[static_cast<std::size_t>(g)];
                if (own.round != round || own.state != want) continue;
                const auto& team = m.team[static_cast<std::size_t>(g)];
                const bool same = team.round >= 0 && team.state == own.state && (want != fish::st_respawning || team.respawn_round == own.respawn_round);
                if (same) continue;
                if (want == fish::st_alive && !(team.round >= 0 && (team.state == fish::st_empty || team.state == fish::st_respawning))) continue;
                if (want == fish::st_respawning && own.respawn_round <= round) continue;
                const int slot = free[static_cast<std::size_t>(used++)];
                L.record[static_cast<std::size_t>(slot)].set(bits, encode(L, g, want, want == fish::st_respawning ? own.respawn_round : round));
                state.changed[static_cast<std::size_t>(slot)] = round;
                m.team[static_cast<std::size_t>(g)] = own;
                if (want == fish::st_respawning) world.camps[static_cast<std::size_t>(g)].told_respawn = own.respawn_round;
                dirty = true;
            }
        }
    }

    // Bags change at captures, kills, deaths and tributes. A bag not yet read at our previous turn
    // may not have reached every teammate: ours waits. Turn order changes every round, so a
    // teammate can miss a bag overwritten before its next turn: each in turn re-posts its own.
    const int me = world.me().index;
    const int bag_by = bag_body(L, bits);
    const bool bag_fresh = (state.fresh & L.bag_bits) && bag_by != me;
    const int fours = std::min(127, (detail::posts.my_bag + 3) / 4);
    const bool bag_reminder = (round + 1) % L.team == me && (bag_by != me || bag_fours(L, bits) != fours);
    if (!bag_fresh && (fours != state.posted_bag || bag_reminder)) {
        L.bag.set(bits, static_cast<std::uint64_t>(fours * L.team + me));
        state.posted_bag = fours;
        dirty = true;
    }
    world.throw_if_stale();
    if (dirty) write_bits(bits, round);
}

void bag(int gems) { detail::posts.my_bag = gems; }

void claim(int group) { detail::posts.mine = group < max_group ? group : -1; }

bool support_request(const World& world) {
    return support.valid(support_mailbox::protected_mate, world.round);
}

bool support_available(const World& world) {
    return support.valid(support_mailbox::healer, world.round);
}

void support_intent(int round, bool positive) { support_intent_round = round, support_intent_value = positive; }

std::uint32_t priority_payload(const World&) { return 0; }

} // namespace aph::comms

#endif
