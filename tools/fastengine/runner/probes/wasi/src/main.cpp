#include <cambc.h>
#include <wasi/api.h>
#include <cstdio>
#include <cstring>
#include <cerrno>
#include <algorithm>
int main() {
    int k = 0;
    while (true) {
        if (cambc::is_draft()) {
            const auto chosen = cambc::draft::current_draft(cambc::team::ally);
            for (int i = 0; i < 11; ++i) {
                auto p = static_cast<cambc::champion_draft>(i);
                if (std::find(chosen.begin(), chosen.end(), p) == chosen.end()) { cambc::draft::pick(p); break; }
            }
        } else if (k++ == 0) {
            char b[8]; __wasi_iovec_t iov{(uint8_t*)b, 8}; __wasi_size_t n = 777;
            for (int fd = 0; fd < 4; ++fd) { n = 777; int rc = __wasi_fd_read(fd, &iov, 1, &n); std::printf("fd_read(%d) rc=%d n=%u\n", fd, rc, (unsigned)n); }
            for (int fd = 0; fd < 4; ++fd) { __wasi_prestat_t ps; int rc = __wasi_fd_prestat_get(fd, &ps); std::printf("prestat(%d) rc=%d\n", fd, rc); }
            for (int fd = 0; fd < 4; ++fd) {
                __wasi_filestat_t st; std::memset(&st, 0xAB, sizeof st); int rc = __wasi_fd_filestat_get(fd, &st);
                std::printf("filestat(%d) rc=%d dev=%llx ino=%llx type=%d nlink=%llx size=%llx a=%llx m=%llx c=%llx\n", fd, rc,
                  (unsigned long long)st.dev, (unsigned long long)st.ino, (int)st.filetype, (unsigned long long)st.nlink, (unsigned long long)st.size,
                  (unsigned long long)st.atim, (unsigned long long)st.mtim, (unsigned long long)st.ctim);
            }
            for (int fd = 0; fd < 4; ++fd) { __wasi_filesize_t o = 99; int rc = __wasi_fd_tell(fd, &o); std::printf("tell(%d) rc=%d o=%llu\n", fd, rc, (unsigned long long)o); }
            for (int fd = 0; fd < 4; ++fd) { int rc = __wasi_fd_fdstat_set_flags(fd, 0); std::printf("setflags(%d) rc=%d\n", fd, rc); }
            for (int fd = 0; fd < 4; ++fd) { __wasi_fd_t o = 99; int rc = __wasi_path_open(fd, 0, "x.txt", 0, 0, 0, 0, &o); std::printf("path_open(%d) rc=%d\n", fd, rc); }
            { errno = 0; FILE* f = std::fopen("x.txt", "r"); std::printf("fopen f=%d errno=%d\n", f != nullptr, errno); }
            { __wasi_timestamp_t t = 5; int rc = __wasi_clock_time_get(7, 1, &t); std::printf("clock(7) rc=%d t=%llu\n", rc, (unsigned long long)t); }
            { __wasi_timestamp_t t = 5; int rc = __wasi_clock_res_get(7, &t); std::printf("res(7) rc=%d t=%llu\n", rc, (unsigned long long)t); }
            std::fflush(stdout);
        }
        cambc::end_turn();
    }
}
