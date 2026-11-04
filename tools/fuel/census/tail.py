"""The budget tail of a --trace census: OOF turns by the last fuel check they passed (fuel left there, what it
needed, the scopes entered after it), the work veto's asks after it, finished turns' CLC lines (decide's spend
after its last check) and CLF lines (after the farm loop's last check), and OOF turns' components with and without
any passed check.

    py tools/fuel/census/tail.py replays/fuel/cen [VETO_LINE_BEFORE VETO_LINE_AFTER]

The two optional lines are model/pathing.cc's fuel() reads around veto_fn_ in the instrumented copy (they
move with the code); without them the veto columns are skipped.
"""
import sys, zipfile, re, statistics
from collections import Counter, defaultdict
from pathlib import Path

root = sys.argv[1]
VETO = (int(sys.argv[2]), int(sys.argv[3])) if len(sys.argv) > 3 else None


def q(xs, f):
    xs = sorted(xs)
    return xs[min(len(xs) - 1, int(f * len(xs)))] if xs else 0


cen, ctr, clc = {}, [], []
for z in sorted(Path(root).rglob("*.repl26a")):
    with zipfile.ZipFile(z) as f:
        for name in f.namelist():
            if not name.endswith(".stdout"):
                continue
            for ln in f.read(name).replace(b"\0", b"").decode(errors="replace").splitlines():
                p = ln.split()
                try:
                    if ln.startswith("CEN "):
                        cen[(z, name, int(p[1]), int(p[2]))] = ln
                    elif ln.startswith("CTR "):
                        ev = []
                        for tok in p[3:]:
                            try:
                                k, rest = tok.split(":", 1)
                                fl, l, fu, nd = rest.rsplit(":", 3)
                                ev.append((k, fl, int(l), int(fu), int(nd)))
                            except ValueError:
                                pass
                        ctr.append((z, name, int(p[1]), int(p[2]), ev))
                    elif ln.startswith("CLC "):
                        clc.append((p[3], int(p[4]), int(p[5]), int(p[6])))
                except (ValueError, IndexError):
                    pass

rows = defaultdict(list)
inner = defaultdict(Counter)
after_scopes = defaultdict(Counter)
for z, name, rnd, champ, ev in ctr:
    c = cen.get((z, name, rnd, champ), "")
    m = re.search(r" dpost (\d+)", c)
    dpost = int(m[1]) if m else 0
    stack = c.split(" stack ")[1].split(" |")[0] if " stack " in c else "?"
    last = max((i for i, e in enumerate(ev) if e[0] == "c"), default=-1)
    # Did decide start after the last check? (a 'decide' scope entry after it)
    if last >= 0:
        k, fl, l, fu, nd = ev[last]
        site = f"{fl}:{l}"
    else:
        site, fu, nd = "(none)", 0, 0
    calls, spent, opened = 0, 0, None
    if VETO:
        for e in ev[max(last, 0):]:
            if e[0] == "r" and e[1] == "pathing.cc" and e[2] == VETO[0]:
                opened, calls = e[3], calls + 1
            elif e[0] == "r" and e[1] == "pathing.cc" and e[2] == VETO[1] and opened is not None:
                spent, opened = spent + opened - e[3], None
        if opened is not None:
            spent += opened
    rows[site].append((fu, nd, dpost, rnd, calls, spent, opened is not None))
    inner[site][stack.split("/")[-1]] += 1
    # Top scopes entered after the check (depth recorded in 'l' for e events)
    seen = set()
    for e in ev[max(last, 0):]:
        if e[0] == "e" and e[1] not in seen:
            seen.add(e[1])
            after_scopes[site][e[1]] += 1

