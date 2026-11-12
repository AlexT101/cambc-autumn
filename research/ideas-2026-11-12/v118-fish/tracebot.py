"""v118's trace bot: bots/baselines/v118/src plus read-only decision logging, as release code.

    py research/ideas-2026-11-12/v118-fish/tracebot.py [--out replays/v118/trace-bot] [--refund 2] [--no-extra]

tools/replay/harness/live_trace_bot.py ported to v118's source (its chase_trade call site differs), with lines added
for this study. Every line runs inside fc_block (a fuel-paused window that flushes stdout and refunds its own cost),
so the bot plays the release build's code; direct_batch.py then keeps each game only through the round before its
first difference from the live replay.

Lines (all fields integers unless noted; handles are champion ids):
  D   r h branch farm_group claim                       the turn's branch (bot_parts.h Branch)
  CS  ...                                               stand verdict (live_trace_bot.inc cal_print)
  CC  ...                                               chase verdict
  HG  r h x y hp branch priced | e:d:strike:blow:stuns  visible enemies whose strike reaches our end tile
  TT  r h sx sy ex ey hp maxhp gems gold branch score_us score_them alive winning   one per turn, at its end
  EB  r h e visible tracked x y pos_round hp maxhp str foc gems shield              our belief of each living enemy,
                                                        seen or tracked, at the turn's end
  WH  r h x y code     want_home's answer and first reason: 0 no, 1 low health under the recall line, 2 pack zone,
                       3 camp trap, 4 camp_fled, 5 Willow exposed, 6 finish_heal or a lost stand (a CS line precedes)
  CR  r h home bits    continue_recall's home-keep test on a running recall: bits 1 walk beats recall, 2 threatened here,
                       4 can tribute safely, 8 recall outruns (only the tests the short-circuit reached; seen mask << 8)
  CX  r h home         the recall was cancelled (no keep applied)
  ST  r h x y lost self_falls turns_to_kill_us turns_to_kill_them allies enemies falls pursued unseen hit key walking
                       stand_lost_at's verdict at (x, y) (--no-cal; key: ally bits low 16, enemy bits high 16, by index)
  CT  r h target tx ty lost self_falls tku tkt i key delayed late      prey's chase verdict on a target (--no-cal)
"""
import argparse, shutil, sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
HARNESS = REPO / "tools/replay/harness"
ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
ap.add_argument("--src", default=str(REPO / "bots/baselines/v118/src"))
ap.add_argument("--out", default=str(REPO / "replays/v118/trace-bot"))
ap.add_argument("--refund", type=int, default=2, help="fuel each fc_block refunds")
ap.add_argument("--note-refund", type=int, default=2, help="fuel each fc_note (a recorded condition) refunds")
ap.add_argument("--no-extra", action="store_true", help="only live_trace_bot.py's lines (CS, CC, HG, D)")
ap.add_argument("--no-cal", action="store_true", help="no CS / CC lines")
ap.add_argument("--no-st", action="store_true", help="no ST / CT lines (they cost ~11 fuel a call beyond any refund: 1 of 6 test games left the live game with them)")
ap.add_argument("--st-refund", type=int, default=2, help="fuel the ST block refunds")
ap.add_argument("--ct-refund", type=int, default=2, help="fuel the CT block refunds")
ap.add_argument("--no-hg", action="store_true", help="no HG lines")
a = ap.parse_args()
src, out = Path(a.src), Path(a.out)
if out.exists():
    shutil.rmtree(out)
shutil.copytree(src, out / "src")
s = out / "src"


def sub(rel, old, new, count=1):
    p = s / rel
    t = p.read_text()
    n = t.count(old)
    if n != count:
        sys.exit(f"{rel}: {n} matches for {old[:70]!r}, want {count}")
    p.write_text(t.replace(old, new))


B = "fc_block"
if not a.no_cal: sub("combat/fight.cc", "    const auto t = safety.stand_trade(roster, falls);\n",
    "    const auto t = safety.stand_trade(roster, falls);\n"
    "    " + B + "({ safety.cal_stand(p, roster, falls, t, (pursued ? 1 : 0) | (unseen ? 2 : 0) | (reach.hit ? 4 : 0)); });\n")
if not a.no_cal: sub("combat/fight.cc", "            t = safety.chase_trade(key, delayed, cooldowns, cast_available, linked, late);\n",
    "            t = safety.chase_trade(key, delayed, cooldowns, cast_available, linked, late);\n"
    "            " + B + "({ safety.cal_chase(target.pos, key, delayed, cooldowns, cast_available, linked, late, 0, t, static_cast<int>(target.handle), i); });\n")
