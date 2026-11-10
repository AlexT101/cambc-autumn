"""Exercise the actual SIMD rank kernel on all team sizes, tied and extreme int32 priorities."""
from pathlib import Path
import subprocess, tempfile, sys
root = Path(__file__).resolve().parents[3]
bot = root / (sys.argv[1] if len(sys.argv) > 1 else 'bots/variants/oc-fuel-497')
s = (bot/'src/model/world.cc').read_text()
s = s[s.index('// Compare every cyclic offset'):s.index('\n} // namespace\n\nvoid World::rank_turns()')]
with tempfile.TemporaryDirectory() as d:
 p = Path(d)
 (p/'check.cc').write_text('#define SIMDE_ENABLE_NATIVE_ALIASES\n#include <simde/wasm/simd128.h>\n#include <array>\n#include <bit>\n#include <algorithm>\n#include <limits>\n#include <random>\n#include <cstdio>\n'+s+r'''
int main() {
 std::mt19937 random(1461310);
 unsigned checks = 0;
 for (int n=0; n<=16; ++n)
  for (int trial=0; trial<100000; ++trial) {
   std::array<std::int32_t,16> p;
   for (auto& x:p) {
    const unsigned v=random();
    x=trial%3==0 ? static_cast<std::int32_t>(v%5)-2 : trial%3==1 ? (v%2 ? INT32_MIN : INT32_MAX) : static_cast<std::int32_t>(v);
   }
   bool ok=true;
   int writes=0;
   rank_by(p.data(),n,[&](int i,int rank) {
    int expected=0;
    for(int j=0;j<n;++j) expected+=p[j]>p[i]||(p[j]==p[i]&&j<i);
    ok &= rank==expected;
    ++writes;
   });
   if(!ok||writes!=n) return 1;
   ++checks;
  }
 std::printf("%u exact ranking checks, sizes 0..16 including ties and int32 extremes\n",checks);
}
''')
 subprocess.run(['clang++','-std=c++20','-O2','-I',str(root/'tools/fastengine/runner/vendor/simde/include'),str(p/'check.cc'),'-o',str(p/'check')],check=True)
 subprocess.run([str(p/'check')],check=True)
