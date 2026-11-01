// Decision trace (TRACE_SCHEMA.md). Read-only: the hooks below only copy values the bot already
// computed into trace storage, and read the engine raw into their own buffers inside debug_block,
// where tools/replay/harness/wrappers/harness_trace.h neither counts nor virtualises host calls. Nothing here
// calls the bot's own evaluators (Safety, Pathing) or its scratch-static readers (my_record()...).
#pragma once
#include <cambc.h>
#include <cstdint>
#include "util.h"

extern "C" const char* trace_site; // the decision site acting now: TA lines (harness) carry it

namespace aph {
class World;
struct Memory;
struct Trade;
struct ChampionBelief;
} // namespace aph

namespace aph::trace {

inline constexpr int version = 1;

// 0: TT only; 1 (default): + TB, TE, TS, TF summaries; 2: + every fight, candidate and fighter,
// within the round window. From the harness's per-game config when built with it.
int level();
bool detail(); // level 2 and this round in the window
std::uint32_t round();

// The site any action until the scope ends is taken for.
struct Site {
    const char* prev;
    explicit Site(const char* s) : prev{trace_site} { trace_site = s; }
    ~Site() { trace_site = prev; }
    Site(const Site&) = delete;
    Site& operator=(const Site&) = delete;
};

// "TE r=<round> c=<id> k=<kind> " then the formatted fields and a newline.
[[gnu::format(printf, 2, 3)]] void ev(const char* kind, const char* fmt, ...);

// "TE r=<round> c=<id> k=<kind>" without the newline: fields follow, then put_enemies or "\n".
void ev_open(const char* kind);
// " en=<handle>:<dist>:<health>:<gems>:<age>;..." for the living enemies believed within `radius` of p
// (age: rounds since that position was fixed, 0 = seen now), then the newline. Beliefs only: no host calls.
void put_enemies(const World& world, vec2 p, int radius);

void begin_turn(const World& world, const Memory& memory);
void end_turn(const World& world, const Memory& memory, char decision, bool completed);

// Safety's results as the bot computes them, keyed by tile; `kind` names the query.
enum class Q : std::uint8_t { lethal, threatened, camp, bound, ceiling, idle_kill };
void note_value(Q kind, vec2 p, float v);
// A fight result: `how` f fight(), c chase_trade, s stand(); `fresh` if simulated now, not memoised.
void note_fight(char how, vec2 p, std::uint32_t key, const Trade& t, bool fresh);
// Simulations run (Safety::new_fight, chase_trade, stand), for telling memo hits from fresh ones.
inline int& simulations() {
    static int n = 0;
    return n;
}

} // namespace aph::trace

// Only the debug-built tracer reads the site; a release build compiles it away.
#ifdef CAMBC_DEBUG
#define TRACE_SITE(name) const ::aph::trace::Site trace_site_scope_{name}
#else
#define TRACE_SITE(name) static_cast<void>(0)
#endif
