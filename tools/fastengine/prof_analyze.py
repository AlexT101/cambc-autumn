"""Where a `cambc run` spends its time, from a samply profile.

    python3 tools/fastengine/prof_analyze.py PROFILE.json.gz [PROFILE2 ...] --syms SYMS [--imports] [--leaves N] [--json OUT]

PROFILE is `samply record --save-only` output (samply needs /proc/sys/kernel/perf_event_paranoid <= 1; see
profile_games.sh). SYMS is cambc's symbol table:

    nm -C -S --defined-only cambc | grep -E '^[0-9a-f]+ ([0-9a-f]+ )?[TtWw] ' > cambc.syms

Frames outside every mapped library are wasmtime's JIT code: the bots' compiled WASM, fuel metering included.
Each sample gets one category (CATEGORIES, first match wins), from its leaf frame and whether a JIT frame is on the
stack. --imports also splits host-call samples by the import closure the bot called (runner::api::...{closure#N}).
"""
import bisect
import collections
import gzip
import json
import re
import sys


def load_syms(path):
    rows = []
    for line in open(path, encoding="utf-8", errors="replace"):
        m = re.match(r"^([0-9a-f]+) (?:([0-9a-f]+) )?([A-Za-z]) (.*)$", line.rstrip("\n"))
        if m:
            addr, size, _kind, name = m.groups()
            rows.append((int(addr, 16), int(size or "0", 16), re.sub(r"::h[0-9a-f]{16}$", "", name)))
    rows.sort()
    return [r[0] for r in rows], rows


def short(name):
    name = re.sub(r"<[^<>]*(<[^<>]*(<[^<>]*>[^<>]*)*>[^<>]*)*>", "<..>", name)
    return name[:150]


ENGINE = re.compile(r"^(Game_|Engine::|Deep::|Bitboard_|DistanceField_|Managed_)")
EXPORT_LOOKUP = re.compile(r"hash_one|sip::Hasher|DefaultHasher|get_atom|StringPool|IndexMap<wasmtime_environ|"
                           r"get_export|_get_export|get_exported_memory")
STARTUP = re.compile(r"ZSTD|zstd|sha2::|deserialize|cranelift|wasmtime_cache|object::|gimli|Module>::from|"
                     r"Engine>::new|wasmtime::runtime::module|wasmtime::runtime::instance|_dl_|ld-linux")
REPLAY = re.compile(r"miniz_oxide|zip::|flate2|SaveReplay|encode|crc32")

CATEGORIES = [
    "bot JIT code (WASM + fuel metering)",
    "engine work under host calls (C++ Game_/Engine::, incl. its memcpy)",
    "altar_locks map scan (runner::engine::ffi::visible_altar_locks)",
    "export lookup per host call (Caller::get_export(\"memory\") hashing)",
    "other host-call glue (trampolines, catch_unwind, guest_ptr, charge_fuel, fuel meter)",
    "game loop outside bots (engine phases, runner)",
    "replay/fuel file writing",
    "startup (module cache load, instantiation, process)",
    "other, no JIT frame",
]


def classify(frames):
    """frames: [(lib, name)] leaf first; lib 'JIT' for anonymous code."""
    lib, name = frames[0]
    jit_on_stack = any(f[0] == "JIT" for f in frames)
    if lib == "JIT":
        return CATEGORIES[0]
    if jit_on_stack:
        upto = next(i for i, f in enumerate(frames) if f[0] == "JIT")
        inner = frames[:upto]
        if any("visible_altar_locks" in f[1] for f in inner):
            return CATEGORIES[2]
        if ENGINE.search(name) or (lib != "cambc" and any(ENGINE.search(f[1]) for f in inner[1:3])):
            return CATEGORIES[1]
        if EXPORT_LOOKUP.search(name):
            return CATEGORIES[3]
        return CATEGORIES[4]
    names = " ".join(f[1] for f in frames[:12])
    if REPLAY.search(names):
        return CATEGORIES[6]
    if STARTUP.search(names) or lib.startswith("ld-linux"):
        return CATEGORIES[7]
    if ENGINE.search(names) or "runner::" in names:
        return CATEGORIES[5]
    return CATEGORIES[8]


