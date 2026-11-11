// Emblem passives: which families an item set holds, and the damage factors ours give.
#pragma once
#include "util.h"

namespace aph {

// `owned` holds an emblem of `family` (cambc::item_family's order, which the item enum's layout follows).
inline bool has_family(const cambc::enum_map<cambc::item_type>& owned, int family) {
    const auto emblem = [&](int stat) { return owned[cambc::item_type{static_cast<std::uint32_t>(family * 6 + stat * 2 + 1)}]; };
    return emblem(0) + emblem(1) + emblem(2) > 0;
}

inline constexpr float monster_camp_dealt = 1.15f; // damage to camps from a Monster emblem's owner
inline constexpr float skirmish_dealt = 1.1f;      // damage to champions from a Skirmish emblem's owner
inline constexpr float collectors_dealt = 0.01f;   // extra damage per emblem family (its own included) a Collectors emblem's owner has

// Damage dealt per point owning `owned` and an emblem of `added` (-1: none), to champions and to camps.
struct Dealt {
    float champion, camp;
};
[[gnu::always_inline]] inline Dealt dealt_with(const cambc::enum_map<cambc::item_type>& owned, int added = -1) {
    using F = cambc::item_family;
    const auto owns = [&](F family) { return added == static_cast<int>(family) || has_family(owned, static_cast<int>(family)); };
    Dealt d{owns(F::skirmish) ? skirmish_dealt : 1.0f, owns(F::monster) ? monster_camp_dealt : 1.0f};
    // Collectors: 1% per emblem family owned, its own included. Branched: rarely owned.
    if (owns(F::collectors)) {
        int families = added >= 0 && !has_family(owned, added);
        for (int f = 0; f <= static_cast<int>(F::collectors); ++f) families += has_family(owned, f);
        const float scale = 1.0f + collectors_dealt * static_cast<float>(families);
        d.champion *= scale;
        d.camp *= scale;
    }
    return d;
}

// Our purchases so far (shop.cc's buy, counted before the call): our items change only with one.
inline unsigned items_bought = 0;

// Ours, as of our last purchase; defined in economy/camps.cc.
// Camps hit a Jungle emblem's owner 30% softer, and a Durability emblem's 10%.
float camp_hit_factor();
// A Monster emblem's owner hits camps 15% harder, a Collectors one 1% per emblem family owned.
float camp_dealt_factor();
// A Skirmish emblem's owner hits champions 5% harder, a Collectors one 1% per emblem family owned.
float champion_dealt_factor();

} // namespace aph
