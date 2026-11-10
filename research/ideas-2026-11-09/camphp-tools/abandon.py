#!/usr/bin/env python3
"""Part-damaged camp groups in extracted ladder replays: who leaves them damaged, and what happens next.

Per group life (round 1 or a respawn, to its clear or the game end): damage by team per round. A gap of
>= GAP rounds with no damage while members live is an abandonment; recorded with the hp left, who had
damaged it, and the outcome (who next damages it, who clears it, who captures).
Output: one JSON line per abandonment to stdout.
"""
import gzip, json, os, sys
from multiprocessing import Pool

GAP = int(os.environ.get('GAP', '10'))
NAMES = {}
for l in open(os.path.expanduser('~/tmp-offload/camphp/names.tsv')):
    mid, created, a, b, mp = l.rstrip('\n').split('\t')
    NAMES[mid] = (created, a, b, mp)
MAPS = {}


def load_map(d, rel):
    p = os.path.normpath(os.path.join(os.path.realpath(d), rel))
    if p not in MAPS:
        MAPS[p] = json.load(open(p))
    return MAPS[p]


def game(d):
    try:
        meta = json.load(open(os.path.join(d, 'meta.json')))
    except Exception:
        return []
    mid = os.path.basename(meta['source']).split('.')[0]
    if mid in NAMES:
        created, na, nb, mpname = NAMES[mid]
    elif meta.get('sourceKind') == 'batch':
        created, na, nb, mpname = '9999-local', meta['teams'][0]['name'], meta['teams'][1]['name'], meta['map']['name']
    else:
        return []
    mp = load_map(d, meta['mapFile'])
    camp_group = {c['id']: c['group'] for c in mp['camps']}
    camp_type = {c['id']: c['type'] for c in mp['camps']}
    gtypes = {g['id']: g['types'] for g in mp['groups']}
    ghp = {}
    for c in mp['camps']:
        ghp[c['group']] = ghp.get(c['group'], 0) + c['hp']
    greward = {g['id']: (g['gems'], g['gold']) for g in mp['groups']}
    team_of = {c['id']: c['team'] for c in meta['champions']}
    rounds_total = meta['result']['rounds']
    winner = meta['result']['winner']
    # per group: list of lives; life = dict(start, dmg=[(r, team, amt)], clear=(r, team)|None, cap=(r, team)|None)
    lives = {g: [dict(start=1, dmg=[], clear=None, cap=None, killers=set())] for g in ghp}
    deaths = []  # (r, champion id)
    recalls = []
    ev = [json.loads(l) for l in gzip.open(os.path.join(d, 'events.jsonl.gz'), 'rt')]
    RR = json.load(gzip.open(os.path.join(d, 'rounds.json.gz')))
    ridx = {r: i for i, r in enumerate(RR['round'])}
    chs = {c['id']: c for c in RR['champions']}
    camp_pos = {c['id']: (c['x'], c['y']) for c in mp['camps']}
    camp_hp = {c['id']: c['hp'] for c in mp['camps']}
    gcamps = {}
    for c in mp['camps']:
        gcamps.setdefault(c['group'], []).append(c['id'])
    for e in ev:
        k = e['k']
        if k in ('attack', 'cast') and e.get('cdmg'):
            t = team_of.get(e['a'])
            for cid, amt in e['cdmg']:
                g = camp_group.get(cid)
                if g is None or amt <= 0:
                    continue
                L = lives[g][-1]
                L['dmg'].append((e['r'], t, amt, e['a'], cid))
        elif k == 'camp_attack' and e.get('refl'):
            t = team_of.get(e['tgt'])
            for cid, amt in e['refl']:
                g = camp_group.get(cid)
                if g is not None and amt > 0:
                    lives[g][-1]['dmg'].append((e['r'], t, amt, e['tgt'], cid))
        elif k == 'group_clear':
            L = lives[e['g']][-1]
            L['clear'] = (e['r'], team_of.get(e.get('by')))
        elif k == 'capture':
            L = lives[e['g']][-1]
            L['cap'] = (e['r'], e['team'])
        elif k == 'group_respawn':
            lives[e['g']].append(dict(start=e['r'], dmg=[], clear=None, cap=None, killers=set()))
        elif k == 'death':
            deaths.append((e['r'], e['v']))
        elif k == 'recall_end':
            recalls.append((e['r'], e['a']))
    out = []
    for g, ls in lives.items():
        H = ghp[g]
        for L in ls:
            dm = L['dmg']
            if not dm:
                continue
            end = L['clear'][0] if L['clear'] else rounds_total
            cum = [0.0, 0.0]
            i = 0
            n = len(dm)
            tot = [sum(x[2] for x in dm if x[1] == 0), sum(x[2] for x in dm if x[1] == 1)]
            found = False
            while i < n:
                r, t, amt, a, _c = dm[i]
                if t in (0, 1):
                    cum[t] += amt
                nxt = dm[i + 1][0] if i + 1 < n else None
                gap_end = nxt if nxt is not None else end
                left = H - cum[0] - cum[1]
                if gap_end - r >= GAP and left > 1 and (nxt is not None or L['clear'] is None):
                    # who was damaging just before: last 5 rounds
                    recent = [0.0, 0.0]
                    hitters = set()
                    for (r2, t2, a2, c2, _c2) in dm[max(0, i - 200):i + 1]:
                        if r - r2 <= 5 and t2 in (0, 1):
                            recent[t2] += a2
                            hitters.add(c2)
                    lt = 0 if recent[0] >= recent[1] else 1
                    died = any(r - 3 <= dr <= r + 3 and v in hitters for dr, v in deaths)
                    recalled = any(r - 1 <= rr <= r + 8 and v in hitters for rr, v in recalls)
                    nt = dm[i + 1][1] if nxt is not None else None
                    cd = {}
                    for x in dm[:i + 1]:
                        cd[x[4]] = cd.get(x[4], 0) + x[2]
                    rem = [[camp_type[c], round(camp_hp[c] - cd.get(c, 0))] for c in gcamps[g] if camp_hp[c] - cd.get(c, 0) > 0.5]
                    j = ridx.get(r)
                    hhp = None; edist = None; hgems = None; hdist = None
                    if j is not None:
                        ps = [camp_pos[c] for c in gcamps[g]]
                        for cid_, c in chs.items():
                            if c['team'] == lt and cid_ in hitters and c['alive'][j]:
                                f = c['hp'][j] / max(1, c['maxHp'][j])
                                hhp = f if hhp is None else min(hhp, f)
                                hgems = max(hgems or 0, c['gems'][j])
                            if c['team'] == 1 - lt and c['alive'][j] and c['x'][j] is not None:
                                dd = min(max(abs(c['x'][j] - px), abs(c['y'][j] - py)) for px, py in ps)
                                edist = dd if edist is None else min(edist, dd)
                        if j + 3 < len(RR['round']):
                            for cid_, c in chs.items():
                                if cid_ in hitters and c['alive'][j + 3] and c['x'][j + 3] is not None:
                                    dd = min(max(abs(c['x'][j + 3] - px), abs(c['y'][j + 3] - py)) for px, py in ps)
                                    hdist = dd if hdist is None else min(hdist, dd)
                    out.append(dict(
                        mid=mid, created=created, map=mpname, names=[na, nb], winner=winner, g=g, types=gtypes[g],
                        reward=greward[g], H=H, left=left, frac=left / H, by=lt, cum=cum[:], r=r, resume=nxt,
                        next_team=nt, clear=L['clear'], cap=L['cap'], end=rounds_total, died=died, recalled=recalled,
                        life_start=L['start'], tot=tot, rem=rem, dps=recent[lt] / 5, hhp=hhp, edist=edist, hgems=hgems,
                        hdist3=hdist, nhit=len(hitters), hitters=sorted(hitters)))
                    found = True
                    break  # first abandonment per life only
                i += 1
            if not found:
                out.append(dict(mid=mid, created=created, map=mpname, names=[na, nb], winner=winner, g=g, types=gtypes[g],
                                reward=greward[g], H=H, clear=L['clear'], cap=L['cap'], end=rounds_total,
                                life_start=L['start'], tot=tot, r=None))
    return out


def main():
    dirs = []
    for root in sys.argv[1:]:
        for x in os.listdir(root):
            p = os.path.join(root, x)
            if os.path.isfile(os.path.join(p, 'meta.json')):
                dirs.append(p)
    seen = set()
    with Pool(int(os.environ.get('J', '6'))) as pool:
        for res in pool.imap_unordered(game, dirs, chunksize=8):
            for x in res:
                key = (x['mid'], x['g'], x['life_start'])
                if key in seen:
                    continue
                seen.add(key)
                print(json.dumps(x))


if __name__ == '__main__':
    main()
