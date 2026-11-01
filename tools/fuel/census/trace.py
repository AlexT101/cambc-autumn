"""Reads the CTR lines of a census built with --trace: for each turn that ran out, the last fuel check it passed,
what that check needed, and the work after it (the scopes entered and the fuel spent between events).

    py tools/fuel/census/trace.py replays/fuel/cen [--show N] [--site farm.cc:1271]

Groups turns by the last passed check (file:line), with the fuel left there and the margin over what it needed,
then lists the costliest stretches between consecutive events after it. --show prints N sample traces.
"""
import sys
import zipfile
from collections import Counter, defaultdict
from pathlib import Path


def lines(root):
    for z in sorted(Path(root).rglob("*.repl26a")):
        try:
            with zipfile.ZipFile(z) as f:
                for name in f.namelist():
                    if name.endswith(".stdout"):
                        for ln in f.read(name).replace(b"\0", b"").decode(errors="replace").splitlines():
                            yield z, name, ln
        except zipfile.BadZipFile:
            pass


def parse_ctr(ln):
    parts = ln.split()
    rnd, champ = int(parts[1]), int(parts[2])
    ev = []
    pending = ""
    for tok in parts[3:]:
        tok = pending + tok
        if tok.count(":") < 4:  # a label with a space ("comms receive")
            pending = tok + "_"
            continue
        pending = ""
        try:
            k, rest = tok.split(":", 1)
            f, l, fu, nd = rest.rsplit(":", 3)
            ev.append((k, f, int(l), int(fu), int(nd)))
        except ValueError:  # another line's output interleaved
            pass
    return rnd, champ, ev


def label(e):
    k, f, l, fu, nd = e
    return f"{f}" if k in "ex" else f"{f}:{l}"


def main():
    root = sys.argv[1]
    show = int(sys.argv[sys.argv.index("--show") + 1]) if "--show" in sys.argv else 0
    site = sys.argv[sys.argv.index("--site") + 1] if "--site" in sys.argv else None
    cen = {}
    turns = []
    for z, name, ln in lines(root):
        if ln.startswith("CEN "):
            p = ln.split()
            cen[(z, name, int(p[1]), int(p[2]))] = ln
        elif ln.startswith("CTR "):
            rnd, champ, ev = parse_ctr(ln)
            turns.append((z, name, rnd, champ, ev))
    by_site = defaultdict(list)
    stretch = Counter()
    stretch_fuel = Counter()
    for z, name, rnd, champ, ev in turns:
        last = max((i for i, e in enumerate(ev) if e[0] == "c"), default=-1)
        key = label(ev[last]) if last >= 0 else "(none)"
        c = cen.get((z, name, rnd, champ), "")
        stack = c.split(" stack ")[1].split(" |")[0] if " stack " in c else "?"
        by_site[key].append((z, name, rnd, champ, ev, last, stack))
        start = max(last, 0)
        tail = ev[start:] + [("o", "OOF", 0, 0, 0)]
        for a, b in zip(tail, tail[1:]):
            d = a[3] - b[3]
            # Scope entries are named by their label; reads and checks by site.
            k = f"{label(a)} -> {label(b)}"
            stretch[k] += 1
            stretch_fuel[k] += d
    n = len(turns)
    print(f"traced OOF turns: {n}")
    print("\n== last passed check (site): turns, fuel there mean/median, needed mean, margin mean")
    for key, lst in sorted(by_site.items(), key=lambda kv: -len(kv[1]))[:30]:
        fu = sorted(t[4][t[5]][3] for t in lst if t[5] >= 0) or [0]
        nd = [t[4][t[5]][4] for t in lst if t[5] >= 0] or [0]
        stacks = Counter(t[6].split("/")[-1] for t in lst).most_common(3)
        print(f"  {key:28s} {len(lst):5d} ({100*len(lst)/n:4.1f}%)  left {sum(fu)//len(fu):6d} / {fu[len(fu)//2]:6d}"
              f"  needed {sum(nd)//len(nd):6d}  margin {(sum(fu)-sum(nd))//len(fu):6d}  inner: {stacks}")
    print("\n== costliest stretches after the last passed check (summed fuel, count, mean)")
    for k, v in stretch_fuel.most_common(40):
        print(f"  {v:10d} {stretch[k]:5d} {v//stretch[k]:7d}  {k}")
    shown = 0
    for key, lst in sorted(by_site.items(), key=lambda kv: -len(kv[1])):
        if site and key != site:
            continue
        for z, name, rnd, champ, ev, last, stack in lst:
            if shown >= show:
                break
            shown += 1
            print(f"\n-- {z.parent.name}/{z.name} {name} r{rnd} c{champ} stack {stack}")
            for e in ev[max(0, last - 3):]:
                k, f, l, fu, nd = e
                print(f"   {k} {f}:{l} fuel {fu} needed {nd}")


if __name__ == "__main__":
    main()
