"""Dash-value shadow run: each logged dash (EDV lines of a debug build with escape::shadow_dash) joined to the
dasher's death within 10 rounds.
usage: dv_shadow.py EXTRACT_DIR BOTNAME [--json OUT]

EDV r h site fx fy qx qy act A K S kd Kw dn D fuel F gems G hp H M
  site: S strike search dash, N strike search no dash (dash ready), A dash_to_attack, K dash_onto (sure kill),
        H Heart of Ruin camp landing, T travel dash, P capture handoff, E escape dash.
  K / S: the plan's hits on turns 2..5 after the turn ends on q with the dash kept / spent (0, 1, 2 = many).
  kd: keep_dash (this turn's walk with the dash kept, turn 1 by the plan). Kw: least K over our walk tiles."""
import sys, json, gzip, zipfile
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor


def parse(src, letter):
    z = zipfile.ZipFile(src)
    lines = z.read(f'team-{letter}.stdout').decode(errors='replace').replace('\x00', '').splitlines()
    edv, dec = [], {}
    for l in lines:
        p = l.split()
        if len(p) < 4: continue
        try:
            if p[0] == 'EDV':
                r, h = int(p[1]), int(p[2])
                site = p[3]
                if p[8] == 'gated':
                    edv.append(dict(r=r, h=h, site=site, gated=True, fuel=int(p[9])))
                    continue
                act, K, S, kd, Kw = map(int, p[9:14])
                dn = int(p[15]); fuel = int(p[17]); gems = int(p[19]); hp = float(p[21]); mhp = float(p[22])
                edv.append(dict(r=r, h=h, site=site, gated=False, act=act, K=K, S=S, kd=kd, Kw=Kw, dn=dn, fuel=fuel, gems=gems,
                                hp=hp, mhp=mhp, f=(int(p[4]), int(p[5])), q=(int(p[6]), int(p[7]))))
            elif p[0] == 'D':
                dec[(int(p[1]), int(p[2]))] = p[3]
        except (ValueError, IndexError):
            pass
    return edv, dec


def one(args):
    ex, g, bot = args
    meta = json.load(open(f"{ex}/{g['dir']}/meta.json"))
    ev = [json.loads(l) for l in gzip.open(f"{ex}/{g['dir']}/events.jsonl.gz", 'rt')]
    team_of = {c['id']: c['team'] for c in meta['champions']}
    rows = []
    for t in (0, 1):
        if g['teams'][t] != bot: continue
        try:
            edv, dec = parse(g['source'], 'ab'[t])
        except KeyError:
            continue
        deaths = defaultdict(list)
        for e in ev:
            if e['k'] == 'death' and team_of.get(e['v']) == t: deaths[e['v']].append((e['r'], e.get('by') is not None))
        for x in edv:
            ds = [(r, champ) for r, champ in deaths.get(x['h'], []) if x['r'] < r <= x['r'] + 10]
            x['die'] = bool(ds)
            x['die_champ'] = any(c for _, c in ds)
            x['retreat3'] = any(dec.get((rr, x['h'])) == 'R' for rr in range(x['r'] + 1, x['r'] + 4))
            x['dec'] = dec.get((x['r'], x['h']), '.')
            x['game'] = g['dir']
            rows.append(x)
    return rows, 1 if bot in g['teams'] else 0


def cls(x):
    if x['gated']: return 'gated'
    if not x['act']: return 'inactive'
    if x['S'] == 0: return 'clean-spent'
    if x['K'] == 0: return 'transition'
    return 'saturated'


def show(rows, games, title, key):
    C, D = Counter(), Counter()
    for x in rows:
        k = key(x)
        C[k] += 1
        D[k] += x['die_champ']
    print(f'\n{title}')
    for k in sorted(C):
        n = C[k]
        p = D[k] / n
        se = (p * (1 - p) / n) ** 0.5
        print(f'  {str(k):40s} {n:7d} {n / games:7.2f}/g  die10 {p:6.3f} +-{1.96 * se:5.3f}')


if __name__ == '__main__':
    ex, bot = sys.argv[1], sys.argv[2]
    idx = json.load(open(f'{ex}/index.json'))
    rows, games = [], 0
    with ProcessPoolExecutor(16) as pool:
        for r, n in pool.map(one, [(ex, g, bot) for g in idx['games'] if g.get('ok')]):
            rows += r
            games += n
    print(f'{games} games, {len(rows)} EDV lines')
    show(rows, games, 'by site', lambda x: x['site'])
    show(rows, games, 'by site x class (deaths to champions within 10)', lambda x: (x['site'], cls(x)))
    # The report's criterion: a clean walk with the dash kept, the dash leaf not clean.
    show([x for x in rows if not x['gated'] and x['act'] and x['site'] != 'N'], games, 'report criterion (Kw==0) on dashes',
         lambda x: (x['site'] if x['site'] in 'SE' else 'other', 'clean-spent' if x['S'] == 0 else 'Kw-clean' if x['Kw'] == 0 else 'Kw-saturated'))
    show([x for x in rows if x['site'] == 'N' and not x['gated'] and x['act']], games, 'search non-dash leaves: end tile with the dash kept',
         lambda x: ('K', x['K']))
    show([x for x in rows if x['site'] in 'SN' and not x['gated']], games, 'search turns: fuel at the choice >= 50k',
         lambda x: (x['site'], x['fuel'] >= 50000))
    show([x for x in rows if x['site'] in 'SN' and not x['gated'] and x['act']], games, 'search, by bag (>=30)',
         lambda x: (x['site'], cls(x), x['gems'] >= 30))
    if '--json' in sys.argv:
        json.dump(rows, open(sys.argv[sys.argv.index('--json') + 1], 'w'))
