#!/usr/bin/env python3
"""Extract, compile and exercise the exact candidate helper bodies against thin mocks."""
from __future__ import annotations
import hashlib, json, pathlib, re, subprocess, sys

ROOT = pathlib.Path(__file__).resolve().parents[4]
ART = pathlib.Path(__file__).resolve().parents[1]
SOURCE = ART / 'source-after/src/turn_order.cpp'
OUT_CPP = ART / 'fixtures/production_helper_fixture.generated.cpp'
OUT_JSON = ART / 'fixtures/production_helper_fixture.receipt.json'
binary = OUT_CPP.with_suffix('.bin')

def body(text: str, signature: str) -> str:
    start = text.index(signature)
    brace = text.index('{', start)
    depth = 0
    for i in range(brace, len(text)):
        if text[i] == '{': depth += 1
        elif text[i] == '}':
            depth -= 1
            if depth == 0: return text[start:i+1]
    raise ValueError(f'unclosed function {signature}')

source = SOURCE.read_bytes()
text = source.decode()
camp = body(text, 'bool contact_camps_clear(')
recall = body(text, 'bool recall_contact_priority(')
prefix = r'''#include <algorithm>
#include <cassert>
#include <cstdlib>
#include <iostream>
#include <string>
#include <tuple>
#include <vector>
using std::vector;
struct vec2 { int x=0,y=0; };
int dist(vec2 a, vec2 b) { return std::max(std::abs(a.x-b.x), std::abs(a.y-b.y)); }
enum class Channel { none, recalling };
enum class CampState { unknown, active, respawning, cleared };
struct Group { int strength=0, respawn=0; };
struct Camp { CampState state=CampState::unknown; int respawn_round=0,state_round=0; };
struct Map { int max_camp_reach=5; vector<Group> groups; vector<int> nearby; bool team_a=false; vector<int> groups_near(vec2,int) const { return nearby; } };
struct StartUnit { bool stunned=false; };
struct Starts { int count=0; vector<StartUnit> units; };
struct Belief { bool acted=true; int pos_round=101,stats_round=101,priority_round=101; Channel channel=Channel::none; vec2 pos{}; int handle=0,priority=10,next_priority=10; };
struct Enemy { const Belief* belief=nullptr; int handle=0,next_priority=0; };
struct Ally { bool is_self=false; int handle=0,next_priority=0; };
struct Self { int handle=5; };
struct World { int round=101; Map m; Self self; vector<Ally> allies; vector<Enemy> enemies; vector<Belief> beliefs; vector<Camp> camps; vector<Group> groups; Starts priority_start_enemies; vector<int> priority_start_handles; const Map& map() const { return m; } const Self& me() const { return self; } };
bool we_start(const World& w,int round) { return w.map().team_a == (round % 2 == 1); }
struct Strike { int reach=2; bool hits(int d) const { return d<=reach; } };
Strike strike(const Belief&,int) { return Strike{2}; }

// Independent engine-order oracle: sort each roster, then alternate teams.
int oracle_slot(vector<std::pair<int,int>> a, vector<std::pair<int,int>> b, int team_a_first, int ident) {
 auto cmp=[](auto x,auto y){ return x.second!=y.second ? x.second>y.second : x.first<y.first; };
 std::sort(a.begin(),a.end(),cmp); std::sort(b.begin(),b.end(),cmp);
 size_t i=0,j=0; int cursor=team_a_first?0:1, slot=0;
 while(i<a.size()||j<b.size()) { if(cursor==0&&i<a.size()){if(a[i].first==ident)return slot;++i;++slot;} else if(cursor==1&&j<b.size()){if(b[j].first==ident)return slot;++j;++slot;} cursor^=1; }
 return -1;
}
'''
tests = r'''
using namespace aph;
World positive() {
 World w; w.round=101; w.m.team_a=false; w.self.handle=5;
 w.allies={{false,3,8},{false,4,9},{true,5,7}};
 w.enemies={{nullptr,0,10},{nullptr,1,0},{nullptr,2,-1}};
 w.beliefs={{true,101,101,101,Channel::none,{15,12},0,10,10}};
 w.enemies[0].belief=&w.beliefs[0];
 w.priority_start_enemies={1,{{false}}}; w.priority_start_handles={0};
 w.m.nearby={}; return w;
}
int main() {
 World w=positive();
 auto old_w=oracle_slot({{3,8},{4,9},{5,7}},{{0,10},{1,0},{2,-1}},1,5);
 auto old_e=oracle_slot({{0,10},{1,0},{2,-1}},{{3,8},{4,9},{5,7}},0,0);
 auto new_w=oracle_slot({{3,8},{4,9},{5,13}},{{0,10},{1,0},{2,-1}},1,5);
 assert(old_w==4 && old_e==1 && new_w==0);
 assert(recall_contact_priority(w,{15,15},7,{{&w.beliefs[0],0,10}}));

 // Current live camp evidence rejects; known-clear and future-respawn exemptions pass.
 w.camps={{CampState::active,0,0}}; w.m.groups={{10,3}}; w.m.nearby={0};
 assert(!recall_contact_priority(w,{15,15},7,{{&w.beliefs[0],0,10}}));
 w.camps[0]={CampState::cleared,0,100}; w.m.groups[0].respawn=10;
 assert(recall_contact_priority(w,{15,15},7,{{&w.beliefs[0],0,10}}));
 w.camps[0]={CampState::respawning,105,0}; assert(recall_contact_priority(w,{15,15},7,{{&w.beliefs[0],0,10}}));
 w.camps[0]={CampState::respawning,102,0}; assert(!recall_contact_priority(w,{15,15},7,{{&w.beliefs[0],0,10}}));
 w.camps.clear(); w.groups.clear(); w.m.groups.clear(); w.m.nearby.clear();

 // Freshness, acted, channel and stun admission are exercised in the extracted helper.
 auto attempt=[&](){ return recall_contact_priority(w,{15,15},7,{{&w.beliefs[0],0,10}}); };
 w.beliefs[0].pos_round=100; assert(!attempt()); w.beliefs[0].pos_round=101;
 w.beliefs[0].stats_round=100; assert(!attempt()); w.beliefs[0].stats_round=101;
 w.beliefs[0].priority_round=100; assert(!attempt()); w.beliefs[0].priority_round=101;
 w.beliefs[0].acted=false; assert(!attempt()); w.beliefs[0].acted=true;
 w.beliefs[0].channel=Channel::recalling; assert(!attempt()); w.beliefs[0].channel=Channel::none;
 w.priority_start_enemies.count=0; assert(!attempt()); w.priority_start_enemies.count=1;
 w.priority_start_enemies.units[0].stunned=true; assert(!attempt()); w.priority_start_enemies.units[0].stunned=false;

 // Enemy-first parity cannot cross ahead of the enemy; equal ranks do not nominate.
 w.m.team_a=true; assert(!attempt()); w.m.team_a=false;
 assert(!recall_contact_priority(w,{15,15},13,{{&w.beliefs[0],0,10}}));
 std::cout << "compiled production helper fixture passed; independent old/new slots="
           << old_w << '/' << old_e << '/' << new_w << "\n";
}
'''
OUT_CPP.write_text(prefix + 'namespace aph {\n' + camp + '\n' + recall + '\n}\n' + tests)
receipt = {
 'schema':'contact-priority-production-helper-fixture/v1',
 'candidate_source_sha256':hashlib.sha256(source).hexdigest(),
 'source_file':str(SOURCE),
 'helpers':{
  'contact_camps_clear':hashlib.sha256(camp.encode()).hexdigest(),
  'recall_contact_priority':hashlib.sha256(recall.encode()).hexdigest()},
 'generated_cpp':str(OUT_CPP),
 'mocked_dependencies':['World roster and map groups','Enemy beliefs and priority-start stun snapshot','we_start parity','dist Chebyshev geometry','strike reach2 at requested rounds'],
 'scope':'Exact extracted candidate helper bodies compiled and called; no SDK observation/executor or outer set_turn_order integration.',
 'dispatch_scope':'The live/off-spawn/recalling/no-Wish/fallback-below-13 dispatch is source-reviewed only; not separately reimplemented as a fixture.',
 'fixture_cases':['positive legal-contact rank crossing','active camp rejection','known clear exemption','future respawn exemption','respawn exactly next round rejection','stale position/stats/priority','unacted enemy','enemy channel','missing priority-start snapshot','known stun','opposite parity','unchanged rank']
}
if len(sys.argv)>1 and sys.argv[1]=='--compile':
 subprocess.run(['c++','-std=c++17','-O0','-Wall','-Wextra','-o',str(binary),str(OUT_CPP)],check=True)
 subprocess.run([str(binary)],check=True)
 receipt['compile_and_run']={'status':'passed','compiler':'c++ -std=c++17 -O0 -Wall -Wextra','binary_sha256':hashlib.sha256(binary.read_bytes()).hexdigest()}
else:
 receipt['compile_and_run']={'status':'not-run'}
OUT_JSON.write_text(json.dumps(receipt,indent=2)+'\n')
