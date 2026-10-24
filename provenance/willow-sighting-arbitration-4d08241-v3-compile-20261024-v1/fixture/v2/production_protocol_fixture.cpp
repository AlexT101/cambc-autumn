#include <algorithm>
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
namespace aph::comms {

namespace {

// Layout, least significant bit first:
//   [0, 7)    sighting x + 1, 0 = none
//   [7, 14)   sighting y
//   [14, 17)  enemy index
//   [17, 20)  its health in sevenths of its max, floored; 7 = full
//   [20, 21)  round parity
//   [21, 28)  bag in fours, rounded up
//   [28, 31)  carrying ally's index
//   [32, 40)  captured group + 1, 0 = none
//   [40, 48)  its respawn round mod 256
//   [48, 56)  claimed group + 1, 0 = none
//   [56, 59)  claiming ally's index
//   [59, 61)  normal sighting generation
//   [61, 62)  this round's single replacement used
//   [31, 32)  support payload; even rounds Prism requests, odd rounds Willow offers
//   [62, 64)  support writer round modulo four
// Generation distinguishes unchanged normal publications; the marker bounds same-round replacement.
// A claim or a bag is a standing state, rewritten only when it changes or as a reminder.
struct BitField {
    int shift, width;
    constexpr std::uint64_t mask() const { return ((std::uint64_t{1} << width) - 1) << shift; }
    constexpr int get(std::uint64_t bits) const { return static_cast<int>((bits & mask()) >> shift); }
    constexpr void set(std::uint64_t& bits, int value) const {
        bits = (bits & ~mask()) | ((static_cast<std::uint64_t>(value) << shift) & mask());
    }
};

constexpr BitField sight_x{0, 7}, sight_y{7, 7}, sight_index{14, 3}, sight_health{17, 3}, sight_parity{20, 1};
constexpr BitField bag_fours{21, 7}, bag_body{28, 3};
constexpr BitField camp_group{32, 8}, camp_respawn{40, 8};
constexpr BitField claim_group{48, 8}, claim_body{56, 3};
constexpr BitField sight_generation{59, 2}, sight_replaced{61, 1};
constexpr int max_group = (1 << 8) - 1; // camp_group and claim_group hold the group + 1
constexpr std::uint64_t sight_payload = sight_x.mask() | sight_y.mask() | sight_index.mask() | sight_health.mask();
constexpr std::uint64_t sighting_bits = sight_payload | sight_parity.mask() | sight_generation.mask() | sight_replaced.mask();
constexpr std::uint64_t bag_bits = bag_fours.mask() | bag_body.mask();
constexpr std::uint64_t camp_bits = camp_group.mask() | camp_respawn.mask();
constexpr std::uint64_t claim_bits = claim_group.mask() | claim_body.mask();
constexpr std::uint64_t support_bits = support_mailbox::bits_mask;
static_assert((sighting_bits & bag_bits) == 0 && ((sighting_bits | bag_bits) & camp_bits) == 0
              && ((sighting_bits | bag_bits | camp_bits) & claim_bits) == 0);
static_assert(((sighting_bits | bag_bits | camp_bits | claim_bits) & support_bits) == 0);

int health_code(float health, float max_health) {
    const float fraction = max_health > 0 ? health / max_health : 1.0f;
    return fraction >= 1.0f ? 7 : std::clamp(static_cast<int>(fraction * 7.0f), 0, 6);
}

std::uint64_t payload(int enemy, vec2 pos, float health, float max_health) {
    std::uint64_t bits = 0;
    sight_x.set(bits, pos.x + 1);
    sight_y.set(bits, pos.y);
    sight_index.set(bits, enemy);
    sight_health.set(bits, health_code(health, max_health));
    return bits;
}

std::uint64_t payload(const ChampionBelief& e) { return payload(e.index, e.pos, e.health, e.max_health); }

void put_sighting_payload(std::uint64_t& bits, std::uint64_t contact, int round, bool replacement) {
    bits = (bits & ~sight_payload) | contact;
    sight_parity.set(bits, round & 1);
    if (!replacement) sight_generation.set(bits, sight_generation.get(bits) + 1);
    sight_replaced.set(bits, replacement);
}

void put_sighting(std::uint64_t& bits, const ChampionBelief& e, int round) {
    put_sighting_payload(bits, payload(e), round, false);
}

struct State {
    std::uint64_t last = 0; // the bits as we left them at the end of our previous turn
    std::uint64_t now = 0;  // this turn's, as receive() read them and send() leaves them
    int now_round = -1;
    int last_round = -1;
    std::uint64_t fresh = 0; // records written since then
    int posted_bag = -1;
    int posted = -1;
    std::uint64_t received_payload = 0;
    int received_round = -1, sight_round = -1;
    bool duplicate = false, consecutive = false;
};
State state;

support_mailbox::State support;
int support_intent_round = -1;
bool support_intent_value = false;

// Prism and Willow, found once: the picks are fixed after the draft.
std::array<const ChampionBelief*, 2> endpoints(const World& world) {
    static std::array<int, 2> index{-2, -2};
    if (index[0] == -2) {
        index = {-1, -1};
        for (int i = 0; i < static_cast<int>(world.allies.size()); ++i) {
            if (world.allies[i].type == cambc::champion_type::prism) index[0] = i;
            if (world.allies[i].type == cambc::champion_type::willow) index[1] = i;
        }
    }
    std::array<const ChampionBelief*, 2> pair{};
    for (int i = 0; i < 2; ++i)
        if (index[i] >= 0) pair[i] = &world.allies[index[i]];
    return pair;
}

// Only the pair reads the mailbox.
void receive_support(const World& world, std::uint64_t bits) {
    const auto pair = endpoints(world);
    if (!pair[0] || !pair[1] || (!pair[0]->is_self && !pair[1]->is_self)) return;
    std::array<support_mailbox::Endpoint, 2> endpoint{};
    for (int i = 0; i < 2; ++i)
        if (pair[i]) endpoint[i] = {true, pair[i]->alive, pair[i]->is_self, pair[i]->respawned_round};
    support.receive(world.round, bits, endpoint);
}

// Raw reads and writes: the SDK's checked ones cost several times more.
std::uint64_t read_bits() {
    std::uint64_t bits = 0;
    ok(cambc::detail::sdk_read_shared_memory(0, &bits, sizeof bits));
    return bits;
}

void write_bits(std::uint64_t bits, int round) {
    ok(cambc::detail::sdk_write_shared_memory(0, &bits, sizeof bits));
    state.last = state.now = bits;
    state.last_round = round;
}

std::uint64_t changes(std::uint64_t bits) {
    std::uint64_t fresh = 0;
    for (const auto mask : {sighting_bits, bag_bits, camp_bits, claim_bits})
        if ((bits ^ state.last) & mask) fresh |= mask;
    return fresh;
}

// A changed record was written after our previous turn, normally last round or this one; after
// missed turns (out of fuel), take the earliest round that fits.
int dated(int parity) {
    const int after = std::max(state.last_round, 0);
    return (after & 1) == parity ? after : after + 1;
}

// A publication priority only: known strike geometry, without pathfinding or a fight forecast.
int strike_reach(const ChampionBelief& e, int round) {
    const auto& f = e.facts();
    const int basic = f.attack_range() + (f.passive == Passive::splash_attack ? 1 : 0);
    int reach = basic;
    for (int slot = 0; slot < 2; ++slot) {
        const auto& ability = f.abilities[slot];
        if (!e.ability_ready(slot, round) && !e.cooldowns_uncertain()) continue;
        if (ability.hits_enemies()) reach = std::max(reach, ability.reach());
        if (ability.kind == AbilityKind::dash) reach = std::max(reach, basic + ability.range());
    }
    return reach;
}

bool local_contact(const World& world, const ChampionBelief& e, vec2 pos) {
    const int reach = strike_reach(e, world.round) + params::pursuit_steps;
    if (dist(pos, my_position()) <= reach) return true;
    for (const auto& ally : world.allies)
        if (!ally.is_self && ally.alive && ally.visible && ally.pos_source == Source::seen
            && ally.pos_round == world.round && ally.stats_round == world.round && dist(pos, ally.pos) <= reach
            && test(world.visible, ally.pos)) return true;
    return false;
}

bool current_contact(const World& world, const ChampionBelief& e) {
    return e.alive && e.visible && e.pos_source == Source::seen && e.pos_round == world.round
           && e.stats_round == world.round && in_bounds(e.pos);
}

int replacement_candidate(const World& world, std::uint64_t bits) {
    if (state.sight_round != world.round || sight_replaced.get(bits) || !world.me().alive || !in_bounds(my_position())) return -1;
    const int incumbent = sight_index.get(bits), n = static_cast<int>(world.enemies.size());
    const vec2 pos{sight_x.get(bits) - 1, sight_y.get(bits)};
    if (incumbent >= n || !in_bounds(pos)) return -1;
    const auto& old = world.enemies[incumbent];
    // Direct confirmation improves this enemy's report without displacing its identity.
    if (current_contact(world, old) && payload(old) != (bits & sight_payload)) return incumbent;
    if (!state.duplicate || !old.alive || old.channel == Channel::tribute || old.channel == Channel::teleport
        || old.gems + world.score.enemy >= static_cast<int>(cambc::constants::winning_gems)
        || local_contact(world, old, pos)) return -1;
    for (int k = 1; k < n; ++k) {
        const int i = (incumbent + k) % n;
        const auto& candidate = world.enemies[i];
        if (current_contact(world, candidate) && local_contact(world, candidate, candidate.pos)) return i;
    }
    return -1;
}

} // namespace

[[gnu::flatten]] void expect(World& world) {
    world.expected_sighting = {};
    const auto bits = read_bits();
    if ((changes(bits) & sighting_bits) && sight_x.get(bits) != 0)
        world.expected_sighting = {sight_index.get(bits), {sight_x.get(bits) - 1, sight_y.get(bits)}, dated(sight_parity.get(bits))};
}

[[gnu::flatten]] void receive(World& world) {
    world.throw_if_stale();
    const auto bits = state.now = read_bits();
    const int round = state.now_round = world.round;
    receive_support(world, bits);
    state.fresh = changes(bits);
    state.consecutive = state.last_round == round - 1;
    state.sight_round = (state.fresh & sighting_bits) && sight_x.get(bits) != 0 ? dated(sight_parity.get(bits)) : -1;
    state.duplicate = state.sight_round == round && state.received_round == round - 1
                      && state.received_payload == (bits & sight_payload);
    state.received_payload = bits & sight_payload;
    state.received_round = round;
    if ((state.fresh & sighting_bits) && sight_x.get(bits) != 0) {
        const vec2 pos{sight_x.get(bits) - 1, sight_y.get(bits)};
        const int code = sight_health.get(bits);
        const float health = code == 7 ? 1.0f : (static_cast<float>(code) + 0.5f) / 7.0f;
        world.note_sighting(sight_index.get(bits), pos, dated(sight_parity.get(bits)), health);
    }
    if ((state.fresh & bag_bits) && bag_body.get(bits) != world.me().index) detail::posts.bags[bag_body.get(bits)] = 4 * bag_fours.get(bits);
    if ((state.fresh & claim_bits) && claim_body.get(bits) != world.me().index)
        detail::posts.claims[claim_body.get(bits)] = claim_group.get(bits) - 1;
    if ((state.fresh & camp_bits) && camp_group.get(bits) != 0) {
        const int after = std::max(state.last_round, 0);
        const int respawn = after + ((camp_respawn.get(bits) - after) & 255);
        world.note_capture(camp_group.get(bits) - 1, respawn);
    }
    state.last = bits;
    state.last_round = round;
}

// No teammate acts during our turn: the bits are still those receive() read, if it read them this
// round. Older bits would overwrite what teammates wrote since.
void send(World& world, bool moved, bool refresh) {
    if (state.now_round != world.round) return;
    auto bits = state.now;
    const int round = world.round;
    // A missed reader cannot mint another normal generation from an aliased current-parity record.
    const bool sighted = sight_x.get(bits) != 0 && sight_parity.get(bits) == (round & 1)
                         && ((state.fresh & sighting_bits) || !state.consecutive);
    // A capture someone posted since our last turn stays up for the rest of the team.
    const bool camp_free = !(state.fresh & camp_bits);
    bool dirty = false;

    // Before anything is marked posted: an observe that runs out of fuel resumes a round late,
    // when these bits would overwrite what teammates wrote since.
    int replacement = sighted ? replacement_candidate(world, bits) : -1;
    std::uint64_t replacement_payload = 0;
    if (replacement >= 0 && moved) {
        if (!refresh) replacement = -1;
        else {
            world.observe();
            if (world.is_stale()) return;
            replacement = replacement_candidate(world, bits);
        }
    }
    if (replacement >= 0) {
        const auto& candidate = world.enemies[replacement];
        // Our attacks can change a contact even when an unmoved sender needed no observe().
        const auto* live = visible_record(candidate.handle);
        if (!live || !(live->health > 0) || !in_bounds({live->x, live->y})) replacement = -1;
        else {
            const vec2 pos{live->x, live->y};
            replacement_payload = payload(candidate.index, pos, live->health, live->max_health);
            if (candidate.index == sight_index.get(bits)) {
                if (replacement_payload == (bits & sight_payload)) replacement = -1;
            } else if (!local_contact(world, candidate, pos)) replacement = -1;
        }
        if (world.is_stale()) return;
    }
    if (!sighted) {
        if (refresh) world.observe();
        else if (moved) note_shortcut("comms-stale-vision");
        if (world.is_stale()) return;
    }

    if (camp_free) {
        const auto& groups = world.map().groups;
        world.each_respawning([&](int g) {
            if (g >= max_group) return true;
            auto& c = world.camps[g];
            if (c.respawn_round <= round || c.told_respawn == c.respawn_round) return false;
            // Seen respawning, not inferred from a hold out of sight.
            if (c.state_round + groups[g].respawn < c.respawn_round) return false;
            camp_group.set(bits, g + 1);
            camp_respawn.set(bits, c.respawn_round & 255);
            c.told_respawn = c.respawn_round;
            dirty = true;
            return true;
        });
    }

    // A claim not yet read at our previous turn may not have reached every teammate: ours waits.
    // Turn order changes every round, so a teammate can miss a claim overwritten before its next
    // turn: each in turn re-posts its standing claim into a free slot.
    const int me = world.me().index;
    const bool claim_fresh = (state.fresh & claim_bits) && claim_body.get(bits) != me;
    const int team = static_cast<int>(world.allies.size());
    const bool reminder = round % team == me
                          && (claim_body.get(bits) != me || claim_group.get(bits) != detail::posts.mine + 1);
    if (!claim_fresh && (detail::posts.mine != state.posted || reminder)) {
        claim_group.set(bits, detail::posts.mine + 1);
        claim_body.set(bits, me);
        state.posted = detail::posts.mine;
        dirty = true;
    }

    // Bags change at captures, kills, deaths and tributes; the same rules as claims, one turn later
    // in the reminder cycle.
    const bool bag_fresh = (state.fresh & bag_bits) && bag_body.get(bits) != me;
    const int fours = std::min(127, (detail::posts.my_bag + 3) / 4);
    const bool bag_reminder = (round + 1) % team == me && (bag_body.get(bits) != me || bag_fours.get(bits) != fours);
    if (!bag_fresh && (fours != state.posted_bag || bag_reminder)) {
        bag_fours.set(bits, fours);
        bag_body.set(bits, me);
        state.posted_bag = fours;
        dirty = true;
    }

    if (replacement >= 0) {
        put_sighting_payload(bits, replacement_payload, round, true);
        dirty = true;
        debug_block({ std::printf("CSIGHT %d replaced %d duplicate %d\n", round, replacement, static_cast<int>(state.duplicate)); });
    } else if (!sighted) {
        const int n = static_cast<int>(world.enemies.size());
        const int start = sight_x.get(bits) != 0 ? sight_index.get(bits) + 1 : 0;
        for (int k = 0; k < n; ++k) {
            const auto& e = world.enemies[(start + k) % n];
            if (!e.visible) continue;
            put_sighting(bits, e, round);
            dirty = true;
            break;
        }
    }
    const auto pair = endpoints(world);
    const int writer = round & 1;
    if (pair[0] && pair[1] && pair[writer]->is_self) {
        const bool positive = support_mailbox::publish_value(round, support_intent_round, support_intent_value,
                                                             pair[0]->alive && pair[1]->alive);
        support_mailbox::write(bits, round, positive);
        dirty = true;
    }
    world.throw_if_stale();
    if (dirty) {
        write_bits(bits, round);
        support.raw = support_mailbox::raw_bits(bits);
    }
}

} // namespace aph::comms

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
