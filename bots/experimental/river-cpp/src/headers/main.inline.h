// Inline functions and templates, defined after every class: src/unity.cpp includes this after
// every header (the declarations are in them).
#pragma once

namespace {
template <class F> bool run(const char* phase, F&& f)
{
    debug_block({ aph::fuel_phase() = phase; });
    try {
        f();
        return true;
    } catch (const aph::StaleTurn&) {
    } catch (const std::exception& e) {
        std::printf("r%u %s error: %s\n", cambc::round_number(), phase, e.what());
    } catch (...) {
        std::printf("r%u %s error: unknown exception\n", cambc::round_number(), phase);
    }
    return false;
}

}
