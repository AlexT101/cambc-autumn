"""mkan.py GAMES_DIR...: tabulate mkprof.py's MK lines (per farm loop: key moves, fact recomputes, their fuel)."""
import collections, re, sys, zipfile
from pathlib import Path

CTX_BITS = ["bag", "short_by", "banking", "emblems", "sticky"]
CLR_BITS = ["version", "strength", "reflect", "spells", "basic", "range", "survivable"]
KEY_CLR = ["strength", "reflect", "spells", "basic", "range"]


def lines(dirs):
    for d in dirs:
        for b in sorted(Path(d).rglob("*.repl26a")):
            with zipfile.ZipFile(b) as z:
                for team in "ab":
                    try:
                        out = z.read(f"team-{team}.stdout").replace(b"\0", b"").decode("utf-8", "replace")
                    except KeyError:
                        continue
                    for line in out.splitlines():
                        if line.startswith("MK "):
                            yield b, team, line


num = re.compile(r"^([a-zA-Z]+)(-?[\d.e+-]+(?:>-?[\d.e+-]+)?(?:/[\d.e+-]+)*)$")


def parse(line):
    head, _, rest = line.partition(" CR")
    t = head.split()
    r = {"round": int(t[1]), "h": int(t[2])}
    for tok in t[3:]:
        m = num.match(tok)
        if not m:
            continue
        k, v = m.groups()
        if ">" in v:
            a, b = v.split(">")
            r[k] = (float(a), float(b))
        elif "/" in v:
            r[k] = [int(x) for x in v.split("/")]
        else:
            r[k] = int(v) if v.lstrip("-").isdigit() else float(v)
    sec = {}
    cur = None
    for tok in ("CR" + rest).split():
        if tok in ("CR", "CF", "GR", "KR", "KF"):
            cur = tok
            sec[cur] = []
        else:
            sec[cur].append([int(x) for x in tok.split(":")])
    r["sec"] = sec
    return r


