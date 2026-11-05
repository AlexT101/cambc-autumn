// Who a monster hits (rules camps.attack): each awake monster attacks the nearest champion of either
// team within its own reach, a tie to the one acting first in that round's order. Camp phase R comes
// before R's turns (rules rounds.sequence), so a champion stands there where it stands now, unless a
// recall or teleport completes at its turn start before then (channel_end_round < R): a recall takes
// it home, a teleport to its landing. Dead and unseen champions count as none.
#pragma once
#include <limits>
#include "world.h"

namespace aph {

// The champions besides the one asked about that may take a monster's hit in camp phase `round`.
struct CampField {
    enum class Foes : std::uint8_t {
        seen, // every enemy in sight, where it stands
        held, // only those held in place until the phase: acted this round, or channelling
        none, // no enemy: a caller that does not lean on one staying
    };
    int round;
    const ChampionBelief* asked = nullptr; // never its own rival
    bool self = false;                     // us, at my_position(): when the one asked about is an ally
    bool allies = true;                    // the other allies in sight
    Foes foes = Foes::seen;
    vec2 dead{-1, -1}; // an enemy killed this turn, which the beliefs still hold alive
};

// c stands in place for camp phase `round`: alive, in sight, and no recall or teleport completing before it.
inline bool camp_present(const ChampionBelief& c, int round) {
    return c.alive && c.visible && !((c.channel == Channel::recall || c.channel == Channel::teleport) && c.channel_end_round < round);
}

struct NoSkip {
    bool operator()(const ChampionBelief&) const { return false; }
};

// Each champion of `f` with its tile, until `fn` returns true; `skip` leaves out more (a Safety's
// enemies killed this turn).
template <class Fn, class Skip = NoSkip> bool each_camp_rival(const World& world, const CampField& f, Fn&& fn, Skip&& skip = {}) {
    if (f.self && f.asked != &world.me() && fn(world.me(), my_position())) return true;
    if (f.allies)
        for (const auto& o : world.allies)
            if (!o.is_self && &o != f.asked && camp_present(o, f.round) && !skip(o) && fn(o, o.pos)) return true;
    if (f.foes != CampField::Foes::none)
        for (const auto& o : world.enemies)
            if (&o != f.asked && camp_present(o, f.round) && o.pos != f.dead
                && (f.foes == CampField::Foes::seen || o.acted || o.channel != Channel::none) && !skip(o) && fn(o, o.pos))
                return true;
    return false;
}

// The nearest of a field's champions within a monster's reach, the first to act in f.round among
// those as near.
struct CampRival {
    int d = unreachable; // none within the reach
    int slot = std::numeric_limits<int>::max();
    const ChampionBelief* who = nullptr;
};

// Whether a champion d from a monster of reach `reach`, at `slot` in the phase round's order, is the
// one it hits rather than rival r.
constexpr bool camp_picks(int d, int slot, int reach, const CampRival& r) {
    return d <= reach && (d < r.d || (d == r.d && slot < r.slot));
}

template <class Skip = NoSkip> CampRival camp_rival(const World& world, vec2 m, int reach, const CampField& f, Skip&& skip = {}) {
    CampRival r;
    each_camp_rival(
        world, f,
        [&](const ChampionBelief& o, vec2 p) {
            const int d = dist(m, p);
            if (d > reach || d > r.d) return false;
            const int s = world.slot(o, f.round);
            if (d < r.d || s < r.slot) r = {d, s, &o};
            return false;
        },
        skip);
    return r;
}

// camp_picks against camp_rival, stopping at the first rival that takes the hit.
template <class Skip = NoSkip> bool camp_takes(const World& world, vec2 m, int reach, int d, int slot, const CampField& f, Skip&& skip = {}) {
    if (d > reach) return false;
    return !each_camp_rival(
        world, f,
        [&](const ChampionBelief& o, vec2 p) {
            const int od = dist(m, p);
            return od < d || (od == d && world.slot(o, f.round) < slot);
        },
        skip);
}

} // namespace aph
