"""mkcprof.py SRC DST: bots/variants/DST = bots/SRC/src + CREWPROF lines (crew pricing fuel by part, per farm loop)."""
import shutil, sys
from pathlib import Path

root = Path(__file__).resolve().parents[2]
dst = root / "bots/variants" / sys.argv[2]
shutil.rmtree(dst, ignore_errors=True)
shutil.copytree(root / "bots" / sys.argv[1] / "src", dst / "src")


def patch(rel, reps):
    p = dst / "src" / rel
    s = p.read_text()
    for a, b in reps:
        assert s.count(a) == 1, (rel, a)
        s = s.replace(a, b)
    p.write_text(s)


# Slots: 0 crew_work (claimed), 1 plan_crew claimed, 2 may_beat block, 3 plan_crew crewable,
# 4 crew_allies build, 5 pc claimers+survivable, 6 pc first mcd, 7 pc first share, 8 pc free list,
# 9 pc exp mcd, 10 pc exp share, 11 pc exp total, 12 home_survivable in price, 13 share add-loop (arrivals),
# 14 share sort+level+trips, 15 pc exp iterations (count only)
patch("economy/crew.cc", [
("""int crew_arrival(const World& world, const ChampionBelief& a, int g, vec2 p) {
""", """int crew_arrival_(const World& world, const ChampionBelief& a, int g, vec2 p);
int crew_arrival(const World& world, const ChampionBelief& a, int g, vec2 p) {
    const std::uint64_t t0 = fuel();
    const int r = crew_arrival_(world, a, g, p);
    CPROF(16, t0);
    return r;
}
int crew_arrival_(const World& world, const ChampionBelief& a, int g, vec2 p) {
"""),
("""    if (k.first != key) k = {key, steps_to(world.map().groups[g], p)};""",
 """    if (k.first != key) { k = {key, steps_to(world.map().groups[g], p)}; debug_block({ crew_prof.v[17] += world.map().groups[g].members.size(); crew_prof.c[17]++; }); }"""),
("""        if (!a.has_pool) read_pool(allies, a);""", """        if (!a.has_pool) { const std::uint64_t t0 = fuel(); read_pool(allies, a); CPROF(21, t0); }"""),
("""bool crew_available(const World& world, const CrewAllies& allies, const CrewAllies::Ally& a, int g) {
    if (!a.has_avail) read_avail(world, allies, a);""", """bool crew_available_(const World& world, const CrewAllies& allies, const CrewAllies::Ally& a, int g);
bool crew_available(const World& world, const CrewAllies& allies, const CrewAllies::Ally& a, int g) {
    const std::uint64_t t0 = fuel();
    const bool r = crew_available_(world, allies, a, g);
    CPROF(22, t0);
    return r;
}
bool crew_available_(const World& world, const CrewAllies& allies, const CrewAllies::Ally& a, int g) {
    if (!a.has_avail) { const std::uint64_t t0 = fuel(); read_avail(world, allies, a); CPROF(23, t0); }"""),
("""namespace aph {

namespace {
""", """namespace aph {

struct CrewProf { std::uint64_t v[24]{}; int c[24]{}; };
inline CrewProf crew_prof;
inline bool crew_prof_first = true;
#define CPROF(i, t0) do { const std::uint64_t _t1 = fuel(); debug_block({ crew_prof.v[i] += (t0) - _t1; crew_prof.c[i]++; }); } while (0)

namespace {
"""),
("""    std::array<const CrewAllies::Ally*, 16> pool;
    int n = 0;
    const int mine""", """    const std::uint64_t s0 = fuel();
    std::array<const CrewAllies::Ally*, 16> pool;
    int n = 0;
    const int mine"""),
("""    std::sort(pool.begin(), pool.begin() + n, [](const CrewAllies::Ally* x, const CrewAllies::Ally* y) { return x->score > y->score; });
""", """    CPROF(13, s0);
    const std::uint64_t s1 = fuel();
    std::sort(pool.begin(), pool.begin() + n, [](const CrewAllies::Ally* x, const CrewAllies::Ally* y) { return x->score > y->score; });
"""),
("""        p.trips += extra_trips(absorbed * m.taken, m.budget, m.usable);
    }
}""", """        p.trips += extra_trips(absorbed * m.taken, m.budget, m.usable);
    }
    CPROF(14, s1);
}"""),
("""    CrewPlan plan;
    plan.output = my_output;""", """    std::uint64_t q0 = fuel();
    CrewPlan plan;
    plan.output = my_output;"""),
("""    const auto price = [&](CrewPlan& p) {
        float h = survivable;
        for (int k = 0; k < p.n_expected; ++k) h = std::min(h, home_survivable(*allies.at[static_cast<std::size_t>(p.expected[k])].a));
        p.damage = min_camp_damage(world, g, p.output, &p.rounds, 0, -1, h);
        // Only the traces read the tank.
        debug_block({ p.tank = crew_tank(world, g, {p.expected.data(), static_cast<std::size_t>(p.n_expected)}); });
        share_damage(world, allies, g, p);
    };
    price(plan);
    if (!expect || plan.trips == 0) return plan;""", """    CPROF(5, q0);
    const auto price = [&](CrewPlan& p) {
        std::uint64_t r0 = fuel();
        float h = survivable;
        for (int k = 0; k < p.n_expected; ++k) h = std::min(h, home_survivable(*allies.at[static_cast<std::size_t>(p.expected[k])].a));
        CPROF(12, r0);
        r0 = fuel();
        p.damage = min_camp_damage(world, g, p.output, &p.rounds, 0, -1, h);
        CPROF(crew_prof_first ? 6 : 9, r0);
        // Only the traces read the tank.
        debug_block({ p.tank = crew_tank(world, g, {p.expected.data(), static_cast<std::size_t>(p.n_expected)}); });
        r0 = fuel();
        share_damage(world, allies, g, p);
        CPROF(crew_prof_first ? 7 : 10, r0);
    };
    crew_prof_first = true;
    price(plan);
    if (!expect || plan.trips == 0) return plan;
    q0 = fuel();"""),
("""    std::sort(free.begin(), free.begin() + n_free);
    for (int i = 0; i < n_free""", """    std::sort(free.begin(), free.begin() + n_free);
    CPROF(8, q0);
    q0 = fuel();
    crew_prof_first = false;
    for (int i = 0; i < n_free"""),
("""        if (more.trips >= plan.trips) break;
        plan = more;
    }
    return plan;""", """        debug_block({ crew_prof.c[15]++; });
        if (more.trips >= plan.trips) break;
        plan = more;
    }
    CPROF(11, q0);
    return plan;"""),
])

