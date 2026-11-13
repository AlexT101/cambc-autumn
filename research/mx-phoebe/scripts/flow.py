"""Gem and gold flow, time and cohesion per team, from an extract.mjs --out DIR.

    python3 flow.py EXTRACT_DIR [--by-bot CAND] [--json OUT]

Default: winner vs loser (mirror). With --by-bot NAME: that team vs the other.
"""
import argparse, gzip, json, sys, statistics
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

CHECK = (150, 300, 450, 600, 800)


def cheb(a, b):
    return max(abs(a[0] - b[0]), abs(a[1] - b[1]))


def one(args):
    d, by_bot = args
    d = Path(d)
    try:
        meta = json.loads((d / 'meta.json').read_text())
        mp = json.loads((d / meta['mapFile']).resolve().read_text())
        R = json.load(gzip.open(d / 'rounds.json.gz'))
        ev = [json.loads(l) for l in gzip.open(d / 'events.jsonl.gz', 'rt')]
    except Exception:
        return None
    res = meta['result']
    winner = res['winner']
    nR = len(R['round'])
    champs = R['champions']
    team_of = {c['id']: c['team'] for c in champs}
    mc = {c['id']: c for c in meta['champions']}
    typ = {c['id']: mc[c['id']]['name'] for c in champs}
    names = [t['name'] for t in meta['teams']]
    if by_bot:
        if names[0] == names[1]:
            return None
        focus = 0 if names[0] == by_bot else 1 if names[1] == by_bot else None
        if focus is None:
            return None
    else:
        focus = winner
    groups = {g['id']: g for g in mp['groups']}
    out = {}
    for team in (0, 1):
        o = defaultdict(float)
        o['win'] = 1.0 if winner == team else 0.0
        o['rounds'] = res['rounds']
        o['gems_final'] = res['gems'][team]
        ids = [c['id'] for c in champs if c['team'] == team]
        o['bodies'] = len(ids)
        o['has_prism'] = 1.0 if any(typ[i] == 'Prism' for i in ids) else 0.0
        out[team] = o
    # captures
    cap_by_round = {0: [], 1: []}
    for e in ev:
        k = e['k']
        if k == 'capture':
            t = e['team']
            o = out[t]
            g = groups.get(e['g'])
            gems = sum(s[1] for s in e['shares'])
            gold = sum(s[2] for s in e['shares'])
            o['captures'] += 1
            o['cap_gems'] += gems
            o['cap_gold'] += gold
            o['cap_sharers'] += len(e['shares'])
            side = g['side'] if g else -1
            rel = 'mid' if side == -1 else ('own' if side == t else 'enemy')
            o['cap_gems_' + rel] += gems
            o['captures_' + rel] += 1
            for cid, gm, gd in e['shares']:
                if typ.get(cid) == 'Prism':
                    o['cap_gems_prism'] += gm
            for c in CHECK:
                if e['r'] <= c:
                    o[f'cap_gems@{c}'] += gems
        elif k == 'death':
            v = e['v']
            t = team_of[v]
            o = out[t]
            o['deaths'] += 0 if e.get('linked') else 1
            g = e.get('gems', 0) or 0
            if 'camp' in e and e.get('camp') is not None:
                o['gems_lost_camp'] += g
                o['camp_deaths'] += 1
            else:
                o['gems_lost_kill'] += g
                if e.get('by') in team_of:
                    out[team_of[e['by']]]['gems_from_kills'] += g
                    out[team_of[e['by']]]['kills'] += 0 if e.get('linked') else 1
            if typ[v] == 'Prism':
                o['prism_deaths'] += 1
                if o['prism_first_death'] == 0:
                    o['prism_first_death'] = e['r']
            for c in CHECK:
                if e['r'] <= c:
                    o[f'deaths@{c}'] += 0 if e.get('linked') else 1
        elif k == 'tribute_start':
            out[team_of[e['a']]]['tribute_starts'] += 1
        elif k == 'tribute_end':
            o = out[team_of[e['a']]]
            o['tributes'] += 1
            o['tribute_gems'] += e['gems']
        elif k == 'tribute_cancel':
            out[team_of[e['a']]]['tribute_cancels'] += 1
        elif k == 'recall_end':
            out[team_of[e['a']]]['recalls'] += 1
        elif k == 'shop':
            out[team_of[e['a']]]['shop_visits'] += 1
    # per-round state
    for team in (0, 1):
        o = out[team]
        ids = [i for i, c in enumerate(champs) if c['team'] == team]
        en = [i for i, c in enumerate(champs) if c['team'] != team]
        g = R['gems'][team]
        for c in CHECK:
            o[f'trib@{c}'] = g[min(c, nR) - 1]
            ix = min(c, nR) - 1
            o[f'carried@{c}'] = sum(champs[i]['gems'][ix] for i in ids if champs[i]['alive'][ix])
            o[f'earned@{c}'] = sum(champs[i]['earned'][ix] for i in ids)
            o[f'unspent@{c}'] = sum(champs[i]['gold'][ix] for i in ids)
            o[f'hold@{c}'] = o[f'trib@{c}'] + o[f'carried@{c}']
            pr = [i for i in ids if typ[champs[i]['id']] == 'Prism']
            o[f'prismbag@{c}'] = sum(champs[i]['gems'][ix] for i in pr if champs[i]['alive'][ix])
        # cohesion r1-600
        iso = n = 0
        nnd = 0.0
        sup_ok = sup_n = 0
        for ix in range(min(600, nR)):
            alive = [(champs[i]['x'][ix], champs[i]['y'][ix]) for i in ids if champs[i]['alive'][ix] and champs[i]['x'][ix] is not None]
            alive_e = [(champs[i]['x'][ix], champs[i]['y'][ix]) for i in en if champs[i]['alive'][ix] and champs[i]['x'][ix] is not None]
            if len(alive) < 2:
                continue
            for a in alive:
                dmin = min(cheb(a, b) for b in alive if b is not a)
                nnd += dmin
                n += 1
                if dmin > 8:
                    iso += 1
                # local superiority: enemies within 8 of a
                ne = sum(1 for b in alive_e if cheb(a, b) <= 8)
                if ne:
                    na = sum(1 for b in alive if cheb(a, b) <= 8)  # incl self
                    sup_n += 1
                    sup_ok += 1 if na >= ne else 0
        o['nn_dist'] = nnd / n if n else 0
        o['isolated'] = iso / n if n else 0
        o['contact_rounds'] = sup_n
        o['contact_outnumbered'] = (sup_n - sup_ok) / sup_n if sup_n else 0
        # time budget-ish
        dead = alive_r = 0
        for i in ids:
            for ix in range(nR):
                if champs[i]['alive'][ix]:
                    alive_r += 1
                else:
                    dead += 1
        o['dead_frac'] = dead / max(1, dead + alive_r)
    # group availability (alive & asleep) by side relative to team
    rows = R.get('groups', [])
    cols = R.get('groupCols')
    st = {}
    avail = {0: defaultdict(int), 1: defaultdict(int)}
    last_round = {}
    # forward fill: rows [round, group, state, team, timer, respawn, awake, hp]
    rows_by_g = defaultdict(list)
    for r in rows:
        rows_by_g[r[1]].append(r)
    for gid, rs in rows_by_g.items():
        G = groups.get(gid)
        if not G:
            continue
        rs.sort()
        for j, r in enumerate(rs):
            r0 = r[0]
            r1 = rs[j + 1][0] if j + 1 < len(rs) else nR + 1
            r1 = min(r1, 601)
            if r0 >= 601:
                break
            span = max(0, r1 - r0)
            state, awake = r[2], r[6]
            if state == 1 and awake == 0:
                for team in (0, 1):
                    side = G['side']
                    rel = 'mid' if side == -1 else ('own' if side == team else 'enemy')
                    avail[team]['idle_gem_rounds_' + rel] += span * G['gems']
            if state == 2:
                for team in (0, 1):
                    side = G['side']
                    rel = 'mid' if side == -1 else ('own' if side == team else 'enemy')
                    avail[team]['cleared_gem_rounds_' + rel] += span * G['gems']
    for team in (0, 1):
        for k, v in avail[team].items():
            out[team][k] = v
    f = focus
    return {'focus': dict(out[f]), 'other': dict(out[1 - f]), 'map': meta['map']['name']}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('dir')
    ap.add_argument('--by-bot')
    ap.add_argument('--json')
    ap.add_argument('--threads', type=int, default=16)
    a = ap.parse_args()
    root = Path(a.dir)
    dirs = [p.parent for p in root.glob('*/meta.json')]
    with ProcessPoolExecutor(a.threads) as ex:
        rs = [r for r in ex.map(one, [(str(d), a.by_bot) for d in dirs], chunksize=8) if r]
    print(f'{len(rs)} games')
    keys = sorted(set(k for r in rs for k in r['focus']))
    print(f"{'metric':28s} {'focus':>10s} {'other':>10s} {'diff':>9s}")
    for k in keys:
        fa = [r['focus'].get(k, 0) for r in rs]
        ot = [r['other'].get(k, 0) for r in rs]
        mf, mo = statistics.mean(fa), statistics.mean(ot)
        print(f'{k:28s} {mf:10.3f} {mo:10.3f} {mf - mo:9.3f}')
    if a.json:
        Path(a.json).write_text(json.dumps(rs))


if __name__ == '__main__':
    main()
