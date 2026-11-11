#pragma once
// Fuel-lean std::partial_sort for 16- and 32-bit integer keys. Fuel is one per wasm
// instruction, SIMD included, so these work on a whole vector of keys per instruction
// where they can: eight 16-bit keys, four 32-bit ones. Measured in
// test-bots/bench-sort-cpp.
//
//   topk::partial_sort<K>(a, n)        as std::partial_sort(a, a + K, a + n), K <= n
//   topk::partial_sort<K, true>(a, n)  largest first, as with std::greater
//   topk::partial_sort(a, k, n)        k at run time
//   topk::sort(a, n)                   the whole of a sorted
//
// a is u16*, i16*, u32* or i32*. 16-bit keys cost about 0.6x as much a key (distance
// fields are u16). To sort records, pack the score above an index (score << 10 | i) and
// sort that: distinct keys also keep the large-k path from gathering a crowd of ties.
//
// K <= 16: the K first so far live sorted in SIMD registers and a scan of eight vectors
// at a time lets only keys before the K-th through. Larger K: a threshold from 16
// sampled keys, every key at or before it swapped to the front, then those sorted
// (sorting networks on 16 vectors, merges a vector at a time).
#include <algorithm>
#include <array>
#include <cstdint>
#include <functional>
#include <type_traits>
#include <utility>
#include <wasm_simd128.h>

#define TOPK_INLINE __attribute__((always_inline))
// Keeps a loop pointer as it is, so loads take their offsets as immediates (LLVM
// otherwise rebases it and pays an add for every negative offset).
#define TOPK_OPAQUE(x) asm("" : "+r"(x))
// In a rarely taken branch: stops LLVM turning it into selects that run every time.
#define TOPK_RARE() asm volatile("")

namespace topk {
    using u16 = std::uint16_t;
    using i16 = std::int16_t;
    using u32 = std::uint32_t;
    using i32 = std::int32_t;
    using u64 = std::uint64_t;

    namespace detail {
        // Key width (W16: 16-bit keys, 8 lanes; else 32-bit, 4), signed or not,
        // smallest or largest first. "lo" is whichever of two comes first.
        template <bool W16, bool S, bool D> struct ord {
            using key = std::conditional_t<W16, u16, u32>; // as stored
            using mask =
                std::conditional_t<W16, u64, u32>; // a bit a key over eight vectors
            static constexpr u32 L = W16 ? 8 : 4;  // keys a vector
            static constexpr bool is_signed = S;
            static constexpr key last =
                W16 ? (S ? (D ? 0x8000 : 0x7fff)
                         : (D ? 0 : 0xffff)) // no key comes after it
                    : (S ? (D ? 0x80000000u : 0x7fffffffu) : (D ? 0u : ~0u));
            TOPK_INLINE static v128_t vmin(v128_t a, v128_t b) {
                if constexpr (W16)
                    return S ? wasm_i16x8_min(a, b) : wasm_u16x8_min(a, b);
                else
                    return S ? wasm_i32x4_min(a, b) : wasm_u32x4_min(a, b);
            }
            TOPK_INLINE static v128_t vmax(v128_t a, v128_t b) {
                if constexpr (W16)
                    return S ? wasm_i16x8_max(a, b) : wasm_u16x8_max(a, b);
                else
                    return S ? wasm_i32x4_max(a, b) : wasm_u32x4_max(a, b);
            }
            TOPK_INLINE static v128_t vlt(v128_t a, v128_t b) {
                if constexpr (W16)
                    return S ? wasm_i16x8_lt(a, b) : wasm_u16x8_lt(a, b);
                else
                    return S ? wasm_i32x4_lt(a, b) : wasm_u32x4_lt(a, b);
            }
            TOPK_INLINE static v128_t vge(v128_t a, v128_t b) {
                if constexpr (W16)
                    return S ? wasm_i16x8_ge(a, b) : wasm_u16x8_ge(a, b);
                else
                    return S ? wasm_i32x4_ge(a, b) : wasm_u32x4_ge(a, b);
            }
            TOPK_INLINE static v128_t lo(v128_t a, v128_t b) {
                return D ? vmax(a, b) : vmin(a, b);
            }
            TOPK_INLINE static v128_t hi(v128_t a, v128_t b) {
                return D ? vmin(a, b) : vmax(a, b);
            }
            TOPK_INLINE static v128_t first(v128_t a, v128_t b) {
                return D ? vlt(b, a) : vlt(a, b);
            } // a strictly first
            TOPK_INLINE static bool none_first(v128_t a, v128_t b) {
                const v128_t ge = D ? vge(b, a) : vge(a, b);
                if constexpr (W16)
                    return wasm_i16x8_all_true(ge);
                else
                    return wasm_i32x4_all_true(ge);
            }
            TOPK_INLINE static bool first(key a, key b) {
                using T = std::conditional_t<S, std::conditional_t<W16, i16, i32>, key>;
                return D ? T(b) < T(a) : T(a) < T(b);
            }
            TOPK_INLINE static key next(key b) {
                return key(D ? b - 1 : b + 1);
            } // the key right after b
            TOPK_INLINE static v128_t splat(key x) {
                if constexpr (W16)
                    return wasm_i16x8_splat(x);
                else
                    return wasm_i32x4_splat(x);
            }
            TOPK_INLINE static v128_t load_splat(const key* p) {
                if constexpr (W16)
                    return wasm_v128_load16_splat(p);
                else
                    return wasm_v128_load32_splat(p);
            }
            template <int I> TOPK_INLINE static key lane(v128_t v) {
                if constexpr (W16)
                    return wasm_u16x8_extract_lane(v, I);
                else
                    return wasm_u32x4_extract_lane(v, I);
            }
            TOPK_INLINE static u32 bits(v128_t m) { // a bit a lane
                if constexpr (W16)
                    return wasm_i16x8_bitmask(m);
                else
                    return wasm_i32x4_bitmask(m);
            }
            TOPK_INLINE static v128_t eq(v128_t a, v128_t b) {
                if constexpr (W16)
                    return wasm_i16x8_eq(a, b);
                else
                    return wasm_i32x4_eq(a, b);
            }
        };
        template <class M> TOPK_INLINE inline u32 ctz(M m) {
            if constexpr (sizeof(M) == 8)
                return u32(__builtin_ctzll(m));
            else
                return u32(__builtin_ctz(m));
        }
        template <class M> TOPK_INLINE inline u32 popcount(M m) {
            if constexpr (sizeof(M) == 8)
                return u32(__builtin_popcountll(m));
            else
                return u32(__builtin_popcount(m));
        }

