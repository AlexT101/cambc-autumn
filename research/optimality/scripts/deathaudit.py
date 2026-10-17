# For each champion killed by enemy champions: from the first round the victim saw a (later) attacker,
# does a guaranteed escape path exist against the exact multi-turn reach of the visible enemies?
# Conservative for the victim: enemies move by Chebyshev distance (walls ignored), other units ignored.
import json, gzip, os, sys, collections, pickle, statistics as st
from concurrent.futures import ProcessPoolExecutor
ROOT = r'C:\Users\alext\Github\cambc-autumn\replays\.analysis'
MELEE = {'Ryth', 'Vendetta', 'Marcella', 'Ren', 'Varg', 'Issac'}
DASH = {'Vesper Vale': 1, 'Vendetta': 1, 'Ren': 1, 'Issac': 1}
RESET = {'Ryth': 1, 'Vesper Vale': 0, 'Vendetta': 0, 'Issac': 0, 'Marcella': 0, 'Willow': 1, 'Varg': 0, 'Tavi': 0}
UNIT = {'Cassi': [0, 1], 'Stellar': [0], 'Prism': [0], 'Marcella': [1], 'Ren': [0], 'Tavi': [1]}
GROUND = {'Ryth': [0], 'Stellar': [1], 'Prism': [1]}
HORIZON = 8


def cheb(a, b):
    return max(abs(a[0] - b[0]), abs(a[1] - b[1]))


def reach(nm, m, cd):
    """Farthest Chebyshev distance nm can damage after m of its own turns (abilities ready iff cd==0)."""
    if m <= 0:
        return -1
    melee = nm in MELEE
    r = (1 + m) if melee else (3 + m - 1)
    if not melee and nm in RESET and cd[RESET[nm]] == 0:
        r = max(r, 3 + m)
    if nm in DASH and cd[DASH[nm]] == 0:
        r += 2
    for s in UNIT.get(nm, []):
        if cd[s] == 0:
            r = max(r, 4 + m - 1)
    for s in GROUND.get(nm, []):
        if cd[s] == 0:
            r = max(r, 5 + m - 1)
    return r


