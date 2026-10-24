#!/usr/bin/env python3
"""Compile the exact production comms.cpp protocol slice against small host mocks."""
import hashlib, pathlib, subprocess, sys
ROOT = pathlib.Path(__file__).resolve().parents[4]
PROV = pathlib.Path(__file__).resolve().parent
SOURCE = ROOT / 'bots/variants/willow-sighting-arbitration-4d08241-work/src/comms.cpp'
OUT = PROV / 'production_protocol_fixture.cpp'
BIN = PROV / 'production_protocol_fixture'
source = SOURCE.read_text()
start = source.index('namespace aph::comms {')
end = source.index('void bag(int gems)', start)
production = source[start:end] + '} // namespace aph::comms\n'
header = r'''#include <algorithm>
#include <array>
#include <cassert>
#include <cmath>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <functional>
#include <iostream>
#include <string>
#include <unordered_map>
#include <vector>

struct vec2 { int x=0,y=0; friend bool operator==(vec2 a, vec2 b){return a.x==b.x&&a.y==b.y;} friend bool operator!=(vec2 a, vec2 b){return !(a==b);} };
inline int dist(vec2 a, vec2 b){return std::max(std::abs(a.x-b.x),std::abs(a.y-b.y));}
inline bool in_bounds(vec2 p){return p.x>=0&&p.x<100&&p.y>=0&&p.y<100;}
inline bool test(const std::vector<vec2>& cells, vec2 p){return std::find(cells.begin(),cells.end(),p)!=cells.end();}
namespace cambc { enum class champion_type { prism, willow, marcella, other }; }
enum class Source { none, seen };
enum class Channel { none, tribute, teleport, recall };
enum class Passive { none, splash_attack };
enum class AbilityKind { none, damage, dash, heal };
enum class Targeting { none, unit };
struct Ability { AbilityKind kind=AbilityKind::none; Targeting target=Targeting::none; int range_=0, reach_=0; float multiplier=0; bool enemies=false, excludes_walking=false; int reach()const{return reach_;} int range()const{return range_;} bool hits_enemies()const{return enemies;} };
struct Facts { int attack=1; Passive passive=Passive::none; std::array<Ability,2> abilities{}; int attack_range()const{return attack;} };
struct ChampionBelief {
 int index=0; vec2 pos{}; float health=100,max_health=100; cambc::champion_type type=cambc::champion_type::other; bool is_self=false,alive=true,visible=false;
 Source pos_source=Source::none; int pos_round=-1,stats_round=-1,respawned_round=-1; Channel channel=Channel::none; int gems=0,handle=0;
 Facts fact{}; std::array<bool,2> ready{}; bool uncertain=false;
 const Facts& facts()const{return fact;} bool ability_ready(int s,int)const{return ready[s];} bool cooldowns_uncertain()const{return uncertain;}
};
struct Live { int x=0,y=0; float health=0,max_health=0; };
static std::unordered_map<int,Live> live_records;
inline const Live* visible_record(int h){auto i=live_records.find(h);return i==live_records.end()?nullptr:&i->second;}
inline vec2 my_position();
extern std::uint64_t mock_bits;
namespace cambc {
namespace constants { constexpr int winning_gems=1000; constexpr int capture_time=5; }
namespace error_code { constexpr int ok=0; }
namespace detail { inline int sdk_read_shared_memory(int,std::uint64_t* p,std::size_t){*p=::mock_bits;return 0;} inline int sdk_write_shared_memory(int,const std::uint64_t* p,std::size_t){::mock_bits=*p;return 0;} }
}
namespace params { constexpr int pursuit_steps=3; }
inline void ok(int){}
inline void note_shortcut(const char*){}
#define debug_block(...) ((void)0)
namespace aph {
struct Self { int index=2; bool alive=true; Facts fact{}; const Facts& facts()const{return fact;} };
struct Score { int enemy=0; };
struct CampBelief { int respawn_round=0,told_respawn=-1,state_round=0,state=0; };
struct CampGroup { int respawn=50; };
struct Map { std::vector<CampGroup> groups; };
struct Expected { int index=-1; vec2 pos{-1,-1}; int round=-1; };
struct World {
 int round=0; std::vector<ChampionBelief> allies,enemies; std::vector<CampBelief> camps; Map map_data; std::vector<vec2> visible; Self self{}; Score score{}; Expected expected_sighting{}; int observes=0; bool stale=false;
 Self& me(){return self;} const Self& me()const{return self;} Map& map(){return map_data;} const Map& map()const{return map_data;}
 void throw_if_stale()const{} bool is_stale()const{return stale;} void observe(){++observes;}
 void note_sighting(int i,vec2 p,int r,float h){sightings.push_back({i,p,r,h});}
 void note_capture(int,int){}
 template<class F> void each_respawning(F f){for(int i=0;i<(int)camps.size();++i)if(camps[i].respawn_round>0)if(f(i))break;}
 struct Seen {int i;vec2 p;int r;float h;}; std::vector<Seen> sightings;
};
namespace comms::detail { struct Posts {std::array<int,8> bags{};std::array<int,8> claims{-1,-1,-1,-1,-1,-1,-1,-1};int my_bag=0,mine=-1;}; inline Posts posts; }
namespace comms::support_mailbox {
inline constexpr int prism=0, willow=1; inline constexpr std::uint64_t bits_mask=(std::uint64_t{1}<<31)|(std::uint64_t{3}<<62);
inline int payload(std::uint64_t b){return int((b>>31)&1);} inline std::uint64_t raw_bits(std::uint64_t b){return b&bits_mask;}
inline bool publish_value(int r,int ir,bool in,bool both){return r==ir&&in&&both;}
inline void write(std::uint64_t& b,int r,bool p){b=(b&~bits_mask)|(p?(std::uint64_t{1}<<31):0)|(std::uint64_t(r&3)<<62);}
struct Endpoint{bool present=false,alive=false,is_self=false;int respawned_round=-1;}; struct State{std::uint64_t raw=0;int read_round=-1;std::array<int,2> sent{-1,-1},respawn{-1,-1};std::array<bool,2> positive{},alive{};bool receive(int r,std::uint64_t,const std::array<Endpoint,2>&){read_round=r;return true;}bool valid(int,int)const{return false;}};
}
}
std::uint64_t mock_bits=0;
static vec2 actor_pos{19,56}; inline vec2 my_position(){return actor_pos;}
'''
tests = r'''
namespace aph::comms {
static int field(std::uint64_t b,int s,int w){return int((b>>s)&((std::uint64_t{1}<<w)-1));}
static std::uint64_t encode(int idx,vec2 p,int health_code,int generation,int parity,bool replaced=false){std::uint64_t b=0;b|=std::uint64_t(p.x+1);b|=std::uint64_t(p.y)<<7;b|=std::uint64_t(idx)<<14;b|=std::uint64_t(health_code)<<17;b|=std::uint64_t(parity&1)<<20;b|=std::uint64_t(generation&3)<<59;b|=std::uint64_t(replaced)<<61;return b;}
static void reset_world(World& w){
 state=State{}; support= support_mailbox::State{}; support_intent_round=-1; support_intent_value=false; detail::posts=detail::Posts{};
 mock_bits=0; live_records.clear(); w=World{}; w.round=760; w.map_data.groups.resize(4); w.camps.resize(4); actor_pos={19,56};
 w.allies.resize(3); w.allies[0].type=cambc::champion_type::prism;w.allies[0].index=0;w.allies[0].alive=true;
 w.allies[1].type=cambc::champion_type::willow;w.allies[1].index=1;w.allies[1].alive=true;
 w.allies[2].type=cambc::champion_type::marcella;w.allies[2].index=2;w.allies[2].alive=true;w.allies[2].is_self=true;
 w.self.index=2;w.self.alive=true;w.self.fact.attack=2;
 w.enemies.resize(3);
 for(int i=0;i<3;++i){w.enemies[i].index=i;w.enemies[i].alive=true;w.enemies[i].handle=100+i;w.enemies[i].max_health=1000;w.enemies[i].health=1000;}
 w.enemies[0].pos={80,80};w.enemies[0].visible=false;w.enemies[0].pos_source=Source::none; // incumbent: Heart of Ruin, alive but no current sight
 w.enemies[1].pos={25,56};w.enemies[1].visible=true;w.enemies[1].pos_source=Source::seen;w.enemies[1].pos_round=765;w.enemies[1].stats_round=765;
 // Real Vesper publication reach: basic 3, dash adds 2, then three pursuit steps.
 w.enemies[1].fact.attack=3;w.enemies[1].fact.abilities[0].kind=AbilityKind::dash;w.enemies[1].fact.abilities[0].range_=2;w.enemies[1].ready[0]=true;
 w.enemies[2].pos={90,90};w.enemies[2].visible=false;
 w.visible.push_back({25,56});
 live_records[101]={25,56,800,1000};
}
static void must(bool b,const char* m){if(!b){std::cerr<<"FAIL: "<<m<<"\n";std::exit(2);}}
static void seed_duplicate(World& w){
 // Establish a real previously-read round so production dated() has a baseline.
 std::uint64_t other=0; other|=std::uint64_t{5}<<21; other|=std::uint64_t{1}<<28; other|=std::uint64_t{3}<<32; other|=std::uint64_t{0xaa}<<40; other|=std::uint64_t{9}<<48; other|=std::uint64_t{1}<<56;
 write_bits(0,763); w.round=764; mock_bits=encode(0,{80,80},7,0,0); receive(w);
 // Unrelated records become newly fresh with the same-round duplicate, so the send path must preserve them.
 w.round=765; mock_bits=encode(0,{80,80},7,1,1)|other; receive(w);
 must(state.duplicate,"same payload on consecutive round is marked duplicate");
 must(state.sight_round==765,"publication is dated to current parity round");
}
static std::uint64_t unrelated(std::uint64_t b){const std::uint64_t mask=(std::uint64_t{0x7f}<<21)|(std::uint64_t{7}<<28)|(std::uint64_t{0xff}<<32)|(std::uint64_t{0xff}<<40)|(std::uint64_t{0xff}<<48)|(std::uint64_t{7}<<56);return b&mask;}
static int witness(bool moved,bool refresh){
 World w;reset_world(w);seed_duplicate(w);
 const auto before=mock_bits, other=unrelated(before); const int generation=field(before,59,2);
 send(w,moved,refresh);
 const bool should=(!moved||refresh);
 must((field(mock_bits,14,3)==(should?1:0)),should?"765 witness replaces HoR with locally actionable Vesper":"moved without refresh refuses replacement");
 must(w.observes==((moved&&refresh)?1:0),"fresh observation is requested only for moved qualified replacement");
 must(unrelated(mock_bits)==other,"replacement preserves bag/camp/claim masks");
 must(field(mock_bits,59,2)==generation,"replacement does not mint a second normal generation");
 must(field(mock_bits,61,1)==(should?1:0),"replacement marker records one same-round replacement");
 if(should){
  const auto once=mock_bits;
  // Make a different otherwise-eligible contact available and move away from the incumbent,
  // so only the one-replacement marker can stop the second write.
  actor_pos={10,10};w.enemies[2].pos={40,56};w.enemies[2].visible=true;w.enemies[2].pos_source=Source::seen;w.enemies[2].pos_round=765;w.enemies[2].stats_round=765;w.visible.push_back({40,56});live_records[102]={40,56,800,1000};
  send(w,false,false);must(mock_bits==once,"same-round marker blocks a second otherwise-eligible replacement");
 }
 return 0;
}
static int protected_case(const char* mode){
 World w;reset_world(w);seed_duplicate(w);
 if(std::string(mode)=="tribute")w.enemies[0].channel=Channel::tribute;
 else if(std::string(mode)=="teleport")w.enemies[0].channel=Channel::teleport;
 else if(std::string(mode)=="winning")w.enemies[0].gems=1000;
 else if(std::string(mode)=="notlocal"){w.enemies[1].pos={40,56};w.enemies[1].pos_round=765;w.enemies[1].stats_round=765;w.visible.clear();w.visible.push_back({40,56});live_records[101]={40,56,800,1000};}
 else if(std::string(mode)=="stale")w.enemies[1].stats_round=764;
 const auto before=mock_bits;send(w,false,false);must(mock_bits==before,"protected, nonlocal, or stale candidate leaves contact unchanged");return 0;
}
static int normal_fresh(){
 World w;reset_world(w);const auto contact=payload(1,{25,56},5.0f,7.0f);std::uint64_t bits=contact;
 // Exercise the exact production writer helper and expect/receive path for unchanged contact on healthy ABBA turns.
 for(int round=760;round<764;++round){const auto previous=bits;put_sighting_payload(bits,contact,round,false);state=State{};state.last=previous;state.last_round=round-1;w.round=round;mock_bits=bits;expect(w);must(w.expected_sighting.round==round,"expect dates each healthy alternating publication");receive(w);must(w.sightings.back().r==round,"receive sees unchanged payload as new via generation");}
 must(field(bits,59,2)==0,"generation wraps after four normal publications");return 0;
}
static int normal_write(){
 World w;reset_world(w);write_bits(0,759);
 for(int round=760;round<764;++round){w.round=round;receive(w);send(w,false,false);must(field(mock_bits,59,2)==((round-759)&3),"consecutive actual sender advances generation");must(field(mock_bits,14,3)==1,"normal sender keeps publishing same visible contact");}
 must(field(mock_bits,59,2)==0,"actual sender wraps generation after four publications");return 0;
}
static int missed_gap(){
 World w;reset_world(w);write_bits(0,799);w.round=800;mock_bits=encode(0,{80,80},7,1,0);receive(w);
 // The reader misses rounds 801-803. A changed even-parity publication is dated to earliest fitting round.
 w.round=804;mock_bits=encode(1,{25,56},5,2,0);expect(w);must(w.expected_sighting.round==800,"missed-turn dating chooses earliest parity-compatible round after last read");receive(w);must(w.sightings.back().r==800,"receive uses same earliest-fit dating after gap");
 // An aliased unchanged payload/generation/parity after a gap must not be treated as newly dated.
 w.round=808;mock_bits=encode(1,{25,56},5,2,0);expect(w);must(w.expected_sighting.index==-1,"unchanged aliased current-parity payload is not fresh");receive(w);must(state.sight_round==-1,"missed reader cannot mint freshness from alias");return 0;
}
static int nonconsecutive_send(int marker){
 World w;reset_world(w);write_bits(0,799);w.round=804;mock_bits=encode(0,{80,80},7,2,0,marker);receive(w);
 must(!state.consecutive&&state.sight_round==800,"stale contact after missed turns is nonconsecutive and dated to the earliest fitting round");
 const std::uint64_t mask=((std::uint64_t{1}<<21)-1)|(std::uint64_t{7}<<59);const auto sighting=mock_bits&mask;send(w,false,false);
 must((mock_bits&mask)==sighting,"nonconsecutive send does not refresh current-parity sighting or increment generation");
 const int generation=field(mock_bits,59,2);w.round=805;receive(w);send(w,false,false);
 must(field(mock_bits,59,2)==((generation+1)&3),"later healthy consecutive turn publishes normally and advances generation");
 must(field(mock_bits,14,3)==1,"later normal publication selects current visible Vesper");return 0;
}
}
int main(int argc,char**argv){
 using namespace aph::comms;
 if(argc<2)return 2;
 const std::string mode=argv[1];
 if(mode=="witness")return witness(true,true);
 if(mode=="no-refresh")return witness(true,false);
 if(mode=="not-moved")return witness(false,true);
 if(mode=="normal")return normal_fresh();
 if(mode=="normal-write")return normal_write();
 if(mode=="gap")return missed_gap();
 if(mode=="gap-marker0")return nonconsecutive_send(0);
 if(mode=="gap-marker1")return nonconsecutive_send(1);
 if(mode=="tribute"||mode=="teleport"||mode=="winning"||mode=="notlocal"||mode=="stale")return protected_case(argv[1]);
 return 2;
}
'''
cpp = header + production + tests
OUT.write_text(cpp)
cmd=['clang++','-std=c++20','-O0','-Wall','-Wextra','-Werror=return-type',str(OUT),'-o',str(BIN)]
subprocess.run(cmd,check=True)
for mode in ['witness','no-refresh','not-moved','normal','normal-write','gap','gap-marker0','gap-marker1','tribute','teleport','winning','notlocal','stale']:
 subprocess.run([str(BIN),mode],check=True)
print('PASS: 13 source-bound production protocol scenarios')
print('production slice sha256',hashlib.sha256(production.encode()).hexdigest())
print('production source sha256',hashlib.sha256(source.encode()).hexdigest())
