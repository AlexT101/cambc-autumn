import sys, zipfile, re, collections
from pathlib import Path
ph = collections.Counter(); n = 0; games = 0; rounds = collections.Counter()
for d in sorted(Path(sys.argv[1]).iterdir()):
    m = re.match(r"(.+)-([ab])$", d.name)
    if not m: continue
    b = next(d.glob("*.repl26a"), None)
    if not b: continue
    games += 1
    with zipfile.ZipFile(b) as z:
        for l in z.read(f"team-{m[2]}.stdout").decode("utf-8", "replace").splitlines():
            if l.startswith("OOF "):
                p = l.split(None, 2); ph[p[2] if len(p) > 2 else "?"] += 1; n += 1
                r = int(p[1].strip("\x00")); rounds["1" if r == 1 else "2-10" if r <= 10 else "11-60" if r <= 60 else "61-300" if r <= 300 else "300+"] += 1
print(games, "games", n, "OOF lines")
for k, v in ph.most_common(): print(f"{k:20s} {v:6d} {v/n*100:5.1f}%")
print(dict(rounds))
