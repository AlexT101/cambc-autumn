import sys, os, glob, json, numpy as np
sys.path.insert(0, '/home/ubuntu/cambc-autumn/research/notes/ideas-2026-11-09/oppmodel')
from build_ds import one
from model import load_tables
m = load_tables('/home/ubuntu/cambc-autumn/research/notes/ideas-2026-11-09/oppmodel/opp_tables.h')
R = [10, 25, 50, 100, 200, 400]
for an in sys.argv[1:]:
    P = []
    for d in sorted(glob.glob(f'{an}/*/meta.json')):
        meta = json.load(open(d)); base = os.path.basename(meta['source']).split('.')[0]
        bs = 1 if base.endswith('-12') else 0
        rows = one((os.path.dirname(d), base))
        if not rows: continue
        P.append(m.trajectory(rows[bs], R))
    P = np.array(P)  # games x rounds x 3
    print(os.path.basename(an), len(P), ' '.join(f"r{r}: F{P[:, i, 0].mean():.2f} M{P[:, i, 1].mean():.2f} O{P[:, i, 2].mean():.2f} argmax F{(P[:, i].argmax(1) == 0).mean():.2f} M{(P[:, i].argmax(1) == 1).mean():.2f}" for i, r in enumerate(R)))
