"""v118's trace bot: bots/baselines/v118/src plus logging in fuel-paused windows (tools/replay/harness/live_trace_bot.py's
method: a RELEASE_CODE build, so the bot plays its release code; each line inside pause / refund / resume).

    py research/ideas-2026-11-12/v118-fish-b/mktrace.py --out replays/v118b/trace-bot [--rich]

live_trace_bot.py itself stops on v118 (its chase_trade line has no `const auto`), so its lines are ported here:
  D   round handle branch farm_group claim                           (the bot's own line, every turn)
  CS / CC   the stand / chase verdict with margin and roster          (fishcal's lines, live_trace_bot.inc)
  HG  turn-end reach: each visible enemy whose strike reaches our end tile
--rich adds, all from plain reads or per-turn Safety queries:
  DX  round handle x y hp maxhp gems (at the turn's start) score_us score_them enemy_rate*1000 ally_rate*1000
      end_x end_y end_hp want_home_reason leave mend
      want_home_reason: 0 none, 1 drawn_home (recall line / pack zone), 2 camp trapped, 3 camp fled, 4 Willow exposed,
                        5 finish_heal, 6 stand lost, -1 want_home not asked this turn
  PX  round handle lethal_at_end_tile turns_to_kill_idle(end tile, 8)    (a Prism carrying 50+ gems only)
"""
import argparse, shutil, sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
HARNESS = REPO / "tools/replay/harness"
ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
ap.add_argument("--src", default=str(REPO / "bots/baselines/v118/src"))
ap.add_argument("--out", required=True)
ap.add_argument("--rich", action="store_true", help="every line")
ap.add_argument("--lines", default="d,cs,cc,hg", help="comma-separated of d (always), dx, tw (want_home's reason, in DX), px, hg, cs, cc; end: dx/px/hg from one noinline call in D's window")
ap.add_argument("--release-guard", type=int, default=2)
a = ap.parse_args()
src, out = Path(a.src), Path(a.out)
L = set("d,dx,tw,px,hg,cs,cc".split(",")) if a.rich else set(a.lines.split(","))
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


if "cs" in L:
    sub("combat/fight.cc", "    const auto t = safety.stand_trade(roster, falls);\n",
        "    const auto t = safety.stand_trade(roster, falls);\n"
        "    fc_block({ safety.cal_stand(p, roster, falls, t, (pursued ? 1 : 0) | (unseen ? 2 : 0) | (reach.hit ? 4 : 0)); });\n")
if "cc" in L:
    sub("combat/fight.cc", "            t = safety.chase_trade(key, delayed, cooldowns, cast_available, linked, late);\n",
        "            t = safety.chase_trade(key, delayed, cooldowns, cast_available, linked, late);\n"
        "            fc_block({ safety.cal_chase(target.pos, key, delayed, cooldowns, cast_available, linked, late, 0, t, static_cast<int>(target.handle), i); });\n")
if L & {"cs", "cc"}:
    sub("model/safety.h", "    Trade stand_trade(const StandRoster& r, bool falls);\n",
        "    Trade stand_trade(const StandRoster& r, bool falls);\n"
        "    void cal_stand(vec2 p, const StandRoster& r, bool falls, const Trade& t, int flags);\n"
        "    void cal_chase(vec2 p, std::uint32_t key, std::uint32_t delayed, const std::array<int, 2>& self_cooldowns, bool can_cast, bool falls,\n"
        "                   std::uint32_t late, float boost, const Trade& t, int target, int flags);\n")

D_OLD = 'debug_block({ std::printf("D %d %u %c %d %d\\n", world.round, static_cast<std::uint32_t>(world.me().handle), static_cast<char>(decision), memory.farm_group, memory.claim); });\n'
tail = ""
if "dx" in L:
    # Memory reads only (the turn-start record, the scores), plus one direct host read of our record into a local for the
    # end tile: the bot's cached accessors (my_position, my_gems, gems_short) are left alone. This form reproduced
    # 30 of 30 games; with the accessors it left the live game in half of them.
    tail += (
        "    fc_block({\n"
        "        const auto& m = world.me();\n"
        "        cambc::detail::champion_info rec{};\n"
        "        if (m.alive) cambc::detail::sdk_champion(my_handle(), &rec);\n"
        "        std::printf(\"DX %d %u %d %d %d %d %d %d %d %d %d %d %d %d %d %d %d\\n\", world.round, static_cast<std::uint32_t>(m.handle), m.pos.x, m.pos.y,\n"
        "                    static_cast<int>(m.health), static_cast<int>(m.max_health), m.gems, world.score.ally, world.score.enemy,\n"
        "                    static_cast<int>(1000 * world.enemy_rate()), static_cast<int>(1000 * world.ally_rate()), m.alive ? rec.x : -1, m.alive ? rec.y : -1,\n"
        "                    m.alive ? static_cast<int>(rec.health) : 0, fc_tw, fc_leave, fc_mend);\n"
        + ("        if (m.alive && m.facts().passive == Passive::gem_focus && m.gems >= 50 && !test(world.map().ally_spawn, vec2{rec.x, rec.y}))\n"
        "            std::printf(\"PX %d %u %d %d\\n\", world.round, static_cast<std::uint32_t>(m.handle), static_cast<int>(safety.lethal(vec2{rec.x, rec.y})), safety.turns_to_kill_idle(vec2{rec.x, rec.y}, 8));\n" if "px" in L else "") +
        "        fc_tw = -1; fc_leave = -1; fc_mend = -1;\n"
        "    });\n")
