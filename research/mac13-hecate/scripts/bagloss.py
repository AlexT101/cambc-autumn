"""Bag-loss study (h-atrace BL lines): classify the trace side's deaths by model gap.
Usage: bagloss.py BATCH_DIR EXTRACT_DIR [TRACE_TEAM_NAME] > out.json (rows), then bagloss_report.py."""
import sys, re, json, gzip, zipfile, collections
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor

BATCH, AN = Path(sys.argv[1]), Path(sys.argv[2])
TRACE = sys.argv[3] if len(sys.argv) > 3 else 'h-atrace'
D_RE = re.compile(rb'^[\s\0]*D (\d+) (\d+) (\S) (-?\d+) (-?\d+)\s*$', re.M)
BL_RE = re.compile(rb'^[\s\0]*BL(S?) (\d+) (\d+) ?(.*)$', re.M)
TOK_RE = re.compile(r'(\d+)([VT])(-?\d+),(-?\d+),(\d+),(\d+),(-?[\d.]+),(-?\d+),(-?[\d.]+),(\d)(\d),([0-9a-f]+),(-?[\d.]+)(s?)')
NTOK_RE = re.compile(r'(\d+)N(-?\d+),(-?\d+),(\d+),(\d+)(?=\s|$)')


def parse_bl(rest):
    s = rest.decode(errors='replace')
    head, ver, esc, en = s.split('|', 3)
    h = head.split()
    v = ver.split()
    cds = h[6]
    out = dict(br=h[0][0], why=h[0][1], ex=int(h[1]), ey=int(h[2]), hp=float(h[3]), gems=int(h[4]), foc=float(h[5]),
               cd0=int(cds[0]), cd1=int(cds[1]), stunned=int(cds[2]), hits=int(h[7], 16))
    flags = v[0]
    out.update(lethal=int(flags[0]), threatened=int(flags[1]), touched=int(flags[2]))
    out.update(flost=int(v[1][0]), ffalls=int(v[1][1]), fttk=int(v[2]), fall=int(v[3]), fen=int(v[4]), bdmg=float(v[5]))
    esc = esc.strip()
    out['esc'] = None if esc in ('-', '') else (int(esc[0]), int(esc[1]))
    toks = {}
    for m in TOK_RE.finditer(en):
        toks[int(m[1])] = dict(kind=m[2], x=int(m[3]), y=int(m[4]), age=int(m[5]), d=int(m[6]), hp=float(m[7]), gems=int(m[8]),
                               foc=float(m[9]), c0=int(m[10]), c1=int(m[11]), flags=int(m[12], 16), blow=float(m[13]), stun=bool(m[14]))
    for m in NTOK_RE.finditer(en):
        toks.setdefault(int(m[1]), dict(kind='N', x=int(m[2]), y=int(m[3]), age=int(m[4]), d=int(m[5]), blow=-1, stun=False))
    out['en'] = toks
    out['raw'] = s
    return out


ACTIONS = {'move', 'attack', 'cast', 'ward', 'recall_start', 'tribute_start', 'shop', 'blocked', 'lock_place', 'teleport_start'}


def is_action(x):
    # a channel cancelled by damage or a stun is logged under the victim but happens in the enemy's turn
    return x['k'] in ACTIONS or (x['k'] in ('recall_cancel', 'tribute_cancel') and x.get('cause') == 'manual')


def cheb(a, b):
    return max(abs(a[0] - b[0]), abs(a[1] - b[1]))


