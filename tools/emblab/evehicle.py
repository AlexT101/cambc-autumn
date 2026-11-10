"""Emblem lab vehicles: draft lab vehicles (tools/draftlab/vehicle.py) of a bot with the learned table (astraeus
8fad72c on, ocean), whose champions draw some new emblems at random in the game (trainer.h). Where the table forces
the k-th new emblem (k < 12), the arm is drawn from
    mode 0: eps / n over the n arms whose passive is not owned (Power and Bruiser repeat), plus (1 - eps) x softmax of
            (v[a] - v[base]) / tau + corr[a] / corr_tau, v the current logic's value of the arm, corr the previous
            fit's static gain (logit) of the arm over the current logic's choice;
    mode 1: uniform over those n arms (the unbiased check).
Every new-emblem decision buy_shards reaches is logged in debug_block (no fuel in local builds) as one line:

    EMB3 round type k forced mode chosen base current q qb gold strength focus max_health own_gems enemy_gems carried
         allies_alive picks v0 ... v41

base: the bot's own choice (its learned table, else the current logic); current: the current logic's; chosen: what
was bought (base unless forced); q: the probability the proposal gave chosen (1 unforced); qb: the probability it
gives base, forced or not (round 4 on: with it the logging probability of every row is known without recomputing
the proposal, so corr may change between batches); v: the current logic's value of every arm, x where Greed or not
drawable. Arms are family * 3 + stat.

Round 4 (ocean): only buy_shards' own calls draw (lab_shopping; ocean's best_emblem also serves forecasts), and
every other debug_block but main.cc's OOF line is compiled out (lab_off), so the 1 MiB stdout cap never cuts an
EMB3 line and games cost no printing."""
import json
import sys
from functools import lru_cache
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE.parent / "draftlab"))
import vehicle  # noqa: E402

CHAMPS = vehicle.CHAMPS
TYPES = ["ryth", "vesper_vale", "vendetta", "cassi", "issac", "stellar", "prism", "marcella", "willow", "ren", "varg", "tavi", "heart_of_ruin"]
FAMILIES = ["monster", "power", "durability", "treasure", "jungle", "home", "bruiser", "tribute", "capture", "prospector",
            "hunter", "skirmish", "greed", "collectors"]
STATS = ["strength", "focus", "health"]
ARMS = [f * 3 + s for f in range(len(FAMILIES)) for s in range(3) if FAMILIES[f] != "greed"]
ORDINALS = 12
NARMS = 42

