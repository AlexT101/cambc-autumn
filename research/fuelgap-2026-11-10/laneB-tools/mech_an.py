#!/usr/bin/env python3
"""Count the candidate's (bot 1's) farm-loop cut traces in a debug batch: FLK lines (k, evaluated),
SHORTCUT lines by kind, per game. Usage: mech_an.py BATCH [BATCH...]"""
import json, sys, zipfile, statistics as st
from collections import Counter
for batch in sys.argv[1:]:
    r = json.load(open(f"{batch}/results.json"))
    ks, games, sc, rounds, wins = [], 0, Counter(), 0, 0
    for m in r["matches"]:
        if not m.get("replay"): continue
        side = "a" if m["order"][0] == 0 else "b"
        t = zipfile.ZipFile(m["replay"]).read(f"team-{side}.stdout").decode("utf-8", "replace").replace("\x00", "\n")
        games += 1; rounds += m.get("rounds", 0); wins += m.get("winner") == 1
        for ln in t.splitlines():
            if ln.startswith("FLK "):
                f = ln.split()
                if len(f) == 6: ks.append((int(f[3]), int(f[4])))
            elif ln.startswith("SHORTCUT "):
                f = ln.split()
                if len(f) >= 4: sc[f[3]] += 1
    print(batch.split("/")[-1], f"games {games}, rounds {rounds}")
    print(f"  cut loops {len(ks)} ({len(ks)/games:.1f} a game); k mean {st.mean(k for k,_ in ks):.2f}, median {st.median(k for k,_ in ks)}, k==0 {sum(k==0 for k,_ in ks)/len(ks):.3f}; k/n mean {st.mean(k/max(n,1) for k,n in ks):.3f}")
    for name in ("farm-partial-evaluation", "farm-plan-reused", "farm-kept-target"):
        print(f"  {name}: {sc[name]} ({sc[name]/games:.1f} a game)")
    print("  top shortcuts:", sc.most_common(8))