sub("model/safety.h", "    Trade stand_trade(const StandRoster& r, bool falls);\n",
    "    Trade stand_trade(const StandRoster& r, bool falls);\n"
    "    void cal_stand(vec2 p, const StandRoster& r, bool falls, const Trade& t, int flags);\n"
    "    void cal_chase(vec2 p, std::uint32_t key, std::uint32_t delayed, const std::array<int, 2>& self_cooldowns, bool can_cast, bool falls,\n"
    "                   std::uint32_t late, float boost, const Trade& t, int target, int flags);\n")
D_OLD = 'debug_block({ std::printf("D %d %u %c %d %d\\n", world.round, static_cast<std::uint32_t>(world.me().handle), static_cast<char>(decision), memory.farm_group, memory.claim); });\n'
D_NEW = D_OLD.replace("debug_block", B, 1)
HG = (
    "    " + B + "({\n"
    "        static std::size_t hg_bytes = 0;\n"
    "        if (world.me().alive && hg_bytes < 1500000) {\n"
    "            const vec2 p = my_position();\n"
    "            int n = 0, k = 0;\n"
    "            for (const auto& e : world.enemies) {\n"
    "                if (!e.alive || !e.visible) continue;\n"
    "                const int d = dist(p, e.pos);\n"
    "                const float at = safety.strike_of(e).at(d);\n"
    "                if (!(at > 0)) continue;\n"
    "                if (!k++) n += std::printf(\"HG %d %u %d %d %d %c %d |\", world.round, static_cast<std::uint32_t>(world.me().handle), p.x, p.y, static_cast<int>(my_health()), static_cast<char>(decision), static_cast<int>(search_priced_end()));\n"
    "                const Blow b = safety.blow(e, p);\n"
    "                n += std::printf(\" %u:%d:%d:%d:%d\", static_cast<std::uint32_t>(e.handle), d, static_cast<int>(at), static_cast<int>(b.damage), static_cast<int>(b.stuns));\n"
    "            }\n"
    "            if (k) n += std::printf(\"\\n\");\n"
    "            hg_bytes += static_cast<std::size_t>(n);\n"
    "        }\n"
    "    });\n")
TT = (
    "    " + B + "({\n"
    "        static std::size_t tt_bytes = 0;\n"
    "        if (tt_bytes < 6000000) {\n"
    "            const auto& me = world.me();\n"
    "            const vec2 p = me.alive ? my_position() : vec2{-1, -1};\n"
    "            const int bag = me.alive ? static_cast<int>(my_gems()) : 0;\n"
    "            int n = std::printf(\"TT %d %u %d %d %d %d %d %d %d %d %c %d %d %d %d\\n\", world.round, static_cast<std::uint32_t>(me.handle),\n"
    "                                world.turn_start.x, world.turn_start.y, p.x, p.y, me.alive ? static_cast<int>(my_health()) : 0,\n"
    "                                me.alive ? static_cast<int>(my_max_health()) : 0, bag, static_cast<int>(my_gold()), static_cast<char>(decision),\n"
    "                                world.score.ally, world.score.enemy, static_cast<int>(me.alive), static_cast<int>(me.alive && winning_bag(world)));\n"
    "            if (me.alive)\n"
    "                for (const auto& e : world.enemies) {\n"
    "                    if (!e.alive || !(e.visible || e.tracked)) continue;\n"
    "                    n += std::printf(\"EB %d %u %u %d %d %d %d %d %d %d %d %d %d %d\\n\", world.round, static_cast<std::uint32_t>(me.handle),\n"
    "                                     static_cast<std::uint32_t>(e.handle), static_cast<int>(e.visible), static_cast<int>(e.tracked), e.pos.x, e.pos.y,\n"
    "                                     e.pos_round, static_cast<int>(e.health), static_cast<int>(e.max_health), static_cast<int>(e.strength),\n"
    "                                     static_cast<int>(e.focus), e.gems, static_cast<int>(e.shield));\n"
    "                }\n"
    "            tt_bytes += static_cast<std::size_t>(std::max(0, n));\n"
    "        }\n"
    "    });\n")
sub("bot.cc", "    " + D_OLD, "    " + D_NEW + ("" if a.no_hg else HG) + ("" if a.no_extra else TT))

