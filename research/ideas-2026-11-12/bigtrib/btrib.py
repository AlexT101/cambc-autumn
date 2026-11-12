"""Fish's big tributes in live r8 games, and what our side does around them.
    py btrib.py [--min 100] [--json OUT]
For each Fish tribute start with a bag of at least --min gems: its outcome (scored, cancelled by stun / lock /
death), our nearest body to the altar and to the carrier over the channel, who of ours saw it, who held a lock or a
ready stun, whether the carrier died within the channel or 20 rounds after (and to whom), and our deaths near the
altar meanwhile."""
import json, gzip, os, sys, collections, statistics as st
from multiprocessing import Pool
EXT = os.path.expanduser('~/tmp-offload/fishr8/live/ext'); ROWS = os.path.expanduser('~/tmp-offload/fishr8/ours.json')
cheb = lambda a, b: max(abs(a[0] - b[0]), abs(a[1] - b[1]))
STUN = {'Ryth': 0, 'Prism': 0, 'Tavi': 1, 'Ren': 0, 'Cassi': 1}  # stun slot; Marcella's is a reset-attack (slot 0)
STUN_RANGE = {'Ryth': 4, 'Prism': 4, 'Tavi': 4, 'Ren': 4, 'Cassi': 4, 'Marcella': 1}
args = sys.argv[1:]
MIN = int(args[args.index('--min') + 1]) if '--min' in args else 100

def game(job):
    d, row = job
    try:
        meta = json.load(open(f'{EXT}/{d}/meta.json')); R = json.load(gzip.open(f'{EXT}/{d}/rounds.json.gz'))
        ev = [json.loads(l) for l in gzip.open(f'{EXT}/{d}/events.jsonl.gz', 'rt')]
    except Exception: return None
    ours = 0 if row['side'] == 'a' else 1; fish = 1 - ours
    champs = meta['champions'] if isinstance(meta['champions'], list) else None
    team = {c['id']: c['team'] for c in R['champions']}
    name = {c['id']: c['name'] for c in champs} if champs else {}
    rix = {r: i for i, r in enumerate(R['round'])}; C = {c['id']: c for c in R['champions']}
    won = meta['result']['winner'] == ours
    out = []
    starts = [e for e in ev if e['k'] == 'tribute_start' and team.get(e['a']) == fish]
    fish_total = sum(e['gems'] for e in ev if e['k'] == 'tribute_end' and team.get(e['a']) == fish)
    for s in starts:
        if s['gems'] < MIN: continue
        a = s['a']; r0 = s['r']; alt = tuple(s['altar'])
        # Outcome: the carrier's next end or cancel, or its death.
        res = None
        for e in ev:
            if e['r'] < r0 or (e['r'] == r0 and e['s'] <= s['s']): continue
            if e['k'] in ('tribute_end', 'tribute_cancel') and e.get('a') == a: res = e; break
            if e['k'] == 'death' and e['v'] == a: res = e; break
        r1 = res['r'] if res else r0 + s['dur']
        kind = 'end' if res and res['k'] == 'tribute_end' else ('death' if res and res['k'] == 'death' else (res.get('cause', '?') if res else 'none'))
        # Our bodies over the channel.
        near_alt = 99; near_car = 99; saw = set(); lockers = set(); lock_in2 = False; stunners = set(); ours_n = 0
        for r in range(r0, r1 + 1):
            i = rix.get(r)
            if i is None: continue
            cx, cy = C[a]['x'][i], C[a]['y'][i]
            for c in R['champions']:
                if c['team'] != ours or not c['alive'][i] or c['x'][i] is None: continue
                p = (c['x'][i], c['y'][i]); da = cheb(p, alt)
                near_alt = min(near_alt, da)
                if cx is not None: near_car = min(near_car, cheb(p, (cx, cy)))
                if a in (c['sees'][i] or []): saw.add(c['id'])
                if c['cons'][i][2] > 0 and da <= 8: lockers.add(c['id'])
                if c['cons'][i][2] > 0 and da <= 2: lock_in2 = True
                nm = name.get(c['id'], '')
                if nm in STUN and cx is not None and (c['cd1'] if STUN[nm] else c['cd0'])[i] == 0 and cheb(p, (cx, cy)) <= 8: stunners.add(c['id'])
        # Carrier death soon after.
        died = None
        for e in ev:
            if e['k'] == 'death' and e['v'] == a and r0 <= e['r'] <= r1 + 20: died = e; break
        our_deaths = [e for e in ev if e['k'] == 'death' and team.get(e['v']) == ours and r0 - 2 <= e['r'] <= r1 + 10 and cheb(e['at'], alt) <= 10]
        our_locks = [e for e in ev if e['k'] == 'lock_place' and team.get(e.get('a')) == ours and r0 <= e['r'] <= r1 and tuple(e['to']) == alt]
        i0 = rix.get(r0, 0)
        out.append(dict(game=d, won=won, r=r0, gems=s['gems'], dur=s['dur'], carrier=name.get(a, '?'), kind=kind, scored=res.get('gems') if kind == 'end' else 0,
                        near_alt=near_alt, near_car=near_car, saw=len(saw), lockers=len(lockers), lock_in2=lock_in2, stunners=len(stunners),
                        died=bool(died), died_by_us=bool(died and team.get(died.get('by')) == ours), died_r=died['r'] if died else None,
                        our_deaths=len(our_deaths), our_gems_lost=sum(e.get('gems', 0) for e in our_deaths), our_locks=len(our_locks),
                        fish_score=R['gems'][fish][i0], our_score=R['gems'][ours][i0], fish_total=fish_total, rounds=meta['result']['rounds'],
                        carrier_hp=C[a]['hp'][i0], carrier_max=C[a]['maxHp'][i0]))
    return dict(game=d, won=won, n_big=len(out), fish_total=fish_total, rows=out)