        TOPK_INLINE inline v128_t load(const void* p) {
            return wasm_v128_load(p);
        }
        template <class O> TOPK_INLINE inline v128_t rev(v128_t v) {
            if constexpr (O::L == 8)
                return wasm_i16x8_shuffle(v, v, 7, 6, 5, 4, 3, 2, 1, 0);
            else
                return wasm_i32x4_shuffle(v, v, 3, 2, 1, 0);
        }
        template <class O>
        TOPK_INLINE inline v128_t
        lo4(const typename O::key* p) { // lane-wise first of 4 vectors
            constexpr u32 L = O::L;
            return O::lo(O::lo(load(p), load(p + L)),
                         O::lo(load(p + 2 * L), load(p + 3 * L)));
        }
        template <class O> TOPK_INLINE inline v128_t lo8(const typename O::key* p) {
            return O::lo(lo4<O>(p), lo4<O>(p + 4 * O::L));
        }
        template <class O>
        TOPK_INLINE inline v128_t hlo(v128_t m) { // every lane the first of m
            if constexpr (O::L == 8) {
                m = O::lo(m, wasm_i16x8_shuffle(m, m, 4, 5, 6, 7, 0, 1, 2, 3));
                m = O::lo(m, wasm_i16x8_shuffle(m, m, 2, 3, 0, 1, 6, 7, 4, 5));
                return O::lo(m, wasm_i16x8_shuffle(m, m, 1, 0, 3, 2, 5, 4, 7, 6));
            } else {
                m = O::lo(m, wasm_i32x4_shuffle(m, m, 2, 3, 0, 1));
                return O::lo(m, wasm_i32x4_shuffle(m, m, 1, 0, 3, 2));
            }
        }
        // bit i set when p[i] comes before thr, over 4 vectors (16 or 32 keys)
        template <class O>
        TOPK_INLINE inline u32 first4(const typename O::key* p, v128_t thr) {
            constexpr u32 L = O::L;
            const v128_t a = O::first(load(p), thr), b = O::first(load(p + L), thr),
                         c = O::first(load(p + 2 * L), thr),
                         d = O::first(load(p + 3 * L), thr);
            if constexpr (L == 8)
                return u32(wasm_i8x16_bitmask(wasm_i8x16_narrow_i16x8(a, b))) |
                       u32(wasm_i8x16_bitmask(wasm_i8x16_narrow_i16x8(c, d))) << 16;
            else
                return wasm_i8x16_bitmask(wasm_i8x16_narrow_i16x8(
                    wasm_i16x8_narrow_i32x4(a, b), wasm_i16x8_narrow_i32x4(c, d)));
        }
        template <class O>
        TOPK_INLINE inline typename O::mask first8(const typename O::key* p,
                                                   v128_t thr) {
            using M = typename O::mask;
            return M(first4<O>(p, thr)) | M(first4<O>(p + 4 * O::L, thr)) << (4 * O::L);
        }

