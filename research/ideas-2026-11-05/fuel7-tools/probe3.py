"""probe3.py SRC: call counters for the farm loop's crew work, on top of probe2.py (run probe2 first).

Global counters (util.h's f7c) of calls and fuel, printed with probe2's LS lines as `LC round handle c0 f0 c1 f1 ...`:
0 work_arrival, 1 its misses, 2 plan_crew, 3 its price(), 4 min_camp_damage inside price, 5 share_damage,
6 crew_available_bits, 7 crew_allies, 8 the crewable bound's ally pass (crew_bound), 9 crew_work.
"""
import sys
from pathlib import Path

root = Path(sys.argv[1])


def edit(rel, pairs):
    p = root / rel
    s = p.read_text()
    for old, new in pairs:
        if s.count(old) != 1:
            sys.exit(f"{rel}: pattern found {s.count(old)} times: {old[:90]!r}")
        s = s.replace(old, new)
    p.write_text(s)


edit("util.h", [("inline std::uint64_t fuel() { return static_cast<std::uint64_t>(cambc::detail::sdk_fuel_remaining()); }",
                 """inline std::uint64_t fuel() { return static_cast<std::uint64_t>(cambc::detail::sdk_fuel_remaining()); }
inline std::uint64_t f7c[2][16];
struct F7Time {
    int i;
    std::uint64_t at;
    explicit F7Time(int i) : i(i), at(fuel()) {}
    ~F7Time() { ++f7c[0][i], f7c[1][i] += at - fuel(); }
};""")])
edit("economy/farm.cc", [
    ("""    const auto work_arrival = [&](const ChampionBelief& a, int g) __attribute__((always_inline)) {
        WorkArrival arrival;""",
     """    const auto work_arrival = [&](const ChampionBelief& a, int g) __attribute__((always_inline)) {
        F7Time f7t(0);
        WorkArrival arrival;"""),
    ("""            *kept = {true, a.visible, a.pos.x, a.pos.y, belief.version, arrival.dash_ready, arrival.recall_delay, first_turn, -1};
        }""",
     """            *kept = {true, a.visible, a.pos.x, a.pos.y, belief.version, arrival.dash_ready, arrival.recall_delay, first_turn, -1};
        }
        F7Time f7m(1);"""),
    ("""    const auto crew_work = [&](const CrewAllies* allies, int g, int working, int waiting) __attribute__((always_inline)) {
        CrewWork total;""",
     """    const auto crew_work = [&](const CrewAllies* allies, int g, int working, int waiting) __attribute__((always_inline)) {
        F7Time f7t(9);
        CrewWork total;"""),
    ("""        if (!crew_read) crew_allies(world, line, crew_table), crew_read = true;""",
     """        if (!crew_read) { F7Time f7t(7); crew_allies(world, line, crew_table), crew_read = true; }"""),
    ("""                float claimers = 0, all = strength;
                int members = 0;""",
     """                F7Time f7t(8);
                float claimers = 0, all = strength;
                int members = 0;"""),
    ("""            std::printf("\\nLX %d %u %d", round""",
     """            std::printf("\\nLC %d %u", round, my_handle());
            for (int i = 0; i < 10; ++i) std::printf(" %llu %llu", (unsigned long long)f7c[0][i], (unsigned long long)f7c[1][i]);
            std::printf("\\nLX %d %u %d", round"""),
])
edit("economy/crew.cc", [
    ("""CrewPlan plan_crew(const World& world, const CrewAllies& allies, int g, float my_output, bool expect, int cap) {
    CrewPlan plan;""",
     """CrewPlan plan_crew(const World& world, const CrewAllies& allies, int g, float my_output, bool expect, int cap) {
    F7Time f7t(2);
    CrewPlan plan;"""),
    ("""    const auto price = [&](CrewPlan& p) {
        float h = survivable;""",
     """    const auto price = [&](CrewPlan& p) {
        F7Time f7p(3);
        float h = survivable;"""),
    ("""        p.damage = min_camp_damage(world, g, p.output, &p.rounds, 0, -1, h);""",
     """        { F7Time f7m(4); p.damage = min_camp_damage(world, g, p.output, &p.rounds, 0, -1, h); }"""),
    ("""void share_damage(const CrewAllies::Ally* const* members, int n, CrewPlan& p) {
    std::array<const CrewAllies::Ally*, 16> pool;""",
     """void share_damage(const CrewAllies::Ally* const* members, int n, CrewPlan& p) {
    F7Time f7t(5);
    std::array<const CrewAllies::Ally*, 16> pool;"""),
    ("""std::uint32_t crew_available_bits(const World& world, const CrewAllies& allies, int g) {
    if (allies.avail_group == g) return allies.avail_bits;""",
     """std::uint32_t crew_available_bits(const World& world, const CrewAllies& allies, int g) {
    F7Time f7t(6);
    if (allies.avail_group == g) return allies.avail_bits;"""),
])
print("ok")
