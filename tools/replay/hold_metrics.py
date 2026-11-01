"""Capture-hold and flip metrics of extract.mjs output, per bot (team name): captures, capture resets by cause (walked: the
holder stepped off alive, not contested), walked resets with the payout <= 2 rounds away, holds under
pressure (an enemy within 3 of the tiles) and their outcome, deaths, and A-B-A flips (a champion's round-end
tile equals the one two rounds before and differs from the one between), with the share taking no damage.
usage: py tools/replay/hold_metrics.py EXTRACT_DIR [EXTRACT_DIR...]"""
import sys, os, json, gzip
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor

def cheb(a, b): return max(abs(a[0] - b[0]), abs(a[1] - b[1]))

def one(args):
    ex, g = args
    d = g['dir']
    meta = json.load(open(f'{ex}/{d}/meta.json'))
    mp = json.load(open(f"{ex}/maps/{meta['map']['hash']}.json"))
    ev = [json.loads(l) for l in gzip.open(f'{ex}/{d}/events.jsonl.gz', 'rt')]
    R = json.load(gzip.open(f'{ex}/{d}/rounds.json.gz'))
    teams = g['teams']
    idx = {r: i for i, r in enumerate(R['round'])}
    ch = {c['id']: c for c in R['champions']}
    team = {c['id']: c['team'] for c in meta['champions']}
    def pos(c, i):
        a = ch[c]
        if i is None or i < 0 or not a['alive'][i] or a['x'][i] is None: return None
        return (a['x'][i], a['y'][i])
    gt = {gg['id']: set(map(tuple, gg['tiles'])) for gg in mp['groups']}
    out = {t: Counter() for t in (0, 1)}
    for t in (0, 1):
        out[t]['games'] += 1
        out[t]['wins'] += g['winner'] == t
        out[t]['gems'] += g['gems'][t]
    open_ = {}
    for e in ev:
        k = e['k']
        if k == 'death': out[team[e['v']]]['deaths'] += 1 if e.get('linked') is None else 0
        elif k == 'capture':
            out[e['team']]['captures'] += 1
            out[e['team']]['capture_gems'] += sum(s[1] for s in e.get('shares', []))
        if k == 'capture_hold': open_[(e['g'], e['team'])] = e['r']
        elif k in ('capture', 'capture_reset') and (e['g'], e['team']) in open_:
            t = e['team']; r0 = open_.pop((e['g'], t)); r1 = e['r']; tiles = gt[e['g']]
            if k == 'capture': oc = 'paid'
            elif e.get('contested'): oc = 'contested'
            else:
                i = idx.get(r1)
                lv = [c for c in team if team[c] == t and i and pos(c, i - 1) in tiles and pos(c, i) not in tiles]
                oc = 'died' if lv and not ch[lv[0]]['alive'][i] else 'walked'
                if oc == 'walked' and e.get('left') is not None and e['left'] <= 2: out[t]['walked_left<=2'] += 1
            if k == 'capture_reset': out[t]['reset_' + oc] += 1
            pr = False
            for r in range(r0, r1):
                i = idx.get(r)
                if i is None: continue
                ds = [min(cheb(pos(c, i), q) for q in tiles) for c in team if team[c] != t and pos(c, i)]
                if ds and min(ds) <= 3: pr = True; break
            if pr: out[t]['pressured'] += 1; out[t]['pressured_' + oc] += 1
    n = len(R['round'])
    for c in ch:
        t = team[c]; a = ch[c]
        for i in range(2, n):
            if not (a['alive'][i] and a['alive'][i - 1] and a['alive'][i - 2]): continue
            out[t]['alive_rounds'] += 1
            p0, p1, p2 = (a['x'][i - 2], a['y'][i - 2]), (a['x'][i - 1], a['y'][i - 1]), (a['x'][i], a['y'][i])
            if p2 == p0 and p1 != p0:
                out[t]['flips'] += 1
                if a['hp'][i] >= a['hp'][i - 2] - 1e-6 and a['hp'][i - 1] >= a['hp'][i - 2] - 1e-6: out[t]['flips_nodamage'] += 1
    return {teams[t]: dict(out[t]) for t in (0, 1)}

if __name__ == '__main__':
    tot = defaultdict(Counter)
    jobs = []
    for ex in sys.argv[1:]:
        for g in json.load(open(f'{ex}/index.json'))['games']:
            if g.get('ok'): jobs.append((ex, g))
    with ProcessPoolExecutor(24) as pool:
        for res in pool.map(one, jobs, chunksize=4):
            for name, c in res.items(): tot[name].update(c)
    keys = ['wins', 'gems', 'captures', 'capture_gems', 'reset_walked', 'walked_left<=2', 'reset_contested', 'reset_died', 'pressured',
            'pressured_paid', 'pressured_walked', 'pressured_contested', 'pressured_died', 'deaths', 'flips', 'flips_nodamage']
    for name, c in sorted(tot.items()):
        ng = c['games']
        print(f"{name}: games {ng}")
        for k in keys: print(f"   {k:20s} {c[k] / ng:8.2f} /game")
        print(f"   flips per 100 alive champion-rounds {100 * c['flips'] / max(1, c['alive_rounds']):.2f}; no damage {c['flips_nodamage'] / max(1, c['flips']):.2f}")
        print(f"   pressured holds paid {c['pressured_paid'] / max(1, c['pressured']):.3f} walked {c['pressured_walked'] / max(1, c['pressured']):.3f}")
