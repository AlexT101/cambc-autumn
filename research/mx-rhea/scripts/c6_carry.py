"""Carrier deaths (killed by a champion with 50+ gems, Cassi and Issac's bags together): the victim's D branches over
its last 10 rounds, when the killer was first seen (start of the unbroken stretch of sight ending at the first hit) and
at what distance, the recalls it kept (a recall not cancelled at its first chance) and how they ended, and the branch
when the killer was first seen. Usage: py c6_carry.py ANALYSIS_DIR [--team NAME] [--list N]"""
import gzip, json, sys, zipfile
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

ROOT = Path('/home/ubuntu/wt/mx-rhea')


def cheb(a, b): return max(abs(a[0] - b[0]), abs(a[1] - b[1]))


def game(args):
    d, team_name = args
    try:
        meta = json.loads((d / 'meta.json').read_text())
        R = json.load(gzip.open(d / 'rounds.json.gz'))
        ev = [json.loads(l) for l in gzip.open(d / 'events.jsonl.gz', 'rt')]
    except Exception:
        return []
    src = None
    for s in meta['sources']:
        if (ROOT / s['source']).exists(): src = ROOT / s['source']; teams = [t['name'] for t in s['teams']]; break
    if src is None: return []
    z = zipfile.ZipFile(src)
    D = {}; extra = defaultdict(list)
    for side, t in (('a', 0), ('b', 1)):
        try: lines = z.read(f'team-{side}.stdout').decode(errors='replace').splitlines()
        except KeyError: continue
        for l in lines:
            p = l.lstrip('\x00').split()
            if not p: continue
            if p[0] == 'D' and len(p) >= 4: D[(int(p[1]), int(p[2]))] = p[3]
            elif p[0] in ('CARRY', 'CARRYR') and len(p) >= 3: extra[(int(p[1]), int(p[2]))].append(' '.join(p))
    names = {c['id']: c['name'] for c in meta['champions']}
    ch = R['champions']; idx = {c['id']: i for i, c in enumerate(ch)}
    rix = {r: i for i, r in enumerate(R['round'])}
    winner = meta['result']['winner']
    hits = defaultdict(list)  # victim -> [(round, attacker, dmg, stun)]
    recalls = defaultdict(list)  # id -> [(round, kind, cause, left)]
    for e in ev:
        if e['k'] in ('attack', 'cast') and 'dmg' in e:
            for v, a in e['dmg']: hits[v].append((e['r'], e['a'], a, bool(e.get('stun'))))
        if e['k'] in ('attack', 'cast') and e.get('stun') and 'tgt' in e and 'dmg' not in e:
            hits[e['tgt']].append((e['r'], e['a'], 0, True))
        if e['k'] in ('recall_start', 'recall_cancel', 'recall_end'):
            recalls[e['a']].append((e['r'], e['k'], e.get('cause'), e.get('left')))
    out = []
    for e in ev:
        if e['k'] != 'death' or 'by' not in e or e['v'] not in idx: continue
        v = e['v']; cv = ch[idx[v]]; team = cv['team']
        if team_name and teams[team] != team_name: continue
        r = e['r']; i = rix.get(r)
        if i is None: continue
        bag = e.get('gemsTo', e.get('gems', 0))
        if bag < 50: continue
        killer = e['by']; ck = ch[idx[killer]] if killer in idx else None
        # first hit: walk back from the death through enemy-champion damage with gaps of at most 3 rounds
        hh = sorted([h for h in hits[v] if h[0] <= r and h[1] in idx and ch[idx[h[1]]]['team'] != team], key=lambda h: h[0])
        first = r
        for h in reversed(hh):
            if first - h[0] <= 3: first = min(first, h[0])
            else: break
        # killer first seen: unbroken stretch of the victim seeing the killer ending at the first hit
        seen_from = None
        j = rix.get(first)
        if j is not None:
            if killer not in cv['sees'][j] and j > 0 and killer in cv['sees'][j - 1]: j -= 1
            k = j
            while k >= 0 and killer in cv['sees'][k] and cv['alive'][k]: k -= 1
            seen_from = R['round'][k + 1] if k + 1 <= j and killer in cv['sees'][j] else None
        warn = first - seen_from if seen_from is not None else -1
        dist0 = cheb((cv['x'][rix[seen_from]], cv['y'][rix[seen_from]]), (ck['x'][rix[seen_from]], ck['y'][rix[seen_from]])) if seen_from and ck else -1
        # kept recalls in [seen_from or first-10, death]
        lo = (seen_from if seen_from else first) - 1
        # a recall kept: continue_recall kept it (K) at the turn after its start; its end
        kept = []
        st = None
        for (rr, kind, cause, left) in recalls[v]:
            if rr < lo - 6 or rr > r: continue
            if kind == 'recall_start': st = rr; continue
            if st is None: continue
            if D.get((st + 1, v)) == 'K' or kind == 'recall_end':
                kept.append((st, rr, 'landed' if kind == 'recall_end' else cause))
            st = None
        kept = [k for k in kept if k[1] >= lo]
        # D branches over the last 10 rounds
        br = ''.join(D.get((rr, v), '.') for rr in range(r - 10, r + 1))
        brs = D.get((seen_from, v), '?') if seen_from else '?'
        # the enemies within 4 in the window [seen_from, first) (a recall then may have drawn the attack)
        near = 99
        if seen_from:
            for rr in range(seen_from, first):
                k = rix[rr]
                for c in ch:
                    if c['team'] != team and c['alive'][k]: near = min(near, cheb((cv['x'][k], cv['y'][k]), (c['x'][k], c['y'][k])))
        hp0 = cv['hp'][rix[seen_from]] / cv['maxHp'][rix[seen_from]] if seen_from else -1
        hp1 = cv['hp'][rix[first] - 1] / cv['maxHp'][rix[first] - 1] if rix.get(first, 0) > 0 else -1
        ex = [x for rr in range(lo, r + 1) for x in extra.get((rr, v), [])]
        # CARRY lines (turn ends): round -> (decision, why, reach, recall turns, near)
        cl = {}
        for rr in range(r - 30, r + 1):
            for x in extra.get((rr, v), []):
                q = x.split()
                if q[0] == 'CARRY': cl[rr] = (q[5], q[6], int(q[8]), int(q[10]), int(q[12]))
        other = 1 - team
        k1 = rix.get(r - 1, i)
        mine_win = any(c['team'] == team and c['alive'][k1] and R['gems'][team][k1] + c['gems'][k1] >= 1000 for c in ch)
        their_win = any(c['team'] == other and c['alive'][k1] and R['gems'][other][k1] + c['gems'][k1] >= 1000 for c in ch)
        out.append(dict(mine_win=mine_win, their_win=their_win, game=d.name, r=r, v=v, name=names[v], team=teams[team], won=winner == team, bag=bag,
                        killer=names.get(killer), first=first, seen=seen_from, warn=warn, dist=dist0, near=near,
                        kept=kept, cl=cl, br=br, brs=brs, hp0=hp0, hp1=hp1, extra=ex))
    return out


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    team = sys.argv[sys.argv.index('--team') + 1] if '--team' in sys.argv else None
    if team: args.remove(team)
    nlist = int(sys.argv[sys.argv.index('--list') + 1]) if '--list' in sys.argv else 0
    if nlist: args.remove(str(nlist))
    if '--pickle' in sys.argv: args.remove(sys.argv[sys.argv.index('--pickle') + 1])
    root = Path(args[0])
    dirs = sorted(p for p in root.iterdir() if (p / 'meta.json').exists())
    rows = []
    with ProcessPoolExecutor(32) as ex:
        for o in ex.map(game, [(d, team) for d in dirs], chunksize=4): rows += o
    games = len(dirs)
    if '--pickle' in sys.argv:
        import pickle; pickle.dump(rows, open(sys.argv[sys.argv.index('--pickle') + 1], 'wb'))
    sides = 1 if team else 2
    print(f'{games} games, {sides} side(s)')
    for lo, hi, lab in ((200, 10 ** 9, '200+'), (50, 200, '50-199')):
        S = [x for x in rows if lo <= x['bag'] < hi]
        print(f'\n## bag {lab}: {len(S)} deaths, {len(S) / games / sides:.3f} per game-side; in losses {sum(not x["won"] for x in S)}')
        print('victim', Counter(x['name'] for x in S).most_common())
        print('killer', Counter(x['killer'] for x in S).most_common(6))
        W = Counter('unseen' if x['warn'] < 0 else '0-2' if x['warn'] <= 2 else '3-5' if x['warn'] <= 5 else '6-10' if x['warn'] <= 10 else '11+' for x in S)
        print('killer seen before first hit', sorted(W.items()))
        Ds = Counter('-' if x['dist'] < 0 else '<=4' if x['dist'] <= 4 else '5-6' if x['dist'] <= 6 else '7-8' for x in S)
        print('distance when first seen', sorted(Ds.items()))
        print('branch when killer first seen', Counter(x['brs'] for x in S).most_common())
        last = Counter()
        for x in S:
            for c in set(x['br'][:-1]): last[c] += 1
        print('branches present in last 10 rounds (deaths with)', last.most_common())
        dom = Counter(Counter(x['br'][:-1].replace('.', '')).most_common(1)[0][0] if x['br'][:-1].replace('.', '') else '.' for x in S)
        print('dominant branch last 10', dom.most_common())
        print('winning bags (ours, theirs) the round before', Counter((x['mine_win'], x['their_win']) for x in S).most_common())
        print('E in last 10 rounds', sum('E' in x['br'] for x in S), ' T', sum('T' in x['br'] for x in S),
              ' R and no E/T', sum('R' in x['br'] and 'E' not in x['br'] and 'T' not in x['br'] for x in S))
        K = Counter()
        for x in S:
            if not x['kept']: K['no recall kept'] += 1
            else:
                for k in x['kept']: K[k[2].split('@')[0]] += 1
        print('recalls kept in window, by end', K.most_common())
        safe = [x for x in S if x['warn'] >= 6]
        print(f'safe window (seen 6+ before first hit): {len(safe)}; of them no enemy within 4: {sum(x["near"] > 4 for x in safe)};'
              f' kept a recall: {sum(bool(x["kept"]) for x in safe)}; branch when seen {Counter(x["brs"] for x in safe).most_common()}')
        H = Counter('hp<.32' if x['hp0'] < 0.32 else 'hp<.5' if x['hp0'] < 0.5 else 'hp<.8' if x['hp0'] < 0.8 else 'hp.8+' for x in safe)
        print('  hp share when seen (safe window):', sorted(H.items()))
        C = [x for x in S if x['cl']]
        if C:
            print(f'CARRY traced deaths: {len(C)}')
            op = Counter(); dec = Counter(); hw = Counter(); gap = Counter()
            for x in C:
                before = sorted(rr for rr in x['cl'] if rr < x['first'])
                opn = [rr for rr in before if x['cl'][rr][2] > x['cl'][rr][3]]
                if not opn: op['never open in last 30'] += 1; continue
                last = opn[-1]; op['open'] += 1
                g = x['first'] - last
                gap['1' if g <= 1 else '2-3' if g <= 3 else '4-6' if g <= 6 else '7-15' if g <= 15 else '16+'] += 1
                dec[x['cl'][last][0]] += 1; hw[x['cl'][last][1]] += 1
            print('  recall window (reach > recall turns) at a turn end before the first hit:', dict(op))
            print('  rounds from its last open turn end to the first hit:', sorted(gap.items()))
            print('  branch at that turn:', dec.most_common(), ' want_home reason:', hw.most_common())
            R = Counter()
            for x in C:
                for rr, c in x['cl'].items():
                    if rr < x['first'] and c[0] == 'R': R['R with window open' if c[2] > c[3] else 'R window closed'] += 1
            print('  retreat turn ends before the first hit:', dict(R))
        if nlist:
            for x in sorted(S, key=lambda x: -x['bag'])[:nlist]:
                print(f"  {x['game']} r{x['r']} #{x['v']} {x['name']} bag {x['bag']} by {x['killer']} first {x['first']} seen {x['seen']} "
                      f"warn {x['warn']} d{x['dist']} near {x['near']} hp {x['hp0']:.2f}->{x['hp1']:.2f} br {x['br']} kept {x['kept']} won {x['won']}")
                for l in x['extra'][-14:]: print('     ', l)


if __name__ == '__main__':
    main()
