"""A candidate astraeus from a dfit.mjs --dr selection (<model>.policy2.json): a copy of bots/astraeus whose learned
table is indexed [picks - 3][type][ordinal < 12][the current logic's pick family]. Cells the selection leaves at the
base keep the shipped table's arm (emblem_table.h, ordinals < 8) or the current logic.

    py tools/emblab/candidate.py replays/emblab/r2/dmodel-dr.policy2.json --key 1-1 --out bots/variants/astraeus-dr11
    py tools/emblab/candidate.py SELECTION --key 0-2 --flat --out bots/astraeus   # class 0: the table only

--flat (class 0 selections only): learned_arm[picks - 3][type][ordinal < 12], shop.cc unchanged, so the current logic's
choice is not computed up front (one current_emblem call fewer where a learned arm applies).
"""
import argparse
import json
import re
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TYPES = ["ryth", "vesper_vale", "vendetta", "cassi", "issac", "stellar", "prism", "marcella", "willow", "ren", "varg", "tavi", "heart_of_ruin"]
FAMILIES = ["monster", "power", "durability", "treasure", "jungle", "home", "bruiser", "tribute", "capture", "prospector",
            "hunter", "skirmish", "greed", "collectors"]
ORD, CURRENT = 12, 255

SHOP_OLD = """Emblem best_emblem(const World& world, const Build& bought = {}, const cambc::enum_map<cambc::item_type>* items = nullptr) {
    const int picks = economy_pick_count(world), type = static_cast<int>(world.me().type);
    if (!shopping || items || picks < 3 || picks > 5) return current_emblem(world, bought, items);
    const auto& owned = my_items();
    if (begun_emblem(world, owned)) return current_emblem(world, bought, items);
    unsigned ordinal = 0;
    for (int family = monster; family <= collectors; ++family)
        for (int stat = strength_stat; stat <= health_stat; ++stat) ordinal += owned[emblem_of(family, stat)];
    if (ordinal >= std::size(learned_arm[0][0])) return current_emblem(world, bought, items);
    const int arm = learned_arm[picks - 3][type][ordinal], family = arm / 3;
    if (arm == 255 || (family != power && family != bruiser && has_family(owned, family))) return current_emblem(world, bought, items);"""
SHOP_NEW = """Emblem best_emblem(const World& world, const Build& bought = {}, const cambc::enum_map<cambc::item_type>* items = nullptr) {
    const int picks = economy_pick_count(world), type = static_cast<int>(world.me().type);
    const Emblem current = current_emblem(world, bought, items);
    if (!shopping || items || picks < 3 || picks > 5) return current;
    const auto& owned = my_items();
    if (begun_emblem(world, owned)) return current;
    unsigned ordinal = 0;
    for (int family = monster; family <= collectors; ++family)
        for (int stat = strength_stat; stat <= health_stat; ++stat) ordinal += owned[emblem_of(family, stat)];
    if (ordinal >= std::size(learned_arm[0][0])) return current;
    const int arm = learned_arm[picks - 3][type][ordinal][current.family], family = arm / 3;
    if (arm == 255 || (family != power && family != bruiser && has_family(owned, family))) return current;"""


def old_table(path):
    """The shipped learned_arm[3][13][8] from emblem_table.h."""
    rows = [list(map(int, m.group(1).split(", "))) for m in re.finditer(r"\{([\d, ]+)\}, // \w+", path.read_text())]
    assert len(rows) == 3 * len(TYPES), len(rows)
    return [[rows[p * len(TYPES) + t] for t in range(len(TYPES))] for p in range(3)]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("selection")
    ap.add_argument("--key", required=True, help="class-z, e.g. 1-1 (class 1: keyed by the current logic's pick family)")
    ap.add_argument("--out", required=True)
    # The bot whose round-1 table the selection was measured against (the lab's base).
    ap.add_argument("--source", default=str(ROOT / "bots/variants/astraeus-8fad72c"))
    ap.add_argument("--flat", action="store_true")
    a = ap.parse_args()
    src, out = Path(a.source), Path(a.out)
    old = old_table(src / "src/economy/emblem_table.h")
    table = [[[[old[p][t][k] if k < len(old[p][t]) else CURRENT for _ in FAMILIES] for k in range(ORD)] for t in range(len(TYPES))] for p in range(3)]
    sel = json.loads(Path(a.selection).read_text())[a.key]
    changed = 0
    for c in sel:
        p, t, k = c["picks"] - 3, TYPES.index(c["type"]), c["k"]
        fams = [FAMILIES.index(c["current_family"])] if c["current_family"] else range(len(FAMILIES))
        for f in fams:
            new = CURRENT if c["arm"] < 0 else c["arm"]
            changed += table[p][t][k][f] != new
            table[p][t][k][f] = new
    if a.flat:
        assert a.key.startswith("0-"), "--flat takes class 0 selections"
        assert all(len(set(ks)) == 1 for ts in table for t in ts for ks in t)
        # Into an existing bot only the table is written (its other files are left alone).
        if not out.exists():
            shutil.copytree(src, out, ignore=shutil.ignore_patterns(".cambc", "compile_commands.json"))
        body = ",\n".join("    {\n" + "\n".join("        {" + ", ".join(str(ks[0]) for ks in t) + "}, // " + TYPES[ti] for ti, t in enumerate(ts)) + "\n    }" for ts in table)
        (out / "src/economy/emblem_table.h").write_text(
            "#pragma once\n"
            f"// Generated by tools/emblab/candidate.py --flat from {Path(a.selection).name} [{a.key}] over the round-1 table\n"
            "// (tools/emblab/README.md). learned_arm[picks - 3][champion_type][ordinal]: family * 3 + stat of the champion's\n"
            f"// ordinal-th new emblem, or {CURRENT} for the current logic's choice.\n#include <cstdint>\n\nnamespace aph {{\n\n"
            f"inline constexpr std::uint8_t learned_arm[3][{len(TYPES)}][{ORD}] = {{\n{body}\n}};\n\n}}\n")
        print(f"{out}: {len(sel)} selected cells, {changed // len(FAMILIES)} table entries changed (flat)")
        return
    if out.exists():
        shutil.rmtree(out)
    shutil.copytree(src, out, ignore=shutil.ignore_patterns(".cambc", "compile_commands.json"))
    body = ",\n".join("    {\n" + ",\n".join("        {" + ", ".join("{" + ", ".join(map(str, fs)) + "}" for fs in ks) + "}, // " + TYPES[t]
                                             for t, ks in enumerate(ts)) + "\n    }" for ts in table)
    (out / "src/economy/emblem_table.h").write_text(
        "#pragma once\n"
        f"// Generated by tools/emblab/candidate.py from {Path(a.selection).name} [{a.key}] over the shipped table.\n"
        f"// learned_arm[picks - 3][champion_type][ordinal][the current logic's pick family]: family * 3 + stat, or {CURRENT}\n"
        "// for the current logic's choice.\n#include <cstdint>\n\nnamespace aph {\n\n"
        f"inline constexpr std::uint8_t learned_arm[3][{len(TYPES)}][{ORD}][{len(FAMILIES)}] = {{\n{body}\n}};\n\n}}\n")
    shop = out / "src/economy/shop.cc"
    text = shop.read_text()
    assert text.count(SHOP_OLD) == 1, "shop.cc's best_emblem changed"
    shop.write_text(text.replace(SHOP_OLD, SHOP_NEW))
    print(f"{out}: {len(sel)} selected cells, {changed} table entries changed")


if __name__ == "__main__":
    main()
