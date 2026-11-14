#pragma once

#include <cambc.h>
#include <cstdio>

// Opt-in traces (debug builds only; a team's output is capped at 1 MiB): comms' picture of
// allies against the truth, and fuel by phase.
inline constexpr bool trace_comms = false;

inline constexpr bool trace_fuel = false;

// Debug output only: plain printf changes the game, so it runs inside debug_block (off in --release).
template <class... Args> void log(const char* format, Args... args);

// Where the turn is, for the error line in main: a pointer store, so cheap enough to leave in.
inline const char* _phase = "";

inline unsigned _turn_round = 0;

inline bool _late_logged = false;

// Debug: fuel spent since the previous phase, charged to that phase; printed at the turn's end.
inline unsigned long long _phase_fuel = 0;

inline const char* _phase_names[64] = {};

inline unsigned long long _phase_costs[64] = {};

inline int _phase_count = 0;

inline void charge_phase();

// Debug: the first phase a turn reaches after running out of fuel and resuming next round.
inline void set_phase(const char* phase);

inline void print_phases(unsigned round);
