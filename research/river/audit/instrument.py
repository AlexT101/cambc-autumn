"""Make an audit copy of river: bots/variants/<name> with src only, tracing for audit.py, farm_switches.py and
retreat_swaps.py. Every trace is in debug_block (refunded), so build without --release.

    python3 research/river/audit/instrument.py aud
    cambc build bots/variants/aud
    python3 tools/run_batched.py bots/variants/aud bots/astraeus --maps-dir <ladder> --one-side --output replays/aud

Lines (team stdout, capped at 1 MiB a team; the noisiest existing traces are silenced):
  AUD round index state from to d0 d1 n hash adv  every turn a state ends: the static walk distance from the
      turn's start (d0) and end (d1) to the goals of the turn's last movement call (n tiles, hash), and
      whether the move was made with an Advance set (1, 0; -1 no move by try_move).
  FG ...  a farm turn walking to another group than last farm turn's: how each fared (farm_switches.py).
  WH round index low pack trapped lethal seen cached hp  a turn that leaves (want_home's terms).
"""
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
name = sys.argv[1] if len(sys.argv) > 1 else "aud"
out = ROOT / "bots" / "variants" / name
if out.exists():
    shutil.rmtree(out)
out.mkdir(parents=True)
shutil.copytree(ROOT / "bots" / "river" / "src", out / "src")
src = out / "src"


def patch(path, old, new, count=1):
    p = src / path
    s = p.read_text()
    assert s.count(old) == count, (path, old[:60], s.count(old))
    p.write_text(s.replace(old, new))


(src / "audit.h").write_text('''// Audit tracing: the goals of the last movement call this turn.
namespace aph {
struct AuditRec {
    bitboard goals{cambc::uninitialized};
    bool have = false;
    int round = -1, adv = -1, adv_round = -1;
};
inline AuditRec& audit_rec() { static AuditRec a; return a; }
inline void audit_goals(const bitboard& g) {
    auto& a = audit_rec();
    a.round = cambc::round_number();
    copy_into(g, a.goals);
    a.have = true;
}
inline void audit_tile(vec2 p) {
    static bitboard one{cambc::uninitialized};
    clear_board(one);
    set_tile(one, p);
    audit_goals(one);
}
inline int audit_dist(const bitboard& walls, const bitboard& goals, vec2 p) {
    static bitboard open{cambc::uninitialized}, visited{cambc::uninitialized};
    static cambc::distance_field f;
    not_into(walls, open);
    open &= goals;
    if (board_empty(open)) return -2;
    (void)f.compute_with_expansion_count(walls, open, visited);
    const int d = steps_at(f, p);
    return d >= unreachable ? -1 : d;
}
}
''')
patch("unity.cpp", '#include "headers/log.inline.h"\n', '#include "audit.h"\n#include "headers/log.inline.h"\n')

# Silence the noisiest traces: the stdout cap would cut the audit lines.
for path, old in [("headers/comms.inline.h", 'std::printf("SHORTCUT '), ("headers/comms.inline.h", 'std::printf("DRS '),
                  ("map_info.inl", 'std::printf("SLOT '), ("champions/shared/turn.inl", 'std::printf("D %d %u %c'),
                  ("champions/shared/plan.inl", 'std::printf("SRCH ')]:
    patch(path, old, "if (0) " + old)
p = src / "headers/comms.inline.h"
p.write_text(p.read_text().replace('log("D %u %d ', 'if (0) log("D %u %d '))

# Goals of every movement entry point; the Advance flag of a move.
s = (src / "pathing.inl").read_text()


def after(s, head, anchor, ins):
    i = s.index(head)
    j = s.index(anchor, i) + len(anchor)
    return s[:j] + ins + s[j:]


s = after(s, "bool Pathing::step_towards(const bitboard& goals, const bitboard* avoid, int max_steps, std::optional<vec2> aim)",
          "    if (!my_can_move()) return false;\n", "    debug_block({ audit_goals(goals); });\n")
s = after(s, "bool Pathing::step_towards_funded(const bitboard& goals, std::uint64_t fuel_floor)",
          "    if (!my_can_move() || test(goals, my_pos())) return false;\n", "    debug_block({ audit_goals(goals); });\n")
s = after(s, "bool Pathing::descend(const Field& field, const bitboard* avoid, std::optional<vec2> aim)",
          "    if (!my_can_move()) return false;\n", "    debug_block({ audit_goals(field.goals); });\n")
s = after(s, "bool Pathing::step_closer(vec2 target, const bitboard* avoid, std::optional<vec2> aim)",
          "    if (!my_can_move()) return false;\n", "    debug_block({ audit_tile(target); });\n")
a = "        if (cambc::self().move_absolute(tile)) {\n            ::comms::moved(from);\n"
assert s.count(a) == 1
s = s.replace(a, a + "            debug_block({ audit_rec().adv = advance_ ? 1 : 0; audit_rec().adv_round = cambc::round_number(); });\n")
(src / "pathing.inl").write_text(s)

# AUD: one line per turn, from the state that ended it.
s = (src / "state.inl").read_text()
a = "    const auto ran = [&](const State& s) {\n        if (!s.run(t)) return false;\n"
assert s.count(a) == 1
s = s.replace(a, a + '''        debug_block({
            const vec2 to = my_position();
            auto& rec = audit_rec();
            const bool have = rec.have && rec.round == cambc::round_number();
            int n = 0; long h = 0, d0 = -3, d1 = -3;
            if (have) {
                const auto& m = t.world.map();
                for (int y = 0; y < m.height; ++y) for (int x = 0; x < m.width; ++x) if (test(rec.goals, {x, y})) h = (h * 31 + x * 977 + y) % 1000003, ++n;
                d0 = audit_dist(t.pathing.static_walls(), rec.goals, audit_from);
                d1 = audit_dist(t.pathing.static_walls(), rec.goals, to);
            }
            std::printf("AUD %d %d %s %d,%d %d,%d %ld %ld %d %ld %d\\n", t.world.round, t.world.me().index, s.name, audit_from.x, audit_from.y,
                        to.x, to.y, d0, d1, n, h, rec.adv_round == cambc::round_number() ? rec.adv : -1);
        });
''')
a = "void run_states(Turn& t, std::span<const State> states)\n"
i = s.index(a)
j = s.index("{\n", i) + 2
s = s[:j] + "    const vec2 audit_from = my_position();\n" + s[j:]
(src / "state.inl").write_text(s)

