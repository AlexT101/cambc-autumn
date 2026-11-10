"""Compare actual old/new Reach recipes, including order, damage, stuns and the basic index."""
from pathlib import Path
import subprocess, sys, tempfile
root = Path(__file__).resolve().parents[3]
base = root/'bots/variants/oc-fuel-496/src'
bot = root/(sys.argv[1] if len(sys.argv)>1 else 'bots/variants/oc-fuel-497')/'src'
def shape(directory):
 header=(directory/'model/safety.h').read_text()
 def struct(name):
  a=header.index('    struct '+name+' {')
  return header[a:header.index('\n    };',a)+7]
 return header[header.index('    enum Tiles'):header.index('    struct Way')]+struct('Way')+struct('Recipe')+struct('Ways')
common = r'''using namespace aph;
struct ChampionBelief {
 cambc::champion_type type;
 float strength,focus,scale;
 const ChampionFacts& facts() const {return aph::facts(type);}
};
float hit_strength(const ChampionBelief& c) {return c.strength*c.scale;}
float hit_focus(const ChampionBelief& c) {return c.focus*c.scale;}
struct Reach {
'''+'@SHAPE@'+r'''
 std::array<Ways,18> ways_by_{};
 Ways* ways_=&ways_by_[0];
 int add(Tiles,int,bool,float,bool,bool);
 void build_ways(const ChampionBelief&,std::array<bool,2>,std::array<bool,2>,bool);
};
'''
code='#include "champions.h"\n#include <bit>\n#include <random>\n#include <cstdio>\n'
for ns,directory in [('before',base),('after',bot)]:
 s=(directory/'model/safety.cc').read_text()
 ret = 'bool' if 'bool Reach::build_ways(' in s else 'void'
 body=s[s.index(ret+' Reach::build_ways('):s.index('\nint Reach::reach()')]
 if ns=='before':body=s[s.index('int Reach::add('):s.index('void Reach::build(')]+body
 code+='namespace '+ns+' {\n'+common.replace('@SHAPE@',shape(directory)).replace('void build_ways(',ret+' build_ways(')+body+'\n}\n'
code+=r'''
int main() {
 std::mt19937 rng(1461310);
 std::uniform_real_distribution<float> stat(0,1000000),scale(0,2);
 unsigned checks=0;
 for(int kit=0;kit<13;++kit)
  for(int k=0;k<18;++k) {
   const bool twice=k>=9;
   const int x=k%9;
   if(!twice&&(x%3==1||x/3==1))continue;
   std::array<bool,2> ready{x%3==2,x/3==2},ready2{x%3!=0,x/3!=0};
   before::Reach a; after::Reach b;
   for(int trial=0;trial<20000;++trial) {
    float s=trial<2?0:stat(rng), f=trial==0||trial==2?0:stat(rng), z=scale(rng);
    a.build_ways({static_cast<cambc::champion_type>(kit),s,f,z},ready,ready2,twice);
    b.build_ways({static_cast<cambc::champion_type>(kit),s,f,z},ready,ready2,twice);
    auto& aa=*a.ways_; auto& bb=*b.ways_;
    if(aa.count!=bb.count||aa.basic!=bb.basic)return 1;
    for(int i=0;i<aa.count;++i) {
     auto& u=aa.way[i];auto& v=bb.way[i];
     if(u.key!=v.key||u.stuns!=v.stuns||u.sight!=v.sight||u.walked!=v.walked||int(u.from)!=int(v.from)||u.range!=v.range||std::bit_cast<unsigned>(u.damage)!=std::bit_cast<unsigned>(v.damage)) {
      std::printf("Mismatch kit%d mask%d trial%d way%d: %.9g vs %.9g\n",kit,k,trial,i,u.damage,v.damage);return 1;
     }
    }
    ++checks;
   }
  }
 std::printf("%u exact Reach recipes, all 13 bodies and every valid readiness combination\n",checks);
}
'''
stub=(root/'research/fuel-2026-11-10-next/tools/check_output.py').read_text().split("write_text(\'\'\'",1)[1].split("\'\'\')",1)[0]
with tempfile.TemporaryDirectory() as d:
 p=Path(d);(p/'cambc.h').write_text(stub);(p/'check.cc').write_text(code)
 subprocess.run(['clang++','-std=c++20','-O2','-ffp-contract=off','-I',str(p),'-I',str(bot),str(p/'check.cc'),'-o',str(p/'check')],check=True)
 subprocess.run([str(p/'check')],check=True)
