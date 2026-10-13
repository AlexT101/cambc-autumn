#include "comms.h"
#include <span>
#include "world.h"

namespace aph::comms {

namespace {

// Layout, least significant bit first:
//   [0, 11)   sighting round, 0 = no sighting
//   [11, 14)  enemy index
//   [14, 21)  x
//   [21, 28)  y
//   [28, 64)  unused
constexpr int round_bits = 11, index_bits = 3, coord_bits = 7;
constexpr int round_shift = 0, index_shift = 11, x_shift = 14, y_shift = 21;

constexpr std::uint64_t field(std::uint64_t bits, int shift, int width) {
    return (bits >> shift) & ((std::uint64_t{1} << width) - 1);
}

constexpr std::uint64_t put(std::uint64_t value, int shift, int width) {
    return (value & ((std::uint64_t{1} << width) - 1)) << shift;
}

} // namespace

Message decode(std::uint64_t bits) {
    Message m;
    if (const auto round = static_cast<int>(field(bits, round_shift, round_bits)); round != 0) {
        m.sighting = Sighting{round, static_cast<int>(field(bits, index_shift, index_bits)),
                              {static_cast<int>(field(bits, x_shift, coord_bits)), static_cast<int>(field(bits, y_shift, coord_bits))}};
    }
    return m;
}

std::uint64_t encode(const Message& m) {
    std::uint64_t bits = 0;
    if (m.sighting) {
        bits |= put(static_cast<std::uint64_t>(m.sighting->round), round_shift, round_bits);
        bits |= put(static_cast<std::uint64_t>(m.sighting->enemy_index), index_shift, index_bits);
        bits |= put(static_cast<std::uint64_t>(m.sighting->pos.x), x_shift, coord_bits);
        bits |= put(static_cast<std::uint64_t>(m.sighting->pos.y), y_shift, coord_bits);
    }
    return bits;
}

Message read() {
    std::uint64_t bits = 0;
    cambc::shared_memory.read(0, std::span{&bits, 1});
    return decode(bits);
}

void write(const Message& message) {
    std::uint64_t bits = encode(message);
    cambc::shared_memory.write(0, std::span{&bits, 1});
}

void receive(World& world) {
    const auto m = read();
    if (m.sighting) world.note_sighting(m.sighting->enemy_index, m.sighting->pos, m.sighting->round);
}

void send(World& world, bool refresh) {
    // Placeholder: post a visible enemy unless this round has one, rotating through them.
    auto m = read();
    if (m.sighting && m.sighting->round >= world.round) return;
    if (refresh) world.observe();
    const int n = static_cast<int>(world.enemies.size());
    const int start = m.sighting ? m.sighting->enemy_index + 1 : 0;
    for (int k = 0; k < n; ++k) {
        const auto& e = world.enemies[(start + k) % n];
        if (!e.visible) continue;
        m.sighting = Sighting{world.round, e.index, e.pos};
        write(m);
        return;
    }
}

} // namespace aph::comms