WRAPPER = r'''
// Emblem lab: at a new emblem the table forces, a drawn arm in place of the base's (base_emblem); every new emblem
// logged with the current logic's value of every arm.
bool lab_shopping = false; // inside buy_shards
Emblem lab_pinned(const World& world, const Build& bought, int family, int stat) {
    pin_family = family, pin_stat = stat;
    const Emblem e = current_emblem(world, bought, nullptr);
    pin_family = -1;
    return e;
}

Emblem best_emblem(const World& world, const Build& bought = {}, const cambc::enum_map<cambc::item_type>* items = nullptr) {
    const Emblem base = base_emblem(world, bought, items);
    if (!lab_shopping || items) return base;
    const auto& owned = my_items();
    if (begun_emblem(world, owned)) return base;
    int ordinal = 0;
    for (int family = monster; family <= collectors; ++family)
        for (int stat = strength_stat; stat <= health_stat; ++stat) ordinal += static_cast<int>(owned[emblem_of(family, stat)]);
    const auto& self = world.me();
    double u = 0;
    int mode = 0;
    const bool force = trainer::forced(self.type, ordinal, &u, &mode);
    const int base_arm = base.family * 3 + base.stat;
    int arm = base_arm;
    debug_block({
        static int drawn_ordinal = -1, drawn_arm = -1, logged = -1;
        static float drawn_q = 1;
        float v[trainer::arms], p[trainer::arms];
        bool ok[trainer::arms];
        int n = 0;
        for (int family = monster; family <= collectors; ++family)
            for (int stat = strength_stat; stat <= health_stat; ++stat) {
                const int a = family * 3 + stat;
                ok[a] = family != greed && (family == power || family == bruiser || !has_family(owned, family));
                v[a] = ok[a] ? lab_pinned(world, bought, family, stat).saved : 0;
                n += ok[a];
            }
        const float vb = lab_pinned(world, bought, base.family, base.stat).saved;
        const int picks = economy_pick_count(world), t = static_cast<int>(self.type);
        float q = 1, qb = 1;
        int pick = -1;
        if (n > 0) {
            float top = -1e30f;
            for (int a = 0; a < trainer::arms; ++a)
                if (ok[a]) {
                    p[a] = (v[a] - vb) / trainer::proposal_tau;
                    if (picks >= 3 && picks <= 5) p[a] += trainer::corr[picks - 3][t][std::min(ordinal, trainer::ordinals - 1)][a] / trainer::corr_tau;
                    top = std::max(top, p[a]);
                }
            float sum = 0;
            for (int a = 0; a < trainer::arms; ++a) sum += ok[a] ? (p[a] = std::exp(p[a] - top)) : 0;
            const float eps = mode == 1 ? 1.0f : trainer::proposal_eps;
            double acc = 0;
            for (int a = 0; a < trainer::arms; ++a)
                if (ok[a]) {
                    p[a] = eps / static_cast<float>(n) + (1 - eps) * p[a] / sum;
                    acc += p[a];
                    if (pick < 0 && u < acc) pick = a;
                }
            for (int a = trainer::arms - 1; pick < 0 && a >= 0; --a) // rounding: the last drawable arm
                if (ok[a]) pick = a;
            qb = ok[base_arm] ? p[base_arm] : 0;
        }
        if (force && ordinal == drawn_ordinal) arm = drawn_arm, q = drawn_q;
        else if (force && n > 0) {
            arm = pick, q = p[pick];
            drawn_ordinal = ordinal, drawn_arm = arm, drawn_q = q;
        }
        if (ordinal != logged) {
            logged = ordinal;
            const Emblem cur = current_emblem(world, bought, items);
            int alive = 0;
            for (const auto& ally : world.allies) alive += ally.alive;
            std::printf("EMB3 %d %d %d %d %d %d %d %d %.4g %.4g %u %.1f %.1f %.0f %u %u %d %d %d", world.round, t, ordinal, force ? 1 : 0, mode, arm,
                        base_arm, cur.family * 3 + cur.stat, q, qb, my_gold(), self.strength, self.focus, self.max_health,
                        cambc::global_submitted_gems(cambc::team::ally), cambc::global_submitted_gems(cambc::team::enemy), self.gems, alive, picks);
            for (int a = 0; a < trainer::arms; ++a)
                if (ok[a]) std::printf(" %.4g", v[a]);
                else std::printf(" x");
            std::printf("\n");
        }
    });
    return arm == base_arm ? base : lab_pinned(world, bought, arm / 3, arm % 3);
}
'''

SHOP = "src/economy/shop.cc"
PATCHES = {SHOP: [
    [('#include "emblem_table.h"\n', '#include "emblem_table.h"\n#include "../draft/trainer.h"\n#include <cmath>\n')],
    [("Emblem best_emblem(const World& world, const Build& bought = {}, const cambc::enum_map<cambc::item_type>* items = nullptr) {\n",
      "Emblem base_emblem(const World& world, const Build& bought, const cambc::enum_map<cambc::item_type>* items) {\n")],
    [("// True if any shard was bought.\nbool buy_shards(const World& world) {\n",
      WRAPPER.lstrip("\n") + "\n// True if any shard was bought.\nbool buy_shards(const World& world) {\n")],
    # Only the purchase draws: ocean's best_emblem also prices forecasts (prices(), affordable_prefix()).
    [("        const auto [family, stat, saved, cost, passive] = best_emblem(world, bought);\n        const unsigned have",
      "        const auto [family, stat, saved, cost, passive] = (lab_shopping = true, best_emblem(world, bought));\n"
      "        lab_shopping = false;\n        const unsigned have")],
]}
LAB_OFF = "#ifndef lab_off\n#define lab_off(...) if (false) { __VA_ARGS__ } else (void)0\n#endif\n"


def quiet(blobs):
    """Compiles out every debug_block of the source but main.cc's OOF line: the engine caps a team's stdout at
    1 MiB whatever --log-limit says, and the vehicle's own block (the wrapper, patched in after this) must never be
    cut. Debug blocks pause fuel, so play is as before."""
    for rel, data in blobs.items():
        if not rel.endswith((".cc", ".h", ".cpp")) or b"debug_block(" not in data:
            continue
        parts = data.decode().split("debug_block(")
        out = parts[0]
        for part in parts[1:]:
            out += ("debug_block(" if 'std::printf("OOF ' in part[:400] else "lab_off(") + part
        blobs[rel] = (LAB_OFF + out).encode()


