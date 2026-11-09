#!/usr/bin/env python3
"""Chase-verdict fuel checkpoints for a copy of ocean (debug builds only: all inside debug_block).

usage: cg_instrument.py SRC_DIR [--ref]
--ref: a bot without the verdict (oc-esc-merge): only the turn checkpoints.

Prints, per turn that finished in its round and reached chase_aim or asked a chase plan:
  CG <round> <handle> <ck> <branch> <aim> <aim_end> <search_end> <prey> <end> <n> [caller:at:cost]* <gated> <gated_at>
and per out-of-fuel turn, whatever it reached:
  CGO <round> <handle> <ck> <branch> <aim> <aim_end> <search_end> <prey> <phase> <n> [caller:at:cost]* <gated> <gated_at>
Fuel fields are the fuel left at that point (0 if not reached). ck is the last checkpoint passed:
1 decide, 2 chase_aim, 3 chase_aim done, 4 plan_strikes done, 5 search_strikes done, 6 prey (chase), 7 prey done,
8 retreat, 9 decide done, 10 act done, 11 turn order done.
Callers: 1 prey pressed, 2 prey team-pressed, 3 prey loop, 4 aim team-pressed, 5 aim engaged; +10 when prey is
continue_tribute's. trace_verdict is switched off, so debug builds ask the same plans as release ones."""
import sys, pathlib

src = pathlib.Path(sys.argv[1])
ref = "--ref" in sys.argv


def patch(rel, old, new, count=1):
    p = src / rel
    t = p.read_text()
    if t.count(old) == 0:  # chase_aim's asks with their own fuel need (the fuel gate's variants)
        for a, b in (("escapes(world, pathing, *t))", "escapes(world, pathing, *t, need))"),
                     ("escapes(world, pathing, *order[i].second))", "escapes(world, pathing, *order[i].second, need))")):
            old, new = old.replace(a, b), new.replace(a, b)
    n = t.count(old)
    if n != count:
        sys.exit(f"{rel}: pattern found {n} times, want {count}: {old[:80]!r}")
    p.write_text(t.replace(old, new))


patch("util.h", "\n} // namespace aph\n", r"""
struct CgBuild { std::uint32_t caller, at, cost; };
struct CgTurn {
    std::uint32_t round = 0;
    int ck = 0, branch = -1, caller = 0, ctx = 0, n = 0, gated = 0, aim_used = 0, aim_esc = 0, gated_caller = 0, prey_esc = 0, prey_sims = 0, prey_lost = 0;
    std::uint64_t sim_cost = 0;
    std::uint64_t aim = 0, aim_end = 0, search_end = 0, prey = 0, gated_at = 0;
    CgBuild b[8];
};
inline CgTurn& cg() { static CgTurn t; return t; }
inline bool cg_live() { return round_now() == cg().round; }
#define CGK(i) debug_block({ if (::aph::cg_live()) ::aph::cg().ck = (i); })
#define CGF(i, field) debug_block({ if (::aph::cg_live()) { ::aph::cg().ck = (i); ::aph::cg().field = ::aph::fuel(); } })
#define CGCALL(c) debug_block({ ::aph::cg().caller = (c); })
inline void cg_print(const char* tag, const char* last) {
    auto& t = cg();
    std::printf("%s %u %u %d %d %llu %llu %llu %llu %s %d", tag, t.round, my_handle(), t.ck, t.branch, (unsigned long long)t.aim,
                (unsigned long long)t.aim_end, (unsigned long long)t.search_end, (unsigned long long)t.prey, last, t.n);
    for (int i = 0; i < t.n; ++i) std::printf(" %u:%u:%u", t.b[i].caller, t.b[i].at, t.b[i].cost);
    std::printf(" %d %llu %d %d %d %d %d %d %llu\n", t.gated, (unsigned long long)t.gated_at, t.aim_used, t.aim_esc, t.gated_caller, t.prey_esc, t.prey_sims, t.prey_lost, (unsigned long long)t.sim_cost);
}

} // namespace aph
""")

