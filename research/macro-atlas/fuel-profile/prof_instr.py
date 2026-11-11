"""Adds per-turn fuel scopes to a debug copy of charybdis (517 or 517+remaining)."""
import sys, re
from pathlib import Path
SRC = Path(sys.argv[1])

def sub(name, a, b, need=True):
    p = SRC / name
    s = p.read_text()
    n = s.count(a)
    if n != 1:
        if need: raise SystemExit(f"{name}: {n} matches for {a[:80]!r}")
        print(f"skip {name}: {a[:60]!r}"); return
    p.write_text(s.replace(a, b))

PROF = r'''
namespace prof {
// 0 lethal, 1 stunner_near, 2 stun_follow_up, 3 lethal stun-path worst_damage, 5 coming_casts, 6 retreat_step,
// 7 press (computed), 8 press_taken (computed), 9 press_avoid, 10 step_guard, 11 decide
inline std::uint64_t acc[16];
inline std::uint32_t cnt[16];
inline std::uint64_t cum[16];
inline std::uint32_t cumc[16];
inline std::uint64_t now() { return static_cast<std::uint64_t>(cambc::detail::sdk_fuel_remaining()); }
inline void add(int k, std::uint64_t f) { acc[k] += f, ++cnt[k]; }
struct Scope {
    int k; std::uint64_t s;
    explicit Scope(int k) : k{k}, s{now()} {}
    ~Scope() { const auto e = now(); if (e <= s) add(k, s - e); }
};
} // namespace prof
#define PROF_SCOPE(K) ::aph::prof::Scope prof_scope_{K}
'''
# util.h: after fuel() definition
sub("util.h", "inline std::uint64_t fuel() { return static_cast<std::uint64_t>(cambc::detail::sdk_fuel_remaining()); }\n",
    "inline std::uint64_t fuel() { return static_cast<std::uint64_t>(cambc::detail::sdk_fuel_remaining()); }\n" + PROF)

sub("model/safety.cc", "bool Safety::lethal(vec2 p) {\n", "bool Safety::lethal(vec2 p) {\n    PROF_SCOPE(0);\n")
sub("model/safety.cc", "bool Safety::stunner_near(vec2 p) {\n", "bool Safety::stunner_near(vec2 p) {\n    PROF_SCOPE(1);\n", need=False)
sub("model/safety.cc", "float Safety::stun_follow_up(vec2 p, float blow_scale, float& cost) {\n",
    "float Safety::stun_follow_up(vec2 p, float blow_scale, float& cost) {\n    PROF_SCOPE(2);\n", need=False)
sub("model/safety.cc", "    const float first = worst_damage(p, taken);\n    if (first >= health || !stun) return first >= health;\n",
    "    const auto prof_w = prof::now();\n    const float first = worst_damage(p, taken);\n    if (stun) prof::add(3, prof_w - prof::now());\n    if (first >= health || !stun) return first >= health;\n", need=False)
sub("combat/fight.cc", "int coming_casts(const World& world, std::array<ComingCast, 8>& out) {\n",
    "int coming_casts(const World& world, std::array<ComingCast, 8>& out) {\n    PROF_SCOPE(5);\n", need=False)
sub("combat/fight.cc", "void retreat_step(const World& world, Pathing& pathing, Safety& safety, const Field& home, bool survivable = false) {\n",
    "void retreat_step(const World& world, Pathing& pathing, Safety& safety, const Field& home, bool survivable = false) {\n    PROF_SCOPE(6);\n", need=False)
sub("combat/fight.cc", "void retreat_step(const World& world, Pathing& pathing, Safety& safety, const Field& home) {\n",
    "void retreat_step(const World& world, Pathing& pathing, Safety& safety, const Field& home) {\n    PROF_SCOPE(6);\n", need=False)
sub("combat/fight.cc", "    m.value = {};\n    m.taken = -1;\n", "    m.value = {};\n    m.taken = -1;\n    PROF_SCOPE(7);\n", need=False)
sub("combat/fight.cc", "    if (press_memo.taken < 0) {\n        int held = 0;\n", "    if (press_memo.taken < 0) {\n        PROF_SCOPE(8);\n        int held = 0;\n", need=False)
sub("combat/fight.cc", "const bitboard& press_avoid(const World& world, Safety& safety, const ChampionBelief& target, const bitboard* zone) {\n",
    "const bitboard& press_avoid(const World& world, Safety& safety, const ChampionBelief& target, const bitboard* zone) {\n    PROF_SCOPE(9);\n", need=False)
sub("combat/guard.cc", "const bitboard* step_guard(const World& world, Safety& safety, vec2 here, int radius) {\n",
    "const bitboard* step_guard(const World& world, Safety& safety, vec2 here, int radius) {\n    PROF_SCOPE(10);\n")
sub("main.cc", "            aph::FuelMeter meter{\"decide\"};\n", "            aph::FuelMeter meter{\"decide\"};\n            PROF_SCOPE(11);\n")
# main loop: print per turn
sub("main.cc", "        else\n            instance.play_turn(late);\n",
"""        else {
            const auto prof_f0 = aph::fuel();
            for (auto& x : aph::prof::acc) x = 0;
            for (auto& x : aph::prof::cnt) x = 0;
            instance.play_turn(late);
            const auto prof_f1 = aph::fuel();
            const bool prof_oof = aph::round_now() != round;
            debug_block({
                using namespace aph::prof;
                for (int k = 0; k < 16; ++k) cum[k] += acc[k], cumc[k] += cnt[k];
                const unsigned h = static_cast<unsigned>(static_cast<cambc::handle_champion_t>(cambc::self()));
                if (prof_oof || acc[11] >= 50000) {
                    std::printf("PROF %u %u %d %llu", round, h, prof_oof ? 1 : 0, static_cast<unsigned long long>(prof_oof ? 0 : prof_f0 - prof_f1));
                    for (int k = 0; k < 12; ++k) std::printf(" %llu:%u", static_cast<unsigned long long>(acc[k]), cnt[k]);
                    std::printf("\\n");
                }
                if (round % 250 == 0 || round == 1999 || round == 2000) {
                    std::printf("PCUM %u %u", round, h);
                    for (int k = 0; k < 12; ++k) std::printf(" %llu:%u", static_cast<unsigned long long>(cum[k]), cumc[k]);
                    std::printf("\\n");
                }
            });
        }
""")
print("ok")
