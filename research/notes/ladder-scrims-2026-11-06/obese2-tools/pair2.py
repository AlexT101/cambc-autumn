"""pair2.py BASE_BATCH ARM_BATCH [MAPS.txt]: per game (map, sides), the arm's CAND result against the base mirror's
on the same map and side, split by whether the arm's CAND saw a non-Prism obese bag (OBESEC) and whether the gate
fired (KOBESE). Optional MAPS.txt restricts to those map names."""
import json, sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from obstat import one

def load(b):
    r = json.loads((Path(b) / 'results.json').read_text())
    return {(Path(m['map']).name, tuple(m['order'])): m for m in r['matches'] if 'winner' in m}

if __name__ == '__main__':
    base, arm = load(sys.argv[1]), load(sys.argv[2])
    keep = set(open(sys.argv[3]).read().split()) if len(sys.argv) > 3 else None
    keys = [k for k in arm if k in base and (keep is None or k[0] in keep)]
    with ProcessPoolExecutor(16) as ex:
        rows = list(ex.map(one, [(sys.argv[2], arm[k]) for k in keys], chunksize=32))
    groups = {}
    for k, r in zip(keys, rows):
        vw, bw = arm[k]['winner'] == 0, base[k]['winner'] == 0
        g = 'fired' if r.get('kill') or r.get('bank') else ('obese seen' if r.get('census_np') else 'rest')
        s = groups.setdefault(g, [0, 0, 0, 0, 0])
        s[0] += 1; s[1] += vw; s[2] += bw; s[3] += vw and not bw; s[4] += bw and not vw
    tot = [sum(s[i] for s in groups.values()) for i in range(5)]
    for g, (n, vw, bw, up, dn) in list(groups.items()) + [('all', tot)]:
        if n: print(f"{g:11s}: {n:6d} games, arm CAND {100*vw/n:5.1f}%, mirror CAND {100*bw/n:5.1f}%, diff {100*(vw-bw)/n:+.2f} pts"
                    f" (flips +{up} / -{dn})")