@lru_cache(maxsize=4)
def corr_values(model_path):
    """corr[picks - 3][type][k][arm]: a fit's static gain (logit) of each arm, 0 for Greed or without a model. From a
    round-1 model (fit.mjs: armGains without the model-choice terms, which cancel in the softmax; k >= the fit's
    buckets using its last) or a per-decision one (dfit.mjs: phi's static terms EA + ETF + ETS + EKF + EKS + EPF +
    EPS; the base's cancel in the softmax)."""
    out = [[[[0.0] * NARMS for _ in range(ORDINALS)] for _ in TYPES] for _ in range(3)]
    if not model_path:
        return out
    m = json.loads((ROOT / model_path).read_text())
    th, L = m["theta"], m["L"]
    NF, NT = len(FAMILIES), len(TYPES)
    if "EA" in L:
        NKC = 5
        for pi in range(3):
            for t in range(NT):
                for k in range(ORDINALS):
                    kc = k if k < 3 else 3 if k < 6 else 4
                    for a in ARMS:
                        f, s = divmod(a, 3)
                        out[pi][t][k][a] = (th[L["EA"] + (t * ORDINALS + k) * NARMS + a] + th[L["ETF"] + (t * NKC + kc) * NF + f]
                                            + th[L["ETS"] + (t * NKC + kc) * 3 + s] + th[L["EKF"] + k * NF + f] + th[L["EKS"] + k * 3 + s]
                                            + th[L["EPF"] + (pi * NT + t) * NF + f] + th[L["EPS"] + (pi * NT + t) * 3 + s])
        return out
    N = m["N"]

    def at(name, i, pi):
        return th[L[name] + i] + th[L[name + "P"] + pi * N[name] + i]
    for pi in range(3):
        for t in range(NT):
            for k in range(ORDINALS):
                kb = min(k, 3)
                for a in ARMS:
                    f, s = divmod(a, 3)
                    out[pi][t][k][a] = at("ET", t * NF + f, pi) + at("ST", t * 3 + s, pi) + at("EK", kb * NF + f, pi) + at("SK", kb * 3 + s, pi)
    return out


def table_header(entries, model_path=None):
    """entries: [(key hex, team 0/1, [champion names], mode, seed, force: 6 row bitmasks)], any order."""
    rows = sorted((int(k, 16), t, tuple(CHAMPS.index(c) for c in comp), mode, seed, tuple(force)) for k, t, comp, mode, seed, force in entries)
    for a, b in zip(rows, rows[1:]):
        assert a[:2] != b[:2], f"duplicate entry {a[:2]}"
    lines = []
    for k, t, c, mode, seed, force in rows:
        assert len(force) == 6 and all(0 <= x < 1 << ORDINALS for x in force)
        lines.append(f"    {{0x{k:016x}ull, {t}, {len(c)}, {mode}, {{{', '.join(map(str, c + (0,) * (5 - len(c))))}}}, {seed}u, "
                     f"{{{', '.join(map(str, force))}}}}},")
    lines.append("    {0xffffffffffffffffull, 255, 0, 0, {0, 0, 0, 0, 0}, 0u, {0, 0, 0, 0, 0, 0}},")
    corr = corr_values(model_path)
    cl = ",\n".join("    {" + ", ".join("{" + ", ".join("{" + ", ".join(f"{x:.4e}f" for x in arms) + "}" for arms in ks) + "}" for ks in ts) + "}"
                    for ts in corr)
    return ("#pragma once\n// Generated by tools/emblab/evehicle.py: (map key, team, picks, mode, draft ids, seed, force), sorted;\n"
            f"// corr from {model_path or 'no model'}.\n"
            "namespace aph::trainer {\ninline constexpr Entry entries[] = {\n" + "\n".join(lines) + "\n};\n"
            "inline constexpr float proposal_tau = 0.04f, proposal_eps = 0.3f, corr_tau = 0.04f;\n"
            f"inline constexpr float corr[3][13][{ORDINALS}][{NARMS}] = {{\n{cl}\n}};\n}}\n")


