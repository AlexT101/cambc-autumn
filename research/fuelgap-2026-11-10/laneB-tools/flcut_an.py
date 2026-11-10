#!/usr/bin/env python3
"""Read fgb-flcut debug games (FLCUT, FLCREW lines from the candidate's stdout) and summarise
cut versus full farm-loop choices and crew-plan reuse. Usage: flcut_an.py BATCH_DIR [--cand-index 0]"""
import json, sys, zipfile, statistics as st
from collections import Counter, defaultdict

def lines(batch, cand=0):
    r = json.load(open(f"{batch}/results.json"))
    for m in r["completed"] if "completed" in r and isinstance(r["completed"], list) else r["matches"]:
        if not m.get("replay"): continue
        side = "a" if m["order"][0] == cand else "b"
        try:
            z = zipfile.ZipFile(m["replay"])
            txt = z.read(f"team-{side}.stdout").decode("utf-8", "replace").replace("\x00", "\n")
        except Exception as e:
            continue
        yield m, txt

def main():
    batch = sys.argv[1]
    cuts = []
    crew_last = {}  # (game, handle) -> last FLCREW fields
    part_last = {}
    games = 0
    for m, txt in lines(batch):
        games += 1
        for ln in txt.splitlines():
            if ln.startswith("FLCUT ") and ln.count("|") in (7, 8) and len(ln.split("|")[7].split()) == 9 and (ln.count("|") == 7 or len(ln.split("|")[8].split()) == 8):
                parts = ln.split("|")
                h = parts[0].split()[1:]
                c = parts[1].split(); f = parts[2].split(); p = parts[3].split(); d = parts[4].split(); lf = parts[5].split()
                lost = [tuple(map(int, x.split(":"))) for x in parts[6].split()]
                won = [tuple(map(int, x.split(":"))) for x in parts[7].split()]
                cuts.append(dict(round=int(h[0]), me=h[1], tm=h[2], bank=int(h[3]), n=int(h[4]), k=int(h[5]), kend=int(h[6]), kind=int(h[7]),
                                 fcut=int(h[8]), ffull=int(h[9]), farm=int(h[10]), first=int(h[11]),
                                 cb=int(c[0]), cbv=float(c[1]), csh=int(c[2]), csv=float(c[3]), crk=int(c[4]), chp=int(c[6]),
                                 fb=int(f[0]), fbv=float(f[1]), fsh=int(f[2]), fsv=float(f[3]), frk=int(f[4]), fhp=int(f[6]), fmode=f[8],
                                 pc=int(p[0]), pvc=float(p[1]), pf=int(p[2]), pvf=float(p[3]), posf=int(p[4]), clf=int(p[5]), posfarm=int(p[6]),
                                 D=int(d[0]), dv=float(d[1]), dage=int(d[2]), dcur=float(d[3]), lvf=float(lf[0]), agef=int(lf[1]),
                                 lost=lost, won=won, game=m["replay"],
                                 parts=[tuple(map(int, x.split(":"))) for x in parts[8].split()] if len(parts) > 8 else None))
            elif ln.startswith("FLPART ") and len(ln.split()) == 3 + 8 + 6:
                h = ln.split()
                part_last[(m["replay"], h[2])] = ([tuple(map(float, x.split(":"))) for x in h[3:11]], [tuple(map(int, x.split("/"))) for x in h[11:]])
            elif ln.startswith("FLCREW ") and ln.count("|") == 2 and len(ln.split("|")[2].split()) == 12:
                parts = ln.split("|")
                h = parts[0].split()
                crew_last[(m["replay"], h[2])] = (int(h[3]), int(h[4]), [list(map(float, x.split())) for x in parts[1:]])
    n = len(cuts)
    print(f"games {games}, cut loops {n}")
    loops = sum(v[0] for v in crew_last.values()); ncut = sum(v[1] for v in crew_last.values())
    print(f"loops (to the last FLCREW line) {loops}, cut {ncut} = {100*ncut/max(loops,1):.2f}%")
    tm = Counter(c["tm"] for c in cuts); print("by template", dict(tm), "banks_bag", sum(c["bank"] for c in cuts))
    same = sum(c["pc"] == c["pf"] for c in cuts)
    print(f"same pick {same} = {100*same/n:.1f}%")
    nopick = [c for c in cuts if c["pc"] == -1]
    print(f"cut pick none: {len(nopick)} = {100*len(nopick)/n:.1f}%; k==0: {sum(c['k']==0 for c in nopick)}; k>0: {sum(c['k']>0 for c in nopick)}")
    for lab, sub in (("k==0", [c for c in nopick if c["k"] == 0]), ("k>0", [c for c in nopick if c["k"] > 0])):
        if not sub: continue
        fnone = sum(c["pf"] == -1 for c in sub)
        eqfarm = sum(c["pf"] == c["farm"] and c["farm"] >= 0 for c in sub)
        hasfarm = sum(c["farm"] >= 0 for c in sub)
        posd = Counter(min(c["posf"] - c["k"], 9) if c["posf"] >= 0 else -9 for c in sub if c["pf"] >= 0)
        dok = sum(c["D"] >= 0 and c["D"] == c["pf"] for c in sub); dany = sum(c["D"] >= 0 for c in sub)
        print(f"  {lab} ({len(sub)}): full none {fnone}, full == last choice {eqfarm} (last choice set {hasfarm}); full pos - k {sorted(posd.items())}; D exists {dany}, D == full {dok}")
        modes = Counter(c["fmode"] if c["pf"] == c["fb"] else ("J" if c["pf"] == c["fsh"] else "H" if c["pf"] == c["fhp"] else "?") for c in sub if c["pf"] >= 0)
        print(f"     full pick kind {dict(modes)}; mean k {st.mean(c['k'] for c in sub):.1f} of n {st.mean(c['n'] for c in sub):.1f}")
    diff = [c for c in cuts if c["pc"] != c["pf"] and c["pc"] != -1]
    print(f"pick set and different: {len(diff)} = {100*len(diff)/n:.1f}%")
    if diff:
        posd = Counter(min(c["posf"] - c["k"], 12) if c["posf"] >= 0 else -99 for c in diff)
        print("  full pos - k:", sorted(posd.items()))
        print("  full claimed:", sum(c["clf"] for c in diff), " full is bank(-2):", sum(c["pf"] == -2 for c in diff), " cut is bank:", sum(c["pc"] == -2 for c in diff))
        rel = [c["pvc"] / c["pvf"] for c in diff if c["pvf"] > 0 and c["pvc"] >= 0]
        if rel: print(f"  cut pick value / full pick value: median {st.median(rel):.3f}, p25 {sorted(rel)[len(rel)//4]:.3f}, share < 0.8: {sum(r<0.8 for r in rel)/len(rel):.2f}")
        dany = sum(c["D"] >= 0 for c in diff); dok = sum(c["D"] >= 0 and c["D"] == c["pf"] for c in diff)
        print(f"  D (unweighed, last value > cut pick's) exists {dany}, D == full {dok}")
    # D in all cut loops: would adopting D help?
    dall = [c for c in cuts if c["D"] >= 0 and c["dv"] > max(c["pvc"], 0)]
    if dall:
        good = sum(c["D"] == c["pf"] for c in dall); bad = sum(c["D"] != c["pf"] and c["pc"] == c["pf"] for c in dall)
        print(f"D beats cut pick by last value: {len(dall)} = {100*len(dall)/n:.1f}% of cuts; D == full {good}; cut pick was right (D wrong) {bad}; neither {len(dall)-good-bad}")
        cur = [c["dcur"] / c["dv"] for c in dall if c["dcur"] > 0]
        print(f"   D's value now / last: median {st.median(cur) if cur else -1:.3f} over {len(cur)} priced now; unpriced now (pruned or skipped) {sum(c['dcur']<=0 for c in dall)}")
    # fuel
    print(f"loop fuel to cut median {st.median(c['fcut'] for c in cuts):.0f}, full median {st.median(c['ffull'] for c in cuts):.0f}; k median {st.median(c['k'] for c in cuts)} of n {st.median(c['n'] for c in cuts)}; kend median {st.median(c['kend'] for c in cuts)}")
    print("cut kind (0 header, 1 field, 2 hop):", dict(Counter(c["kind"] for c in cuts)))
    names = ["prefacts", "facts", "steps", "trip", "claimed", "claimed-plan", "clearing", "crew-plan", "final"]
    tl = [sum(c["lost"][i][1] for c in cuts) for i in range(9)]; tw = [sum(c["won"][i][1] for c in cuts) for i in range(9)]
    nl = [sum(c["lost"][i][0] for c in cuts) for i in range(9)]; nw = [sum(c["won"][i][0] for c in cuts) for i in range(9)]
    tot = sum(tl) + sum(tw)
    print("prefix fuel by furthest stage (lost / won): share, count, mean")
    for i in range(9):
        print(f"  {names[i]:13s} lost {100*tl[i]/tot:5.1f}% n {nl[i]:7d} mean {tl[i]/max(nl[i],1):6.0f} | won {100*tw[i]/tot:5.1f}% n {nw[i]:6d} mean {tw[i]/max(nw[i],1):6.0f}")
    # crew reuse
    tot = [[0.0] * 12 for _ in range(2)]
    for v in crew_last.values():
        for s in range(2):
            for j in range(12): tot[s][j] += v[2][s][j]
    for s, lab in enumerate(("claimed", "crewable")):
        t = tot[s]
        if t[0] == 0: continue
        print(f"crew {lab}: calls {t[0]:.0f}, fuel/call {t[10]/t[0]:.0f}; with a plan 1-3 rounds old {t[2]:.0f} (1 round {t[1]:.0f}); key same {t[3]:.0f}; plan same {t[4]:.0f}; "
              f"value within 2% {t[7]:.0f}; decision flips {t[5]:.0f} ({100*t[5]/max(t[2],1):.1f}%), of them key same {t[6]:.0f}; wins act {t[8]:.0f} stale {t[9]:.0f}")
    if part_last:
        pn = ["plan claimed", "plan crewable", "crew_work", "mcd clearing", "mcd kited", "home_trip", "live_steps", "plan reusable"]
        allp = [[0.0, 0.0] for _ in range(8)]
        cond = [[0, 0] for _ in range(6)]
        for fx, cd in part_last.values():
            for i in range(8): allp[i][0] += fx[i][0]; allp[i][1] += fx[i][1]
            for i in range(6): cond[i][0] += cd[i][0]; cond[i][1] += cd[i][1]
        print("every loop, by part: calls, fuel a loop, fuel a call")
        for i in range(8): print(f"  {pn[i]:14s} {allp[i][0]:9.0f} {allp[i][1]/max(loops,1):7.0f} {allp[i][1]/max(allp[i][0],1):7.0f}")
        lab = ["age 1", "age 1, claimers same", "and version same"]
        for si, site in enumerate(("claimed", "crewable")):
            print(f"  flips {site}: " + "; ".join(f"{lab[j]} {cond[3*si+j][0]}/{cond[3*si+j][1]} = {100*cond[3*si+j][0]/max(cond[3*si+j][1],1):.2f}%" for j in range(3)))
        pc = [c for c in cuts if c["parts"]]
        print(f"cut loops' prefix, by part (median prefix {st.median(c['fcut'] for c in pc):.0f}): mean calls, mean fuel, share of prefix")
        tot = sum(c["fcut"] for c in pc)
        for i in range(8):
            print(f"  {pn[i]:14s} {sum(c['parts'][i][0] for c in pc)/len(pc):6.2f} {sum(c['parts'][i][1] for c in pc)/len(pc):7.0f} {100*sum(c['parts'][i][1] for c in pc)/tot:5.1f}%")
        mc = [c for c in pc if c["kend"] > c["k"]]
        sav = [c["parts"][7][1] for c in mc]
        print(f"  meaningful cuts: reusable plan fuel in prefix: mean {st.mean(sav):.0f}, share > 0: {sum(x>0 for x in sav)/len(sav):.2f}, p75 {sorted(sav)[3*len(sav)//4]}")
    json.dump(cuts, open(f"{batch}/flcut.json", "w"))

main()
