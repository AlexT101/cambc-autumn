"""firedwin.py BATCH PREFIX: CAND's win rate in games where CAND printed PREFIX lines, and in the rest."""
import json, sys, zipfile
from pathlib import Path
b = Path(sys.argv[1]); pre = sys.argv[2]
r = json.loads((b / 'results.json').read_text())
fired = [0, 0]; rest = [0, 0]
for m in r['matches']:
    if 'replay' not in m or 'winner' not in m: continue
    f = b / Path(m['replay']).name
    cand_team = 'a' if m['order'][0] == 0 else 'b'
    try:
        z = zipfile.ZipFile(f)
        out = z.read(f'team-{cand_team}.stdout').replace(b'\0', b'').decode('utf-8', 'replace')
    except Exception:
        continue
    n = sum(1 for l in out.splitlines() if l.startswith(pre))
    t = fired if n else rest
    t[0] += m['winner'] == 0; t[1] += 1
print(f"{pre}: fired games {fired[1]}, cand won {fired[0]} ({100*fired[0]/max(1,fired[1]):.1f}%); other games {rest[1]}, cand won {100*rest[0]/max(1,rest[1]):.1f}%")
