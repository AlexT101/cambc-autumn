#pragma once
#include <cambc.h>
#include <cstdint>
#include <iostream>
#include <vector>

namespace aph {

using cambc::bitboard;
using cambc::team;
using cambc::vec2;

// A stdout line costs about 1.3k fuel and each team's output is capped at 1 MiB; indicator dots
// and lines are cheaper.
inline constexpr bool debug_log = false;    // periodic world-belief summary on stdout
inline constexpr bool debug_draw = false;   // world beliefs as indicator dots and lines
inline constexpr bool debug_fuel = false;   // fuel used by each phase of the turn
inline constexpr int debug_log_period = 10; // rounds between summaries
// Belief dump for tools/replay/audit_beliefs.py: a "BD" stdout line per champion every period
// rounds (and in rounds 1-3), self-limited to a share of the team's 1 MiB output.
inline constexpr bool debug_beliefs = false;
inline constexpr int debug_beliefs_period = 10;
// Fight-model calibration: an "FF" stdout line per turn in reach of an enemy, "FC" per chase.
inline constexpr bool debug_fights = false;

inline int dist(vec2 a, vec2 b) { return static_cast<int>(a.chebyshev_distance(b)); }

inline bool in_bounds(vec2 p) { return cambc::map::is_in_bounds(p); }

inline int tile_index(vec2 p) { return p.x + p.y * cambc::map::width(); }

inline vec2 tile_at(int index) { return {index % cambc::map::width(), index / cambc::map::width()}; }

// The 8 king-step directions, north first and clockwise.
inline constexpr vec2 directions[8] = {vec2::north, vec2::north_east, vec2::east, vec2::south_east,
                                       vec2::south, vec2::south_west, vec2::west, vec2::north_west};

inline bitboard single(vec2 p) {
    bitboard b;
    b.set(p);
    return b;
}

inline bitboard square(vec2 p, int r) {
    bitboard b;
    b.draw_chebyshev(p, static_cast<float>(r));
    return b;
}

inline constexpr std::uint16_t unreachable = cambc::distance_field::unreachable;

struct Field {
    cambc::distance_field steps;
    bitboard goals;
    int at(vec2 p) const { return steps.get(p); } // `unreachable` if cut off
};

inline Field make_field(const bitboard& walls, const bitboard& goals) {
    Field f;
    f.goals = goals & ~walls;
    bitboard visited;
    f.steps.compute(walls, f.goals, visited);
    return f;
}

inline std::uint64_t fuel() { return cambc::fuel_remaining(); }

// Generous: a full field measured 2-13k on the competition maps.
inline std::uint64_t field_cost_estimate() {
    return 4ull * static_cast<std::uint64_t>(cambc::map::width() * cambc::map::height()) + 4000;
}
inline constexpr std::uint64_t small_cost_estimate = 5000;

// Generous. Measured: ~1 fuel per 4 map tiles to set up, then ~1 per 64 tiles per layer.
inline std::uint64_t search_cost_estimate(int layers) {
    const auto area = static_cast<std::uint64_t>(cambc::map::width() * cambc::map::height());
    return area / 2 + 1000 + static_cast<std::uint64_t>(layers) * (area / 32 + 40);
}

inline bool fuel_ok(std::uint64_t needed) { return fuel() >= needed; }

// WASI randomness is always zero in matches, so seed from our spawn and this instance's start.
inline std::uint32_t random_seed() {
    const auto spawn = cambc::map::spawn_region(team::ally).positions()[0];
    std::uint32_t seed = spawn.x * 73856093u ^ spawn.y * 19349663u;
    if (!cambc::is_draft()) {
        const auto start = cambc::self().position();
        seed ^= start.x * 83492791u ^ start.y * 2654435761u;
    }
    return seed;
}

// PCG32. Seeding std::mt19937 alone costs about 15k fuel in WASM.
class Rng {
public:
    explicit Rng(std::uint64_t seed) : state_{seed + 0x853c49e6748fea9bULL} { next(); }
    std::uint32_t next() {
        const std::uint64_t old = state_;
        state_ = old * 6364136223846793005ULL + 1442695040888963407ULL;
        const auto xorshifted = static_cast<std::uint32_t>(((old >> 18u) ^ old) >> 27u);
        const auto rot = static_cast<std::uint32_t>(old >> 59u);
        return (xorshifted >> rot) | (xorshifted << ((32u - rot) & 31u));
    }

private:
    std::uint64_t state_;
};

inline Rng& rng() {
    static Rng generator{random_seed()};
    return generator;
}

inline unsigned random_below(unsigned limit) {
    return static_cast<unsigned>((static_cast<std::uint64_t>(rng().next()) * limit) >> 32);
}

inline void draw_dot(vec2 p, std::uint32_t rgb) {
    if constexpr (debug_draw) cambc::debug::draw_dot(p, rgb);
}

inline void draw_line(vec2 a, vec2 b, std::uint32_t rgb) {
    if constexpr (debug_draw) cambc::debug::draw_line(a, b, rgb);
}

// Samples print together at the end of the turn, so printing does not skew them.
struct FuelSample {
    const char* label;
    std::uint32_t round;
    std::uint64_t used;
    bool spilled;
};

inline std::vector<FuelSample>& fuel_log() {
    static std::vector<FuelSample> log;
    return log;
}

class FuelMeter {
public:
    explicit FuelMeter(const char* label) : label_{label} {
        if constexpr (debug_fuel) {
            start_ = fuel();
            round_ = cambc::round_number();
        }
    }
    ~FuelMeter() {
        if constexpr (debug_fuel) {
            const auto now = fuel();
            const bool spilled = cambc::round_number() != round_;
            fuel_log().push_back({label_, round_, spilled ? 0 : start_ - now, spilled});
        }
    }
    FuelMeter(const FuelMeter&) = delete;
    FuelMeter& operator=(const FuelMeter&) = delete;

private:
    const char* label_;
    std::uint64_t start_ = 0;
    std::uint32_t round_ = 0;
};

// A meter still open when this runs is reported on the next line.
inline void print_fuel_log() {
    if constexpr (debug_fuel) {
        std::cout << "fuel r" << cambc::round_number() << " c"
                  << (cambc::is_draft() ? -1 : static_cast<int>(static_cast<cambc::handle_champion_t>(cambc::self())));
        auto& log = fuel_log();
        for (std::size_t i = 0; i < log.size(); ++i) {
            if (!log[i].label) continue;
            std::cout << ' ' << log[i].label << '=';
            if (log[i].spilled) {
                std::cout << "SPILLED(r" << log[i].round << ')';
                continue;
            }
            std::uint64_t total = log[i].used;
            int count = 1;
            for (std::size_t j = i + 1; j < log.size(); ++j)
                if (log[j].label == log[i].label && !log[j].spilled) total += log[j].used, ++count, log[j].label = nullptr;
            std::cout << total;
            if (count > 1) std::cout << '/' << count;
        }
        std::cout << " left=" << fuel() << '\n';
        fuel_log().clear();
    }
}

} // namespace aph