n = sum(len(v) for v in rows.values())
print(f"OOF turns traced {n}")
print(f"{'site':24s} {'turns':>6s} {'%':>5s} {'left p50':>8s} {'need p50':>8s} {'marg p50':>8s}  veto: turns% calls fuel-p50 OOF-in  inner")
for site, lst in sorted(rows.items(), key=lambda kv: -len(kv[1])):
    fu = [r[0] for r in lst]
    nd = [r[1] for r in lst]
    mg = [r[0] - r[1] for r in lst]
    v = [r for r in lst if r[4]]
    veto = f"{100*len(v)//len(lst):3d}% {sum(r[4] for r in v)/max(1,len(v)):4.2f} {q([r[5] for r in v],.5):6d} {sum(r[6] for r in lst):5d}" if VETO else ""
    print(f"{site:24s} {len(lst):6d} {100*len(lst)/n:5.1f} {q(fu,.5):8d} {q(nd,.5):8d} {q(mg,.5):8d}  {veto}  {inner[site].most_common(4)}")
print("\nscopes entered after the last check (share of the site's turns)")
for site, lst in sorted(rows.items(), key=lambda kv: -len(kv[1]))[:10]:
    print(f"  {site}: " + ", ".join(f"{k} {100*v//len(lst)}%" for k, v in after_scopes[site].most_common(18)))

clf = defaultdict(list)
for z in sorted(Path(root).rglob("*.repl26a")):
    with zipfile.ZipFile(z) as f:
        for name in f.namelist():
            if name.endswith(".stdout"):
                for ln in f.read(name).replace(b"\0", b"").decode(errors="replace").splitlines():
                    if ln.startswith("CLF "):
                        p = ln.split()
                        try:
                            clf[p[2]].append((int(p[3]), int(p[4]), int(p[5])))
                        except (ValueError, IndexError):
                            pass
for k, lst in sorted(clf.items()):
    a = [x[2] for x in lst]
    print(f"\nCLF farm loop {'cut' if k == 'f' else 'done'} ({len(lst)} finished turns): decide after it p50 {q(a,.5)} p90 {q(a,.9)} p99 {q(a,.99)}, needed p50 {q([x[1] for x in lst],.5)}")
print(f"\nCLC (finished turns whose decide spent >8k after its last check): {len(clc)}")
by = defaultdict(list)
for s, fu, nd, after in clc:
    by[s].append((fu, nd, after))
print(f"{'site':28s} {'n':>6s} {'after p50':>9s} {'p90':>7s} {'p99':>7s} {'need p50':>8s} {'after-need p50':>8s}")
for s, lst in sorted(by.items(), key=lambda kv: -len(kv[1]))[:20]:
    a = [x[2] for x in lst]
    nd = [x[1] for x in lst]
    print(f"{s:28s} {len(lst):6d} {q(a,.5):9d} {q(a,.9):7d} {q(a,.99):7d} {q(nd,.5):8d} {q([x[2]-x[1] for x in lst],.5):8d}")

# Components of OOF turns, by class: (none) vs a check passed.
def comps(line):
    out = {}
    for m in re.finditer(r" (\S+?)=(\d+):(\d+):(\d+)", line.split(" | ", 1)[1] if " | " in line else ""):
        out[m[1]] = (int(m[2]), int(m[3]), int(m[4]))
    return out

cls = defaultdict(list)
for z, name, rnd, champ, ev in ctr:
    c = cen.get((z, name, rnd, champ))
    if not c:
        continue
    last = max((i for i, e in enumerate(ev) if e[0] == "c"), default=-1)
    k = "none" if last < 0 else "check"
    nn = int(re.search(r" nn (\d+)", c)[1])
    cls[k].append((comps(c), nn, rnd))
for k, lst in cls.items():
    print(f"\n== OOF turns, class {k}: {len(lst)}; enemies within 6: {Counter(min(x[1],3) for x in lst)}; rounds 300+: {sum(x[2]>300 for x in lst)}")
    tot = Counter(); cnt = Counter(); slf = Counter()
    for c, _, _ in lst:
        for name, (inc, se, calls) in c.items():
            tot[name] += inc; cnt[name] += 1; slf[name] += se
    for name, v in tot.most_common(45):
        print(f"  {name:24s} {100*cnt[name]//len(lst):3d}%  incl/turn-with {v//cnt[name]:6d}  self {slf[name]//cnt[name]:6d}")
