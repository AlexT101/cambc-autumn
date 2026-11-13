"""pwar counters from a debug batch: PWX zone/press turns a game (from stdout), and, given an extracted dir, Prism
deaths and kills of CAND vs REF a game. Usage: pwarcount.py BATCH_DIR [EXTRACTED_DIR CAND_NAME]"""
import sys, zipfile, glob, json, gzip, collections
from pathlib import Path

batch = Path(sys.argv[1])
games = zone = press = zone_br = 0
brs = collections.Counter()
pbrs = collections.Counter()
for f in sorted(batch.glob('*.repl26a')):
    z = zipfile.ZipFile(f)
    games += 1
    for t in ('team-a.stdout', 'team-b.stdout'):
        for l in z.read(t).decode(errors='replace').splitlines():
            if l.startswith('PWX '):
                p = l.split()
                zone += p[4] == '1'
                press += p[5] == '1'
                if p[4] == '1': brs[p[3]] += 1
                if p[5] == '1': pbrs[p[3]] += 1
print(f'games {games}: zone turns {zone / games:.2f} a game {dict(brs.most_common(8))}; press turns {press / games:.2f} a game {dict(pbrs.most_common(5))}')
if len(sys.argv) > 3:
    cand = sys.argv[3]
    d = collections.Counter()
    n = 0
    first = collections.Counter()
    for m in Path(sys.argv[2]).iterdir():
        if not (m / 'meta.json').exists(): continue
        meta = json.loads((m / 'meta.json').read_text())
        tn = [t['name'] for t in meta['teams']]
        if cand not in tn: continue
        us = tn.index(cand)
        pr = {int(c['id']): int(c['team']) for c in meta['champions'] if c['name'] == 'Prism'}
        if len(pr) != 2: continue
        n += 1
        fd = None
        for l in gzip.open(m / 'events.jsonl.gz', 'rt'):
            e = json.loads(l)
            if e['k'] == 'death' and e['v'] in pr:
                side = 'cand' if pr[e['v']] == us else 'ref'
                d[side + '_prism_deaths'] += 1
                if e.get('by') in pr: d[side + '_prism_deaths_by_prism'] += 1
                if fd is None: fd = side; first[side] += 1
    print(f'two-Prism games {n}: ' + ', '.join(f'{k} {v / n:.3f}' for k, v in sorted(d.items())) + f'; first Prism death cand {first["cand"]} ref {first["ref"]}')