if not a.no_extra:
    # The stand and chase verdicts from the values the bot already holds: cal_stand / cal_chase (CS / CC) play the
    # fight again and change v118's later answers (3 of 6 test games left the live game; without them 6 of 6 exact).
    if a.no_cal and not a.no_st:
        sub("combat/fight.cc", "    const auto t = safety.stand_trade(roster, falls);\n",
            "    const auto t = safety.stand_trade(roster, falls);\n"
            "    " + "fc_block_r(" + str(a.st_refund) + ", " + '{ std::printf("ST %d %u %d %d %d %d %d %d %d %d %d %d %d %d %u %u\\n", world.round, my_handle(), p.x, p.y, static_cast<int>(t.lost), static_cast<int>(t.self_falls), '
            "t.turns_to_kill_us, t.turns_to_kill_them, t.allies, t.enemies, static_cast<int>(falls), static_cast<int>(pursued), static_cast<int>(unseen), reach.hit ? 1 : 0, roster.key, roster.walking); });\n")
        sub("combat/fight.cc", "            t = safety.chase_trade(key, delayed, cooldowns, cast_available, linked, late);\n",
            "            t = safety.chase_trade(key, delayed, cooldowns, cast_available, linked, late);\n"
            "            " + "fc_block_r(" + str(a.ct_refund) + ", " + '{ std::printf("CT %d %u %u %d %d %d %d %d %d %d %u %u %u\\n", world.round, my_handle(), static_cast<std::uint32_t>(target.handle), target.pos.x, target.pos.y, '
            "static_cast<int>(t.lost), static_cast<int>(t.self_falls), t.turns_to_kill_us, t.turns_to_kill_them, i, key, delayed, late); });\n")
    # want_home: the answer and its first reason.
    wh = lambda code: B + '({ std::printf("WH %d %u %d %d ' + str(code) + '\\n", world.round, my_handle(), here.x, here.y); });'
    sub("combat/fight.cc",
        "    HoldAt hold(world, pathing, here, memory.damage);\n    if (drawn_home(world, safety, hold)) return true;\n",
        "    HoldAt hold(world, pathing, here, memory.damage);\n"
        "    if (drawn_home(world, safety, hold)) {\n"
        "        " + B + '({ std::printf("WH %d %u %d %d %d\\n", world.round, my_handle(), here.x, here.y, fc_drawn); });\n'
        "        return true;\n    }\n")
    sub("combat/fight.cc",
        "    if (mono >= 0 ? mono == 1 : camp_trapped(world, pathing, safety, here, health, memory.siege)) return true;\n",
        "    if (mono >= 0 ? mono == 1 : camp_trapped(world, pathing, safety, here, health, memory.siege)) {\n        " + wh(3) + "\n        return true;\n    }\n")
    sub("combat/fight.cc",
        "    if (memory.camp_fled >= 0 && !memory.siege) return true;\n    // Willow holds no fight: an enemy likely",
        "    if (memory.camp_fled >= 0 && !memory.siege) {\n        " + wh(4) + "\n        return true;\n    }\n    // Willow holds no fight: an enemy likely")
    sub("combat/fight.cc",
        "        && !willow_stands(world))\n        return true;\n    return finish_heal(world, pathing, safety) || stand_lost_at(world, safety, hold);\n",
        "        && !willow_stands(world)) {\n        " + wh(5) + "\n        return true;\n    }\n"
        "    const bool fc_home = finish_heal(world, pathing, safety) || stand_lost_at(world, safety, hold);\n"
        "    " + B + '({ std::printf("WH %d %u %d %d %d\\n", world.round, my_handle(), here.x, here.y, fc_home ? 6 : 0); });\n'
        "    return fc_home;\n")
    # drawn_home's two reasons, for want_home's line (drawn_home_at's callers read other tiles).
    sub("combat/fight.cc",
        "        && !finishing_camp(world, hold.p) && !hold.keeps_us(safety))\n        return true;\n    return outmatched(world, safety, hold) && !hold.keeps_us(safety);\n",
        "        && !finishing_camp(world, hold.p) && !hold.keeps_us(safety)) {\n        " + B + "({ fc_drawn = 1; });\n        return true;\n    }\n"
        "    " + B + "({ fc_drawn = 2; });\n"
        "    return outmatched(world, safety, hold) && !hold.keeps_us(safety);\n")
    # continue_recall's home keep: which tests the short-circuit reached and what they said.
    sub("economy/bank.cc",
        "    if (*home && !walk_beats_recall(world, pathing, safety, my_channel_time()) && !safety.threatened(my_position())\n"
        "        && !can_tribute_safely(world, pathing, safety, memory) && recall_outruns(safety))\n        return true;\n",
        "    " + B + "({ fc_cr = 0; });\n"
        "    if (*home && !fc_note(0, walk_beats_recall(world, pathing, safety, my_channel_time())) && !fc_note(1, safety.threatened(my_position()))\n"
        "        && !fc_note(2, can_tribute_safely(world, pathing, safety, memory)) && fc_note(3, recall_outruns(safety))) {\n"
        "        " + B + '({ std::printf("CR %d %u %d %d\\n", world.round, my_handle(), 1, fc_cr); });\n'
        "        return true;\n    }\n"
        "    " + B + '({ std::printf("CR %d %u %d %d\\n", world.round, my_handle(), static_cast<int>(*home), fc_cr); });\n')
    sub("economy/bank.cc",
        "    throw_if_stale();\n    try {\n        self_acted(), me.cancel_recall();\n    } catch (const std::exception&) {\n        return true;\n    }\n    return false;\n}\n\n// Carrying: chase a kill",
        "    " + B + '({ std::printf("CX %d %u %d\\n", world.round, my_handle(), static_cast<int>(*home)); });\n'
        "    throw_if_stale();\n    try {\n        self_acted(), me.cancel_recall();\n    } catch (const std::exception&) {\n        return true;\n    }\n    return false;\n}\n\n// Carrying: chase a kill")