patch("economy/farm.cc", [
("""            const float output = camp_output(a);
            total.output += output;
            const auto arrival = work_arrival(a, g);""", """            std::uint64_t w0 = fuel();
            const float output = camp_output(a);
            CPROF(19, w0);
            total.output += output;
            w0 = fuel();
            const auto arrival = work_arrival(a, g);
            CPROF(18, w0);"""),
("""        if (!crew_read) crew_allies(world, line, crew_table), crew_read = true;""",
 """        if (!crew_read) { const std::uint64_t t0 = fuel(); crew_allies(world, line, crew_table), crew_read = true; CPROF(4, t0); }"""),
("""            const auto crew = crew_work(g, working, waiting);""",
 """            std::uint64_t cw0 = fuel();
            const auto crew = crew_work(g, working, waiting);
            CPROF(0, cw0);"""),
("""            const CrewPlan plan = op ? plan_crew(world, crew_allies_now(), g, strength, expect, crew_cap(g)) : CrewPlan{};""",
 """            const auto& cw_allies = crew_allies_now();
            cw0 = fuel();
            const CrewPlan plan = op ? plan_crew(world, cw_allies, g, strength, expect, crew_cap(g)) : CrewPlan{};
            if (op) CPROF(1, cw0);"""),
("""            bool may_beat = true;
            if (worth > 0 && g != memory.mono_group) {""", """            bool may_beat = true;
            std::uint64_t mb0 = fuel();
            if (worth > 0 && g != memory.mono_group) {"""),
("""            const CrewPlan plan = may_beat ? plan_crew(world, crew_allies_now(), g, strength, expect, crew_cap(g)) : CrewPlan{};""",
 """            CPROF(2, mb0);
            const auto& mb_allies = crew_allies_now();
            mb0 = fuel();
            const CrewPlan plan = may_beat ? plan_crew(world, mb_allies, g, strength, expect, crew_cap(g)) : CrewPlan{};
            if (may_beat) CPROF(3, mb0);"""),
("""    if (k < evaluated) note_shortcut("farm-partial-evaluation");""", """    debug_block({
        if (!opening) {
            std::printf("CREWPROF %d %u cut %d bank %d k %d n %d", round, my_handle(), k < evaluated ? 1 : 0, banks_bag ? 1 : 0, k, n_groups);
            for (int i = 0; i < 24; ++i) std::printf(" %llu:%d", (unsigned long long)crew_prof.v[i], crew_prof.c[i]);
            std::printf("\\n");
        }
        crew_prof = CrewProf{};
    });
    { const std::uint64_t t0 = fuel(); CPROF(20, t0); }
    if (k < evaluated) note_shortcut("farm-partial-evaluation");"""),
])
