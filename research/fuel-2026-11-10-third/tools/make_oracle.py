"""Copy a candidate and compare Reach/ward results against the full calculation in each query.

Usage: make_oracle.py CAND TARGET (bot paths). Build TARGET in debug mode, run at 100M.
"""
from pathlib import Path
import subprocess
import sys

root = Path(__file__).resolve().parents[3]
source, target = map(Path, sys.argv[1:])
subprocess.run([str(root / 'copybot'), str(source), str(target)], cwd=root, check=True)
target = root / target
h = target / 'src/model/safety.h'
s = h.read_text().replace('    Blow at(vec2 p) const;', '    Blow at_reference(vec2 p) const;\n    Blow at(vec2 p) const;', 1)
h.write_text(s)
p = target / 'src/model/safety.cc'
s = p.read_text()
base = (root / 'bots/variants/oc-fuel-496/src/model/safety.cc').read_text()
ref = base[base.index('Blow Reach::at(vec2 p) const {'):base.index('\nBlow Threat::at(')]
ref = ref.replace('Blow Reach::at(', 'Blow Reach::at_reference(')
ref = ref.replace('    if (memo.stamp == stamp_ && memo.p == p) return memo.blow;\n', '')
ref = ref.replace('bounds_[static_cast<std::size_t>(i)]', 'bound(ws.way[static_cast<std::size_t>(i)])')
ref = ref.replace('    memo = {p, out, stamp_};\n', '')
start = s.index('Blow Reach::at(vec2 p) const {')
end = s.index('\nBlow Threat::at(', start)
body = s[start:end]
body = body.replace('    memo = {p, out, stamp_};', '''    debug_block({
        const Blow expected = at_reference(p);
        if (out.hits != expected.hits || out.stuns != expected.stuns
            || std::bit_cast<std::uint32_t>(out.damage) != std::bit_cast<std::uint32_t>(expected.damage)) {
            printf("REACH-ORACLE-FAIL %d %d\\n", p.x, p.y);
            __builtin_trap();
        }
        static unsigned checks = 0;
        if (++checks == 1 || checks % 256 == 0) printf("REACH-ORACLE %u %u\\n", my_handle(), checks);
    });
    memo = {p, out, stamp_};''')
s = s[:start] + ref + body + s[end:]
s = s.replace('Reach::Window window_square(int range) { return tables.square[static_cast<std::size_t>(range)]; }', '''Reach::Window window_square(int range) {
    const auto out = tables.square[static_cast<std::size_t>(range)];
    debug_block({
        Window expected;
        for (int dy = -range; dy <= range; ++dy)
            for (int dx = -range; dx <= range; ++dx) expected |= win_bit(dx + win_r, dy + win_r);
        if (out.lo != expected.lo || out.hi != expected.hi) {
            printf("SQUARE-ORACLE-FAIL\\n");
            __builtin_trap();
        }
    });
    return out;
}''')
s = s.replace('    if (t.chunked) return t.chunk_window(board.ptr(), centre);', '''    if (t.chunked) {
        const auto out = t.chunk_window(board.ptr(), centre);
        debug_block({
            Window expected;
            for (int dy = -win_r; dy <= win_r; ++dy)
                for (int dx = -win_r; dx <= win_r; ++dx) {
                    const vec2 q{centre.x + dx, centre.y + dy};
                    if (t.inside(q) && test(board, q)) expected |= win_bit(dx + win_r, dy + win_r);
                }
            if (out.lo != expected.lo || out.hi != expected.hi) {
                printf("WARD-ORACLE-FAIL %d %d\\n", centre.x, centre.y);
                __builtin_trap();
            }
            static unsigned checks = 0;
            if (++checks == 1 || checks % 32 == 0) printf("WARD-ORACLE %u %u\\n", my_handle(), checks);
        });
        return out;
    }''')
p.write_text(s)
