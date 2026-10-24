#include <array>
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
std::optional<int> Pathing::CampEscape::at(vec2 p) const {
    if (!valid || !exact || !in_bounds(p) || test(walls, p)) return std::nullopt;
    if (steps == unreachable) return exhausted ? std::optional<int>{unreachable} : std::nullopt;
    if (p == origin) return steps;
    if (steps == 0) return test(goals, p) ? std::optional<int>{0} : std::nullopt;
    if (ray != vec2{}) {
        for (int k = 0; k <= steps; ++k)
            if (p == origin + vec2{ray.x * k, ray.y * k}) return steps - k;
        return std::nullopt;
    }
    const int d = steps_at(*labels, p);
    return d <= steps ? std::optional<int>{d} : std::nullopt;
}

#include <cstdio>
namespace { int dash_ready=0; bool wakes=false, suicidal=false; int dash_calls=0; }
enum class AbilityKind { dash };
struct World {};
struct Landings { int count=0; vec2 tiles[1]{}; };
int ready(const World&,AbilityKind){return dash_ready;}
bool wakes_camp(const World&,vec2){return wakes;}
bool landing_suicidal(const World&,vec2){return suicidal;}
bool dash_to_first(int,Pathing&,const Landings& l){if(l.count!=1)return false;++dash_calls;return true;}

bool camp_escape_dash(const World& world, Pathing& pathing, vec2 landing) {
    const int dash = ready(world, AbilityKind::dash);
    if (dash < 0 || !test(pathing.dash_landings(), landing) || wakes_camp(world, landing)
        || landing_suicidal(world, landing)) return false;
    Landings selected;
    selected.count = 1;
    selected.tiles[0] = landing;
    return dash_to_first(dash, pathing, selected);
}

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
    struct Endpoint { int steps; float damage; };
    Unwritten<Endpoint, 49> points;
    std::array<bool, 49> evaluated{};
    const auto endpoint = [&](vec2 p) -> const Endpoint& {
        const int i = p.x - here.x + 3 + 7 * (p.y - here.y + 3);
        if (!evaluated[i]) {
            evaluated[i] = true;
            const auto steps = escape.at(p);
            points.a[i] = {steps ? *steps : unreachable, 0};
            if (steps && *steps < normal_steps) points.a[i].damage = safety.damage_bound(p);
        }
        return points.a[i];
    };
    vec2 landing{-1, -1}, finish{-1, -1};
    int best_steps = normal_steps, best_home = unreachable;
    float best_damage = normal_damage;
    for (const auto p : Tiles<25>{pathing.dash_landings()}) {
        const auto consider = [&](vec2 q) {
            if (!in_bounds(q)) return;
            const auto& e = endpoint(q);
            if (e.steps == unreachable || e.steps >= normal_steps || e.damage > normal_damage) return;
            const int home_steps = home.at(q);
            if (e.steps < best_steps || (e.steps == best_steps && (e.damage < best_damage
                || (e.damage == best_damage && home_steps < best_home))))
                landing = p, finish = q, best_steps = e.steps, best_damage = e.damage, best_home = home_steps;
        };
        consider(p);
        if (walking) for (const auto d : directions) consider(p + d);
    }
    if (landing.x < 0) return false;

    result={landing,finish,best_steps,best_damage,best_home}; return true;
}


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
