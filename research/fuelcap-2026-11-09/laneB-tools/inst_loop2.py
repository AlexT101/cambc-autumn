"""Instrument farm_turn's loop: fuel per iteration by exit line and sub-meters, all and heavy (>=15k) loops; low overhead."""
import re, sys
p = sys.argv[1] + '/src/economy/farm.cc'
L = open(p).read().split('\n')
LO, HI = 1711, 2202
assert L[LO-1].strip().startswith('for (; k < evaluated && room(); ++k) {'), L[LO-1]
assert L[HI-1].strip() == '}', L[HI-1]
def sub(n, old, new, count=1):
    assert old in L[n-1], (n, old, L[n-1]); L[n-1] = L[n-1].replace(old, new, count)
sub(2013, 'const auto& allies = crew_allies_now();', 'FBM(1, (crew_allies_now(), 0)); const auto& allies = crew_allies_now();')
sub(2020, 'const auto crew = crew_work(', 'FBM(2, (op || crew_read ? (crew_allies_now(), 0) : 0)); const auto crew = FBM(3, crew_work(')
sub(2020, 'working, waiting);', 'working, waiting));')
sub(2031, 'plan_crew(world, crew_allies_now(), g, strength, expect, crew_cap(g))', 'FBM(4, plan_crew(world, crew_allies_now(), g, strength, expect, crew_cap(g)))')
sub(2175, 'plan_crew(world, crew_allies_now(), g, strength, expect, crew_cap(g))', 'FBM(5, plan_crew(world, crew_allies_now(), g, strength, expect, crew_cap(g)))')
for n in range(LO, HI):
    L[n-1] = re.sub(r'trips_home\((static_cast<float>\([a-z_]+\))\)', r'FBM(6, trips_home(\1))', L[n-1])
    L[n-1] = re.sub(r'too_late\(([a-z_.]+)\)', r'FBM(7, too_late(\1))', L[n-1])
sub(2049, 'min_camp_damage(world, g, strength + others, &joint_rounds)', 'FBM(8, min_camp_damage(world, g, strength + others, &joint_rounds))')
sub(2062, 'min_camp_damage(world, g, strength, &known.rounds, reflect)', 'FBM(9, min_camp_damage(world, g, strength, &known.rounds, reflect))')
sub(2063, 'spell_clear_rounds(world, g, range, spells, basic)', 'FBM(10, spell_clear_rounds(world, g, range, spells, basic))')
sub(1932, 'pathing.live_steps(g, belief.state != CampState::cleared ? range : 0)', 'FBM(11, pathing.live_steps(g, belief.state != CampState::cleared ? range : 0))')
sub(1822, 'known.fastest = fastest_clear(world, g, strength)', 'known.fastest = FBM(12, fastest_clear(world, g, strength))')
sub(1946, 'via_recall.sooner(spawn_steps(g), respawn, steps)', 'via_recall.sooner(FBM(13, spawn_steps(g)), respawn, steps)')
sub(1838, 'if (steps_known < 0) {', 'if (steps_known < 0) { FbSub fbs_(14);')
sub(1781, 'known.planned != (g == planned_now)) {', 'known.planned != (g == planned_now)) { FbSub fbs_(15);')
sub(1767, 'fastest = kf.fastest = fastest_clear(world, g, strength)', 'fastest = kf.fastest = FBM(16, fastest_clear(world, g, strength))')
for i in range(LO, HI - 1):
    if i + 1 == 1716: continue
    L[i] = re.sub(r'\bcontinue;', '{ fbi_it.line = %d; continue; }' % (i + 1), L[i])
    L[i] = re.sub(r'\bbreak;', '{ fbi_it.line = %d; break; }' % (i + 1), L[i])
