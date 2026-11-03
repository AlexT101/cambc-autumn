"""Profiling copy for the Safety fuel study (safety-fuel.md): the fuel census (--fine) plus Safety scopes and
counters, summed over every turn and printed as cumulative "CSUM" lines, so a whole game's fuel by component fits
in the 1 MiB stdout cap.

    python3 research/turn-order-2026-11-02/scripts/sfuel_instrument.py bots/variants/ast-safety-prof-pwc/src

Copy a bot without .cambc/ first (./copybot). Debug-only: never for a real bot. Patterns that no longer match
are skipped with a warning (the copies differ slightly), so check the warnings.
"""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SRC = Path(sys.argv[1])
subprocess.run(["cp", str(ROOT / "tools/fuel/census/census.h"), str(SRC)], check=True)
subprocess.run([sys.executable, str(ROOT / "tools/fuel/census/instrument.py"), str(SRC), "--fine", "--lenient"], check=True)


def sub(name, pairs, need=True):
    p = SRC / name
    s = p.read_text()
    for a, b in pairs:
        if s.count(a) != 1:
            print(f"SKIP {name}: {a.splitlines()[0][:90]} ({s.count(a)})", file=sys.stderr)
            assert not need
            continue
        s = s.replace(a, b)
    p.write_text(s)


def scope_fn(name, prefix, label):
    p = SRC / name
    lines = p.read_text().split("\n")
    hits = [i for i, l in enumerate(lines) if l.startswith(prefix) and not l.rstrip().endswith(";")]
    if len(hits) != 1:
        print(f"SKIP scope {label}: {len(hits)} hits", file=sys.stderr)
        return
    i = hits[0]
    j = next(k for k in range(i, i + 4) if lines[k].rstrip().endswith("{"))
    lines.insert(j + 1, f'    CENSUS("{label}");')
    p.write_text("\n".join(lines))


sub("census.h", [("inline constexpr int max_labels = 96, max_depth = 48;", "inline constexpr int max_labels = 192, max_depth = 48;")])
# Cumulative sums: every turn, and turns spending >= 85k ("heavy"), printed every 100 rounds as deltas.
sub("census.h", [
    ("inline constexpr std::uint64_t print_floor = 70000;", "inline constexpr std::uint64_t print_floor = ~0ull;"),
    ("struct State {", """struct Sum {
    const char* labels[max_labels]{};
    std::uint64_t incl[max_labels]{}, self[max_labels]{}, heavy[max_labels]{};
    std::uint64_t calls[max_labels]{};
    int n = 0;
    std::uint64_t turns = 0, spent = 0, heavy_turns = 0, heavy_spent = 0, over100 = 0, near = 0, near_spent = 0;
    std::uint32_t printed_block = 0;
};

inline Sum& sum() {
    static Sum s;
    return s;
}

inline int sum_slot(const char* label) {
    auto& s = sum();
    for (int i = 0; i < s.n; ++i)
        if (s.labels[i] == label || std::strcmp(s.labels[i], label) == 0) return i;
    if (s.n >= max_labels) return max_labels - 1;
    s.labels[s.n] = label;
    return s.n++;
}

struct State {"""),
    ("""    s.on = false;
    if (!s.ran_out && !s.late && spent < print_floor) return;""", """    s.on = false;
    {
        auto& m = sum();
        const bool heavy = spent >= 85000;
        ++m.turns, m.spent += spent;
        m.heavy_turns += heavy, m.heavy_spent += heavy ? spent : 0, m.over100 += spent > 100000;
        m.near += s.near_enemies > 0, m.near_spent += s.near_enemies > 0 ? spent : 0;
        for (int i = 0; i < s.n; ++i) {
            const int j = sum_slot(s.labels[i]);
            m.incl[j] += s.incl[i], m.self[j] += s.self[i], m.calls[j] += static_cast<std::uint64_t>(s.calls[i]);
            if (heavy) m.heavy[j] += s.incl[i];
        }
        if (const std::uint32_t block = s.round / 100; block != m.printed_block) {
            m.printed_block = block;
            std::printf("CSUM %u %u t%d turns %llu spent %llu heavy %llu hspent %llu over100 %llu near %llu nspent %llu |", s.round,
                        static_cast<unsigned>(static_cast<cambc::handle_champion_t>(cambc::self())), s.type,
                        (unsigned long long)m.turns, (unsigned long long)m.spent, (unsigned long long)m.heavy_turns,
                        (unsigned long long)m.heavy_spent, (unsigned long long)m.over100, (unsigned long long)m.near,
                        (unsigned long long)m.near_spent);
            for (int i = 0; i < m.n; ++i)
                if (m.calls[i])
                    std::printf(" %s=%llu:%llu:%llu:%llu", m.labels[i], (unsigned long long)m.incl[i], (unsigned long long)m.self[i],
                                (unsigned long long)m.calls[i], (unsigned long long)m.heavy[i]);
            std::printf("\\n");
            const char* keep[max_labels];
            const int n = m.n;
            for (int i = 0; i < n; ++i) keep[i] = m.labels[i];
            m = Sum{};
            m.printed_block = block;
            for (int i = 0; i < n; ++i) m.labels[i] = keep[i];
            m.n = n;
        }
    }
    if (!s.ran_out && !s.late && spent < print_floor) return;"""),
    ("""struct Scope {""", """// A counter: one call of `label`, no fuel.
inline void count(const char* label, int n = 1) {
    auto& s = st();
    if (!s.on) return;
    s.calls[slot(label)] += n;
}

struct Scope {"""),
])
sub("census.h", [("#define CEN_CAT2(a, b) a##b", "#define CEN_COUNT(label) debug_block({ ::aph::census::count(label); })\n#define CEN_CAT2(a, b) a##b")])

