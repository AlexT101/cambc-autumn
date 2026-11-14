"""Emblem lab round 5: the edit library. An edit is a policy-level change to ocean's emblem choice that a team plays
all game: a list of learned_arm cells (a table edit), lab flags (a structural edit, shop.cc hooks in evehicle.py), or
nothing (a placebo). A lab team plays the base plus a few non-conflicting edits (elab.py); efit.py estimates each.

    py tools/emblab/edits.py build --base bots/variants/oc-wakecold-500 --out replays/emblab/r5/edits.json [--structural]
    py tools/emblab/edits.py table --registry edits.json --base BOT --out bots/variants/NAME ID_OR_NAME...   # a candidate bot

The registry is append-only (an id never changes meaning) and carries a sha256 of its edits, printed by build: note
it before play. Edit fields: id (from 1), name, tier, cells [[picks - 3, type, ordinal, arm]], flags [[name, value]],
need (the draft pick a team must hold for the edit to do anything, or null), expect (an A/B's points, where known)."""
import argparse, collections, hashlib, json, re, shutil, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
TYPES = ["ryth", "vesper_vale", "vendetta", "cassi", "issac", "stellar", "prism", "marcella", "willow", "ren", "varg", "tavi", "heart_of_ruin"]
FAMILIES = ["monster", "power", "durability", "treasure", "jungle", "home", "bruiser", "tribute", "capture", "prospector", "hunter", "skirmish",
            "greed", "collectors"]
STATS = ["str", "foc", "hp"]
FAM = {f: i for i, f in enumerate(FAMILIES)}
NONE = 255
K = 12
PASSIVES = ["monster", "durability", "treasure", "jungle", "home", "tribute", "capture", "prospector", "hunter", "skirmish", "collectors"]
POOLED_AT = [1, 2, 3, 6, 8, 10]
ROW = re.compile(r"\{([\d, ]+)\}, // (\w+)")


def pick_of(t):
    """The draft pick that fields type t."""
    return "cassi_and_issac" if TYPES[t] in ("cassi", "issac") else TYPES[t]


def read_table(text):
    rows = [list(map(int, m.group(1).split(", "))) for m in ROW.finditer(text)]
    assert len(rows) == 39 and all(len(r) == K for r in rows)
    return [rows[p * 13:(p + 1) * 13] for p in range(3)]


def write_table(text, table):
    it = iter(r for p in table for r in p)
    return ROW.sub(lambda m: "{" + ", ".join(map(str, next(it))) + "}, // " + m.group(2), text)


def main_stats(table):
    """A type's usual stat: the commonest stat of its table arms from ordinal 3 on (collectors.py)."""
    out = {}
    for t in range(13):
        c = collections.Counter(x % 3 for p in range(3) for x in table[p][t][3:] if x != NONE)
        out[t] = c.most_common(1)[0][0] if c else 0
    return out


def diff(table, new):
    return [[p, t, k, new[p][t][k]] for p in range(3) for t in range(13) for k in range(K) if new[p][t][k] != table[p][t][k]]


def mapped(table, fn, types=None):
    """Cells of the table with fn(p, t, k, arm) -> arm applied to every cell (of `types`)."""
    new = [[[fn(p, t, k, a) if types is None or t in types else a for k, a in enumerate(r)] for t, r in enumerate(pt)] for p, pt in enumerate(table)]
    return diff(table, new)


