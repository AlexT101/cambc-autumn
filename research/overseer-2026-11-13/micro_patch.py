"""Micro-timing copy of nyx-vl-fuel's ward scoring: per candidate, the cast, the board scoring, ward_value (first, then a hit); MICRO2 lines, MICROBAD on a value mismatch.
python3 micro_patch.py BOT/src/bot.cc"""
import sys
p = sys.argv[1]
s = open(p).read()
def rep(a, b):
    global s
    assert s.count(a) == 1, a
    s = s.replace(a, b)
rep('''// ward_sight_from(map, p, vision_radius, out), from the cache once cast.''', '''std::uint64_t micro_cast = 0, micro_score = 0, micro_v3 = 0, micro_hits = 0, micro_n = 0, micro_hitscore = 0;
// ward_sight_from(map, p, vision_radius, out), from the cache once cast.''')
rep('''        const int v = ward_value(map, p, near, far);''', '''        {
            static bitboard scratch{cambc::uninitialized};
            const int ti = tile_index(p);
            const bool hit = ward_sights.known[ti];
            const std::uint64_t a0 = fuel();
            ward_sight_from(map, p, 6, scratch);
            const std::uint64_t a1 = fuel();
            const auto& layout = cambc::detail::layout();
            const int stride = static_cast<int>(layout.chunk_stride);
            const SightWindow win = sight_window(p, 6);
            const std::uint64_t *const seen = scratch.ptr(), *const near_w = near.ptr(), *const far_w = far.ptr();
            const auto chunk = [&](int at) { const std::uint64_t q = seen[at]; return 2 * __builtin_popcountll(q & near_w[at]) + __builtin_popcountll(q & far_w[at]); };
            int value = 0;
            for (int cy = win.y0, at = win.y0 * stride + win.x0; cy <= win.y1; ++cy, at += stride) {
                value += chunk(at);
                if (win.x1 > win.x0) value += chunk(at + 1);
                if (win.x1 > win.x0 + 1) value += chunk(at + 2);
            }
            const std::uint64_t a2 = fuel();
            const int v3 = ward_value(map, p, near, far);
            const std::uint64_t a3 = fuel();
            const int v4 = ward_value(map, p, near, far);
            const std::uint64_t a4 = fuel();
            micro_cast += a0 - a1, micro_score += a1 - a2, micro_v3 += a2 - a3, micro_hitscore += a3 - a4, ++micro_n;
            if (hit) ++micro_hits;
            if (v3 != value || v4 != value) std::printf("MICROBAD %d %d %d\\n", value, v3, v4);
        }
        const int v = ward_value(map, p, near, far);''')
rep('''    if (!cut && n == 0 && site == asked_site) remember();''', '''    debug_block({ if (micro_n) std::printf("MICRO2 %llu %llu %llu %llu %llu %llu 0 0 0\\n", (unsigned long long)micro_n, (unsigned long long)micro_hits, (unsigned long long)micro_cast, (unsigned long long)micro_score, (unsigned long long)micro_v3, (unsigned long long)micro_hitscore); });
    micro_n = micro_hits = micro_cast = micro_score = micro_v3 = micro_hitscore = 0;
    if (!cut && n == 0 && site == asked_site) remember();''')
open(p, "w").write(s)
