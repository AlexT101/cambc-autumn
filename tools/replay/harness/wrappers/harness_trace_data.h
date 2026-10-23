// The recorder's data for one game, compiled into the tracer (rec_data.cpp, from trace_data.py).
#pragma once
#include <cstdint>

struct HtF { // @f: fuel_remaining call #idx of segment seg returned v
    uint32_t seg, idx;
    int64_t v;
};
struct HtR { // @r: the bot ran out of fuel before host call #idx of segment seg, the first of `round`
    uint32_t seg, idx, round;
};
struct HtY { // @y: segment's round at its yield, counted calls (the yield included) and call hash
    uint32_t round, calls, hash;
};
struct HtInst { // one bot instance: me is the champion id, -1 the draft bot
    int32_t me;
    uint32_t nf, nr, ny;
    const HtF* f;
    const HtR* r;
    const HtY* y; // by segment
};

extern "C" const HtInst ht_insts[];
extern "C" const uint32_t ht_ninst;
extern "C" const char ht_game[];
