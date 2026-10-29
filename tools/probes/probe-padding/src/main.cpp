// probe-padding: what host bitboard ops do with a board's padding bits (raw storage bits that are not map
// tiles: edge-chunk bits past width/height, the extra stride column of words, any rows past chunked_height).
// Layout assumed, and checked against set() and fill(): word cy * chunk_stride + cx, bit (y % 8) * 8 + x % 8.
// Each op's output is reported as on-map tiles (count()) and padding bits (counted from the raw words). Ops that
// write into an output run twice, into an output pre-filled with all-ones raw and with all-zeros raw, to tell
// "writes padding" from "leaves the destination's padding alone".
// P is a padding-only board (every padding bit, no tile). The key question: does shifting P put tiles on the map?
//   cambc run tools/probes/probe-padding tools/probes/probe-padding --map 00ambush --rounds 2 --fuel 50000000 -o <dir>
#include <cambc.h>
#include <cstdint>
#include <cstdio>
#include <cstring>

namespace {

using cambc::bitboard;
using cambc::vec2;

std::uint32_t W, H, CW, CH, S, NW;

bool on_map(std::uint32_t i, int b) {
    const std::uint32_t cy = i / S, cx = i % S;
    const std::uint32_t x = cx * 8 + b % 8, y = cy * 8 + b / 8;
    return cx < CW && cy < CH && x < W && y < H;
}

std::uint64_t map_mask(std::uint32_t i) {
    std::uint64_t m = 0;
    for (int b = 0; b < 64; ++b)
        if (on_map(i, b)) m |= std::uint64_t{1} << b;
    return m;
}

struct Pad {
    unsigned edge = 0, stride = 0, rows = 0;  // padding bits set: in-map words' edge bits, stride column, extra rows
    unsigned total() const { return edge + stride + rows; }
};

Pad pad(const bitboard& b) {
    Pad p;
    const std::uint64_t* w = b.ptr();
    for (std::uint32_t i = 0; i < NW; ++i) {
        const unsigned n = static_cast<unsigned>(__builtin_popcountll(w[i] & ~map_mask(i)));
        if (i / S >= CH) p.rows += n;
        else if (i % S >= CW) p.stride += n;
        else p.edge += n;
    }
    return p;
}

unsigned raw_tiles(const bitboard& b) {
    unsigned n = 0;
    for (std::uint32_t i = 0; i < NW; ++i) n += static_cast<unsigned>(__builtin_popcountll(b.ptr()[i] & map_mask(i)));
    return n;
}

void raw_fill(bitboard& b, std::uint64_t v) { for (std::uint32_t i = 0; i < NW; ++i) b.ptr()[i] = v; }

bitboard padding_only() {
    bitboard b;
    for (std::uint32_t i = 0; i < NW; ++i) b.ptr()[i] = ~map_mask(i);
    return b;
}

void log(const char* what, const bitboard& b) {
    const Pad p = pad(b);
    const unsigned c = b.count();
    char where[160] = "";
    if (c > 0 && c <= 400) {
        vec2 buf[400];
        const unsigned n = b.positions_into(buf);
        int minx = 1 << 20, maxx = -1, miny = 1 << 20, maxy = -1;
        for (unsigned k = 0; k < n; ++k) {
            if (buf[k].x < minx) minx = buf[k].x;
            if (buf[k].x > maxx) maxx = buf[k].x;
            if (buf[k].y < miny) miny = buf[k].y;
            if (buf[k].y > maxy) maxy = buf[k].y;
        }
        std::snprintf(where, sizeof where, " tiles x=%d..%d y=%d..%d", minx, maxx, miny, maxy);
    }
    debug_block({
        std::printf("PROBE %-40s count=%u raw_tiles=%u is_empty=%d pad_edge=%u pad_stride=%u pad_rows=%u%s\n", what, c,
                    raw_tiles(b), b.is_empty() ? 1 : 0, p.edge, p.stride, p.rows, where);
    });
}

// Run op into a destination pre-filled with all-ones and all-zeros raw, logging both.
template <class F>
void into(const char* what, F op) {
    char name[64];
    bitboard out;
    raw_fill(out, ~std::uint64_t{0});
    op(out);
    std::snprintf(name, sizeof name, "%s [out=1s]", what);
    log(name, out);
    raw_fill(out, 0);
    op(out);
    std::snprintf(name, sizeof name, "%s [out=0s]", what);
    log(name, out);
}

void run() {
    const auto& L = cambc::detail::layout();
    W = static_cast<std::uint32_t>(L.width);
    H = static_cast<std::uint32_t>(L.height);
    CW = L.chunked_width;
    CH = L.chunked_height;
    S = L.chunk_stride;
    NW = L.board_bytes / 8;
    debug_block({
        std::printf("PROBE layout W=%u H=%u chunked_width=%u chunked_height=%u chunk_stride=%u board_bytes=%u words=%u field_bytes=%u\n",
                    W, H, CW, CH, S, L.board_bytes, NW, L.field_bytes);
    });

    // Layout check: set() of each corner lands on the predicted bit; fill() sets exactly the predicted tiles.
    {
        const vec2 corners[] = {{0, 0}, {static_cast<int>(W) - 1, 0}, {0, static_cast<int>(H) - 1},
                                {static_cast<int>(W) - 1, static_cast<int>(H) - 1}, {5, 9}};
        unsigned bad = 0;
        for (vec2 c : corners) {
            bitboard b;
            b.set(c);
            const std::uint32_t i = (c.y / 8) * S + c.x / 8;
            const int bit = (c.y % 8) * 8 + c.x % 8;
            for (std::uint32_t j = 0; j < NW; ++j) {
                const std::uint64_t want = j == i ? std::uint64_t{1} << bit : 0;
                if (b.ptr()[j] != want) ++bad;
            }
        }
        debug_block({ std::printf("PROBE layout set() mismatched words=%u\n", bad); });
    }
    bitboard empty;
    bitboard full;
    full.fill();
    log("fill()", full);
    {
        bitboard f;
        raw_fill(f, ~std::uint64_t{0});
        f.fill();
        log("fill() over all-ones raw", f);
    }
    {
        bitboard z;
        raw_fill(z, ~std::uint64_t{0});
        z.clear();
        log("clear() over all-ones raw", z);
    }
    log("empty", empty);

    const bitboard P = padding_only();
    log("P (padding only)", P);
    debug_block({ std::printf("PROBE P == empty: %d\n", P == empty ? 1 : 0); });

    // Not, set ops.
    log("~empty", ~empty);
    log("~full", ~full);
    log("~P", ~P);
    log("~~P", ~~P);
    log("P | empty", P | empty);
    log("empty | P", empty | P);
    log("P & full", P & full);
    log("P & P2 (copy)", P & bitboard{P});
    log("P ^ empty", P ^ empty);
    log("full ^ P", full ^ P);
    log("copy of P", bitboard{P});
    into("Not(P) into", [&](bitboard& o) { cambc::detail::check(cambc::detail::sdk_Bitboard_Not(P.ptr(), o.ptr())); });
    into("Not(empty) into", [&](bitboard& o) { cambc::detail::check(cambc::detail::sdk_Bitboard_Not(empty.ptr(), o.ptr())); });
    into("Union(empty,empty) into", [&](bitboard& o) {
        cambc::detail::check(cambc::detail::sdk_Bitboard_Union(empty.ptr(), empty.ptr(), o.ptr()));
    });

    // Direction convention.
    {
        bitboard t;
        t.set(vec2{10, 10});
        log("(10,10) shift_right(1)", t.shift_right(1));
        log("(10,10) shift_up(1)", t.shift_up(1));
    }

    // Shifts of P by 1 in each of 8 directions (diagonals as two shifts, as a bot would build them).
    const int dirs[8][2] = {{1, 0}, {-1, 0}, {0, 1}, {0, -1}, {1, 1}, {1, -1}, {-1, 1}, {-1, -1}};
    for (auto& d : dirs) {
        char name[64];
        bitboard s = P;
        if (d[0]) s = s.shift_right(d[0]);
        if (d[1]) s = s.shift_up(d[1]);
        std::snprintf(name, sizeof name, "P shift (%+d,%+d)", d[0], d[1]);
        log(name, s);
    }
    for (int k : {2, 7, 8, 9}) {
        char name[64];
        std::snprintf(name, sizeof name, "P shift_right(%d)", -k);
        log(name, P.shift_right(-k));
        std::snprintf(name, sizeof name, "P shift_up(%d)", -k);
        log(name, P.shift_up(-k));
        std::snprintf(name, sizeof name, "P shift_up(%d)", k);
        log(name, P.shift_up(k));
    }
    // A full board's shifts: do tiles shifted off the map survive as padding and come back?
    log("full shift_right(1)", full.shift_right(1));
    log("full shift_up(1)", full.shift_up(1));
    log("full shift_up(-1)", full.shift_up(-1));
    {
        bitboard edge;
        for (std::uint32_t y = 0; y < H; ++y) edge.set(vec2{static_cast<int>(W) - 1, static_cast<int>(y)});
        log("right column", edge);
        const bitboard out = edge.shift_right(1);
        log("right column shift_right(1)", out);
        log("right column shift_right(1) then (-1)", out.shift_right(-1));
        bitboard top;
        for (std::uint32_t x = 0; x < W; ++x) top.set(vec2{static_cast<int>(x), static_cast<int>(H) - 1});
        log("row H-1", top);
        log("row H-1 shift_up(1) then (-1)", top.shift_up(1).shift_up(-1));
        log("row H-1 shift_up(-1) then (+1)", top.shift_up(-1).shift_up(1));
        bitboard bottom;
        for (std::uint32_t x = 0; x < W; ++x) bottom.set(vec2{static_cast<int>(x), 0});
        log("row 0 shift_up(1) then (-1)", bottom.shift_up(1).shift_up(-1));
        log("row 0 shift_up(-1) then (+1)", bottom.shift_up(-1).shift_up(1));
    }
    into("ShiftRight(P,1) into", [&](bitboard& o) { cambc::detail::check(cambc::detail::sdk_Bitboard_ShiftRight(P.ptr(), o.ptr(), 1)); });
    into("ShiftRight(empty,1) into", [&](bitboard& o) { cambc::detail::check(cambc::detail::sdk_Bitboard_ShiftRight(empty.ptr(), o.ptr(), 1)); });
    into("ShiftUp(empty,1) into", [&](bitboard& o) { cambc::detail::check(cambc::detail::sdk_Bitboard_ShiftUp(empty.ptr(), o.ptr(), 1)); });
    into("ShiftUp(empty,-1) into", [&](bitboard& o) { cambc::detail::check(cambc::detail::sdk_Bitboard_ShiftUp(empty.ptr(), o.ptr(), -1)); });

    // Reflections of P.
    log("P reflect_horizontal", P.reflect_horizontal());
    log("P reflect_vertical", P.reflect_vertical());
    log("P rotate_180", P.rotate_180());

    // Draws near the far corner.
    {
        bitboard d;
        d.draw_chebyshev(vec2{static_cast<int>(W) - 1, static_cast<int>(H) - 1}, 3);
        log("draw_chebyshev(far corner,3)", d);
    }

    // reachable_tiles: output padding, and walls / origin effects of P.
    const vec2 corner{static_cast<int>(W) - 1, static_cast<int>(H) - 1};
    into("reachable(walls=empty, far corner, 3) into", [&](bitboard& o) { empty.reachable_tiles_into(corner, 3, o); });
    into("reachable(walls=empty, (2,2), 255) into", [&](bitboard& o) { empty.reachable_tiles_into(vec2{2, 2}, 255, o); });
    into("reachable(walls=P, far corner, 3) into", [&](bitboard& o) { P.reachable_tiles_into(corner, 3, o); });
    into("reachable(walls=~P, far corner, 3) into", [&](bitboard& o) { (~P).reachable_tiles_into(corner, 3, o); });
    {
        bitboard fr, sc;
        into("reachable scratch(walls=empty, far corner, 3) into", [&](bitboard& o) {
            raw_fill(fr, ~std::uint64_t{0});
            raw_fill(sc, ~std::uint64_t{0});
            empty.reachable_tiles_into(corner, 3, fr, sc, o);
        });
    }

    // distance_field: visited padding, field padding values, padding in walls / roots.
    {
        cambc::distance_field f;
        bitboard roots;
        roots.set(corner);
        into("field(walls=empty, root far corner) visited", [&](bitboard& v) { f.compute(empty, roots, v); });
        // Field layout: chunk (y / 8) * chunked_width + x / 8 (no stride column), u16 (y % 8) * 8 + x % 8.
        unsigned field_pad_reached = 0, field_pad_total = 0;
        const std::uint32_t nvals = cambc::distance_field::raw_buffer_size() / 2;
        const std::uint16_t* fw = f.ptr();
        for (std::uint32_t k = 0; k < nvals; ++k) {
            const std::uint32_t c = k / 64, b = k % 64;
            const std::uint32_t x = (c % CW) * 8 + b % 8, y = (c / CW) * 8 + b / 8;
            if (x < W && y < H) continue;
            ++field_pad_total;
            if (fw[k] != cambc::distance_field::unreachable) ++field_pad_reached;
        }
        const std::uint32_t ci = (corner.y / 8) * CW + corner.x / 8;
        const int cb = (corner.y % 8) * 8 + corner.x % 8;
        const unsigned at_root = fw[ci * 64 + cb];
        const unsigned at_next = (corner.x % 8) < 7 ? fw[ci * 64 + cb + 1] : 0u;
        debug_block({
            std::printf("PROBE field values=%u padding slots=%u not-unreachable=%u (layout check: root slot %u, slot x+1 %u)\n",
                        nvals, field_pad_total, field_pad_reached, at_root, at_next);
        });
        bitboard v;
        cambc::distance_field g;
        g.compute(P, roots, v);
        unsigned diff = 0;
        for (std::uint32_t y = 0; y < H; ++y)
            for (std::uint32_t x = 0; x < W; ++x)
                if (f.get(vec2{static_cast<int>(x), static_cast<int>(y)}) != g.get(vec2{static_cast<int>(x), static_cast<int>(y)})) ++diff;
        debug_block({ std::printf("PROBE field walls=P vs walls=empty: on-map tiles differing=%u\n", diff); });
        log("field(walls=P) visited", v);
        cambc::distance_field h;
        h.compute(empty, P, v);
        unsigned reached = 0;
        for (std::uint32_t y = 0; y < H; ++y)
            for (std::uint32_t x = 0; x < W; ++x)
                if (h.get(vec2{static_cast<int>(x), static_cast<int>(y)}) != cambc::distance_field::unreachable) ++reached;
        debug_block({ std::printf("PROBE field(roots=P only): on-map tiles reached=%u\n", reached); });
        log("field(roots=P) visited", v);
    }

    // Walls that seal the map edge to edge: can a search step around their end through padding? A full row
    // y = H/2 splits the map; with clear padding at x >= W a path (W-1, H/2-1) -> (W, H/2) -> (W-1, H/2+1)
    // would exist. Likewise a full column x = W/2 against padding at y >= H.
    {
        bitboard row, col;
        for (std::uint32_t x = 0; x < W; ++x) row.set(vec2{static_cast<int>(x), static_cast<int>(H / 2)});
        for (std::uint32_t y = 0; y < H; ++y) col.set(vec2{static_cast<int>(W / 2), static_cast<int>(y)});
        bitboard roots, v;
        roots.set(vec2{0, 0});
        const vec2 past_row{static_cast<int>(W) - 1, static_cast<int>(H) - 1}, past_col{static_cast<int>(W) - 1, 0};
        for (int padded = 0; padded < 2; ++padded) {
            const bitboard wr = padded ? (row | P) : row, wc = padded ? (col | P) : col;
            cambc::distance_field f;
            f.compute(wr, roots, v);
            const unsigned d_row = f.get(past_row);
            const unsigned n_row = wr.reachable_tiles(vec2{0, 0}, 1000).count();
            const unsigned n_row_e = wr.reachable_tiles(vec2{static_cast<int>(W) - 1, 0}, 1000).count();
            f.compute(wc, roots, v);
            const unsigned d_col = f.get(past_col);
            const unsigned n_col = wc.reachable_tiles(vec2{0, 0}, 1000).count();
            const unsigned n_col_n = wc.reachable_tiles(vec2{0, static_cast<int>(H) - 1}, 1000).count();
            debug_block({
                std::printf("PROBE sealing walls%s: row: field past it=%u reachable from (0,0)=%u from (W-1,0)=%u; "
                            "column: field past it=%u reachable from (0,0)=%u from (0,H-1)=%u\n",
                            padded ? " with padding set" : " (padding clear)", d_row, n_row, n_row_e, d_col, n_col, n_col_n);
            });
        }
    }

    // shadow_cast output padding.
    into("shadow_cast(walls=empty, far corner, 8) into", [&](bitboard& o) { empty.shadow_cast_into(corner, 8, o); });
}

}  // namespace

int main() {
    if (cambc::is_draft()) {
        while (true) cambc::end_turn();
    }
    if (cambc::detail::cached_my_team == 0 && cambc::detail::cached_my_champion == 0) run();
    while (true) cambc::end_turn();
}
