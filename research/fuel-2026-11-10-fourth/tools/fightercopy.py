from pathlib import Path
import sys
p=Path(sys.argv[1])/'src/model/safety.cc';s=p.read_text().replace('''        auto& g = fighters[count];
        g = f;''','''        auto& g = fighters[count];
#if defined(__wasm_simd128__)
        static_assert(sizeof(Fighter) == 56 && std::is_trivially_copyable_v<Fighter>);
        const auto* src = reinterpret_cast<const unsigned char*>(&f);
        auto* dst = reinterpret_cast<unsigned char*>(&g);
        wasm_v128_store(dst, wasm_v128_load(src));
        wasm_v128_store(dst + 16, wasm_v128_load(src + 16));
        wasm_v128_store(dst + 32, wasm_v128_load(src + 32));
        wasm_v128_store64_lane(dst + 48, wasm_v128_load64_zero(src + 48), 0);
#else
        g = f;
#endif''');p.write_text(s)
