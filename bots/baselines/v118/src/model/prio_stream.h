#pragma once
// Live builds only (written in by stream_patch.py; never in git): our priorities as replays show them,
// coded from a secret key and facts every ally knows at round 1. A successor to prio_mask.h.
//
// A priority is rank << 16 | payload. Coded:
// - the payload's low 14 bits are xored with a mask drawn per round and champion; its top 2 bits (0
//   plain) carry the round mod 4, so a reader knows which round's mask to undo (exact for a value up to
//   3 rounds old). Every turn publishes, so the payload never shows the same number twice running.
// - the rank goes through a strictly increasing map drawn once per game that keeps the sign: each idle
//   or negative rank code (99.7% of values) starts a random distance above the last (k to ~400-500,
//   against 8 plain); the protect and kill bands above keep plain steps. Ranks written in any rounds compare
//   as the plain ones, so the engine's order and every comparison World and turn_order make on ranks
//   as read are unchanged. Not per round: a rank that changes every round makes World re-rank the team
//   every round (rank_turns, ~+640 fuel a turn), and allies would need to decode each other's.
// packed() (payload plain) is what turn_order compares ranks with; publish() adds the mask and tag once a turn.
#include <cstdint>

namespace aph {
class World;
}

namespace aph::prio_stream {

inline constexpr std::uint64_t key[2] = {0x3736373637363736ull, 0x3736373637363736ull};
inline constexpr bool on = key[0] != 0 || key[1] != 0;

inline std::uint64_t mix(std::uint64_t z) {
    z = (z ^ (z >> 30)) * 0xbf58476d1ce4e5b9ull;
    z = (z ^ (z >> 27)) * 0x94d049bb133111ebull;
    return z ^ (z >> 31);
}

// Plain rank hi = q * 8 + 7 - index; s = (hi & 7) - sub orders the k bodies within a code q (0 to k - 1).
// q in [0, npos): y = 1 + pos[q] + s. q >= npos: y = 1 + pos[npos] + (q - npos) * k + s.
// q < 0, u = -1 - q: y = -(1 + neg[u] + k - 1 - s).
struct Game {
    std::uint64_t seed = 0;
    std::int32_t k = 8, sub = 0, npos = 0, nneg = 0;
    std::uint32_t tag = 0;
    std::int32_t pos[64] = {}, neg[64] = {};
    // rank_of's: code q < npos is base[q + nneg] + s; above, top + q * k + s.
    std::int32_t base[128] = {}, top = 0;
};
inline Game game;
struct Round {
    std::int32_t w = -(1 << 30);
    std::uint64_t mask = 0; // champion i's is bits 7i to 7i + 13
};
inline Round rounds[4];

// t[0] uniform in [0, avail / 4), then n steps each k plus uniform in [0, e): t[n] <= avail.
inline void draw(std::int32_t* t, int n, std::int32_t avail, std::uint64_t seed) {
    const std::int32_t e = n > 0 ? (avail - avail / 4) / n - game.k : 0;
    std::uint64_t h = mix(seed);
    t[0] = static_cast<std::int32_t>(((h & 0xffff) * static_cast<std::uint64_t>(avail / 4)) >> 16);
    for (int i = 1, left = 3; i <= n; ++i, --left) {
        if (left == 0) h = mix(h ^ seed), left = 4;
        h >>= 16;
        t[i] = t[i - 1] + game.k + (e > 0 ? static_cast<std::int32_t>(((h & 0xffff) * static_cast<std::uint64_t>(e)) >> 16) : 0);
    }
}

// The code for one game: seed, plain ranks hi in [hi_min, hi_max] (hi_min a multiple of 8), the protect band's
// first hi (a multiple of 8), the team's bodies (Cassi and Issac apart). False if the ranges don't fit.
inline bool make(std::uint64_t seed, std::int32_t hi_min, std::int32_t hi_max, std::int32_t hi_protect, int champions) {
    game.seed = mix(seed ^ key[0]);
    game.k = champions < 1 ? 1 : champions > 8 ? 8 : champions;
    game.sub = 8 - game.k;
    game.npos = hi_protect >> 3;
    game.nneg = -(hi_min >> 3);
    const std::int32_t above = ((hi_max >> 3) - game.npos + 1) * game.k; // the protect and kill bands' span
    if (game.npos < 0 || game.npos > 63 || game.nneg < 1 || game.nneg > 64 || above > 32000) return false;
    draw(game.pos, game.npos, 32766 - above, game.seed ^ 0x51);
    draw(game.neg, game.nneg - 1, 32768 - game.k, game.seed ^ 0x52);
    for (int q = -game.nneg; q < game.npos; ++q)
        game.base[q + game.nneg] = q < 0 ? -(game.neg[-1 - q] + game.k) : 1 + game.pos[q];
    game.top = 1 + game.pos[game.npos] - game.npos * game.k;
    game.tag = static_cast<std::uint32_t>(mix(game.seed ^ 0x7a6)) & 3;
    for (auto& r : rounds) r.w = -(1 << 30);
    return true;
}

void setup(const World& world); // turn_order.cc: make() with this game's seed and the rank range; once, at World's init

// Coded plain rank hi.
inline std::int32_t rank_of(std::int32_t hi) {
    const std::int32_t q = hi >> 3, s = (hi & 7) - game.sub;
    return q < game.npos ? game.base[q + game.nneg] + s : game.top + q * game.k + s;
}

// packed_priority's value for plain rank hi over `payload`: never 0.
inline std::int32_t packed(std::int32_t hi, std::uint32_t payload) {
    return static_cast<std::int32_t>(static_cast<std::uint32_t>(rank_of(hi)) << 16 | payload);
}

// Kept by tag: of the rounds a reader can meet, (now - 4, now], one has each tag.
inline std::uint32_t tag_of(std::int32_t w) { return (static_cast<std::uint32_t>(w) + game.tag) & 3; }
inline const Round& round_code(std::int32_t w, std::uint32_t tag) {
    Round& r = rounds[tag];
    if (r.w != w) r.w = w, r.mask = mix(game.seed ^ static_cast<std::uint64_t>(w) * 0x9e3779b97f4a7c15ull);
    return r;
}

// Champion `index`'s 14-bit payload mask: overlapping windows of one draw, so any two champions' masks still
// differ by a random xor.
inline std::uint32_t mask_of(const Round& r, int index) {
    return static_cast<std::uint32_t>(r.mask >> ((index & 7) * 7)) & 0x3fff;
}

// A packed() value as champion `index` publishes it in round w.
inline std::int32_t publish(std::int32_t v, std::int32_t w, int index) {
    const std::uint32_t tag = tag_of(w);
    const std::uint32_t payload = (static_cast<std::uint32_t>(v) & 0x3fff) ^ mask_of(round_code(w, tag), index);
    return static_cast<std::int32_t>((static_cast<std::uint32_t>(v) & 0xffff0000u) | tag << 14 | payload);
}

// The plain payload of champion `index`'s published value `v` (not 0), read in round `now`.
inline std::uint32_t payload_of(std::int32_t v, std::int32_t now, int index) {
    const std::uint32_t tag = (static_cast<std::uint32_t>(v) >> 14) & 3;
    const Round* r = &rounds[tag];
    // Else the latest round up to now with this tag.
    if (static_cast<std::uint32_t>(now - r->w) >= 4) r = &round_code(now - static_cast<std::int32_t>((tag_of(now) - tag) & 3), tag);
    return (static_cast<std::uint32_t>(v) ^ mask_of(*r, index)) & 0x3fff;
}

// A published value, plain (tools and tests).
inline std::int32_t decode(std::int32_t v, std::int32_t now, int index) {
    if (v == 0) return 0;
    const std::int32_t y = v >> 16;
    // The last entry of t[0..n) at most m.
    const auto find = [](const std::int32_t* t, int n, std::int32_t m) {
        int lo = 0;
        for (int step = 32; step; step >>= 1)
            if (lo + step < n && t[lo + step] <= m) lo += step;
        return lo;
    };
    std::int32_t q, s;
    if (y > 0 && y - 1 >= game.pos[game.npos]) {
        const std::int32_t x = y - 1 - game.pos[game.npos];
        q = game.npos + x / game.k, s = x % game.k;
    } else if (y > 0) {
        q = find(game.pos, game.npos, y - 1), s = y - 1 - game.pos[q];
    } else {
        const std::int32_t m = -y - 1, u = find(game.neg, game.nneg, m);
        q = -1 - u, s = game.k - 1 - (m - game.neg[u]);
    }
    return static_cast<std::int32_t>(static_cast<std::uint32_t>(q * 8 + s + game.sub) << 16 | payload_of(v, now, index));
}

} // namespace aph::prio_stream