        // The first m = 1..L-1 keys at p into a vector, O::last after them; and back.
        template <class O>
        TOPK_INLINE inline v128_t load_part(const typename O::key* p, u32 m) {
            auto pad = [](v128_t v, v128_t keep) TOPK_INLINE {
                if constexpr (O::last == typename O::key(~0u))
                    return wasm_v128_or(v, wasm_v128_not(keep));
                else
                    return wasm_v128_bitselect(v, O::splat(O::last), keep);
            };
            if constexpr (O::L == 8) {
                const v128_t z = wasm_i16x8_splat(0);
                switch (m) {
                    case 1:
                        return pad(wasm_v128_load16_lane(p, z, 0),
                                   wasm_i16x8_const(-1, 0, 0, 0, 0, 0, 0, 0));
                    case 2:
                        return pad(wasm_v128_load32_zero(p),
                                   wasm_i16x8_const(-1, -1, 0, 0, 0, 0, 0, 0));
                    case 3:
                        return pad(
                            wasm_v128_load16_lane(p + 2, wasm_v128_load32_zero(p), 2),
                            wasm_i16x8_const(-1, -1, -1, 0, 0, 0, 0, 0));
                    case 4:
                        return pad(wasm_v128_load64_zero(p),
                                   wasm_i16x8_const(-1, -1, -1, -1, 0, 0, 0, 0));
                    case 5:
                        return pad(
                            wasm_v128_load16_lane(p + 4, wasm_v128_load64_zero(p), 4),
                            wasm_i16x8_const(-1, -1, -1, -1, -1, 0, 0, 0));
                    case 6:
                        return pad(
                            wasm_v128_load32_lane(p + 4, wasm_v128_load64_zero(p), 2),
                            wasm_i16x8_const(-1, -1, -1, -1, -1, -1, 0, 0));
                    case 7:
                        return pad(wasm_v128_load16_lane(
                                       p + 6,
                                       wasm_v128_load32_lane(
                                           p + 4, wasm_v128_load64_zero(p), 2),
                                       6),
                                   wasm_i16x8_const(-1, -1, -1, -1, -1, -1, -1, 0));
                }
            } else {
                switch (m) {
                    case 1:
                        return pad(wasm_v128_load32_zero(p),
                                   wasm_i32x4_const(-1, 0, 0, 0));
                    case 2:
                        return pad(wasm_v128_load64_zero(p),
                                   wasm_i32x4_const(-1, -1, 0, 0));
                    case 3:
                        return pad(
                            wasm_v128_load32_lane(p + 2, wasm_v128_load64_zero(p), 2),
                            wasm_i32x4_const(-1, -1, -1, 0));
                }
            }
            return load(p);
        }
        template <class O>
        TOPK_INLINE inline void store_part(typename O::key* p, v128_t v,
                                           u32 m) { // m = 1..L
            if constexpr (O::L == 8) {
                switch (m) {
                    case 1:
                        return wasm_v128_store16_lane(p, v, 0);
                    case 2:
                        return wasm_v128_store32_lane(p, v, 0);
                    case 3:
                        return wasm_v128_store32_lane(p, v, 0),
                               wasm_v128_store16_lane(p + 2, v, 2);
                    case 4:
                        return wasm_v128_store64_lane(p, v, 0);
                    case 5:
                        return wasm_v128_store64_lane(p, v, 0),
                               wasm_v128_store16_lane(p + 4, v, 4);
                    case 6:
                        return wasm_v128_store64_lane(p, v, 0),
                               wasm_v128_store32_lane(p + 4, v, 2);
                    case 7:
                        return wasm_v128_store64_lane(p, v, 0),
                               wasm_v128_store32_lane(p + 4, v, 2),
                               wasm_v128_store16_lane(p + 6, v, 6);
                }
            } else {
                switch (m) {
                    case 1:
                        return wasm_v128_store32_lane(p, v, 0);
                    case 2:
                        return wasm_v128_store64_lane(p, v, 0);
                    case 3:
                        return wasm_v128_store64_lane(p, v, 0),
                               wasm_v128_store32_lane(p + 2, v, 2);
                }
            }
            wasm_v128_store(p, v);
        }

