"""Which knob draws make the noise bodies beat us: our win regressed on the body's draws (log-multipliers, N(0,1)) per
epoch, with (bot, map, side, opponent) cell means removed, over cached dgate runs on the new bodies (diverse agent).
    python3 knobreg.py DRAWS.npz [BOT_TAG_REGEX]
OPP=F|M keeps one opponent's bodies. A negative coefficient: raising that knob in the body (x exp(0.2)) lowers our win rate, i.e. helps the body."""
import sys, os, re, json, collections, numpy as np
sys.path.insert(0, '/home/ubuntu/cambc-autumn/research/ideas-2026-11-08/spar-tools'); import local
NAMES = [n for n, _ in json.load(open('/home/ubuntu/cambc-autumn/bots/variants/dvp-n1/src/tune.json'))['floats']] + \
        [n for n, _ in json.load(open('/home/ubuntu/cambc-autumn/bots/variants/dvp-n1/src/tune.json'))['ints']]
USE = [i for i in range(26) if i not in (2, 5)]  # 2, 5 are map-conditioned, not drawn
E = 5
d = np.load(sys.argv[1]); D = {k: v for k, v in zip(d['keys'], d['vals'])}
pat = re.compile(sys.argv[2] if len(sys.argv) > 2 else '.')
runs = [n for n in os.listdir('/home/ubuntu/cambc-autumn/replays/ab') if re.match(r'^spar-c.*-dvn\d+[FM]2$', n)]
rows = collections.defaultdict(list)  # cell -> [(y, x)]
for n in runs:
    m = re.match(r'^spar-c(.*)-dvn(\d+)([FM])2$', n); bot, k, o = m.group(1), int(m.group(2)), m.group(3)
    if k > 600 or not pat.search(bot) or (os.environ.get('OPP') and o != os.environ['OPP']): continue
    try: ms = list(local.matches(n))
    except Exception: continue
    for mp, side, mm in ms:
        t = 1 if side == 'a' else 0  # the body's team
        x = [D.get(f'{mp}|{t}|{k}|{e}') for e in range(E)]
        if any(v is None for v in x): continue
        rows[(bot, mp, side, o)].append((float(mm['winner'] == 0), np.concatenate([v[USE] for v in x]) / 1000.0))
Y, X = [], []
for c, r in rows.items():
    if len(r) < 2: continue
    y = np.array([a for a, _ in r]); x = np.array([b for _, b in r])
    Y.append(y - y.mean()); X.append(x - x.mean(0))
Y = np.concatenate(Y); X = np.concatenate(X)
beta, *_ = np.linalg.lstsq(X, Y, rcond=None)
res = Y - X @ beta; s2 = res.var(); se = np.sqrt(np.diag(np.linalg.inv(X.T @ X)) * s2)
print(f'{len(Y)} games, {len(rows)} cells; coefficient = our win-rate points per +1 sd of the body draw (sd 0.2 in log)')
B = (100 * beta).reshape(E, len(USE)); S = (100 * se).reshape(E, len(USE))
print(f"{'knob':28s}" + ''.join(f'   e{e} (r{100*e}-{100*e+99})' for e in range(E)) + '   all-epochs sum')
order = np.argsort(B.sum(0))
for j in order:
    tot = B[:, j].sum(); tse = np.sqrt((S[:, j] ** 2).sum())
    print(f'{NAMES[USE[j]]:28s}' + ''.join(f'  {B[e, j]:+6.2f} ±{1.96*S[e, j]:4.2f}   ' for e in range(E)) + f'  {tot:+6.2f} ±{1.96*tse:4.2f}')
