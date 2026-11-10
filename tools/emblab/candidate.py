"""A candidate bot from a dfit.mjs --dr selection (<model>.policy2.json): a copy of --source (the lab's base bot)
whose learned table is indexed [picks - 3][type][ordinal < 12][the current logic's pick family]. Cells the selection
leaves at the base keep the source's table arm (emblem_table.h) or the current logic.

    py tools/emblab/candidate.py replays/emblab/r2/dmodel-dr.policy2.json --key 1-1 --out bots/variants/astraeus-dr11 --source bots/variants/astraeus-8fad72c
    py tools/emblab/candidate.py SELECTION --key 0-2 --flat --source bots/variants/ocean-<sha7> --out bots/variants/NAME   # class 0: the table only (ocean: the only form)

--flat (class 0 selections only): learned_arm[picks - 3][type][ordinal < 12], shop.cc unchanged, so the current logic's
choice is not computed up front (one current_emblem call fewer where a learned arm applies).

    py tools/emblab/candidate.py MODEL.mappolicy.json --mappolicy "type x bucket, static" --key 2 --flat --source BOT --out bots/variants/NAME

--mappolicy LABEL (with --key Z, --flat): a static selection of dfit.mjs --mapdr at another granularity (its `all`
list: "cell, static", "type x bucket, static", "type, static"), spread over the table's cells.

    py tools/emblab/select.py MODEL.json --write "gold_side@4:tb-z2" --out sel.json
    py tools/emblab/candidate.py sel.json --key "gold_side@4:tb-z2" --mapkey MODEL.json --source BOT --out bots/variants/NAME

--buy (round 4 on, ocean; with a select.py or class 0 selection): the selection goes into a second table,
learned_buy, that only buy_shards reads, and the source's own table and forecasts stay as they are. This is what the
lab's vehicle does (it draws an arm at the purchase; prices(), affordable_prefix() and the trip home still price the
base's emblem), so it is the policy the lab measured. Writing the selection into learned_arm itself (--flat) also
changes ocean's forecasts: round 4's first candidate built that way lost 2.9 points to the gate's bodies.

--mapkey MODEL (a select.py map rule): two tables, learned_arm[side][picks - 3][type][ordinal], side 1 on maps whose
feature is at or above the rule's cut; shop.cc reads the feature from the static map (MAP_FEATURES: the ones a
champion can compute for nothing in play). MODEL gives the feature's transform, mean and sd.
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


# Feature values in play, from StaticMap (world.map()): each a C++ expression over gold, gems, cluster (all camp
# groups' rewards summed: a side's are half, the mapgen metrics' mine + shared / 2) and the map.
MAP_FEATURES = {
    "gold_side": "gold / 2", "gems_side": "gems / 2",
    "cluster_share": "std::round(100 * cluster / std::max(1.0f, gems)) / 100",  # mapgen rounds shares to 2 places
    "area": "static_cast<float>(world.map().width * world.map().height)",
}
MAP_SIDE = """// The learned table's map side (tools/emblab, select.py's {rule}): 1 where this map's {feature} is at or
// above the lab's cut.
int emblem_map_side(const World& world) {{
    static const int side = [&] {{
        float gold = 0, gems = 0, cluster = 0;
        for (const auto& g : world.map().groups) gold += static_cast<float>(g.gold), gems += static_cast<float>(g.gems), cluster += static_cast<float>(g.cluster_gems);
        const float value = {expr};
        debug_block({{ std::printf("EMBSIDE %.4f %d\\n", value, value >= learned_split_at ? 1 : 0); }});
        return value >= learned_split_at ? 1 : 0;
    }}();
    return side;
}}

