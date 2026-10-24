"""Generate zz_harness.cpp: a wrapper for every engine import a bot uses, linked in place of the import.

The bot's own object files are untouched: their calls to the `sdk_*` import symbols resolve to these
definitions, which call the real import under another symbol name and then run a hook. The hook is in
harness_rec.h (recorder: logs fuel readings, out-of-fuel points and per-turn call hashes, refunding its
own fuel exactly) or harness_trace.h (tracer: replays the recorder's fuel readings and out-of-fuel
points, and checks the calls against the recorder's hashes).

    py tools/replay/harness/gen_wrappers.py --mode rec|trace --wasm BOT.wasm --sdk SDK/cpp --out DIR/zz_harness.cpp [--costs costs.json]

--wasm lists the imports to wrap (those the bot really uses). --costs gives each wrapper's unpaused
operator count (from count_ops.py on a build; for rec mode count_ops.py --split, [pre, post] per
wrapper); without it they are 0 (the calibration build).
Trace mode needs --rec-table (the recorder's zz_harness.json): a call hashes with the recorder's id
for its import, and an import the recorder never wrapped gets id 1000 + its index. The debug-only
fuel_pause/fuel_resume/fuel_adjust are left unwrapped.
"""
import argparse
import json
import re
import struct
from pathlib import Path

DECL = re.compile(r'(?:BC_IMPORT\("([^"]+)"\)|__attribute__\(\(import_module\("env"\), import_name\("([^"]+)"\)\)\))\s*'
                  r'((?:const\s+)?[\w:]+(?:\s*\*)?)\s+(sdk_\w+)\s*\(([^)]*)\)\s*;', re.S)


def wasm_imports(path):
    b = Path(path).read_bytes()
    p = 8

    def leb():
        nonlocal p
        r = s = 0
        while True:
            x = b[p]
            p += 1
            r |= (x & 127) << s
            s += 7
            if not x & 128:
                return r

    def name():
        nonlocal p
        n = leb()
        v = b[p:p + n].decode()
        p += n
        return v

    out = []
    while p < len(b):
        sid = b[p]
        p += 1
        size = leb()
        start = p
        if sid == 2:
            for _ in range(leb()):
                mod, field = name(), name()
                kind = b[p]
                p += 1
                if kind != 0:
                    raise ValueError("non-function import")
                leb()
                out.append((mod, field))
        p = start + size
    return out


def ctype(t):
    t = t.strip()
    if "*" in t:
        return "void*", "ptr"
    base = t.replace("const", "").replace("std::", "").strip()
    if base == "void":
        return "void", "void"
    if base in ("int64_t",):
        return "int64_t", "i64"
    if base in ("uint64_t",):
        return "uint64_t", "i64"
    if base == "float":
        return "float", "f32"
    if base == "double":
        return "double", "f64"
    if base in ("int32_t", "int"):
        return "int32_t", "i32"
    if base in ("uint32_t", "size_t", "uint16_t", "uint8_t", "unsigned"):
        return {"uint32_t": "uint32_t", "size_t": "uint32_t", "uint16_t": "uint16_t", "uint8_t": "uint8_t", "unsigned": "uint32_t"}[base], "u32"
    raise ValueError(f"unknown type {t}")


# Trace mode: imports that act, logged as TA lines.
ACTIONS = {"attack", "cast_with_result", "move_to_with_result", "place_ward_with_result", "recall", "cancel_channel",
           "submit_gems", "buy_item", "buy_consumable", "use_consumable_with_result", "set_priority", "sell"}


def parse_sdk(sdk):
    text = (Path(sdk) / "imports.h").read_text(encoding="utf-8") + (Path(sdk) / "cambc.h").read_text(encoding="utf-8")
    text = re.sub(r"///[^\n]*", "", text)
    decls = {}
    for m in DECL.finditer(text):
        imp = m.group(1) or m.group(2)
        ret, fn, params = m.group(3), m.group(4), m.group(5)
        ps = []
        for prm in [x.strip() for x in params.split(",") if x.strip()]:
            prm = re.sub(r"\s+[a-z_]\w*$", "", prm) if not prm.endswith("*") else prm
            ps.append(ctype(prm))
        decls[imp] = (fn, ctype(ret), ps)
    return decls


