// Turn order within the team for next round. Teams alternate one champion at a time, so an ally
// ranked higher acts before more enemies; each ally sets its own priority from what it needs.
#pragma once

namespace aph {

class World;
class Safety;

void set_turn_order(const World& world, Safety& safety);

} // namespace aph
