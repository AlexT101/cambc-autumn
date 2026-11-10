from pathlib import Path
import sys
p=Path(sys.argv[1])/'src/model/safety.h'
s=p.read_text().replace('#include <span>','#include <span>\n#if defined(__wasm_simd128__)\n#include <wasm_simd128.h>\n#endif')
for op,fun in [('&','and'),('|','or')]:
    old=f'friend constexpr Window operator{op}(Window a, Window b) {{ return {{a.lo {op} b.lo, a.hi {op} b.hi}}; }}'
    new=f'''friend constexpr Window operator{op}(Window a, Window b) {{
#if defined(__wasm_simd128__)
            if (!std::is_constant_evaluated()) {{
                Window c;
                wasm_v128_store(&c, wasm_v128_{fun}(wasm_v128_load(&a), wasm_v128_load(&b)));
                return c;
            }}
#endif
            return {{a.lo {op} b.lo, a.hi {op} b.hi}};
        }}'''
    assert old in s
    s=s.replace(old,new)
s=s.replace('constexpr explicit operator bool() const { return (lo | hi) != 0; }','''constexpr explicit operator bool() const {
#if defined(__wasm_simd128__)
            if (!std::is_constant_evaluated()) return wasm_v128_any_true(wasm_v128_load(this));
#endif
            return (lo | hi) != 0;
        }''')
p.write_text(s)