def one(f):
    f = Path(f)
    d = INDEX.get(f.name)
    if d is None:
        return None
    try:
        meta = json.loads((d / 'meta.json').read_text())
        R = json.load(gzip.open(d / 'rounds.json.gz'))
        ev = [json.loads(l) for l in gzip.open(d / 'events.jsonl.gz', 'rt')]
        z = zipfile.ZipFile(f)
    except Exception:
        return None
    names = [t['name'] for t in meta['teams']]
    try:
        mp = json.loads((d / meta['mapFile']).read_text())
        BUSH = {tuple(t) for t in mp['bushes']}
    except Exception:
        BUSH = set()
    if TRACE not in names:
        return None
    tt = names.index(TRACE)
    out_side = 'team-a.stdout' if tt == 0 else 'team-b.stdout'
    raw = z.read(out_side)
    D = collections.defaultdict(dict)   # handle -> round -> (branch, farm)
    for m in D_RE.finditer(raw):
        D[int(m[2])][int(m[1])] = m[3].decode()
    BL = collections.defaultdict(dict)
    prev = {}
    for m in BL_RE.finditer(raw):
        h, rr = int(m[3]), int(m[2])
        if m[1] == b'S':
            if h in prev:
                BL[h][rr] = prev[h]
            continue
        try:
            BL[h][rr] = prev[h] = parse_bl(m[4])
        except Exception:
            pass
    for h, m in BL.items():
        for rr, b in m.items():
            D[h][rr] = b['br']
    r0 = R['round'][0]
    nR = len(R['round'])
    ch = {c['id']: c for c in R['champions']}
    cname = {c['id']: c['name'] for c in meta['champions']}
    team = {c['id']: c['team'] for c in meta['champions']}
    # Damage and stuns to each champion: (r, t, s, attacker, dmg, stun, kind)
    hits = collections.defaultdict(list)
    for e in ev:
        k = e.get('k')
        if k in ('attack', 'cast') and 'dmg' in e:
            for tgt, dmg in e['dmg']:
                if tgt in ch:
                    hits[tgt].append((e['r'], e['t'], e['s'], e['a'], dmg, False, e.get('ab', 'Attack')))
        if k == 'cast' and e.get('stun'):
            for tgt in (e['stun'] if isinstance(e['stun'], list) else [e.get('tgt')]):
                tg = tgt[0] if isinstance(tgt, list) else tgt
                if tg in ch:
                    hits[tg].append((e['r'], e['t'], e['s'], e['a'], 0, True, e.get('ab')))
        if k == 'camp_attack' and e.get('tgt') in ch:
            hits[e['tgt']].append((e['r'], -1, e['s'], -1, e.get('dmg', 0), False, 'camp'))
    own_turn = {}  # (id, r) -> s of its first action
    for e in ev:
        if 'a' in e and e.get('t', -1) >= 0 and is_action(e):
            own_turn.setdefault((e['a'], e['r']), e['s'])
    deaths = [e for e in ev if e.get('k') == 'death' and team.get(e['v']) == tt]
    by_r = collections.defaultdict(list)
    for x in ev:
        if x.get('k') != 'death':
            by_r[x['r']].append(x)
    trunc = len(raw) >= 1040000
    traced_to = max((rr for m in D.values() for rr in m), default=0)
    first_prism = None
    rows = []
    for e in deaths:
        v, r = e['v'], e['r']
        linked = e.get('linked')
        row = dict(map=meta['map']['name'], src=f.name, r=r, v=v, vname=cname[v], gems=e.get('gems', 0), by=e.get('by'),
                   kname=cname.get(e.get('by')), cause=e.get('cause'), linked=linked)
        if cname[v] == 'Prism' and first_prism is None:
            first_prism = r
            row['first_prism'] = True
        # the body that was hit: for a linked death classify by the partner's trace
        hv = linked if linked is not None else v
        row['hv'] = hv
        k = e.get('by')
        rows.append(row)
        if trunc and r > traced_to - 2:
            row['cls'] = 'truncated'
            continue
        if k is None or k not in ch or team.get(k) == tt:
            row['cls'] = 'camp'
            continue
        # last turn of hv at or before r
        # its turn in the death round counts only if it came before the death (a dead turn prints a D line too)
        acted_r = any(x.get('a') == hv and x['r'] == r and x['s'] < e['s'] and x.get('t', -1) >= 0 and is_action(x) for x in by_r.get(r, ()))
        turns = sorted(rr for rr in D[hv] if (rr < r or (rr == r and acted_r)) and rr >= r - 70)
        if not turns:
            row['cls'] = 'noturn'
            continue
        last = turns[-1]
        row['last'] = last
        row['last_br'] = D[hv][last]
        bl = BL[hv].get(last)
        row['bl'] = bl is not None
        # damage window: after hv's last turn
        s_last = own_turn.get((hv, last))
        win = [h for h in hits[hv] if (h[0] > last or (h[0] == last and (s_last is None or h[2] > s_last))) and h[0] <= r]
        champ = [h for h in win if h[3] >= 0 and not h[5]]
        row['attackers'] = sorted({h[3] for h in champ})
        row['k_turns'] = len({(h[0], h[1]) for h in champ if h[3] == k})
        row['k_dmg'] = sum(h[4] for h in champ if h[3] == k)
        row['all_dmg'] = sum(h[4] for h in win)
        row['camp_dmg'] = sum(h[4] for h in win if h[3] < 0)
        row['stun_in_win'] = any(h[5] for h in win)
        row['k_abs'] = sorted({h[6] for h in champ if h[3] == k})
        # was the victim stunned on its last turn(s)?
        row['stunned_last'] = bl['stunned'] if bl else None
        # decision turn: last unstunned BL turn
        dec = None
        for rr in reversed(turns[-6:]):
            b = BL[hv].get(rr)
            if b and not b['stunned']:
                dec = rr
                break
        row['dec'] = dec
        # replay truth at the victim's last turn round
        # round-end snapshot before the victim's last turn (the death round's has it dead)
        i = max(0, min(nR - 1, last - r0 - 1))
        vx, vy = ch[hv]['x'][i], ch[hv]['y'][i]
        kx, ky = ch[k]['x'][i], ch[k]['y'][i]
        row['kd_true'] = cheb((vx, vy), (kx, ky)) if None not in (vx, vy, kx, ky) else None
        row['k_seen_by_v'] = hv in (ch[k]['seenBy'][i] or [])
        row['k_seen_by_team'] = any(team.get(a) == tt for a in (ch[k]['seenBy'][i] or []))
        # rounds since the victim / any teammate last saw the killer (replay truth), up to 60
        def since(pred):
            for j in range(i, max(-1, i - 61), -1):
                if pred(ch[k]['seenBy'][j] or []):
                    return i - j
            return None
        row['v_saw_ago'] = since(lambda sb: hv in sb)
        row['t_saw_ago'] = since(lambda sb: any(team.get(a) == tt for a in sb))
        row['k_bush'] = (kx, ky) in BUSH if kx is not None else None
        row['v_bush'] = (vx, vy) in BUSH if vx is not None else None
        row['k_foc'] = ch[k]['foc'][i]
        row['v_foc'] = ch[hv]['foc'][i]
        row['v_hp_true'] = ch[hv]['hp'][i]
        # lines over the 10 rounds before
        hist = []
        for rr in range(r - 20, r + 1):
            if rr in D[hv] and rr in turns:
                b = BL[hv].get(rr)
                hist.append((rr, D[hv][rr], b['lethal'] if b else None, b['why'] if b else None))
        row['hist'] = hist
        row['raw_hist'] = [f"{rr} {BL[hv][rr]['raw'][:400]}" for rr in turns[-4:] if rr in BL[hv]]
        if bl:
            row['bl_line'] = {kk: vv for kk, vv in bl.items() if kk not in ('en', 'raw')}
            row['ktok'] = bl['en'].get(k)
            row['en_n'] = len(bl['en'])
        if dec is not None and dec != last:
            db = BL[hv][dec]
            row['dec_line'] = {kk: vv for kk, vv in db.items() if kk not in ('en', 'raw')}
            row['dec_ktok'] = db['en'].get(k)
        # earliest sighting of the killer as V in the victim's BL lines in the 40 rounds before
        seen = [rr for rr in range(r - 40, r + 1) if rr in BL[hv] and BL[hv][rr]['en'].get(k, {}).get('kind') == 'V']
        row['k_V_rounds'] = len(seen)
        row['k_V_last'] = (last - seen[-1]) if seen else None
        # exposure in the last 10: lethal turns
        row['lethal_turns10'] = sum(1 for rr in range(r - 10, r + 1) if rr in BL[hv] and BL[hv][rr]['lethal'])
    # BL-wide stats for the game: lethal turn ends and how many died within 2 rounds
    deathr = collections.defaultdict(list)
    for e in [x for x in ev if x.get('k') == 'death']:
        deathr[e['v']].append(e['r'])
    st = collections.Counter()
    for h, m in BL.items():
        for rr, b in m.items():
            dead = any(rr <= dr <= rr + 1 for dr in deathr.get(h, []))
            key = f"L{b['lethal']}"
            st[key] += 1
            st[key + '_die'] += dead
            st[key + '_br' + b['br']] += 1
            st[key + '_br' + b['br'] + '_die'] += dead
    sc = R['gems']
    win = 1 if sc[tt][-1] > sc[1 - tt][-1] else 0 if sc[tt][-1] < sc[1 - tt][-1] else 0.5
    for row in rows:
        row['win'] = win
        row['score'] = (sc[tt][min(nR - 1, max(0, row['r'] - r0))], sc[1 - tt][min(nR - 1, max(0, row['r'] - r0))])
        row['score_end'] = (sc[tt][-1], sc[1 - tt][-1])
    return dict(win=win, rows=rows, st=dict(st), rounds=nR, deaths_all=len(deaths), stdout=len(raw), trunc=trunc, traced_to=traced_to, src=f.name)


INDEX = {}


def init(index):
    INDEX.update(index)


if __name__ == '__main__':
    for dd in AN.iterdir():
        if (dd / 'meta.json').exists():
            INDEX[Path(json.loads((dd / 'meta.json').read_text())['source']).name] = dd
    files = sorted(BATCH.glob('*.repl26a'))
    res = []
    with ProcessPoolExecutor(32, initializer=init, initargs=(INDEX,)) as ex:
        for o in ex.map(one, files, chunksize=4):
            if o:
                res.append(o)
    json.dump(res, sys.stdout)
