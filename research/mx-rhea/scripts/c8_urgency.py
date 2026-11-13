"""E-branch (stop_game_ender) episodes on a debug batch's extracted games: at each E turn, the ender's tribute channel
(turns left, how long it had run), how that channel ended (stun / lock by whom, the owner's manual cancel, completion,
the owner's death) and whether the E champion died within 10 rounds. Usage: py c8_urgency.py ANALYSIS_DIR BATCH"""
import gzip, json, sys, zipfile
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

ROOT = Path('/home/ubuntu/wt/mx-rhea')


def bucket(x, edges=(1, 2, 3, 5, 10, 20, 40)):
    for e in edges:
        if x <= e: return f'<={e}'
    return f'>{edges[-1]}'


def game(args):
    d, src = args
    try:
        meta = json.loads((d/'meta.json').read_text())
        R = json.load(gzip.open(d/'rounds.json.gz'))
        ev = [json.loads(l) for l in gzip.open(d/'events.jsonl.gz', 'rt')]
        z = zipfile.ZipFile(src)
    except Exception:
        return None
    # The source's sides: index.json's source is the replay this dir came from.
    names = {c['id']: c['name'] for c in meta['champions']}
    team = {c['id']: c['team'] for c in meta['champions']}
    ch = {c['id']: c for c in R['champions']}
    ri = {r: i for i, r in enumerate(R['round'])}
    E = defaultdict(set)  # cid -> rounds on E
    for side in 'ab':
        try: lines = z.read(f'team-{side}.stdout').decode(errors='replace').splitlines()
        except KeyError: continue
        for l in lines:
            l = l.lstrip('\x00')
            if l.startswith('D '):
                p = l.split()
                if len(p) >= 4 and p[3] == 'E': E[int(p[2])].add(int(p[1]))
    # Tribute channels: start event, end event.
    chans = []
    open_ = {}
    first_s = {}  # (cid, round) -> first event s by that champion
    by_s = defaultdict(list)
    for e in ev:
        a = e.get('a')
        if a is not None and (a, e['r']) not in first_s and e['k'] not in ('recall_cancel', 'tribute_cancel', 'tribute_end', 'recall_end'):
            first_s[(a, e['r'])] = e['s']
        by_s[e['s']].append(e)
        if e['k'] == 'tribute_start':
            c = dict(a=a, s=e['s'], r=e['r'], dur=e['dur'], gems=e['gems'], end=None)
            chans.append(c); open_[a] = c
        elif e['k'] in ('tribute_cancel', 'tribute_end') and a in open_:
            c = open_.pop(a)
            c['end'] = e['k'] if e['k'] == 'tribute_end' else e['cause']
            c['end_r'] = e['r']; c['end_s'] = e['s']
            if e['k'] == 'tribute_cancel' and e['cause'] in ('stun', 'lock'):
                actor = [x.get('a') for x in by_s[e['s']] if x['k'] in ('cast', 'attack', 'lock_place') and x.get('a') is not None]
                c['by'] = actor[0] if actor else None
        elif e['k'] == 'death' and e['v'] in open_:
            c = open_.pop(e['v']); c['end'] = 'death'; c['end_r'] = e['r']; c['end_s'] = e['s']; c['by'] = e.get('by')
    deaths = defaultdict(list)
    for e in ev:
        if e['k'] == 'death': deaths[e['v']].append(e)
    winner = meta['result']['winner']
    rows = []
    for cid, rounds in E.items():
        T = team[cid]
        rs = sorted(rounds)
        for r0 in rs:
            ep_start = (r0 - 1) not in rounds and (r0 - 2) not in rounds
            s_turn = first_s.get((cid, r0))
            i_prev = ri.get(r0 - 1)
            if i_prev is None: continue
            need = 1000 - R['gems'][1 - T][i_prev]
            # Enemy channels live at our turn (or at the end of r0-1 when we left no event).
            live = []
            for c in chans:
                if team[c['a']] == T: continue
                st = c['s']; en = c.get('end_s', 10**12)
                at = s_turn if s_turn is not None else first_s.get((cid, r0), None)
                if at is None:
                    if c['r'] <= r0 and (c.get('end_r', 10**9) >= r0): live.append(c)
                elif st < at < en or (st < at and en == at):
                    live.append(c)
            if not live: rows.append(dict(cid=cid, r=r0, start=ep_start, ender=None)); continue
            win = [c for c in live if c['gems'] >= need] or (live if sum(c['gems'] for c in live) >= need else [])
            if not win: rows.append(dict(cid=cid, r=r0, start=ep_start, ender='nowin')); continue
            me = ch[cid]
            def dd(c):
                o = ch[c['a']]
                return max(abs(o['x'][i_prev] - me['x'][i_prev]), abs(o['y'][i_prev] - me['y'][i_prev])) if me['x'][i_prev] is not None and o['x'][i_prev] is not None else 99
            c = min(win, key=dd)
            left = c['r'] + c['dur'] - r0
            ran = r0 - c['r']
            how = c['end'] or 'open'
            if how in ('stun', 'lock', 'death'):
                b = c.get('by')
                how += '-self' if b == cid else ('-ally' if b is not None and team.get(b) == T else '-other')
            died = [x for x in deaths[cid] if r0 <= x['r'] <= r0 + 10]
            rows.append(dict(cid=cid, name=names[cid], r=r0, start=ep_start, ender=names[c['a']], left=left, ran=ran,
                             dur=c['dur'], how=how, how_r=c.get('end_r'), dist=dd(c),
                             died=bool(died), died_by=(names.get(died[0].get('by'), 'camp') if died else None),
                             died_gems=(died[0].get('gems', 0) if died else 0), won=winner == T,
                             gems=me['gems'][i_prev] or 0))
    return rows


