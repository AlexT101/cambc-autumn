"""Make a combat-lab copy of an ocean or astraeus bot directory: ./copybot, then the control block's hooks.

    python3 tools/combatlab/labify.py BOT DST     # e.g. baselines/v83 variants/lab-v83

BOT and DST are names under bots/. The copy gets src/lab.h (tools/combatlab/lab.h: the block, behind the
magic "CAMBC-LAB-BLK-1", that `fastrunner scenario --lab` reads and writes between turns) and hooks:
  - main.cc, util.h: per-turn output reset; the warm start (flag bit 0): on the instance's first turn, after
    the world update and map conditioning and before comms receive, the turn-end queue runs to completion
    (the tables around us to warm_radius), then aph::fuel reads, for the rest of that turn, what a normal
    100k turn has at that point (100k less warm_pre) until its decision ends; the instance's first round
    reads as 1.
  - bot.cc: the turn's branch (decide's `decision`).
  - fight.cc: want_home's verdict (forced by home_round/home_force), stand_lost_at's prediction, chase's
    target (forced by chase_round/chase_force: 0 no chase, 1 chase prey or else the nearest visible enemy).
  - plan.cc: each plan_strikes call's chosen candidate and score parts; the ban list (ban_round, ban_call).
  - bot.cc: forced actions (lab.h LabAct, fastrunner forkgame): ops run at the start of decide, then the world is
    re-read (see_again, see_stuns) and ocean plays the rest of the turn; op 7 skips act (the turn ends).
With flags 0 and no inputs set, the copy plays as BOT (checked by bundle identity). Each anchor must occur
exactly once, so a bot whose code moved fails loudly rather than being patched wrongly.
"""
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent


def sub(text, old, new, what, scope=None):
    """Replace the one occurrence of `old` (within the function starting at `scope`, if given)."""
    lo, hi = 0, len(text)
    if scope:
        if text.count(scope) != 1:
            sys.exit(f"labify: {what}: scope {scope[:60]!r} found {text.count(scope)} times")
        lo = text.index(scope)
        hi = text.index("\n}\n", lo) + 3
    part = text[lo:hi]
    # Alternatives (old, new) pairs: the first whose anchor occurs exactly once (the base's code moved between versions).
    alts = list(zip(old, new)) if isinstance(old, tuple) else [(old, new)]
    for o, n in alts:
        if part.count(o) == 1:
            return text[:lo] + part.replace(o, n) + text[hi:]
    sys.exit(f"labify: {what}: anchor {alts[0][0][:70]!r} found {part.count(alts[0][0])} times")


def patch(path, edits):
    s = path.read_text()
    for e in edits:
        s = sub(s, *e)
    path.write_text(s)


WARM = """        if (lab_on()) cambc_lab.pre_fuel = static_cast<std::uint32_t>(start - aph::fuel());
        if ((cambc_lab.flags & 1) && cambc_lab.warm_round < 0) {
            // The lab's warm start: a fresh instance fills the turn end's caches first, then is left
            // what a normal turn has here (as read: the host budget stays large), so that its fuel-gated
            // choices are a mid-game turn's.
            const std::uint64_t pre = cambc_lab.warm_pre ? cambc_lab.warm_pre : start - aph::fuel();
            const auto before = aph::fuel();
            queue.lab_radius = cambc_lab.warm_radius;
            run("lab warm", [&] { queue.run(*world, *pathing, memory, 0); });
            queue.lab_radius = 0;
            const auto after = aph::fuel();
            const std::uint64_t left = turn_fuel > pre ? turn_fuel - pre : 0;
            lab_fuel_offset = after > left ? after - left : 0;
            cambc_lab.warm_round = world->round;
            cambc_lab.warm_pre_used = start - before;
            cambc_lab.warm_fuel = before - after;
            cambc_lab.warm_offset = lab_fuel_offset;
            start = turn_fuel;
            late = false;
            // Not the game's start: the first-round paths (farm_turn<true>, the recall line, turn order) stay off.
            world->first_round = 1;
        }
"""

RECORD = """    if (chosen >= 0) seq = concrete(tiles[chosen]), dropped[tiles[chosen].c] = true;
    const int lab_first = chosen;
    if (lab_on()) {
        lab.status = chosen >= 0 ? 1 : 2;
        lab.capped = capped;
        lab.tiles = static_cast<std::int16_t>(nt);
        lab.queries = static_cast<std::int16_t>(queries);
        for (int i = 0; i < nt; ++i) {
            const int c = tiles[i].c;
            const vec2 tp = S.tile(c);
            lab.exact_tiles += tiles[i].exact;
            for (int keep = 0; keep < 2; ++keep) {
                if (!((keep ? S.kept_has : S.has) >> c & 1)) continue;
                const auto& fr = (keep ? plan_tables.kept : S.best)[c];
                for (int e = 0; e < fr.n; ++e) {
                    const bool b = lab_bans && lab_banned(tp.x, tp.y, keep == 1, fr.e[e].removed);
                    lab.banned += b;
                    lab.exact_cands += tiles[i].exact && !b;
                }
            }
        }
        if (chosen >= 0) {
            const auto& t = tiles[chosen];
            const vec2 p = S.tile(t.c);
            const auto& ch = (t.keep ? plan_tables.kept : S.best)[t.c].e[t.entry];
            auto& o = lab.c;
            o.x = static_cast<std::int16_t>(p.x), o.y = static_cast<std::int16_t>(p.y);
            o.removed = ch.removed;
            o.keep = t.keep, o.entry = t.entry;
            o.raw = ch.raw, o.shield = t.keep ? t.shield : 0.0f, o.camp = camp_at(p), o.gain = t.gain, o.total = t.total;
            o.danger = o.raw + o.shield + o.gain - o.camp - o.total;
            o.price = 0;
            for (int k = 0; k < seq.n && k < 8; ++k) {
                o.ops[k] = "wardchs"[static_cast<int>(seq.a[k].op)];
                if (seq.a[k].op == Op::spell) o.price += cast_cost;
                if (seq.a[k].op == Op::dash) o.price += S.dash_cost;
            }
        }
    }
"""