# Branch scopes the census patterns missed.
sub("bot.cc", [
    ("""    if (holding) {
        hold_capture(world, memory, attacked);
        return;
    }""", """    if (holding) {
        CENSUS("hold_capture");
        hold_capture(world, memory, attacked);
        return;
    }"""),
    ("""    if (my_can_move() || my_can_cast()) guard_work(world, pathing, safety, memory.damage);""",
     """    if (my_can_move() || my_can_cast()) {
        CENSUS("guard_work");
        guard_work(world, pathing, safety, memory.damage);
    }"""),
    ("""    if (chase(world, pathing, safety)) return;
    strike_guard_known""", """    {
        CENSUS("chase");
        if (chase(world, pathing, safety)) return;
    }
    strike_guard_known"""),
], need=False)

for name, prefix, label in [
    ("combat/guard.cc", "const bitboard* step_guard(const World& world, Safety& safety, vec2 here, int radius) {", "g.step_guard"),
    ("combat/guard.cc", "unsigned keep_out(", "g.keep_out"),
    ("combat/guard.cc", "const bitboard* work_guard(", "g.work_guard"),
    ("combat/guard.cc", "WorkAround work_around(", "g.work_around"),
    ("combat/fight.cc", "bool outmatched(const World& world, Safety& safety, vec2 p, int rounds) {", "wh.outmatched"),
    ("model/safety.cc", "[[gnu::noinline]] void Safety::build_reach(", "s.reach"),
    ("model/safety.cc", "Trade Safety::new_fight(", "s.new_fight"),
    ("model/safety.cc", "Trade Safety::chase_trade(", "s.chase_trade"),
    ("model/safety.cc", "bool Safety::threatened_now(", "s.threatened"),
    ("model/safety.cc", "const bitboard& Safety::enemy_area() {", "s.enemy_area"),
    ("model/safety.cc", "float Safety::damage_bound(", "s.damage_bound"),
    ("model/safety.cc", "float Safety::damage_ceiling(", "s.damage_ceiling"),
    ("model/safety.cc", "int Safety::turns_to_kill_idle(", "s.kill_idle"),
    ("model/safety.cc", "std::uint32_t Safety::late(", "s.late"),
    ("model/safety.cc", "std::uint32_t Safety::fight_enemies_any(", "s.fight_any"),
    ("model/safety.cc", "int Safety::threats_at(", "s.threats_at"),
    ("model/safety.cc", "[[gnu::noinline]] void Safety::find_members() {", "s.find_members"),
    ("model/turn_order.cc", "void set_turn_order(", "o.set_turn_order"),
    ("combat/fight.cc", "float recall_line(const World& world, Safety& safety, vec2 p) {", "wh.recall_line"),
    ("combat/fight.cc", "bool hold_outlasts(", "wh.hold_outlasts"),
    ("combat/fight.cc", "bool paying_soon(", "wh.paying_soon"),
    ("combat/fight.cc", "bool flee_camps(", "r.flee_camps"),
    ("combat/fight.cc", "void retreat_step(", "r.retreat_step"),
    ("combat/fight.cc", "const ChampionBelief* game_ender(", "c.game_ender"),
    ("combat/fight.cc", "bool want_home(", "wh.want_home"),
    ("economy/crew.cc", "int mono_trapped(", "wh.mono_trapped"),
    ("economy/bank.cc", "bool tribute_safe(", "c.tribute_safe"),
    ("economy/bank.cc", "bool can_tribute_safely(", "c.can_tribute_safely"),
    ("economy/bank.cc", "bool recall_to_bank(", "c.recall_to_bank"),
    ("economy/bank.cc", "bool recall_outruns(", "c.recall_outruns"),
    ("economy/bank.cc", "bool recall_to_farm(", "c.recall_to_farm"),
    ("economy/capture.cc", "bool capture_recall(", "c.capture_recall"),
    ("economy/shop.cc", "bool wants_shop(", "c.wants_shop"),
    ("model/turn_order.cc", "int danger(", "o.danger"),
    ("model/turn_order.cc", "void offer_kills(", "o.offer_kills"),
    ("model/turn_order.cc", "void offer_channel(", "o.offer_channel"),
    ("model/turn_order.cc", "bool may_escape(", "o.may_escape"),
    ("model/turn_order.cc", "void offer_escape(", "o.offer_escape"),
    ("model/turn_order.cc", "void offer_heal(", "o.offer_heal"),
    ("model/safety.cc", "int Safety::approach(", "s.approach"),
    ("model/safety.cc", "std::uint32_t Safety::fight_key(vec2 p) {", "s.fight_key"),
    ("model/safety.cc", "bool Safety::avoid_within(", "s.avoid_within"),
    ("model/safety.cc", "float Safety::worst_damage(", "s.worst_damage"),
]:
    scope_fn(name, prefix, label)

