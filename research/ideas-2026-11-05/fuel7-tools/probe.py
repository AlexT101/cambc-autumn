"""probe.py SRC: instrument a copy's economy/farm.cc with the fuel round 7 farm-loop probe (debug_block lines).

Per group weighed in rounds 150-299: `LQ round handle g bank stage exit cost pre post m1..m5 flags`, where stage is
the last marker reached (0 start, 1 past the pre-facts bounds, 2 facts read, 3 steps known, 4 live_steps,
5 at prunes(trip), 6 past it), exit the `continue` taken past prunes(trip) (or '-'), cost the group's fuel, pre its
fuel up to prunes(trip), post after it, m1..m5 the fuel of the parts after prunes(trip) (clearing estimate,
claimed/kited/crew work, the quickest prune, the value with too_late and trips_home, the crew bound and plan), and
flags: c clearing estimate computed, p plan_crew called, r crew table read.
Per loop: `LQE round handle k evaluated bank loop_fuel best`.
"""
import re
import sys
from pathlib import Path

p = Path(sys.argv[1]) / "economy/farm.cc"
s = p.read_text()


def sub(old, new, count=1):
    global s
    n = s.count(old)
    if n != count:
        sys.exit(f"pattern found {n} times, wanted {count}: {old[:80]!r}")
    s = s.replace(old, new)


# the per-group record
sub("""    static CrewAllies crew_table;
    bool crew_read = false;
    const auto crew_allies_now = [&]() -> const CrewAllies& {
        if (!crew_read) crew_allies(world, line, crew_table), crew_read = true;""",
"""    struct Lq {
        int round = 0, g = -1, stage = 0;
        unsigned h = 0;
        bool bank = false, clr = false, plan = false, table = false;
        char exit = '-';
        std::uint64_t t0 = 0, t5 = 0, t6 = 0;
        std::uint64_t m[6] = {0, 0, 0, 0, 0, 0};
        std::uint64_t acc[8] = {0, 0, 0, 0, 0, 0, 0, 0};
        std::uint64_t last = 0;
        void at(int i) { const auto f = fuel(); m[i] += last - f; last = f; }
        void flush() {
            if (g < 0) return;
            const auto f = fuel();
            if (round >= 150 && round < 300)
                debug_block({ std::printf("LQ %d %u %d %d %d %c %llu %llu %llu %llu %llu %llu %llu %llu %llu %llu %llu %llu %llu %llu %llu %s%s%s\\n", round, h, g, (int)bank, stage, exit,
                                          (unsigned long long)(t0 - f), (unsigned long long)(t0 - (t5 ? t5 : f)), (unsigned long long)(t6 ? t6 - f : 0),
                                          (unsigned long long)m[1], (unsigned long long)m[2], (unsigned long long)m[3], (unsigned long long)m[4], (unsigned long long)m[5],
                                          (unsigned long long)acc[0], (unsigned long long)acc[1], (unsigned long long)acc[2], (unsigned long long)acc[3],
                                          (unsigned long long)acc[4], (unsigned long long)acc[5], (unsigned long long)acc[6],
                                          clr ? "c" : "", plan ? "p" : "", table ? "r" : ""); });
            g = -1;
        }
    } lq;
    static CrewAllies crew_table;
    bool crew_read = false;
    const auto crew_allies_now = [&]() -> const CrewAllies& {
        if (!crew_read) { const auto f0 = fuel(); crew_allies(world, line, crew_table), crew_read = true; lq.acc[0] += f0 - fuel(); }""")
sub("""    int k = 0;
    for (; k < evaluated && room(); ++k) {
        int g = order ? (*order)[k] : (first + k) % n_groups;""",
"""    int k = 0;
    const std::uint64_t lq_loop = fuel();
    for (; k < evaluated && room(); ++k) {
        lq.flush();
        int g = order ? (*order)[k] : (first + k) % n_groups;""")
sub("""            const auto crew = crew_work(op || crew_read ? &crew_allies_now() : nullptr, g, working, waiting);""",
"""            const auto lq_w = fuel();
            const auto crew = crew_work(op || crew_read ? &crew_allies_now() : nullptr, g, working, waiting);
            lq.acc[1] += lq_w - fuel();""")
sub("""            if (known.to_altar < 0) known.to_altar = pathing.centre_to_altar(g);
            const int last = known.to_altar;""",
"""            if (known.to_altar < 0) { const auto f0 = fuel(); known.to_altar = pathing.centre_to_altar(g); lq.acc[4] += f0 - fuel(); }
            const int last = known.to_altar;""")
sub("""            if (trip_home_rounds < 0) trip_home_rounds = home_trip(g, steps);""",
"""            if (trip_home_rounds < 0) { const auto f0 = fuel(); trip_home_rounds = home_trip(g, steps); lq.acc[5] += f0 - fuel(); }""")
sub("""            const int live = pathing.live_steps(g, belief.state != CampState::cleared ? range : 0);""",
"""            const auto lq_l = fuel();
            const int live = pathing.live_steps(g, belief.state != CampState::cleared ? range : 0);
            lq.acc[6] += lq_l - fuel();""")
