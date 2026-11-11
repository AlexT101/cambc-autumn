import sys, zipfile, re, glob, collections
from pathlib import Path
NAMES = {12: "press_pre", 13: "press_sim", 14: "press_kill_tiles", 15: "press_packdmg", 0: "lethal", 1: "stunner_near", 2: "stun_follow", 3: "lethal_stun_wd", 5: "coming_casts", 6: "retreat_step", 7: "press", 8: "press_taken", 9: "press_avoid", 10: "step_guard", 11: "decide"}
def load(d):
    games = 0; cum = collections.Counter(); cumc = collections.Counter(); oof = 0; heavy = []; oofl = []; turns = 0
    for g in sorted(Path(d).iterdir()):
        if not g.is_dir(): continue
        side = g.name[-1]
        z = list(g.glob("*.repl26a"))
        if not z: continue
        s = zipfile.ZipFile(z[0]).read(f"team-{side}.stdout").decode("utf-8", "replace").replace("\x00", "")
        games += 1
        last = {}
        for line in s.splitlines():
            if line.startswith("PCUM "):
                p = line.split()
                if len(p) in (15, 19): last[p[2]] = p[3:]
            elif line.startswith("PROF "):
                p = line.split()
                if len(p) not in (17, 21): continue
                try: vals = [tuple(map(int, x.split(":"))) for x in p[5:]]
                except ValueError: continue
                (oofl if p[3] == "1" else heavy).append(vals)
            elif line.startswith("OOF "):
                r = int(line.split()[1])
                if r > 5: oof += 1
        for h, v in last.items():
            for k, x in enumerate(v):
                try: f, c = map(int, x.split(":"))
                except ValueError: continue
                cum[k] += f; cumc[k] += c
    return games, cum, cumc, oof, heavy, oofl
res = {}
for d in sys.argv[1:]:
    res[d] = load(d)
    games, cum, cumc, oof, heavy, oofl = res[d]
    print(f"== {d}: {games} games, OOF turns {oof} ({oof/games:.2f}/game), heavy(>=50k decide) {len(heavy)}, oof PROF lines {len(oofl)}")
    print(f"{'key':16s} {'fuel/game':>10s} {'calls/game':>10s} {'per call':>8s} | {'heavy mean':>10s} {'heavy share':>10s} | {'oof mean':>9s} {'oof frac>0':>9s}")
    for k, n in NAMES.items():
        hm = sum(v[k][0] for v in heavy if len(v) > k) / max(1, len(heavy)); om = sum(v[k][0] for v in oofl if len(v) > k) / max(1, len(oofl))
        hs = sum(v[k][0] for v in heavy if len(v) > k) / max(1, sum(v[11][0] for v in heavy))
        of = sum(len(v) > k and v[k][0] > 0 for v in oofl) / max(1, len(oofl))
        print(f"{n:16s} {cum[k]/games:10.0f} {cumc[k]/games:10.1f} {cum[k]/max(1,cumc[k]):8.0f} | {hm:10.0f} {hs:10.3f} | {om:9.0f} {of:9.2f}")
