#pragma once

// Per-champion probe state.
class Bot {
    int turns = 0;

public:
    // Dump live self/champion data on the first play turns.
    void play_turn();
};