# Counters (no fuel to speak of): how often each query runs, and the widening behind it.
sub("model/safety.cc", [
    ("""Blow Safety::blow(const ChampionBelief& e, vec2 p) {
""", """Blow Safety::blow(const ChampionBelief& e, vec2 p) {
    CEN_COUNT("n.blow");
"""),
    ("""    if (memo.stamp == stamp_ && memo.p == p) return memo.blow;
    Blow out;""", """    if (memo.stamp == stamp_ && memo.p == p) return memo.blow;
    CEN_COUNT(twice_ ? "n.reach_at2" : "n.reach_at1");
    Blow out;"""),
    ("""    if (memo.stamp == stamp_ && memo.p == p) return memo.blow;
    Blow out, one;""", """    if (memo.stamp == stamp_ && memo.p == p) return memo.blow;
    CEN_COUNT(twice_ ? "n.reach_at2" : "n.reach_at1");
    Blow out, one;"""),
    ("""    r.build(world_, e, next_turn_round(world_, e), turns_before_ours(world_, e) >= 2);""",
     """    debug_block({ census::count(turns_before_ours(world_, e) >= 2 ? "n.reach_build2" : "n.reach_build1"); });
    r.build(world_, e, next_turn_round(world_, e), turns_before_ours(world_, e) >= 2);"""),
    ("""    m.widened_known = true;
    m.widened_slots = m2.slots;""", """    m.widened_known = true;
    CEN_COUNT("n.widen");
    m.widened_slots = m2.slots;"""),
    ("""Safety::Bound Safety::bound(vec2 p, float blow_scale) {
""", """Safety::Bound Safety::bound(vec2 p, float blow_scale) {
    CEN_COUNT("n.bound");
"""),
    ("""bool Safety::lethal(vec2 p) {
""", """bool Safety::lethal(vec2 p) {
    CEN_COUNT("n.lethal");
"""),
    ("""std::uint32_t Safety::fight_key(vec2 p) {
""", """std::uint32_t Safety::fight_key(vec2 p) {
    CEN_COUNT("n.fight_key");
"""),
    ("""Trade Safety::stand(vec2 p, int approach, bool falls, bool unseen, int joined) {
""", """Trade Safety::stand(vec2 p, int approach, bool falls, bool unseen, int joined) {
    CEN_COUNT("n.stand");
"""),
    ("""bool Safety::threatened(vec2 p) {
""", """bool Safety::threatened(vec2 p) {
    CEN_COUNT("n.threatened");
"""),
], need=False)

