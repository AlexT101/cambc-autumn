// Native time per call of cambc 4.0.0's bitboard / distance-field / vision engine functions against the
// fuel each is charged (host price formulas from tools/fastengine/runner/src/api_defs.rs, exact).
//   cc -O2 -o bench host-bench.c -ldl -lm && ./bench /abs/path/cambc-lib cambc.syms MAP...
// cambc-lib: a copy of the cambc binary with DF_1_PIE (0x08000000) cleared in DT_FLAGS_1 so dlopen
// accepts it; cambc.syms: `nm cambc` (symbols are resolved by name against the load base).
#define _GNU_SOURCE
#include <dlfcn.h>
#include <link.h>
#include <math.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

typedef uint64_t u64;
typedef uint32_t u32;
typedef uint16_t u16;
static uintptr_t base;
static char* symtext;

static void* sym(const char* name) {
    size_t n = strlen(name);
    for (char* line = symtext; line && *line;) {
        char* nl = strchr(line, '\n');
        char* last = NULL;
        for (char* p = line; p < (nl ? nl : line + strlen(line)); ++p)
            if (*p == ' ') last = p;
        if (last && strncmp(last + 1, name, n) == 0 && (last[1 + n] == '\n' || last[1 + n] == 0))
            return (void*)(base + strtoull(line, NULL, 16));
        line = nl ? nl + 1 : NULL;
    }
    fprintf(stderr, "missing %s\n", name);
    exit(1);
}

static double now(void) {
    struct timespec t;
    clock_gettime(CLOCK_MONOTONIC, &t);
    return t.tv_sec * 1e9 + t.tv_nsec;
}

typedef const void* C;
typedef void* P;
static int (*from_map)(const uint8_t*, size_t, u64*);
static int (*runner_init)(u64);
static int (*get_state)(u64, u32*), (*advance)(u64), (*end_turn)(u64, u32), (*draft)(u64, int);
static int (*get_meta)(u64, u32*);
static int (*get_walls)(u64, u64, P), (*get_holes)(u64, u64, P), (*get_altars)(u64, u64, P), (*get_bushes)(u64, u64, P);
static int (*bb_zero)(C, P), (*bb_not)(C, C, P), (*bb_union)(C, C, C, P), (*bb_shift_right)(C, C, P, int);
static int (*bb_count)(C, C, P), (*bb_set_bits)(C, C, P, size_t, P), (*bb_export_linear)(C, C, P, size_t);
static int (*bb_test)(C, C, int, int, P), (*bb_set)(C, P, int, int, int);
static int (*bb_draw_cheb)(C, P, int, int, float);
static int (*bb_reach)(C, C, int, int, P, u16, u16*);
static int (*bb_shadow)(C, C, int, int, P, u32, u32*);
static int (*df_copy)(C, C, P), (*df_get)(C, C, int, int, P);
static int (*df_compute)(C, C, C, P, P, u16, P);
static int (*df_compute_to)(C, C, C, C, P, P, u16, P);
static int (*vision_mask)(u64, u64, int, int, int, P), (*ward_vision_mask)(u64, u64, int, int, P);

static u32 meta[5];
static u64 chunks, board_bytes, field_bytes;
static int W, H;

static u64 span(int c, long r, int n) {
    long n1 = (n >= 2 ? n : 1) - 1;
    long hi = c + r, lo = c - r;
    long hc = hi < 0 ? 0 : (hi < n1 ? hi : n1) >> 3;
    long lc = lo < 0 ? 0 : (lo < n1 ? lo : n1) >> 3;
    return (u64)(hc - lc + 1);
}

static P board(void) { P p = aligned_alloc(16, (board_bytes + 15) & ~15ull); memset(p, 0, board_bytes); return p; }
static P out_dbg_dummy(void) { static P d; if (!d) d = aligned_alloc(16, 1 << 16); return d; }
static int test(C b, int x, int y) {
    u32 v = 0;
    bb_test(meta, b, x, y, &v);
    return v;
}

