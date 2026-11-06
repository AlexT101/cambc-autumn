"""paired.py BASE_BATCH VAR_BATCH PREFIX: per game (map, sides) the variant's CAND result against base-vs-base's,
split by whether the variant's CAND printed PREFIX lines (the rule fired)."""
import json, sys, zipfile
from pathlib import Path
def load(b):
    r = json.loads((Path(b) / 'results.json').read_text())
    return {(Path(m['map']).name, tuple(m['order'])): m for m in r['matches'] if 'winner' in m}
base, var, pre = load(sys.argv[1]), load(sys.argv[2]), sys.argv[3]
stats = {True: [0, 0, 0, 0], False: [0, 0, 0, 0]}  # games, var wins, base wins, flips(+)
for k, m in var.items():
    if k not in base: continue
    team = 'a' if m['order'][0] == 0 else 'b'
    fired = False
    if pre != '-':
        try:
            out = zipfile.ZipFile(m['replay']).read(f'team-{team}.stdout').replace(b'\0', b'').decode('utf-8', 'replace')
            fired = any(l.startswith(pre) for l in out.splitlines())
        except Exception:
            pass
    s = stats[fired]
    vw, bw = m['winner'] == 0, base[k]['winner'] == 0
    s[0] += 1; s[1] += vw; s[2] += bw
for f, (n, vw, bw, _) in stats.items():
    if n: print(f"fired={f}: {n} games, variant CAND {100*vw/n:.1f}%, base CAND {100*bw/n:.1f}%, diff {100*(vw-bw)/n:+.2f} pts ({vw-bw:+d} games)")