        // Sorting networks in registers; missing keys padded with O::last.
        template <class O>
        TOPK_INLINE inline void ce(v128_t& a, v128_t& b) { // lane-wise compare-exchange
            const v128_t l = O::lo(a, b);
            b = O::hi(a, b), a = l;
        }
        // 32-bit keys. L and H each a bitonic run of 4 -> each sorted. Rev: H comes out
        // reversed, and L reversed into H's place, the order the next merge wants.
        template <class O, bool Rev = false>
        TOPK_INLINE inline void bitonic4x2(v128_t& L, v128_t& H) {
            v128_t a = wasm_i32x4_shuffle(L, H, 0, 1, 4, 5),
                   b = wasm_i32x4_shuffle(L, H, 2, 3, 6, 7);
            ce<O>(a, b);
            v128_t c = wasm_i32x4_shuffle(a, b, 0, 4, 2, 6),
                   d = wasm_i32x4_shuffle(a, b, 1, 5, 3, 7);
            ce<O>(c, d);
            if constexpr (Rev)
                L = wasm_i32x4_shuffle(c, d, 7, 3, 6, 2),
                H = wasm_i32x4_shuffle(c, d, 5, 1, 4, 0);
            else
                L = wasm_i32x4_shuffle(c, d, 0, 4, 1, 5),
                H = wasm_i32x4_shuffle(c, d, 2, 6, 3, 7);
        }
        template <class O> TOPK_INLINE inline void sort4(v128_t& x) {
            v128_t y = wasm_i32x4_shuffle(x, x, 1, 0, 3, 2);
            x = wasm_i32x4_shuffle(O::lo(x, y), O::hi(x, y), 0, 5, 2, 7);
            y = wasm_i32x4_shuffle(x, x, 2, 3, 0, 1);
            x = wasm_i32x4_shuffle(O::lo(x, y), O::hi(x, y), 0, 1, 6, 7);
            y = wasm_i32x4_shuffle(x, x, 0, 2, 1, 3);
            x = wasm_i32x4_shuffle(O::lo(x, y), O::hi(x, y), 0, 1, 6, 3);
        }
        template <class O> TOPK_INLINE inline void sort8(v128_t& r0, v128_t& r1) {
            ce<O>(r0, r1); // four sorted pairs, one per lane
            v128_t x = wasm_i32x4_shuffle(r0, r1, 0, 4, 2, 6),
                   y = wasm_i32x4_shuffle(r1, r0, 1, 5, 3, 7);
            ce<O>(x, y); // pairs 0,1 and 2,3 merged as bitonic runs: distance 2
            v128_t c = wasm_i32x4_shuffle(x, y, 0, 4, 2, 6),
                   d = wasm_i32x4_shuffle(x, y, 1, 5, 3, 7);
            ce<O>(c, d); // distance 1: runs A = c0 d0 c1 d1, B = c2 d2 c3 d3
            r0 = wasm_i32x4_shuffle(c, d, 0, 4, 1, 5),
            r1 = wasm_i32x4_shuffle(c, d, 7, 3, 6, 2); // A, B reversed
            ce<O>(r0, r1);
            bitonic4x2<O>(r0, r1);
        }
        // K <= 8 leaves r2, r3 unsorted.
        template <class O, u32 K = 16>
        TOPK_INLINE inline void sort16(v128_t& r0, v128_t& r1, v128_t& r2, v128_t& r3) {
            ce<O>(r0, r1), ce<O>(r2, r3), ce<O>(r0, r2), ce<O>(r1, r3),
                ce<O>(r1, r2); // columns sorted
            // transpose: rows are the sorted columns, the 2nd and 4th reversed for the
            // merges
            const v128_t t0 = wasm_i32x4_shuffle(r0, r1, 0, 4, 1, 5),
                         t1 = wasm_i32x4_shuffle(r0, r1, 2, 6, 3, 7);
            const v128_t t2 = wasm_i32x4_shuffle(r2, r3, 0, 4, 1, 5),
                         t3 = wasm_i32x4_shuffle(r2, r3, 2, 6, 3, 7);
            r0 = wasm_i32x4_shuffle(t0, t2, 0, 1, 4, 5),
            r1 = wasm_i32x4_shuffle(t2, t0, 3, 2, 7, 6);
            r2 = wasm_i32x4_shuffle(t1, t3, 0, 1, 4, 5),
            r3 = wasm_i32x4_shuffle(t3, t1, 3, 2, 7, 6);
            ce<O>(r0, r1), ce<O>(r2, r3);
            bitonic4x2<O>(r0, r1),
                bitonic4x2<O, true>(r2, r3); // r0 r1 sorted, r2 r3 sorted and reversed
            ce<O>(r0, r2), ce<O>(r1, r3);
            ce<O>(r0, r1);
            bitonic4x2<O>(r0, r1);
            if constexpr (K > 8)
                ce<O>(r2, r3), bitonic4x2<O>(r2, r3);
        }
        // 16-bit keys. L and H each a bitonic run of 8 -> each sorted: distance 4, 2,
        // 1, two shuffles a level.
        template <class O> TOPK_INLINE inline void bitonic8x2(v128_t& L, v128_t& H) {
            v128_t x = wasm_i16x8_shuffle(L, H, 0, 1, 2, 3, 8, 9, 10, 11),
                   y = wasm_i16x8_shuffle(L, H, 4, 5, 6, 7, 12, 13, 14, 15);
            ce<O>(x, y);
            v128_t x2 = wasm_i16x8_shuffle(x, y, 0, 1, 8, 9, 4, 5, 12, 13),
                   y2 = wasm_i16x8_shuffle(x, y, 2, 3, 10, 11, 6, 7, 14, 15);
            ce<O>(x2, y2);
            v128_t x3 = wasm_i16x8_shuffle(x2, y2, 0, 8, 2, 10, 4, 12, 6, 14),
                   y3 = wasm_i16x8_shuffle(x2, y2, 1, 9, 3, 11, 5, 13, 7, 15);
            ce<O>(x3, y3);
            L = wasm_i16x8_shuffle(x3, y3, 0, 8, 1, 9, 2, 10, 3, 11),
            H = wasm_i16x8_shuffle(x3, y3, 4, 12, 5, 13, 6, 14, 7, 15);
        }
        // 8 keys in one vector: Batcher's 19 compare-exchanges in six layers, each a
        // shuffle to the partner, lo and hi, and a shuffle picking each lane's side.
        template <class O> TOPK_INLINE inline void sort1x8(v128_t& x) {
            auto layer = [&](v128_t y, auto pick) TOPK_INLINE {
                x = pick(O::lo(x, y), O::hi(x, y));
            };
#define TOPK_LAYER(p0, p1, p2, p3, p4, p5, p6, p7, s0, s1, s2, s3, s4, s5, s6, s7)     \
    layer(wasm_i16x8_shuffle(x, x, p0, p1, p2, p3, p4, p5, p6, p7),                    \
          [](v128_t l, v128_t h) TOPK_INLINE {                                         \
              return wasm_i16x8_shuffle(l, h, s0, s1, s2, s3, s4, s5, s6, s7);         \
          })
            TOPK_LAYER(1, 0, 3, 2, 5, 4, 7, 6, 0, 9, 2, 11, 4, 13, 6, 15);
            TOPK_LAYER(2, 3, 0, 1, 6, 7, 4, 5, 0, 1, 10, 11, 4, 5, 14, 15);
            TOPK_LAYER(0, 2, 1, 3, 4, 6, 5, 7, 0, 1, 10, 3, 4, 5, 14, 7);
            TOPK_LAYER(4, 5, 6, 7, 0, 1, 2, 3, 0, 1, 2, 3, 12, 13, 14, 15);
            TOPK_LAYER(0, 1, 4, 5, 2, 3, 6, 7, 0, 1, 2, 3, 12, 13, 6, 7);
            TOPK_LAYER(0, 2, 1, 4, 3, 6, 5, 7, 0, 1, 10, 3, 12, 5, 14, 7);
#undef TOPK_LAYER
        }
        // 8 vectors: columns sorted (the same 19 compare-exchanges, lane-wise), then
        // transposed, so each vector is a sorted 8
        template <class O> TOPK_INLINE inline void sort_cols8(v128_t* r) {
            ce<O>(r[0], r[1]), ce<O>(r[2], r[3]), ce<O>(r[4], r[5]), ce<O>(r[6], r[7]);
            ce<O>(r[0], r[2]), ce<O>(r[1], r[3]), ce<O>(r[4], r[6]), ce<O>(r[5], r[7]);
            ce<O>(r[1], r[2]), ce<O>(r[5], r[6]);
            ce<O>(r[0], r[4]), ce<O>(r[1], r[5]), ce<O>(r[2], r[6]), ce<O>(r[3], r[7]);
            ce<O>(r[2], r[4]), ce<O>(r[3], r[5]);
            ce<O>(r[1], r[2]), ce<O>(r[3], r[4]), ce<O>(r[5], r[6]);
            v128_t t[8], u[8];
            for (u32 i = 0; i < 4; ++i) {
                t[2 * i] = wasm_i16x8_shuffle(r[2 * i], r[2 * i + 1], 0, 8, 1, 9, 2, 10,
                                              3, 11);
                t[2 * i + 1] = wasm_i16x8_shuffle(r[2 * i], r[2 * i + 1], 4, 12, 5, 13,
                                                  6, 14, 7, 15);
            }
            for (u32 h = 0; h < 8; h += 4)
                for (u32 i = 0; i < 2; ++i) {
                    u[h + 2 * i] =
                        wasm_i32x4_shuffle(t[h + i], t[h + i + 2], 0, 4, 1, 5);
                    u[h + 2 * i + 1] =
                        wasm_i32x4_shuffle(t[h + i], t[h + i + 2], 2, 6, 3, 7);
                }
            for (u32 i = 0; i < 4; ++i)
                r[2 * i] = wasm_i64x2_shuffle(u[i], u[i + 4], 0, 2),
                      r[2 * i + 1] = wasm_i64x2_shuffle(u[i], u[i + 4], 1, 3);
        }
        // L and H each a bitonic run of one vector -> each sorted
        template <class O> TOPK_INLINE inline void bitonic_pair(v128_t& L, v128_t& H) {
            if constexpr (O::L == 8)
                bitonic8x2<O>(L, H);
            else
                bitonic4x2<O>(L, H);
        }
        // r[0, M) and r[M, 2M) sorted -> r[0, 2M) sorted: the second half reversed,
        // then a bitonic merge.
        template <class O, u32 M> TOPK_INLINE inline void merge_net(v128_t* r) {
            for (u32 j = 0; j < M / 2; ++j)
                std::swap(r[M + j], r[2 * M - 1 - j]);
            for (u32 j = M; j < 2 * M; ++j)
                r[j] = rev<O>(r[j]);
            for (u32 d = M; d; d /= 2)
                for (u32 j = 0; j < 2 * M; ++j)
                    if (!(j & d))
                        ce<O>(r[j], r[j + d]);
            for (u32 j = 0; j < 2 * M; j += 2)
                bitonic_pair<O>(r[j], r[j + 1]);
        }
        // N vectors (a power of two) sorted as one run. K: 32-bit keys, N = 4, K <= 8
        // leaves r[2], r[3] unsorted.
        template <class O, u32 N, u32 K = 64>
        TOPK_INLINE inline void sort_vecs(v128_t* r) {
            if constexpr (O::L == 4 && N == 1)
                sort4<O>(r[0]);
            else if constexpr (O::L == 4 && N == 2)
                sort8<O>(r[0], r[1]);
            else if constexpr (O::L == 4 && N == 4)
                sort16<O, K>(r[0], r[1], r[2], r[3]);
            else if constexpr (O::L == 8 && N == 1)
                sort1x8<O>(r[0]);
            else if constexpr (O::L == 8 && N == 8) {
                sort_cols8<O>(r);
                for (u32 j = 0; j < 8; j += 2)
                    merge_net<O, 1>(r + j);
                merge_net<O, 2>(r), merge_net<O, 2>(r + 4);
                merge_net<O, 4>(r);
            } else {
                sort_vecs<O, N / 2>(r), sort_vecs<O, N / 2>(r + N / 2);
                merge_net<O, N / 2>(r);
            }
        }
        // m <= N L keys from a sorted into out, padded with O::last to N vectors.
        template <class O, u32 N>
        TOPK_INLINE inline void sort_chunk(const typename O::key* a, u32 m,
                                           typename O::key* out) {
            constexpr u32 L = O::L;
            v128_t r[N];
            for (u32 j = 0; j < N; ++j) {
                const u32 at = L * j;
                r[j] = at + L <= m ? load(a + at)
                       : at < m    ? load_part<O>(a + at, m - at)
                                   : O::splat(O::last);
            }
            sort_vecs<O, N>(r);
            for (u32 j = 0; j < N; ++j)
                wasm_v128_store(out + L * j, r[j]);
        }
        // The keys a sort_small takes: 16 32-bit, 64 16-bit.
        template <class O> constexpr u32 small_max = O::L == 8 ? 64 : 16;
        // a[0, n) sorted, n <= Max <= small_max (with K < n only a[0, K) need come out
        // sorted, the rest a permutation). Max keeps the bigger networks out of the
        // code.
        template <class O, u32 K = 64, u32 Max = small_max<O>>
        inline void sort_small(typename O::key* a, u32 n) {
            constexpr u32 L = O::L;
            auto run = [&]<u32 N, u32 KK>() TOPK_INLINE {
                v128_t r[N];
                for (u32 j = 0; j < N; ++j) {
                    const u32 at = L * j;
                    r[j] = at + L <= n ? load(a + at)
                           : at < n    ? load_part<O>(a + at, n - at)
                                       : O::splat(O::last);
                }
                sort_vecs<O, N, KK>(r);
                for (u32 j = 0; j < N; ++j) {
                    const u32 at = L * j;
                    if (at + L <= n)
                        wasm_v128_store(a + at, r[j]);
                    else if (at < n)
                        store_part<O>(a + at, r[j], n - at);
                }
            };
            if (Max <= L || n <= L)
                run.template operator()<1, 64>();
            else if constexpr (Max > L) {
                if (Max <= 2 * L || n <= 2 * L)
                    run.template operator()<2, 64>();
                else if constexpr (Max > 2 * L) {
                    if (Max <= 4 * L || n <= 4 * L) {
                        if (n == 4 * L) // padding must end up last, so pruning only
                                        // without it
                            run.template operator()<4, K>();
                        else
                            run.template operator()<4, 64>();
                    } else if constexpr (Max > 4 * L)
                        run.template operator()<8, 64>();
                }
            }
        }

