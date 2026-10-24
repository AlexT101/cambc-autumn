#include <algorithm>
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
namespace aph {
bool contact_camps_clear(const World& world, vec2 p) {
    const auto& map = world.map();
    for (const int g : map.groups_near(p, map.max_camp_reach)) {
        const auto& group = map.groups[static_cast<std::size_t>(g)];
        if (group.strength <= 0) continue;
        const auto& camp = world.camps[static_cast<std::size_t>(g)];
        if (camp.state == CampState::respawning && camp.respawn_round > world.round + 1) continue;
        if (camp.state == CampState::cleared && camp.state_round > 0
            && camp.state_round + group.respawn > world.round + 1)
            continue;
        // Safety's camp reaches already include the old priority's nearest-target tie winner.
        return false;
    }
    return true;
}
bool recall_contact_priority(const World& world, vec2 p, int fallback, const std::vector<Enemy>& enemies) {
    constexpr int floor = 13;
    int old_rank = 0, new_rank = 0;
    const auto handle = world.me().handle;
    for (const auto& ally : world.allies) {
        if (ally.is_self) continue;
        const bool tie_first = ally.handle < handle;
        old_rank += ally.next_priority > fallback || (ally.next_priority == fallback && tie_first);
        new_rank += ally.next_priority > floor || (ally.next_priority == floor && tie_first);
    }
    if (old_rank == new_rank) return false;
    const auto slot = [](int rank, int others, bool first) {
        return rank < others ? 2 * rank + (first ? 0 : 1) : others + rank;
    };
    const bool first = we_start(world, world.round + 1);
    const int old_slot = slot(old_rank, static_cast<int>(world.enemies.size()), first);
    const int new_slot = slot(new_rank, static_cast<int>(world.enemies.size()), first);
    for (const auto& enemy : enemies) {
        const auto& e = *enemy.belief;
        if (!e.acted || e.pos_round != world.round || e.stats_round != world.round
            || e.priority_round != world.round || e.channel != Channel::none)
            continue;
        int rank = 0;
        for (const auto& other : world.enemies)
            rank += other.next_priority > e.next_priority
                    || (other.next_priority == e.next_priority && other.handle < e.handle);
        const int enemy_slot = slot(rank, static_cast<int>(world.allies.size()), !first);
        if (new_slot >= enemy_slot || old_slot < enemy_slot) continue;
        const int distance = dist(p, e.pos);
        // The later strike allows one prior approach walk; it is not next-activation damage.
        if (strike(e, world.round + 1).hits(distance)
            || strike(e, world.round + 2).hits(std::max(0, distance - 1))) {
            // Start snapshots carry known stuns; action flags after an enemy acted do not.
            bool unstunned = false;
            for (int i = 0; i < world.priority_start_enemies.count; ++i)
                if (world.priority_start_handles[static_cast<std::size_t>(i)] == e.handle) {
                    unstunned = !world.priority_start_enemies.units[static_cast<std::size_t>(i)].stunned;
                    break;
                }
            if (!unstunned) continue;
            return contact_camps_clear(world, p);
        }
    }
    return false;
}
}

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