def main():
    ana, batch = Path(sys.argv[1]), sys.argv[2]
    idx = json.load(open(ana/'index.json'))['games']
    jobs, seen = [], set()
    for g in idx:
        if g['dir'] in seen or batch not in g['source']: continue
        seen.add(g['dir']); jobs.append((ana/g['dir'], ROOT/g['source']))
    rows = []
    with ProcessPoolExecutor(32) as ex:
        for o in ex.map(game, jobs, chunksize=4):
            if o: rows += o
    print(len(jobs), 'games;', len(rows), 'E turns;', sum(r['start'] for r in rows), 'episode starts')
    print('ender at our turn:', Counter('none' if r['ender'] is None else ('nowin' if r['ender'] == 'nowin' else 'winning') for r in rows))
    W = [r for r in rows if isinstance(r.get('left'), int)]
    for label, sel in (('all E turns', W), ('episode starts', [r for r in W if r['start']])):
        print(f'\n== {label}: {len(sel)}')
        print('channel ran (rounds since start) :', sorted(Counter(bucket(r['ran'], (0, 1, 2, 5, 10, 30))
                                                                  for r in sel).items()))
        print('left at our turn:', sorted(Counter(bucket(r['left']) for r in sel).items(), key=lambda x: x[0]))
        print('how the channel ended:', Counter(r['how'] for r in sel).most_common())
        print('our champion died within 10:', sum(r['died'] for r in sel), f"({sum(r['died'] for r in sel)/max(1,len(sel)):.1%})")
        print(' by left bucket: n / how / died')
        by = defaultdict(list)
        for r in sel: by[bucket(r['left'])].append(r)
        for k in sorted(by, key=lambda k: (k[0] == '>', int(k.lstrip('<=>')))):
            v = by[k]
            hw = Counter(r['how'].split('-')[0] + ('-us' if r['how'].endswith('-self') else '') for r in v)
            print(f'  {k:>5} {len(v):6}  died {sum(r["died"] for r in v)/len(v):5.1%}  win {sum(r["won"] for r in v)/len(v):5.1%}  ', dict(hw.most_common()))
    # Deaths on E: the ender's clock at the episode's last E turn before the death.
    ds = [r for r in W if r['died']]
    print('\nE turns with a death within 10, ender channel ran 0-1 rounds (fresh / one-turn):',
          sum(1 for r in ds if r['ran'] <= 1), 'of', len(ds))
    one = [r for r in W if r['start'] and r['how'] == 'manual' and r['how_r'] is not None and r['how_r'] - (r['r'] - r['ran']) <= 1]
    print('episode starts whose ender channel was a one-turn channel cancelled by its owner:', len(one))
    import pickle
    pickle.dump(rows, open('/tmp/c8_rows.pkl', 'wb'))


if __name__ == '__main__':
    main()
