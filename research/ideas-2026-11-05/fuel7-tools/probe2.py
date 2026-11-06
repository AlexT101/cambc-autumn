"""probe2.py SRC: the fuel round 7 segment profile of farm_turn's group loop (economy/farm.cc), aggregated in the bot.

The loop body is cut into segments by fuel() marks; each group's fuel per segment, and its exit (the segment it
left in), are summed per champion and loop kind (banking or not). Every 100 rounds a champion prints its running
totals: `LS round handle bank loops loop_fuel groups mark_cost seg0 cnt0 seg1 cnt1 ...` (cnt: groups that ran the
segment) and `LX round handle bank exit n fuel ...` (exit: the segment a group left in; its whole cost).
Segments (SEGS below) name the code between consecutive marks.
"""
import sys
from pathlib import Path

SEGS = ["top", "prefacts", "stage1", "rated", "facts", "fastest", "steps", "least", "hops", "live", "bounds", "via",
        "claim_bound", "crew_work", "claim_mid", "claim_plan", "claim_end", "clear", "kited", "quick", "value", "crew_bound",
        "crew_plan", "crew_end", "tail"]
N = len(SEGS)

p = Path(sys.argv[1]) / "economy/farm.cc"
s = p.read_text()


def sub(old, new, count=1):
    global s
    n = s.count(old)
    if n != count:
        sys.exit(f"pattern found {n} times, wanted {count}: {old[:90]!r}")
    s = s.replace(old, new)


def M(name):
    return f"lsm({SEGS.index(name)});"


sub("""    int k = 0;
    for (; k < evaluated && room(); ++k) {
        int g = order ? (*order)[k] : (first + k) % n_groups;""",
"""    int k = 0;
    struct LsTotals {
        std::uint64_t loops = 0, loop_fuel = 0, groups = 0, marks = 0;
        std::uint64_t seg[%(N)d] = {}, cnt[%(N)d] = {}, xn[%(N)d] = {}, xf[%(N)d] = {};
        int printed = -1;
    };
    static LsTotals ls_tot[2];
    auto& lst = ls_tot[banks_bag ? 1 : 0];
    std::uint64_t ls_last = fuel(), ls_start = ls_last, ls_group = 0;
    int ls_seg = -1;
    const auto lsm = [&](int i) __attribute__((always_inline)) {
        const std::uint64_t f = fuel();
        lst.seg[i] += ls_last - f, ++lst.cnt[i];
        ls_last = f, ls_seg = i;
    };
    const auto ls_end = [&]() __attribute__((always_inline)) {
        if (ls_seg < 0) return;
        const std::uint64_t f = fuel();
        lst.seg[%(TAIL)d] += ls_last - f, ++lst.cnt[%(TAIL)d];
        ++lst.xn[ls_seg], lst.xf[ls_seg] += ls_group - f, ++lst.groups;
        ls_seg = -1, ls_last = f;
    };
    // the cost of a mark: two in a row
    { const std::uint64_t a = fuel(); const std::uint64_t b = fuel(); lst.marks += a - b; }
    for (; k < evaluated && room(); ++k) {
        ls_end();
        ls_last = ls_group = fuel(), ls_seg = -1;
        int g = order ? (*order)[k] : (first + k) %% n_groups;""" % {"N": N, "TAIL": SEGS.index("tail")})
sub("""        if ((pre_pruned && barred()) || (pre_banked && best >= 0)) pre_bounds(g);""",
    M("top") + """
        if ((pre_pruned && barred()) || (pre_banked && best >= 0)) pre_bounds(g);""")
sub("""        const auto& group = group_data[g];
        const auto& belief = camp_data[g];
        read_g = -1, read_kited = kited_of(g)""",
    M("prefacts") + """
        const auto& group = group_data[g];
        const auto& belief = camp_data[g];
        read_g = -1, read_kited = kited_of(g)""")
sub("""        const bool claimed = is_claimed(g);
        // Carrying, compare whole trips""",
    M("stage1") + """
        const bool claimed = is_claimed(g);
        // Carrying, compare whole trips""")
sub("""        auto& known = group_facts[g];
        if (known.context != context || known.sticky != (g == farm_group)) {""",
    M("rated") + """
        auto& known = group_facts[g];
        if (known.context != context || known.sticky != (g == farm_group)) {""")
sub("""        if (known.version != belief.version || known.fastest_strength != strength)
            known.version = belief.version, known.fastest_strength = strength, known.fastest = fastest_clear(world, g, strength);
        // Ren's for the rated prunes""",
    M("facts") + """
        if (known.version != belief.version || known.fastest_strength != strength)
            known.version = belief.version, known.fastest_strength = strength, known.fastest = fastest_clear(world, g, strength);
        // Ren's for the rated prunes""")
sub("""        auto& steps_known = steps_data[g];
        if (steps_known < 0) {""",
    M("fastest") + """
        auto& steps_known = steps_data[g];
        if (steps_known < 0) {""")
