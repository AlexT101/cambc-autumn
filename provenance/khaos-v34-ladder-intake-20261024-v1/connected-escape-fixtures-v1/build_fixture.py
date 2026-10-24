from pathlib import Path
import hashlib, json, re
ROOT=Path(__file__).resolve().parents[3]
BOT=ROOT/'bots/variants/willow-v47-connected-escape-work/src'
OUT=Path(__file__).resolve().parent
SOURCES=['pathing.cpp','self_abilities.cpp','bot.cpp']
def body(text, marker):
    start=text.index(marker); brace=text.index('{',start); depth=0
    for i in range(brace,len(text)):
        if text[i]=='{': depth+=1
        elif text[i]=='}':
            depth-=1
            if depth==0:return text[start:i+1],start,i+1
    raise ValueError('unclosed '+marker)
p= (BOT/'pathing.cpp').read_text(); at,a0,a1=body(p,'std::optional<int> Pathing::CampEscape::at(vec2 p) const')
self_src=(BOT/'self_abilities.cpp').read_text(); dash,d0,d1=body(self_src,'bool camp_escape_dash(const World& world, Pathing& pathing, vec2 landing)')
b=(BOT/'bot.cpp').read_text(); sel0=b.index('    struct Endpoint { int steps; float damage; };',b.index('bool connected_camp_dash'));  sel1=b.index('    if (!camp_escape_dash(world, pathing, landing))',sel0); selection=b[sel0:sel1]
# Pin and record exact source bytes plus source line boundaries for all planned production sites.
records=[]
for name in SOURCES:
    s=(BOT/name).read_text(); records.append({'path':str(BOT/name),'sha256':hashlib.sha256((BOT/name).read_bytes()).hexdigest()})
