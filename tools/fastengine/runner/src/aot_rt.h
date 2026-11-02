/* Runtime for bots translated by aot.rs (fastrunner's native mode). Wasm semantics on x86-64; compiled with
 * -ffp-contract=off so float results match wasmtime's (no fused multiply-add). */
#include <stdint.h>
#include <string.h>

typedef uint8_t u8;
typedef int8_t i8;
typedef uint16_t u16;
typedef int16_t i16;
typedef uint32_t u32;
typedef int32_t i32;
typedef uint64_t u64;
typedef int64_t i64;
typedef float f32;
typedef double f64;

typedef u8 v128 __attribute__((vector_size(16), aligned(16)));
typedef i8 i8x16 __attribute__((vector_size(16)));
typedef u8 u8x16 __attribute__((vector_size(16)));
typedef i16 i16x8 __attribute__((vector_size(16)));
typedef u16 u16x8 __attribute__((vector_size(16)));
typedef i32 i32x4 __attribute__((vector_size(16)));
typedef u32 u32x4 __attribute__((vector_size(16)));
typedef i64 i64x2 __attribute__((vector_size(16)));
typedef u64 u64x2 __attribute__((vector_size(16)));
typedef f32 f32x4 __attribute__((vector_size(16)));
typedef f64 f64x2 __attribute__((vector_size(16)));
typedef i8 i8x8 __attribute__((vector_size(8)));
typedef u8 u8x8 __attribute__((vector_size(8)));
typedef i16 i16x4 __attribute__((vector_size(8)));
typedef u16 u16x4 __attribute__((vector_size(8)));
typedef i32 i32x2 __attribute__((vector_size(8)));
typedef u32 u32x2 __attribute__((vector_size(8)));
typedef f32 f32x2 __attribute__((vector_size(8)));

/* Must match native.rs's NInst. `fuel` is wasmtime's VMStoreContext fuel_consumed: minus the fuel left in the
 * active chunk, positive once overrun. {mem, size} is the memory's VMMemoryDefinition layout. */
typedef struct Inst {
  i64 fuel;
  u8* mem;
  u64 size;
  u64 exn;
  void* rt;
  u64 pad[3];
  u64 g[];
} Inst;

#define LIKELY(x) __builtin_expect(!!(x), 1)
#define UNLIKELY(x) __builtin_expect(!!(x), 0)
#define HIDDEN __attribute__((visibility("hidden")))
#define INL static inline __attribute__((always_inline))

/* Provided by libfastrunner.so (preloaded, so in global scope). */
extern void fr_trap(Inst*, u32 code) __attribute__((noreturn, cold));
extern void fr_out_of_gas(Inst*) __attribute__((cold));
extern u32 fr_memory_grow(Inst*, u32 delta);

enum { T_UNREACHABLE = 0, T_DIV0, T_INT_OVERFLOW, T_BAD_CONV, T_OOB, T_NULL_CALL, T_SIG, T_TABLE_OOB, T_NULL_REF,
       T_UNCAUGHT };

#define FUEL_CHECK() do { if (UNLIKELY(fuel >= 0)) { I->fuel = fuel; fr_out_of_gas(I); fuel = I->fuel; } } while (0)

/* Linear memory: an 8 GiB reservation, inaccessible past `size`, so any i32 address plus offset faults instead
 * of needing a bounds check (native.rs turns the fault into a trap). */
#define LD(T, a, o) ({ T _v; memcpy(&_v, M + (u64)(u32)(a) + (u64)(o), sizeof(T)); _v; })
#define ST(T, a, o, v) do { T _v = (v); memcpy(M + (u64)(u32)(a) + (u64)(o), &_v, sizeof(T)); } while (0)

#define EXN_MAKE(tag, p) ((((u64)(tag) + 1) << 32) | (u64)(u32)(p))
#define EXN_TAG(e) ((u32)((e) >> 32) - 1)
#define EXN_PAY(e) ((u32)(e))

