"""Compare the bot's OPPC lines (debug stdout) with the offline posterior from the same replays.

usage: check_bot.py ANALYSIS_DIR REPLAY_DIR TABLES.h BOTNAME
Offline: per observer (our champion), the stream of the enemy priorities it saw at its turn starts,
state from the end of the previous round; tables from the bot's opp_tables.h.
"""
import glob, gzip, json, os, subprocess, sys, zipfile
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from build_ds import one
from model import load_tables

an, rd, tabs, bot = sys.argv[1:5]
m = load_tables(tabs)
idx = json.load(open(os.path.join(an, 'index.json')))
tot = agree = 0; worst = 0
for g in idx['games']:
    src = g['source']
    if not os.path.isabs(src): src = os.path.normpath(os.path.join(os.getcwd(), src))
    cands = glob.glob(os.path.join(rd, '**', os.path.basename(src)), recursive=True)
    if not cands: continue
    z = zipfile.ZipFile(cands[0])
    base = os.path.basename(cands[0])
    a_name = base.split('-vs-')[0]
    side = 0 if a_name == bot else 1
    out = z.read(f'team-{"ab"[side]}.stdout').decode('latin1')
    lines = [l.split() for l in out.splitlines() if l.startswith('OPPC ')]
    sides = one((os.path.join(an, g['dir']), base))
    enemy = sides[1 - side]  # the side we classify is the opponent of our bot
    meta = json.load(open(os.path.join(an, g['dir'], 'meta.json')))
    ours = [c['id'] for c in meta['champions'] if c['team'] == side]
    for l in lines:
        r, h = int(l[1]), int(l[2]); bp = np.array([float(x) for x in l[3:6]])
        o = ours.index(h)
        p = m.trajectory(enemy, [r], observer=o)[0]
        d = np.abs(p - bp).max(); tot += 1; agree += d < 2e-3; worst = max(worst, d)
        if d >= 2e-3 and tot - agree <= 10: print('DIFF', base, r, h, bp, p)
print(f'{agree}/{tot} OPPC lines agree within 0.002; worst {worst:.4f}')

# Exact check: feed the bot's own inputs (OPPT lines) to the offline token and posterior code.
from tokens import token, fish_ranks
tot2 = ok_tok = ok_post = 0
for g in idx['games']:
    cands = glob.glob(os.path.join(rd, '**', os.path.basename(g['source'])), recursive=True)
    if not cands: continue
    z = zipfile.ZipFile(cands[0]); base = os.path.basename(cands[0])
    side = 0 if base.split('-vs-')[0] == bot else 1
    out = z.read(f'team-{"ab"[side]}.stdout').decode('latin1').splitlines()
    enemy = one((os.path.join(an, g['dir']), base))[1 - side]
    roster = enemy['roster']; rk = fish_ranks(roster); n1 = len(roster) + 1
    lp = {}; res0 = {}; pend = {}
    for l in out:
        f = l.split()
        if not f or f[0] not in ('OPPT', 'OPPC'): continue
        h = int(f[2])
        if h not in lp: lp[h] = np.zeros(len(m.sub_cls)); res0[h] = {}
        if f[0] == 'OPPT':
            j, v, t = int(f[3]), int(f[4]), int(f[5])
            hp, mx, sh, gm = float(f[6]), float(f[7]), float(f[8]), int(f[9])
            tt = token(v, j, roster, rk, hp, mx, gm, sh, res0[h].get(j))
            if v != 0 and j not in res0[h]: res0[h][j] = (-v) % n1
            ok_tok += tt == t; tot2 += 1
            lp[h] = lp[h] + m.tau * m.logP[:, t]
        else:
            cl = m.prior + m.draft_ll(enemy) + m.class_lp(lp[h], n1); q = np.exp(cl - cl.max()); q /= q.sum()
            ok_post += np.abs(q - np.array([float(x) for x in f[3:6]])).max() < 1e-3
print(f'exact: tokens {ok_tok}/{tot2} equal; posteriors match on {ok_post} OPPC lines')
