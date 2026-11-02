// Last-error probe: reads the engine's last error at the points a bot can observe it that no import sets itself:
// the first import of an instance, the first import after a yield / out-of-fuel resume / restart, after WASI writes,
// and after a debug_block overrun. Before each, a failing call (seed) leaves a known stale error.
#include "imp.h"
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <wasi/api.h>

alignas(16) static unsigned char SCR[4096];
static char LOG[1 << 15];
static int LN = 0;
static int OVR = -2;
static U A(const void* p) { return (U)(uintptr_t)p; }

#define SEED() X_champion(0x7fff0000u, A(SCR))
#define REC(tag)                                                                          \
    do {                                                                                  \
        int _n = X_bc_get_last_error(0, 0);                                               \
        char _b[128];                                                                     \
        int _m = _n > 0 ? (_n < 120 ? _n : 120) : 0;                                      \
        if (_m) X_bc_get_last_error(A(_b), _m);                                           \
        _b[_m] = 0;                                                                       \
        LN += std::snprintf(LOG + LN, sizeof LOG - LN, "%s len=%d '%s'\n", tag, _n, _b);  \
    } while (0)

static void fdw(int fd, const char* s, int len) {
    __wasi_ciovec_t io{(const uint8_t*)s, (size_t)len};
    __wasi_size_t nw;
    (void)__wasi_fd_write(fd, &io, 1, &nw);
}
static void fdw2(const char* s, int len) {
    __wasi_ciovec_t io[2] = {{(const uint8_t*)s, 0}, {(const uint8_t*)s, (size_t)len}};
    __wasi_size_t nw;
    (void)__wasi_fd_write(1, io, 2, &nw);
}
static void flush_log(const char* who, int turn) {
    std::printf("== %s turn %d\n", who, turn);
    std::fwrite(LOG, 1, LN, stdout);
    std::fflush(stdout);
    LN = 0;
}
static volatile unsigned SINK;
__attribute__((noinline)) static void burn(unsigned n) {
    for (unsigned i = 0; i < n; ++i) SINK = SINK + i;
}
static void wasi_tests(const char* pre) {
    char t[64];
    SEED(); fdw(1, "#w1\n", 4); std::snprintf(t, sizeof t, "%s fd_write stdout", pre); REC(t);
    SEED(); fdw(1, "", 0); std::snprintf(t, sizeof t, "%s fd_write empty", pre); REC(t);
    SEED(); fdw2("#w2\n", 4); std::snprintf(t, sizeof t, "%s fd_write 2 iovs", pre); REC(t);
    SEED(); fdw(2, "#e\n", 3); std::snprintf(t, sizeof t, "%s fd_write stderr", pre); REC(t);
    SEED(); fdw(9, "#x\n", 3); std::snprintf(t, sizeof t, "%s fd_write bad fd", pre); REC(t);
    SEED(); std::printf("#pf\n"); std::fflush(stdout); std::snprintf(t, sizeof t, "%s printf+fflush", pre); REC(t);
    SEED(); (void)X_fuel_remaining(); std::snprintf(t, sizeof t, "%s fuel_remaining", pre); REC(t);
    SEED(); (void)X_fuel_pause(); X_fuel_resume(); std::snprintf(t, sizeof t, "%s fuel_pause+resume", pre); REC(t);
}

int main() {
    REC("start");
    int me = X_my_champion();
    int team = X_my_team();
    if (me == -1) {
        static const int picks[] = {3, 7, 9, 11, 6, 0, 1, 2, 4, 5, 8, 10};
        int pi = 0;
        for (int turn = 0;; ++turn) {
            if (turn > 0) REC("draft after yield");
            if (turn == 0) wasi_tests("draft");
            while (pi < 12 && X_draft_champion(picks[pi]) != 0) ++pi;
            ++pi;
            REC("draft after pick");
            flush_log("draft", turn);
            SEED();
            X_yield();
        }
    }
    char who[32];
    std::snprintf(who, sizeof who, "t%d c%d", team, me);
    int stage = 0;
    for (int turn = 0;; ++turn) {
        if (turn > 0) REC("after yield");
        U rnd = 0;
        X_bc_round_number(A(&rnd));
        LN += std::snprintf(LOG + LN, sizeof LOG - LN, "round %u\n", rnd);
        if (turn == 0) wasi_tests("play");
        if (OVR != -2) {
            LN += std::snprintf(LOG + LN, sizeof LOG - LN, "after overrun len=%d\n", OVR);
            OVR = -2;
        }
        if (rnd >= 4) {
            switch (stage++) {
            case 0: {
                // a debug block past its free budget (quantum * quanta * 1000 = 1e8 by default): fuel_resume
                // reports the overrun. Calibrated to overshoot by ~2 turns of fuel.
                long long f0 = X_fuel_remaining();
                burn(2000);
                long long f1 = X_fuel_remaining();
                long long per = f0 - f1;
                unsigned n = per > 0 ? (unsigned)((100000000LL + 1000000) * 2000 / per) : 0;
                LN += std::snprintf(LOG + LN, sizeof LOG - LN, "calibration %lld per 2000, n=%u\n", per, n);
                if (X_fuel_pause()) {
                    burn(n);
                    SEED();
                    X_fuel_resume();
                    OVR = X_bc_get_last_error(0, 0);
                }
                break;
            }
            case 1:
                SEED();
                burn(40000);  // runs out of fuel; resumes next turn
                REC("after out of fuel");
                break;
            case 2:
                flush_log(who, turn);
                SEED();
                if (me % 2 == 0) __builtin_trap();
                std::exit(3);
            default:
                break;
            }
        }
        flush_log(who, turn);
        SEED();
        X_yield();
    }
}