        // t holds the K first keys so far, in order, in ceil(K/L) vectors; x (splat)
        // goes in as t = lo(t, hi(t moved up one lane, x)), and t's last lane falls
        // off. No branches.
        template <class O, u32 V>
        TOPK_INLINE inline void insert(v128_t (&t)[V], v128_t x) {
            v128_t prev = x;
            for (u32 j = 0; j < V; ++j) {
                v128_t up;
                if constexpr (O::L == 8)
                    up = wasm_i16x8_shuffle(prev, t[j], 7, 8, 9, 10, 11, 12, 13, 14);
                else
                    up = wasm_i32x4_shuffle(prev, t[j], 3, 4, 5, 6);
                prev = t[j];
                t[j] = O::lo(t[j], O::hi(up, x));
            }
        }

        // The last (in order) of the A L lane firsts of [p, end) cut to whole 4-vector
        // chunks: A L keys at distinct places come no later, so it bounds the (A L)-th
        // key. A <= 4, end - p >= 4 L.
        template <class O, u32 A>
        inline typename O::key bound(const typename O::key* p,
                                     const typename O::key* end) {
            constexpr u32 L = O::L;
            v128_t m[A];
            for (u32 j = 0; j < A; ++j)
                m[j] = O::splat(O::last);
            for (const typename O::key* lim = end - 4 * L; p <= lim; p += 4 * L) {
                TOPK_OPAQUE(p);
                for (u32 i = 0; i < 4; ++i)
                    m[i % A] = O::lo(m[i % A], load(p + L * i));
            }
            v128_t x = m[0];
            for (u32 j = 1; j < A; ++j)
                x = O::hi(x, m[j]);
            x = O::hi(x, wasm_i32x4_shuffle(x, x, 2, 3, 0, 1));
            x = O::hi(x, wasm_i32x4_shuffle(x, x, 1, 0, 3, 2));
            if constexpr (L == 8)
                x = O::hi(x, wasm_i16x8_shuffle(x, x, 1, 0, 3, 2, 5, 4, 7, 6));
            return O::template lane<0>(x);
        }

