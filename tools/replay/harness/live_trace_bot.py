"""A live version's trace bot: its exact source plus the combat lab's verdict logging (CS / CC lines with the margin,
HG turn-end reach lines), the noisiest debug traces muted.

    py tools/replay/harness/live_trace_bot.py --version v105              # -> replays/v105/trace-bot
    py tools/replay/harness/live_trace_bot.py --src SRC_DIR --out BOT_DIR [--debug-blocks] [--no-hg] [--no-d]

By default the bot builds as release code (a RELEASE_CODE marker: setup_ws.py's cmake patch drops CAMBC_DEBUG for it
even in a debug run), so it plays the release build's code, and only these lines run, each inside fc_block: a
fuel-paused window like DebugGuard's, declared here since the SDK declares the pause imports only under CAMBC_DEBUG.
On cambc 5.0.1 that reproduces 85% of v105's turns fuel-identically, where debug builds diverge (README, v105-v111).
--debug-blocks logs from ordinary debug blocks instead.

Ported from bots/variants/cal-dbg (oc-cl2-base): chase_trade here has no boost argument, so CC lines carry boost 0,
and cal_cap is raised from 150 kB to 3 MB per instance, since these runs have no 1 MiB log cap."""
import argparse, shutil, sys
from pathlib import Path

import versions

HERE = Path(__file__).resolve().parent
ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
ap.add_argument("--version", choices=list(versions.VERSIONS), help="source and output from the version's row")
ap.add_argument("--src", help="a bot's src/ directory")
ap.add_argument("--out", help="the trace bot directory to (re)create")
ap.add_argument("--release-guard", type=int, default=2, metavar="R",
                help="fuel each fc_block refunds (default %(default)s: cancels the window's own cost on cambc 5.0.1)")
ap.add_argument("--debug-blocks", action="store_true", help="debug_block logging, not release code")
ap.add_argument("--no-hg", action="store_true", help="no HG lines")
ap.add_argument("--no-d", action="store_true", help="leave the bot's own D line a debug block")
a = ap.parse_args()
if a.version:
    cfg = versions.get(a.version)
    if not cfg.src:
        sys.exit(f"{cfg.name} has no source directory (not a live version)")
    src, out = Path(a.src or cfg.src), Path(a.out or cfg.trace_bot)
elif a.src and a.out:
    src, out = Path(a.src), Path(a.out)
else:
    ap.error("give --version, or --src and --out")
NO_HG = a.no_hg
REL = None if a.debug_blocks else a.release_guard
BLOCK = "fc_block" if REL is not None else "debug_block"
if out.exists():
    shutil.rmtree(out)
shutil.copytree(src, out / "src")
s = out / "src"


def sub(rel, old, new, count=1):
    p = s / rel
    t = p.read_text()
    n = t.count(old)
    if n != count:
        sys.exit(f"{rel}: {n} matches for {old[:60]!r}, want {count}")
    p.write_text(t.replace(old, new))


sub("combat/fight.cc", "    const auto t = safety.stand_trade(roster, falls);\n",
    "    const auto t = safety.stand_trade(roster, falls);\n"
    "    " + BLOCK + "({ safety.cal_stand(p, roster, falls, t, (pursued ? 1 : 0) | (unseen ? 2 : 0) | (reach.hit ? 4 : 0)); });\n")
sub("combat/fight.cc", "        const auto t = safety.chase_trade(key, delayed, cooldowns, cast_available, linked, late);\n",
    "        const auto t = safety.chase_trade(key, delayed, cooldowns, cast_available, linked, late);\n"
    "        " + BLOCK + "({ safety.cal_chase(target.pos, key, delayed, cooldowns, cast_available, linked, late, 0, t, static_cast<int>(target.handle), i); });\n")
