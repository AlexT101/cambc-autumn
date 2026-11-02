#include <cambc.h>
#include <wasi/api.h>
#include <cstdio>
#include <algorithm>
static unsigned char buf[4096];
int main() {
    int k = 0;
    while (true) {
        if (cambc::is_draft()) {
            const auto chosen = cambc::draft::current_draft(cambc::team::ally);
            for (int i = 0; i < 11; ++i) {
                auto p = static_cast<cambc::champion_draft>(i);
                if (std::find(chosen.begin(), chosen.end(), p) == chosen.end()) { cambc::draft::pick(p); break; }
            }
        } else if (k < 14) {
            long long d[3];
            for (int r = 0; r < 3; ++r) {
                __wasi_timestamp_t t; __wasi_iovec_t iov{buf, 8}; __wasi_size_t n;
                auto f0 = cambc::fuel_remaining();
                switch (k) {
                case 0: break;
                case 1: __wasi_random_get(buf, 0); break;
                case 2: __wasi_random_get(buf, 1); break;
                case 3: __wasi_random_get(buf, 4); break;
                case 4: __wasi_random_get(buf, 16); break;
                case 5: __wasi_random_get(buf, 256); break;
                case 6: __wasi_random_get(buf, 4096); break;
                case 7: __wasi_clock_time_get(__WASI_CLOCKID_MONOTONIC, 1, &t); break;
                case 8: __wasi_clock_res_get(__WASI_CLOCKID_MONOTONIC, &t); break;
                case 9: __wasi_fd_read(0, &iov, 1, &n); break;
                case 10: __wasi_sched_yield(); break;
                case 11: __wasi_fd_tell(1, &t); break;
                case 12: { __wasi_prestat_t ps; __wasi_fd_prestat_get(3, &ps); } break;
                case 13: { __wasi_filestat_t st; __wasi_fd_filestat_get(1, &st); } break;
                }
                d[r] = (long long)(f0 - cambc::fuel_remaining());
            }
            std::printf("k=%d cost=%lld %lld %lld\n", k, d[0], d[1], d[2]); std::fflush(stdout);
            ++k;
        }
        cambc::end_turn();
    }
}