static u64 rng = 88172645463325252ull;
static u64 rnd(void) { rng ^= rng << 13, rng ^= rng >> 7, rng ^= rng << 17; return rng; }

typedef struct { const char* name; double ns, fuel, extra; long n; } Row;
static Row rows[64];
static int nrows;
static Row* row(const char* name) {
    for (int i = 0; i < nrows; ++i)
        if (!strcmp(rows[i].name, name)) return &rows[i];
    rows[nrows].name = name;
    return &rows[nrows++];
}
static void add(const char* name, double ns, double fuel, double extra) {
    Row* r = row(name);
    r->ns += ns, r->fuel += fuel, r->extra += extra, r->n++;
}

int main(int argc, char** argv) {
    void* h = dlopen(argv[1], RTLD_NOW | RTLD_LOCAL);
    if (!h) { fprintf(stderr, "dlopen: %s\n", dlerror()); return 1; }
    struct link_map* lm;
    dlinfo(h, RTLD_DI_LINKMAP, &lm);
    base = lm->l_addr;
    FILE* sf = fopen(argv[2], "rb");
    fseek(sf, 0, SEEK_END); long sl = ftell(sf); fseek(sf, 0, SEEK_SET);
    symtext = malloc(sl + 1); fread(symtext, 1, sl, sf); symtext[sl] = 0; fclose(sf);
#define S(v, n) v = sym(n)
    S(from_map, "Game_FromMapFileBytes"); S(runner_init, "Game_Runner_Init"); S(get_state, "Game_Runner_GetState"); S(advance, "Game_Runner_Advance");
    S(end_turn, "Game_Runner_EndTurn"); S(draft, "Game_Action_Draft"); S(get_meta, "Game_API_Map_GetBitboardMetadata");
    S(get_walls, "Game_API_Map_GetWallBitboard"); S(get_holes, "Game_API_Map_GetHoleBitboard");
    S(get_altars, "Game_API_Map_GetAltarBitboard"); S(get_bushes, "Game_API_Map_GetBushBitboard");
    S(bb_zero, "Bitboard_Zero"); S(bb_not, "Bitboard_Not"); S(bb_union, "Bitboard_Union"); S(bb_shift_right, "Bitboard_ShiftRight");
    S(bb_count, "Bitboard_NumSetBits"); S(bb_set_bits, "Bitboard_GetSetBits"); S(bb_export_linear, "Bitboard_ExportLinearBuffer");
    S(bb_test, "Bitboard_Test"); S(bb_set, "Bitboard_Set"); S(bb_draw_cheb, "Bitboard_DrawChebyshev");
    S(bb_reach, "Bitboard_ReachableMaskWithExpansionCount"); S(bb_shadow, "Bitboard_ShadowCastWithScanCount");
    S(df_copy, "DistanceField_Copy"); S(df_get, "DistanceField_Get");
    S(df_compute, "DistanceField_ComputeWithExpansionCount"); S(df_compute_to, "DistanceField_ComputeToWithExpansionCount");
    S(vision_mask, "Game_API_GetVisionMask"); S(ward_vision_mask, "Game_API_GetWardVisionMask");

    printf("map\tW\tH\tchunks\top\tcalls\tns_per_call\tfuel_per_call\tns_per_fuel\textra\n");
    for (int m = 3; m < argc; ++m) {
        FILE* f = fopen(argv[m], "rb");
        fseek(f, 0, SEEK_END); long len = ftell(f); fseek(f, 0, SEEK_SET);
        uint8_t* buf = malloc(len); fread(buf, 1, len, f); fclose(f);
        u64 g = 0;
        if (from_map(buf, len, &g) != 0) { fprintf(stderr, "load %s failed\n", argv[m]); continue; }
        int init_rc = runner_init(g);
        get_meta(g, meta);
        W = meta[0], H = meta[1];
        chunks = (u64)meta[2] * meta[3];
        board_bytes = (u64)meta[4] * meta[3] * 8;
        field_bytes = (u64)meta[2] * meta[3] * 128;
        u64 persp = 0xFFFFFFFFull << 32;  // team 0, the draft bot
        P walls = board(), t = board(), bushes = board(), opaque = board(), open = board();
        get_walls(g, persp, walls);
        get_holes(g, persp, t); bb_union(meta, walls, t, walls);
        get_altars(g, persp, t); bb_union(meta, walls, t, walls);
        get_bushes(g, persp, bushes);
        get_walls(g, persp, opaque); bb_union(meta, opaque, bushes, opaque);
        bb_not(meta, walls, open);
        // open tiles
        // Play the draft (first accepted pick) up to the first champion turn: champion perspectives exist from there.
        u64 cpersp = persp;
        for (int it = 0; it < 200; ++it) {
            u32 st[4];
            if (get_state(g, st) != 0 || st[0] == 2) break;
            if (st[1] == 2) { advance(g); continue; }
            if (st[3] == 0xFFFFFFFFu) {
                for (int c = 0; c < 12; ++c)
                    if (draft(g, c) == 0) break;
                end_turn(g, 0);
                continue;
            }
            cpersp = (u64)st[1] | (u64)st[3] << 32;
            break;
        }
        { u32 nw = 0, no = 0; bb_count(meta, walls, &nw); bb_count(meta, open, &no);
          int vr = vision_mask(g, cpersp, 0, W / 2, H / 2, out_dbg_dummy());
          fprintf(stderr, "%s init=%d walls=%u open=%u vision_rc=%d\n", argv[m], init_rc, nw, no, vr); }
        int ntiles = 0;
        int* tx = malloc(sizeof(int) * W * H), *ty = malloc(sizeof(int) * W * H);
        for (int y = 0; y < H; ++y)
            for (int x = 0; x < W; ++x)
                if (!test(walls, x, y)) tx[ntiles] = x, ty[ntiles] = y, ntiles++;
        P roots = board(), dests = board(), visited = board(), out = board(), b2 = board();
        P dist = aligned_alloc(16, field_bytes), dist2 = aligned_alloc(16, field_bytes);
        uint8_t* lin = malloc(board_bytes * 2 + 64);
        u32* pos = malloc(8 * W * H + 64);
        nrows = 0;
        memset(rows, 0, sizeof rows);
        const int reps = 200;
        for (int i = 0; i < reps; ++i) {
            int a = rnd() % ntiles, b = rnd() % ntiles;
            int ax = tx[a], ay = ty[a], bx = tx[b], by = ty[b];
            u16 cnt = 0;
            double t0, t1;
            // distance fields
            bb_zero(meta, roots); bb_set(meta, roots, ax, ay, 1);
            t0 = now(); df_compute(meta, walls, roots, visited, dist, 0xffff, &cnt); t1 = now();
            add("df_full", t1 - t0, fmin((cnt + 16.0) * chunks, 40000), cnt);
            t0 = now(); df_compute(meta, walls, roots, visited, dist, 8, &cnt); t1 = now();
            add("df_cap8", t1 - t0, fmin((cnt + 16.0) * chunks, 40000), cnt);
            bb_zero(meta, dests); bb_set(meta, dests, bx, by, 1);
            t0 = now(); df_compute_to(meta, walls, roots, dests, visited, dist, 0xffff, &cnt); t1 = now();
            add("df_to_random", t1 - t0, fmin((cnt + 16.0) * chunks, 40000), cnt);
            // a nearby destination: within 6 tiles
            int nb = -1;
            for (int k = 0; k < 50 && nb < 0; ++k) {
                int c = rnd() % ntiles;
                if (abs(tx[c] - ax) <= 6 && abs(ty[c] - ay) <= 6 && c != a) nb = c;
            }
            if (nb < 0)
                for (int c = 0; c < ntiles; ++c)
                    if (c != a && abs(tx[c] - ax) <= 6 && abs(ty[c] - ay) <= 6) { nb = c; break; }
            if (nb >= 0) {
                bb_zero(meta, dests); bb_set(meta, dests, tx[nb], ty[nb], 1);
                t0 = now(); df_compute_to(meta, walls, roots, dests, visited, dist, 0xffff, &cnt); t1 = now();
                add("df_to_near6", t1 - t0, fmin((cnt + 16.0) * chunks, 40000), cnt);
            }
            // reachable masks
            const int ds[3] = {2, 8, 0xffff};
            const char* rn[3] = {"reach_d2", "reach_d8", "reach_full"};
            for (int k = 0; k < 3; ++k) {
                t0 = now(); bb_reach(meta, walls, ax, ay, out, ds[k], &cnt); t1 = now();
                add(rn[k], t1 - t0, (cnt + 2.0) * span(ax, ds[k], W) * span(ay, ds[k], H) + chunks, cnt);
            }
            // sight
            u32 scan = 0;
            t0 = now(); bb_shadow(meta, opaque, ax, ay, out, 8, &scan); t1 = now();
            add("shadow_cast_r8", t1 - t0, scan / 2 + 2.0 * chunks, scan);
            t0 = now(); bb_shadow(meta, opaque, ax, ay, out, 4, &scan); t1 = now();
            add("shadow_cast_r4", t1 - t0, scan / 2 + 2.0 * chunks, scan);
            if (init_rc == 0) {
                int rc;
                t0 = now(); rc = vision_mask(g, cpersp, 0, ax, ay, out); t1 = now();
                if (rc == 0) add("vision_mask", t1 - t0, 2.0 * chunks, 0);
                t0 = now(); rc = ward_vision_mask(g, cpersp, ax, ay, out); t1 = now();
                if (rc == 0) add("ward_vision_mask", t1 - t0, 2.0 * chunks, 0);
            }
            // whole-board ops
            t0 = now(); bb_union(meta, walls, opaque, out); t1 = now();
            add("union", t1 - t0, chunks, 0);
            t0 = now(); bb_shift_right(meta, walls, out, 1); t1 = now();
            add("shift_right", t1 - t0, chunks, 0);
            u32 n = 0;
            t0 = now(); bb_count(meta, open, &n); t1 = now();
            add("num_set_bits", t1 - t0, chunks, 0);
            t0 = now(); bb_set_bits(meta, open, pos, W * H, &n); t1 = now();
            add("get_set_bits(open)", t1 - t0, chunks + n, n);
            t0 = now(); bb_export_linear(meta, walls, lin, board_bytes * 2); t1 = now();
            add("export_linear", t1 - t0, chunks, 0);
            t0 = now(); bb_draw_cheb(meta, b2, ax, ay, 8.0f); t1 = now();
            add("draw_chebyshev_r8", t1 - t0, (double)span(ax, 8, W) * span(ay, 8, H), 0);
            t0 = now(); df_copy(meta, dist, dist2); t1 = now();
            add("df_copy", t1 - t0, (field_bytes + 7) / 8, 0);
            u16 v;
            t0 = now();
            for (int k = 0; k < 64; ++k) df_get(meta, dist, tx[(a + k) % ntiles], ty[(a + k) % ntiles], &v);
            t1 = now();
            add("df_get(x64)", t1 - t0, 0, 0);
        }
        const char* name = strrchr(argv[m], '/');
        name = name ? name + 1 : argv[m];
        for (int i = 0; i < nrows; ++i) {
            Row* r = &rows[i];
            double ns = r->ns / r->n, fu = r->fuel / r->n;
            printf("%s\t%d\t%d\t%llu\t%s\t%ld\t%.0f\t%.0f\t%.2f\t%.1f\n", name, W, H, (unsigned long long)chunks, r->name, r->n, ns, fu,
                   fu > 0 ? ns / fu : 0.0, r->extra / r->n);
        }
        fflush(stdout);
    }
    return 0;
}
