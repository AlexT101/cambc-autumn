# Rows of draft5 for the GBM: the games model.mjs gameRows keeps, map features, folds (model.mjs hash % 5).
import json, math, sys
import numpy as np

LAB = '/home/ubuntu/cambc-autumn/replays/draftlab/draft5'
OUT = sys.argv[1]
CHAMPS = ['ryth', 'vesper_vale', 'vendetta', 'cassi_and_issac', 'stellar', 'prism', 'marcella', 'willow', 'ren', 'varg', 'tavi', 'heart_of_ruin']
CI = {c: i for i, c in enumerate(CHAMPS)}
FEAT = [('area', 'log'), ('reach_frac', None), ('spawn_dist', 'log'), ('detour', None), ('choke_rel', None), ('openness', None),
        ('bushes', None), ('holes', None), ('altars', 'log1p'), ('altar_ratio', None), ('altar_centre', None), ('gems_side', 'log1p'),
        ('gold_side', 'log1p'), ('big_share', None), ('cluster_share', None), ('contested_share', None), ('big_camp_share', None),
        ('dash_short', None), ('camp_near', 'log1p'), ('dash_gain', 'log'), ('narrow', None), ('spawn_ring', None),
        ('max_group', 'log1p'), ('camp_altar', 'log'), ('sight_gap', None)]
# Raw metrics not in the model, for the GBM to find missing structure (cheap ones in C++ or not).
EXTRA = ['altar_near', 'walls', 'aspect', 'monoliths', 'golems', 'shared_groups', 'camps_side', 'altar_gap', 'altar_slots', 'off_altars', 'tele_gain', 'W', 'H']


def fnv(s):
    h = 2166136261
    for ch in s:
        h = ((h ^ ord(ch)) * 16777619) & 0xffffffff
    return h


def tf(v, t):
    if v is None or (isinstance(v, float) and not math.isfinite(v)) or isinstance(v, bool):
        return float('nan') if not isinstance(v, bool) else float(v)
    if t == 'log': return math.log(max(v, 1))
    if t == 'log1p': return math.log1p(max(v, 0))
    return float(v)


maps = {}
for l in open(f'{LAB}/maps.jsonl'):
    m = json.loads(l)
    if m['picks'] not in (3, 4, 5): continue
    f = m['f']
    row = [tf(f.get(n), t) for n, t in FEAT] + [float(f['altars'])] + [tf(f.get(n) if n not in 'WH' else m[n], None) for n in EXTRA]
    maps[m['key']] = (row, m['set'] == 'maps', m['set'])
mkeys = sorted(maps)
mindex = {k: i for i, k in enumerate(mkeys)}
MF = np.array([maps[k][0] for k in mkeys], dtype=np.float64)
ladder = np.array([maps[k][1] for k in mkeys])

ids, mi, picks, A, B, win = [], [], [], [], [], []
meta = json.load(open(f'{LAB}/games.slim.json'))
assert meta['bytes'] == __import__('os').path.getsize(f'{LAB}/games.jsonl')
with open(f'{LAB}/games.slim.jsonl') as fh:
    for l in fh:
        g = json.loads(l)
        if g.get('error') or g.get('winner') is None or g.get('draft_ok') is False: continue
        if g['key'] not in mindex: continue
        a = np.zeros(12, np.int8); b = np.zeros(12, np.int8)
        for c in g['A']: a[CI[c]] = 1
        for c in g['B']: b[CI[c]] = 1
        ids.append(g['id']); mi.append(mindex[g['key']]); picks.append(g['picks']); A.append(a); B.append(b); win.append(1 if g['winner'] == 0 else 0)
fold = np.array([fnv(k) % 5 for k in mkeys], np.int8)
np.savez_compressed(OUT, ids=np.array(ids), mi=np.array(mi, np.int32), picks=np.array(picks, np.int8), A=np.array(A), B=np.array(B),
                    win=np.array(win, np.int8), MF=MF, mkeys=np.array(mkeys), mfold=fold, ladder=ladder,
                    fnames=np.array([n for n, _ in FEAT] + ['altars_raw'] + EXTRA))
print(len(ids), 'games', len(mkeys), 'maps')
