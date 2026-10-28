#include "comms.h"
#include <algorithm>
#include <bit>
#include <utility>
#include <vector>
#include "safety.h"
#include "support_mailbox.h"
#include "turn_order.h"
#include "world.h"
#include "../draft/map_economy.h"

namespace aph::comms {

namespace {

// Each record is one mixed-radix number in its own bits, as narrow as the map and the team sizes
// allow, so every teammate derives the same layout. Least significant first:
//   sighting  0 = none, else 1 + ((y * width + x) * enemies + enemy index) * 8 + health in sevenths
//             of its max, floored (7 = full)
//   parity    the sighting's round parity
//   count     sighting write count
//   bag       bag in fours, rounded up, * team + carrying ally's index
//   claim     (claimed group + 1) * team + claiming ally's index
//   camp      0 = none, else 1 + offset[captured group] + its respawn round mod period[group]
//   then free bits
// With room for it, the camp slot holds either record, a capture (posted rarely, and winning the
// slot) or a second sighting, by its lowest bit: 0, then the camp record; or 1, then the second's
// write count (3 bits), parity (1) and sighting.
// Each ally's priority payload (turn_order.h) also carries its claim + 1 in its low 8 bits, and
// support_mailbox.h's intents above them.
// A claim or a bag is a standing state, rewritten only when it changes or as a reminder.
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
    int width = 0, enemies = 1, team = 1;
    BitField sight, parity, count, bag, camp, claim;
    bool second = false; // the camp slot also carries a second sighting
    std::vector<int> camp_offset; // by group, then the total
    std::uint64_t sighting_bits = 0, bag_bits = 0, camp_bits = 0, claim_bits = 0;
    int period(int g) const { return camp_offset[g + 1] - camp_offset[g]; }
};

Layout layout_;

// At most 60 bits: 19 sighting (100x100, 6 enemies), 4 parity and count, 10 bag (6 allies), 11
// claim, 16 camp (255 groups).
[[gnu::noinline]] void lay_out(const World& world) {
    auto& L = layout_;
    const auto& map = world.map();
    L.enemies = std::max(1, static_cast<int>(world.enemies.size()));
    L.team = std::max(1, static_cast<int>(world.allies.size()));
    const int groups = std::min(static_cast<int>(map.groups.size()), max_group);
    L.camp_offset.assign(static_cast<std::size_t>(groups + 1), 0);
    for (int g = 0; g < groups; ++g)
        L.camp_offset[static_cast<std::size_t>(g + 1)] = L.camp_offset[static_cast<std::size_t>(g)] + map.groups[static_cast<std::size_t>(g)].respawn + 1 + camp_slack;
    int shift = 0;
    const auto field = [&](std::uint64_t states) {
        const int width = static_cast<int>(std::bit_width(states - 1));
        const BitField f{shift, ((std::uint64_t{1} << width) - 1) << shift};
        shift += width;
        return f;
    };
    L.sight = field(static_cast<std::uint64_t>(map.width) * static_cast<std::uint64_t>(map.height) * static_cast<std::uint64_t>(L.enemies) * 8 + 1);
    L.parity = field(2);
    L.count = field(8);
    L.bag = field(128 * static_cast<std::uint64_t>(L.team));
    L.claim = field(static_cast<std::uint64_t>(groups + 1) * static_cast<std::uint64_t>(L.team));
    const int camp_width = static_cast<int>(std::bit_width(static_cast<std::uint64_t>(L.camp_offset.back())));
    const int sight_width = static_cast<int>(std::bit_width(L.sight.mask >> L.sight.shift));
    const int slot_width = 1 + std::max(camp_width, sight_width + 4);
    L.second = shift + slot_width <= 64;
    L.camp = field(std::uint64_t{1} << (L.second ? slot_width : camp_width));
    L.sighting_bits = L.sight.mask | L.parity.mask | L.count.mask;
    L.bag_bits = L.bag.mask;
    L.camp_bits = L.camp.mask;
    L.claim_bits = L.claim.mask;
    L.width = map.width;
}

const Layout& layout(const World& world) {
    if (!layout_.width) lay_out(world);
    return layout_;
}

struct Sighting {
    int index;
    vec2 pos;
    int health; // sevenths
};

// A nonzero sighting value.
Sighting decode(const Layout& L, std::uint64_t value) {
    auto v = value - 1;
    const int health = static_cast<int>(v % 8);
    v /= 8;
    const int index = static_cast<int>(v % static_cast<std::uint64_t>(L.enemies));
    v /= static_cast<std::uint64_t>(L.enemies);
    const auto w = static_cast<std::uint64_t>(L.width);
    return {index, {static_cast<int>(v % w), static_cast<int>(v / w)}, health};
}

Sighting sighting(const Layout& L, std::uint64_t bits) { return decode(L, L.sight.get(bits)); }

// A sighting's health as a share of max: the middle of its seventh.
float health_share(int sevenths) { return sevenths == 7 ? 1.0f : (static_cast<float>(sevenths) + 0.5f) / 7.0f; }

// The capture record in the camp slot, 0 for none.
std::uint64_t camp_code(const Layout& L, std::uint64_t bits) {
    const auto v = L.camp.get(bits);
    return !L.second ? v : (v & 1) ? 0 : v >> 1;
}
void put_camp(const Layout& L, std::uint64_t& bits, std::uint64_t code) { L.camp.set(bits, L.second ? code << 1 : code); }

struct Second {
    std::uint64_t sight = 0; // as the first's field: 0 = none
    int parity = 0, count = 0;
};
Second second_sighting(const Layout& L, std::uint64_t bits) {
    const auto v = L.camp.get(bits);
    if (!L.second || !(v & 1)) return {};
    return {v >> 5, static_cast<int>(v >> 4 & 1), static_cast<int>(v >> 1 & 7)};
}

std::uint64_t sight_value(const Layout& L, const ChampionBelief& e) {
    const float fraction = e.max_health > 0 ? e.health / e.max_health : 1.0f;
    const int health = fraction >= 1.0f ? 7 : std::clamp(static_cast<int>(fraction * 7.0f), 0, 6);
    const auto tile = static_cast<std::uint64_t>(e.pos.y) * static_cast<std::uint64_t>(L.width) + static_cast<std::uint64_t>(e.pos.x);
    return 1 + (tile * static_cast<std::uint64_t>(L.enemies) + static_cast<std::uint64_t>(e.index)) * 8 + static_cast<std::uint64_t>(health);
}

// The write count makes a sighting rewritten unchanged, with the same parity, still read as new.
void put_sighting(const Layout& L, std::uint64_t& bits, const ChampionBelief& e, int round) {
    L.sight.set(bits, sight_value(L, e));
    L.parity.set(bits, static_cast<std::uint64_t>(round & 1));
    L.count.set(bits, L.count.get(bits) + 1);
}

void put_second(const Layout& L, std::uint64_t& bits, const ChampionBelief& e, int round) {
    const int count = (second_sighting(L, bits).count + 1) & 7;
    L.camp.set(bits, sight_value(L, e) << 5 | static_cast<std::uint64_t>(round & 1) << 4 | static_cast<std::uint64_t>(count) << 1 | 1);
}

// Another live ally as urgency() reads it: where we last saw it, how long ago, and whether in sight.
struct Mate {
    vec2 pos;
    int age;
    bool visible;
};

// Worked out by receive() at the turn start, where fuel is plentiful, rather than by send() at the
// turn's end: nothing moves during our turn, so they hold then.
struct Urgencies {
    int round = -1;
    Unwritten<Mate, 8> mates; // vec2 would zero them, at a fuel a byte
    int count = -1; // mates listed, -1 until the first urgency() this turn
    std::uint8_t known = 0; // bit i: enemy[i] and bush[i] hold
    std::array<int, 8> enemy;
    std::array<bool, 8> bush;
    int first = 0, second = 0; // the sighting slots' as receive() read them
};
Urgencies urgencies;

// Whether an enemy at `pos` may strike a teammate who lacks the sighting before that teammate's next
// turn, and how soon: the distance to the nearest mate not seen to see it (vision.personal: only its
// own tile and ward), less the rounds since we saw that mate, as it may have walked a step a round
// towards it. Lower is sooner. Beyond a strike's reach every sighting counts the same (`far`), so
// the rotation keeps the rest fresh: Safety leaves out an enemy whose possible tiles grow too wide.
// A mate we see within vision range counts as seeing it, walls ignored (a shadow cast per enemy
// costs more than the whole send); for an enemy in a bush, only from inside its cluster.
constexpr int far = Strike::max_reach + 1;
int urgency(const World& world, vec2 pos, bool bush) {
    auto& U = urgencies;
    const auto& map = world.map();
    if (U.count < 0) {
        U.count = 0;
        for (const auto& a : world.allies)
            if (!a.is_self && a.alive && a.pos_round >= 0 && U.count < 8)
                U.mates.a[static_cast<std::size_t>(U.count++)] = {a.pos, world.round - a.pos_round, a.visible};
    }
    // Grown on demand: whether warm-up has found it yet depends on fuel.
    const BushCluster* cluster = nullptr;
    int best = far;
    for (int i = 0; i < U.count; ++i) {
        const auto& m = U.mates.a[static_cast<std::size_t>(i)];
        const int d = dist(m.pos, pos);
        if (m.visible && d <= vision_radius) {
            if (!bush) continue;
            if (!cluster) cluster = &map.bush_cluster(pos);
            if (test(cluster->tiles, m.pos)) continue;
        }
        best = std::min(best, std::max(0, d - m.age));
    }
    return best;
}

// An enemy in sight: its urgency, and whether it stands in a bush.
int urgency_of(const World& world, const ChampionBelief& e, bool& bush) {
    auto& U = urgencies;
    const auto i = static_cast<std::size_t>(e.index);
    if (!(U.known >> i & 1)) {
        U.bush[i] = test(world.map().bushes, e.pos);
        U.enemy[i] = urgency(world, e.pos, U.bush[i]);
        U.known |= static_cast<std::uint8_t>(1u << i);
    }
    bush = U.bush[i];
    return U.enemy[i];
}

int bag_body(const Layout& L, std::uint64_t bits) { return static_cast<int>(L.bag.get(bits) % static_cast<std::uint64_t>(L.team)); }
int bag_fours(const Layout& L, std::uint64_t bits) { return static_cast<int>(L.bag.get(bits) / static_cast<std::uint64_t>(L.team)); }
int claim_body(const Layout& L, std::uint64_t bits) { return static_cast<int>(L.claim.get(bits) % static_cast<std::uint64_t>(L.team)); }
// The claimed group + 1.
int claim_group(const Layout& L, std::uint64_t bits) { return static_cast<int>(L.claim.get(bits) / static_cast<std::uint64_t>(L.team)); }

struct State {
    std::uint64_t last = 0; // the bits as we left them at the end of our previous turn
    std::uint64_t now = 0;  // this turn's, as receive() read them and send() leaves them
    int now_round = -1;
    int last_round = -1;
    std::uint64_t fresh = 0; // records written since then
    int posted_bag = -1;
    int posted = -1;
};
State state;

support_mailbox::State support;
int support_intent_round = -1;
bool support_intent_value = false;

// The protected mate and the healer, found once: the picks are fixed after the draft.
std::array<const ChampionBelief*, 2> endpoints(const World& world) {
    static std::array<int, 2> index{-2, -2};
    if (index[0] == -2) {
        index = {-1, -1};
        for (int i = 0; i < static_cast<int>(world.allies.size()); ++i) {
            if (support_protected(world, world.allies[i])) index[support_mailbox::protected_mate] = i;
            if (support_healer(world.allies[i])) index[support_mailbox::healer] = i;
        }
    }
    std::array<const ChampionBelief*, 2> pair{};
    for (int i = 0; i < 2; ++i)
        if (index[i] >= 0) pair[i] = &world.allies[index[i]];
    return pair;
}

// An ally's priority payload as read this turn, or -1: out of sight, or a priority of 0 (none).
std::int64_t payload_of(const World& world, const ChampionBelief& a) {
    if (a.priority_round != world.round || a.next_priority == 0) return -1;
    return static_cast<std::uint32_t>(a.next_priority) & ((1u << priority_payload_bits) - 1);
}

// Only the pair reads the mailbox.
void receive_support(const World& world) {
    const auto pair = endpoints(world);
    if (!pair[0] || !pair[1] || (!pair[0]->is_self && !pair[1]->is_self)) return;
    std::array<support_mailbox::Endpoint, 2> endpoint;
    for (int i = 0; i < 2; ++i) endpoint[i] = {true, pair[i]->alive, pair[i]->is_self, pair[i]->respawned_round};
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
    return whole(L.sighting_bits) | whole(L.bag_bits) | whole(L.camp_bits) | whole(L.claim_bits);
}

// A changed record was written after our previous turn, normally last round or this one; after
// missed turns (out of fuel), take the earliest round that fits.
int dated(int parity) {
    const int after = std::max(state.last_round, 0);
    return (after & 1) == parity ? after : after + 1;
}

// f(slot, sighting, round written) for each slot's sighting changed in `fresh`, the first slot first.
template <class F> void each_fresh_sighting(const Layout& L, std::uint64_t bits, std::uint64_t fresh, F&& f) {
    if ((fresh & L.sighting_bits) && L.sight.get(bits) != 0) f(0, sighting(L, bits), dated(static_cast<int>(L.parity.get(bits))));
    if (const auto two = second_sighting(L, bits); (fresh & L.camp_bits) && two.sight != 0) f(1, decode(L, two.sight), dated(two.parity));
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

[[gnu::flatten]] void expect(World& world) {
    world.expected_sighting = world.expected_second = {};
    const auto& L = layout(world);
    const auto bits = read_bits();
    each_fresh_sighting(L, bits, changes(L, bits), [&](int slot, const Sighting& s, int round) {
        (slot == 0 ? world.expected_sighting : world.expected_second) = {s.index, s.pos, round};
    });
}

[[gnu::flatten]] void receive(World& world) {
    world.throw_if_stale();
    const auto& L = layout(world);
    const auto bits = state.now = read_bits();
    const int round = state.now_round = world.round;
    auto& U = urgencies;
    U.round = round;
    U.known = 0;
    U.count = -1;
    U.first = U.second = 0;
    receive_support(world);
    state.fresh = changes(L, bits);
    each_fresh_sighting(L, bits, state.fresh, [&](int, const Sighting& s, int seen) {
        world.note_sighting(s.index, s.pos, seen, health_share(s.health));
    });
    if (state.fresh & L.bag_bits)
        if (const int body = bag_body(L, bits); body != world.me().index) detail::posts.bags[body] = 4 * bag_fours(L, bits);
    if (state.fresh & L.claim_bits)
        if (const int body = claim_body(L, bits); body != world.me().index) detail::posts.claims[body] = claim_group(L, bits) - 1;
    // The claim of an ally in sight as of its last turn, never older than the slot's.
    for (const auto& a : world.allies)
        if (const auto p = a.is_self ? -1 : payload_of(world, a); p >= 0) detail::posts.claims[a.index] = static_cast<int>(p & 0xff) - 1;
    if (const auto record = camp_code(L, bits); (state.fresh & L.camp_bits) && record != 0) {
        const auto [g, respawn] = decode_capture(L, record);
        world.note_capture(g, respawn);
    }
    state.last = bits;
    state.last_round = round;

    const auto& map = world.map();
    bool bush = false;
    for (const auto& e : world.enemies)
        if (e.index < 8 && e.alive && e.visible) urgency_of(world, e, bush);
    const auto slot = [&](std::uint64_t code) {
        if (code == 0) return 0;
        const auto s = decode(L, code);
        return urgency(world, s.pos, test(map.bushes, s.pos));
    };
    // Only a teammate's sighting from this round can be replaced (send()).
    const bool now = (state.fresh & L.sighting_bits) && static_cast<int>(L.parity.get(bits)) == (round & 1);
    if (now) U.first = slot(L.sight.get(bits));
    if (const auto two = second_sighting(L, bits); (state.fresh & L.camp_bits) && two.parity == (round & 1)) U.second = slot(two.sight);
}

// No teammate acts during our turn: the bits are still those receive() read, if it read them this
// round. Older bits would overwrite what teammates wrote since.
void send(World& world, bool moved, bool refresh) {
    if (state.now_round != world.round) return;
    const auto& L = layout(world);
    auto bits = state.now;
    const int round = world.round;
    const bool sighted = (state.fresh & L.sighting_bits) && static_cast<int>(L.parity.get(bits)) == (round & 1) && L.sight.get(bits) != 0;
    // A capture someone posted since our last turn stays up for the rest of the team; one we post
    // replaces a second sighting.
    const bool camp_free = !((state.fresh & L.camp_bits) && camp_code(L, bits) != 0);
    const auto old_second = second_sighting(L, bits);
    const bool second_taken = (state.fresh & L.camp_bits) && old_second.sight != 0 && old_second.parity == (round & 1);
    bool dirty = false, posted_camp = false;

    // Before anything is marked posted: an observe that runs out of fuel resumes a round late,
    // when these bits would overwrite what teammates wrote since.
    if (!sighted || (L.second && camp_free && !second_taken)) {
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
            put_camp(L, bits, static_cast<std::uint64_t>(1 + L.camp_offset[static_cast<std::size_t>(g)] + c.respawn_round % L.period(g)));
            c.told_respawn = c.respawn_round;
            dirty = posted_camp = true;
            return true;
        });
    }

