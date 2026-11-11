import sys, zipfile, collections
from pathlib import Path
for d in sys.argv[1:]:
    c = collections.Counter(); sc = collections.Counter(); games = 0
    for g in Path(d).iterdir():
        if not g.is_dir(): continue
        z = list(g.glob("*.repl26a"))
        if not z: continue
        games += 1
        s = zipfile.ZipFile(z[0]).read(f"team-{g.name[-1]}.stdout").decode("utf-8", "replace").replace("\x00", "")
        for line in s.splitlines():
            if line.startswith("OOF "):
                p = line.split(maxsplit=2)
                if int(p[1]) > 5: c[p[2] if len(p) > 2 else "?"] += 1
            elif line.startswith("SHORTCUT "):
                p = line.split()
                if len(p) >= 4: sc[p[3]] += 1
    print(d, games, sum(c.values()) / games)
    for k, v in c.most_common(12): print(f"   {k:30s} {v/games:.3f}")
    print("  shortcuts/game:", {k: round(v / games, 1) for k, v in sc.most_common(14)})
