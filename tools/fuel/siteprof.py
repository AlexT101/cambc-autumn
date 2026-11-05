"""Fuel by wasm function from fast-runner site traces.

    FASTRUNNER_MODE=native FASTRUNNER_TRACE_SITES=1 FASTRUNNER_TRACE_FUEL=t.tr \\
        tools/fastengine/runner/fastrunner run BOT BOT --map MAP -o DIR
    py tools/fuel/siteprof.py WASM TRACE [TRACE ...] [--vs WASM2 TRACE2 [...]] [--top N]

A trace line is the fuel counter at a host call and its site (function index:offset). The fuel spent since the
previous host call is charged to the function making this call: a flat (leaf-ish) profile of the code between host
calls, not inclusive of callees. Jumps between turns and fuel chunks (a drop or a gap over --max) are skipped. Play
both sides with the same bot so every line names one wasm's functions. WASM is the bot's built
`.cambc/build/bot.wasm` (its name section). With --vs, prints both profiles per game and their difference.
"""
import argparse, collections, re


def leb(b, i):
    r = s = 0
    while True:
        x = b[i]
        i += 1
        r |= (x & 0x7F) << s
        s += 7
        if x < 0x80:
            return r, i


def names(path):
    b = open(path, "rb").read()
    i, out = 8, {}
    while i < len(b):
        sid = b[i]
        size, j = leb(b, i + 1)
        end = j + size
        if sid == 0:
            n, k = leb(b, j)
            if b[k:k + n] == b"name":
                k += n
                while k < end:
                    sub, k = leb(b, k)
                    ssz, k = leb(b, k)
                    if sub == 1:
                        cnt, m = leb(b, k)
                        for _ in range(cnt):
                            idx, m = leb(b, m)
                            ln, m = leb(b, m)
                            out[idx] = b[m:m + ln].decode("utf-8", "replace")
                            m += ln
                    k += ssz
        i = end
    return out


def demangle(n):
    # The name section holds demangled C++ names: cut at the argument list, keep the anonymous namespace out.
    n = n.replace("(anonymous namespace)::", "")
    depth = 0
    for i, ch in enumerate(n):
        if ch == "<":
            depth += 1
        elif ch == ">":
            depth -= 1
        elif ch == "(" and depth == 0 and i > 0:
            return n[:i][-90:]
    return n[-90:]


def profile(traces, cap):
    by = collections.Counter()
    total = 0
    for t in traces:
        prev = None
        with open(t) as f:
            for line in f:
                v, _, site = line.partition(" ")
                v = int(v)
                if prev is not None and 0 <= v - prev <= cap:
                    fn = int(site.split(":")[0], 16)
                    by[fn] += v - prev
                    total += v - prev
                prev = v
    return by, total


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("wasm")
    ap.add_argument("traces", nargs="+")
    ap.add_argument("--vs", nargs="+", help="WASM2 TRACE2 [...]: a second bot's profile to compare")
    ap.add_argument("--top", type=int, default=40)
    ap.add_argument("--max", type=int, default=100000, help="largest delta charged (bigger is a chunk or turn jump)")
    a = ap.parse_args()
    n1 = names(a.wasm)
    p1, t1 = profile(a.traces, a.max)
    g1 = len(a.traces)
    agg1 = collections.Counter()
    for k, v in p1.items():
        agg1[demangle(n1.get(k, f"f{k}"))] += v
    if not a.vs:
        print(f"total {t1 / g1:.0f} per game over {g1} games")
        for name, v in agg1.most_common(a.top):
            print(f"{v / g1:12.0f} {100 * v / t1:5.1f}%  {name}")
        return
    n2 = names(a.vs[0])
    p2, t2 = profile(a.vs[1:], a.max)
    g2 = len(a.vs) - 1
    agg2 = collections.Counter()
    for k, v in p2.items():
        agg2[demangle(n2.get(k, f"f{k}"))] += v
    print(f"total per game: A {t1 / g1:.0f} ({g1} games)  B {t2 / g2:.0f} ({g2} games)")
    keys = set(agg1) | set(agg2)
    rows = sorted(keys, key=lambda k: -(agg1[k] / g1 - agg2[k] / g2))
    print(f"{'A/game':>12s} {'B/game':>12s} {'A-B':>12s}  function")
    for k in rows[:a.top]:
        print(f"{agg1[k] / g1:12.0f} {agg2[k] / g2:12.0f} {agg1[k] / g1 - agg2[k] / g2:+12.0f}  {k}")


if __name__ == "__main__":
    main()
