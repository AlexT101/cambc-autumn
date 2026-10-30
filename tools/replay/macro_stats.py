"""Macro statistics per team from extracted replays: where champion time goes, how camps are cleared,
captured and lost, and how winners differ from losers.

    py tools/replay/macro_stats.py ANALYSIS_DIR [--bot NAME] [--json OUT]

ANALYSIS_DIR is an extract.mjs --out directory (or replays/.analysis). With --bot, only that team's rows
(teams are named by the batch's bots), else both teams of every game."""
import argparse
import gzip
import json
import sys
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path


def cheb(a, b):
    return max(abs(a[0] - b[0]), abs(a[1] - b[1]))


def game_stats(d):
    d = Path(d)
    meta = json.loads((d / 'meta.json').read_text())
    root = d.parent
    mf = (d / meta['mapFile']).resolve()
    mp = json.loads(mf.read_text()) if mf.exists() else None
    if mp is None:
        return None
    R = json.load(gzip.open(d / 'rounds.json.gz'))
    ev = [json.loads(l) for l in gzip.open(d / 'events.jsonl.gz', 'rt')]
    n = len(R['round'])
    champs = R['champions']
    team_of = {c['id']: c['team'] for c in champs}
    idx = {c['id']: i for i, c in enumerate(champs)}
    camp_group = {c['id']: c['group'] for c in mp['camps']}
    groups = mp['groups']
    group_gems = {g['id']: g['gems'] for g in groups}
    group_tiles = {}
    for g in groups:
        for t in g['tiles']:
            group_tiles[tuple(t)] = g['id']
    spawn = mp['spawn']

    def on_spawn(team, x, y):
        s = spawn[team]
        return s['minX'] <= x <= s['maxX'] and s['minY'] <= y <= s['maxY']

    # per champion per round flags
    campdmg = defaultdict(float)   # (cid, r) -> camp damage dealt
    champdmg = defaultdict(float)  # (cid, r) -> champion damage dealt
    took_champ = defaultdict(float)
    took_camp = defaultdict(float)
    recall_rounds = set()
    real_recalls = Counter()
    clear_dmg = defaultdict(lambda: defaultdict(float))  # group -> cid -> damage since last clear
    clear_start = {}
    clear_taken = defaultdict(lambda: defaultdict(float))  # group -> team -> camp damage taken
    clears = []
    captures = []
    deaths = []
    tributes = []
    kills = Counter()
    for e in ev:
        k = e['k']
        r = e['r']
        if k in ('attack', 'cast'):
            a = e['a']
            for cid, amt in e.get('cdmg', []) or []:
                campdmg[(a, r)] += amt
                g = camp_group.get(cid)
                if g is not None:
                    clear_dmg[g][a] += amt
                    clear_start.setdefault(g, r)
            for cid, amt in e.get('dmg', []) or []:
                if cid in team_of and team_of[cid] != team_of[a]:
                    champdmg[(a, r)] += amt
                    took_champ[(cid, r)] += amt
        elif k == 'camp_attack':
            t = e.get('tgt')
            if t is not None:
                took_camp[(t, r)] += e['dmg']
                g = e.get('g')
                clear_taken[g][team_of[t]] += e['dmg']
        elif k == 'recall_end':
            a = e['a']
            real_recalls[a] += 1
            for rr in range(r - 5, r + 1):
                recall_rounds.add((a, rr))
        elif k == 'group_clear':
            g = e['g']
            by = e.get('by')
            t = team_of.get(by, -1)
            dm = clear_dmg.get(g, {})
            ours = {c: v for c, v in dm.items() if team_of[c] == t}
            theirs = {c: v for c, v in dm.items() if team_of[c] != t}
            tot = sum(ours.values())
            helpers = sum(1 for v in ours.values() if v >= 0.1 * tot)
            clears.append({'r': r, 'g': g, 'team': t, 'types': groups[g]['types'], 'gems': groups[g]['gems'], 'gold': groups[g]['gold'],
                           'n': len(ours), 'n10': helpers, 'dur': r - clear_start.get(g, r) + 1, 'enemy_dmg': sum(theirs.values()),
                           'taken': clear_taken[g][t], 'taken_enemy': clear_taken[g][1 - t] if t in (0, 1) else 0})
            clear_dmg.pop(g, None)
            clear_start.pop(g, None)
            clear_taken.pop(g, None)
        elif k == 'capture':
            captures.append({'r': r, 'g': e['g'], 'team': e['team'], 'holders': len(e['shares']),
                             'gems': sum(s[1] for s in e['shares']), 'gold': sum(s[2] for s in e['shares'])})
        elif k == 'death':
            v = e['v']
            deaths.append({'r': r, 'team': team_of[v], 'gems': e.get('gems', 0), 'camp': 'camp' in e, 'by': e.get('by'),
                           'linked': 'linked' in e})
            if 'by' in e and e['by'] is not None and not e.get('linked'):
                kills[team_of[e['by']]] += 1
        elif k == 'tribute_end':
            tributes.append({'r': r, 'team': team_of[e['a']], 'gems': e['gems']})

    # time classification
    cats = ['dead', 'tribute', 'recall', 'spawn', 'camp', 'hold', 'fight', 'move', 'still']
    time = {0: Counter(), 1: Counter()}
    # capture holding: on a cleared group's tile
    # groups state forward-fill
    gstate = {}
    grows = R['groups']
    gi = 0
    gstate_by_round = []
    ally_near = {0: [], 1: []}  # mean count of allies within 5 while alive, sampled
    sep = {0: [], 1: []}
    idle_gem_rounds = Counter()
    seqs = defaultdict(list)
    xs = [c['x'] for c in champs]
    ys = [c['y'] for c in champs]
    for i in range(n):
        rnd = R['round'][i]
        while gi < len(grows) and grows[gi][0] <= rnd:
            row = grows[gi]
            gstate[row[1]] = row
            gi += 1
        for gid, row in gstate.items():
            if row[2] == 1 and row[6] == 0:
                side = groups[gid]['side']
                idle_gem_rounds[side] += group_gems[gid] / max(1, groups[gid]['respawn'])
        for j, c in enumerate(champs):
            t = c['team']
            cid = c['id']
            if not c['alive'][i]:
                time[t]['dead'] += 1
                continue
            x, y = c['x'][i], c['y'][i]
            if x is None:
                time[t]['dead'] += 1
                continue
            ch = c['chan'][i]
            if ch == 2:
                cat = 'tribute'
            elif (cid, rnd) in recall_rounds:
                cat = 'recall'
            elif campdmg.get((cid, rnd)):
                cat = 'camp'
            elif champdmg.get((cid, rnd)) or took_champ.get((cid, rnd)):
                cat = 'fight'
            elif (x, y) in group_tiles and gstate.get(group_tiles[(x, y)], [0, 0, 0])[2] == 2:
                cat = 'hold'
            elif on_spawn(t, x, y):
                cat = 'spawn'
            elif i > 0 and (c['x'][i - 1], c['y'][i - 1]) != (x, y):
                cat = 'move_bag' if c['gems'][i] > 0 else ('move_hurt' if c['hp'][i] < 0.5 * c['maxHp'][i] else 'move')
            else:
                cat = 'still'
            time[t][cat] += 1
            seqs[cid].append(cat)
            if i % 10 == 0:
                near = 0
                for j2, c2 in enumerate(champs):
                    if j2 != j and c2['team'] == t and c2['alive'][i] and c2['x'][i] is not None and cheb((x, y), (c2['x'][i], c2['y'][i])) <= 5:
                        near += 1
                ally_near[t].append(near)

    out = {'dir': d.name, 'map': meta['map']['name'], 'rounds': meta['result']['rounds'], 'winner': meta['result']['winner'],
           'gems': meta['result']['gems'], 'names': [meta['teams'][0].get('name'), meta['teams'][1].get('name')],
           'picks': len([c for c in champs if c['team'] == 0]), 'area': mp['width'] * mp['height'], 'teams': {}}
    final = n - 1
    segs = {0: Counter(), 1: Counter()}
    seg_n = {0: Counter(), 1: Counter()}
    walkish = ('move', 'move_bag', 'move_hurt', 'still')
    for c in champs:
        q = seqs[c['id']]
        i = 0
        while i < len(q):
            if q[i] in walkish:
                j = i
                kinds = Counter()
                while j < len(q) and q[j] in walkish:
                    kinds[q[j]] += 1
                    j += 1
                end = q[j] if j < len(q) else 'end'
                start = q[i - 1] if i > 0 else 'start'
                segs[c['team']][f'from:{start}'] += j - i
                seg_n[c['team']][f'from:{start}'] += 1
                lead = 'bag' if kinds['move_bag'] > (j - i) / 2 else 'hurt' if kinds['move_hurt'] > (j - i) / 2 else 'empty'
                segs[c['team']][f'{lead}->{end}'] += j - i
                seg_n[c['team']][f'{lead}->{end}'] += 1
                i = j
            else:
                i += 1
    for t in (0, 1):
        tc = [c for c in champs if c['team'] == t]
        cl = [c for c in clears if c['team'] == t]
        cp = [c for c in captures if c['team'] == t]
        dt = [x for x in deaths if x['team'] == t and not x['linked']]
        out['teams'][t] = {
            'time': dict(time[t]),
            'earned': sum(c['earned'][final] for c in tc),
            'earned300': sum(c['earned'][min(300, final)] for c in tc),
            'gems300': R['gems'][t][min(300, final)],
            'gems600': R['gems'][t][min(600, final)],
            'clears': len(cl),
            'clear_gems': sum(c['gems'] for c in cl),
            'clear_helpers': Counter(min(c['n10'], 4) for c in cl if 'Gem cluster' not in c['types'] and 'Gold cluster' not in c['types']),
            'clear_taken': sum(c['taken'] for c in cl),
            'clear_by_type': Counter('+'.join(sorted(set(c['types']))) for c in cl),
            'striker_clears': [(c['n10'], c['dur'], c['taken'], c['gems']) for c in cl if any(tp in ('Wolf', 'Elk', 'Golem', 'Monolith') for tp in c['types'])],
            'captures': len(cp),
            'capture_gems': sum(c['gems'] for c in cp),
            'capture_gold': sum(c['gold'] for c in cp),
            'holders': Counter(c['holders'] for c in cp),
            'deaths': len(dt),
            'deaths_camp': sum(1 for x in dt if x['camp']),
            'gems_lost': sum(x['gems'] for x in dt),
            'kills': kills[t],
            'segs': dict(segs[t]), 'seg_n': dict(seg_n[t]),
            'idle_own': idle_gem_rounds[t] / n, 'idle_mid': idle_gem_rounds[-1] / n, 'idle_enemy': idle_gem_rounds[1 - t] / n,
            'gem_rate_total': sum(g['gems'] / max(1, g['respawn']) for g in groups),
            'tributes': len([x for x in tributes if x['team'] == t]),
            'tribute_gems': sum(x['gems'] for x in tributes if x['team'] == t),
            'recalls': sum(real_recalls[c['id']] for c in tc),
            'ally_near': sum(ally_near[t]) / max(1, len(ally_near[t])),
            'camp_taken': sum(v for (cid, r), v in took_camp.items() if team_of[cid] == t),
            'champ_taken': sum(v for (cid, r), v in took_champ.items() if team_of[cid] == t),
        }
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('root')
    ap.add_argument('--json')
    ap.add_argument('--threads', type=int, default=32)
    ap.add_argument('--limit', type=int, default=0)
    args = ap.parse_args()
    root = Path(args.root)
    dirs = sorted(p.parent for p in root.glob('*/meta.json'))
    if args.limit:
        dirs = dirs[:args.limit]
    with ProcessPoolExecutor(args.threads) as ex:
        res = [r for r in ex.map(game_stats, dirs, chunksize=2) if r]
    if args.json:
        Path(args.json).write_text(json.dumps(res, default=lambda o: dict(o)))
    report(res)


