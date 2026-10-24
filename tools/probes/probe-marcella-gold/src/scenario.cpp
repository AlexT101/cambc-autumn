// Scenario script (see main.cpp). 00collision: group 4 = wolf (19,13) + gold (20,13) + gem (19,14);
// group 6 = wolf (24,18) + gems (24,19), (25,18); altar (27,20).
#include "bot.h"

using cambc::champion_draft;
using cambc::champion_type;
using S = Step;

std::vector<champion_draft> scenario_draft() {
    return {champion_draft::marcella, champion_draft::vendetta, champion_draft::varg};
}

std::vector<Step> scenario_script(champion_type who) {
    const cambc::vec2 g4{19, 13}, g6{24, 18}, altar{27, 20};
    if (who == champion_type::marcella)
        return {S{Op::kill, g4}, S{Op::go, g4}, S{Op::wait_reward},
                S{Op::kill, g6}, S{Op::go, g6}, S{Op::wait_reward},
                S{Op::tribute, altar},                       // control: no gold bonus
                S{Op::buy_treasure, {}, 5},
                S{Op::kill, g4}, S{Op::go, g4}, S{Op::wait_reward, {}, 300},
                S{Op::kill, g6}, S{Op::go, g6}, S{Op::wait_reward, {}, 300},
                S{Op::tribute, altar},                       // with the Treasure emblem
                S{Op::kill, g4}, S{Op::go, g4}, S{Op::wait_reward, {}, 300},
                S{Op::tribute, altar},                       // 11 gems: does the previous 0.6 carry over?
                S{Op::idle}};
    return {S{Op::kill, g4}, S{Op::kill, g6}, S{Op::wait_alive, g4}, S{Op::kill, g4},
            S{Op::wait_alive, g6}, S{Op::kill, g6}, S{Op::wait_alive, g4}, S{Op::kill, g4}, S{Op::idle}};
}
