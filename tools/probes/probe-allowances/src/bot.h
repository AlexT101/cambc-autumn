#pragma once
#include "probe.h"
// Per-champion scripted probe; the script is built on the first turn from the champion type.
class Bot {
    bool built = false;
    probe::Script script;
public:
    void play_turn();
};
