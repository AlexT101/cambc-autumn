#!/usr/bin/env python3
"""Lines of both teams' stdout starting with PREFIX, over a batch dir: python3 grep_out.py DIR PREFIX [MAX]"""
import sys, zipfile
from pathlib import Path

d, prefix = sys.argv[1], sys.argv[2]
most = int(sys.argv[3]) if len(sys.argv) > 3 else 20
n = 0
last = {}
for p in sorted(Path(d).glob("*.repl26a")):
    with zipfile.ZipFile(p) as z:
        for t in "ab":
            s = z.read(f"team-{t}.stdout").replace(b"\0", b"").decode("utf-8", "replace")
            for line in s.splitlines():
                if line.startswith(prefix):
                    n += 1
                    last[(p.name, t)] = line
                    if n <= most:
                        print(p.name, t, line)
print("lines", n)
for k, v in list(last.items())[:10]:
    print("last", k, v)
