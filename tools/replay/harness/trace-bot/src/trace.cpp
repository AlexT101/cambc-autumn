#include "trace.h"
#include <cstdarg>
#include <cstdio>
#include "bot.h"
#include "safety.h"
#include "world.h"

extern "C" {
const char* trace_site = "-";
// Defaults for a build without the tracer harness; rec_data.cpp (trace_data.py) and
// harness_trace.h define the real ones.
__attribute__((weak)) std::int32_t ht_trace_level = 1;
__attribute__((weak)) std::int32_t ht_trace_r0 = 0;
__attribute__((weak)) std::int32_t ht_trace_r1 = 1 << 30;
__attribute__((weak)) const char* ht_game_key() { return "-"; }
__attribute__((weak)) std::int64_t ht_last_fuel() { return -1; }
__attribute__((weak)) std::uint32_t ht_mismatches() { return 0; }
}

namespace aph::trace {
namespace d = cambc::detail;

namespace {

const char* const type_names[] = {"ryth", "vesper", "vendetta", "cassi", "issac", "stellar", "prism",
                                  "marcella", "willow", "ren", "varg", "tavi", "hor"};
const char* type_name(int t) { return t >= 0 && t < 13 ? type_names[t] : "?"; }
const char* channel_name(Channel c) {
    switch (c) {
    case Channel::recall: return "rec";
    case Channel::tribute: return "trib";
    case Channel::teleport: return "tp";
    default: return "-";
    }
}
char source_char(Source s) {
    switch (s) {
    case Source::seen: return 's';
    case Source::comms: return 'c';
    case Source::inferred: return 'i';
    default: return 'n';
    }
}

struct Self {
    bool alive = false;
    vec2 pos{-1, -1};
    float health = 0, max_health = 0, shield = 0, strength = 0, focus = 0;
    std::uint32_t gems = 0, gold = 0;
    std::int32_t state = 0, channel = 0;
    std::int32_t cooldown[2]{};
    bool stunned = false;
};

Self read_self() {
    Self s;
    const std::uint32_t h = my_handle();
    static d::champion_info info;
    if (d::sdk_champion(h, &info) != 0 || info.x < 0) return s;
    s.alive = true;
    s.pos = {info.x, info.y};
    s.health = info.health, s.max_health = info.max_health, s.strength = info.strength, s.focus = info.focus;
    s.state = info.state;
    (void)d::sdk_champion_gems(h, &s.gems);
    (void)d::sdk_champion_gold(h, &s.gold);
    for (std::uint32_t k = 0; k < 2; ++k) (void)d::sdk_champion_cooldown(h, k, &s.cooldown[k]);
    (void)d::sdk_champion_channel_time(h, &s.channel);
    static std::array<d::buff_data, 8> buffs;
    std::uint32_t n = 0;
    if (d::sdk_champion_buff_data(h, buffs.data(), static_cast<std::uint32_t>(buffs.size()), &n) == 0)
        for (std::uint32_t i = 0; i < n && i < buffs.size(); ++i) {
            if (buffs[i].type == static_cast<std::uint32_t>(cambc::buff_types::shield)) s.shield += buffs[i].data.shield.value;
            if (buffs[i].type == static_cast<std::uint32_t>(cambc::buff_types::stun)) s.stunned = true;
        }
    return s;
}

std::uint32_t count_of(const bitboard& b) {
    std::uint32_t n = 0;
    return d::sdk_Bitboard_NumSetBits(b.ptr(), &n) == 0 ? n : 0;
}
bool on(const bitboard& b, vec2 p) {
    std::int32_t v = 0;
    return in_bounds(p) && d::sdk_Bitboard_Test(b.ptr(), p.x, p.y, &v) == 0 && v != 0;
}

struct Fight {
    vec2 p;
    std::uint32_t key;
    char how;
    bool fresh;
    Trade t;
};
struct Value {
    vec2 p;
    Q q;
    float v;
};

struct Turn {
    std::uint32_t round = 0;
    Self start;
    int fights = 0, fresh = 0;
    std::array<Fight, 64> fight;
    int values = 0;
    std::array<Value, 160> value;
};
Turn T;
bool introduced = false;

const Fight* fight_at(vec2 p) {
    for (int i = std::min(T.fights, static_cast<int>(T.fight.size())) - 1; i >= 0; --i)
        if (T.fight[i].p == p && T.fight[i].how == 'f') return &T.fight[i];
    for (int i = std::min(T.fights, static_cast<int>(T.fight.size())) - 1; i >= 0; --i)
        if (T.fight[i].p == p) return &T.fight[i];
    return nullptr;
}
const Value* value_at(Q q, vec2 p) {
    for (int i = std::min(T.values, static_cast<int>(T.value.size())) - 1; i >= 0; --i)
        if (T.value[i].q == q && T.value[i].p == p) return &T.value[i];
    return nullptr;
}

void put_trade(const Trade& t) {
    std::printf("%d:%d:%d:%c:%d:%d", t.lost ? 1 : 0, t.turns_to_kill_us, t.turns_to_kill_them,
                t.falls_known ? (t.self_falls ? '1' : '0') : '?', t.allies, t.enemies);
}
void put_fight(const char* name, vec2 p) {
    std::printf(" %s=", name);
    if (const auto* f = fight_at(p)) {
        if (f->key == Safety::no_fight) std::printf("none");
        else put_trade(f->t);
    } else {
        std::printf("?");
    }
}
void put_value(const char* name, Q q, vec2 p) {
    if (const auto* v = value_at(q, p)) std::printf(" %s=%.0f", name, static_cast<double>(v->v));
}

void put_belief(const World& world, const ChampionBelief& b) {
    const bool enemy = b.side == team::enemy;
    std::printf("TB r=%u c=%u s=%c i=%d h=%u t=%s al=%d", T.round, my_handle(), enemy ? 'e' : 'a', b.index,
                static_cast<unsigned>(b.handle), type_name(static_cast<int>(b.type)), b.alive ? 1 : 0);
    if (!b.alive) {
        std::printf(" rsp=%d-%d\n", b.respawn_earliest, b.respawn_latest);
        return;
    }
    std::printf(" v=%d p=%d,%d pr=%d src=%c hp=%.0f/%.0f", b.visible ? 1 : 0, b.pos.x, b.pos.y, b.pos_round,
                source_char(b.pos_source), static_cast<double>(b.health), static_cast<double>(b.max_health));
    if (b.shield > 0) std::printf(" sh=%.0f", static_cast<double>(b.shield));
    std::printf(" gm=%d", b.gems);
    if (b.channel != Channel::none) std::printf(" ch=%s:%d", channel_name(b.channel), b.channel_end_round);
    if (enemy) {
        std::printf(" rr=%d,%d act=%d", b.ready_round[0], b.ready_round[1], b.acted ? 1 : 0);
        if (b.respawned_round == static_cast<int>(T.round)) std::printf(" rsp=now");
        if (!b.visible) {
            std::printf(" tr=%d", b.tracked ? 1 : 0);
            if (b.tracked) std::printf(" np=%u fx=%d tsf=%d", count_of(b.possible), b.fixed.round, b.turns_since_fixed);
        }
        if (b.pos.x >= 0) std::printf(" bu=%d", on(world.map().bushes, b.pos) ? 1 : 0);
    }
    std::printf("\n");
}

} // namespace

int level() { return ht_trace_level; }

std::uint32_t round() {
    std::uint32_t r = 0;
    (void)d::sdk_bc_round_number(&r);
    return r;
}

bool detail() {
    if (ht_trace_level < 2) return false;
    const auto r = static_cast<std::int32_t>(round());
    return r >= ht_trace_r0 && r <= ht_trace_r1;
}

void ev(const char* kind, const char* fmt, ...) {
    if (ht_trace_level < 1) return;
    std::printf("TE r=%u c=%u k=%s ", round(), my_handle(), kind);
    va_list args;
    va_start(args, fmt);
    std::vprintf(fmt, args);
    va_end(args);
    std::printf("\n");
}

void begin_turn(const World& world, const Memory& memory) {
    T.round = static_cast<std::uint32_t>(world.round);
    T.fights = T.fresh = T.values = 0;
    T.start = read_self();
    if (!introduced) {
        introduced = true;
        std::printf("TV v=%d bot=hyperion-v38-trace game=%s c=%u t=%s team=%c lvl=%d win=%d-%d\n", version, ht_game_key(), my_handle(),
                    type_name(static_cast<int>(world.me().type)), world.map().team_a ? 'a' : 'b', ht_trace_level, ht_trace_r0,
                    ht_trace_r1);
    }
    (void)memory;
    if (ht_trace_level < 1) return;
    for (const auto& e : world.enemies) put_belief(world, e);
    if (detail())
        for (const auto& a : world.allies)
            if (!a.is_self) put_belief(world, a);
}

void end_turn(const World& world, const Memory& memory, char decision, bool completed) {
    const Self& s = T.start;
    const Self e = read_self();
    std::printf("TT r=%u c=%u t=%s a=%d p=%d,%d q=%d,%d hp=%.0f hq=%.0f mh=%.0f", T.round, my_handle(),
                type_name(static_cast<int>(world.me().type)), s.alive ? 1 : 0, s.pos.x, s.pos.y, e.pos.x, e.pos.y,
                static_cast<double>(s.health), static_cast<double>(e.health), static_cast<double>(s.max_health));
    if (s.shield > 0 || e.shield > 0) std::printf(" sh=%.0f,%.0f", static_cast<double>(s.shield), static_cast<double>(e.shield));
    std::printf(" g=%u gq=%u au=%u d=%c dmg=%.0f fg=%d cl=%d", s.gems, e.gems, e.gold, decision, static_cast<double>(memory.damage),
                memory.farm_group, memory.claim);
    if (memory.siege) std::printf(" sg=1");
    if (memory.banking) std::printf(" bk=1");
    if (memory.crew) std::printf(" cr=1");
    if (memory.wait_altar >= 0) std::printf(" wa=%d:%d", memory.wait_altar, memory.wait_since);
    if (s.stunned) std::printf(" st=1");
    const auto states = cambc::champion_state::from_bits_retain(s.state);
    const char* channel = states.contains(cambc::champion_state::recalling)        ? "rec"
                          : states.contains(cambc::champion_state::submitting_gems) ? "trib"
                          : states.contains(cambc::champion_state::teleporting)     ? "tp"
                                                                                     : nullptr;
    if (channel) std::printf(" ch=%s:%d", channel, s.channel);
    const auto ends = cambc::champion_state::from_bits_retain(e.state);
    const char* channel_end = ends.contains(cambc::champion_state::recalling)        ? "rec"
                              : ends.contains(cambc::champion_state::submitting_gems) ? "trib"
                              : ends.contains(cambc::champion_state::teleporting)     ? "tp"
                                                                                       : nullptr;
    if (channel_end) std::printf(" chq=%s:%d", channel_end, e.channel);
    std::printf(" cd=%d,%d cq=%d,%d", s.cooldown[0], s.cooldown[1], e.cooldown[0], e.cooldown[1]);
    if (memory.ward.x >= 0) std::printf(" wd=%d,%d", memory.ward.x, memory.ward.y);
    if (s.alive) std::printf(" bu=%d vis=%u", on(world.map().bushes, s.pos) ? 1 : 0, count_of(world.visible));
    std::printf(" fu=%lld nf=%d/%d", static_cast<long long>(ht_last_fuel()), T.fights, T.fresh);
    if (s.alive) {
        put_fight("fs", s.pos);
        if (e.pos != s.pos && e.alive) put_fight("fe", e.pos);
        put_value("ls", Q::lethal, s.pos);
        if (e.pos != s.pos) put_value("le", Q::lethal, e.pos);
        put_value("cs", Q::camp, s.pos);
        if (e.pos != s.pos) put_value("ce", Q::camp, e.pos);
        if (const auto* v = value_at(Q::threatened, s.pos)) std::printf(" ts=%.0f", static_cast<double>(v->v));
    }
    if (!completed) std::printf(" ok=0");
    if (const auto m = ht_mismatches()) std::printf(" mm=%u", m);
    std::printf("\n");
    if (detail()) {
        for (int i = 0; i < std::min(T.fights, static_cast<int>(T.fight.size())); ++i) {
            const auto& f = T.fight[i];
            std::printf("TF r=%u c=%u k=%c p=%d,%d key=%x new=%d t=", T.round, my_handle(), f.how, f.p.x, f.p.y, f.key, f.fresh ? 1 : 0);
            put_trade(f.t);
            std::printf("\n");
        }
        static const char* const qnames[] = {"lethal", "threat", "camp", "bound", "ceiling", "idle"};
        for (int i = 0; i < std::min(T.values, static_cast<int>(T.value.size())); ++i)
            std::printf("TQ r=%u c=%u q=%s p=%d,%d v=%.1f\n", T.round, my_handle(), qnames[static_cast<int>(T.value[i].q)], T.value[i].p.x,
                        T.value[i].p.y, static_cast<double>(T.value[i].v));
    }
}

void note_value(Q kind, vec2 p, float v) {
    if (value_at(kind, p)) return;
    if (T.values < static_cast<int>(T.value.size())) T.value[static_cast<std::size_t>(T.values)] = {p, kind, v};
    ++T.values;
}

void note_fight(char how, vec2 p, std::uint32_t key, const Trade& t, bool fresh) {
    T.fresh += fresh;
    for (int i = 0; i < std::min(T.fights, static_cast<int>(T.fight.size())); ++i)
        if (T.fight[i].p == p && T.fight[i].how == how && T.fight[i].key == key) {
            T.fight[i].t = t;
            return;
        }
    if (T.fights < static_cast<int>(T.fight.size())) T.fight[static_cast<std::size_t>(T.fights)] = {p, key, how, fresh, t};
    ++T.fights;
}

} // namespace aph::trace
