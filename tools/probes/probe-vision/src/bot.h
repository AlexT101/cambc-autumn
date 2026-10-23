#pragma once
class Bot {
public:
    int idx = -1; // index of self among champions(team::ally)
    void play_turn();
};
