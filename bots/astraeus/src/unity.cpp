// One translation unit: the ladder builds src/*.cpp with no LTO, so calls between files are
// inlined only when they share one (EXPERIMENTS Fuel, "unity build").
#include "abilities.cc"
#include "bot.cc"
#include "comms.cc"
#include "draft.cc"
#include "pathing.cc"
#include "plan.cc"
#include "safety.cc"
#include "self_abilities.cc"
#include "turn_order.cc"
#include "world.cc"
#include "main.cc"
