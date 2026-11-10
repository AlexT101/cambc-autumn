"""Live trace check: our OPPL lines (release printf) from captured platform games.

usage: live_check.py WORK LIST.tsv TABLES.h
WORK holds zips/ (capture zips, any depth); LIST.tsv is the capture listing
(match_id created_at kind map team_a team_b name_a name_b result_a picks_a picks_b engine replay).
Unpacks replays to WORK/repl, extracts to WORK/an (extract.mjs), then reports per champion instance:
accuracy by round of the bot's argmax against the true opponent, confident misreads, and the bot's
posterior against the offline one restricted to that instance's view.
"""
import collections, glob, json, os, re, subprocess, sys, zipfile
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from build_ds import one
from model import load_tables

OURS = '547efb5b-57e5-4355-8501-3b331f506d62'
ROUNDS = [1, 25, 50, 100, 200, 300, 500, 1000]
work, lst, tabs = sys.argv[1:4]
m = load_tables(tabs)
cls_of = lambda n: 0 if n == 'Intercontinental Fish' else 1 if n == 'Mite' else 2

games = {}
for l in open(lst):
    f = l.rstrip('\n').split('\t')
    if len(f) < 13 or f[0] == 'match_id': continue
    side = 0 if f[4] == OURS else 1 if f[5] == OURS else None
    if side is None: continue
    games[f[0]] = dict(side=side, opp=f[7 - side], kind=f[2], map=f[3], zip=f[12])

repl = os.path.join(work, 'repl'); os.makedirs(repl, exist_ok=True)
traces = {}
for mid, g in games.items():
    zs = glob.glob(os.path.join(work, 'zips', '**', mid + '.zip'), recursive=True)
    if not zs: continue
    z = zipfile.ZipFile(zs[0]); names = z.namelist()
    so = f'team-{"ab"[g["side"]]}.stdout'
    if so not in names: continue
    # stdout carries other bytes before a line: match the fields, not the line start
    lines = [x.split() for x in re.findall(r'OPPL -?\d+ \d+ [\d.]+ [\d.]+ [\d.]+', z.read(so).decode('latin1'))]
    if not lines: continue  # another version of ours
    traces[mid] = lines
    rp = os.path.join(repl, mid + '.repl26a')
    if not os.path.exists(rp):
        open(rp, 'wb').write(z.read('replay.repl26a'))
an = os.path.join(work, 'an')
if not os.path.exists(os.path.join(an, 'index.json')):
    subprocess.run(['node', 'tools/replay/extract.mjs', repl, '--threads', '4', '--out', an],
                   cwd='/home/ubuntu/cambc-autumn', stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
idx = json.load(open(os.path.join(an, 'index.json')))
dir_of = {os.path.basename(g['source']).split('.')[0]: g['dir'] for g in idx['games']}

acc = collections.defaultdict(lambda: collections.defaultdict(list))  # [opp][r] -> correct flags
conf_wrong = collections.defaultdict(lambda: collections.defaultdict(int))
diffs = []; worst = []
per_game = []
for mid, lines in traces.items():
    g = games[mid]; true = cls_of(g['opp'])
    d = dir_of.get(mid)
    meta = json.load(open(os.path.join(an, d, 'meta.json'))) if d else None
    nround = meta.get('rounds', 2000) if meta else 2000
    ours = [c['id'] for c in meta['champions'] if c['team'] == g['side']] if meta else []
    enemy = one((os.path.join(an, d), mid + '.repl26a'))[1 - g['side']] if d else None
    by_h = collections.defaultdict(list)
    for l in lines:
        by_h[int(l[2])].append((int(l[1]), np.array([float(x) for x in l[3:6]])))
    for h, seq in by_h.items():
        for r in ROUNDS:
            if r > nround: continue
            prev = [p for rr, p in seq if rr <= r]
            if not prev: continue
            p = prev[-1]; top = int(p.argmax())
            acc[g['opp']][r].append(top == true)
            if top != true and p[top] > 0.9: conf_wrong[g['opp']][r] += 1
        if enemy is not None and h in ours:
            o = ours.index(h)
            off = m.trajectory(enemy, [rr for rr, _ in seq], observer=o)
            for (rr, p), q in zip(seq, off):
                dd = float(np.abs(p - q).max()); diffs.append(dd)
                if dd >= 2e-3: worst.append((dd, mid, h, rr, p.round(4).tolist(), np.round(q, 4).tolist()))
    per_game.append((g['opp'], g['kind'], mid))

print(f'games with OPPL: {len(traces)} of {len(games)} listed ours')
kinds = collections.Counter(k for _, k, _ in per_game); print('kinds', dict(kinds))
grp = lambda n: 'Fish' if cls_of(n) == 0 else 'Mite' if cls_of(n) == 1 else n
pooled = collections.defaultdict(lambda: collections.defaultdict(list))
pcw = collections.defaultdict(lambda: collections.defaultdict(int))
for opp, rs in acc.items():
    for r, v in rs.items():
        pooled[grp(opp)][r] += v; pcw[grp(opp)][r] += conf_wrong[opp][r]
        if cls_of(opp) == 2: pooled['all other'][r] += v; pcw['all other'][r] += conf_wrong[opp][r]
print('accuracy (argmax = true) per instance by round; n instances; confident (>0.9) misreads')
print(f'{"opponent":28s} ' + ' '.join(f'r{r:<5d}' for r in ROUNDS))
for k in sorted(pooled, key=lambda k: (k not in ('Fish', 'Mite', 'all other'), k)):
    rs = pooled[k]
    print(f'{k[:28]:28s} ' + ' '.join(f'{np.mean(rs[r]):.3f} ' if rs.get(r) else '  -    ' for r in ROUNDS)
          + f' n={len(rs.get(1, rs.get(25, [])))} conf_wrong@r100/300={pcw[k][100]}/{pcw[k][300]}')
if diffs:
    d = np.array(diffs)
    print(f'bot vs offline (own view): {np.mean(d < 2e-3) * 100:.2f}% of {len(d)} OPPL lines within 0.002; worst {d.max():.4f}')
    for w in sorted(worst, reverse=True)[:8]: print('DIFF', w)
