"""pp.py BATCHDIR... : per batch, cand's OOF turns by phase, SHORTCUT labels, prof keys (PCUM / PROF lines)."""
import sys, zipfile, collections, glob, os
NAMES = {13: "press_sim", 0: "lethal", 1: "stunner_near", 2: "stun_follow", 3: "lethal_stun_wd", 5: "coming_casts", 6: "retreat_step", 7: "press", 8: "press_taken", 9: "press_avoid", 10: "step_guard", 11: "decide"}
def cand_stdout(f):
    side = 'a' if f.endswith('-12.repl26a') else 'b'
    return zipfile.ZipFile(f).read(f"team-{side}.stdout").decode("utf-8", "replace").replace("\x00", "")
for d in sys.argv[1:]:
    files = sorted(glob.glob(d + '/*.repl26a'))
    oofp = collections.Counter(); sc = collections.Counter(); cum = collections.Counter(); cumc = collections.Counter()
    heavy = []; oofl = []; n = 0; oof = 0
    for f in files:
        try: s = cand_stdout(f)
        except Exception: continue
        n += 1; last = {}
        for line in s.splitlines():
            if line.startswith("OOF "):
                p = line.split(maxsplit=2)
                if int(p[1]) > 5: oof += 1; oofp[p[2] if len(p) > 2 else "?"] += 1
            elif line.startswith("SHORTCUT "):
                p = line.split()
                if len(p) >= 4: sc[p[3]] += 1
            elif line.startswith("PCUM "):
                p = line.split(); last[p[2]] = p[3:]
            elif line.startswith("PROF "):
                p = line.split()
                try: vals = [tuple(map(int, x.split(":"))) for x in p[5:]]
                except ValueError: continue
                (oofl if p[3] == "1" else heavy).append(vals)
        for h, v in last.items():
            for k, x in enumerate(v):
                try: fu, c = map(int, x.split(":"))
                except ValueError: continue
                cum[k] += fu; cumc[k] += c
    print(f"== {os.path.basename(d)}: {n} games, OOF {oof/n:.2f}/game; heavy {len(heavy)/n:.2f}/game")
    for k, v in oofp.most_common(10): print(f"   oof {k:28s} {v/n:.3f}")
    print("   shortcuts/game:", {k: round(v / n, 2) for k, v in sc.most_common(16)})
    for k, nm in NAMES.items():
        if cumc[k] == 0: continue
        hm = sum(v[k][0] for v in heavy if len(v) > k) / max(1, len(heavy)); om = sum(v[k][0] for v in oofl if len(v) > k) / max(1, len(oofl))
        print(f"   {nm:15s} fuel/game {cum[k]/n:9.0f} calls/game {cumc[k]/n:8.1f} per {cum[k]/max(1,cumc[k]):7.0f} | heavy mean {hm:7.0f} | oof mean {om:7.0f}")