INL f32 f32_bits(u32 b) { f32 f; memcpy(&f, &b, 4); return f; }
INL f64 f64_bits(u64 b) { f64 f; memcpy(&f, &b, 8); return f; }
INL u32 bits_f32(f32 f) { u32 b; memcpy(&b, &f, 4); return b; }
INL u64 bits_f64(f64 f) { u64 b; memcpy(&b, &f, 8); return b; }
INL v128 v128_make(u64 lo, u64 hi) { u64x2 v = {lo, hi}; return (v128)v; }

/* ---- integers ---- */
INL u32 clz32(u32 a) { return a ? (u32)__builtin_clz(a) : 32; }
INL u32 ctz32(u32 a) { return a ? (u32)__builtin_ctz(a) : 32; }
INL u64 clz64(u64 a) { return a ? (u64)__builtin_clzll(a) : 64; }
INL u64 ctz64(u64 a) { return a ? (u64)__builtin_ctzll(a) : 64; }
INL u32 rotl32(u32 a, u32 b) { b &= 31; return (a << b) | (a >> ((32 - b) & 31)); }
INL u32 rotr32(u32 a, u32 b) { b &= 31; return (a >> b) | (a << ((32 - b) & 31)); }
INL u64 rotl64(u64 a, u64 b) { b &= 63; return (a << b) | (a >> ((64 - b) & 63)); }
INL u64 rotr64(u64 a, u64 b) { b &= 63; return (a >> b) | (a << ((64 - b) & 63)); }
INL u32 div_s32(Inst* I, u32 a, u32 b) {
  if (UNLIKELY(b == 0)) fr_trap(I, T_DIV0);
  if (UNLIKELY(a == 0x80000000u && b == 0xffffffffu)) fr_trap(I, T_INT_OVERFLOW);
  return (u32)((i32)a / (i32)b);
}
INL u32 div_u32(Inst* I, u32 a, u32 b) { if (UNLIKELY(b == 0)) fr_trap(I, T_DIV0); return a / b; }
INL u32 rem_s32(Inst* I, u32 a, u32 b) {
  if (UNLIKELY(b == 0)) fr_trap(I, T_DIV0);
  if (UNLIKELY(b == 0xffffffffu)) return 0;
  return (u32)((i32)a % (i32)b);
}
INL u32 rem_u32(Inst* I, u32 a, u32 b) { if (UNLIKELY(b == 0)) fr_trap(I, T_DIV0); return a % b; }
INL u64 div_s64(Inst* I, u64 a, u64 b) {
  if (UNLIKELY(b == 0)) fr_trap(I, T_DIV0);
  if (UNLIKELY(a == 0x8000000000000000ull && b == ~0ull)) fr_trap(I, T_INT_OVERFLOW);
  return (u64)((i64)a / (i64)b);
}
INL u64 div_u64(Inst* I, u64 a, u64 b) { if (UNLIKELY(b == 0)) fr_trap(I, T_DIV0); return a / b; }
INL u64 rem_s64(Inst* I, u64 a, u64 b) {
  if (UNLIKELY(b == 0)) fr_trap(I, T_DIV0);
  if (UNLIKELY(b == ~0ull)) return 0;
  return (u64)((i64)a % (i64)b);
}
INL u64 rem_u64(Inst* I, u64 a, u64 b) { if (UNLIKELY(b == 0)) fr_trap(I, T_DIV0); return a % b; }