sub("""            const CrewPlan plan = op ? plan_crew(world, crew_allies_now(), g, strength, expect, crew_cap(g)) : CrewPlan{};
            const float others = op ? plan.output - strength : crew.output;""",
"""            const auto lq_p = fuel();
            const CrewPlan plan = op ? plan_crew(world, crew_allies_now(), g, strength, expect, crew_cap(g)) : CrewPlan{};
            lq.acc[2] += lq_p - fuel();
            const float others = op ? plan.output - strength : crew.output;""")
sub("""            const CrewPlan plan = may_beat ? plan_crew(world, crew_allies_now(), g, strength, expect, crew_cap(g)) : CrewPlan{};
            if (may_beat && plan.output > strength && !too_late(plan.rounds)) {""",
"""            const auto lq_p = fuel();
            const CrewPlan plan = may_beat ? plan_crew(world, crew_allies_now(), g, strength, expect, crew_cap(g)) : CrewPlan{};
            lq.acc[2] += lq_p - fuel();
            if (may_beat && plan.output > strength && !too_late(plan.rounds)) {""")
sub("""                known.damage = min_camp_damage(world, g, strength, &known.rounds, reflect);
                if (group.strength > 0) known.kite = spell_clear_rounds(world, g, range, spells, basic);""",
"""                const auto f0 = fuel();
                known.damage = min_camp_damage(world, g, strength, &known.rounds, reflect);
                if (group.strength > 0) known.kite = spell_clear_rounds(world, g, range, spells, basic);
                lq.acc[3] += f0 - fuel();""")
# group start: after the stop logic
sub("""        if ((pre_pruned && barred()) || (pre_banked && best >= 0)) pre_bounds(g);""",
"""        lq = Lq{};
        lq.round = round, lq.g = g, lq.h = my_handle(), lq.bank = banks_bag, lq.t0 = fuel();
        if ((pre_pruned && barred()) || (pre_banked && best >= 0)) pre_bounds(g);""")
sub("""        const auto& group = group_data[g];
        const auto& belief = camp_data[g];
        read_g = -1, read_kited = kited_of(g)""",
"""        lq.stage = 1;
        const auto& group = group_data[g];
        const auto& belief = camp_data[g];
        read_g = -1, read_kited = kited_of(g)""")
sub("""        auto& known = group_facts[g];
        if (known.context != context || known.sticky != (g == farm_group)) {""",
"""        lq.stage = 2;
        auto& known = group_facts[g];
        if (known.context != context || known.sticky != (g == farm_group)) {""")
sub("""        auto& steps_known = steps_data[g];
        if (steps_known < 0) {""",
"""        lq.stage = 3;
        auto& steps_known = steps_data[g];
        if (steps_known < 0) {""")
sub("""        const bool walked = steps == steps_known;
        if (walked) {""",
"""        lq.stage = 4;
        const bool walked = steps == steps_known;
        if (walked) {""")
sub("""        if (prunes(trip)) continue;
        // No known way""",
"""        lq.stage = 5, lq.t5 = fuel();
        if (prunes(trip)) continue;
        lq.stage = 6, lq.t6 = lq.last = fuel();
        // No known way""")
# claimed branch
sub("""        if (claimed && !(group.has_monolith && belief.state == CampState::cleared)) {
            if (belief.state == CampState::cleared) continue;""",
"""        if (claimed && !(group.has_monolith && belief.state == CampState::cleared)) {
            if (belief.state == CampState::cleared) { lq.exit = 'a'; continue; }""")
sub("""                if (beaten_claimed(wins ? rate(world, worth, trip) : claim_bound(worth, health, health / (strength + others_claiming), trip))) continue;""",
"""                if (beaten_claimed(wins ? rate(world, worth, trip) : claim_bound(worth, health, health / (strength + others_claiming), trip))) { lq.table = crew_read, lq.at(2), lq.exit = 'b'; continue; }""")
sub("""            if (health <= 0 || health_left <= 0) continue;""",
"""            if (health <= 0 || health_left <= 0) { lq.table = crew_read, lq.at(2), lq.exit = 'c'; continue; }""")
sub("""                && beaten_claimed(claim_bound(worth, health, health_left / (strength + others_claiming), trip)))
                continue;""",
"""                && beaten_claimed(claim_bound(worth, health, health_left / (strength + others_claiming), trip))) {
                lq.table = crew_read, lq.at(2), lq.exit = 'd';
                continue;
            }""")
sub("""            lq.acc[2] += lq_p - fuel();
            const float others = op ? plan.output - strength : crew.output;""",
"""            lq.acc[2] += lq_p - fuel();
            lq.plan = op, lq.table = crew_read, lq.at(5);
            const float others = op ? plan.output - strength : crew.output;""")
