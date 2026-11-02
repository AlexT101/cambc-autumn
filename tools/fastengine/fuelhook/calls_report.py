"""Host calls per import from fuelhook's FUELHOOK_CALLS output, named by the import's closure and the wasm import
it is linked to when known (IMPORT_NAMES, filled from cambc's import table order where verified).

    python3 tools/fastengine/fuelhook/calls_report.py SYMS calls.tsv [...]
"""
import bisect
import collections
import re
import sys

sys.path.insert(0, __file__.rsplit("/", 2)[0])
import prof_analyze as pa  # noqa: E402


def closure_key(name):
    m = re.search(r"<(runner::[a-z_:]+(?:imports)?)(?:<[^{]*?>)?(::\{closure#\d+\}(?:::\{closure#\d+\})*) as wasmtime::runtime::func::IntoFunc", name)
    if m:
        return m.group(1) + m.group(2)
    m = re.search(r"linker<runner::api::imports<[^{]*\{closure#0\}>::(\{closure#\d+\})", name)
    if m:
        return "wasm_runtime::Runtime::linker::" + m.group(1)
    m = re.search(r"wasmtime_wasi[^ ]*?add_to_linker[^ ]*?::(\{closure#\d+\})", name)
    if m:
        return "wasi::" + m.group(1)
    return pa.short(name)[:120]


def main():
    addrs, rows = pa.load_syms(sys.argv[1])
    exact = {a: r[2] for a, r in zip(addrs, rows)}
    calls = collections.Counter()
    for path in sys.argv[2:]:
        for line in open(path):
            off, n = line.split()
            name = exact.get(int(off, 16), "?")
            if not name.startswith("<wasmtime::runtime::func::HostFunc>::array_call_trampoline"):
                continue  # catch_unwind_and_record_trap instances share the pattern; count each call once
            calls[closure_key(exact.get(int(off, 16), "?"))] += int(n)
    total = sum(calls.values())
    print("total host calls", total)
    for k, v in calls.most_common():
        print("%10d %5.1f%%  %s" % (v, 100 * v / total, k))


if __name__ == "__main__":
    main()
