"""Compile the actual strike functions and compare every range bitwise for all kits and slot masks."""
from pathlib import Path
import subprocess, sys, tempfile
root = Path(__file__).resolve().parents[3]
base = root / 'bots/variants/oc-fuel-496/src'
cand = root / (sys.argv[1] if len(sys.argv) > 1 else 'bots/variants/oc-fuel-497') / 'src'
old = (base/'model/safety.cc').read_text()
old = old[old.index('Strike compute_strike('):old.index('// Called many times a turn')].replace('compute_strike(', 'old_strike(')
new = (cand/'model/safety.cc').read_text()
new = new[new.index('// Movement and ability ranges are static;'):new.index('// Called many times a turn')]
header = (cand/'model/safety.h').read_text()
start = header.index('struct Strike {')
strike = header[start:header.index('\n};',start)+3]
# Use the tiny metadata-only stub already used for the output-coefficient check.
stub = (root/'research/fuel-2026-11-10-next/tools/check_output.py').read_text().split("write_text('''",1)[1].split("''')",1)[0]
with tempfile.TemporaryDirectory() as d:
 p = Path(d)
 (p/'cambc.h').write_text(stub)
 (p/'check.cc').write_text('#include "champions.h"\n#include <algorithm>\n#include <bit>\n#include <cstdio>\n#include <random>\nnamespace aph {\nstruct Blow {float damage; bool hits,stuns;};\n'+strike+'\n'+old+'\n'+new+'\n}\n'+r'''
int main() {
    std::mt19937 random(20261110);
    std::uniform_real_distribution<float> stat(0, 1000000);
    unsigned checks = 0;
    for (const auto& f : aph::champion_table)
        for (unsigned slots = 0; slots < 4; ++slots)
            for (bool moved : {false, true})
                for (int i = 0; i < 20000; ++i) {
                    const float strength = i < 2 ? 0 : stat(random), focus = i == 0 || i == 2 ? 0 : stat(random);
                    const auto a = aph::old_strike(f, strength, focus, slots, moved);
                    const auto b = aph::compute_strike(f, strength, focus, slots, moved);
                    if (a.reach != b.reach || a.stuns != b.stuns) return 1;
                    for (int d = 0; d <= aph::Strike::max_reach; ++d)
                        if (std::bit_cast<unsigned>(a.damage[d]) != std::bit_cast<unsigned>(b.damage[d])) {
                            std::printf("mismatch kit %td slots %u moved %d distance %d strength %.9g focus %.9g: %.9g != %.9g\n",
                                        &f-aph::champion_table.data(), slots, moved, d, strength, focus, a.damage[d], b.damage[d]);
                            return 1;
                        }
                    ++checks;
                }
    std::printf("%u bit-identical strikes, all 13 bodies, four slot masks, both movement modes\n", checks);
}
''')
 subprocess.run(['clang++','-std=c++20','-O2','-ffp-contract=off','-I',str(p),'-I',str(cand),str(p/'check.cc'),'-o',str(p/'check')],check=True)
 subprocess.run([str(p/'check')],check=True)
 source = (p/'check.cc').read_text()
 (p/'check.cc').write_text('#define SIMDE_ENABLE_NATIVE_ALIASES\n#define __wasm_simd128__ 1\n#include <simde/wasm/simd128.h>\n'+source)
 subprocess.run(['clang++','-std=c++20','-O2','-ffp-contract=off','-I',str(p),'-I',str(cand),'-I',str(root/'tools/fastengine/runner/vendor/simde/include'),str(p/'check.cc'),'-o',str(p/'check')],check=True)
 subprocess.run([str(p/'check')],check=True)