CHASE = """    const auto* target = prey(world, safety);
    if (cambc_lab.chase_round == world.round && cambc_lab.chase_force >= 0) {
        if (!cambc_lab.chase_force) target = nullptr;
        else if (!target) {
            int best = 1 << 20;
            for (const auto& e : world.enemies)
                if (e.alive && e.visible && dist(my_position(), e.pos) < best) best = dist(my_position(), e.pos), target = &e;
        }
    }
    if (lab_on()) cambc_lab.chase = target != nullptr, cambc_lab.chase_target = target ? static_cast<std::uint32_t>(target->handle) : 0;
    if (!target) return false;"""

WANT = "bool want_home(const World& world, Pathing& pathing, Safety& safety, const Memory& memory) {"
WANT_WRAP = WANT.replace("want_home(", "want_home_impl(").replace(" {", ";") + "\n" + WANT + """
    if (lab_on()) cambc_lab.stand.verdict = -1;
    const bool verdict = want_home_impl(world, pathing, safety, memory);
    const bool forced = cambc_lab.home_round == world.round && cambc_lab.home_force >= 0;
    if (lab_on()) cambc_lab.home_impl = verdict, cambc_lab.home = forced ? cambc_lab.home_force != 0 : verdict;
    return forced ? cambc_lab.home_force != 0 : verdict;
}

""" + WANT.replace("want_home(", "want_home_impl(")

STAND = "bool stand_lost_at(const World& world, Safety& safety, HoldAt& hold) {"