    // A claim not yet read at our previous turn may not have reached every teammate: ours waits.
    // Turn order changes every round, so a teammate can miss a claim overwritten before its next
    // turn: each in turn re-posts its standing claim into a free slot.
    const int me = world.me().index;
    const int claim_by = claim_body(L, bits);
    const bool claim_fresh = (state.fresh & L.claim_bits) && claim_by != me;
    const bool reminder = round % L.team == me && (claim_by != me || claim_group(L, bits) != detail::posts.mine + 1);
    if (!claim_fresh && (detail::posts.mine != state.posted || reminder)) {
        L.claim.set(bits, static_cast<std::uint64_t>((detail::posts.mine + 1) * L.team + me));
        state.posted = detail::posts.mine;
        dirty = true;
    }

    // Bags change at captures, kills, deaths and tributes; the same rules as claims, one turn later
    // in the reminder cycle.
    const int bag_by = bag_body(L, bits);
    const bool bag_fresh = (state.fresh & L.bag_bits) && bag_by != me;
    const int fours = std::min(127, (detail::posts.my_bag + 3) / 4);
    const bool bag_reminder = (round + 1) % L.team == me && (bag_by != me || bag_fours(L, bits) != fours);
    if (!bag_fresh && (fours != state.posted_bag || bag_reminder)) {
        L.bag.set(bits, static_cast<std::uint64_t>(fours * L.team + me));
        state.posted_bag = fours;
        dirty = true;
    }

