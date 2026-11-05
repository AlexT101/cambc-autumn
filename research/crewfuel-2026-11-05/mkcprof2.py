"""mkcprof2.py SRC DST: as mkcprof.py for the rewritten crew pricing (crew tables): bots/variants/DST = bots/SRC/src +
CREWPROF lines, the same 24 slots (those the rewrite has no part for stay 0)."""
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


patch("economy/camps.cc", [
("""namespace aph {
""", """namespace aph {

struct CrewProf { std::uint64_t v[24]{}; int c[24]{}; };
inline CrewProf crew_prof;
inline bool crew_prof_first = true, crew_prof_in = false;
#define CPROF(i, t0) do { const std::uint64_t _t1 = fuel(); debug_block({ crew_prof.v[i] += (t0) - _t1; crew_prof.c[i]++; }); } while (0)
"""),
])
patch("economy/crew.cc", [
("""    int mine = -1;
""", """    int mine = -1;
    std::uint64_t z0 = fuel();
"""),
("""    if (self >= 0) take(self);
""", """    if (self >= 0) take(self);
    CPROF(21, z0);
"""),
("""        CrewPlan more = plan;
        const int slot = free[i].second;
        more.expected[more.n_expected++] = slot;
        const auto& a = allies.at[static_cast<std::size_t>(slot)];
        more.output += crew_output(a);
        if (a.a->alive && in_time(a)) joins |= 1u << slot;""", """        z0 = fuel();
        CrewPlan more = plan;
        const int slot = free[i].second;
        more.expected[more.n_expected++] = slot;
        const auto& a = allies.at[static_cast<std::size_t>(slot)];
        CPROF(23, z0);
        z0 = fuel();
        more.output += crew_output(a);
        if (a.a->alive && in_time(a)) joins |= 1u << slot;
        CPROF(22, z0);"""),
("""    CrewPlan plan;
    plan.output = my_output;""", """    std::uint64_t q0 = fuel();
    CrewPlan plan;
    plan.output = my_output;"""),
("""    // Expected allies in the pool, by slot bit.""", """    CPROF(5, q0);
    // Expected allies in the pool, by slot bit."""),
("""        p.damage = min_camp_damage(world, g, p.output, &p.rounds, 0, -1, h);""", """        std::uint64_t r0 = fuel();
        int hits0 = 0;
        debug_block({ crew_prof_in = true; hits0 = crew_prof.c[16]; });
        const std::uint64_t m0 = fuel();
        p.damage = min_camp_damage(world, g, p.output, &p.rounds, 0, -1, h);
        const std::uint64_t m1 = fuel();
        debug_block({ crew_prof_in = false; crew_prof.v[crew_prof.c[16] != hits0 ? 16 : 17] += m0 - m1; });
        CPROF(crew_prof_first ? 6 : 9, r0);
        r0 = fuel();
        struct Done { std::uint64_t r0; ~Done() { CPROF(crew_prof_first ? 7 : 10, r0); } } done{r0};"""),
("""    price(plan);
    if (!expect || plan.trips == 0) return plan;""", """    crew_prof_first = true;
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
("""            const auto arrival = work_arrival(a, g);""", """            const std::uint64_t w0 = fuel();
            const auto arrival = work_arrival(a, g);
            CPROF(18, w0);"""),
("""        if (!crew_read) crew_allies(world, line, crew_table), crew_read = true;""",
 """        if (!crew_read) { const std::uint64_t t0 = fuel(); crew_allies(world, line, crew_table), crew_read = true; CPROF(4, t0); }"""),
("""            const auto crew = crew_work(op || crew_read ? &crew_allies_now() : nullptr, g, working, waiting);""",
 """            const CrewAllies* cw_allies0 = op || crew_read ? &crew_allies_now() : nullptr;
            std::uint64_t cw0 = fuel();
            const auto crew = crew_work(cw_allies0, g, working, waiting);
            CPROF(0, cw0);"""),
("""            const CrewPlan plan = op ? plan_crew(world, crew_allies_now(), g, strength, expect, crew_cap(g)) : CrewPlan{};""",
 """            const auto& cw_allies = crew_allies_now();
            cw0 = fuel();
            const CrewPlan plan = op ? plan_crew(world, cw_allies, g, strength, expect, crew_cap(g)) : CrewPlan{};
            if (op) CPROF(1, cw0);"""),
("""            bool may_beat = true;
""", """            bool may_beat = true;
            std::uint64_t mb0 = fuel();
"""),
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
    if (k < evaluated) note_shortcut("farm-partial-evaluation");"""),
("""                if (crew_value > value) {
                    value = crew_value, late = false, spell = false;""", """                debug_block({ if (crew_value > value) { crew_prof.c[12]++; if (crew_value > best_value) crew_prof.c[13]++; } });
                if (crew_value > value) {
                    value = crew_value, late = false, spell = false;"""),
("""            shared = g, shared_value = value, shared_steps = steps;""", """            debug_block({ if (op) crew_prof.c[14]++; });
            shared = g, shared_value = value, shared_steps = steps;"""),
])

patch("economy/camps.cc", [
("""            *rounds = c.rounds[i];
            return c.damage[i];
        }""", """            *rounds = c.rounds[i];
            debug_block({ if (crew_prof_in) crew_prof.c[16]++; });
            return c.damage[i];
        }"""),
("""    const int i = c.next;
    c.next = (c.next + 1) % static_cast<int>(c.strength.size());""", """    debug_block({ if (crew_prof_in) crew_prof.c[17]++; });
    const int i = c.next;
    c.next = (c.next + 1) % static_cast<int>(c.strength.size());"""),
])
patch("economy/farm.cc", [
])