/* ---- floats ---- */
INL f32 fmin32(f32 a, f32 b) {
  if (a != a || b != b) return a + b;
  if (a == b) return bits_f32(a) & 0x80000000u ? a : b;
  return a < b ? a : b;
}
INL f32 fmax32(f32 a, f32 b) {
  if (a != a || b != b) return a + b;
  if (a == b) return bits_f32(a) & 0x80000000u ? b : a;
  return a > b ? a : b;
}
INL f64 fmin64(f64 a, f64 b) {
  if (a != a || b != b) return a + b;
  if (a == b) return bits_f64(a) & 0x8000000000000000ull ? a : b;
  return a < b ? a : b;
}
INL f64 fmax64(f64 a, f64 b) {
  if (a != a || b != b) return a + b;
  if (a == b) return bits_f64(a) & 0x8000000000000000ull ? b : a;
  return a > b ? a : b;
}
INL f32 fabs32(f32 a) { return f32_bits(bits_f32(a) & 0x7fffffffu); }
INL f32 fneg32(f32 a) { return f32_bits(bits_f32(a) ^ 0x80000000u); }
INL f64 fabs64(f64 a) { return f64_bits(bits_f64(a) & 0x7fffffffffffffffull); }
INL f64 fneg64(f64 a) { return f64_bits(bits_f64(a) ^ 0x8000000000000000ull); }
INL f32 fcopysign32(f32 a, f32 b) { return f32_bits((bits_f32(a) & 0x7fffffffu) | (bits_f32(b) & 0x80000000u)); }
INL f64 fcopysign64(f64 a, f64 b) {
  return f64_bits((bits_f64(a) & 0x7fffffffffffffffull) | (bits_f64(b) & 0x8000000000000000ull));
}

/* trapping float -> int (bounds are the exclusive limits of truncation toward zero) */
#define TRUNC(name, F, R, lo, hi)                                    \
  INL R name(Inst* I, F a) {                                         \
    if (UNLIKELY(a != a)) fr_trap(I, T_BAD_CONV);                    \
    if (UNLIKELY(!(a > (F)(lo) && a < (F)(hi)))) fr_trap(I, T_INT_OVERFLOW); \
    return (R)a;                                                     \
  }
TRUNC(trunc_f32_i32s, f32, i32, -2147483904.0, 2147483648.0)
TRUNC(trunc_f32_i32u, f32, u32, -1.0, 4294967296.0)
TRUNC(trunc_f64_i32s, f64, i32, -2147483649.0, 2147483648.0)
TRUNC(trunc_f64_i32u, f64, u32, -1.0, 4294967296.0)
TRUNC(trunc_f32_i64s, f32, i64, -9223373136366403584.0, 9223372036854775808.0)
TRUNC(trunc_f32_i64u, f32, u64, -1.0, 18446744073709551616.0)
TRUNC(trunc_f64_i64s, f64, i64, -9223372036854777856.0, 9223372036854775808.0)
TRUNC(trunc_f64_i64u, f64, u64, -1.0, 18446744073709551616.0)

#define TRUNC_SAT(name, F, R, lo, hi, rmin, rmax)       \
  INL R name(F a) {                                     \
    if (a != a) return 0;                               \
    if (!(a > (F)(lo))) return rmin;                    \
    if (!(a < (F)(hi))) return rmax;                    \
    return (R)a;                                        \
  }
TRUNC_SAT(sat_f32_i32s, f32, i32, -2147483904.0, 2147483648.0, INT32_MIN, INT32_MAX)
TRUNC_SAT(sat_f32_i32u, f32, u32, -1.0, 4294967296.0, 0, UINT32_MAX)
TRUNC_SAT(sat_f64_i32s, f64, i32, -2147483649.0, 2147483648.0, INT32_MIN, INT32_MAX)
TRUNC_SAT(sat_f64_i32u, f64, u32, -1.0, 4294967296.0, 0, UINT32_MAX)
TRUNC_SAT(sat_f32_i64s, f32, i64, -9223373136366403584.0, 9223372036854775808.0, INT64_MIN, INT64_MAX)
TRUNC_SAT(sat_f32_i64u, f32, u64, -1.0, 18446744073709551616.0, 0, UINT64_MAX)
TRUNC_SAT(sat_f64_i64s, f64, i64, -9223372036854777856.0, 9223372036854775808.0, INT64_MIN, INT64_MAX)
TRUNC_SAT(sat_f64_i64u, f64, u64, -1.0, 18446744073709551616.0, 0, UINT64_MAX)