    // The most urgent, then an enemy in a bush (only whoever shares its cluster sees it, while one in
    // the open is seen by any teammate near enough), then in turn after `start`. Never `skip`, the
    // other slot's. Visibility is the turn start's or a later observe's: nothing moves during our turn.
    const auto choose = [&](int start, int skip, int& best) -> const ChampionBelief* {
        const int n = static_cast<int>(world.enemies.size());
        const ChampionBelief* pick = nullptr;
        bool pick_bush = false;
        for (int k = 0; k < n; ++k) {
            const auto& e = world.enemies[(start + k) % n];
            if (!e.alive || !e.visible || e.index == skip || e.index >= 8) continue;
            bool bush = false;
            const int u = urgency_of(world, e, bush);
            if (!pick || u < best || (u == best && bush && !pick_bush)) pick = &e, best = u, pick_bush = bush;
        }
        return pick;
    };
    // A teammate's sighting this round reached those between it and us: one more urgent replaces it
    // for those after us.
    const auto replaces = [&](std::uint64_t old, int u, int old_urgency, const ChampionBelief& e) {
        return decode(L, old).index != e.index && u < old_urgency;
    };
    const int first = L.sight.get(bits) != 0 ? sighting(L, bits).index : -1;
    int posted_first = sighted ? first : -1;
    int u = 0;
    if (const auto* e = choose(first + 1, -1, u); e && (!sighted || replaces(L.sight.get(bits), u, urgencies.first, *e))) {
        put_sighting(L, bits, *e, round);
        posted_first = e->index;
        dirty = true;
    }
    // A capture we posted this turn holds the slot.
    if (L.second && camp_free && !posted_camp) {
        const int last = old_second.sight != 0 ? decode(L, old_second.sight).index : first;
        if (const auto* e = choose(last + 1, posted_first, u); e && (!second_taken || replaces(old_second.sight, u, urgencies.second, *e))) {
            put_second(L, bits, *e, round);
            dirty = true;
        }
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

std::uint32_t priority_payload(const World& world) {
    auto payload = static_cast<std::uint32_t>(detail::posts.mine + 1);
    const auto pair = endpoints(world);
    if (pair[0] && pair[1] && (pair[0]->is_self || pair[1]->is_self))
        payload |= support_mailbox::encode(world.round, support_mailbox::publish_value(world.round, support_intent_round, support_intent_value,
                                                                                     pair[0]->alive && pair[1]->alive));
    return payload;
}

} // namespace aph::comms