"""
BEST = "// The current logic's emblem, except that a new one is the learned one (tools/emblab) for our pick count, type and\n"
SIZE_OLD, SIZE_NEW = "if (ordinal >= std::size(learned_arm[0][0])) return", "if (ordinal >= std::size(learned_arm[0][0][0])) return"
ARM_OLD = "const int arm = learned_arm[picks - 3][type][ordinal], family = arm / 3;"
ARM_NEW = "const int arm = learned_arm[emblem_map_side(world)][picks - 3][type][ordinal], family = arm / 3;"


def map_keyed(a, src, out, old, doc):
    """--mapkey: the two-sided table and shop.cc's side."""
    model = json.loads(Path(a.mapkey).read_text())
    names = [f[0] for f in model["features"]]
    i = names.index(doc["feature"])
    tf = model["features"][i][1] if len(model["features"][i]) > 1 else None
    at = model["mean"][i] + model["sd"][i] * doc["threshold_z"]
    import math
    raw = math.exp(at) if tf == "log" else math.expm1(at) if tf == "log1p" else at
    assert doc["feature"] in MAP_FEATURES, f"{doc['feature']}: no in-play expression (MAP_FEATURES)"
    tables, counts = [], []
    for side in ("low", "high"):
        t = [[list(old[p][ti]) + [CURRENT] * (ORD - len(old[p][ti])) for ti in range(len(TYPES))] for p in range(3)]
        n = 0
        for c in doc[side]:
            new = CURRENT if c["arm"] < 0 else c["arm"]
            n += t[c["picks"] - 3][TYPES.index(c["type"])][c["k"]] != new
            t[c["picks"] - 3][TYPES.index(c["type"])][c["k"]] = new
        tables.append(t)
        counts.append(n)
    if out.exists():
        shutil.rmtree(out)
    shutil.copytree(src, out, ignore=shutil.ignore_patterns(".cambc", "compile_commands.json"))
    body = ",\n".join("    {\n" + ",\n".join("        {\n" + "\n".join("            {" + ", ".join(map(str, ks)) + "}, // " + TYPES[ti] for ti, ks in enumerate(ts)) + "\n        }"
                                             for ts in t) + "\n    }" for t in tables)
    (out / "src/economy/emblem_table.h").write_text(
        "#pragma once\n"
        f"// Generated by tools/emblab/candidate.py --mapkey from {Path(a.selection).name} [{a.key}] over {src.name}'s table\n"
        "// (tools/emblab/README.md). learned_arm[map side][picks - 3][champion_type][ordinal]: family * 3 + stat of the\n"
        f"// champion's ordinal-th new emblem, or {CURRENT} for the current logic's choice. Side 1: {doc['feature']} >= learned_split_at.\n"
        "#include <cstdint>\n\nnamespace aph {\n\n"
        f"inline constexpr float learned_split_at = {float(f'{raw:.6g}')!r}f;\n"
        f"inline constexpr std::uint8_t learned_arm[2][3][{len(TYPES)}][{ORD}] = {{\n{body}\n}};\n\n}}\n")
    shop = out / "src/economy/shop.cc"
    text = shop.read_text()
    for o in (BEST, SIZE_OLD, ARM_OLD):
        assert text.count(o) == 1, f"shop.cc changed: {o[:50]!r}"
    text = text.replace(BEST, MAP_SIDE.format(rule=a.key, feature=doc["feature"], expr=MAP_FEATURES[doc["feature"]]) + BEST)
    shop.write_text(text.replace(SIZE_OLD, SIZE_NEW).replace(ARM_OLD, ARM_NEW))
    print(f"{out}: {doc['feature']} >= {raw:.6g} (z {doc['threshold_z']:.3f}); low {len(doc['low'])} cells ({counts[0]} entries changed), "
          f"high {len(doc['high'])} ({counts[1]})")


BUY = """bool buying = false; // inside buy_shards
// What buy_shards buys: the emblem lab's selection (learned_buy, tools/emblab candidate.py --buy) where it names an
// arm for a new emblem, as the lab's vehicle drew it: at the purchase only, so every forecast prices base_emblem's.
Emblem best_emblem(const World& world, const Build& bought = {}, const cambc::enum_map<cambc::item_type>* items = nullptr) {
    const Emblem base = base_emblem(world, bought, items);
    const int picks = economy_pick_count(world), type = static_cast<int>(world.me().type);
    if (!buying || items || picks < 3 || picks > 5) return base;
    const auto& owned = my_items();
    if (begun_emblem(world, owned)) return base;
    unsigned ordinal = 0;
    for (int family = monster; family <= collectors; ++family)
        for (int stat = strength_stat; stat <= health_stat; ++stat) ordinal += owned[emblem_of(family, stat)];
    if (ordinal >= std::size(learned_buy{index0}[0][0])) return base;
    int arm = learned_buy{index}[picks - 3][type][ordinal];
    if (arm == 255) return base;
    const auto drawable = [&](int a) { return a / 3 != greed && (a / 3 == power || a / 3 == bruiser || !has_family(owned, a / 3)); };
    // An arm whose passive we own, and 254, are the current logic's choice (the lab's fallback).
    if (arm == 254 || !drawable(arm)) {
        const Emblem cur = current_emblem(world, bought, nullptr);
        arm = cur.family * 3 + cur.stat;
        if (!drawable(arm)) return base;
    }
    if (arm == base.family * 3 + base.stat) return base;
    pin_family = arm / 3, pin_stat = arm % 3;
    const Emblem e = current_emblem(world, bought, nullptr);
    pin_family = -1;
    return e;
}

"""
BEST_SIG = "Emblem best_emblem(const World& world, const Build& bought = {}, const cambc::enum_map<cambc::item_type>* items = nullptr) {\n"
BASE_SIG = "Emblem base_emblem(const World& world, const Build& bought, const cambc::enum_map<cambc::item_type>* items) {\n"
BUY_AT = "// True if any shard was bought.\nbool buy_shards(const World& world) {\n"
CALL_OLD = "        const auto [family, stat, saved, cost, passive] = best_emblem(world, bought);\n        const unsigned have"
CALL_NEW = ("        const auto [family, stat, saved, cost, passive] = (buying = true, best_emblem(world, bought));\n"
            "        buying = false;\n        const unsigned have")


