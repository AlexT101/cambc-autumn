"""Per-import call counts and fuel prices from fuelhook.tsv files (see fuelhook.c).

    python3 tools/fastengine/fuelhook/hook_report.py SYMS hook.tsv [...]

Each return address is mapped to the enclosing cambc function (the import closure or the helper that charges).
"""
import bisect
import collections
import re
import sys

sys.path.insert(0, __file__.rsplit("/", 2)[0])
import prof_analyze as pa  # noqa: E402


def main():
    addrs, rows = pa.load_syms(sys.argv[1])

    def sym(a):
        i = bisect.bisect_right(addrs, a) - 1
        return rows[i][2] if i >= 0 else "?"

    by = collections.defaultdict(collections.Counter)
    total = 0
    for path in sys.argv[2:]:
        for line in open(path):
            if line.startswith("#"):
                continue
            ret, amount, count = line.split()
            name = sym(int(ret, 16))
            m = pa.IMPORT_RX[0].search(name)
            m1 = pa.IMPORT_RX[1].search(name)
            key = m.group(1) if m else (m1.group(1) + "::" + m1.group(2)) if m1 else pa.short(name)[:110]
            by[key][int(amount)] += int(count)
            total += int(count)
    print("total charges", total)
    for key, amounts in sorted(by.items(), key=lambda kv: -sum(kv[1].values())):
        n = sum(amounts.values())
        fuel = sum(a * c for a, c in amounts.items())
        top = " ".join("%d:%d" % (a, c) for a, c in amounts.most_common(6))
        print("%9d %5.1f%% fuel %11d  %s\n          amounts(price:count) %s" % (n, 100 * n / total, fuel, key, top))


if __name__ == "__main__":
    main()
