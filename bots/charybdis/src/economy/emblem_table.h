#pragma once
// learned_arm[picks - 3][champion_type][ordinal]: family * 3 + stat of the champion's ordinal-th new emblem, or
// 255 for the current logic's choice. Round 2 of the emblem lab (tools/emblab candidate.py --flat,
// dmodel-dr.policy2.json [0-2] over the round-1 table), then Skirmish in the type's usual stat at ordinal 4 of
// the 37 rows with none by then (research/ideas-2026-11-10/emblab4/collectors.py --family skirmish --at 4).
// Round 5 (tools/emblab elab.py, CHANGES 504): Prism's rows to the current logic; Collectors in the type's usual stat
// at ordinal 8 of the rows with none by then (not Vesper Vale's); Issac's ordinal 0 Durability-Health; Vesper Vale's
// ordinal 7 Collectors-Health (4 and 5 picks).
#include <cstdint>

namespace aph {

inline constexpr std::uint8_t learned_arm[3][13][12] = {
    {
        {255, 2, 2, 41, 35, 41, 41, 17, 14, 1, 29, 30}, // ryth
        {255, 255, 26, 0, 33, 0, 39, 39, 20, 255, 3, 15}, // vesper_vale
        {255, 255, 255, 12, 35, 41, 15, 41, 17, 17, 32, 16}, // vendetta
        {1, 255, 1, 40, 34, 40, 40, 20, 255, 255, 255, 7}, // cassi
        {8, 32, 2, 23, 35, 23, 23, 18, 41, 255, 9, 255}, // issac
        {255, 255, 255, 255, 34, 1, 28, 255, 40, 19, 255, 255}, // stellar
        {255, 255, 255, 255, 255, 255, 255, 17, 40, 255, 255, 39}, // prism
        {255, 25, 14, 27, 34, 40, 40, 40, 255, 31, 2, 7}, // marcella
        {255, 13, 25, 23, 35, 17, 31, 6, 41, 255, 255, 17}, // willow
        {255, 12, 255, 19, 33, 27, 17, 27, 39, 255, 20, 255}, // ren
        {255, 5, 255, 255, 33, 255, 0, 35, 39, 41, 15, 39}, // varg
        {27, 10, 255, 2, 33, 3, 16, 16, 39, 9, 255, 41}, // tavi
        {255, 255, 8, 40, 34, 7, 0, 39, 255, 32, 14, 255}, // heart_of_ruin
    },
    {
        {255, 20, 26, 26, 35, 2, 39, 17, 18, 41, 1, 255}, // ryth
        {255, 255, 12, 14, 33, 8, 35, 41, 39, 20, 41, 17}, // vesper_vale
        {255, 255, 255, 0, 35, 0, 29, 41, 255, 29, 255, 10}, // vendetta
        {255, 255, 8, 16, 34, 6, 16, 16, 40, 33, 255, 255}, // cassi
        {8, 11, 32, 23, 35, 23, 20, 6, 41, 255, 39, 255}, // issac
        {255, 255, 5, 11, 34, 255, 15, 255, 40, 255, 255, 255}, // stellar
        {255, 255, 255, 255, 255, 255, 255, 17, 40, 255, 255, 39}, // prism
        {255, 28, 7, 1, 34, 13, 1, 1, 40, 255, 255, 4}, // marcella
        {255, 8, 14, 6, 35, 7, 3, 23, 41, 255, 22, 255}, // willow
        {18, 255, 255, 24, 33, 255, 12, 40, 17, 255, 40, 27}, // ren
        {27, 255, 255, 255, 33, 6, 10, 17, 39, 255, 255, 5}, // varg
        {27, 30, 25, 0, 33, 16, 32, 9, 39, 255, 0, 30}, // tavi
        {255, 255, 8, 7, 34, 25, 2, 40, 255, 0, 41, 255}, // heart_of_ruin
    },
    {
        {255, 14, 8, 2, 35, 18, 20, 20, 41, 255, 255, 255}, // ryth
        {255, 255, 0, 0, 33, 17, 0, 41, 39, 20, 41, 23}, // vesper_vale
        {255, 14, 29, 0, 35, 0, 9, 23, 41, 35, 18, 22}, // vendetta
        {20, 255, 255, 16, 34, 16, 16, 31, 40, 255, 10, 30}, // cassi
        {8, 255, 29, 41, 35, 23, 23, 30, 6, 255, 255, 255}, // issac
        {255, 15, 255, 5, 34, 255, 255, 7, 40, 255, 255, 255}, // stellar
        {255, 255, 255, 255, 255, 255, 255, 17, 40, 255, 255, 39}, // prism
        {28, 7, 28, 13, 34, 13, 40, 2, 255, 22, 0, 255}, // marcella
        {255, 14, 14, 28, 35, 23, 21, 7, 41, 4, 7, 3}, // willow
        {18, 14, 6, 12, 35, 12, 12, 12, 39, 255, 255, 4}, // ren
        {255, 255, 13, 6, 33, 6, 6, 6, 39, 1, 255, 1}, // varg
        {27, 30, 6, 24, 33, 31, 13, 13, 39, 255, 30, 3}, // tavi
        {255, 255, 8, 18, 34, 1, 7, 7, 40, 33, 20, 255}, // heart_of_ruin
    }
};

}
