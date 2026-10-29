"""Emblem lab vehicles: draft lab vehicles (tools/draftlab/vehicle.py) whose champions also buy their k-th new
emblem from the table (trainer.h), with gold priced at trainer::gold_price_scale. Every new-emblem decision
buy_shards reaches is logged in debug_block (no fuel in local builds) as one line:

    EMB round type ordinal arm chosen model gold strength focus max_health v0 ... v41

arm: the table's (family * 3 + stat), -1 none, -2 its passive already owned (the model's then); chosen and
model: family * 3 + stat; v: the model's value (best_emblem's `saved`) of every arm, x for Greed's."""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "draftlab"))
import vehicle  # noqa: E402

CHAMPS = vehicle.CHAMPS
FAMILIES = ["monster", "power", "durability", "treasure", "jungle", "home", "bruiser", "tribute", "capture", "prospector",
            "hunter", "skirmish", "greed", "collectors"]
STATS = ["strength", "focus", "health"]
ARMS = [f * 3 + s for f in range(len(FAMILIES)) for s in range(3) if FAMILIES[f] != "greed"]
ORDINALS = 8
MODEL = 255

WRAPPER = r'''
// Emblem lab: at each new emblem buy_shards starts, the table's arm in place of the model's, logged
// with the model's value of every arm.
bool trainer_priced_passive(int family) {
    return family == treasure || family == tribute || family == capture || family == prospector || family == hunter || family == skirmish ||
           family == greed || family == collectors;
}

Emblem pinned_emblem(const World& world, const Build& bought, int family, int stat) {
    trainer::pin_family = family, trainer::pin_stat = stat;
    const Emblem e = model_emblem(world, bought, nullptr);
    trainer::pin_family = -1;
    return e;
}

Emblem best_emblem(const World& world, const Build& bought = {}, const cambc::enum_map<cambc::item_type>* items = nullptr) {
    const Emblem model = model_emblem(world, bought, items);
    if (!trainer::buying || items) return model;
    const auto& owned = my_items();
    if (begun_emblem(world, owned)) return model;
    int ordinal = 0;
    for (int family = monster; family <= collectors; ++family)
        for (int stat = strength_stat; stat <= health_stat; ++stat) ordinal += static_cast<int>(owned[emblem_of(family, stat)]);
    int arm = trainer::emblem_arm(world.me().type, ordinal);
    if (arm >= 0 && arm / 3 != power && arm / 3 != bruiser && arm / 3 != greed && has_family(owned, arm / 3)) arm = -2;
    const Emblem chosen = arm >= 0 ? pinned_emblem(world, bought, arm / 3, arm % 3) : model;
    debug_block({
        static int logged = -1;
        if (ordinal != logged) {
            logged = ordinal;
            const auto& self = world.me();
            std::printf("EMB %d %d %d %d %d %d %u %.1f %.1f %.0f", world.round, static_cast<int>(self.type), ordinal, arm,
                        chosen.family * 3 + chosen.stat, model.family * 3 + model.stat, my_gold(), self.strength, self.focus, self.max_health);
            for (int family = monster; family <= collectors; ++family)
                for (int stat = strength_stat; stat <= health_stat; ++stat)
                    if (family == greed) std::printf(" x");
                    else std::printf(" %.4g", pinned_emblem(world, bought, family, stat).saved);
            std::printf("\n");
        }
    });
    return chosen;
}
'''

SHOP = "src/economy/shop.cc"
PATCHES = {SHOP: [
    [('#include "../bot_parts.h"\n', '#include "../bot_parts.h"\n#include "../draft/trainer.h"\n')],
    [("std::optional<Begun> begun_emblem(const World& world, const cambc::enum_map<cambc::item_type>& owned) {\n",
      "bool trainer_priced_passive(int family);\n"
      "std::optional<Begun> begun_emblem(const World& world, const cambc::enum_map<cambc::item_type>& owned) {\n"
      "    if (trainer::pin_family >= 0) return Begun{trainer::pin_family, trainer::pin_stat, trainer_priced_passive(trainer::pin_family)};\n")],
    # Any emblem the table began, which the model's list need not name.
    [("    return std::nullopt;\n}\n\n// Our stats",
      "    for (int family = monster; family <= collectors; ++family)\n"
      "        for (int stat = strength_stat; family != greed && stat <= health_stat; ++stat)\n"
      "            if (has(family, stat)) return Begun{family, stat, trainer_priced_passive(family)};\n"
      "    return std::nullopt;\n}\n\n// Our stats")],
    [("Emblem best_emblem(const World& world, const Build& bought = {}, const cambc::enum_map<cambc::item_type>* items = nullptr) {\n",
      "Emblem model_emblem(const World& world, const Build& bought, const cambc::enum_map<cambc::item_type>* items) {\n")],
    [("// True if any shard was bought.\nbool buy_shards(const World& world) {\n",
      WRAPPER.lstrip("\n") + "\n// True if any shard was bought.\nbool buy_shards(const World& world) {\n    trainer::buying = true;\n"
      "    struct Done { ~Done() { trainer::buying = false; } } done;\n")],
    [("        kept.per_gold = now.share * kept.next.saved / static_cast<float>(std::max(1u, kept.next.cost));\n",
      "        kept.per_gold = trainer::gold_price_scale * now.share * kept.next.saved / static_cast<float>(std::max(1u, kept.next.cost));\n")],
],
    # The 1 MiB stdout cap: the two chattiest debug lines would crowd out late EMB lines.
    "src/model/world.cc": [[('std::printf("SLOT %d', 'if (false) std::printf("SLOT %d')]],
    "src/bot.cc": [[('std::printf("D %d %u %c', 'if (false) std::printf("D %d %u %c')]],
}


def table_header(entries):
    """entries: [(key hex, team 0/1, [champion names], arms: 6 rows of ORDINALS arm bytes)], any order."""
    rows = sorted((int(k, 16), t, tuple(CHAMPS.index(c) for c in comp), arms) for k, t, comp, arms in entries)
    for a, b in zip(rows, rows[1:]):
        assert a[:2] != b[:2], f"duplicate entry {a[:2]}"
    lines = []
    for k, t, c, arms in rows:
        assert len(arms) == 6 and all(len(r) == ORDINALS for r in arms)
        a = ", ".join("{" + ", ".join(map(str, r)) + "}" for r in arms)
        lines.append(f"    {{0x{k:016x}ull, {t}, {len(c)}, {{{', '.join(map(str, c + (0,) * (5 - len(c))))}}}, {{{{{a}}}}}}},")
    none = ", ".join("{" + ", ".join([str(MODEL)] * ORDINALS) + "}" for _ in range(6))
    lines.append(f"    {{0xffffffffffffffffull, 255, 0, {{0, 0, 0, 0, 0}}, {{{{{none}}}}}}},")
    return ("#pragma once\n// Generated by tools/emblab/evehicle.py: (map key, team, picks, draft ids, arms), sorted.\n"
            "namespace aph::trainer {\ninline constexpr Entry entries[] = {\n" + "\n".join(lines) + "\n};\n}\n")


def make(source, name, entries):
    return vehicle.make(source, name, entries, trainer=HERE / "trainer.h", table=table_header(entries), patches=PATCHES)
