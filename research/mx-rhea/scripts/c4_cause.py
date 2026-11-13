"""C4 cause split: recall-to-farm landings (RFCHOOSE ... RFLAND) whose farm group changes within 5 turns, by what
changed. Usage: py c4_cause.py ANALYSIS_DIR [MAX_ROUND]
Per switch, in order: X taken by an ally (an ally's D claim on X, or its capture / hold of X, during the trip; split
by whether the ally claimed X before our RFCHOOSE, during the channel, or on/after landing), X lost otherwise
(enemy hold or capture, enemy near X seen), the new group Y was excluded at the choice by the respawn wait
(true respawn left minus the walk from the recall tile above max_wait) and is now in reach, Y's respawn ended
during the trip, else none of these (price)."""
import gzip, json, sys, zipfile
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from tt_pursuit import fields, ROOT

MAX_WAIT = 2
MAXR = int(sys.argv[2]) if len(sys.argv) > 2 else 600


def game(args):
    d, src = args
    g = ROOT / 'replays/ana-mirror' / d
    try:
        meta = json.loads((g/'meta.json').read_text())
        ev = [json.loads(l) for l in gzip.open(g/'events.jsonl.gz', 'rt')]
        mp = json.loads((g/meta['mapFile']).resolve().read_text())
        R = json.load(gzip.open(g/'rounds.json.gz'))
        z = zipfile.ZipFile(ROOT / src)
    except Exception:
        return None
    winner = meta['result']['winner']
    team = {c['id']: c['team'] for c in meta['champions']}
    name = {c['id']: c['name'] for c in meta['champions']}
    D = {}; lands = []; choose = defaultdict(dict); picks = defaultdict(list)
    for side in 'ab':
        try: txt = z.read(f'team-{side}.stdout').decode(errors='replace')
        except KeyError: continue
        for l in txt.splitlines():
            p = l.replace('\x00', '').split()
            if not p: continue
            if p[0] == 'D' and len(p) >= 6: D[(int(p[1]), int(p[2]))] = (p[3], int(p[4]), int(p[5]))
            elif p[0] == 'RFLAND' and len(p) >= 4: lands.append((int(p[1]), int(p[2]), int(p[3])))
            elif p[0] == 'RFCHOOSE' and len(p) >= 5: choose[int(p[2])][int(p[1])] = int(p[3])
            elif p[0] == 'CREW' and len(p) >= 6 and p[1] == 'PICK': (picks[int(p[3])].append((int(p[2]), p[5])) if p[2].isdigit() and p[3].isdigit() else None)
    F = fields(mp)
    gtiles = {x['id']: x['tiles'] for x in mp['groups']}
    gc = {x['id']: x['tiles'][0] for x in mp['groups']}
    camp_g = {c_['id']: c_['group'] for c_ in mp['camps']}
    byr = defaultdict(list)
    for e in ev: byr[e['r']].append(e)
    def evr(a_, b_):
        for r_ in range(a_, b_ + 1): yield from byr.get(r_, ())
    rend = {}
    for e in ev:
        if e['k'] == 'recall_end': rend[(e['a'], e['r'])] = (tuple(e['f']), tuple(e['to']))
    caps = defaultdict(list)  # group -> [(round, team)]
    for e in ev:
        if e['k'] == 'capture' and e.get('shares'):
            caps[e['g']].append((e['r'], team[e['shares'][0][0]]))
    rows = defaultdict(dict)
    for row in R['groups']: rows[row[1]][row[0]] = row
    def gstate(gid, r):
        best = None
        for rr in sorted(rows.get(gid, {})):
            if rr <= r: best = rows[gid][rr]
            else: break
        return best
    ri = {r: i for i, r in enumerate(R['round'])}
    C = {c['id']: c for c in R['champions']}
    out = []
    for rl, cid, gl in lands:
        if rl > MAXR: continue
        my_team = team[cid]
        allies = [a for a in team if team[a] == my_team and a != cid]
        r0 = next((r for r in range(rl - 7, rl) if r in choose[cid]), None)
        if r0 is None: continue
        fe = rend.get((cid, rl)) or rend.get((cid, rl - 1))
        if not fe: continue
        f, to = fe
        later = [(rr, D.get((rr, cid), ('?', -9, -9))[1]) for rr in range(rl, rl + 6)]
        sw = next(((rr, x) for rr, x in later if x >= 0 and x != gl), None)
        won = my_team == winner
        mode = next((m for rr, m in reversed(picks[cid]) if rr <= r0), '?')
        nxt = next((e for e in ev if e['k'] == 'capture' and e['g'] == gl and e['r'] >= r0 and e.get('shares')), None)
        got = 'none' if nxt is None or nxt['r'] > rl + 40 else ('me' if any(s_[0] == cid for s_ in nxt['shares']) else ('ally' if team[nxt['shares'][0][0]] == my_team else 'enemy'))
        gstr = sum(1 for c_ in mp['camps'] if c_['group'] == gl and c_.get('type') not in ('gem_cluster', 'gold_cluster', 'Gem cluster', 'Gold cluster'))
        cap_r = nxt['r'] if nxt else rl + 40
        hit_x = any(e['k'] in ('attack', 'cast') and e.get('a') == cid and camp_g.get(e.get('camp')) == gl for e in evr(rl, cap_r))
        claimed0 = any(D.get((rr, al), ('', -9, -9))[2] == gl for al in allies for rr in (r0 - 1, r0))
        if sw is None:
            out.append(dict(won=won, champ=name[cid], kind='kept', mode=mode, got=got, claimed0=claimed0, strong=gstr > 0, hit_x=hit_x)); continue
        rs, new = sw
        if new not in F or gl not in F: continue
        a = F[new][f[0]][f[1]]; b = F[new][to[0]][to[1]]
        lost = 4 + b - a if a >= 0 and b >= 0 else None
        i0 = ri.get(r0)
        if lost is not None and i0 is not None and C[cid]['hp'][i0] < 0.6 * C[cid]['maxHp'][i0]: lost = min(lost, 0)
        # What the allies claiming X at our choice were doing (D branch), and who captured X next.
        ally_br = [D[(r0, al)][0] for al in allies if (r0, al) in D and D[(r0, al)][2] == gl] + \
                  [D[(r0 - 1, al)][0] for al in allies if (r0 - 1, al) in D and D[(r0 - 1, al)][2] == gl and not ((r0, al) in D and D[(r0, al)][2] == gl)]
        # Allies' claims on X: when did each start claiming it (latest run up to rs)?
        claim_when = None
        for al in allies:
            for rr in range(r0 - 3, rs + 1):
                k = D.get((rr, al))
                if k and k[2] == gl:
                    w = 'before' if rr <= r0 else ('channel' if rr < rl else 'landing')
                    if claim_when is None or ['before', 'channel', 'landing'].index(w) < ['before', 'channel', 'landing'].index(claim_when):
                        claim_when = w
                    break
        ally_recall = any(gl == choose[al].get(rr) for al in allies for rr in range(r0 - 5, rs + 1))
        st0, st = gstate(gl, r0), gstate(gl, rs)
        cap_trip = [t for r, t in caps[gl] if r0 <= r <= rs]
        x_ally = bool(cap_trip and cap_trip[0] == my_team) or (st and st[2] == 2 and st[3] == my_team)
        x_enemy = bool(cap_trip and cap_trip[0] != my_team) or (st and st[2] == 2 and st[3] == 1 - my_team)
        # An enemy seen by our team within 8 of X at rs.
        ii = ri.get(rs)
        enemy_near = False
        if ii is not None:
            seen = set()
            for al in [cid] + allies:
                s = C[al]['sees'][ii]
                if s: seen |= set(s)
            cx, cy = gc[gl]
            for e in seen:
                if team.get(e) == 1 - my_team and C[e]['alive'][ii] and max(abs(C[e]['x'][ii] - cx), abs(C[e]['y'][ii] - cy)) <= 8:
                    enemy_near = True
        # Back on X within the next turns: a flicker, not a retarget.
        after = [D.get((rr, cid), ('?', -9, -9))[1] for rr in range(rs + 1, rs + 4)]
        flicker = gl in after
        stl = gstate(gl, rl)
        bx = F[gl][to[0]][to[1]]
        x_wait_land = bool(stl and stl[2] == 3 and bx >= 0 and stl[5] - bx > MAX_WAIT)
        sp = mp['spawn'][my_team]
        cx_, cy_ = (sp['minX'] + sp['maxX']) // 2, (sp['minY'] + sp['maxY']) // 2
        cxw = F[gl][cx_][cy_]
        hp_full = i0 is not None and C[cid]['hp'][i0] >= C[cid]['maxHp'][i0]
        x_wait_sub = None
        if x_wait_land:
            x_wait_sub = 'landing-tile' if stl[5] - cxw <= MAX_WAIT else ('hurt' if not hp_full and stl[5] - cxw <= MAX_WAIT + 1 else 'other')
        y0 = gstate(new, r0)
        y_wait_excluded = bool(y0 and y0[2] == 3 and a >= 0 and y0[5] - a > MAX_WAIT)
        y_resp_end = bool(y0 and y0[2] == 3 and gstate(new, rs) and gstate(new, rs)[2] != 3)
        # The group's respawn left at the choice and at the switch (true).
        x_resp0 = st0[5] if st0 and st0[2] == 3 else -1
        if x_wait_land: cause = 'X-wait-at-landing'
        elif claim_when or x_ally: cause = 'ally:' + (claim_when or 'capture')
        elif x_enemy: cause = 'enemy-took'
        elif enemy_near: cause = 'enemy-near'
        elif y_wait_excluded: cause = 'Y-wait-excluded'
        elif y_resp_end: cause = 'Y-respawned'
        else: cause = 'price'
        out.append(dict(won=won, champ=name[cid], kind='switched', cause=cause, strong=gstr > 0, hit_x=hit_x, x_wait_sub=x_wait_sub, land_minus_centre=(bx - cxw) if bx >= 0 and cxw >= 0 else None, flicker=flicker, mode=mode, claimed0=claimed0, ally_br=tuple(sorted(set(ally_br))), got=got, lost=lost, ally_recall=ally_recall,
                        x_resp0=x_resp0, y_from_start=a, y_from_spawn=b, x_state=st[2] if st else -1,
                        x_is_start=F[gl][f[0]][f[1]], y_dist_start=a, key=(d, cid, rl, gl, new)))
    return out


