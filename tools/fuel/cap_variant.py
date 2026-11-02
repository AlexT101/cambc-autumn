"""Copy a bot to bots/variants/<name>/ so that, run under a larger --fuel, it keeps the real budget.

The engine's --fuel applies to both teams. This copy charges the excess at the start of each fresh
budget through the debug-build import fuel_adjust (a negative delta charges; one call costs 2), so
the other bot gets the whole --fuel while this one plays as if at --cap. Debug builds only:
run_batched.py and ab.py never pass --release.

  py tools/fuel/cap_variant.py hyperion --run-fuel 10000000        # bots/variants/hyperion-cap100000-at10000000/
  py tools/ab.py main variants/hyperion-cap100000-at10000000 --fuel 10000000

Keep --run-fuel at or below ~30M: at 100M an instance that works and is charged every turn traps
("all fuel consumed") near round 1000 and the engine restarts it, losing its state. 10M is already
over 10x the costliest hyperion turn.

The charge comes after an out-of-fuel resume only once the bot's main loop notices it, so a resumed
remainder costing more than --cap runs on (real: it would run out again).
"""
import argparse
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

HEADER = """
// Inserted by tools/fuel/cap_variant.py: run under --fuel {run}, this copy keeps a {cap} budget.
#ifndef CAMBC_DEBUG
#error "fuel cap needs a debug build (fuel_adjust)"
#endif
namespace fuel_cap {{
constexpr std::int64_t run = {run}, cap = {cap};
inline std::int64_t left() {{ return cambc::detail::sdk_fuel_remaining(); }}
// The +3 here and +{first_refund} below refund the patch's own cost, measured against the unpatched bot.
inline void charge(std::int64_t turns) {{ cambc::detail::sdk_fuel_adjust(-(turns * (run - cap)) + 3); }}
// fuel_adjust never takes a turn's spending past one run-sized budget, so the rest of the first
// turn's excess (2x budget, 10x for the draft) is burnt to just below the target, then refunded.
// An instance the engine restarted after a trap starts on a 1x budget.
[[gnu::noinline]] void first_turn() {{
    const std::int64_t target = left() - (left() > run ? (cambc::is_draft() ? 10 : 2) : 1) * (run - cap);
    charge(1);
    volatile std::int64_t spin = 0;
    while (left() > target)
        for (int i = 0; i < 100; ++i) spin = spin + 1;
    cambc::detail::sdk_fuel_adjust(target - left() + {first_refund});
}}
}} // namespace fuel_cap

int main() {{
    fuel_cap::first_turn();
"""

FIRST_REFUND = 15

OOF = """            aph::note_shortcut("out-of-fuel");
            continue;"""
END = """        cambc::end_turn();
    }"""


def patch(source, run, cap):
    if source.count("int main() {") != 1 or source.count(OOF) != 1 or source.count(END) != 1:
        raise SystemExit("the main file no longer has the expected main loop; update cap_variant.py")
    source = source.replace("int main() {\n", HEADER.format(run=run, cap=cap, first_refund=FIRST_REFUND).lstrip("\n"), 1)
    source = source.replace(OOF, OOF.replace("continue;", "fuel_cap::charge(1);\n            continue;"), 1)
    return source.replace(END, END.replace("end_turn();", "end_turn();\n        fuel_cap::charge(1);"), 1)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("bot", help="Bot directory under bots/, or a path")
    parser.add_argument("--run-fuel", type=int, required=True, help="The --fuel the games will be run at")
    parser.add_argument("--cap", type=int, default=100_000, help="Budget this copy keeps (default 100000)")
    parser.add_argument("--name", help="Variant name (default <bot>-cap<cap>-at<run-fuel>)")
    args = parser.parse_args()
    if args.run_fuel <= args.cap:
        raise SystemExit("--run-fuel must exceed --cap")
    src = Path(args.bot) if Path(args.bot).is_dir() else ROOT / "bots" / args.bot
    name = args.name or f"{src.name}-cap{args.cap}-at{args.run_fuel}"
    dest = ROOT / "bots" / "variants" / name
    if dest.exists():
        shutil.rmtree(dest)
    shutil.copytree(src, dest, ignore=shutil.ignore_patterns(".cambc"))
    # astraeus builds one unity.cpp, which includes main.cc; other bots have main.cpp.
    main_cpp = next(p for p in (dest / "src" / "main.cpp", dest / "src" / "main.cc") if p.exists())
    main_cpp.write_text(patch(main_cpp.read_text(), args.run_fuel, args.cap), newline="\n")
    (dest / "manifest.json").write_text(json.dumps(
        {"source": str(src.relative_to(ROOT)) if src.is_relative_to(ROOT) else str(src),
         "run_fuel": args.run_fuel, "cap": args.cap}, indent=1) + "\n")
    print(dest.relative_to(ROOT))


if __name__ == "__main__":
    sys.exit(main())
