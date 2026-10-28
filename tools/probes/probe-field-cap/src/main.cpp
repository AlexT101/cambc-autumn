// probe-field-cap: what distance_field::compute_with_expansion_count returns against the field's deepest
// distance D and the cap. Synthetic boards: everything wall except a 1-wide strip on row 0, x = 0..L, so a
// root's distances run along it. Cases: one root at x=0 (D = L), two roots at both ends (D = L/2), a lone
// root (D = 0). Each runs with no cap and caps D-2..D+2 (those >= 0), logging the return, the visited count,
// and every strip tile's distance ('.' for unreachable).
//   cambc run tools/probes/probe-field-cap tools/probes/probe-field-cap --map 00corners --rounds 2 --fuel 50000000 -o <dir>
#include <cambc.h>
#include <cstdint>
#include <cstdio>

namespace {

void run(const char* name, int len, bool both_ends, int D) {
    cambc::bitboard walls, roots, visited;
    walls.fill();
    for (int x = 0; x <= len; ++x) walls.set(cambc::vec2{x, 0}, false);
    roots.set(cambc::vec2{0, 0});
    if (both_ends) roots.set(cambc::vec2{len, 0});
    cambc::distance_field f;
    for (int c = D - 2; c <= D + 3; ++c) {
        if (c < 0) continue;
        const bool nocap = c == D + 3;
        const std::uint16_t cap = nocap ? cambc::distance_field::unreachable : static_cast<std::uint16_t>(c);
        const unsigned r = f.compute_with_expansion_count(walls, roots, visited, cap);
        char line[256];
        int n = 0;
        for (int x = 0; x <= len; ++x) {
            const std::uint16_t d = f.get(cambc::vec2{x, 0});
            n += d == cambc::distance_field::unreachable ? std::snprintf(line + n, sizeof line - n, " .")
                                                       : std::snprintf(line + n, sizeof line - n, " %u", d);
        }
        const unsigned vc = static_cast<unsigned>(visited.count());
        const unsigned capu = cap;
        debug_block({ std::printf("PROBE %s D=%d cap=%u%s return=%u visited=%u strip:%s\n", name, D, capu,
                                  nocap ? "(none)" : "", r, vc, line); });
    }
}

} // namespace

int main() {
    if (cambc::is_draft()) {
        while (true) cambc::end_turn();
    }
    if (cambc::detail::cached_my_team == 0 && cambc::detail::cached_my_champion == 0) {
        debug_block({ std::printf("PROBE map=%dx%d\n", cambc::map::width(), cambc::map::height()); });
        run("one-root", 5, false, 5);
        run("one-root", 12, false, 12);
        run("two-roots", 10, true, 5);
        run("two-roots", 24, true, 12);
        run("lone-root", 0, false, 0);
    }
    while (true) cambc::end_turn();
}