if __name__ == '__main__':
    ana = sys.argv[1]
    idx = json.load(open(Path(ana)/'index.json'))['games']
    seen = {}
    for r in idx:
        if r['dir'] not in seen and Path(ROOT/r['source']).exists(): seen[r['dir']] = r['source']
    rows = []
    with ProcessPoolExecutor(16) as ex:
        for o in ex.map(game, list(seen.items()), chunksize=4):
            if o: rows.extend(o)
    nTG = 2 * len(seen)
    sw = [r for r in rows if r['kind'] == 'switched']
    print(f'games {len(seen)}; landings r<={MAXR}: {len(rows)} ({len(rows)/nTG:.2f}/team-game), switched {len(sw)} ({len(sw)/nTG:.2f}/team-game, {len(sw)/max(1,len(rows)):.0%})')
    cc = Counter(r['cause'] for r in sw)
    for c, n in cc.most_common():
        sub = [r for r in sw if r['cause'] == c]
        pos = [r for r in sub if r['lost'] is not None and r['lost'] > 0]
        ar = sum(r['ally_recall'] for r in sub)
        fl = sum(r['flicker'] for r in sub)
        print(f'  {c:16s} {n:5d} ({n/len(sw):.0%})  walk-sooner {len(pos)/n:.0%}  mean excess {sum(r["lost"] for r in pos)/max(1,len(pos)):.1f}'
              f'  ally also recalled for X {ar/n:.0%}  flicker {fl/n:.0%}  W {sum(r["won"] for r in sub)} L {n - sum(r["won"] for r in sub)}')
    print('by champion:', Counter(r['champ'] for r in sw).most_common(8))
    ps = [r for r in sw if not r['flicker']]
    print(f'persistent switches {len(ps)} ({len(ps)/nTG:.2f}/team-game)')
    for c, n in Counter(r['cause'] for r in ps).most_common():
        sub = [r for r in ps if r['cause'] == c]
        pos = [r for r in sub if r['lost'] is not None and r['lost'] > 0]
        print(f'  {c:18s} {n:5d} ({n/len(ps):.0%})  walk-sooner {len(pos)/n:.0%}  mean excess {sum(r["lost"] for r in pos)/max(1,len(pos)):.1f}  excess/team-game {sum(r["lost"] for r in pos)/nTG:.2f}  ally recalled for X {sum(r["ally_recall"] for r in sub)/n:.0%}')
    for c in ('ally:before', 'ally:channel', 'X-wait-at-landing', 'price', 'Y-wait-excluded'):
        sub = [r for r in ps if r['cause'] == c]
        print(c, 'mode', Counter(r['mode'] for r in sub).most_common(6), 'ally branch', Counter(r['ally_br'] for r in sub).most_common(5), 'X next capture', Counter(r['got'] for r in sub).most_common())
    xw = [r for r in sw if r['cause'] == 'X-wait-at-landing']
    print('X-wait-at-landing sub-causes', Counter(r['x_wait_sub'] for r in xw).most_common(), 'landing-centre steps', Counter(r['land_minus_centre'] for r in xw).most_common(6))
    print('all switches landing-centre steps', Counter(r['land_minus_centre'] for r in sw).most_common(6))
    print('all landings by mode at choice: n, switched persistent, X captured by me / ally / none / enemy')
    for m, n in Counter(r['mode'] for r in rows).most_common(7):
        sub = [r for r in rows if r['mode'] == m]
        sp = sum(r['kind'] == 'switched' and not r['flicker'] for r in sub)
        g_ = Counter(r['got'] for r in sub)
        print(f"  {m} {n:6d} ({n/nTG:.2f}/tg) sw {sp/n:.0%}  me {g_['me']/n:.0%} ally {g_['ally']/n:.0%} none {g_['none']/n:.0%} enemy {g_['enemy']/n:.0%}  claimed by ally at choice {sum(r['claimed0'] for r in sub)/n:.0%}")
    for m in ('J', 'S', 'C'):
        for st_ in (False, True):
            sub = [r for r in rows if r['mode'] == m and r['strong'] == st_]
            if not sub: continue
            g_ = Counter(r['got'] for r in sub)
            print(f"  {m} strong={st_} {len(sub)/nTG:.2f}/tg hit X {sum(r['hit_x'] for r in sub)/len(sub):.0%} me {g_['me']/len(sub):.0%} ally {g_['ally']/len(sub):.0%} none {g_['none']/len(sub):.0%} switched {sum(r['kind']=='switched' for r in sub)/len(sub):.0%}")
    sub = [r for r in rows if r['claimed0']]
    g_ = Counter(r['got'] for r in sub)
    print(f"  claimed at choice: {len(sub)} ({len(sub)/nTG:.2f}/tg) me {g_['me']/len(sub):.0%} ally {g_['ally']/len(sub):.0%} none {g_['none']/len(sub):.0%}")
    pr = [r for r in sw if r['cause'] == 'price']
    print('price cases: X respawning at choice', sum(r['x_resp0'] >= 0 for r in pr), 'Y walk from start <= from spawn', sum(r['y_from_start'] <= r['y_from_spawn'] for r in pr))
    import random
    random.seed(1)
    for c in cc:
        ex = [r['key'] for r in sw if r['cause'] == c and not r['flicker']]
        print(c, random.sample(ex, min(3, len(ex))))
