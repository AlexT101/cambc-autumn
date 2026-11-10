"""Compare all derived metadata with the frozen original header."""
from pathlib import Path
import subprocess, sys, tempfile
root = Path(__file__).resolve().parents[3]
bot = root / (sys.argv[1] if len(sys.argv)>1 else 'bots/variants/oc-fuel-497')
base = (root/'bots/variants/oc-fuel-496/src/champions.h').read_text().replace('namespace aph', 'namespace previous')
stub = (root/'research/fuel-2026-11-10-next/tools/check_output.py').read_text().split("write_text(\'\'\'",1)[1].split("\'\'\')",1)[0]
with tempfile.TemporaryDirectory() as d:
 p = Path(d)
 (p/'cambc.h').write_text(stub)
 (p/'previous.h').write_text(base)
 (p/'check.cc').write_text('''#include "champions.h"
#include "previous.h"
#include <cstdio>
int main() {
 for (int i=0;i<13;++i) {
  const auto& a = previous::champion_table[i];
  const auto& b = aph::champion_table[i];
  for (int k=0;k<7;++k)
   if(a.slot_of(static_cast<previous::AbilityKind>(k))!=b.slot_of(static_cast<aph::AbilityKind>(k))) return 1;
  if(a.cast_reach()!=b.cast_reach() || a.dash_kind()!=b.dash_kind()) return 1;
  for(int s=0;s<2;++s)
   if(a.stun_reach(s)!=b.stun_reach(s)||a.stun_reach_with_walk(s)!=b.stun_reach_with_walk(s)) return 1;
  int act = a.basic_reach();
  for (const auto& ab:a.abilities) {
   if(ab.kind==previous::AbilityKind::damage || ab.kind==previous::AbilityKind::stun) act=std::max(act,ab.reach());
   else if(ab.lands()) act=std::max(act,ab.radius);
  }
  if(act!=b.action_range) return 1;
 }
 std::puts("All derived metadata exact for all 13 bodies");
}
''')
 subprocess.run(['clang++','-std=c++20','-O2','-I',str(p),'-I',str(bot/'src'),str(p/'check.cc'),'-o',str(p/'check')],check=True)
 subprocess.run([str(p/'check')],check=True)
