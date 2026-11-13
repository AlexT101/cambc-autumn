"""R-branch turns in farm-break windows: local numbers (allies incl. self vs enemies within 8), damage taken in the
5 rounds before / after, bag, and whether the enemy captured a group within 8 of the retreat tile in the next 20
rounds (the gems of those captures). Writes /tmp/mxi-study/retreats.json."""
import json, sys
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor
sys.path.insert(0, '/home/ubuntu/wt/mx-iapetus/tools/replay')
sys.path.insert(0, '/tmp/mxi-study')
from analysis.data import Game, chebyshev  # noqa
from analysis import macro  # noqa
from farmwin import read_trace  # noqa


def work(row):
    d, w0, w1 = row['dir'], row['w0'], row['w1']
    g = Game(d)
    R = g.rounds
    Wt = g.winner
    role = {Wt: 'W', 1 - Wt: 'L'}
    tr = read_trace(g.meta['source'])
    cls = macro.classify(g)
    champs = R['champions']
    gm = {grp['id']: grp for grp in g.map.groups}
    dmg = g.damaged_rounds
    caps = [(e['r'], e['team'], e['g'], sum(s[1] for s in e['shares'])) for e in g.events if e['k'] == 'capture']
    pos = lambda c, i: (c['x'][i], c['y'][i]) if c['alive'][i] and c['x'][i] is not None else None
    out = []
    for c in champs:
        cid, t = c['id'], c['team']
        prev_r = -10
        for r in range(w0, w1 + 1):
            b = tr.get((cid, r))
            if not b or b[0] != 'R' or cls[cid][r] == 'dead':
                continue
            i = max(0, r - 2)  # state at turn start
            p = pos(c, i)
            if not p: continue
            al = en = 0
            ehp = ahp = 0.0
            enames = []
            for cc in champs:
                q = pos(cc, i)
                if not q or chebyshev(p, q) > 8: continue
                if cc['team'] == t: al += 1; ahp += cc['hp'][i]
                else: en += 1; ehp += cc['hp'][i]; enames.append(g.name_of[cc['id']])
            before = any(rr in dmg[cid] for rr in range(r - 5, r))
            after = any(rr in dmg[cid] for rr in range(r, r + 6))
            # enemy captures near in the next 20 rounds
            ecap = [(rr, gg, gems) for rr, tt, gg, gems in caps if tt != t and r <= rr <= r + 20
                    and min(chebyshev(p, tuple(x)) for x in gm[gg]['tiles']) <= 8]
            episode_start = r - prev_r > 3
            prev_r = r
            out.append({'team': role[t], 'type': g.name_of[cid], 'r': r, 'al': al, 'en': en, 'ahp': ahp, 'ehp': ehp,
                        'hp': c['hp'][i] / max(1, c['maxHp'][i]), 'bag': c['gems'][i] or 0, 'before': before, 'after': after,
                        'ecap': ecap, 'start': episode_start, 'enames': enames, 'seen': len(c['sees'][r - 1]) if r - 1 < len(c['sees']) else 0,
                        'cls_prev': cls[cid][r - 1]})
    return {'dir': d, 'rows': out}


if __name__ == '__main__':
    rows = [json.loads(l) for l in open('/tmp/mxi-study/farmwin.jsonl')]
    with ProcessPoolExecutor(24) as ex:
        res = list(ex.map(work, rows, chunksize=2))
    json.dump(res, open('/tmp/mxi-study/retreats.json', 'w'))
    N = len(res)
    allr = [dict(x, dir=g['dir']) for g in res for x in g['rows']]
    for team in 'WL':
        S = [x for x in allr if x['team'] == team]
        print(f'\n## {team}: R turns/game {len(S)/N:.1f}; episodes (starts)/game {sum(x["start"] for x in S)/N:.2f}')
        c = Counter()
        for x in S:
            num = 'ahead' if x['al'] > x['en'] else 'even' if x['al'] == x['en'] else 'behind'
            if x['en'] == 0: num = 'no enemy within 8'
            dm = 'hit before' if x['before'] else 'no hit before'
            c[(num, dm, 'hit after' if x['after'] else 'no hit after')] += 1
        for k, v in sorted(c.items(), key=lambda kv: -kv[1]):
            print(f'   {k}: {v/N:.2f}/game')
        # give-way: no damage before or after, not behind
        G_ = [x for x in S if not x['before'] and not x['after'] and x['en'] > 0 and x['al'] >= x['en']]
        print(f'   give-way (no hit 5 before/after, not outnumbered within 8): {len(G_)/N:.2f} turns/game, {sum(x["start"] for x in G_)/N:.2f} episodes/game')
        print('     by type:', ', '.join(f'{k} {v/N:.2f}' for k, v in Counter(x['type'] for x in G_).most_common(8)))
        print('     enemy types present:', ', '.join(f'{k} {v/N:.2f}' for k, v in Counter(n for x in G_ for n in x['enames']).most_common(8)))
        print('     bag: 0', sum(x['bag'] == 0 for x in G_) / N, '1-49', sum(0 < x['bag'] < 50 for x in G_) / N, '50+', sum(x['bag'] >= 50 for x in G_) / N,
              ' hp<60%', sum(x['hp'] < 0.6 for x in G_) / N)
        st = [x for x in S if x['start']]
        eg = sum(sum(gm for _, _, gm in x['ecap']) for x in st)
        print(f'   retreat episodes followed by an enemy capture within 8 of the tile in 20 rounds: {sum(1 for x in st if x["ecap"])/N:.2f}/game, gems {eg/N:.1f}/game')
        stg = [x for x in st if not x['before'] and x['en'] > 0 and x['al'] >= x['en']]
        eg2 = sum(sum(gm for _, _, gm in x['ecap']) for x in stg)
        print(f'     of which give-way starts (no hit before, not outnumbered): {sum(1 for x in stg if x["ecap"])/N:.2f}/game, gems {eg2/N:.1f}/game')
        print('   prev class of retreat starts:', ', '.join(f'{k} {v/N:.2f}' for k, v in Counter(x['cls_prev'] for x in st).most_common(8)))
