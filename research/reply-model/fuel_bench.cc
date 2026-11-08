// Instruction counts of danger evaluators in the bot's wasm build (PLAN2.md, fuel). Not bot code.
//   fuel_bench_rows.h: 64 held-out danger rows (replays/combatlab/reply/compress/val.npy, seed 1), `static float rows[64][48]`.
//   W=~/.cache/cambc/wasi-sdk-33; $W/bin/clang++ --target=wasm32-wasip1 --sysroot=$W/share/wasi-sysroot -O3 -std=c++20 \
//     -msimd128 -mbulk-memory -fno-exceptions -nostartfiles -Wl,--no-entry -o bench.wasm fuel_bench.cc
//   wasm-interp bench.wasm -r run_query --trace | grep '^#' | grep -vE '\| (nop|drop|block|loop|end|else|return|drop_keep|alloca)\b' | wc -l
//   (minus run_empty's, over 64 rows). Tables hold dummy values (init/init2 keep them from folding to constants).
#include <cmath>
#include "/home/ubuntu/cambc-autumn/bots/variants/oc-reply/src/combat/reply_lean.h"
#include "/home/ubuntu/cambc-autumn/bots/variants/oc-reply/src/combat/reply_model.h"
#include "fuel_bench_rows.h"
#define K 64
volatile float sink;
// A GAM: F 1-D tables of 16 bins, binned by a 4-step branchless search over 15 edges.
constexpr int F = 17;
static float edges[F][16];
static float table[F][16];
static float sig[256];
static int feat[F] = {0,1,2,4,6,7,8,9,11,12,13,14,26,27,28,37,40};
__attribute__((noinline)) float gam(const float* x) {
  float z = 0.1f;
  for (int f = 0; f < F; ++f) {
    const float v = x[feat[f]];
    const float* e = edges[f];
    int b = 0;
    b += (v >= e[b + 8]) ? 8 : 0;
    b += (v >= e[b + 4]) ? 4 : 0;
    b += (v >= e[b + 2]) ? 2 : 0;
    b += (v >= e[b + 1]) ? 1 : 0;
    z += table[f][b];
  }
  return x[1] / (1.0f + std::exp(-z));
}
// Per-enemy constant folded: only the per-tile features (d, blow, stuns) looked up; sigmoid by table.
__attribute__((noinline)) float gam_folded(const float* x, float enemy_z) {
  float z = enemy_z;
  z += table[0][static_cast<int>(x[0]) & 15];
  z += table[2][static_cast<int>(x[2]) & 1];
  const float v = x[1]; const float* e = edges[1]; int b = 0;
  b += (v >= e[b + 8]) ? 8 : 0; b += (v >= e[b + 4]) ? 4 : 0; b += (v >= e[b + 2]) ? 2 : 0; b += (v >= e[b + 1]) ? 1 : 0;
  z += table[1][b];
  int s = static_cast<int>(z * 16.0f + 128.0f); s = s < 0 ? 0 : s > 255 ? 255 : s;
  return x[1] * sig[s];
}
static float t3[3][8][16];
__attribute__((noinline)) float tab3(const float* x) {
  int a = static_cast<int>(x[40]); a = a < 0 ? 0 : a > 2 ? 2 : a;
  int d = static_cast<int>(x[0]) & 7; int t = static_cast<int>(x[4]) & 15;
  return x[1] * t3[a][d][t];
}
extern "C" {
__attribute__((export_name("run_empty"))) void run_empty() { float s = 0; for (int k = 0; k < K; ++k) s += rows[k][1]; sink = s; }
__attribute__((export_name("run_lean"))) void run_lean() { float s = 0; for (int k = 0; k < K; ++k) s += aph::reply::lean::danger(rows[k]); sink = s; }
__attribute__((export_name("run_full"))) void run_full() { float s = 0; for (int k = 0; k < K; ++k) s += aph::reply::model::danger(rows[k]); sink = s; }
__attribute__((export_name("run_gam"))) void run_gam() { float s = 0; for (int k = 0; k < K; ++k) s += gam(rows[k]); sink = s; }
__attribute__((export_name("run_folded"))) void run_folded() { float s = 0; for (int k = 0; k < K; ++k) s += gam_folded(rows[k], 0.3f); sink = s; }
__attribute__((export_name("run_tab3"))) void run_tab3() { float s = 0; for (int k = 0; k < K; ++k) s += tab3(rows[k]); sink = s; }
}
extern "C" __attribute__((export_name("init"))) void init(float v) {
  for (int f = 0; f < F; ++f) for (int b = 0; b < 16; ++b) edges[f][b] = v * b, table[f][b] = v - b;
  for (int s = 0; s < 256; ++s) sig[s] = v * s;
  for (int a = 0; a < 3; ++a) for (int d = 0; d < 8; ++d) for (int t = 0; t < 16; ++t) t3[a][d][t] = v * t;
}
__attribute__((noinline)) float gam_sig(const float* x) {
  float z = 0.1f;
  for (int f = 0; f < F; ++f) {
    const float v = x[feat[f]];
    const float* e = edges[f];
    int b = 0;
    b += (v >= e[b + 8]) ? 8 : 0;
    b += (v >= e[b + 4]) ? 4 : 0;
    b += (v >= e[b + 2]) ? 2 : 0;
    b += (v >= e[b + 1]) ? 1 : 0;
    z += table[f][b];
  }
  int s = static_cast<int>(z * 16.0f + 128.0f); s = s < 0 ? 0 : s > 255 ? 255 : s;
  return x[1] * sig[s];
}
__attribute__((noinline)) float expo(float z) { return 1.0f / (1.0f + std::exp(-z)); }
extern "C" {
__attribute__((export_name("run_gamsig"))) void run_gamsig() { float s = 0; for (int k = 0; k < K; ++k) s += gam_sig(rows[k]); sink = s; }
__attribute__((export_name("run_exp"))) void run_exp() { float s = 0; for (int k = 0; k < K; ++k) s += expo(rows[k][7]); sink = s; }
}
// The recommended query: per-enemy tables (d 8, blow 32 edges, stuns 2), sigmoid table, capped multiplier.
struct EnemyTables { float z; float td[8]; float edges[32]; float tb[32]; float ts[2]; float k; };
static EnemyTables et[4];
static float my_hp_cap = 700;
__attribute__((noinline)) float query(const EnemyTables& t, int d, float blow, bool stuns) {
  const float* e = t.edges; int b = 0;
  b += (blow >= e[b + 16]) ? 16 : 0; b += (blow >= e[b + 8]) ? 8 : 0; b += (blow >= e[b + 4]) ? 4 : 0;
  b += (blow >= e[b + 2]) ? 2 : 0; b += (blow >= e[b + 1]) ? 1 : 0;
  const float z = t.z + t.td[d & 7] + t.tb[b] + t.ts[stuns];
  int s = static_cast<int>(z * 16.0f + 128.0f); s = s < 0 ? 0 : s > 255 ? 255 : s;
  return (blow < my_hp_cap ? blow : my_hp_cap) * t.k * sig[s];
}
extern "C" {
__attribute__((export_name("init2"))) void init2(float v) { for (auto& t : et) { t.z = v; t.k = v; for (int i = 0; i < 32; ++i) t.edges[i] = v * i, t.tb[i] = v; for (int i = 0; i < 8; ++i) t.td[i] = v; t.ts[0] = t.ts[1] = v; } my_hp_cap = v; }
__attribute__((export_name("run_query"))) void run_query() { float s = 0; for (int k = 0; k < K; ++k) s += query(et[k & 3], static_cast<int>(rows[k][0]), rows[k][1], rows[k][2] > 0); sink = s; }
}