def main():
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    src, dst = sys.argv[1], sys.argv[2]
    subprocess.run([sys.executable, str(ROOT / "copybot"), src, dst], check=True)
    d = ROOT / "bots" / dst.removeprefix("bots/") / "src"
    shutil.copy(HERE / "lab.h", d / "lab.h")
    patch(d / "util.h", [
        ("#include <cambc.h>\n", '#include <cambc.h>\n#include "lab.h"\n', "util.h include"),
        ("inline std::uint64_t fuel() { return static_cast<std::uint64_t>(cambc::detail::sdk_fuel_remaining()); }",
         "inline std::uint64_t fuel() {\n    const auto raw = static_cast<std::uint64_t>(cambc::detail::sdk_fuel_remaining());\n"
         "    return raw > lab_fuel_offset ? raw - lab_fuel_offset : 0;\n}", "fuel reading"),
    ])
    patch(d / "main.cc", [
        ("        const auto start = aph::fuel();\n        aph::FuelMeter meter{\"turn\"};",
         "        lab_fuel_offset = 0;\n        auto start = aph::fuel();\n        lab_begin_turn();\n        aph::FuelMeter meter{\"turn\"};", "turn start"),
        ("    bool map_warmed_up = false, warmed_up = false, foot_warmed = false, clears_warmed = false;\n",
         "    bool map_warmed_up = false, warmed_up = false, foot_warmed = false, clears_warmed = false;\n    int lab_radius = 0;\n", "queue radius"),
        ("        if (me.pos.x >= 0) around(me.pos, me.alive ? aph::vision_radius : 20);",
         "        if (me.pos.x >= 0) around(me.pos, lab_radius > 0 ? lab_radius : me.alive ? aph::vision_radius : 20);", "queue around"),
        ("        // Decided in its own round, the turn end is abandoned as usual if it runs out.\n",
         "        // A warm start's turn ends as a normal one: its cold first decision's excess is forgiven.\n        lab_fuel_offset = 0;\n"
         "        // Decided in its own round, the turn end is abandoned as usual if it runs out.\n", "warm turn end"),
        ('        run("comms receive", [&] { aph::comms::receive(*world); });',
         WARM + '        run("comms receive", [&] { aph::comms::receive(*world); });', "warm start"),
    ])
    # Forced actions (lab.h LabAct): run at the start of decide, then ocean plays the rest on a re-read world.
    bc = (d / "bot.cc").read_text()
    ACT = "    try {\n        act(world, pathing, safety, memory);\n    } catch (const StaleTurn&) {"
    if bc.count(ACT) == 1:
        bc = bc.replace(ACT, "    const int lab_forced = lab_act_run(world.round);\n    try {\n"
                        "        if (lab_forced & 1) see_again(world, pathing, safety), see_stuns(world, safety);\n"
                        "        if (!(lab_forced & 2)) act(world, pathing, safety, memory);\n    } catch (const StaleTurn&) {")
        (d / "bot.cc").write_text(bc)
    else:
        print("labify: no forced-action hook (bot.cc's act call not found): LabAct inputs are ignored")
    patch(d / "bot.cc", [
        ("    memory.round = world.round;\n",
         "    if (lab_on()) cambc_lab.round = world.round, cambc_lab.decision = static_cast<char>(decision);\n    memory.round = world.round;\n",
         "decision", "void play_turn(World& world, Pathing& pathing, Memory& memory) {"),
    ])
    patch(d / "combat" / "fight.cc", [
        (WANT, WANT_WRAP, "want_home"),
        ("    if (!enemy_seen(world) && !safety.unseen_may_hit_within(p, params::pursuit_steps)) return false;",
         "    if (!enemy_seen(world) && !safety.unseen_may_hit_within(p, params::pursuit_steps)) return lab_stand(1, false);",
         "stand 1", STAND),
        ("    if (hold.keeps_us(safety)) return false;", "    if (hold.keeps_us(safety)) return lab_stand(2, false);", "stand 2", STAND),
        ("    if (roster.key == Safety::no_fight) return false;", "    if (roster.key == Safety::no_fight) return lab_stand(3, false);",
         "stand 3", STAND),
        ("    return t.lost || (falls && t.self_falls);",
         """    const bool lab_verdict = t.lost || (falls && t.self_falls);
    if (lab_on())
        cambc_lab.stand = {static_cast<std::int8_t>(lab_verdict), 4, static_cast<std::int8_t>(t.lost), static_cast<std::int8_t>(t.self_falls),
                           static_cast<std::int8_t>(falls), 0, static_cast<std::int16_t>(t.turns_to_kill_us),
                           static_cast<std::int16_t>(t.turns_to_kill_them)};
    return lab_verdict;""", "stand 4", STAND),
        ("    const auto* target = prey(world, safety);\n    if (!target) return false;", CHASE, "chase",
         "bool chase(const World& world, Pathing& pathing, Safety& safety) {"),
    ])
    PS = "[[gnu::flatten]] Planned plan_strikes(const World& world, Pathing& pathing, Safety& safety, const Intent& intent) {"
    patch(d / "combat" / "plan.cc", [
        (PS + "\n    Planned out;\n",
         PS + "\n    Planned out;\n    LabPlan& lab = lab_plan_begin(world.round, keep_only ? 'K' : std::exchange(lab_site, 'S'));\n"
         "    const bool lab_bans = lab_bans_on(world.round);\n", "plan begin"),
        (("    const int empty = strike_free(world, pathing, safety, intent, ready, ready_known);\n",
          "    const int empty = strike_free(world, pathing, safety, intent, ready);\n"),
         ("    const int empty = strike_free(world, pathing, safety, intent, ready, ready_known);\n    lab.early = static_cast<std::int8_t>(empty);\n",
          "    const int empty = strike_free(world, pathing, safety, intent, ready);\n    lab.early = static_cast<std::int8_t>(empty);\n"),
         "plan early", PS),
        ("                cand[k++] = {fr.e[i].raw, 0, fr.e[i].leaf, fr.e[i].removed, keep == 1, static_cast<std::int8_t>(i)};",
         "                if (!lab_bans || !lab_banned(S.tile(c).x, S.tile(c).y, keep == 1, fr.e[i].removed))\n"
         "                    cand[k++] = {fr.e[i].raw, 0, fr.e[i].leaf, fr.e[i].removed, keep == 1, static_cast<std::int8_t>(i)};",
         "plan bans", PS),
        ("        const float base = t.gain - camp;\n        const int nk = gather(t.c);\n",
         "        const float base = t.gain - camp;\n        const int nk = gather(t.c);\n        if (lab_bans && nk == 0) continue;\n",
         "plan banned tile", PS),
        ("            if (t.done || dist(p, here) == grid_r) continue;\n            const int nk = gather(t.c);\n",
         "            if (t.done || dist(p, here) == grid_r) continue;\n            const int nk = gather(t.c);\n"
         "            if (lab_bans && nk == 0) continue;\n", "plan banned capped tile", PS),
        ("    if (chosen >= 0) seq = concrete(tiles[chosen]), dropped[tiles[chosen].c] = true;\n", RECORD, "plan record", PS),
        ("    pathing.restore_guard(guard);\n    world.throw_if_stale();\n",
         "    pathing.restore_guard(guard);\n    lab.replanned = chosen != lab_first;\n    world.throw_if_stale();\n", "plan replanned", PS),
        ("    return plan_strikes(world, pathing, safety, stay);", "    lab_site = 'P';\n    return plan_strikes(world, pathing, safety, stay);",
         "strike_after site"),
    ])
    print(f"labify: bots/{dst.removeprefix('bots/')} made from bots/{src.removeprefix('bots/')}")


main()
