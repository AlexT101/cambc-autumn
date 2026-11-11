#pragma once
#include "../common/common.h"

// What each champion buys. Every entry is a shard kind; five of a kind combine into its emblem.
// First the emblems in `opening`, in order, then the kinds in `cycle`, in turn, for good. The
// builds are what the top 8 teams buy most with each champion (big-arm's capture, engines
// v1_0_2 and v1_0_3, 7,225 games): passive emblems first (a second of a family adds no second
// passive), then mostly Bruiser, whose 7 points beat Power's 6 when every stat counts.
namespace shop {
    using it = cambc::item_type;
    using ct = cambc::champion_type;

    constexpr u32 shards_per_emblem = 5;

    struct build {
        it opening[4];
        u32 n_opening;
        it cycle[3];
        u32 n_cycle;
    };

    constexpr build build_of(ct t) {
        switch (t) {
            case ct::heart_of_ruin:
                return {{it::treasure_shard_of_health, it::jungle_shard_of_focus,
                         it::bruiser_shard_of_health, it::durability_shard_of_health},
                        4,
                        {it::power_shard_of_focus, it::bruiser_shard_of_focus, it::bruiser_shard_of_health},
                        3};
            case ct::vendetta:
                return {{it::treasure_shard_of_health, it::jungle_shard_of_strength,
                         it::bruiser_shard_of_health, it::durability_shard_of_strength},
                        4,
                        {it::bruiser_shard_of_strength, it::bruiser_shard_of_health},
                        2};
            case ct::vesper_vale:
                return {{it::treasure_shard_of_strength, it::jungle_shard_of_strength,
                         it::durability_shard_of_health},
                        3,
                        {it::power_shard_of_strength, it::bruiser_shard_of_strength},
                        2};
            case ct::cassi:
                return {{it::power_shard_of_focus, it::durability_shard_of_focus}, 2,
                        {it::bruiser_shard_of_health}, 1};
            case ct::issac:
                return {{it::treasure_shard_of_strength, it::power_shard_of_strength,
                         it::home_shard_of_health},
                        3,
                        {it::bruiser_shard_of_strength, it::bruiser_shard_of_health},
                        2};
            case ct::marcella:
                return {{it::treasure_shard_of_health, it::jungle_shard_of_strength,
                         it::bruiser_shard_of_health, it::durability_shard_of_health},
                        4,
                        {it::bruiser_shard_of_health, it::bruiser_shard_of_focus,
                         it::bruiser_shard_of_strength},
                        3};
            default: // a champion we don't draft: gold, camps, then health and strength
                return {{it::treasure_shard_of_health, it::jungle_shard_of_health,
                         it::monster_shard_of_health},
                        3,
                        {it::power_shard_of_strength, it::power_shard_of_health},
                        2};
        }
    }

    // the emblem five shards of `shard` combine into: the next item
    constexpr it emblem_of(it shard) {
        return it(u32(it::enum_type(shard)) + 1);
    }

    // The shard to buy next for b with `held` in hand: the opening's first emblem we don't hold
    // (each entry uses up one we do), else the cycle's kinds in turn, by how many of their
    // emblems are left over.
    inline it choose_shard(const build& b, cambc::enum_map<it> held) {
        for (u32 i = 0; i < b.n_opening; ++i) {
            u32& n = held[emblem_of(b.opening[i])];
            if (n == 0)
                return b.opening[i];
            --n;
        }
        u32 n = 0;
        for (u32 i = 0; i < b.n_cycle; ++i)
            n += held[emblem_of(b.cycle[i])];
        return b.cycle[n % b.n_cycle];
    }
} // namespace shop