/* ---- bulk memory (bounds checked before any byte moves) ---- */
INL void mem_copy(Inst* I, u8* M, u32 d, u32 s, u32 n) {
  if (UNLIKELY((u64)d + n > I->size || (u64)s + n > I->size)) fr_trap(I, T_OOB);
  memmove(M + d, M + s, n);
}
INL void mem_fill(Inst* I, u8* M, u32 d, u32 v, u32 n) {
  if (UNLIKELY((u64)d + n > I->size)) fr_trap(I, T_OOB);
  memset(M + d, (int)(u8)v, n);
}

/* ---- SIMD ---- */
#define VB(T, v) ((T)(v))
#define LANES_U8(v) VB(u8x16, v)
INL u32 v_any_true(v128 a) { u64x2 x = (u64x2)a; return (x[0] | x[1]) != 0; }
#define ALL_TRUE(name, T, N) \
  INL u32 name(v128 a) { T x = (T)a; for (int i = 0; i < N; i++) if (x[i] == 0) return 0; return 1; }
ALL_TRUE(i8x16_all_true, u8x16, 16)
ALL_TRUE(i16x8_all_true, u16x8, 8)
ALL_TRUE(i32x4_all_true, u32x4, 4)
ALL_TRUE(i64x2_all_true, u64x2, 2)
#define BITMASK(name, T, N) \
  INL u32 name(v128 a) { T x = (T)a; u32 r = 0; for (int i = 0; i < N; i++) r |= (u32)(x[i] < 0) << i; return r; }
BITMASK(i8x16_bitmask, i8x16, 16)
BITMASK(i16x8_bitmask, i16x8, 8)
BITMASK(i32x4_bitmask, i32x4, 4)
BITMASK(i64x2_bitmask, i64x2, 2)

#define SPLAT(name, T, S, N) INL v128 name(S s) { T v; for (int i = 0; i < N; i++) v[i] = s; return (v128)v; }
SPLAT(i8x16_splat, u8x16, u8, 16)
SPLAT(i16x8_splat, u16x8, u16, 8)
SPLAT(i32x4_splat, u32x4, u32, 4)
SPLAT(i64x2_splat, u64x2, u64, 2)
SPLAT(f32x4_splat, f32x4, f32, 4)
SPLAT(f64x2_splat, f64x2, f64, 2)

/* lane-wise binary ops on a vector type */
#define VBIN(name, T, expr) INL v128 name(v128 a_, v128 b_) { T a = (T)a_, b = (T)b_; return (v128)(expr); }
#define VUN(name, T, expr) INL v128 name(v128 a_) { T a = (T)a_; return (v128)(expr); }
#define VSHIFT(name, T, W, op) INL v128 name(v128 a_, u32 s) { T a = (T)a_; return (v128)(a op (s & (W - 1))); }
#define VLOOP2(name, T, N, expr) \
  INL v128 name(v128 a_, v128 b_) { T a = (T)a_, b = (T)b_, r; for (int i = 0; i < N; i++) r[i] = (expr); return (v128)r; }
#define VLOOP1(name, T, N, expr) \
  INL v128 name(v128 a_) { T a = (T)a_, r; for (int i = 0; i < N; i++) r[i] = (expr); return (v128)r; }

VBIN(v128_and, u64x2, a & b)
VBIN(v128_or, u64x2, a | b)
VBIN(v128_xor, u64x2, a ^ b)
VBIN(v128_andnot, u64x2, a & ~b)
VUN(v128_not, u64x2, ~a)
INL v128 v128_bitselect(v128 a, v128 b, v128 c) {
  u64x2 x = (u64x2)a, y = (u64x2)b, m = (u64x2)c;
  return (v128)((x & m) | (y & ~m));
}

