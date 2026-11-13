"""defer's arrivals home (debug builds' `VISIT round handle N|D|S interval` lines: natural, death, shopping trip): the pooled mean interval between
arrivals no shopping trip brought, as the bot's estimator counts it (closed intervals over natural arrivals), by
phase of the arrival.
    py research/mac13-argo/scripts/visits.py BATCH_DIR [BOT_NAME]"""
import json
import sys
import zipfile
from collections import defaultdict
from pathlib import Path

d = Path(sys.argv[1])
want = sys.argv[2] if len(sys.argv) > 2 else 'defer'
bots = json.loads((d / 'results.json').read_text())['bots']
acc = defaultdict(lambda: [0.0, 0, 0])  # phase -> rounds, natural, shop
games = 0
for b in sorted(d.glob('*.repl26a')):
    order = b.stem.rsplit('-', 1)[1]
    with zipfile.ZipFile(b) as z:
        for team in 'ab':
            if Path(bots[0 if (team == 'a') == (order == '12') else 1]).name != want:
                continue
            games += 1
            out = z.read(f'team-{team}.stdout').replace(b'\0', b'').decode('utf-8', 'replace')
            for line in out.splitlines():
                if not line.startswith('VISIT '):
                    continue
                _, r, h, kind, gap = line.split()[:5]
                r = int(r)
                for ph in ('all', 'r1-400' if r <= 400 else 'r401-800' if r <= 800 else 'r801+'):
                    a = acc[ph]
                    a[0] += float(gap)
                    a[1] += kind in 'ND'
                    a[2] += kind == 'S'
print(f'{games} team-games of {want}')
for ph, (rounds, nat, shop) in sorted(acc.items()):
    print(f'{ph:9s} rounds/natural arrival {rounds / max(1, nat):.1f}  natural {nat}  shop {shop}  (per team-game {nat / games:.2f} / {shop / games:.2f})')