# Per turn: visible enemies counted two turns before ours, and enemies within 4 (the fight size).
sub("bot.cc", [
    ("""        for (const auto& cb : world.camps) c.awake += cb.awake == Awake::awake;
    });""", """        for (const auto& cb : world.camps) c.awake += cb.awake == Awake::awake;
        int two = 0, near4 = 0;
        for (const auto& e : world.enemies)
            if (e.alive && e.visible && dist(e.pos, world.me().pos) <= 6) two += turns_before_ours(world, e) >= 2, ++near4;
        census::count(two == 0 ? "t.two0" : two == 1 ? "t.two1" : "t.two2+");
        census::count(near4 == 0 ? "t.near0" : near4 == 1 ? "t.near1" : "t.near2+");
    });"""),
])
print("instrumented", SRC)

# The worst-case model's own work: enemy_order's recomputes, its callers, strike_foe (threat_strike).
if (SRC / "model/enemy_order.cc").exists():
    sub("model/enemy_order.cc", [
        ("""    if (o.round == world.round && o.observations == world.observations) return o;""",
         """    CEN_COUNT("n.enemy_order");
    if (o.round == world.round && o.observations == world.observations) return o;
    CENSUS("o.enemy_order");"""),
        ('#include "world.h"', '#include "world.h"\n#include "../util.h"'),
    ], need=False)
    sub("model/safety.cc", [
        ("""int turns_before_ours(const World& world, const ChampionBelief& c) {
""", """int turns_before_ours(const World& world, const ChampionBelief& c) {
    CEN_COUNT("n.turns_before_ours");
"""),
    ], need=False)
sub("model/safety.cc", [
    ("""[[gnu::noinline]] void Safety::strike_foe(const ChampionBelief& e, Foe& x) {
""", """[[gnu::noinline]] void Safety::strike_foe(const ChampionBelief& e, Foe& x) {
    CENSUS("s.strike_foe");
"""),
    ("""[[gnu::noinline]] void Safety::count_foe(const ChampionBelief& e, Foe& x) {
""", """[[gnu::noinline]] void Safety::count_foe(const ChampionBelief& e, Foe& x) {
    CENSUS("s.count_foe");
"""),
], need=False)

# ast-safety's per-tile order: the picks and the base Reach builds.
for name, prefix, label in [
    ("model/safety.cc", "[[gnu::noinline]] std::uint32_t Safety::pick(", "s.pick"),
    ("model/safety.cc", "const Reach& Safety::base_reach_of(", "s.base_reach_of"),
    ("model/safety.cc", "std::uint32_t Safety::lost_in_reach(", "s.lost_in_reach"),
    ("model/safety.cc", "Blow Safety::base_blow(", "s.base_blow"),
]:
    scope_fn(name, prefix, label)
