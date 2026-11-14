// Inline functions and templates, defined after every class: src/unity.cpp includes this after
// every header (the declarations are in them).
#pragma once

// Debug output only: plain printf changes the game, so it runs inside debug_block (off in --release).
template <class... Args> void log(const char* format, Args... args)
{
    debug_block({ std::printf(format, args...); });
}

inline void charge_phase()
{
    if constexpr (!trace_fuel) return;
    const auto now = cambc::fuel_remaining();
    if (_phase_fuel > now && *_phase) {
        int k = 0;
        while (k < _phase_count && _phase_names[k] != _phase) ++k;
        if (k == _phase_count && _phase_count < 64) _phase_names[_phase_count++] = _phase;
        if (k < 64) _phase_costs[k] += _phase_fuel - now;
    }
    _phase_fuel = cambc::fuel_remaining();
}

// Debug: the first phase a turn reaches after running out of fuel and resuming next round.
inline void set_phase(const char* phase)
{
    debug_block({
        charge_phase();
        if (!_late_logged && cambc::round_number() != _turn_round) {
            std::printf("OOF %u %s\n", _turn_round, phase);
            _late_logged = true;
        }
    });
    _phase = phase;
}

inline void print_phases(unsigned round)
{
    if constexpr (!trace_fuel) return;
    debug_block({
        charge_phase();
        for (int k = 0; k < _phase_count; ++k)
            if (_phase_costs[k]) std::printf("PH %u %s %llu\n", round, _phase_names[k], _phase_costs[k]), _phase_costs[k] = 0;
    });
}