sub("combat/fight.cc", '                std::printf("CHASE-AVAIL', '                if (0) std::printf("CHASE-AVAIL')
sub("combat/fixc.cc", 'debug_block({ std::printf("FIXC-BUSHT', 'debug_block({ if (0) std::printf("FIXC-BUSHT')
sub("combat/plan.cc", '            std::printf("SRCH ', '            if (0) std::printf("SRCH ')
sub("economy/farm.cc", 'debug_block({ std::printf("CREW BAIL', 'debug_block({ if (0) std::printf("CREW BAIL')
sub("economy/farm.cc", 'debug_block({ std::printf("CREW JOIN', 'debug_block({ if (0) std::printf("CREW JOIN')
sub("economy/farm.cc", 'debug_block({ std::printf("CREW PROPOSE', 'debug_block({ if (0) std::printf("CREW PROPOSE')
sub("economy/farm.cc", '                std::printf("CREW GROUP', '                if (0) std::printf("CREW GROUP')
sub("economy/farm.cc", '            std::printf("CREW PICK', '            if (0) std::printf("CREW PICK')
sub("model/world.cc", '        std::printf("SLOT ', '        if (0) std::printf("SLOT ')
sub("model/safety.h", "    Trade stand_trade(const StandRoster& r, bool falls);\n",
    "    Trade stand_trade(const StandRoster& r, bool falls);\n"
    "    // fishcal: the verdict's margin and roster as a CS (stand) or CC (chase) line. Debug blocks only.\n"
    "    void cal_stand(vec2 p, const StandRoster& r, bool falls, const Trade& t, int flags);\n"
    "    void cal_chase(vec2 p, std::uint32_t key, std::uint32_t delayed, const std::array<int, 2>& self_cooldowns, bool can_cast, bool falls,\n"
    "                   std::uint32_t late, float boost, const Trade& t, int target, int flags);\n")
# HG: at the turn's end, each visible enemy whose strike reaches our tile: its strike.at(d) and blow(e, p), the
# terms the strike search prices at hit_given_reach. Joined offline with the damage it then deals us.
if not NO_HG: sub("bot.cc", "static_cast<char>(decision), memory.farm_group, memory.claim); });\n",
    "static_cast<char>(decision), memory.farm_group, memory.claim); });\n"
    "    " + BLOCK + "({\n"
    "        static std::size_t hg_bytes = 0;\n"
    "        if (world.me().alive && hg_bytes < 1500000) {\n"
    "            const vec2 p = my_position(); // world.me().pos is still the turn's start\n"
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
if REL is not None:
    (out / "RELEASE_CODE").write_bytes(b"")
    if not a.no_d: sub("bot.cc", 'debug_block({ std::printf("D %d %u %c %d %d\\n"', 'fc_block({ std::printf("D %d %u %c %d %d\\n"')
    guard = (
        "// fishcal: a fuel-paused window for the trace lines in a release-code build (live_trace_bot.py).\n"
        "__attribute__((import_module(\"env\"), import_name(\"fuel_pause\"))) int fc_fuel_pause();\n"
        "__attribute__((import_module(\"env\"), import_name(\"fuel_resume\"))) void fc_fuel_resume();\n"
        "__attribute__((import_module(\"env\"), import_name(\"fuel_adjust\"))) void fc_fuel_adjust(long long);\n"
        "__attribute__((import_module(\"env\"), import_name(\"fuel_remaining\"))) long long fc_fuel_remaining();\n"
        "// The pause still charges the window a constant; fuel_adjust refunds it (measured against the ladder's per-turn fuel).\n"
        "struct FcGuard {\n"
        "    FcGuard() { fc_fuel_pause(); }\n"
        f"    ~FcGuard() {{ fc_fuel_adjust({REL}); fc_fuel_resume(); }}\n"
        "};\n"
        "// stdout is flushed inside the window: left buffered, the turn's end would write it at full price.\n"
        "#define fc_block(...) if (FcGuard _fc_guard{}; true) { __VA_ARGS__ std::fflush(stdout); } else (void)0\n")
    h = s / "model/safety.h"
    ht = h.read_text()
    i = ht.index("namespace aph")
    h.write_text(ht[:i] + guard + "\n" + ht[i:])
p = s / "model/safety.cc"
t = p.read_text()
tail = "} // namespace aph\n"
assert t.endswith(tail)
p.write_text(t[: -len(tail)] + (HERE / "live_trace_bot.inc").read_text() + "\n" + tail)
print(f"{out}: trace bot from {src}" + (f", release guard {REL}" if REL is not None else ", debug blocks"))
