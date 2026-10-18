"""Download our groups against top teams since nemesis went live into replays/mine (same layout as fetch_replays.py)."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from fetch_replays import team_groups, download_group, MY_TEAM, ROOT

WANT = ['6c90138d', '1cd3404a', 'c70f7389', '6b3e1f54', '661dfeba', 'c530112b']
groups = {g['id'][:8]: g for g in team_groups(MY_TEAM, 'all', '2026-10-17T13:00', 0) if g['id'][:8] in WANT}
for w in WANT:
    d, n = download_group(ROOT / 'replays' / 'mine', groups[w])
    print(d.name, n, flush=True)