# WH: want_home's terms on a turn that leaves.
patch("champions/shared/steps.inl", "    t.leave = !t.mend && (t.home ? *t.home : want_home(world, t.pathing, t.safety, t.aims));\n",
      '''    t.leave = !t.mend && (t.home ? *t.home : want_home(world, t.pathing, t.safety, t.aims));
    debug_block({
        if (t.leave) {
            const vec2 here = my_position();
            const float health = my_health();
            const bool low = health < params::recall_health_fraction * my_max_health()
                             && health < (recall_unreachable(world, here) ? params::safe_recall_health_fraction : params::recall_health_fraction) * my_max_health()
                             && !finishing_camp(world);
            const bool pack = in_pack_zone_from(world, here) && !paying_soon(world, t.pathing);
            const bool trapped = camp_trapped(world, t.safety, here, health, t.aims.siege);
            std::printf("WH %d %d low %d pack %d trapped %d lethal %d seen %d cached %d hp %.0f\\n", world.round, world.me().index, low, pack,
                        trapped, t.safety.lethal(here), enemy_seen(world), t.home ? 1 : 0, (double)health);
        }
    });
''')

# FG: farm's target switches, with how the old and new targets fared this turn and last.
f = src / "champions/shared/farm.inl"
s = f.read_text()
a = "[[gnu::flatten]] bool farm(World& world, Pathing& pathing, Safety& safety, Aims& aims)"
i = s.index(a)
s = s[:i] + '''struct AuditGroup { int line = 0; int risky = -1; float value = 0, damage = 0, spare = 0, partner = 0; int engaged = 0, steps = -1, claimed = 0; };
inline std::array<AuditGroup, 64>& audit_groups() { static std::array<AuditGroup, 64> a; return a; }
inline std::array<AuditGroup, 64>& audit_groups_last() { static std::array<AuditGroup, 64> a; return a; }
inline void audit_remember() { audit_groups_last() = audit_groups(); }
inline int audit_last_line_of(int g) { const auto& x = audit_groups_last()[g]; return x.line ? x.line : (x.risky >= 0 ? -x.risky - 1 : -9); }
''' + s[i:]
i = s.index("    for (; k < evaluated && (fuel_ok(ample) || fuel_ok(loop_floor + loop_reserve())); ++k) {")
j = s.index('    if (k < evaluated) note_shortcut("farm-partial-evaluation");', i)
body = s[i:j].replace("continue;", '{ debug_block({ if (g >= 0 && g < 64) audit_groups()[g].line = __LINE__; }); continue; }')
s = s[:i] + '    debug_block({ for (auto& x : audit_groups()) x = AuditGroup{}; });\n' + body + s[j:]
a = "        if (damage > spare_health && !ally_engaged(world, g)) {\n            if (value > risky_value) risky = g, risky_value = value, risky_steps = steps;"
assert s.count(a) == 1
s = s.replace(a, '        debug_block({ if (g < 64) audit_groups()[g] = AuditGroup{0, (damage > spare_health && !ally_engaged(world, g)) ? 1 : 0, value, damage, '
              'spare_health, partner_output, ally_engaged(world, g) ? 1 : 0, steps, claimed ? 1 : 0}; });\n' + a)
a = "    if (best < 0) {\n        // Cut short before weighing even last turn's choice: walk on towards it."
assert s.count(a) == 1
s = s.replace(a, '''    debug_block({
        static int last_round = -9, last_final = -1;
        static AuditGroup last_prev{};
        static float last_hp = 0, last_recall = 0;
        const int pick = aims.claim == best && !aims.crew ? best : -2;
        const float hp = my_health(), rl = recall_line(world);
        if (last_round == round - 1 && last_final >= 0 && best >= 0 && best != last_final) {
            const auto& p = audit_groups()[last_final];
            const auto& b = audit_groups()[best];
            std::printf("FG %d %d %d %d %d %d %d | prev l%d r%d v%.3f d%.0f s%.0f p%.0f e%d c%d st%d | was r%d v%.3f d%.0f s%.0f p%.0f e%d c%d st%d | new r%d v%.3f st%d c%d was_new l%d | hp %.0f %.0f rl %.3f %.3f\\n",
                round, world.me().index, last_final, best, pick, shared, help_group,
                p.line, p.risky, (double)p.value, (double)p.damage, (double)p.spare, (double)p.partner, p.engaged, p.claimed, p.steps,
                last_prev.risky, (double)last_prev.value, (double)last_prev.damage, (double)last_prev.spare, (double)last_prev.partner, last_prev.engaged, last_prev.claimed, last_prev.steps,
                b.risky, (double)b.value, b.steps, b.claimed, audit_last_line_of(best), (double)last_hp, (double)hp, (double)last_recall, (double)rl);
        }
        last_round = round, last_final = best, last_hp = hp, last_recall = rl;
        if (best >= 0 && best < 64) last_prev = audit_groups()[best];
        audit_remember();
    });
''' + a)
f.write_text(s)
print(f"made {out}; build it with: cambc build {out.relative_to(ROOT)}")