def buy_table(cells):
    """learned_buy[3][13][12]: 255 keeps the base, 254 the current logic, else the arm."""
    t = [[[255] * ORD for _ in TYPES] for _ in range(3)]
    for c in cells:
        t[c["picks"] - 3][TYPES.index(c["type"])][c["k"]] = 254 if c["arm"] < 0 else c["arm"]
    return t


def table_text(t):
    return ",\n".join("    {\n" + "\n".join("        {" + ", ".join(map(str, ks)) + "}, // " + TYPES[ti] for ti, ks in enumerate(ts)) + "\n    }" for ts in t)


def buy_only(a, src, out, sel):
    """--buy: learned_buy beside the source's own table, read by buy_shards alone."""
    if out.exists():
        shutil.rmtree(out)
    shutil.copytree(src, out, ignore=shutil.ignore_patterns(".cambc", "compile_commands.json"))
    head = out / "src/economy/emblem_table.h"
    text = head.read_text()
    assert text.rstrip().endswith("}") and "learned_buy" not in text
    if a.mapkey:
        doc, (raw, expr) = sel, map_cut(a, sel)
        tables = "inline constexpr float learned_split_at = %rf;\ninline constexpr std::uint8_t learned_buy[2][3][%d][%d] = {\n%s\n};\n" % (
            float(f"{raw:.6g}"), len(TYPES), ORD, ",\n".join("{\n" + table_text(buy_table(doc[side])) + "\n}" for side in ("low", "high")))
        what = f"Side 1: {doc['feature']} >= learned_split_at."
    else:
        tables = "inline constexpr std::uint8_t learned_buy[3][%d][%d] = {\n%s\n};\n" % (len(TYPES), ORD, table_text(buy_table(sel)))
        what = ""
    i = text.rstrip().rfind("}")
    head.write_text(text[:i] + f"// Generated by tools/emblab/candidate.py --buy from {Path(a.selection).name} [{a.key}]: what buy_shards buys for a new\n"
                    f"// emblem in place of the table above. 255: no change; 254: the current logic's choice. {what}\n" + tables + "\n}\n")
    shop = out / "src/economy/shop.cc"
    text = shop.read_text()
    for o in (BEST_SIG, BUY_AT, CALL_OLD):
        assert text.count(o) == 1, f"shop.cc changed: {o[:50]!r}"
    side = MAP_SIDE.format(rule=a.key, feature=sel["feature"], expr=map_cut(a, sel)[1]) if a.mapkey else ""
    buy = BUY.replace("{index0}", "[0]" if a.mapkey else "").replace("{index}", "[emblem_map_side(world)]" if a.mapkey else "")
    text = text.replace(BEST_SIG, BASE_SIG).replace(BUY_AT, side + buy + BUY_AT).replace(CALL_OLD, CALL_NEW)
    shop.write_text(text)
    n = (len(sel["low"]), len(sel["high"])) if a.mapkey else len(sel)
    print(f"{out}: {n} cells in learned_buy (purchase only)" + (f"; {sel['feature']} >= {map_cut(a, sel)[0]:.6g}" if a.mapkey else ""))