def make(source, name, entries, model_path=None):
    return vehicle.make(source, name, entries, trainer=HERE / "trainer.h", table=table_header(entries, model_path), patches=PATCHES,
                        transform=quiet)


def make_body(source, name):
    """A quiet copy (quiet()) of a sparring body, which drafts for itself: the other side of a body game."""
    source, target = Path(source), vehicle.VARIANTS / name
    blobs = {p.relative_to(source).as_posix(): p.read_bytes() for p in (source / "src").rglob("*") if p.is_file()}
    quiet(blobs)
    changed = [rel for rel, data in sorted(blobs.items()) if vehicle.write_if_changed(target / rel, data)]
    return target, bool(changed)


# ---------- round 5: the edit design (elab.py, edits.py) ----------
# Lab flags: (name, default), read by FLAG_PATCHES' hooks in shop.cc; an edit sets some for the game.
FLAGS = [("greed_from", 1000), ("coll_at", 1000), ("diversify", 0), ("stat_b0", 0), ("stat_b1", 0), ("stat_b2", 0), ("stat_b3", 0),
         ("fight_w", 1), ("m_skirmish", 1), ("m_treasure", 1), ("m_prospector", 1), ("m_capture", 1), ("m_hunter", 1), ("m_tribute", 1),
         ("coll_priced", 0)]
FLAG_HOOKS = r"""
// Emblem lab flags (tools/emblab/structural.py); at their defaults every hook leaves the choice as it was.
Emblem lab_pinned(const World& world, const Build& bought, const cambc::enum_map<cambc::item_type>* items, int family, int stat) {
    pin_family = family, pin_stat = stat;
    const Emblem e = current_emblem(world, bought, items);
    pin_family = -1;
    return e;
}
// A new emblem the flags force, or -1: Collectors once coll_at distinct families are owned; Greed in the main stat
// from ordinal greed_from on.
int lab_forced(const World& world, const cambc::enum_map<cambc::item_type>& owned, int ordinal) {
    if (lab_flag[1] < 100 && !has_family(owned, collectors)) {
        int n = 0;
        for (int family = monster; family <= collectors; ++family) n += has_family(owned, family);
        if (static_cast<float>(n) >= lab_flag[1]) return collectors * 3 + main_stat(world);
    }
    if (static_cast<float>(ordinal) >= lab_flag[0]) return greed * 3 + main_stat(world);
    return -1;
}
// diversify: with Collectors owned, a family already owned gives way to the first one not owned. stat_bN: the
// emblems of ordinals 3N..3N+2 in Health (1) or the main stat (2).
Emblem lab_adjust(const World& world, const Build& bought, const cambc::enum_map<cambc::item_type>* items,
                  const cambc::enum_map<cambc::item_type>& owned, int ordinal, const Emblem& e) {
    int family = e.family, stat = e.stat;
    if (lab_flag[2] > 0 && has_family(owned, collectors) && has_family(owned, family))
        for (const int f : {skirmish, durability, monster, jungle, prospector, capture, treasure, hunter, home, tribute, power, bruiser})
            if (!has_family(owned, f)) {
                family = f;
                break;
            }
    if (ordinal < 12) {
        const float s = lab_flag[3 + ordinal / 3];
        if (s == 1) stat = health_stat;
        else if (s == 2) stat = main_stat(world);
    }
    return family == e.family && stat == e.stat ? e : lab_pinned(world, bought, items, family, stat);
}

"""
PASSIVE = "float passive_saved(const World& world, const IncomeRates& rates, const cambc::enum_map<cambc::item_type>& owned, int family, float per_gold) {\n"
PASSIVE_HOOK = r"""float passive_saved_raw(const World& world, const IncomeRates& rates, const cambc::enum_map<cambc::item_type>& owned, int family, float per_gold);
// Emblem lab: a passive's price x its flag; coll_priced prices Collectors' champion damage (x the flag) as Skirmish's.
float passive_saved(const World& world, const IncomeRates& rates, const cambc::enum_map<cambc::item_type>& owned, int family, float per_gold) {
    float m = 1;
    switch (family) {
    case skirmish: m = lab_flag[8]; break;
    case treasure: m = lab_flag[9]; break;
    case prospector: m = lab_flag[10]; break;
    case capture: m = lab_flag[11]; break;
    case hunter: m = lab_flag[12]; break;
    case tribute: m = lab_flag[13]; break;
    case collectors: {
        if (lab_flag[14] <= 0 || has_family(owned, collectors)) return 0;
        int n = 1;
        for (int f = monster; f < collectors; ++f) n += has_family(owned, f);
        return lab_flag[14] * params::fight_weight * lab_flag[7] * fight_share() * (1.0f - 1.0f / (1.0f + 0.01f * static_cast<float>(n)));
    }
    default: break;
    }
    return m * passive_saved_raw(world, rates, owned, family, per_gold);
}
float passive_saved_raw(const World& world, const IncomeRates& rates, const cambc::enum_map<cambc::item_type>& owned, int family, float per_gold) {
"""
OR_PASSIVE = "                best = {family, shards.stat, saved, emblem_price, saved - shards.saved};\n        return best;\n"
OR_PASSIVE_HOOK = OR_PASSIVE.replace("        return best;\n", r"""        if (lab_flag[14] > 0 && !has_family(owned, collectors)) {
            Emblem c = value(collectors, a);
            if (const auto e = value(collectors, b); e.saved > c.saved) c = e;
            const float passive = passive_saved(world, rates, owned, collectors, gold_saves);
            if (c.saved + passive > best.saved) best = {collectors, c.stat, c.saved + passive, emblem_price, passive};
        }
        return best;
""")
BEST_DOC = "// The current logic's emblem, except that a new one is the learned one (tools/emblab) for our pick count, type and\n"
PAST = "    if (ordinal >= std::size(learned_arm[0][0])) return reactive_over(world, bought, current_emblem(world, bought, items), items);\n"
OWNED = ("    if (arm == 255 || (family != power && family != bruiser && has_family(owned, family)))\n"
         "        return reactive_over(world, bought, current_emblem(world, bought, items), items);\n")
