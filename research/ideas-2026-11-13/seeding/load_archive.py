"""Ranked games from big-arm's per-day archive copy (g_*.npy, s_team.npy, meta.json per day).

Usage: python3 load_archive.py DATA_DIR OUT.npz
Writes one row per ranked game: created (unix s), team ids a/b (global index into `ids`),
pre-game ratings a/b, rank a/b, winner (0 = A, 1 = B, other = draw/none), map hash, day.
"""
import json, os, sys
import numpy as np

src, out = sys.argv[1], sys.argv[2]
ids, idx = [], {}
names = {}
rows = []
for day in sorted(os.listdir(src)):
    d = os.path.join(src, day)
    if not os.path.exists(os.path.join(d, 'meta.json')):
        continue
    m = json.load(open(os.path.join(d, 'meta.json')))
    teams = m['teams']
    gmap = np.empty(len(teams), np.int32)
    for i, t in enumerate(teams):
        if t['id'] not in idx:
            idx[t['id']] = len(ids)
            ids.append(t['id'])
        gmap[i] = idx[t['id']]
        names[t['id']] = t['name']  # latest name wins
    kind = np.load(os.path.join(d, 'g_kind.npy'))
    ranked = m['kinds'].index('ranked')
    st = np.load(os.path.join(d, 's_team.npy')).reshape(-1, 2)
    sel = kind == ranked
    cr = np.load(os.path.join(d, 'g_created.npy'))[sel]
    rt = np.load(os.path.join(d, 'g_rating.npy'))[sel]
    rk = np.load(os.path.join(d, 'g_rank.npy'))[sel]
    w = np.load(os.path.join(d, 'g_winner.npy'))[sel]
    mh = np.load(os.path.join(d, 'g_map_hash.npy'))[sel]
    ta, tb = gmap[st[sel, 0]], gmap[st[sel, 1]]
    rows.append(dict(created=cr, a=ta, b=tb, ra=rt[:, 0], rb=rt[:, 1], ka=rk[:, 0], kb=rk[:, 1],
                     winner=w, day=np.full(sel.sum(), int(day.replace('-', '')), np.int32)))
    print(day, int(sel.sum()), file=sys.stderr)
cat = {k: np.concatenate([r[k] for r in rows]) for k in rows[0]}
o = np.argsort(cat['created'], kind='stable')
cat = {k: v[o] for k, v in cat.items()}
np.savez_compressed(out, ids=np.array(ids), names=np.array([names[i] for i in ids]), **cat)