def map_cut(a, doc):
    """(the raw feature value of a map rule's cut, its in-play expression)."""
    import math
    model = json.loads(Path(a.mapkey).read_text())
    i = [f[0] for f in model["features"]].index(doc["feature"])
    tf = model["features"][i][1] if len(model["features"][i]) > 1 else None
    at = model["mean"][i] + model["sd"][i] * doc["threshold_z"]
    assert doc["feature"] in MAP_FEATURES, f"{doc['feature']}: no in-play expression (MAP_FEATURES)"
    return (math.exp(at) if tf == "log" else math.expm1(at) if tf == "log1p" else at), MAP_FEATURES[doc["feature"]]


def static_cells(doc, label, z):
    """A static --mapdr selection as class 0 cells: its granularity's cells spread over (picks, type, ordinal)."""
    hit = [x for x in doc["all"] if x["config"] == label and x["z"] == z and not x["partition"]]
    assert len(hit) == 1, f"{label!r} z {z}: {len(hit)} static selections"
    kc = lambda k: k if k < 3 else 3 if k < 6 else 4  # dfit.mjs KC
    arm = {c["cell"]: c["arm"] for c in hit[0]["cells"]}
    out = []
    for p in range(3):
        for t, name in enumerate(TYPES):
            for k in range(ORD):
                cell = {"cell": (p * len(TYPES) + t) * ORD + k, "type x bucket": t * 5 + kc(k), "type": t}[hit[0]["granularity"]]
                if cell in arm:
                    out.append({"picks": p + 3, "type": name, "k": k, "current_family": None, "arm": arm[cell]})
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("selection")
    ap.add_argument("--key", required=True, help="class-z, e.g. 1-1 (class 1: keyed by the current logic's pick family)")
    ap.add_argument("--out", required=True)
    # The bot whose table the selection was measured against (the lab's base: its config.json "source").
    ap.add_argument("--source", required=True)
    ap.add_argument("--flat", action="store_true")
    ap.add_argument("--mappolicy", help='a static config label of a .mappolicy.json, e.g. "type x bucket, static"')
    ap.add_argument("--mapkey", help="the model (dmodel*.json) of a select.py map rule: a two-sided table")
    ap.add_argument("--buy", action="store_true", help="the selection in learned_buy, read at the purchase only (what the lab measured)")
    a = ap.parse_args()
    src, out = Path(a.source), Path(a.out)
    old = old_table(src / "src/economy/emblem_table.h")
    if a.buy:
        doc = json.loads(Path(a.selection).read_text())[a.key]
        return buy_only(a, src, out, doc if a.mapkey else (static_cells(json.loads(Path(a.selection).read_text()), a.mappolicy, float(a.key)) if a.mappolicy else doc))
    if a.mapkey:
        return map_keyed(a, src, out, old, json.loads(Path(a.selection).read_text())[a.key])
    table = [[[[old[p][t][k] if k < len(old[p][t]) else CURRENT for _ in FAMILIES] for k in range(ORD)] for t in range(len(TYPES))] for p in range(3)]
    sel = static_cells(json.loads(Path(a.selection).read_text()), a.mappolicy, float(a.key)) if a.mappolicy else json.loads(Path(a.selection).read_text())[a.key]
    changed = 0
    for c in sel:
        p, t, k = c["picks"] - 3, TYPES.index(c["type"]), c["k"]
        fams = [FAMILIES.index(c["current_family"])] if c["current_family"] else range(len(FAMILIES))
        for f in fams:
            new = CURRENT if c["arm"] < 0 else c["arm"]
            changed += table[p][t][k][f] != new
            table[p][t][k][f] = new
    if a.flat:
        assert all(c["current_family"] is None for c in sel), "--flat takes class 0 selections (select.py's, dfit's 0-Z)"
        assert all(len(set(ks)) == 1 for ts in table for t in ts for ks in t)
        # Into an existing bot only the table is written (its other files are left alone).
        if not out.exists():
            shutil.copytree(src, out, ignore=shutil.ignore_patterns(".cambc", "compile_commands.json"))
        body = ",\n".join("    {\n" + "\n".join("        {" + ", ".join(str(ks[0]) for ks in t) + "}, // " + TYPES[ti] for ti, t in enumerate(ts)) + "\n    }" for ts in table)
        (out / "src/economy/emblem_table.h").write_text(
            "#pragma once\n"
            f"// Generated by tools/emblab/candidate.py --flat from {Path(a.selection).name} [{a.key}] over {src.name}'s table\n"
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