def rec_wrapper(i, imp, fn, rt, rk, real, plist, alist, hv, cost):
    """Recorder wrapper (harness_rec.h): pause/hook/resume around the real import, as direct import
    calls so that the wrapper adds no fuel check after the import. cost: [pre, post] unpaused
    operators from count_ops.py --split ([0, 0] for the first, calibration build)."""
    pre, post = cost if isinstance(cost, list) else (0, 0)
    head = f"__attribute__((noinline)) {rt} {fn}({plist}) {{ hr_pause(); "
    pre_hook = f"hk_pre_yield({i}, {pre})" if imp == "yield" else f"hk_pre({i}, {pre})"
    if imp == "yield":
        post_hook = f"hk_post_yield({i}, {post})"
    elif imp == "fuel_remaining":
        post_hook = f"hk_post_fuel({i}, {post}, r)"
    else:
        rhash = "(uint32_t)r" if rk in ("i32", "u32") else "0"
        post_hook = f"hk_post({i}, {post}, {rhash if rk != 'void' else '0'}, {', '.join(hv)})"
    if rk == "void":
        return head + f"{pre_hook}; hr_resume(); {real}({alist}); hr_pause(); {post_hook}; hr_resume(); }}"
    return head + f"{pre_hook}; hr_resume(); {rt} r = {real}({alist}); hr_pause(); {post_hook}; hr_resume(); return r; }}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["rec", "trace"], required=True)
    ap.add_argument("--wasm", help="the bot whose imports to wrap")
    ap.add_argument("--all", action="store_true", help="wrap every import the SDK declares (the linker drops unused ones)")
    ap.add_argument("--sdk", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--costs")
    ap.add_argument("--exclude", default="", help="comma-separated imports left unwrapped (diagnostics)")
    ap.add_argument("--rec-table", help="trace mode: the recorder's zz_harness.json")
    args = ap.parse_args()
    decls = parse_sdk(args.sdk)
    costs = json.loads(Path(args.costs).read_text(encoding="utf-8")) if args.costs else {}
    excluded = set(filter(None, args.exclude.split(",")))
    if args.mode == "trace":
        excluded |= {"fuel_pause", "fuel_resume", "fuel_adjust"}
        if not args.rec_table:
            raise SystemExit("--mode trace needs --rec-table")
        rec_ids = {e["import"]: e["id"] for e in json.loads(Path(args.rec_table).read_text(encoding="utf-8"))}
    if args.all:
        used = [f for f in decls if f not in excluded]
    elif args.wasm:
        used = [f for m, f in wasm_imports(args.wasm) if m == "env" and f not in excluded]
    else:
        raise SystemExit("--wasm or --all")
    special = {"fuel_remaining", "yield"}
    lines = [
        "// Generated by tools/replay/harness/gen_wrappers.py: do not edit.",
        "#include <cstdint>",
        f'#include "harness_{args.mode}.h"',
        'extern "C" {',
    ]
    table = []
    for i, imp in enumerate(sorted(used)):
        if imp not in decls:
            raise SystemExit(f"import {imp} not declared in the SDK")
        fn, (rt, rk), ps = decls[imp]
        real = f"rr_{imp}"
        plist = ", ".join(f"{t} a{j}" for j, (t, _) in enumerate(ps))
        alist = ", ".join(f"a{j}" for j in range(len(ps)))
        lines.append(f'__attribute__((import_module("env"), import_name("{imp}"))) {rt} {real}({", ".join(t for t, _ in ps)});')
        # Hash only values that do not depend on memory layout: no pointers.
        hv = [f"(uint32_t)a{j}" if k in ("i32", "u32") else f"hk_f32(a{j})" if k == "f32" else f"(uint32_t)a{j}" if k == "i64" else None
              for j, (t, k) in enumerate(ps)]
        hv = [h for h in hv if h][:3]
        hv += ["0"] * (3 - len(hv))
        cost = costs.get(fn, 0)
        if args.mode == "trace":
            i, cost = rec_ids.get(imp, 1000 + i), 0
        table.append({"id": i, "import": imp, "fn": fn})
        if args.mode == "rec":
            lines.append(rec_wrapper(i, imp, fn, rt, rk, real, plist, alist, hv, costs.get(fn)))
            continue
        if imp == "fuel_remaining":
            lines.append(f"__attribute__((noinline)) {rt} {fn}() {{ return hk_fuel({i}, {cost}, {real}()); }}")
        elif imp == "yield":
            lines.append(f"__attribute__((noinline)) void {fn}() {{ hk_yield({i}, {cost}); {real}(); hk_resumed({i}); }}")
        elif rk == "void":
            lines.append(f"__attribute__((noinline)) void {fn}({plist}) {{ HK_PRE({i}); {real}({alist}); hk({i}, {cost}, 0, {', '.join(hv)}); }}")
        else:
            rhash = "(uint32_t)r" if rk in ("i32", "u32") else "0"
            act = ""
            if args.mode == "trace" and imp in ACTIONS:
                ints = [f"(int32_t)a{j}" for j, (t, k) in enumerate(ps) if k in ("i32", "u32")]
                res = f"r == 0 ? *(int32_t*)a{len(ps) - 1} : -1" if imp.endswith("_with_result") else "-1"
                act = f' ht_act("{imp}", r, {res}, {len(ints)}, {", ".join((ints + ["0"] * 5)[:5])});'
            lines.append(f"__attribute__((noinline)) {rt} {fn}({plist}) {{ HK_PRE({i}); {rt} r = {real}({alist}); hk({i}, {cost}, {rhash}, {', '.join(hv)});{act} return r; }}")
    lines.append("}")
    Path(args.out).write_text("\n".join(lines) + "\n", encoding="utf-8")
    Path(args.out).with_suffix(".json").write_text(json.dumps(table, indent=0))
    print(f"{len(table)} wrappers -> {args.out}")


if __name__ == "__main__":
    main()