if "hg" in L:
    tail += (
        "    fc_block({\n"
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
if "end" in L:
    # One window a turn, as the D-only bot (which reproduces every game): the extra lines come from a noinline
    # function called inside the D line's window, so no second pause and nothing for the optimizer to hoist out of it.
    body = tail.replace("    fc_block({\n", "    {\n").replace("    });\n", "    }\n")
    sub("bot.cc", "void play_turn(World& world, Pathing& pathing, Memory& memory) {\n",
        "[[gnu::noinline]] void fc_end(const World& world, Safety& safety) {\n" + body + "}\n\n"
        "void play_turn(World& world, Pathing& pathing, Memory& memory) {\n")
    sub("bot.cc", D_OLD, D_OLD.replace("debug_block", "fc_block").replace("memory.claim); });", "memory.claim); fc_end(world, safety); });"))
else:
    sub("bot.cc", D_OLD, D_OLD.replace("debug_block", "fc_block") + tail)

if "tw" in L:
    sub("combat/fight.cc", "    if (drawn_home(world, safety, hold)) return true;\n    const int mono = mono_trapped(world, pathing, safety, memory, health);\n"
        "    if (mono >= 0 ? mono == 1 : camp_trapped(world, pathing, safety, here, health, memory.siege)) return true;\n",
        "    if (drawn_home(world, safety, hold)) { fc_note({ fc_tw = 1; }); return true; }\n    const int mono = mono_trapped(world, pathing, safety, memory, health);\n"
        "    if (mono >= 0 ? mono == 1 : camp_trapped(world, pathing, safety, here, health, memory.siege)) { fc_note({ fc_tw = 2; }); return true; }\n")
    sub("combat/fight.cc", "    if (memory.camp_fled >= 0 && !memory.siege) return true;\n",
        "    if (memory.camp_fled >= 0 && !memory.siege) { fc_note({ fc_tw = 3; }); return true; }\n")
    sub("combat/fight.cc", "        && !willow_stands(world))\n        return true;\n    return finish_heal(world, pathing, safety) || stand_lost_at(world, safety, hold);\n",
        "        && !willow_stands(world)) {\n        fc_note({ fc_tw = 4; });\n        return true;\n    }\n"
        "    if (finish_heal(world, pathing, safety)) { fc_note({ fc_tw = 5; }); return true; }\n"
        "    const bool fc_lost = stand_lost_at(world, safety, hold);\n    fc_note({ fc_tw = fc_lost ? 6 : 0; });\n    return fc_lost;\n")
    sub("bot.cc", "    if (leave && fixc_commit(world, pathing)) leave = false;\n",
        "    if (leave && fixc_commit(world, pathing)) leave = false;\n    fc_note({ fc_leave = leave; fc_mend = mend; });\n")

(out / "RELEASE_CODE").write_bytes(b"")
guard = (
    "// A fuel-paused window for the trace lines in a release-code build (mktrace.py, after live_trace_bot.py).\n"
    "__attribute__((import_module(\"env\"), import_name(\"fuel_pause\"))) int fc_fuel_pause();\n"
    "__attribute__((import_module(\"env\"), import_name(\"fuel_resume\"))) void fc_fuel_resume();\n"
    "__attribute__((import_module(\"env\"), import_name(\"fuel_adjust\"))) void fc_fuel_adjust(long long);\n"
    "__attribute__((import_module(\"env\"), import_name(\"fuel_remaining\"))) long long fc_fuel_remaining();\n"
    "// The bot's own-record caches (util.h: self_fresh, gems_fresh) are put back as the window found them: a trace read\n"
    "// that refreshed them would save the bot's next read its host call, and the re-run would leave the live game's fuel.\n"
    "struct FcGuard {\n"
    "    bool self, gems;\n"
    "    FcGuard() : self(aph::self_fresh), gems(aph::gems_fresh) { fc_fuel_pause(); }\n"
    f"    ~FcGuard() {{ aph::self_fresh = self; aph::gems_fresh = gems; fc_fuel_adjust({a.release_guard}); fc_fuel_resume(); }}\n"
    "};\n"
    "#define fc_block(...) if (FcGuard _fc_guard{}; true) { __VA_ARGS__ std::fflush(stdout); } else (void)0\n"
    "#define fc_note(...) if (FcGuard _fc_guard{}; true) { __VA_ARGS__ } else (void)0\n"
    "inline int fc_tw = -1, fc_leave = -1, fc_mend = -1;\n")
h = s / "model/safety.h"
ht = h.read_text()
i = ht.index("namespace aph")
h.write_text(ht[:i] + guard + "\n" + ht[i:])
if L & {"cs", "cc"}:
    p = s / "model/safety.cc"
    t = p.read_text()
    end = "} // namespace aph\n"
    assert t.endswith(end)
    p.write_text(t[: -len(end)] + (HARNESS / "live_trace_bot.inc").read_text() + "\n" + end)
print(f"{out}: trace bot from {src}, lines {','.join(sorted(L))}")
