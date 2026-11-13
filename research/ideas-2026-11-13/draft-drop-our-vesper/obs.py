import json, sys, math
sys.path.insert(0, '/home/ubuntu/cambc-autumn/research/ideas-2026-11-08/spar-tools')
import local
units = {r['map']: r for r in json.load(open('units-draft-drop-our-vesper--fuel200000.json'))}
lad = {l.strip() for l in open('/home/ubuntu/cambc-autumn/tools/ladder128.txt') if l.strip()}
for o, b in (('F', 'fr8-g25'), ('M', 'mf-f9')):
    for name, who in (('REF chy-525', 'chy-525'), ('CAND ban', 'draft-drop-our-vesper')):
        w = {True: [], False: []}
        for j in (0, 1):
            for (m, s), v in local.cells(f'fbe501-{who}-{b}-m2560b{j:03d}-fuel200000-Pv4').items():
                if m in lad or m not in units: continue
                w[bool(units[m]['refV'])].append(v)
        p = {k: sum(v) / len(v) for k, v in w.items()}
        print(f"{b:8s} {name:12s}: win on maps chy-525 drafts Vesper {100*p[True]:.1f}% (n {len(w[True])}), on the others {100*p[False]:.1f}% (n {len(w[False])}); gap {100*(p[True]-p[False]):+.1f}")