        // K = 1, n > L: the first key swapped into a[0]. Tracks only the block holding
        // the first key so far and finds the key in it at the end.
        template <class O> inline void first_to_front(typename O::key* a, u32 n) {
            using key = typename O::key;
            constexpr u32 L = O::L;
            key *const end = a + n, *best = nullptr;
            v128_t thr = O::load_splat(a);
            auto block = [&](key* p, v128_t m) TOPK_INLINE {
                if (O::none_first(m, thr))
                    return;
                TOPK_RARE();
                thr = hlo<O>(m), best = p;
            };
            if (n > 4 * L) {
                key* p = a + 1;
                for (key* lim = end - 16 * L; p < lim; p += 16 * L) {
                    TOPK_OPAQUE(p);
                    block(p, O::lo(lo8<O>(p), lo8<O>(p + 8 * L)));
                }
                if (end - p > 8 * L)
                    block(p, lo8<O>(p)), p += 8 * L;
                if (end - p > 4 * L)
                    block(p, lo4<O>(p));
                block(end - 4 * L, lo4<O>(end - 4 * L));
                if (!best)
                    return;
                const v128_t eq = O::splat(
                    O::next(O::template lane<0>(thr))); // before it: equal to thr
                for (;; best += 4 * L) {
                    TOPK_OPAQUE(best);
                    if (const u32 bits = first4<O>(best, eq)) {
                        best += __builtin_ctz(bits);
                        break;
                    }
                }
            } else {
                key* p = a + 1;
                for (; p + L < end; p += L)
                    block(p, load(p));
                block(end - L, load(end - L));
                if (!best)
                    return;
                best += __builtin_ctz(O::bits(O::eq(load(best), thr)));
            }
            const key x = *best;
            *best = *a, *a = x;
        }

