from pathlib import Path
import sys
p=Path(sys.argv[1])/'src/economy/camps.cc';s=p.read_text()
s=s.replace('''    for (std::size_t i = 0; i < group.members.size(); ++i)
        living += (fresh ? group.members[i].max_health : belief.health[i]) > 0;''','''    std::size_t i = 0;
#if defined(__wasm_simd128__)
    if (!fresh)
        for (; i + 4 <= group.members.size(); i += 4)
            living += std::popcount(static_cast<unsigned>(wasm_i32x4_bitmask(wasm_f32x4_gt(wasm_v128_load(&belief.health[i]), wasm_f32x4_splat(0)))));
#endif
    for (; i < group.members.size(); ++i)
        living += (fresh ? group.members[i].max_health : belief.health[i]) > 0;''')
s=s.replace('''        for (std::size_t m = 0; m < group.members.size(); ++m) {
            const float hp = fresh ? group.members[m].max_health : belief.health[m];
            if (hp > 0) elapsed += std::ceil(hp / strength);
        }''','''        std::size_t m = 0;
#if defined(__wasm_simd128__)
        if (!fresh) {
            const v128_t hit = wasm_f32x4_splat(strength), zero = wasm_f32x4_splat(0);
            for (; m + 4 <= group.members.size(); m += 4) {
                const v128_t hp = wasm_v128_load(&belief.health[m]);
                const v128_t turns = wasm_v128_and(wasm_f32x4_ceil(wasm_f32x4_div(hp, hit)), wasm_f32x4_gt(hp, zero));
                elapsed += wasm_f32x4_extract_lane(turns, 0);
                elapsed += wasm_f32x4_extract_lane(turns, 1);
                elapsed += wasm_f32x4_extract_lane(turns, 2);
                elapsed += wasm_f32x4_extract_lane(turns, 3);
            }
        }
#endif
        for (; m < group.members.size(); ++m) {
            const float hp = fresh ? group.members[m].max_health : belief.health[m];
            if (hp > 0) elapsed += std::ceil(hp / strength);
        }''');p.write_text(s)
