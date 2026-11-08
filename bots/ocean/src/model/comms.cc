#include "comms.h"
#include <algorithm>
#include <bit>
#include <utility>
#include <vector>
#include "support_mailbox.h"
#include "turn_order.h"
#include "world.h"
#include "../params.h"

namespace aph::comms {

namespace {

// Each record sits in its own bits, as narrow as the map and the team size allow, so every
// teammate derives the same layout. Least significant first:
//   claims    one field per ally index: its claimed group + 1, 0 for none
//   bag       bag in fours, rounded up, * team + carrying ally's index
//   camp      0 = none, else 1 + offset[captured group] + its respawn round mod period[group];
//             left out (never posted) when it does not fit
//   ally      0 = none, else 1 + cell * 4 team + 4 ally index + round mod 4 (params::comms_ally): a
//             c x c square (c odd: 1, 3 or 5, the narrowest that fits) centred on the record's tile;
//             left out when it does not fit
//   then free bits
// Each ally's priority payload (turn_order.h) also carries its claim + 1 in its low 8 bits, and
// support_mailbox.h's intents above them.
// Each ally rewrites its own claim field every turn. The bag is a standing state in one shared
// slot, rewritten only when it changes or as a reminder.
struct BitField {
    int shift = 0;
    std::uint64_t mask = 0;
    std::uint64_t get(std::uint64_t bits) const { return (bits & mask) >> shift; }
    void set(std::uint64_t& bits, std::uint64_t value) const { bits = (bits & ~mask) | ((value << shift) & mask); }
};

constexpr int max_group = (1 << 8) - 1; // groups from here on are never posted or claimed
// A posted respawn round lies within a group's respawn of the post, which a reader reads within a
// round; the slack covers a reader that missed this many turns (out of fuel).
constexpr int camp_slack = 16;

struct Layout {
    bool ready = false, camp_on = false;
    int team = 1;
    int claim_cap = 0; // claims of groups from here on post as none
    std::array<BitField, 8> claim{}; // by ally index
    BitField bag, camp;
    std::vector<int> camp_offset; // by group, then the total
    std::uint64_t bag_bits = 0, camp_bits = 0;
    bool ally_on = false;
    BitField ally;
    std::uint64_t ally_bits = 0;
    int cell = 1, cells_y = 1;
    int period(int g) const { return camp_offset[g + 1] - camp_offset[g]; }
};

Layout layout_;

// Worst case (6 bodies, 128+ groups): 6 x 8 claim + 10 bag = 58 bits, leaving no room for the camp
// record (up to 16 bits at 255 groups). Claims are narrowed only past 6 bodies.
[[gnu::noinline]] void lay_out(const World& world) {
    auto& L = layout_;
    const auto& map = world.map();
    L.team = std::clamp(static_cast<int>(world.allies.size()), 1, 8);
    const int groups = std::min(static_cast<int>(map.groups.size()), max_group);
    L.camp_offset.assign(static_cast<std::size_t>(groups + 1), 0);
    for (int g = 0; g < groups; ++g)
        L.camp_offset[static_cast<std::size_t>(g + 1)] = L.camp_offset[static_cast<std::size_t>(g)] + map.groups[static_cast<std::size_t>(g)].respawn + 1 + camp_slack;
    const auto width_of = [](std::uint64_t states) { return static_cast<int>(std::bit_width(states - 1)); };
    int shift = 0;
    const auto field = [&](int width) {
        const BitField f{shift, ((std::uint64_t{1} << width) - 1) << shift};
        shift += width;
        return f;
    };
    const int bag_width = width_of(128 * static_cast<std::uint64_t>(L.team));
    const int claim_width = std::min(width_of(static_cast<std::uint64_t>(groups) + 1), (64 - bag_width) / L.team);
    L.claim_cap = (1 << claim_width) - 1;
    for (int i = 0; i < L.team; ++i) L.claim[static_cast<std::size_t>(i)] = field(claim_width);
    L.bag = field(bag_width);
    const int camp_width = static_cast<int>(std::bit_width(static_cast<std::uint64_t>(L.camp_offset.back())));
    L.camp_on = shift + camp_width <= 64;
    if (L.camp_on) L.camp = field(camp_width);
    if (params::comms_ally && L.camp_on)
        for (const int c : {1, 3, 5}) {
            const auto cells = static_cast<std::uint64_t>((map.width + c - 1) / c) * static_cast<std::uint64_t>((map.height + c - 1) / c);
            const int width = width_of(cells * 4 * static_cast<std::uint64_t>(L.team) + 1);
            if (shift + width > 64) continue;
            L.cell = c, L.cells_y = (map.height + c - 1) / c;
            L.ally = field(width);
            L.ally_on = true;
            break;
        }
    L.ally_bits = L.ally.mask;
    L.bag_bits = L.bag.mask;
    L.camp_bits = L.camp.mask;
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
};
State state;

struct Told {
    vec2 at{-1, -1};
    int round = -1;
};
std::array<Told, 8> told_allies;

support_mailbox::State support;
int support_intent_round = -1;
bool support_intent_value = false;

static_assert(support_mailbox::protected_mate == 0 && support_mailbox::healer == 1); // support_pair's order

// An ally's priority payload as read this turn, or -1: out of sight, or a priority of 0 (none).
std::int64_t payload_of(const World& world, const ChampionBelief& a) {
    if (a.priority_round != world.round || a.next_priority == 0) return -1;
    return static_cast<std::uint32_t>(a.next_priority) & ((1u << priority_payload_bits) - 1);
}

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
    const auto whole = [x](std::uint64_t mask) { return (x & mask) ? mask : 0; };
    return whole(L.bag_bits) | whole(L.camp_bits) | whole(L.ally_bits);
}

// A nonzero capture record's group, and the respawn round it encodes: the first from our previous
// turn on with that residue.
std::pair<int, int> decode_capture(const Layout& L, std::uint64_t record) {
    const int code = static_cast<int>(record) - 1;
    const int g = static_cast<int>(std::upper_bound(L.camp_offset.begin(), L.camp_offset.end(), code) - L.camp_offset.begin()) - 1;
    const int period = L.period(g), base = std::max(state.last_round, 0) + 1;
    return {g, base + ((code - L.camp_offset[static_cast<std::size_t>(g)] - base % period) % period + period) % period};
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
    // An ally in sight's payload is as of the same turn as its field, and never capped.
    for (const auto& a : world.allies) {
        if (a.is_self || a.index >= L.team) continue;
        const auto p = payload_of(world, a);
        detail::posts.claims[a.index] = p >= 0 ? static_cast<int>(p & 0xff) - 1 : static_cast<int>(L.claim[static_cast<std::size_t>(a.index)].get(bits)) - 1;
    }
    if (const auto v = L.ally.get(bits); L.ally_on && (state.fresh & L.ally_bits) && v != 0) {
        const auto code = v - 1, kinds = 4 * static_cast<std::uint64_t>(L.team);
        const int kind = static_cast<int>(code % kinds), cell = static_cast<int>(code / kinds), ally = kind >> 2, h = L.cell / 2;
        if (ally != world.me().index)
            told_allies[static_cast<std::size_t>(ally)] = {{std::min(cell / L.cells_y * L.cell + h, world.map().width - 1),
                                                            std::min(cell % L.cells_y * L.cell + h, world.map().height - 1)},
                                                           round - ((round - kind) & 3)};
    }
    if (const auto record = L.camp.get(bits); (state.fresh & L.camp_bits) && record != 0) {
        const auto [g, respawn] = decode_capture(L, record);
        world.note_capture(g, respawn);
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
    // A capture someone posted since our last turn stays up for the rest of the team.
    const bool camp_free = L.camp_on && !((state.fresh & L.camp_bits) && L.camp.get(bits) != 0);
    bool dirty = false;

    // Before anything is marked posted: an observe that runs out of fuel resumes a round late,
    // when these bits would overwrite what teammates wrote since.
    if (refresh) world.observe();
    else if (moved) note_shortcut("comms-stale-vision");
    if (world.resumed()) return;

    if (camp_free) {
        const auto& groups = world.map().groups;
        world.each_respawning([&](int g) {
            if (g >= max_group) return true;
            auto& c = world.camps[g];
            if (c.respawn_round <= round || c.told_respawn == c.respawn_round) return false;
            // Seen respawning, not inferred from a hold out of sight.
            if (c.state_round + groups[g].respawn < c.respawn_round) return false;
            L.camp.set(bits, static_cast<std::uint64_t>(1 + L.camp_offset[static_cast<std::size_t>(g)] + c.respawn_round % L.period(g)));
            c.told_respawn = c.respawn_round;
            dirty = true;
            return true;
        });
    }

    // Only we write our field, so it holds what we last posted.
    const int me = world.me().index;
    const int mine = detail::posts.mine;
    if (me < L.team) {
        const auto& field = L.claim[static_cast<std::size_t>(me)];
        const auto claim = static_cast<std::uint64_t>(world.me().alive && mine >= 0 && mine < L.claim_cap ? mine + 1 : 0);
        if (field.get(bits) != claim) field.set(bits, claim), dirty = true;
    }

    // One poster a round, by index among the allies that are not healers, while a healer lives.
    if (L.ally_on && world.me().alive && !world.me().facts().heals()) {
        int rank = -1, posters = 0;
        bool healer = false;
        for (const auto& a : world.allies) {
            if (a.facts().heals()) {
                healer |= a.alive;
                continue;
            }
            if (a.is_self) rank = posters;
            ++posters;
        }
        if (healer && round % posters == rank) {
            const vec2 p = my_position();
            const auto v = 1 + static_cast<std::uint64_t>(p.x / L.cell * L.cells_y + p.y / L.cell) * 4 * static_cast<std::uint64_t>(L.team)
                           + static_cast<std::uint64_t>(4 * me + (round & 3));
            if (v != L.ally.get(bits)) L.ally.set(bits, v), dirty = true;
        }
    }

    // Bags change at captures, kills, deaths and tributes. A bag not yet read at our previous turn
    // may not have reached every teammate: ours waits. Turn order changes every round, so a
    // teammate can miss a bag overwritten before its next turn: each in turn re-posts its own.
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

bool told_ally(int ally, vec2& at, int& round) {
    if (ally < 0 || ally >= 8 || told_allies[static_cast<std::size_t>(ally)].round < 0) return false;
    at = told_allies[static_cast<std::size_t>(ally)].at;
    round = told_allies[static_cast<std::size_t>(ally)].round;
    return true;
}

void claim(int group) { detail::posts.mine = group < max_group ? group : -1; }

bool support_request(const World& world) {
    return support.valid(support_mailbox::protected_mate, world.round);
}

bool support_available(const World& world) {
    return support.valid(support_mailbox::healer, world.round);
}

void support_intent(int round, bool positive) { support_intent_round = round, support_intent_value = positive; }

std::uint32_t priority_payload(const World& world) {
    auto payload = static_cast<std::uint32_t>(detail::posts.mine + 1);
    const auto pair = support_pair(world);
    if (pair[0] && pair[1] && (pair[0]->is_self || pair[1]->is_self))
        payload |= support_mailbox::encode(world.round, support_mailbox::publish_value(world.round, support_intent_round, support_intent_value,
                                                                                     pair[0]->alive && pair[1]->alive));
    return payload;
}

} // namespace aph::comms