        // The K first keys by a scan; K <= 16.
        template <class O, u32 K> void scan_sort(typename O::key* a, u32 n) {
            using key = typename O::key;
            using mask = typename O::mask;
            constexpr u32 L = O::L, V = (K + L - 1) / L, Q = (K - 1) / L,
                          R = (K - 1) % L, A = V <= 2 ? V : 4, P = 16 / L;
            static_assert(K >= 1 && K <= 16);
            if constexpr (K == 1)
                return n <= L ? sort_small<O, 1, L>(a, n) : first_to_front<O>(a, n);
            if (n <= 16)
                return sort_small<O, K, 16>(a, n);
            // The first 16 keys (P vectors) sorted in place; t: the first V vectors.
            // t[0, K) are the K first so far, the lanes after K keys already passed
            // over (they stay in a too).
            v128_t r[P], t[V];
            for (u32 j = 0; j < P; ++j)
                r[j] = load(a + L * j);
            sort_vecs<O, P, K>(r);
            for (u32 j = 0; j < P; ++j)
                wasm_v128_store(a + L * j, r[j]);
            for (u32 j = 0; j < V; ++j)
                t[j] = r[j];
            // cur: the K-th key so far; a key before it goes into t, and cur takes its
            // place in a. cur only moves forward, so whatever has been scanned (or
            // written back) never passes again, and blocks may overlap.
            key cur = O::template lane<R>(t[Q]), cap = O::last;
            u32 takes = 0, budget = 2 * K + 8;
            v128_t thr = O::splat(cur);
            key *p = a + 16, *const end = a + n;
            // Capped: keys must also come before cap, just after a bound on the K-th
            // key (see below).
            auto scan = [&]<bool Capped>(key* p) TOPK_INLINE -> key* {
                key f = Capped && O::first(cap, cur) ? cap : cur;
                if constexpr (Capped)
                    thr = O::splat(f);
                auto take = [&](key* q, key x) TOPK_INLINE {
                    *q = cur;
                    insert<O>(t, O::splat(x));
                    cur = O::template lane<R>(t[Q]);
                    if constexpr (Capped)
                        f = O::first(cap, cur) ? cap : cur, thr = O::splat(f);
                    else
                        f = cur, thr = O::splat(cur), ++takes;
                };
                auto hits = [&](key* p, auto bits) TOPK_INLINE {
                    do {
                        key* q = p + ctz(bits);
                        if (const key x = *q; O::first(x, f))
                            take(q, x);
                        bits &= bits - 1;
                    } while (bits);
                };
                if (end - p < 4 * L) {
                    if (end - p >= L) {
                        auto block1 = [&](key* p) TOPK_INLINE {
                            if (const u32 bits = O::bits(O::first(load(p), thr)))
                                hits(p, bits);
                        };
                        for (; p + L < end; p += L)
                            block1(p);
                        block1(end - L);
                    } else {
                        for (; p < end; ++p)
                            if (const key x = *p; O::first(x, f))
                                take(p, x);
                    }
                    return nullptr;
                }
                for (key* lim = end - 8 * L; p < lim; p += 8 * L) {
                    TOPK_OPAQUE(p);
                    if (O::none_first(lo8<O>(p), thr))
                        continue;
                    TOPK_RARE();
                    const mask bits = first8<O>(p, thr);
                    // Many takes for what has been scanned: keys are arriving in
                    // reverse order. Stop here; the caller caps keys at a bound on the
                    // K-th key and goes on from this block.
                    if constexpr (!Capped)
                        if (takes + popcount(bits) > budget + (u32(p - a) >> 4))
                            [[unlikely]] {
                            budget = 1u << 30;
                            if (end - p >= 64)
                                return p;
                        }
                    hits(p, bits);
                }
                auto block4 = [&](key* p) TOPK_INLINE {
                    if (O::none_first(lo4<O>(p), thr))
                        return;
                    TOPK_RARE();
                    hits(p, first4<O>(p, thr));
                };
                if (end - p > 4 * L)
                    block4(p);
                block4(end - 4 * L);
                return nullptr;
            };
            if (key* at = scan.template operator()<false>(p)) {
                const key b = bound<O, A>(at, end);
                cap = b == O::last ? b : O::next(b);
                scan.template operator()<true>(at);
            }
            for (u32 j = 0; j < Q; ++j)
                wasm_v128_store(a + L * j, t[j]);
            store_part<O>(a + L * Q, t[Q], R + 1);
        }

        // Merges sorted runs x[0, lx) and y[0, ly) (multiples of L, at least L) into o,
        // a vector at a time: the carry and the next vector from whichever run's next
        // key comes first go through an L+L network. Once `need` keys are out the rest
        // is copied as it is: what is left of x, the carry, what is left of y (any
        // padding stays last).
        template <class O>
        inline void merge_runs(const typename O::key* x, u32 lx,
                               const typename O::key* y, u32 ly, typename O::key* o,
                               u32 need) {
            constexpr u32 L = O::L;
            const typename O::key *const ex = x + lx, *const ey = y + ly;
            v128_t c = load(x);
            auto step = [&](v128_t w) TOPK_INLINE {
                w = rev<O>(w);
                ce<O>(c, w);
                bitonic_pair<O>(c, w);
                wasm_v128_store(o, c), o += L;
                c = w;
            };
            step(load(y));
            x += L, y += L;
            u32 left = (lx + ly) / L - 2;
            if (const u32 cut = (need - 1) / L; cut < left)
                left = cut; // L + L cut >= need keys out
            for (; left; --left) {
                const typename O::key* q;
                if (y == ey || (x != ex && !O::first(*y, *x)))
                    q = x, x += L;
                else
                    q = y, y += L;
                step(load(q));
            }
            for (; x != ex; x += L, o += L)
                wasm_v128_store(o, load(x));
            wasm_v128_store(o, c), o += L;
            for (; y != ey; y += L, o += L)
                wasm_v128_store(o, load(y));
        }

        // a[0, n) sorted (only a[0, need) when need < n, the rest a permutation):
        // networks on 16 vectors, then merges through two scratch buffers.
        template <class O> void sort_any(typename O::key* a, u32 n, u32 need = ~0u) {
            using key = typename O::key;
            constexpr u32 L = O::L, C = 16 * L;
            if (n <= small_max<O>)
                return sort_small<O>(a, n);
            const u32 full = n / C * C, m = n - full,
                      T = m == 0       ? 0
                          : m <= 4 * L ? 4 * L
                          : m <= 8 * L ? 8 * L
                                       : C,
                      len = full + T;
            static key*
                scratch; // grown, never cleared (clearing costs about a fuel a byte)
            static u32 size;
            if (size < 2 * len)
                delete[] scratch, scratch = new key[size = 2 * len];
            key *src = scratch, *dst = src + len;
            for (u32 i = 0; i < full; i += C)
                sort_chunk<O, 16>(a + i, C, src + i);
            if (T == 4 * L)
                sort_chunk<O, 4>(a + full, m, src + full);
            else if (T == 8 * L)
                sort_chunk<O, 8>(a + full, m, src + full);
            else if (T == C)
                sort_chunk<O, 16>(a + full, m, src + full);
            for (u32 w = C; w < len; w *= 2) {
                for (u32 j = 0; j < len; j += 2 * w) {
                    if (j + w >= len) {
                        for (u32 i = j; i < len; i += L)
                            wasm_v128_store(dst + i, load(src + i));
                    } else
                        merge_runs<O>(src + j, w, src + j + w,
                                      len - j - w < w ? len - j - w : w, dst + j,
                                      2 * w >= len ? need : ~0u);
                }
                key* t = src;
                src = dst, dst = t;
            }
            u32 i = 0;
            for (; i + L <= n; i += L)
                wasm_v128_store(a + i, load(src + i));
            if (i < n)
                store_part<O>(a + i, load(src + i), n - i);
        }