def report(res):
    print(f'{len(res)} games, mean rounds {sum(r["rounds"] for r in res) / len(res):.0f}, reach 2000: {sum(r["rounds"] >= 2000 for r in res)}')
    for label, sel in (('winner', lambda r, t: r['winner'] == t), ('loser', lambda r, t: r['winner'] != t)):
        rows = [r['teams'][t] for r in res for t in (0, 1) if sel(r, t)]
        tot = Counter()
        for x in rows:
            tot.update(x['time'])
        s = sum(tot.values())
        print(f'\n== {label} ({len(rows)} team-games)')
        print('time share: ' + ', '.join(f'{k} {100 * v / s:.1f}%' for k, v in sorted(tot.items(), key=lambda kv: -kv[1])))
        def m(key):
            return sum(x[key] for x in rows) / len(rows)
        for key in ('gems300', 'gems600', 'earned300', 'earned', 'clears', 'clear_gems', 'captures', 'capture_gems', 'capture_gold', 'deaths',
                    'deaths_camp', 'gems_lost', 'kills', 'idle_own', 'idle_mid', 'idle_enemy', 'gem_rate_total', 'tributes', 'tribute_gems', 'recalls', 'ally_near', 'camp_taken', 'champ_taken'):
            print(f'  {key:14s} {m(key):9.1f}')
        sg, sn = Counter(), Counter()
        for x in rows:
            sg.update(x['segs']); sn.update(x['seg_n'])
        tot_alive = sum(v for k, v in tot.items() if k != 'dead')
        print('  walk/idle segments by what ends them: share of alive time, count/game, mean length')
        for k, v in sg.most_common(24):
            print(f'    {k:22s} {100 * v / tot_alive:5.1f}%  {sn[k] / len(rows):6.1f}  {v / sn[k]:5.1f}')
        h = Counter()
        for x in rows:
            h.update({int(k): v for k, v in x['holders'].items()})
        print('  holders per capture:', dict(sorted(h.items())))
        h = Counter()
        for x in rows:
            h.update({int(k): v for k, v in x['clear_helpers'].items()})
        print('  champions (>=10% dmg) per striker clear:', dict(sorted(h.items())))
        sc = [c for x in rows for c in x['striker_clears']]
        by = defaultdict(list)
        for n10, dur, taken, gems in sc:
            by[min(n10, 3)].append((dur, taken, gems))
        for k in sorted(by):
            v = by[k]
            print(f'   n={k}: {len(v)} clears, mean dur {sum(a for a, _, _ in v) / len(v):.1f}, taken {sum(b for _, b, _ in v) / len(v):.0f}, gems {sum(c for _, _, c in v) / len(v):.1f}, taken/gem {sum(b for _, b, _ in v) / max(1, sum(c for _, _, c in v)):.1f}')


if __name__ == '__main__':
    main()