IMPORT_RX = [
    re.compile(r"(runner::api::[a-z_:]*imports(?:::<[^{]*>)?::\{closure#\d+\}::\{closure#\d+\})"),
    re.compile(r"<(runner::[a-z_:]+)[^ ]*?(\{closure#\d+\}(?:::\{closure#\d+\})*) as wasmtime::runtime::func::IntoFunc"),
]


def import_key(frames):
    if frames[0][0] == "JIT" or not any(f[0] == "JIT" for f in frames):
        return None
    upto = next(i for i, f in enumerate(frames) if f[0] == "JIT")
    callee = frames[upto - 1][1]
    m = IMPORT_RX[0].search(callee)
    if m:
        return m.group(1)
    m = IMPORT_RX[1].search(callee)
    if m:
        return m.group(1) + "::" + m.group(2)
    if "wasmtime_wasi" in callee:
        return "wasi"
    return short(callee)[:90]


def analyse(prof_path, addrs, rows, want_imports, nleaves):
    def sym(addr):
        i = bisect.bisect_right(addrs, addr) - 1
        return rows[i][2] if i >= 0 else "cambc@%x" % addr

    p = json.load(gzip.open(prof_path))
    libs = p["libs"]
    cats = collections.Counter()
    imports = collections.Counter()
    import_leaf = collections.defaultdict(collections.Counter)
    leaves = collections.Counter()
    n = 0
    for t in p["threads"]:
        st, ft, fn, rt = t["stackTable"], t["frameTable"], t["funcTable"], t["resourceTable"]
        cache = {}

        def frame(fi):
            v = cache.get(fi)
            if v is None:
                res = fn["resource"][ft["func"][fi]]
                if res is None or res < 0:
                    v = ("JIT", "JIT")
                else:
                    lib = libs[rt["lib"][res]]["name"]
                    v = (lib, sym(ft["address"][fi]) if lib == "cambc" else lib)
                cache[fi] = v
            return v

        for s in t["samples"]["stack"]:
            if s is None:
                continue
            frames = []
            while s is not None:
                frames.append(frame(st["frame"][s]))
                s = st["prefix"][s]
            n += 1
            cats[classify(frames)] += 1
            leaves[short(frames[0][1])] += 1
            if want_imports:
                k = import_key(frames)
                if k:
                    imports[k] += 1
                    import_leaf[k][short(frames[0][1])[:80]] += 1
    return n, cats, imports, import_leaf, leaves


def main():
    args = sys.argv[1:]
    syms = args[args.index("--syms") + 1]
    want_imports = "--imports" in args
    nleaves = int(args[args.index("--leaves") + 1]) if "--leaves" in args else 0
    out = args[args.index("--json") + 1] if "--json" in args else None
    skip = {syms, out, str(nleaves)}
    profiles = [a for a in args if not a.startswith("--") and a not in skip]
    addrs, rows = load_syms(syms)
    report = {}
    for prof in profiles:
        n, cats, imports, import_leaf, leaves = analyse(prof, addrs, rows, want_imports, nleaves)
        report[prof] = {"samples": n, "categories": {c: cats[c] for c in CATEGORIES}}
        print("\n### %s  (%d samples)" % (prof, n))
        for c in CATEGORIES:
            print("%6.2f%%  %7d  %s" % (100 * cats[c] / n, cats[c], c))
        if want_imports:
            print("  -- host calls by import closure --")
            for k, v in imports.most_common(25):
                top = ", ".join("%s %d" % (l, c) for l, c in import_leaf[k].most_common(2))
                print("  %6.2f%%  %6d  %s   [%s]" % (100 * v / n, v, k, top))
        if nleaves:
            print("  -- leaf symbols --")
            for k, v in leaves.most_common(nleaves):
                print("  %6.2f%%  %6d  %s" % (100 * v / n, v, k))
    if out:
        json.dump(report, open(out, "w"), indent=1)


if __name__ == "__main__":
    main()
