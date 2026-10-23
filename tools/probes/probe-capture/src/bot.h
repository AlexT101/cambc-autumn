#pragma once
#include <cambc.h>
#include <vector>

// One scripted step. Scenarios (scenario.cpp) give each champion a list of steps.
//  kill: attack the group owning `tile` until it is reward_available
//  go: walk to `tile`;  wait: stay `n` turns;  wait_reward: stay until gold/gems change (timeout n, default 40)
//  buy_treasure: walk to own spawn and buy `n` treasure shards of strength
//  tribute: walk next to altar `tile`, start tribute, wait until finished
//  wait_alive: stay until the watched group is alive again (timeout n, default 200);  idle: forever
enum class Op { kill, go, wait, wait_reward, buy_treasure, tribute, wait_alive, idle };
struct Step { Op op; cambc::vec2 tile{0, 0}; int n = 0; };

std::vector<cambc::champion_draft> scenario_draft();
std::vector<Step> scenario_script(cambc::champion_type who);

class Bot {
    bool init = false;
    std::vector<Step> script;
    std::size_t idx = 0;
    int turns_in_step = 0;
    std::uint32_t gold0 = 0, gems0 = 0;
    int watch_group = -1;   // group handle logged every turn
    void log_turn();
    bool run_step(const Step& s);  // returns true when the step is finished
public:
    void play_turn();
};