(out / "RELEASE_CODE").write_bytes(b"")
guard = (
    "// A fuel-paused window for the trace lines in a release-code build (tools/replay/harness/live_trace_bot.py).\n"
    "__attribute__((import_module(\"env\"), import_name(\"fuel_pause\"))) int fc_fuel_pause();\n"
    "__attribute__((import_module(\"env\"), import_name(\"fuel_resume\"))) void fc_fuel_resume();\n"
    "__attribute__((import_module(\"env\"), import_name(\"fuel_adjust\"))) void fc_fuel_adjust(long long);\n"
    "__attribute__((import_module(\"env\"), import_name(\"fuel_remaining\"))) long long fc_fuel_remaining();\n"
    "struct FcGuard {\n"
    "    FcGuard() { fc_fuel_pause(); }\n"
    f"    ~FcGuard() {{ fc_fuel_adjust({a.refund}); fc_fuel_resume(); }}\n"
    "};\n"
    "#define fc_block(...) if (FcGuard _fc_guard{}; true) { __VA_ARGS__ std::fflush(stdout); } else (void)0\n"
    "struct FcGuardR {\n"
    "    long long r;\n"
    "    explicit FcGuardR(long long r) : r(r) { fc_fuel_pause(); }\n"
    "    ~FcGuardR() { fc_fuel_adjust(r); fc_fuel_resume(); }\n"
    "};\n"
    "#define fc_block_r(R, ...) if (FcGuardR _fc_guard{R}; true) { __VA_ARGS__ std::fflush(stdout); } else (void)0\n"
    "inline int fc_drawn = 0, fc_cr = 0;\n"
    "// Records a condition as the short-circuit reaches it: bit i its value, bit 8 + i that it was read.\n"
    "struct FcNoteGuard {\n"
    "    FcNoteGuard() { fc_fuel_pause(); }\n"
    f"    ~FcNoteGuard() {{ fc_fuel_adjust({a.note_refund}); fc_fuel_resume(); }}\n"
    "};\n"
    "[[gnu::always_inline]] inline bool fc_note(int i, bool v) {\n"
    "    if (FcNoteGuard g{}; true) fc_cr |= (static_cast<int>(v) << i) | (1 << (8 + i));\n"
    "    return v;\n"
    "}\n")
h = s / "model/safety.h"
ht = h.read_text()
i = ht.index("namespace aph")
h.write_text(ht[:i] + guard + "\n" + ht[i:])
p = s / "model/safety.cc"
t = p.read_text()
tail = "} // namespace aph\n"
assert t.endswith(tail)
p.write_text(t[: -len(tail)] + (HARNESS / "live_trace_bot.inc").read_text() + "\n" + tail)
print(f"{out}: trace bot from {src}, refund {a.refund}, note refund {a.note_refund}" + (", base lines only" if a.no_extra else ""))