def game(d):
    try:
        m = json.load(open(os.path.join(ROOT, d, 'meta.json'), encoding='utf-8'))
        ev = [json.loads(l) for l in gzip.open(os.path.join(ROOT, d, 'events.jsonl.gz'), 'rt')]
        R = json.load(gzip.open(os.path.join(ROOT, d, 'rounds.json.gz')))
        mp = json.load(open(os.path.join(ROOT, 'maps', m['map']['hash'] + '.json')))
    except Exception:
        return []
    champs = m['champions']
    ids = [c['id'] for c in champs]
    name = {c['id']: c['name'] for c in champs}
    team = {c['id']: c['team'] for c in champs}
    idx = {c['id']: i for i, c in enumerate(champs)}
    rix = {r: i for i, r in enumerate(R['round'])}
    W, H = mp['width'], mp['height']
    block = set(map(tuple, mp['walls'])) | set(map(tuple, mp['holes'])) | set(map(tuple, mp['altars'])) | {(c['x'], c['y']) for c in mp['camps']}
    spawns = [{(x, y) for x in range(s['minX'], s['maxX'] + 1) for y in range(s['minY'], s['maxY'] + 1)} for s in mp['spawn']]

    def order(r):
        pi = rix.get(r - 1)
        key = lambda c: (-(R['champions'][idx[c]]['prio'][pi] if pi is not None else 0), c)
        A = sorted([c for c in ids if team[c] == 0], key=key)
        B = sorted([c for c in ids if team[c] == 1], key=key)
        f, s = (A, B) if r % 2 == 1 else (B, A)
        seq = []
        for i in range(max(len(A), len(B))):
            if i < len(f): seq.append(f[i])
            if i < len(s): seq.append(s[i])
        return {c: k for k, c in enumerate(seq)}

    ev.sort(key=lambda e: e['s'])
    byround = collections.defaultdict(list)
    for e in ev:
        byround[e['r']].append(e)
    deaths = [e for e in ev if e['k'] == 'death' and e.get('by') not in (None, 'camp') and not e.get('linked')]
    if not deaths:
        return []
    dmg = collections.defaultdict(list)
    for e in ev:
        if e['k'] in ('attack', 'cast'):
            for v, a in (e.get('dmg') or []):
                if v in team and team[v] != team[e['a']] and a > 0:
                    dmg[v].append((e['r'], e['a']))

    def snap(r, slot):
        cur = {}
        i = rix.get(r - 1)
        for c in ids:
            ch = R['champions'][idx[c]]
            cur[c] = (ch['x'][i], ch['y'][i]) if i is not None and ch['alive'][i] else None
        for e in byround.get(r, []):
            if e['t'] >= slot:
                break
            k = e['k']; a = e.get('a')
            if k == 'move': cur[a] = tuple(e['to'])
            elif k == 'cast' and e.get('moved'): cur[a] = tuple(e['moved'])
            elif k in ('recall_end', 'teleport_end'): cur[a] = tuple(e['to'])
            elif k == 'respawn': cur[a] = tuple(e['at'])
            elif k == 'death': cur[e['v']] = None
        return cur

    def escapable(v, r):
        if r + 1 > R['round'][-1]:
            return None
        o = order(r); o2 = order(r + 1)
        sv = o[v]
        pos = snap(r, sv)
        if pos.get(v) is None:
            return None
        i = rix.get(r)
        seen = R['champions'][idx[v]]['sees'][i] if i is not None else []
        pi = rix.get(r - 1)
        enemies = []
        for e in seen:
            if pos.get(e) is None:
                continue
            ch = R['champions'][idx[e]]
            cd = (ch['cd0'][pi], ch['cd1'][pi]) if pi is not None else (0, 0)
            n1 = (1 if o[e] > sv else 0) + (1 if o2[e] < o2[v] else 0)
            enemies.append((name[e], pos[e], cd, n1, n1 != 1))
        if not enemies:
            return None
        home = spawns[team[v]]
        frontier = {pos[v]}
        for k in range(1, HORIZON + 1):
            nxt = set()
            for (x, y) in frontier:
                for dx in (-1, 0, 1):
                    for dy in (-1, 0, 1):
                        t = (x + dx, y + dy)
                        if not (0 <= t[0] < W and 0 <= t[1] < H) or t in block or t in spawns[1 - team[v]]:
                            continue
                        ok = True
                        for (nm, ep, cd, n1, mirror) in enemies:
                            # cumulative enemy turns before our (k+1)-th turn from now
                            mcum = (n1 + ((k - 1) // 2) * 2 + ((k - 1) % 2) * (2 - n1)) if mirror else k
                            if cheb(ep, t) <= reach(nm, mcum, cd):
                                ok = False
                                break
                        if ok:
                            nxt.add(t)
            if not nxt:
                return False
            if nxt & home:
                return True
            frontier = nxt
        return True

    out = []
    for de in deaths:
        v = de['v']; D = de['r']
        attackers = {a for (r, a) in dmg[v] if D - 5 <= r <= D}
        if not attackers:
            continue
        vi = idx[v]
        first = None
        for r in range(max(1, D - 15), D + 1):
            i = rix.get(r)
            if i is None:
                continue
            if set(R['champions'][vi]['sees'][i]) & attackers:
                first = r
                break
        rec = dict(team=m['teams'][team[v]]['name'], victim=name[v], bag=de.get('gems', 0) or 0, D=D, first=first, game=d)
        if first is None:
            rec['class'] = 'never_seen'
        else:
            i0 = rix.get(first - 1)
            rec['hp0'] = R['champions'][vi]['hp'][i0] / R['champions'][vi]['maxHp'][i0] if i0 is not None and R['champions'][vi]['maxHp'][i0] else None
            esc = escapable(v, first)
            rec['esc_first'] = esc
            last_ok = None
            for r in range(first, D + 1):
                if escapable(v, r):
                    last_ok = r
            rec['last_escapable'] = last_ok
            rec['class'] = 'escapable_at_sight' if esc else ('no_escape_at_sight' if esc is False else 'unknown')
        out.append(rec)
    return out


if __name__ == '__main__':
    idxj = json.load(open(os.path.join(ROOT, 'index.json'), encoding='utf-8'))
    tops = ['Intercontinental Fish', 'Mite', 'Sneaky Bush Campers', 'Univardisty of Shingtonwash', 'procless', 'PTN Hyperion']
    dirs = sorted({g['dir'] for g in idxj['games'] if g['kind'] == 'ladder' and g['ok'] and '20261016' <= g['source'].split('/')[2][:8] and any(t in g['teams'] for t in tops)})
    dirs = dirs[:int(sys.argv[1])]
    rows = []
    with ProcessPoolExecutor(16) as ex:
        for r in ex.map(game, dirs, chunksize=4):
            rows += r
    pickle.dump(rows, open('deathaudit.pkl', 'wb'))
    for t in tops:
        rs = [r for r in rows if r['team'] == t]
        if not rs:
            continue
        c = collections.Counter(r['class'] for r in rs)
        n = len(rs)
        esc = [r for r in rs if r['class'] == 'escapable_at_sight']
        lead = [r['D'] - r['last_escapable'] for r in esc if r.get('last_escapable')]
        print(f"{t[:22]:22s} deaths {n:5d} never_seen {c['never_seen']/n:.2f} no_escape_at_sight {c['no_escape_at_sight']/n:.2f} "
              f"escapable_at_sight {c['escapable_at_sight']/n:.2f} unknown {c['unknown']/n:.2f} | last escapable -> death median "
              f"{st.median(lead) if lead else '-'} | bag mean {st.mean(r['bag'] for r in rs):.1f}")
