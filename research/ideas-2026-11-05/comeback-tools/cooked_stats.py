#!/usr/bin/env python3
"""cooked_stats.py ANA [--batch B] [--json OUT]: cooked states in extracted games.

For each game and each cooked definition, the first round a team is cooked, whether it came back, the rounds
left, and what the leader does from then on (tribute cadence and size, its bodies' spread, carriers alone,
where it farms). With --batch (an ab.py batch dir, bot 1 = CAND), rows carry who was cooked (cand / ref).
Definitions (trailer t, leader o; tributed gems s, bags b):
  g600: s_o >= 600 and s_o - s_t >= 200 (altar_guard's trigger)
  g400: s_o >= 400 and s_o - s_t >= 150
  rs:   R-scaled: gap >= 200 * (1 - round / 2000) + 100 and s_o >= 300 (needs less as rounds run out)
  wb:   with bags: s_o + b_o >= 700 and (s_o + b_o) - (s_t + b_t) >= 300
"""
import json, gzip, os, sys, collections, statistics as st

def defs(so, st_, bo, bt, r):
    return {
        'g600': so >= 600 and so - st_ >= 200,
        'g400': so >= 400 and so - st_ >= 150,
        'rs': so >= 300 and so - st_ >= 200 * (1 - r / 2000) + 100,
        'wb': so + bo >= 700 and (so + bo) - (st_ + bt) >= 300,
    }

def main():
    a = sys.argv[1:]
    ANA = a[0]
    batch = a[a.index('--batch') + 1] if '--batch' in a else None
    out = a[a.index('--json') + 1] if '--json' in a else None
    ix = json.load(open(f'{ANA}/index.json'))
    games = ix['games']
    cand_of = {}
    if batch:
        files = set(f for f in os.listdir(batch) if f.endswith('.repl26a'))
        games = [g for g in games if os.path.basename(g['source']) in files]
        for g in games:
            f = os.path.basename(g['source'])
            cand_of[g['dir']] = 0 if f[-10:-8] == '12' else 1
    rows = []
    for g in games:
        d = f"{ANA}/{g['dir']}"
        try:
            m = json.load(open(f'{d}/meta.json'))
            R = json.load(gzip.open(f'{d}/rounds.json.gz'))
        except Exception:
            continue
        w = m['result']['winner']
        n = len(R['round'])
        ch = R['champions']
        team = [c['team'] for c in ch]
        spawn = [None, None]
        for c in ch:
            if spawn[c['team']] is None: spawn[c['team']] = (c['x'][0], c['y'][0])
        bags = [[0] * n, [0] * n]
        for c in ch:
            for i in range(n): bags[c['team']][i] += c['gems'][i] if c['alive'][i] else 0
        events = None
        for name in ('g600', 'g400', 'rs', 'wb'):
            hit = None
            for i in range(n):
                r = R['round'][i]
                for t in (0, 1):
                    o = 1 - t
                    if defs(R['gems'][o][i], R['gems'][t][i], bags[o][i], bags[t][i], r)[name]: hit = (t, i); break
                if hit: break
            if not hit: continue
            t, i0 = hit
            o = 1 - t
            row = {'game': g['dir'], 'def': name, 'trail': t, 'won': int(w == t), 'round': R['round'][i0], 'end': m['result']['rounds'],
                   'gap': R['gems'][o][i0] - R['gems'][t][i0], 'lead_s': R['gems'][o][i0], 'trail_s': R['gems'][t][i0],
                   'lead_b': bags[o][i0], 'trail_b': bags[t][i0], 'altars': None}
            if batch: row['who'] = 'cand' if t == cand_of[g['dir']] else 'ref'
            if name == 'g600':
                # Leader behaviour from the cook point on.
                lead = [k for k, c in enumerate(ch) if c['team'] == o]
                trail = [k for k, c in enumerate(ch) if c['team'] == t]
                spread, alone_carry, carry_rounds, own_half, rounds = [], 0, 0, 0, 0
                big_alone = 0
                for i in range(i0, n, 5):
                    pts = [(ch[k]['x'][i], ch[k]['y'][i], ch[k]['gems'][i]) for k in lead if ch[k]['alive'][i]]
                    if len(pts) >= 2:
                        ds = [max(abs(p[0] - q[0]), abs(p[1] - q[1])) for x, p in enumerate(pts) for q in pts[x + 1:]]
                        spread.append(st.mean(ds))
                    for p in pts:
                        rounds += 1
                        dso = max(abs(p[0] - spawn[o][0]), abs(p[1] - spawn[o][1]))
                        dst = max(abs(p[0] - spawn[t][0]), abs(p[1] - spawn[t][1]))
                        own_half += dso <= dst
                        if p[2] >= 30:
                            carry_rounds += 1
                            near = any(max(abs(p[0] - q[0]), abs(p[1] - q[1])) <= 4 for q in pts if q is not p)
                            alone_carry += not near
                            big_alone += (not near) and p[2] >= 100
                row.update(spread=st.mean(spread) if spread else None, lead_body_rounds=rounds, lead_own_half=own_half / max(1, rounds),
                           carrier_share=carry_rounds / max(1, rounds), carrier_alone=alone_carry / max(1, carry_rounds),
                           big_alone=big_alone / max(1, rounds))
                tribs, kills_on_lead, lead_bag_taken, trail_deaths, trail_bag_lost = [], 0, 0, 0, 0
                for l in gzip.open(f'{d}/events.jsonl.gz', 'rt'):
                    e = json.loads(l)
                    if e['r'] < R['round'][i0]: continue
                    k = e['k']
                    if k == 'tribute_end' and team[e['a']] == o: tribs.append((e['r'], e['gems']))
                    elif k == 'death':
                        if team[e['v']] == o:
                            if e.get('by') is not None and e['by'] < len(team) and team[e['by']] == t:
                                kills_on_lead += 1; lead_bag_taken += e.get('gems', 0)
                        else:
                            trail_deaths += 1; trail_bag_lost += e.get('gems', 0)
                gaps = [b[0] - a_[0] for a_, b in zip(tribs, tribs[1:])]
                row.update(lead_tribs=len(tribs), lead_trib_mean=st.mean([x[1] for x in tribs]) if tribs else 0,
                           lead_trib_gap=st.median(gaps) if gaps else None, kills_on_lead=kills_on_lead, lead_bag_taken=lead_bag_taken,
                           trail_deaths=trail_deaths, trail_bag_lost=trail_bag_lost)
            rows.append(row)
    if out: json.dump(rows, open(out, 'w'))
    report(rows, bool(batch))