manifest={'schema':'connected-escape-source-fixture-v1','sources':records,'extracted':[{'source':'pathing.cpp','symbol':'Pathing::CampEscape::at','startByte':a0,'endByte':a1,'startLine':p[:a0].count('\n')+1,'endLine':p[:a1].count('\n')+1},{'source':'self_abilities.cpp','symbol':'camp_escape_dash','startByte':d0,'endByte':d1,'startLine':self_src[:d0].count('\n')+1,'endLine':self_src[:d1].count('\n')+1},{'source':'bot.cpp','symbol':'connected_camp_dash endpoint selection loop','startByte':sel0,'endByte':sel1,'startLine':b[:sel0].count('\n')+1,'endLine':b[:sel1].count('\n')+1}] ,'coverage_limit':'The exact at(), camp_escape_dash(), and endpoint-selection excerpts are compiled against declared host mocks. camp_escape cache construction/invalidation, SDK calls, and native gameplay are not executed.'}
(OUT/'SOURCE-PINS.json').write_text(json.dumps(manifest,indent=2)+'\n')
pre=r'''#include <array>
#include <cassert>
#include <cstdlib>
#include <optional>
#include <queue>
#include <vector>
constexpr int unreachable=999;
struct vec2 { int x,y; friend bool operator==(vec2 a,vec2 b){return a.x==b.x&&a.y==b.y;} friend bool operator!=(vec2 a,vec2 b){return !(a==b);} friend vec2 operator+(vec2 a,vec2 b){return {a.x+b.x,a.y+b.y};} };
struct bitboard { bool a[9][9]{}; };
bool in_bounds(vec2 p){return p.x>=0&&p.y>=0&&p.x<9&&p.y<9;}
bool test(const bitboard& b,vec2 p){return in_bounds(p)&&b.a[p.y][p.x];}
struct Labels { int a[9][9]; int at(vec2 p)const{return a[p.y][p.x];} };
int steps_at(const Labels& l,vec2 p){return l.at(p);}
struct Pathing { bitboard lands{}; const bitboard& dash_landings() const{return lands;} struct CampEscape { vec2 origin{-1,-1},ray{}; int steps=unreachable; bool valid=false,exact=false,exhausted=false; bitboard walls{},goals{}; Labels storage{}; Labels* labels=&storage; std::optional<int> at(vec2 p) const;
}; };
using CampEscape = Pathing::CampEscape;
'''
selector_prefix=r'''
#include <algorithm>
#include <cmath>
#include <vector>
struct Field { int at(vec2 p) const{return p.y==3?0:p.x;} };
struct Safety { float damage_bound(vec2 p) const{return (p.x==7)?20.0f:((p.y==3||p.y==5)?5.0f:10.0f);} };
template<class T,int N> struct Unwritten { T a[N]{}; };
std::vector<vec2> candidate_dashes;
template<int N> struct Tiles { std::vector<vec2> v; Tiles(const bitboard&){v=candidate_dashes;} auto begin()const{return v.begin();} auto end()const{return v.end();} };
const vec2 directions[]={{1,0},{-1,0},{0,1},{0,-1},{1,1},{1,-1},{-1,1},{-1,-1}};
int dist(vec2 a,vec2 b){return std::max(std::abs(a.x-b.x),std::abs(a.y-b.y));}
struct Selection { vec2 landing,finish; int steps; float damage; int home; };
bool run_selection(CampEscape& escape,Pathing& pathing,Safety& safety,Field& home,vec2 here,bool walking,vec2 normal,Selection& result){
    const int normal_steps=*escape.at(normal); const float normal_damage=safety.damage_bound(normal);
SELECTION_PLACEHOLDER
    result={landing,finish,best_steps,best_damage,best_home}; return true;
}
'''
selector_prefix=selector_prefix.replace('SELECTION_PLACEHOLDER',selection)
tests=r'''
static void eq(std::optional<int> a,int b){assert(a && *a==b);}
int main(){
  CampEscape ray; ray.valid=ray.exact=true; ray.origin={1,4}; ray.ray={1,0}; ray.steps=4;
  eq(ray.at({1,4}),4); eq(ray.at({3,4}),2); assert(!ray.at({3,5}));
  ray.walls.a[4][3]=true; assert(!ray.at({3,4}));
  CampEscape bfs; bfs.valid=bfs.exact=true; bfs.origin={1,1}; bfs.steps=4;
  for(auto& row:bfs.labels->a) for(int& x:row)x=unreachable;
  // Oracle-derived label field for a detour around wall (3,1), from (1,1) to goal (5,1).
  bfs.walls.a[1][3]=true; int d[9][9]; for(auto& row:d)for(int& x:row)x=-1;
  std::queue<vec2> q; q.push({5,1});d[1][5]=0; const vec2 ds[]={{1,0},{-1,0},{0,1},{0,-1},{1,1},{1,-1},{-1,1},{-1,-1}};
  while(!q.empty()){auto p=q.front();q.pop();for(auto v:ds){auto n=p+v;if(in_bounds(n)&&!test(bfs.walls,n)&&d[n.y][n.x]<0){d[n.y][n.x]=d[p.y][p.x]+1;q.push(n);}}}
  bfs.steps=d[1][1]; for(int y=0;y<9;y++)for(int x=0;x<9;x++)bfs.labels->a[y][x]=d[y][x]<0?unreachable:d[y][x];
  eq(bfs.at({1,1}),4); eq(bfs.at({5,1}),0); assert(!bfs.at({3,1})); assert(!bfs.at({7,7}));
  World world; Pathing path; path.lands.a[2][2]=true;
  dash_ready=-1; assert(!camp_escape_dash(world,path,{2,2}));
  dash_ready=1; wakes=true; assert(!camp_escape_dash(world,path,{2,2})); wakes=false;
  suicidal=true; assert(!camp_escape_dash(world,path,{2,2})); suicidal=false;
  assert(camp_escape_dash(world,path,{2,2})); assert(dash_calls==1);
  CampEscape route; route.valid=route.exact=true; route.origin={4,4}; route.steps=5;
  for(auto& row:route.storage.a)for(int& x:row)x=unreachable;
  route.storage.a[4][4]=5; route.storage.a[4][5]=4; route.storage.a[4][6]=2; route.storage.a[3][6]=2; route.storage.a[5][6]=2; route.storage.a[4][7]=1;
  Pathing sp; Safety safety; Field home; candidate_dashes={{5,4}};
  Selection selected{}; assert(run_selection(route,sp,safety,home,{4,4},true,{4,4},selected)); assert(selected.landing.x==5 && selected.landing.y==4); assert(selected.finish.x==6 && selected.finish.y==3);
  candidate_dashes={{8,4}}; Selection rejected{}; assert(!run_selection(route,sp,safety,home,{4,4},true,{4,4},rejected));
  candidate_dashes={{1,4}}; assert(!run_selection(route,sp,safety,home,{4,4},true,{4,4},rejected));
  candidate_dashes={{5,4}}; assert(!run_selection(route,sp,safety,home,{4,4},true,{6,4},rejected));
  CampEscape ex; ex.valid=ex.exact=ex.exhausted=true; ex.steps=unreachable; eq(ex.at({2,2}),unreachable);
  CampEscape unknown; unknown.valid=true; unknown.exact=false; assert(!unknown.at({2,2}));
  puts("CampEscape::at, camp_escape_dash, and connected_camp_dash endpoint selection source fixtures passed");
}
'''
dash_mocks=r'''
#include <cstdio>
namespace { int dash_ready=0; bool wakes=false, suicidal=false; int dash_calls=0; }
enum class AbilityKind { dash };
struct World {};
struct Landings { int count=0; vec2 tiles[1]{}; };
int ready(const World&,AbilityKind){return dash_ready;}
bool wakes_camp(const World&,vec2){return wakes;}
bool landing_suicidal(const World&,vec2){return suicidal;}
bool dash_to_first(int,Pathing&,const Landings& l){if(l.count!=1)return false;++dash_calls;return true;}
'''
(OUT/'fixture.cpp').write_text(pre+at+'\n'+dash_mocks+'\n'+dash+'\n'+selector_prefix+'\n'+tests)
