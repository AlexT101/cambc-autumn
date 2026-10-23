#pragma once
#include <cambc.h>
#include <functional>
#include <string>
#include <vector>

// One scripted step. Scenarios (scenario.cpp) give each champion a list of steps.
//  kill: attack the group owning `tile` until it is reward_available     go: walk to `tile`
//  wait: stay `n` turns    until: stay until round >= n    wait_reward: stay until gold/gems change (timeout n, default 40)
//  buy: walk to own spawn (unless n2 == 1: buy in place) and buy `n` copies of item `item`, logging health around each buy
//  buy_lock: walk to own spawn and buy an altar lock      tribute: walk next to altar `tile`, start tribute, wait until done
//  place_lock: use the altar lock on altar `tile` (from the current tile)     recall: recall and wait until home
//  fn: custom lambda, returns true when finished     idle: forever
enum class Op { kill, go, wait, until, wait_reward, buy, buy_lock, tribute, place_lock, recall, fn, idle };
struct Step {
    Op op;
    cambc::vec2 tile{0, 0};
    int n = 0;
    int item = 0;
    int n2 = 0;
    std::function<bool(int)> f = nullptr;  // Op::fn: called with turns spent in the step
};

std::vector<cambc::champion_draft> scenario_draft();
std::vector<Step> scenario_script(cambc::champion_type who);

// Helpers shared with scenario.cpp
void probe_prefix(const char* what);
std::string err_str(const std::exception& e);
bool move_towards_closest(cambc::bitboard goals);
cambc::bitboard around(cambc::vec2 p, int r);
int group_of(cambc::vec2 tile);
std::string group_state(int g);
void log_camps_near(cambc::vec2 p, int r);
void log_locks();

class Bot {
    bool init = false;
    std::vector<Step> script;
    std::size_t idx = 0;
    int turns_in_step = 0;
    std::uint32_t gold0 = 0, gems0 = 0;
    void log_turn();
    bool run_step(const Step& s);  // returns true when the step is finished
public:
    int watch_group = -1;   // group handle logged every turn
    void play_turn();
};
