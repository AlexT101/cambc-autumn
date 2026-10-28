// Emblem passives: which families an item set holds, and the damage factors ours give.
#pragma once
#include "util.h"

namespace aph {

// `owned` holds an emblem of `family` (cambc::item_family's order, which the item enum's layout follows).
inline bool has_family(const cambc::enum_map<cambc::item_type>& owned, int family) {
    const auto emblem = [&](int stat) { return owned[cambc::item_type{static_cast<std::uint32_t>(family * 6 + stat * 2 + 1)}]; };
    return emblem(0) + emblem(1) + emblem(2) > 0;
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