def family_at(table, main, family, k, mode="ow", stat=None, types=None):
    """Family F as the k-th new emblem of every row with none at or before k, in the type's usual stat. ow: the cell
    is overwritten (collectors.py). ins: F is inserted and the row's later arms shift one later; a later F cell is
    taken out (the arm moves), else the row's last arm drops."""
    f = FAM[family]
    new = [[list(r) for r in pt] for pt in table]
    for p in range(3):
        for t in range(13):
            r = new[p][t]
            if (types is not None and t not in types) or any(x != NONE and x // 3 == f for x in r[:k + 1]):
                continue
            arm = f * 3 + (main[t] if stat is None else stat)
            if mode == "ow":
                r[k] = arm
            else:
                rest = r[k:]
                later = next((i for i, x in enumerate(rest) if x != NONE and x // 3 == f), None)
                rest = rest[:later] + rest[later + 1:] if later is not None else rest[:-1]
                new[p][t] = r[:k] + [arm] + rest
    return diff(table, new)


def library(base, structural=False):
    """Every edit, in id order. `base`: the bot directory whose table the edits change."""
    text = (Path(base) / "src/economy/emblem_table.h").read_text()
    table, edits = read_table(text), []
    main = main_stats(table)

    def add(name, tier, cells=(), flags=(), need=None, expect=None):
        edits.append({"name": name, "tier": tier, "cells": [list(c) for c in cells], "flags": [list(f) for f in flags], "need": need,
                      "expect": expect})

    fam = lambda a: a // 3 if a != NONE else -1  # noqa: E731
    # Anchors: changes clean A/Bs have measured (EXPERIMENTS "Emblem lab round 4 on ocean"; on 496 unless re-measured).
    add("no-table", "anchor", mapped(table, lambda p, t, k, a: NONE), expect=-3.0)
    add("no-early", "anchor", mapped(table, lambda p, t, k, a: NONE if k < 3 else a), expect=0.3)
    add("no-late", "anchor", mapped(table, lambda p, t, k, a: NONE if k >= 3 else a), expect=-1.9)
    add("no-late-collectors", "anchor", mapped(table, lambda p, t, k, a: NONE if k >= 3 and fam(a) == FAM["collectors"] else a), expect=-1.7)
    for f, e in (("home", -0.2), ("tribute", 0.0), ("monster", -0.3), ("durability", -0.1)):
        add(f"no-late-{f}", "anchor", mapped(table, lambda p, t, k, a, f=f: NONE if k >= 3 and fam(a) == FAM[f] else a), expect=e)
    add("collectors-k1", "anchor", family_at(table, main, "collectors", 1), expect=-1.3)
    add("collectors-k2", "anchor", family_at(table, main, "collectors", 2), expect=-0.6)
    # The Skirmish cell (CHANGES 499) out: every row's ordinal 4 back to the round-2 table's.
    old = read_table((ROOT / "bots/variants/oc-campsh-498/src/economy/emblem_table.h").read_text())
    add("no-skirmish4", "anchor", diff(table, [[[old[p][t][k] if k == 4 else a for k, a in enumerate(r)] for t, r in enumerate(pt)]
                                               for p, pt in enumerate(table)]), expect=-0.4)
    add("power-to-bruiser", "anchor", mapped(table, lambda p, t, k, a: FAM["bruiser"] * 3 + a % 3 if fam(a) == FAM["power"] else a))
    # Placebos: nothing changes. The typed ones go only to teams holding the pick, as typed edits do.
    for i in range(4):
        add(f"placebo-{i}", "placebo")
    for i, t in enumerate(["cassi_and_issac", "ren", "prism", "vendetta"]):
        add(f"placebo-{t}", "placebo", need=t)
    # Pooled: a passive family as everyone's k-th new emblem, overwriting the cell or inserted before it.
    known = {("prospector", 2): 0.0, ("collectors", 5): 0.1, ("monster", 8): 0.1, ("durability", 9): -0.1, ("home", 11): 0.0}
    seen = {json.dumps(sorted(e["cells"])) for e in edits}
    for f in PASSIVES:
        for k in sorted(set(POOLED_AT) | {kk for ff, kk in known if ff == f}):
            for mode in ("ow", "ins"):
                cells = family_at(table, main, f, k, mode)
                key = json.dumps(sorted(cells))
                if not cells or key in seen or (mode == "ins" and k not in POOLED_AT):
                    continue
                seen.add(key)
                add(f"{f}-k{k}-{mode}", "pooled", cells, expect=known.get((f, k)) if mode == "ow" else None)
    # Each type's rows back to the current logic.
    for t in range(13):
        add(f"row-off-{TYPES[t]}", "typed-row", mapped(table, lambda p, tt, k, a: NONE, types={t}), need=pick_of(t))
    if structural:
        import structural as st
        st.add_edits(add, table, main)
        # More placebos, screened from zero with the rest: their share of the survivors is the false-positive rate.
        for i in range(4, 12):
            add(f"placebo-{i}", "placebo")
    for i, e in enumerate(edits):
        e["id"] = i + 1
    return edits


def digest(edits):
    return hashlib.sha256(json.dumps([[e["id"], e["name"], sorted(e["cells"]), sorted(e["flags"]), e["need"]] for e in edits]).encode()).hexdigest()[:16]


def conflicts(a, b):
    """Whether two edits touch a common cell or flag (such a pair is never on one team)."""
    return bool({tuple(c[:3]) for c in a["cells"]} & {tuple(c[:3]) for c in b["cells"]}) or bool({f[0] for f in a["flags"]} & {f[0] for f in b["flags"]})


def load(path):
    reg = json.loads(Path(path).read_text())
    assert digest(reg["edits"]) == reg["sha"], "the registry's edits do not match its hash"
    return reg


def defs_header(reg, flag_names):
    """edit_defs.h: every edit's cells and flags by id, for the vehicle."""
    cells, first, flags, ffirst = [], [0, 0], [], [0, 0]
    for e in reg["edits"]:
        cells += [f"{{{p * 156 + t * 12 + k}, {a}}}" for p, t, k, a in e["cells"]]
        flags += [f"{{{flag_names.index(n)}, {float(v)!r}f}}" for n, v in e["flags"]]
        first.append(len(cells))
        ffirst.append(len(flags))
    wrap = lambda xs: ",\n    ".join(", ".join(xs[i:i + 16]) for i in range(0, len(xs), 16))  # noqa: E731
    return ("#pragma once\n// Generated by tools/emblab/edits.py from registry " + reg["sha"] + ": edit id -> learned_arm cells and lab flags.\n"
            "#include <cstdint>\nnamespace aph::trainer {\nstruct EditCell { std::uint16_t at; std::uint8_t arm; };\n"
            "struct EditFlag { std::uint16_t flag; float value; };\n"
            f"inline constexpr EditCell edit_cells[] = {{\n    {wrap(cells + ['{0, 0}'])}\n}};\n"
            f"inline constexpr std::uint32_t edit_first[] = {{\n    {wrap(list(map(str, first)))}\n}};\n"
            f"inline constexpr EditFlag edit_flags[] = {{\n    {wrap(flags + ['{0, 0.0f}'])}\n}};\n"
            f"inline constexpr std::uint32_t edit_flag_first[] = {{\n    {wrap(list(map(str, ffirst)))}\n}};\n"
            f"inline constexpr int edit_count = {len(reg['edits'])};\n}}\n")


def apply_cells(table, edits):
    new = [[list(r) for r in pt] for pt in table]
    touched = set()
    for e in edits:
        for p, t, k, a in e["cells"]:
            assert (p, t, k) not in touched, f"{e['name']} conflicts with an earlier edit"
            touched.add((p, t, k))
            new[p][t][k] = a
    return new


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("command", choices=["build", "table", "list"])
    ap.add_argument("--base")
    ap.add_argument("--out")
    ap.add_argument("--registry")
    ap.add_argument("--structural", action="store_true", help="add the structural (flag) edits (structural.py)")
    ap.add_argument("ids", nargs="*")
    a = ap.parse_args()
    if a.command == "build":
        edits = library(ROOT / a.base, a.structural)
        out = Path(a.out)
        if out.is_file():  # append-only: an existing id keeps its meaning
            old = load(out)["edits"]
            for o, n in zip(old, edits):
                assert (o["name"], sorted(o["cells"]), sorted(o["flags"]), o["need"]) == (n["name"], sorted(n["cells"]), sorted(n["flags"]), n["need"]), \
                    f"edit {o['id']} ({o['name']}) would change"
            assert len(edits) >= len(old)
        reg = {"base": a.base, "sha": digest(edits), "edits": edits}
        out.write_text(json.dumps(reg) + "\n")
        print(f"{len(edits)} edits, sha {reg['sha']}: {dict(collections.Counter(e['tier'] for e in edits))}")
        return
    reg = load(a.registry)
    if a.command == "list":
        for e in reg["edits"]:
            print(f"{e['id']:4} {e['tier']:10} {e['name']:32} cells {len(e['cells']):3} flags {e['flags']} need {e['need']} expect {e['expect']}")
        return
    by = {str(e["id"]): e for e in reg["edits"]} | {e["name"]: e for e in reg["edits"]}
    chosen = [by[i] for i in a.ids]
    import evehicle
    src, out = ROOT / a.base, ROOT / a.out
    if out.exists():
        shutil.rmtree(out)
    shutil.copytree(src, out, ignore=shutil.ignore_patterns(".cambc", "compile_commands.json", "vehicle.json"))
    p = out / "src/economy/emblem_table.h"
    text = p.read_text()
    p.write_text(write_table(text, apply_cells(read_table(text), chosen)))
    flags = [f for e in chosen for f in e["flags"]]
    if flags:
        evehicle.bake_flags(out, dict(flags))
    print(f"{a.out}: {[e['name'] for e in chosen]}, {sum(len(e['cells']) for e in chosen)} cells, flags {flags}")


if __name__ == "__main__":
    sys.path.insert(0, str(HERE))
    main()