L[LO-1] = '    fbi_turn_begin();\n' + L[LO-1] + ' FbIt fbi_it;'
L[HI-1] = L[HI-1] + '\n    fbi_turn_end(k, evaluated);'
src = '\n'.join(L)
helper = r'''
namespace {
constexpr int fbi_lines = 2600, fbi_subs = 32;
struct FbAcc { std::uint64_t fuel[fbi_lines]{}; std::uint32_t n[fbi_lines]{}; std::uint64_t sf[fbi_subs]{}; std::uint32_t sn[fbi_subs]{}; };
FbAcc fbi_all, fbi_heavy, fbi_turn;
std::uint16_t fbi_touched[4096]; int fbi_nt = 0;
std::uint64_t fbi_start = 0, fbi_loops = 0, fbi_heavy_loops = 0, fbi_heavy_fuel = 0, fbi_heavy_iters = 0, fbi_heavy_groups = 0, fbi_heavy_cut = 0;
int fbi_last_print = 0;
struct FbIt {
    int line = 2201;
    std::uint64_t s = fuel();
    ~FbIt() { const std::uint64_t e = fuel(); if (e < s) fbi_turn.fuel[line] += s - e; if (fbi_turn.n[line]++ == 0 && fbi_nt < 4096) fbi_touched[fbi_nt++] = static_cast<std::uint16_t>(line); }
};
struct FbSub {
    int id; std::uint64_t s;
    explicit FbSub(int i) : id(i), s(fuel()) {}
    ~FbSub() { const std::uint64_t e = fuel(); if (e < s) fbi_turn.sf[id] += s - e; ++fbi_turn.sn[id]; }
};
#define FBM(id, ...) ([&]() { FbSub fbs_(id); return __VA_ARGS__; }())
void fbi_turn_begin() {
    for (int i = 0; i < fbi_nt; ++i) fbi_turn.fuel[fbi_touched[i]] = 0, fbi_turn.n[fbi_touched[i]] = 0;
    fbi_nt = 0;
    for (int i = 0; i < fbi_subs; ++i) fbi_turn.sf[i] = 0, fbi_turn.sn[i] = 0;
    fbi_start = fuel();
}
void fbi_turn_end(int k, int evaluated) {
    const std::uint64_t e = fuel(); const std::uint64_t used = fbi_start > e ? fbi_start - e : 0;
    const bool heavy = used >= 15000;
    ++fbi_loops;
    if (heavy) ++fbi_heavy_loops, fbi_heavy_fuel += used, fbi_heavy_iters += static_cast<std::uint64_t>(k), fbi_heavy_groups += static_cast<std::uint64_t>(evaluated), fbi_heavy_cut += k < evaluated;
    for (int j = 0; j < fbi_nt; ++j) { const int i = fbi_touched[j];
        fbi_all.fuel[i] += fbi_turn.fuel[i], fbi_all.n[i] += fbi_turn.n[i];
        if (heavy) fbi_heavy.fuel[i] += fbi_turn.fuel[i], fbi_heavy.n[i] += fbi_turn.n[i];
    }
    for (int i = 0; i < fbi_subs; ++i) {
        fbi_all.sf[i] += fbi_turn.sf[i], fbi_all.sn[i] += fbi_turn.sn[i];
        if (heavy) fbi_heavy.sf[i] += fbi_turn.sf[i], fbi_heavy.sn[i] += fbi_turn.sn[i];
    }
    debug_block({
        const int r = static_cast<int>(round_now());
        if (r / 250 != fbi_last_print / 250) {
            fbi_last_print = r;
            std::printf("FBI %d loops %llu heavy %llu fuel %llu iters %llu groups %llu cut %llu\n", r, (unsigned long long)fbi_loops, (unsigned long long)fbi_heavy_loops,
                        (unsigned long long)fbi_heavy_fuel, (unsigned long long)fbi_heavy_iters, (unsigned long long)fbi_heavy_groups, (unsigned long long)fbi_heavy_cut);
            for (int i = 0; i < fbi_lines; ++i) if (fbi_all.n[i])
                std::printf("FBL %d %d %u %llu %u %llu\n", r, i, fbi_all.n[i], (unsigned long long)fbi_all.fuel[i], fbi_heavy.n[i], (unsigned long long)fbi_heavy.fuel[i]);
            for (int i = 0; i < fbi_subs; ++i) if (fbi_all.sn[i])
                std::printf("FBS %d %d %u %llu %u %llu\n", r, i, fbi_all.sn[i], (unsigned long long)fbi_all.sf[i], fbi_heavy.sn[i], (unsigned long long)fbi_heavy.sf[i]);
        }
    });
}
}
'''
idx = src.index('namespace aph {') + len('namespace aph {')
src = src[:idx] + '\n' + helper + src[idx:]
open(p, 'w').write(src)
print('ok')
