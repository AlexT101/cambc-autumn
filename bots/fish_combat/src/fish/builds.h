// Fish's emblem builds (FISH_MODEL 3.2; drafts-emblems-games.json.gz's modal formation orders) and
// its shopping rule (8.4): every shop spends floor(gold / 30) on shards in this order, finishing
// each emblem before the next, never saving for one. After the list, `repeat` cycles.
#pragma once
#include <cambc.h>
#include <cstdint>
#include <span>

namespace aph::fish {

// cambc::item_family's order.
enum Family : std::uint8_t { monster, power, durability, treasure, jungle, home, bruiser, tribute, capture, prospector, hunter, skirmish, greed, collectors };
enum Stat : std::uint8_t { S, F, H }; // cambc::item_stat's order

struct Emblem {
    Family family;
    Stat stat;
};

struct Build {
    std::span<const Emblem> order, repeat;
};

namespace builds {
inline constexpr Emblem cassi[] = {{power, F}, {durability, F}, {bruiser, H}};
inline constexpr Emblem cassi_r[] = {{bruiser, H}};
inline constexpr Emblem issac[] = {{prospector, H}, {bruiser, H}, {durability, H}, {power, S}};
inline constexpr Emblem issac_r[] = {{bruiser, H}};
inline constexpr Emblem hor[] = {{prospector, F}, {capture, H}, {jungle, F}, {monster, F}, {hunter, H}, {bruiser, H}};
inline constexpr Emblem hor_r[] = {{bruiser, H}};
inline constexpr Emblem vendetta[] = {{capture, H}, {jungle, S}, {monster, S}, {hunter, H}, {durability, H}, {collectors, S}, {bruiser, S}, {prospector, H}};
inline constexpr Emblem vendetta_r[] = {{bruiser, S}};
inline constexpr Emblem willow[] = {{prospector, H}, {power, S}, {home, H}, {durability, H}};
inline constexpr Emblem willow_r[] = {{bruiser, H}};
inline constexpr Emblem marcella[] = {{prospector, F}, {treasure, F}, {capture, F}, {jungle, F}, {monster, F},
                                      {bruiser, H}, {durability, H}, {bruiser, F}, {skirmish, H}, {collectors, H}};
inline constexpr Emblem marcella_r[] = {{bruiser, F}, {bruiser, H}};
// Prospector-H in fourth place in 57/96 5-pick games (Prospector-S first in most of the rest).
inline constexpr Emblem vesper[] = {{capture, S}, {treasure, S}, {jungle, S}, {prospector, H}, {monster, S},
                                    {hunter, H}, {durability, H}, {collectors, S}, {bruiser, S}, {bruiser, H}};
inline constexpr Emblem vesper_r[] = {{bruiser, S}, {bruiser, H}};
inline constexpr Emblem prism[] = {{prospector, H}};
inline constexpr Emblem prism_r[] = {{greed, H}};
inline constexpr Emblem ren[] = {{prospector, H}, {bruiser, H}, {durability, H}};
inline constexpr Emblem ren_r[] = {{bruiser, H}};
inline constexpr Emblem varg[] = {{prospector, S}, {jungle, H}, {capture, S}, {home, H}, {power, S}};
inline constexpr Emblem varg_r[] = {{bruiser, S}};
} // namespace builds

// Fish's build for a type, or empty spans for those it never drafts (Ryth, Stellar, Tavi).
constexpr Build build_of(cambc::champion_type t) {
    using T = cambc::champion_type;
    using namespace builds;
    switch (t) {
    case T::cassi: return {cassi, cassi_r};
    case T::issac: return {issac, issac_r};
    case T::heart_of_ruin: return {hor, hor_r};
    case T::vendetta: return {vendetta, vendetta_r};
    case T::willow: return {willow, willow_r};
    case T::marcella: return {marcella, marcella_r};
    case T::vesper_vale: return {vesper, vesper_r};
    case T::prism: return {prism, prism_r};
    case T::ren: return {ren, ren_r};
    case T::varg: return {varg, varg_r};
    default: return {};
    }
}

} // namespace aph::fish