#define INT_SHAPE(P, S, U, N, W)                                  \
  VBIN(P##_add, U, a + b)                                         \
  VBIN(P##_sub, U, a - b)                                         \
  VBIN(P##_eq, U, a == b)                                         \
  VBIN(P##_ne, U, a != b)                                         \
  VBIN(P##_lt_s, S, a < b)                                        \
  VBIN(P##_gt_s, S, a > b)                                        \
  VBIN(P##_le_s, S, a <= b)                                       \
  VBIN(P##_ge_s, S, a >= b)                                       \
  VBIN(P##_lt_u, U, a < b)                                        \
  VBIN(P##_gt_u, U, a > b)                                        \
  VBIN(P##_le_u, U, a <= b)                                       \
  VBIN(P##_ge_u, U, a >= b)                                       \
  VSHIFT(P##_shl, U, W, <<)                                       \
  VSHIFT(P##_shr_s, S, W, >>)                                     \
  VSHIFT(P##_shr_u, U, W, >>)                                     \
  VUN(P##_neg, U, (U){0} - a)                                     \
  VLOOP1(P##_abs, U, N, ((S)a)[i] < 0 ? 0 - a[i] : a[i])
INT_SHAPE(i8x16, i8x16, u8x16, 16, 8)
INT_SHAPE(i16x8, i16x8, u16x8, 8, 16)
INT_SHAPE(i32x4, i32x4, u32x4, 4, 32)
INT_SHAPE(i64x2, i64x2, u64x2, 2, 64)
VBIN(i16x8_mul, u16x8, a * b)
VBIN(i32x4_mul, u32x4, a * b)
VBIN(i64x2_mul, u64x2, a * b)
#define MINMAX(P, S, U, N)                                \
  VLOOP2(P##_min_s, S, N, a[i] < b[i] ? a[i] : b[i])     \
  VLOOP2(P##_max_s, S, N, a[i] > b[i] ? a[i] : b[i])     \
  VLOOP2(P##_min_u, U, N, a[i] < b[i] ? a[i] : b[i])     \
  VLOOP2(P##_max_u, U, N, a[i] > b[i] ? a[i] : b[i])
MINMAX(i8x16, i8x16, u8x16, 16)
MINMAX(i16x8, i16x8, u16x8, 8)
MINMAX(i32x4, i32x4, u32x4, 4)
VLOOP2(i8x16_avgr_u, u8x16, 16, (u8)(((u32)a[i] + b[i] + 1) >> 1))
VLOOP2(i16x8_avgr_u, u16x8, 8, (u16)(((u32)a[i] + b[i] + 1) >> 1))
#define SAT_CLAMP(v, lo, hi) ((v) < (lo) ? (lo) : (v) > (hi) ? (hi) : (v))
VLOOP2(i8x16_add_sat_s, i8x16, 16, (i8)SAT_CLAMP((i32)a[i] + b[i], -128, 127))
VLOOP2(i8x16_add_sat_u, u8x16, 16, (u8)SAT_CLAMP((i32)a[i] + b[i], 0, 255))
VLOOP2(i8x16_sub_sat_s, i8x16, 16, (i8)SAT_CLAMP((i32)a[i] - b[i], -128, 127))
VLOOP2(i8x16_sub_sat_u, u8x16, 16, (u8)SAT_CLAMP((i32)a[i] - b[i], 0, 255))
VLOOP2(i16x8_add_sat_s, i16x8, 8, (i16)SAT_CLAMP((i32)a[i] + b[i], -32768, 32767))
VLOOP2(i16x8_add_sat_u, u16x8, 8, (u16)SAT_CLAMP((i32)a[i] + b[i], 0, 65535))
VLOOP2(i16x8_sub_sat_s, i16x8, 8, (i16)SAT_CLAMP((i32)a[i] - b[i], -32768, 32767))
VLOOP2(i16x8_sub_sat_u, u16x8, 8, (u16)SAT_CLAMP((i32)a[i] - b[i], 0, 65535))
VLOOP2(i16x8_q15mulr_sat_s, i16x8, 8, (i16)SAT_CLAMP(((i32)a[i] * b[i] + 0x4000) >> 15, -32768, 32767))
VUN(i8x16_popcnt, u8x16, __builtin_elementwise_popcount(a))

/* narrow: signed inputs saturated to the half-width signed/unsigned range */
#define NARROW(name, S, D, N, lo, hi)                                          \
  INL v128 name(v128 a_, v128 b_) {                                            \
    S a = (S)a_, b = (S)b_; D r;                                               \
    for (int i = 0; i < N; i++) r[i] = SAT_CLAMP(a[i], lo, hi);                \
    for (int i = 0; i < N; i++) r[i + N] = SAT_CLAMP(b[i], lo, hi);            \
    return (v128)r;                                                            \
  }
NARROW(i8x16_narrow_i16x8_s, i16x8, i8x16, 8, -128, 127)
NARROW(i8x16_narrow_i16x8_u, i16x8, u8x16, 8, 0, 255)
NARROW(i16x8_narrow_i32x4_s, i32x4, i16x8, 4, -32768, 32767)
NARROW(i16x8_narrow_i32x4_u, i32x4, u16x8, 4, 0, 65535)

/* extend: low or high half, sign or zero */
#define EXTEND(name, S, D, N, off) \
  INL v128 name(v128 a_) { S a = (S)a_; D r; for (int i = 0; i < N; i++) r[i] = a[i + off]; return (v128)r; }
EXTEND(i16x8_extend_low_i8x16_s, i8x16, i16x8, 8, 0)
EXTEND(i16x8_extend_high_i8x16_s, i8x16, i16x8, 8, 8)
EXTEND(i16x8_extend_low_i8x16_u, u8x16, u16x8, 8, 0)
EXTEND(i16x8_extend_high_i8x16_u, u8x16, u16x8, 8, 8)
EXTEND(i32x4_extend_low_i16x8_s, i16x8, i32x4, 4, 0)
EXTEND(i32x4_extend_high_i16x8_s, i16x8, i32x4, 4, 4)
EXTEND(i32x4_extend_low_i16x8_u, u16x8, u32x4, 4, 0)
EXTEND(i32x4_extend_high_i16x8_u, u16x8, u32x4, 4, 4)
EXTEND(i64x2_extend_low_i32x4_s, i32x4, i64x2, 2, 0)
EXTEND(i64x2_extend_high_i32x4_s, i32x4, i64x2, 2, 2)
EXTEND(i64x2_extend_low_i32x4_u, u32x4, u64x2, 2, 0)
EXTEND(i64x2_extend_high_i32x4_u, u32x4, u64x2, 2, 2)
#define EXTMUL(name, S, D, DE, N, off) \
  INL v128 name(v128 a_, v128 b_) { S a = (S)a_, b = (S)b_; D r; \
    for (int i = 0; i < N; i++) r[i] = (DE)a[i + off] * (DE)b[i + off]; return (v128)r; }
EXTMUL(i16x8_extmul_low_i8x16_s, i8x16, i16x8, i16, 8, 0)
EXTMUL(i16x8_extmul_high_i8x16_s, i8x16, i16x8, i16, 8, 8)
EXTMUL(i16x8_extmul_low_i8x16_u, u8x16, u16x8, u16, 8, 0)
EXTMUL(i16x8_extmul_high_i8x16_u, u8x16, u16x8, u16, 8, 8)
EXTMUL(i32x4_extmul_low_i16x8_s, i16x8, i32x4, i32, 4, 0)
EXTMUL(i32x4_extmul_high_i16x8_s, i16x8, i32x4, i32, 4, 4)
EXTMUL(i32x4_extmul_low_i16x8_u, u16x8, u32x4, u32, 4, 0)
EXTMUL(i32x4_extmul_high_i16x8_u, u16x8, u32x4, u32, 4, 4)
EXTMUL(i64x2_extmul_low_i32x4_s, i32x4, i64x2, i64, 2, 0)
EXTMUL(i64x2_extmul_high_i32x4_s, i32x4, i64x2, i64, 2, 2)
EXTMUL(i64x2_extmul_low_i32x4_u, u32x4, u64x2, u64, 2, 0)
EXTMUL(i64x2_extmul_high_i32x4_u, u32x4, u64x2, u64, 2, 2)
#define EXTADD(name, S, D, DE, N) \
  INL v128 name(v128 a_) { S a = (S)a_; D r; for (int i = 0; i < N; i++) r[i] = (DE)a[2 * i] + (DE)a[2 * i + 1]; return (v128)r; }
EXTADD(i16x8_extadd_pairwise_i8x16_s, i8x16, i16x8, i16, 8)
EXTADD(i16x8_extadd_pairwise_i8x16_u, u8x16, u16x8, u16, 8)
EXTADD(i32x4_extadd_pairwise_i16x8_s, i16x8, i32x4, i32, 4)
EXTADD(i32x4_extadd_pairwise_i16x8_u, u16x8, u32x4, u32, 4)
INL v128 i32x4_dot_i16x8_s(v128 a_, v128 b_) {
  i16x8 a = (i16x8)a_, b = (i16x8)b_; u32x4 r;
  for (int i = 0; i < 4; i++) r[i] = (u32)((i32)a[2 * i] * b[2 * i]) + (u32)((i32)a[2 * i + 1] * b[2 * i + 1]);
  return (v128)r;
}
INL v128 i8x16_swizzle(v128 a_, v128 s_) {
  u8x16 a = (u8x16)a_, s = (u8x16)s_, r;
  for (int i = 0; i < 16; i++) r[i] = s[i] < 16 ? a[s[i]] : 0;
  return (v128)r;
}

/* floats */
#define FLT_SHAPE(P, T, U, N, S, MIN, MAX, ABS, NEG)              \
  VBIN(P##_add, T, a + b)                                         \
  VBIN(P##_sub, T, a - b)                                         \
  VBIN(P##_mul, T, a * b)                                         \
  VBIN(P##_div, T, a / b)                                         \
  VBIN(P##_eq, T, a == b)                                         \
  VBIN(P##_ne, T, a != b)                                         \
  VBIN(P##_lt, T, a < b)                                          \
  VBIN(P##_gt, T, a > b)                                          \
  VBIN(P##_le, T, a <= b)                                         \
  VBIN(P##_ge, T, a >= b)                                         \
  VLOOP2(P##_min, T, N, MIN(a[i], b[i]))                          \
  VLOOP2(P##_max, T, N, MAX(a[i], b[i]))                          \
  VLOOP2(P##_pmin, T, N, b[i] < a[i] ? b[i] : a[i])               \
  VLOOP2(P##_pmax, T, N, a[i] < b[i] ? b[i] : a[i])               \
  VLOOP1(P##_abs, T, N, ABS(a[i]))                                \
  VLOOP1(P##_neg, T, N, NEG(a[i]))                                \
  VUN(P##_sqrt, T, __builtin_elementwise_sqrt(a))                 \
  VUN(P##_ceil, T, __builtin_elementwise_ceil(a))                 \
  VUN(P##_floor, T, __builtin_elementwise_floor(a))               \
  VUN(P##_trunc, T, __builtin_elementwise_trunc(a))               \
  VUN(P##_nearest, T, __builtin_elementwise_roundeven(a))
FLT_SHAPE(f32x4, f32x4, u32x4, 4, f32, fmin32, fmax32, fabs32, fneg32)
FLT_SHAPE(f64x2, f64x2, u64x2, 2, f64, fmin64, fmax64, fabs64, fneg64)
VUN(f32x4_convert_i32x4_s, i32x4, __builtin_convertvector(a, f32x4))
VUN(f32x4_convert_i32x4_u, u32x4, __builtin_convertvector(a, f32x4))
VLOOP1(i32x4_trunc_sat_f32x4_s, i32x4, 4, sat_f32_i32s(((f32x4)a_)[i]))
VLOOP1(i32x4_trunc_sat_f32x4_u, u32x4, 4, sat_f32_i32u(((f32x4)a_)[i]))
INL v128 i32x4_trunc_sat_f64x2_s_zero(v128 a_) { f64x2 a = (f64x2)a_; i32x4 r = {sat_f64_i32s(a[0]), sat_f64_i32s(a[1]), 0, 0}; return (v128)r; }
INL v128 i32x4_trunc_sat_f64x2_u_zero(v128 a_) { f64x2 a = (f64x2)a_; u32x4 r = {sat_f64_i32u(a[0]), sat_f64_i32u(a[1]), 0, 0}; return (v128)r; }
INL v128 f64x2_convert_low_i32x4_s(v128 a_) { i32x4 a = (i32x4)a_; f64x2 r = {(f64)a[0], (f64)a[1]}; return (v128)r; }
INL v128 f64x2_convert_low_i32x4_u(v128 a_) { u32x4 a = (u32x4)a_; f64x2 r = {(f64)a[0], (f64)a[1]}; return (v128)r; }
INL v128 f32x4_demote_f64x2_zero(v128 a_) { f64x2 a = (f64x2)a_; f32x4 r = {(f32)a[0], (f32)a[1], 0, 0}; return (v128)r; }
INL v128 f64x2_promote_low_f32x4(v128 a_) { f32x4 a = (f32x4)a_; f64x2 r = {(f64)a[0], (f64)a[1]}; return (v128)r; }

/* loads/stores of lanes */
#define LOAD_EXT(name, S, D, N)                                                      \
  INL v128 name(u8* p) { S s[N]; memcpy(s, p, sizeof s); D r; for (int i = 0; i < N; i++) r[i] = s[i]; return (v128)r; }
LOAD_EXT(v_load8x8_s, i8, i16x8, 8)
LOAD_EXT(v_load8x8_u, u8, u16x8, 8)
LOAD_EXT(v_load16x4_s, i16, i32x4, 4)
LOAD_EXT(v_load16x4_u, u16, u32x4, 4)
LOAD_EXT(v_load32x2_s, i32, i64x2, 2)
LOAD_EXT(v_load32x2_u, u32, u64x2, 2)
INL v128 v_load(u8* p) { v128 v; memcpy(&v, p, 16); return v; }
INL void v_store(u8* p, v128 v) { memcpy(p, &v, 16); }
#define LOAD_SPLAT(name, S, T, N) INL v128 name(u8* p) { S s; memcpy(&s, p, sizeof s); T r; for (int i = 0; i < N; i++) r[i] = s; return (v128)r; }
LOAD_SPLAT(v_load8_splat, u8, u8x16, 16)
LOAD_SPLAT(v_load16_splat, u16, u16x8, 8)
LOAD_SPLAT(v_load32_splat, u32, u32x4, 4)
LOAD_SPLAT(v_load64_splat, u64, u64x2, 2)
INL v128 v_load32_zero(u8* p) { u32 s; memcpy(&s, p, 4); u32x4 r = {s, 0, 0, 0}; return (v128)r; }
INL v128 v_load64_zero(u8* p) { u64 s; memcpy(&s, p, 8); u64x2 r = {s, 0}; return (v128)r; }
#define LANE_IO(W, S, T)                                                                              \
  INL v128 v_load##W##_lane(u8* p, v128 v_, int l) { T v = (T)v_; S s; memcpy(&s, p, sizeof s); v[l] = s; return (v128)v; } \
  INL void v_store##W##_lane(u8* p, v128 v_, int l) { T v = (T)v_; S s = v[l]; memcpy(p, &s, sizeof s); }
LANE_IO(8, u8, u8x16)
LANE_IO(16, u16, u16x8)
LANE_IO(32, u32, u32x4)
LANE_IO(64, u64, u64x2)
