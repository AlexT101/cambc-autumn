#pragma once
#include "builds.h"

namespace shop {
    // On spawn: our build's shards, as many as the gold buys, each kind up to its emblem.
    inline void try_buy() {
        if (!util::on_spawn())
            return;
        static const u32 cost = it(it::power_shard_of_health).cost(); // every shard's
        static const build b = build_of(champs::my_info().type);
        cambc::enum_map<it> held = champs::my_info().items;
        u32 gold = champs::my_info().gold;
        while (gold >= cost) {
            const it s = choose_shard(b, held);
            const u32 n = std::min(gold / cost, shards_per_emblem - held[s]);
            channel::drop(); // the engine refuses a buy while recalling (error 34)
            g::me().buy(s, n);
            gold -= n * cost;
            if ((held[s] += n) == shards_per_emblem)
                held[s] = 0, ++held[emblem_of(s)];
        }
    }
} // namespace shop
