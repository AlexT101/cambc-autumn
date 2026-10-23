// probe-fuel-e: probe-fuel-b scripted draft: pick, pick, then on draft turn 3 pick and exhaust fuel;
// if resumed in a later draft round it tries to pick varg.
// Run: cambc run probe-fuel probe-fuel-e --map corners --rounds 3 -o <dir>
#define DRAFT_SCRIPT
#define DRAFT_PICK2
#define DRAFT_PICK3
#include "../../probe-fuel-b/src/main.cpp"
