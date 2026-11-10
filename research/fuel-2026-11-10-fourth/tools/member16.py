from pathlib import Path
import sys
p=Path(sys.argv[1])/'src/model/safety.cc';s=p.read_text()
s=s.replace('    std::vector<std::int32_t> x, y, reach;', '    std::vector<std::int8_t> x, y, reach;')
s=s.replace('const std::size_t padded = (n + 3) & ~std::size_t{3};','const std::size_t padded = (n + 15) & ~std::size_t{15};')
s=s.replace('t.x.assign(padded, 1 << 20), t.y.assign(padded, 1 << 20), t.reach.assign(padded, 0);','t.x.assign(padded, 0), t.y.assign(padded, 0), t.reach.assign(padded, 0);')
s=s.replace('t.x[i] = G.members[i].pos.x, t.y[i] = G.members[i].pos.y, t.reach[i] = G.members[i].reach;', 't.x[i] = static_cast<std::int8_t>(G.members[i].pos.x), t.y[i] = static_cast<std::int8_t>(G.members[i].pos.y), t.reach[i] = static_cast<std::int8_t>(G.members[i].reach);')
a=s.index('            // Member by member in order as below');b=s.index('            return;\n        }\n        bool track',a);t=s[a:b]
t=t.replace('minima four members at a time','minima sixteen members at a time')
t=t.replace('std::countr_zero(left) & ~3','std::countr_zero(left) & ~15').replace('& 15u','& 65535u').replace('std::uint64_t{15}', 'std::uint64_t{65535}')
t=t.replace('alignas(16) std::int32_t reach4[4], tie4[4];', 'alignas(16) std::int8_t reach16[16], tie16[16];')
t=t.replace('wasm_i32x4_', 'wasm_i8x16_').replace('wasm_i8x16_splat(near_x[k])','wasm_i8x16_splat(static_cast<std::int8_t>(near_x[k]))').replace('wasm_i8x16_splat(near_y[k])','wasm_i8x16_splat(static_cast<std::int8_t>(near_y[k]))').replace('wasm_i8x16_splat(near_first[k])','wasm_i8x16_splat(static_cast<std::int8_t>(near_first[k]))')
t=t.replace('reach4','reach16').replace('tie4','tie16').replace('j < 4','j < 16').replace('reach16[j] = reach, tie16[j] = tie;', 'reach16[j] = static_cast<std::int8_t>(reach), tie16[j] = static_cast<std::int8_t>(tie);')
s=s[:a]+t+s[b:];p.write_text(s)
