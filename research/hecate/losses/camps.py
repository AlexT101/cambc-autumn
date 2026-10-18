"""Camp episodes: a champion attacking one group (gaps up to 4 rounds). How each ended.

Ends: cleared (by our team within 3 rounds of the last hit), stolen (cleared by the enemy), died,
home (recall landed or reached spawn within 12 rounds, group not cleared), switched (attacked another
group next), left (none of these). Also the first capture round per side.
py research/hecate/losses/camps.py [--examples]
"""
import argparse
import collections
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from common import our_games  # noqa


def episodes(g, team):
    cg = {c['id']: c['group'] for c in g.map.raw['camps']}
    ids = set(g.team_ids[team])
    hits = collections.defaultdict(list)  # cid -> [(r, group, dmg)]
    clears = collections.defaultdict(list)  # group -> [(r, by team)]
    recall_end = collections.defaultdict(list)
    deaths = collections.defaultdict(list)
    for e in g.events:
        k = e['k']
        if k in ('attack', 'cast') and e['a'] in ids and e.get('cdmg'):
            for camp, d in e['cdmg']:
                hits[e['a']].append((e['r'], cg[camp], d))
        elif k == 'group_clear':
            clears[e['g']].append((e['r'], g.team_of.get(e.get('by'))))
        elif k == 'recall_end' and e['a'] in ids:
            recall_end[e['a']].append(e['r'])
        elif k == 'death' and e['v'] in ids:
            deaths[e['v']].append(e['r'])
    out = []
    for cid, hs in hits.items():
        hs.sort()
        cur = None
        for r, gid, d in hs + [(10 ** 9, -1, 0)]:
            if cur and (gid != cur['g'] or r - cur['last'] > 4):
                out.append(cur)
                cur = None
            if gid < 0:
                break
            if not cur:
                cur = dict(cid=cid, g=gid, first=r, last=r, dmg=0, next_g=None)
            cur['last'] = r
            cur['dmg'] += d
        # classify
        for i, ep in enumerate([x for x in out if x['cid'] == cid]):
            pass
    by_cid = collections.defaultdict(list)
    for ep in out:
        by_cid[ep['cid']].append(ep)
    res = []
    for cid, eps in by_cid.items():
        eps.sort(key=lambda x: x['first'])
        ch = g.ch(cid)
        sp = g.map.raw['spawn'][team]
        for j, ep in enumerate(eps):
            L = ep['last']
            cl = [c for c in clears[ep['g']] if ep['first'] <= c[0] <= L + 3]
            if cl:
                end = 'cleared' if cl[0][1] == team else 'stolen'
            elif any(L <= d <= L + 2 for d in deaths[cid]):
                end = 'died'
            else:
                home = any(L < x <= L + 12 for x in recall_end[cid])
                if not home:
                    for r in range(L + 1, min(L + 13, len(ch['x']))):
                        x, y = ch['x'][r - 1], ch['y'][r - 1]
                        if x is not None and sp['minX'] <= x <= sp['maxX'] and sp['minY'] <= y <= sp['maxY']:
                            home = True
                            break
                if home:
                    end = 'home'
                elif j + 1 < len(eps) and eps[j + 1]['first'] <= L + 6:
                    end = 'switched'
                else:
                    end = 'left'
            later = [c for c in clears[ep['g']] if c[0] > L + 3]
            ep['end'] = end
            ep['later_by'] = (later[0][1] == team, later[0][0]) if later else None
            ep['hp'] = ch['hp'][L - 1]
            ep['maxhp'] = ch['maxHp'][L - 1]
            res.append(ep)
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--examples', action='store_true')
    a = ap.parse_args()
    tot = {k: collections.Counter() for k in ('Lus', 'Lthem', 'Wus', 'Wthem')}
    dmg_wasted = collections.Counter()
    first_cap = collections.defaultdict(list)
    ex = []
    for g in our_games():
        res = 'W' if g.winner == g.us else 'L'
        for side, team in (('us', g.us), ('them', g.them)):
            for ep in episodes(g, team):
                if g.map.raw['groups'][ep['g']]['gems'] + g.map.raw['groups'][ep['g']]['gold'] == 0:
                    continue
                strong = any(m['type'] in ('Elk', 'Monolith') for m in [g.map.raw['camps'][c] for c in g.map.raw['groups'][ep['g']]['camps']])
                key = ep['end'] + ('' if strong else '(weak)')
                tot[res + side][key] += 1
                tot[res + side]['n'] += 1
                if ep['end'] in ('home', 'left', 'died'):
                    dmg_wasted[res + side] += ep['dmg']
                if side == 'us' and ep['end'] == 'home' and strong:
                    ex.append((g.dir, g.map_name, res, g.name_of[ep['cid']], ep['first'], ep['last'], g.map.group_label(ep['g']), round(ep['dmg']), round(ep['hp']), ep['later_by']))
            caps = [e['r'] for e in g.events if e['k'] == 'capture' and e['team'] == team and sum(s[1] for s in e['shares']) > 0]
            first_cap[res + side].append(caps[0] if caps else 2000)
    n = collections.Counter('W' if g.winner == g.us else 'L' for g in our_games())
    for k, c in tot.items():
        print(k, 'episodes/game', round(c['n'] / n[k[0]], 1), {x: round(v / n[k[0]], 2) for x, v in sorted(c.items()) if x != 'n'})
        print('   camp hp dealt on unfinished episodes/game', round(dmg_wasted[k] / n[k[0]]), ' median first gem capture', sorted(first_cap[k])[len(first_cap[k]) // 2])
    if a.examples:
        for x in ex[:80]:
            print(x)


if __name__ == '__main__':
    main()