patch("main.cc", """        const auto start = aph::fuel();
        aph::FuelMeter meter{"turn"};""", """        const auto start = aph::fuel();
        debug_block({ aph::cg() = {}; aph::cg().round = aph::round_now(); });
        aph::FuelMeter meter{"turn"};""")
patch("main.cc", """                std::printf("OOF %u %s\\n", round, aph::fuel_phase());""",
      """                std::printf("OOF %u %s\\n", round, aph::fuel_phase());
                if (aph::cg().round == round) aph::cg_print("CGO", aph::fuel_phase());""")
patch("main.cc", """            instance.play_turn(late);
        const bool finished_late""", """            instance.play_turn(late);
        debug_block({
            auto& t = aph::cg();
            if (!cambc::is_draft() && t.round == aph::round_now() && (t.aim || t.n || t.gated)) {
                char end[24];
                std::snprintf(end, sizeof end, "%llu", (unsigned long long)aph::fuel());
                aph::cg_print("CG", end);
            }
        });
        const bool finished_late""")

patch("bot.cc", """    const int claim = memory.claim;
    decide(world, pathing, safety, memory);""", """    const int claim = memory.claim;
    CGK(1);
    decide(world, pathing, safety, memory);
    CGK(9);""")
patch("bot.cc", """    if (!support_owned) start_recall(world);
    count_use(world, could_attack);
}""", """    if (!support_owned) start_recall(world);
    count_use(world, could_attack);
    CGK(10);
    debug_block({ if (::aph::cg_live()) ::aph::cg().branch = static_cast<int>(decision); });
}""")
patch("bot.cc", """        set_turn_order(world, safety);
    } catch (const StaleTurn&) {""", """        set_turn_order(world, safety);
        CGK(11);
    } catch (const StaleTurn&) {""")
aim_call = "chase_aim(world, safety)" if ref else "chase_aim(world, pathing, safety)"
patch("bot.cc", f"""    intent.aim = {aim_call};
    struck = searched = true;
    const auto planned = plan_strikes(world, pathing, safety, intent);""", f"""    CGF(2, aim);
    intent.aim = {aim_call};
    CGF(3, aim_end);
    struck = searched = true;
    const auto planned = plan_strikes(world, pathing, safety, intent);
    CGF(4, search_end);""")
patch("bot.cc", """    shield_if_needed(world, safety, memory.claim);
    return planned.attacked;""", """    shield_if_needed(world, safety, memory.claim);
    CGK(5);
    return planned.attacked;""")
patch("combat/fight.cc", """void retreat(World& world, Pathing& pathing, Safety& safety, Memory& memory) {
    world.throw_if_stale();""", """void retreat(World& world, Pathing& pathing, Safety& safety, Memory& memory) {
    CGK(8);
    world.throw_if_stale();""")

patch("combat/plan.cc", """    if (unguarded >= 2 && S.walks && in_bounds(intent.aim))
        for""", """    debug_block({ if (::aph::cg_live() && unguarded >= 2 && S.walks && in_bounds(intent.aim)) ::aph::cg().aim_used = 1; });
    if (unguarded >= 2 && S.walks && in_bounds(intent.aim))
        for""")
if ref:
    patch("combat/fight.cc", """    const auto* target = prey(world, safety);
    if (!target) return false;""", """    CGF(6, prey);
    const auto* target = prey(world, safety);
    CGK(7);
    if (!target) return false;""")
    sys.exit(0)

patch("combat/fight.cc", """    const auto* target = prey(world, pathing, safety);
    if (!target) return false;""", """    CGF(6, prey);
    const auto* target = prey(world, pathing, safety);
    CGK(7);
    if (!target) return false;""")
# trace_verdict builds a free plan in debug builds that a later ask would then find cached: off.
patch("combat/fight.cc", """void trace_verdict(const World& world, Pathing& pathing, const ChampionBelief& target, char tag) {
    debug_block({""", """void trace_verdict(const World& world, Pathing& pathing, const ChampionBelief& target, char tag) {
    if (true) return;
    debug_block({""")