def main():
    loops = []
    bad = [0]
    for b, team, line in lines(sys.argv[1:]):
        try:
            r = parse(line)
        except Exception:
            bad[0] += 1
            continue
        if not all(k in r for k in ("f", "c", "b", "o", "L", "ctx", "clr", "kf", "fast", "gold", "cm", "gm", "km")):
            bad[0] += 1
            continue
        okv = all(len(e) == {"CR": 4, "CF": 2, "GR": 3, "KR": 3, "KF": 2}[s_] for s_, es in r["sec"].items() for e in es) and line.count(" CR") == 1
        if not okv or r["L"] > 10**7 or len(r["clr"]) != 7 or len(r["ctx"]) != 4 or max(r["clr"][3:6]) > 10**7 or r["ctx"][2] > 10**7 or r["fast"][2] > 10**7 or r["gold"][2] > 10**7:
            bad[0] += 1
            continue
        r["game"] = (str(b), team)
        loops.append(r)
    print(f"{len(loops)} farm loops ({bad[0]} unparsed)")
    groups = collections.defaultdict(list)
    for r in loops:
        key = ("cut" if r["c"] else "uncut") + "/" + ("bank" if r["b"] else "nb") + ("/open" if r["o"] else "")
        groups[key].append(r)
        groups["all"].append(r)
    for key in sorted(groups, key=lambda k: -len(groups[k])):
        rs = groups[key]
        n = len(rs)
        if n < 50:
            continue
        rs2 = [r for r in rs if not r["f"]]
        print(f"\n== {key}: {n} loops; mean loop fuel {sum(r['L'] for r in rs) / n:.0f}; groups weighed (k) mean {sum(r['k'] for r in rs) / n:.1f} of {sum(r['n'] for r in rs) / n:.1f}")
        m = max(1, len(rs2))
        print("  key moved vs last call: context " + ", ".join(f"{name} {sum(r['cm'] >> i & 1 for r in rs2) / m:.2f}" for i, name in enumerate(CTX_BITS[:4]))
              + f"; any {sum(r['cm'] > 0 for r in rs2) / m:.2f}")
        print(f"                         gold per_gold {sum(r['gm'] & 1 for r in rs2) / m:.2f}, tribute_gold {sum(r['gm'] >> 1 & 1 for r in rs2) / m:.2f}; any {sum(r['gm'] > 0 for r in rs2) / m:.2f}")
        print("                         clearing " + ", ".join(f"{name} {sum(r['km'] >> i & 1 for r in rs2) / m:.2f}" for i, name in enumerate(KEY_CLR))
              + f"; any {sum(r['km'] > 0 for r in rs2) / m:.2f}")
        for name, idx in (("ctx", None), ("gold", None), ("fast", None), ("kf", None), ("clr", None)):
            v = [r[name] for r in rs]
            cnt = sum(x[0] for x in v) / n
            if name == "ctx":
                print(f"  ctx  recomputes {cnt:.2f}/loop, same values {sum(x[1] for x in v) / n:.2f}, finer inputs held {sum(x[3] for x in v) / n:.2f}; fuel {sum(x[2] for x in v) / n:.0f}/loop")
            elif name == "gold":
                print(f"  gold recomputes {cnt:.2f}/loop, same {sum(x[1] for x in v) / n:.2f}; fuel {sum(x[2] for x in v) / n:.0f}/loop")
            elif name == "fast":
                print(f"  fast recomputes {cnt:.2f}/loop, same {sum(x[1] for x in v) / n:.2f}; fuel {sum(x[2] for x in v) / n:.0f}/loop")
            elif name == "kf":
                print(f"  kf   recomputes {cnt:.2f}/loop; fuel {sum(x[1] for x in v) / n:.0f}/loop")
            else:
                print(f"  clr  recomputes {cnt:.2f}/loop, same damage {sum(x[1] for x in v) / n:.2f}, same kite {sum(x[2] for x in v) / n:.2f}; fuel {sum(x[3] for x in v) / n:.0f}/loop"
                      f" (min_camp_damage {sum(x[4] for x in v) / n:.0f}, spell_clear {sum(x[5] for x in v) / n:.0f} in {sum(x[6] for x in v) / n:.2f} calls)")
        srs = [r["sr"] for r in rs if "sr" in r and len(r["sr"]) == 4 and r["sr"][0] < 10**7 and r["sr"][2] < 10**7]
        if srs:
            print(f"  static first reads in min_camp_damage: StandReach {sum(x[0] for x in srs) / len(srs):.0f}/loop in {sum(x[1] for x in srs) / len(srs):.2f} builds;"
                  f" clear_fire {sum(x[2] for x in srs) / len(srs):.0f}/loop in {sum(x[3] for x in srs) / len(srs):.2f} calls")
        # reasons
        cr = collections.Counter()
        cf = collections.Counter()
        kr = collections.Counter()
        kf = collections.Counter()
        gr = collections.Counter()
        for r in rs:
            for m_, q, c, _ in r["sec"].get("CR", []):
                cr[m_, q] += c
            for m_, f in r["sec"].get("CF", []):
                cf[m_] += f
            for m_, q, c in r["sec"].get("GR", []):
                gr[m_, q] += c
            for m_, q, c in r["sec"].get("KR", []):
                kr[m_, q] += c
            for m_, f in r["sec"].get("KF", []):
                kf[m_] += f

        def name(mask, bits, first):
            return "first" if mask == first else "+".join(b for i, b in enumerate(bits) if mask >> i & 1) or "none"
        print("  ctx recompute reasons (inputs moved since the group's last compute): same/diff counts per loop, fuel per loop")
        for mk in sorted({m_ for m_, _ in cr}, key=lambda x: -(cr[x, 0] + cr[x, 1]))[:10]:
            print(f"    {name(mk, CTX_BITS, 32):<28} same {cr[mk, 1] / n:.2f} diff {cr[mk, 0] / n:.2f} fuel {cf[mk] / n:.0f}")
        print("  gold reasons")
        for mk in sorted({m_ for m_, _ in gr}, key=lambda x: -(gr[x, 0] + gr[x, 1]))[:6]:
            print(f"    {name(mk, ['per_gold', 'tribute_gold'], 4):<28} same {gr[mk, 1] / n:.2f} diff {gr[mk, 0] / n:.2f}")
        print("  clearing recompute reasons")
        for mk in sorted({m_ for m_, _ in kr}, key=lambda x: -kf[x])[:12]:
            print(f"    {name(mk, CLR_BITS, 128):<40} same {kr[mk, 1] / n:.2f} diff {kr[mk, 0] / n:.2f} fuel {kf[mk] / n:.0f}")
    # strength movement detail
    moved = [r for r in loops if not r["f"] and r["km"] & 1]
    print(f"\nstrength moves: {len(moved)}; relative change p50 "
          + (f"{sorted(abs(r['str'][1] / r['str'][0] - 1) for r in moved if r['str'][0])[len(moved) // 2]:.4f}" if moved else "-"))
    sb = [r for r in loops if not r["f"] and r["cm"] & 2]
    print(f"short_by moves: {len(sb)}; delta p50 " + (f"{sorted(abs(r['sb'][1] - r['sb'][0]) for r in sb)[len(sb) // 2]:.0f}" if sb else "-"))


main()
