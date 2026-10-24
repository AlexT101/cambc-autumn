// Scenario scripts. Select with scenario.h (SCENARIO); run.sh rewrites it per run:
//   bash tools/probes/probe-capture/run.sh <n> <map> <rounds>
// 1 collision 200: timing + diagonal-adjacent tile + respawn      2 collision 200: timer reset + occupied respawn
// 3/4/5 packs 200: 3-way split (no Vesper / Vesper id1 / Vesper id0) + tribute + recapture
// 6 collision 400: Vesper and Vendetta Treasure emblem captures + 44-gem tribute   7 packs 2000: all idle (passive gold)
// 8 elkring 200: elk+gold group split/respawn (Marcella idles on the elk tile, so respawn stays blocked)
// 9 collision 60: orthogonal-adjacent tile
#include "bot.h"
#include "scenario.h"

using cambc::champion_draft;
using cambc::champion_type;
using S = Step;

std::vector<champion_draft> scenario_draft() {
    switch (SCENARIO) {
    case 1: case 2: case 3: return {champion_draft::vendetta, champion_draft::ryth, champion_draft::varg};
    case 4: return {champion_draft::vendetta, champion_draft::vesper_vale, champion_draft::varg};
    case 5: return {champion_draft::vesper_vale, champion_draft::vendetta, champion_draft::varg};
    case 6: case 7: return {champion_draft::vesper_vale, champion_draft::vendetta, champion_draft::ryth};
    case 8: return {champion_draft::ryth, champion_draft::vendetta, champion_draft::varg, champion_draft::marcella, champion_draft::ren};
    case 9: return {champion_draft::vendetta, champion_draft::ryth, champion_draft::varg};
    case 10: return {champion_draft::marcella, champion_draft::ryth, champion_draft::varg};
    default: return {champion_draft::vendetta, champion_draft::ryth, champion_draft::varg};
    }
}

std::vector<Step> scenario_script(champion_type who) {
    const cambc::vec2 gc1{12, 7};   // collision gold cluster, group 8 (35 gold)
    switch (SCENARIO) {
    case 1:  // timing, adjacent-tile region test, respawn count after stepping off
        if (who == champion_type::vendetta)
            return {S{Op::kill, gc1}, S{Op::wait, {}, 8}, S{Op::go, gc1}, S{Op::wait_reward}, S{Op::go, {11, 6}},
                    S{Op::wait_alive}, S{Op::idle}};
        return {S{Op::idle}};
    case 2:  // timer reset by leaving one round; then stay on the tile to test respawn delay
        if (who == champion_type::vendetta)
            return {S{Op::kill, gc1}, S{Op::go, gc1}, S{Op::wait, {}, 3}, S{Op::go, {11, 6}}, S{Op::go, gc1},
                    S{Op::wait_reward}, S{Op::wait, {}, 70}, S{Op::go, {11, 6}}, S{Op::wait_alive}, S{Op::idle}};
        return {S{Op::idle}};
    case 3: case 4: case 5: {  // packs group 2 (2 gold + 2 gem clusters: 70 gold, 48 gems) split 3 ways, then tribute
        const auto order = scenario_draft();
        int role = 0;
        // champion_draft and champion_type numbering differ; map the few we use explicitly.
        auto same = [&](champion_draft d) {
            return (d == champion_draft::vendetta && who == champion_type::vendetta) ||
                   (d == champion_draft::ryth && who == champion_type::ryth) ||
                   (d == champion_draft::varg && who == champion_type::varg) ||
                   (d == champion_draft::vesper_vale && who == champion_type::vesper_vale);
        };
        for (int i = 0; i < 3; ++i) if (same(order[i])) role = i;
        const cambc::vec2 tiles[3] = {{11, 17}, {12, 18}, {11, 18}};
        const cambc::vec2 altars[3] = {{2, 15}, {2, 24}, {2, 6}};
        // Second capture after respawn checks whether fractional gold carries over (hidden accumulator).
        return {S{Op::kill, {11, 17}}, S{Op::go, tiles[role]}, S{Op::wait_reward}, S{Op::tribute, altars[role]},
                S{Op::kill, {11, 17}}, S{Op::go, tiles[role]}, S{Op::wait_reward}, S{Op::idle}};
    }
    case 6: {  // collision: Vesper and Vendetta farm 150+ gold, buy a Treasure emblem, then capture again
        auto cap = [](std::vector<Step>& v, cambc::vec2 t) {
            v.push_back(S{Op::kill, t}); v.push_back(S{Op::go, t}); v.push_back(S{Op::wait_reward});
        };
        std::vector<Step> v;
        if (who == champion_type::vesper_vale) {
            cap(v, {10, 5}); cap(v, {12, 7}); v.push_back(S{Op::buy_treasure, {}, 5}); cap(v, {10, 5});
            v.push_back(S{Op::tribute, {27, 20}});
        } else if (who == champion_type::vendetta) {
            cap(v, {19, 13}); cap(v, {22, 16}); cap(v, {17, 11}); v.push_back(S{Op::buy_treasure, {}, 5}); cap(v, {15, 9});
        }
        v.push_back(S{Op::idle});
        return v;
    }
    case 10: {  // Marcella tribute before and after Treasure; balance, gems, and item inventory logged each turn.
        auto cap = [](std::vector<Step>& v, cambc::vec2 t) {
            v.push_back(S{Op::kill, t}); v.push_back(S{Op::go, t}); v.push_back(S{Op::wait_reward});
        };
        std::vector<Step> v;
        if (who == champion_type::marcella) {
            cap(v, {10, 5}); cap(v, {12, 7});
            v.push_back(S{Op::tribute, {27, 20}}); // pre-Treasure comparison
            cap(v, {19, 13}); cap(v, {22, 16});
            v.push_back(S{Op::buy_treasure, {}, 5});
            cap(v, {17, 11}); cap(v, {15, 9});
            v.push_back(S{Op::tribute, {27, 20}}); // post-Treasure comparison
        }
        v.push_back(S{Op::idle});
        return v;
    }
    case 8: {  // elkring: 5 champions kill elk(3,6)+gold cluster(3,7) (195 gold, 36 gems); two capture; watch respawn
        if (who == champion_type::ryth)
            return {S{Op::kill, {3, 6}}, S{Op::go, {3, 6}}, S{Op::wait_reward}, S{Op::go, {4, 5}}, S{Op::wait_alive}, S{Op::idle}};
        if (who == champion_type::vendetta)
            return {S{Op::kill, {3, 6}}, S{Op::go, {3, 7}}, S{Op::wait_reward}, S{Op::go, {4, 8}}, S{Op::wait_alive}, S{Op::idle}};
        return {S{Op::kill, {3, 6}}, S{Op::idle}};
    }
    case 9:  // orthogonally adjacent tile (11,7) does not capture either?
        if (who == champion_type::vendetta)
            return {S{Op::kill, gc1}, S{Op::go, {11, 7}}, S{Op::wait, {}, 8}, S{Op::go, gc1}, S{Op::wait_reward}, S{Op::idle}};
        return {S{Op::idle}};
    default: return {S{Op::idle}};
    }
}