sub("""            if ((value < shared_value || (value == shared_value && !earlier(g, shared))) || (best >= 0 && value <= best_value) || too_late(rounds))
                continue;""",
"""            if ((value < shared_value || (value == shared_value && !earlier(g, shared))) || (best >= 0 && value <= best_value) || too_late(rounds)) {
                lq.at(4), lq.exit = 'e';
                continue;
            }
            lq.at(4);""")
sub("""                if (hits > spare_health) continue;
            }
            shared = g, shared_value = value, shared_steps = steps;""",
"""                if (hits > spare_health) { lq.at(2), lq.exit = 'f'; continue; }
            }
            lq.exit = 'J';
            shared = g, shared_value = value, shared_steps = steps;""")
# clearing estimate
sub("""        if (known.clearing != clearing || known.clear_version != belief.version) {
            known.clearing = clearing, known.clear_version = belief.version;""",
"""        if (known.clearing != clearing || known.clear_version != belief.version) {
            lq.clr = true;
            known.clearing = clearing, known.clear_version = belief.version;""")
sub("""        const bool under_way = g == memory.farm_group && belief.awake != Awake::asleep;""",
"""        lq.at(1);
        const bool under_way = g == memory.farm_group && belief.awake != Awake::asleep;""")
# kited branch
sub("""                if (worth / (trip + quickest + capture) <= best_value
                    && (!banks_bag || worth / (static_cast<float>(walk_out) + cycle_bank + quickest + capture) <= from_altar_value))
                    continue;
            }
            float rounds = alone_rounds, damage = alone_damage;""",
"""                if (worth / (trip + quickest + capture) <= best_value
                    && (!banks_bag || worth / (static_cast<float>(walk_out) + cycle_bank + quickest + capture) <= from_altar_value)) {
                    lq.at(3), lq.exit = 'k';
                    continue;
                }
            }
            float rounds = alone_rounds, damage = alone_damage;""")
sub("""            if (cast) damage = 0, rounds = kite;
            if (too_late(rounds)) continue;""",
"""            if (cast) damage = 0, rounds = kite;
            if (too_late(rounds)) { lq.at(4), lq.exit = 'l'; continue; }""")
sub("""                if (value > risky_value || (value == risky_value && earlier(g, risky))) risky = g, risky_value = value, risky_steps = steps;
                continue;
            }""",
"""                if (value > risky_value || (value == risky_value && earlier(g, risky))) risky = g, risky_value = value, risky_steps = steps;
                lq.at(2), lq.exit = 'm';
                continue;
            }
            lq.at(2), lq.exit = value > best_value || (value == best_value && earlier(g, best)) ? 'N' : 'n';""")
# quickest prune
sub("""            if (worth / (trip + quickest + capture) <= bar_le()
                && (!banks_bag || worth / (static_cast<float>(walk_out) + cycle_bank + quickest + capture) <= from_altar_value))
                continue;
        }
        float clear_rounds = alone_rounds, share = worth;""",
"""            if (worth / (trip + quickest + capture) <= bar_le()
                && (!banks_bag || worth / (static_cast<float>(walk_out) + cycle_bank + quickest + capture) <= from_altar_value)) {
                lq.at(3), lq.exit = 'q';
                continue;
            }
        }
        lq.at(3);
        float clear_rounds = alone_rounds, share = worth;""")
sub("""        if (crewable) {
            // Allies claiming it and,""",
"""        lq.at(4);
        if (crewable) {
            // Allies claiming it and,""")
sub("""            const auto lq_p = fuel();
            const CrewPlan plan = may_beat ?""",
"""            lq.at(5);
            const auto lq_p = fuel();
            const CrewPlan plan = may_beat ?""")
sub("""            lq.acc[2] += lq_p - fuel();
            if (may_beat""",
"""            lq.acc[2] += lq_p - fuel();
            lq.plan = may_beat, lq.table = crew_read;
            if (may_beat""")
sub("""        if (g == memory.mono_group) mono_seen = value;
        if (late) continue;""",
"""        lq.at(5);
        if (g == memory.mono_group) mono_seen = value;
        if (late) { lq.exit = 'L'; continue; }
        lq.exit = value > best_value || (value == best_value && earlier(g, best)) ? 'B' : 'V';""")
sub("""    read_g = -1;
    if (k < evaluated) note_shortcut("farm-partial-evaluation");""",
"""    lq.flush();
    if (round >= 150 && round < 300)
        debug_block({ std::printf("LQE %d %u %d %d %d %llu %d\\n", round, my_handle(), k, evaluated, (int)banks_bag, (unsigned long long)(lq_loop - fuel()), best); });
    read_g = -1;
    if (k < evaluated) note_shortcut("farm-partial-evaluation");""")
p.write_text(s)
print("ok")
