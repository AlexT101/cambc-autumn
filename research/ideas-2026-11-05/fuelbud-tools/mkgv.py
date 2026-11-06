"""Gate-view oracle copies of an ocean bot (as EXPERIMENTS "What fuel is worth to astraeus").

  py mkgv.py BASE NAME FAMILY [FAMILY ...]     # bots/variants/NAME; FAMILY: base farm loop strike guard prey stand order queue

Run under --fuel 10000000 against `cap_variant.py BASE --run-fuel 10000000`. fuel() reads what the real budget would
leave, so every gate cuts as there, and a turn past it plays on. Each FAMILY puts one function under FreeFuel: inside
it fuel() reads the whole 10M; on leaving, what it spent is refunded to the view.
"""
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]

UTIL_OLD = "inline std::uint64_t fuel() { return static_cast<std::uint64_t>(cambc::detail::sdk_fuel_remaining()); }\n"
UTIL_NEW = """// Diagnostic copy (gate view): run under a large --fuel, every read sees what the real budget would
// leave, so gates cut as there, but a turn past it plays on instead of running out.
inline std::int64_t& fuel_view_offset() { static std::int64_t o = 0; return o; }
inline std::uint64_t fuel() {
    const std::int64_t r = static_cast<std::int64_t>(cambc::detail::sdk_fuel_remaining()) - fuel_view_offset();
    return r > 0 ? static_cast<std::uint64_t>(r) : 0;
}
// A family whose work is free: inside, fuel() reads the whole run budget; on leaving, what it spent is
// refunded to the view, so the rest of the turn reads as if it cost nothing.
inline int& free_fuel_depth() { static int d = 0; return d; }
inline std::int64_t& free_fuel_saved() { static std::int64_t o = 0; return o; }
struct FreeFuel {
    std::int64_t at = 0;
    FreeFuel() {
        if (free_fuel_depth()++ == 0) at = cambc::detail::sdk_fuel_remaining(), free_fuel_saved() = fuel_view_offset(), fuel_view_offset() = 0;
    }
    ~FreeFuel() {
        if (--free_fuel_depth() == 0) fuel_view_offset() = free_fuel_saved() - (at - static_cast<std::int64_t>(cambc::detail::sdk_fuel_remaining()));
    }
};
"""
MAIN_OLD = """        if (cambc::is_draft())
            instance.draft_turn();
        else
            instance.play_turn(late);
"""
MAIN_NEW = """        static bool first_turn = true;
        if (cambc::is_draft()) {
            aph::fuel_view_offset() = static_cast<std::int64_t>(cambc::detail::sdk_fuel_remaining()) - (first_turn ? 10000000 : 100000);
            first_turn = false;
            instance.draft_turn();
            aph::fuel_view_offset() = 0;
        } else {
            first_turn = false;
            static bool first_play = true;
            aph::fuel_view_offset() = static_cast<std::int64_t>(cambc::detail::sdk_fuel_remaining()) - (first_play ? 200000 : 100000);
            first_play = false;
            instance.play_turn(late);
            aph::fuel_view_offset() = 0;
        }
"""

# family: (file, anchor line, inserted after it); "loop" also closes its scope.
FAMILIES = {
    "farm": ("economy/farm.cc", "template <bool opening, bool banking, bool repricing> [[gnu::flatten]] bool farm_turn(World& world, Pathing& pathing, Safety& safety, Memory& memory) {\n", "    FreeFuel free_fuel;\n"),
    "strike": ("combat/plan.cc", "[[gnu::flatten]] Planned plan_strikes(const World& world, Pathing& pathing, Safety& safety, const Intent& intent) {\n", "    FreeFuel free_fuel;\n"),
    "guard": ("combat/guard.cc", "const bitboard* step_guard(const World& world, Safety& safety, vec2 here, int radius) {\n", "    FreeFuel free_fuel;\n"),
    "prey": ("combat/fight.cc", "const ChampionBelief* prey(const World& world, Safety& safety) {\n", "    FreeFuel free_fuel;\n"),
    "stand": ("combat/fight.cc", "bool stand_lost_at(const World& world, Safety& safety, HoldAt& hold) {\n", "    FreeFuel free_fuel;\n"),
    "order": ("model/turn_order.cc", "void set_turn_order(const World& world, Safety& safety) {\n", "    FreeFuel free_fuel;\n"),
    "queue": ("main.cc", "    void run(aph::World& world, aph::Pathing& pathing, const aph::Memory& memory, std::uint64_t start) {\n", "        aph::FreeFuel free_fuel;\n"),
}


def sub(path, old, new):
    s = path.read_text()
    if s.count(old) != 1:
        raise SystemExit(f"{path}: anchor found {s.count(old)} times")
    path.write_text(s.replace(old, new, 1))


def main():
    base, name, fams = sys.argv[1], sys.argv[2], sys.argv[3:]
    dest = ROOT / "bots" / "variants" / name
    subprocess.run([str(ROOT / "copybot"), "-f", base, f"variants/{name}"], check=True, cwd=ROOT)
    src = dest / "src"
    sub(src / "util.h", UTIL_OLD, UTIL_NEW)
    sub(src / "main.cc", MAIN_OLD, MAIN_NEW)
    for f in fams:
        if f == "base":
            continue
        if f.startswith("b") and f[1:].isdigit():  # the whole turn on a budget of f[1:] thousand
            sub(src / "main.cc", "(first_play ? 200000 : 100000)", f"(first_play ? {2 * int(f[1:])}000 : {f[1:]}000)")
            continue
        if f in ("loop", "loopbank", "loopnobank"):
            cond = {"loop": "", "loopbank": "if constexpr (banking) ", "loopnobank": "if constexpr (!banking) "}[f]
            p = src / "economy/farm.cc"
            sub(p, "    int k = 0;\n    for (; k < evaluated && room(); ++k) {\n",
                f"    std::optional<FreeFuel> loop_free; // diagnostic: the group loop is free\n    {cond}loop_free.emplace();\n"
                "    int k = 0;\n    for (; k < evaluated && room(); ++k) {\n")
            sub(p, "    read_g = -1;\n    if (k < evaluated) note_shortcut(\"farm-partial-evaluation\");\n",
                "    loop_free.reset();\n    read_g = -1;\n    if (k < evaluated) note_shortcut(\"farm-partial-evaluation\");\n")
            continue
        file, anchor, ins = FAMILIES[f]
        sub(src / file, anchor, anchor + ins)
    print(dest)


if __name__ == "__main__":
    main()