        // Swaps the keys of a[w, n) that come before cap down to a[w, ...) and returns
        // where they end.
        template <class O>
        inline u32 gather(typename O::key* a, u32 w, u32 n, typename O::key cap) {
            using key = typename O::key;
            constexpr u32 L = O::L;
            const v128_t thr = O::splat(cap);
            key *o = a + w, *p = a + w, *const end = a + n;
            auto hits = [&](key* p, u32 bits) TOPK_INLINE {
                do {
                    key* q = p + __builtin_ctz(bits);
                    const key x = *q;
                    *q = *o, *o++ = x;
                    bits &= bits - 1;
                } while (bits);
            };
            if (end - p >= 4 * L)
                for (key* lim = end - 4 * L; p <= lim; p += 4 * L) {
                    TOPK_OPAQUE(p);
                    if (O::none_first(lo4<O>(p), thr))
                        continue;
                    TOPK_RARE();
                    hits(p, first4<O>(p, thr));
                }
            for (; end - p >= L; p += L)
                if (const u32 bits = O::bits(O::first(load(p), thr)))
                    hits(p, bits);
            for (; p < end; ++p)
                if (const key x = *p; O::first(x, cap))
                    *p = *o, *o++ = x;
            return u32(o - a);
        }

        // Large k: a threshold from 16 sampled keys, every key at or before it gathered
        // to the front, repeated while that is still well over k keys, then the front
        // sorted as far as its first k. k <= n.
        template <class O> void select_sort(typename O::key* a, u32 n, u32 k) {
            using key = typename O::key;
            while (n > k + k / 2 + 32) {
                alignas(16) key s[16];
                const u32 step = n / 16;
                for (u32 j = 0; j < 16; ++j)
                    s[j] = a[step / 2 + j * step];
                sort_small<O, 64, 16>(s, 16);
                // Random keys: about n (i + 1) / 17 come no later than s[i]; keys in
                // order: n (i + 1/2) / 16. Aim for k + k/8 + 8 by the higher of the
                // two, between two sample keys by interpolation, then whole sample keys
                // while that is too few.
                const int64_t want = k + k / 8 + 8,
                              pos = std::max(want * 17 * 65536 / (n + 1) - 65536,
                                             want * 16 * 65536 / n - 32768);
                u32 i = pos < 0 ? 0 : u32(pos >> 16), c = 0;
                if (pos >= 0 && i < 15) {
                    using S = std::conditional_t<O::L == 8, i16, i32>;
                    const auto v = [](key x) {
                        return O::is_signed ? int64_t(S(x)) : int64_t(x);
                    };
                    const key t =
                        key(v(s[i]) +
                            ((v(s[i + 1]) - v(s[i])) * int64_t(pos & 65535) >> 16));
                    if (t != O::last)
                        c = gather<O>(a, 0, n, O::next(t));
                    if (c < k)
                        ++i;
                }
                for (; c < k; ++i) {
                    if (i >= 16 || s[i] == O::last)
                        return sort_any<O>(a, n, k);
                    c = gather<O>(a, c, n, O::next(s[i]));
                }
                if (c == n)
                    break;
                n = c; // the k first keys are among these: k keys come no later than
                       // the threshold
            }
            sort_any<O>(a, n, k);
        }

        template <class T>
        constexpr bool is_key = std::is_same_v<T, u16> || std::is_same_v<T, i16> ||
                                std::is_same_v<T, u32> || std::is_same_v<T, i32>;
        template <class T, bool D>
        using ord_for = ord<sizeof(T) == 2, std::is_signed_v<T>, D>;
    } // namespace detail

    // K up to this goes to the dense scan, past it to select_sort (the cheaper for
    // either key width).
    constexpr u32 scan_max = 16;

    template <u32 K, bool Desc = false, class T> inline void partial_sort(T* a, u32 n) {
        static_assert(detail::is_key<T>);
        using O = detail::ord_for<T, Desc>;
        auto* p = reinterpret_cast<typename O::key*>(a);
        if constexpr (K <= scan_max)
            detail::scan_sort<O, K>(p, n);
        else
            detail::select_sort<O>(p, n, K);
    }
    template <bool Desc = false, class T> inline void sort(T* a, u32 n) {
        static_assert(detail::is_key<T>);
        using O = detail::ord_for<T, Desc>;
        detail::sort_any<O>(reinterpret_cast<typename O::key*>(a), n);
    }
    template <bool Desc = false, class T> inline void select_sort(T* a, u32 k, u32 n) {
        static_assert(detail::is_key<T>);
        using O = detail::ord_for<T, Desc>;
        detail::select_sort<O>(reinterpret_cast<typename O::key*>(a), n, k);
    }
    // k at run time: the dense kernels through a table of their instances, the rest by
    // select_sort.
    template <bool Desc = false, class T> inline void partial_sort(T* a, u32 k, u32 n) {
        static_assert(detail::is_key<T>);
        using fn = void (*)(T*, u32);
        static constexpr auto table = []<u32... I>(std::integer_sequence<u32, I...>) {
            return std::array<fn, sizeof...(I)>{&partial_sort<I + 1, Desc, T>...};
        }(std::make_integer_sequence<u32, scan_max>());
        if (k == 0)
            return;
        if (k <= scan_max)
            return table[k - 1](a, n);
        select_sort<Desc>(a, k, n);
    }
} // namespace topk