LAST = "    return reactive_over(world, bought, e, items);\n}\n\n// True if any shard was bought.\n"
ADJ = "lab_adjust(world, bought, items, owned, static_cast<int>(ordinal), {})"
FLAG_PATCHES = [
    [(PASSIVE, PASSIVE_HOOK)],
    [("    case skirmish: return params::fight_weight * fight_share()", "    case skirmish: return params::fight_weight * lab_flag[7] * fight_share()")],
    [("    const float fight_scale = params::fight_weight * fight_share();\n", "    const float fight_scale = params::fight_weight * lab_flag[7] * fight_share();\n")],
    [(OR_PASSIVE, OR_PASSIVE_HOOK)],
    [(BEST_DOC, FLAG_HOOKS.lstrip("\n") + BEST_DOC)],
    [(PAST, "    if (const int forced = lab_forced(world, owned, static_cast<int>(ordinal)); forced >= 0)\n"
            "        return reactive_over(world, bought, lab_pinned(world, bought, items, forced / 3, forced % 3), items);\n"
            + PAST.replace("current_emblem(world, bought, items)", ADJ.format("current_emblem(world, bought, items)")))],
    [(OWNED, OWNED.replace("current_emblem(world, bought, items)", ADJ.format("current_emblem(world, bought, items)")))],
    [(LAST, LAST.replace("reactive_over(world, bought, e, items)", "reactive_over(world, bought, " + ADJ.format("e") + ", items)"))],
]

EDIT_WRAPPER = r'''
// Emblem lab, edit design (tools/emblab/elab.py): this map and side's edits (trainer_table.h: Entry.force, as edit
// ids) patch a copy of learned_arm and the lab flags at the first emblem choice.
std::uint8_t lab_arm[3][13][12];
float lab_flag[] = {FLAG_DEFAULTS};
bool lab_ready = false;
void lab_init() {
    lab_ready = true;
    std::memcpy(lab_arm, learned_arm, sizeof lab_arm);
    const auto* entry = trainer::find();
    if (!entry) return;
    std::uint8_t* flat = &lab_arm[0][0][0];
    for (const unsigned id : entry->force) {
        if (id == 0 || id > static_cast<unsigned>(trainer::edit_count)) continue;
        for (auto i = trainer::edit_first[id]; i < trainer::edit_first[id + 1]; ++i) flat[trainer::edit_cells[i].at] = trainer::edit_cells[i].arm;
        for (auto i = trainer::edit_flag_first[id]; i < trainer::edit_flag_first[id + 1]; ++i)
            lab_flag[trainer::edit_flags[i].flag] = trainer::edit_flags[i].value;
    }
}

'''
BEST = "Emblem best_emblem(const World& world, const Build& bought = {}, const cambc::enum_map<cambc::item_type>* items = nullptr) {\n"
BEGUN = "// An emblem with shards owned short of it, which best_emblem finishes before any other.\nstruct Begun {"


