// Our own kill bid: a turn end that bids the kill band on an enemy that has acted this round takes
// a seat before it next round, and that turn is to strike it. Kept per bot instance; no message.
#pragma once
#include "world.h"

namespace aph::follow {

struct Bid {
    int target = -1;  // enemy index
    int round = -1;   // the round whose turn end made it; it binds our turn the round after
    float need = 0;   // our blow on it, after its `taken`
    float left = 0;   // the health a plan must leave it at, from its health at the turn's first search
    int left_round = -1;
};
inline Bid posting; // set_turn_order's winning kill offer on an acted enemy, this turn
inline Bid own;     // the last one made

inline const Bid* binding(const World& world) {
    return own.target >= 0 && own.round == world.round - 1 && world.me().alive ? &own : nullptr;
}

} // namespace aph::follow