def main():
    rows = json.load(open(ROWS)); idx = json.load(open(f'{EXT}/index.json'))['games']
    jobs = []
    for g in idx:
        mid = os.path.basename(g['source'])[:-8]
        if mid in rows and rows[mid].get('refset') == 'r8': jobs.append((g['dir'], rows[mid]))
    with Pool(16) as p: G = [g for g in p.map(game, jobs) if g]
    T = [t for g in G for t in g['rows']]
    if '--json' in args: json.dump(G, open(args[args.index('--json') + 1], 'w'))
    N = len(G); print(f'{N} r8 games, {len(T)} Fish tribute starts of {MIN}+ ({len(T)/N:.2f} a game)')
    print('outcome:', collections.Counter(t['kind'] for t in T))
    print('win% games with 0 / 1-2 / 3+ big starts:', [(k, f"{100*st.mean(g['won'] for g in G if f(g['n_big'])):.1f}% of {sum(1 for g in G if f(g['n_big']))}") for k, f in (('0', lambda n: n == 0), ('1-2', lambda n: 1 <= n <= 2), ('3+', lambda n: n >= 3))])
    sc = [t for t in T if t['kind'] == 'end']
    print(f"scored: mean bag {st.mean(t['scored'] for t in sc):.0f}; share of Fish's tributed gems from {MIN}+ starts: {sum(t['scored'] for t in sc)/sum(g['fish_total'] for g in G):.2f}")
    print('dur median', st.median(t['dur'] for t in T), 'gems median', st.median(t['gems'] for t in T), 'carrier', collections.Counter(t['carrier'] for t in T).most_common())
    for lab, f in (('ours within 2 of altar', lambda t: t['near_alt'] <= 2), ('within 4', lambda t: t['near_alt'] <= 4), ('within 8', lambda t: t['near_alt'] <= 8),
                   ('a lock-holder within 8 of altar', lambda t: t['lockers'] > 0), ('lock-holder within 2', lambda t: t['lock_in2']), ('we placed a lock', lambda t: t['our_locks'] > 0),
                   ('a ready stunner within 8 of carrier', lambda t: t['stunners'] > 0), ('one of ours saw carrier', lambda t: t['saw'] > 0),
                   ('carrier died <= end+20', lambda t: t['died']), ('... by us', lambda t: t['died_by_us']), ('our death within 10 of altar', lambda t: t['our_deaths'] > 0)):
        s = [t for t in T if f(t)]
        print(f'  {lab:38s} {len(s)/len(T):.2f}  ({len(s)}); outcome {dict(collections.Counter(t["kind"] for t in s))}; game win {100*st.mean(t["won"] for t in s) if s else 0:.0f}%')
    print('fish score at start median', st.median(t['fish_score'] for t in T), 'ours', st.median(t['our_score'] for t in T))
    print('by round:', {b: sum(1 for t in T if b <= t['r'] < b + 200) for b in range(0, 2000, 200)})
    wins = [t for t in T if t['fish_score'] + t['gems'] >= 1000]; print('starts that would win the game:', len(wins), collections.Counter(t['kind'] for t in wins))
    nw = [t for t in T if t['fish_score'] + t['gems'] < 1000]
    print(f'NON-WINNING starts: {len(nw)} ({len(nw)/N:.2f} a game)', collections.Counter(t['kind'] for t in nw))
    for lab, f in (('ours within 2 of altar', lambda t: t['near_alt'] <= 2), ('within 4', lambda t: t['near_alt'] <= 4), ('within 8', lambda t: t['near_alt'] <= 8),
                   ('a lock-holder within 8 of altar', lambda t: t['lockers'] > 0), ('lock-holder within 2', lambda t: t['lock_in2']), ('we placed a lock', lambda t: t['our_locks'] > 0),
                   ('a ready stunner within 8 of carrier', lambda t: t['stunners'] > 0), ('one of ours saw carrier', lambda t: t['saw'] > 0),
                   ('carrier died <= end+20', lambda t: t['died']), ('our death within 10 of altar', lambda t: t['our_deaths'] > 0)):
        s = [t for t in nw if f(t)]
        print(f'  {lab:38s} {len(s)/len(nw):.2f}  ({len(s)}); outcome {dict(collections.Counter(t["kind"] for t in s))}; game win {100*st.mean(t["won"] for t in s) if s else 0:.0f}%')
    print('  non-winning by round:', {b: sum(1 for t in nw if b <= t['r'] < b + 200) for b in range(0, 2000, 200)})
    print('  non-winning dur median', st.median(t['dur'] for t in nw), 'gems median', st.median(t['gems'] for t in nw), 'scored mean', st.mean(t['scored'] for t in nw if t['kind']=='end'))

if __name__ == '__main__': main()