def edit_patches(baked=None):
    """shop.cc's patches for an edit vehicle; baked: {flag: value} for a candidate bot, which has no trainer table
    (its flags are constants and its table is the edited emblem_table.h)."""
    defaults = ", ".join(f"{float((baked or {}).get(n, d))!r}f" for n, d in FLAGS) or "0.0f"
    if baked is not None:
        return [[(BEGUN, f"float lab_flag[] = {{{defaults}}};\n" + BEGUN)]] + FLAG_PATCHES
    return [
        [('#include "emblem_table.h"\n', '#include "emblem_table.h"\n#include "../draft/trainer.h"\n#include "../draft/edit_defs.h"\n#include <cstring>\n')],
        [(BEGUN, EDIT_WRAPPER.lstrip("\n").replace("FLAG_DEFAULTS", defaults) + BEGUN)],
        [(BEST, BEST + "    if (!lab_ready) lab_init();\n")],
        [("    const int arm = learned_arm[picks - 3][type][ordinal], family = arm / 3;\n",
          "    const int arm = lab_arm[picks - 3][type][ordinal], family = arm / 3;\n")],
    ] + FLAG_PATCHES


def patch_text(text, edits, rel):
    for alternatives in edits:
        old, new = next(((o, n) for o, n in alternatives if o in text), alternatives[0])
        assert text.count(old) == 1, f"{rel} patch point not found once: {old[:70]!r}"
        text = text.replace(old, new)
    return text


def edit_table_header(entries):
    """entries: [(key hex, team 0/1, [edit ids, at most 6])]. n = 0: the draft is the bot's own."""
    rows = sorted((int(k, 16), t, tuple(ids)) for k, t, ids in entries)
    for a, b in zip(rows, rows[1:]):
        assert a[:2] != b[:2], f"duplicate entry {a[:2]}"
    lines = [f"    {{0x{k:016x}ull, {t}, 0, 0, {{0, 0, 0, 0, 0}}, 0u, {{{', '.join(map(str, ids + (0,) * (6 - len(ids))))}}}}}," for k, t, ids in rows]
    lines.append("    {0xffffffffffffffffull, 255, 0, 0, {0, 0, 0, 0, 0}, 0u, {0, 0, 0, 0, 0, 0}},")
    return ("#pragma once\n// Generated by tools/emblab/evehicle.py: (map key, team, -, -, -, -, edit ids), sorted.\n"
            "namespace aph::trainer {\ninline constexpr Entry entries[] = {\n" + "\n".join(lines) + "\n};\n}\n")


def make_edit(source, name, entries, defs):
    """An edit vehicle: the source with shop.cc reading its table and flags through this game's edits. Only shop.cc
    changes (the draft is untouched). defs: edits.defs_header's text."""
    source, target = Path(source), vehicle.VARIANTS / name
    blobs = {p.relative_to(source).as_posix(): p.read_bytes() for p in (source / "src").rglob("*") if p.is_file()}
    blobs[SHOP] = patch_text(blobs[SHOP].decode(), edit_patches(), SHOP).encode()
    blobs["src/draft/trainer.h"] = (HERE / "trainer.h").read_bytes()
    blobs["src/draft/trainer_table.h"] = edit_table_header(entries).encode()
    blobs["src/draft/edit_defs.h"] = defs.encode()
    changed = [rel for rel, data in sorted(blobs.items()) if vehicle.write_if_changed(target / rel, data)]
    for path in sorted((target / "src").rglob("*"), reverse=True):
        if path.is_file() and path.relative_to(target).as_posix() not in blobs:
            path.unlink()
            changed.append(path.name)
    return target, bool(changed)


def bake_flags(bot, values):
    """A candidate bot directory's shop.cc with the flag hooks and these flag values as constants."""
    p = Path(bot) / SHOP
    p.write_text(patch_text(p.read_text(), edit_patches(values), SHOP))