def report(rows, ab):
    by = collections.defaultdict(list)
    for r in rows: by[(r['def'], r.get('who', 'all'))].append(r)
    print('def who n comeback% round(med) rounds_left(med) gap(med)')
    for k in sorted(by):
        v = by[k]
        print(k[0], k[1], len(v), f"{100 * st.mean(x['won'] for x in v):.1f}", st.median(x['round'] for x in v),
              st.median(x['end'] - x['round'] for x in v), st.median(x['gap'] for x in v))
    g = [r for r in rows if r['def'] == 'g600']
    if g:
        keys = ['spread', 'lead_own_half', 'carrier_share', 'carrier_alone', 'big_alone', 'lead_tribs', 'lead_trib_mean', 'lead_trib_gap',
                'kills_on_lead', 'lead_bag_taken', 'trail_deaths', 'trail_bag_lost']
        for who in sorted(set(r.get('who', 'all') for r in g)):
            for won in (0, 1):
                v = [r for r in g if r.get('who', 'all') == who and r['won'] == won]
                if not v: continue
                print(f'g600 {who} won={won} n={len(v)}', ' '.join(
                    f"{k}={st.mean([x[k] for x in v if x[k] is not None]):.2f}" for k in keys if any(x[k] is not None for x in v)))
        # comeback by rounds left and gap at the cook point
        print('g600 comeback by rounds left at cook (all):')
        for lo, hi in ((0, 100), (100, 200), (200, 400), (400, 800), (800, 2000)):
            v = [r for r in g if lo <= r['end'] - r['round'] < hi]
            if v: print(f'  left {lo}-{hi}: n={len(v)} comeback {100 * st.mean(x["won"] for x in v):.1f}%')
        print('g600 comeback by cook round:')
        for lo, hi in ((0, 300), (300, 500), (500, 800), (800, 1200), (1200, 2001)):
            v = [r for r in g if lo <= r['round'] < hi]
            if v: print(f'  round {lo}-{hi}: n={len(v)} comeback {100 * st.mean(x["won"] for x in v):.1f}%')

if __name__ == '__main__':
    main()