sub("""        int steps = steps_known;
        // The walk round live camps""",
    M("steps") + """
        int steps = steps_known;
        // The walk round live camps""")
sub("""        float toll = 0;
        if (steps == unreachable && map.any_group_hop()) {""",
    M("least") + """
        float toll = 0;
        if (steps == unreachable && map.any_group_hop()) {""")
sub("""        const bool walked = steps == steps_known;
        if (walked) {""",
    M("hops") + """
        const bool walked = steps == steps_known;
        if (walked) {""")
sub("""        // The bounds against the best, past the reads whose kept state""",
    M("live") + """
        // The bounds against the best, past the reads whose kept state""")
sub("""        // A group still respawning when we would arrive costs the wait there.
        const int respawn = respawn_in(belief);""",
    M("bounds") + """
        // A group still respawning when we would arrive costs the wait there.
        const int respawn = respawn_in(belief);""")
sub("""        if (prunes(trip)) continue;
        // No known way""",
    """        if (prunes(trip)) continue;
        """ + M("via") + """
        // No known way""")
sub("""            const int waiting = fresh ? std::max(0, belief.respawn_round - round) : 0;""",
    M("claim_bound") + """
            const int waiting = fresh ? std::max(0, belief.respawn_round - round) : 0;""")
sub("""            const float health_left = health - std::max(0.0f, crew.output * static_cast<float>(working) - crew.delayed_damage);""",
    M("crew_work") + """
            const float health_left = health - std::max(0.0f, crew.output * static_cast<float>(working) - crew.delayed_damage);""")
sub("""            const CrewPlan plan = op ? plan_crew(world, crew_allies_now(), g, strength, expect, crew_cap(g)) : CrewPlan{};
            const float others = op ? plan.output - strength : crew.output;""",
    M("claim_mid") + """
            const CrewPlan plan = op ? plan_crew(world, crew_allies_now(), g, strength, expect, crew_cap(g)) : CrewPlan{};
            """ + M("claim_plan") + """
            const float others = op ? plan.output - strength : crew.output;""")
sub("""            shared = g, shared_value = value, shared_steps = steps;""",
    M("claim_end") + """
            shared = g, shared_value = value, shared_steps = steps;""")
sub("""        const bool under_way = g == memory.farm_group && belief.awake != Awake::asleep;""",
    M("clear") + """
        const bool under_way = g == memory.farm_group && belief.awake != Awake::asleep;""")
sub("""        const int alone_trips = extra_trips(alone_damage, budget, usable_health);""",
    M("kited") + """
        const int alone_trips = extra_trips(alone_damage, budget, usable_health);""")
sub("""        float clear_rounds = alone_rounds, share = worth;""",
    M("quick") + """
        float clear_rounds = alone_rounds, share = worth;""")
sub("""        if (crewable) {
            // Allies claiming it and,""",
    M("value") + """
        if (crewable) {
            // Allies claiming it and,""")
sub("""            const CrewPlan plan = may_beat ? plan_crew(world, crew_allies_now(), g, strength, expect, crew_cap(g)) : CrewPlan{};
            if (may_beat && plan.output > strength && !too_late(plan.rounds)) {""",
    M("crew_bound") + """
            const CrewPlan plan = may_beat ? plan_crew(world, crew_allies_now(), g, strength, expect, crew_cap(g)) : CrewPlan{};
            """ + M("crew_plan") + """
            if (may_beat && plan.output > strength && !too_late(plan.rounds)) {""")
sub("""        if (g == memory.mono_group) mono_seen = value;
        if (late) continue;""",
    M("crew_end") + """
        if (g == memory.mono_group) mono_seen = value;
        if (late) continue;""")
sub("""    read_g = -1;
    if (k < evaluated) note_shortcut("farm-partial-evaluation");""",
"""    ls_end();
    ++lst.loops, lst.loop_fuel += ls_start - fuel();
    if (round / 100 != lst.printed) {
        lst.printed = round / 100;
        debug_block({
            std::printf("LS %%d %%u %%d %%llu %%llu %%llu %%llu", round, my_handle(), (int)banks_bag + 2 * (int)banking + 4 * (int)repricing + 8 * (int)opening, (unsigned long long)lst.loops, (unsigned long long)lst.loop_fuel,
                        (unsigned long long)lst.groups, (unsigned long long)lst.marks);
            for (int i = 0; i < %(N)d; ++i) std::printf(" %%llu %%llu", (unsigned long long)lst.seg[i], (unsigned long long)lst.cnt[i]);
            std::printf("\\nLX %%d %%u %%d", round, my_handle(), (int)banks_bag + 2 * (int)banking + 4 * (int)repricing + 8 * (int)opening);
            for (int i = 0; i < %(N)d; ++i) std::printf(" %%llu %%llu", (unsigned long long)lst.xn[i], (unsigned long long)lst.xf[i]);
            std::printf("\\n");
        });
    }
    read_g = -1;
    if (k < evaluated) note_shortcut("farm-partial-evaluation");""" % {"N": N})
p.write_text(s)
print("ok", N)