patch("combat/fight.cc", """        if (const auto* t = team_pressed(world); t && preyable(world, safety, *t, here, range, held) && !escapes(world, pathing, *t))""",
      """        CGCALL(4);
        if (const auto* t = team_pressed(world); t && preyable(world, safety, *t, here, range, held) && !escapes(world, pathing, *t))""")
patch("combat/fight.cc", """    for (int i = 0; i < n; ++i)
        if (!escapes(world, pathing, *order[i].second)) {""", """    CGCALL(5);
    for (int i = 0; i < n; ++i)
        if (!escapes(world, pathing, *order[i].second)) {""")
patch("combat/fight.cc", """            return order[i].second->pos;
        }
    return aim;""", """            return order[i].second->pos;
        } else debug_block({ if (::aph::cg_live()) ++::aph::cg().aim_esc; });
    return aim;""")
patch("combat/fight.cc", """        if (preyable(world, safety, *p, here, range, held) && !escapes(world, pathing, *p)) return p;
    }
    // A teammate's pressed fight is joined as our own.""", """        CGCALL(1);
        if (preyable(world, safety, *p, here, range, held) && !escapes(world, pathing, *p)) return p;
    }
    // A teammate's pressed fight is joined as our own.""")
patch("combat/fight.cc", """        if (preyable(world, safety, *p, here, range, held) && !escapes(world, pathing, *p)) return p;
    }
    std::optional<float> strength;""", """        CGCALL(2);
        if (preyable(world, safety, *p, here, range, held) && !escapes(world, pathing, *p)) return p;
    }
    std::optional<float> strength;""")
patch("combat/fight.cc", """        if (escapes(world, pathing, target)) continue;""", """        CGCALL(3);
        if (escapes(world, pathing, target)) {
            debug_block({ if (::aph::cg_live()) ++::aph::cg().prey_esc; });
            continue;
        }""")
# The loop's fight sims: how many, how many lost, their fuel.
patch("combat/fight.cc", """        const auto t = safety.chase_trade(key, delayed, cooldowns, cast_available, linked, late, boost);""",
      """        std::uint64_t cg_f0 = 0;
        debug_block({ cg_f0 = ::aph::fuel(); });
        const auto t = safety.chase_trade(key, delayed, cooldowns, cast_available, linked, late, boost);
        debug_block({
            if (::aph::cg_live()) {
                auto& c = ::aph::cg();
                ++c.prey_sims, c.prey_lost += t.lost || (linked && t.self_falls), c.sim_cost += cg_f0 - ::aph::fuel();
            }
        });""")
patch("economy/bank.cc", """        && (winning_bag(world) || !prey(world, pathing, safety)))""",
      """        && (winning_bag(world) || [&] { debug_block({ ::aph::cg().ctx = 10; }); const bool p = prey(world, pathing, safety); debug_block({ ::aph::cg().ctx = 0; }); return !p; }()))""")
patch("model/escape.cc", """    if (!fuel_ok(need)) return nullptr;
    auto& p = plans[next];""", """    if (!fuel_ok(need)) {
        debug_block({ if (::aph::cg_live() && need > 0 && !::aph::cg().gated++) ::aph::cg().gated_at = ::aph::fuel(), ::aph::cg().gated_caller = ::aph::cg().caller + ::aph::cg().ctx; });
        return nullptr;
    }
    std::uint64_t cg_at = 0;
    debug_block({ cg_at = ::aph::fuel(); });
    auto& p = plans[next];""")
patch("model/escape.cc", """    p.build_chase(world, pathing, target);
    return &p;""", """    p.build_chase(world, pathing, target);
    debug_block({
        auto& t = ::aph::cg();
        if (::aph::cg_live() && need > 0 && t.n < 8)
            t.b[t.n++] = {static_cast<std::uint32_t>(t.caller + t.ctx), static_cast<std::uint32_t>(cg_at), static_cast<std::uint32_t>(cg_at - ::aph::fuel())};
    });
    return &p;""")
