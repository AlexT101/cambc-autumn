# Level-2 trace reader: turns, beliefs, `TE k=sides` fighters typed and given kits, ready for simport.
import sys, os, json, gzip, zipfile
from collections import defaultdict
sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'extract'))
import simport as SP


def parse_line(l):
    p = l.replace('\x00', '').rstrip('\n').split(' ')
    d = {'tag': p[0]}
    for x in p[1:]:
        if '=' in x:
            k, v = x.split('=', 1); d[k] = v
    return d


def turns(lines, r0=0, r1=1 << 30):
    """(r, c) -> ordered list of parsed lines (TB, TE, TT, TF, TS)."""
    T = defaultdict(list)
    for l in lines:
        l = l.replace('\x00', '')
        tag = l[:2]
        if tag not in ('TT', 'TB', 'TE', 'TF', 'TS'): continue
        d = parse_line(l)
        try: r = int(d['r']); c = int(d['c'])
        except Exception: continue
        if r < r0 or r > r1: continue
        T[(r, c)].append(d)
    return T


def ptrade(s):
    p = s.split(':')
    return dict(lost=int(p[0]), tku=int(p[1]), tkt=int(p[2]), falls=p[3], al=int(p[4]), en=int(p[5]))


class Extract:
    """Per-game truth from tools/replay extract: focus, strength, shield casts, damage events."""
    def __init__(self, exdir, gdir):
        self.dir = os.path.join(exdir, gdir)
        self.meta = json.load(open(self.dir + '/meta.json'))
        self.R = json.load(gzip.open(self.dir + '/rounds.json.gz'))
        self.rix = {r: i for i, r in enumerate(self.R['round'])}
        self.ch = {c['id']: c for c in self.R['champions']}
        self.team = {c['id']: c['team'] for c in self.meta['champions']}
        self.ctype = {c['id']: c['type'] for c in self.meta['champions']}
        self.ev = [json.loads(l) for l in gzip.open(self.dir + '/events.jsonl.gz', 'rt')]
        self.shield_cast = defaultdict(list)
        for e in self.ev:
            if e['k'] == 'cast' and e.get('ab', '').lower().find('shield') >= 0: self.shield_cast[e['a']].append(e['r'])

    def at(self, cid, r, field):
        i = self.rix.get(r - 1, self.rix.get(r))
        return self.ch[cid][field][i] if i is not None else None

    def taken(self, cid, r):
        it = self.at(cid, r, 'items') or []
        return 0.9 if any(it[k] in (13, 15, 17) and it[k + 1] > 0 for k in range(0, len(it) - 1, 2)) else 1.0

    def shield_left(self, cid, r):
        rs = [x for x in self.shield_cast.get(cid, []) if x <= r]
        if not rs: return 3
        return max(0, 5 - (r - rs[-1]))


def type_fighters(turn, sides, my_type, my_handle):
    """Identify each fighter of a sides line: returns (us, them) lists of (fighter dict + typ, handle) or None."""
    en = {}; al = {}
    for d in turn:
        if d['tag'] == 'TB' and d.get('al') == '1':
            hp = d.get('hp', '0/0').split('/')
            rec = dict(i=int(d['i']), h=int(d['h']), t=d['t'], hp=float(hp[0]), max=float(hp[1]), v=d.get('v') == '1', p=d.get('p'))
            (en if d['s'] == 'e' else al)[rec['i']] = rec
    us = SP.parse_fighters(sides['us']); them = SP.parse_fighters(sides['them'])
    self_i = int(sides['self'])
    last = -1
    for f in them:
        hit = None
        for i in sorted(en):
            if i <= last: continue
            e = en[i]
            if abs(e['hp'] - f['health']) < 1 and abs(e['max'] - f['max']) < 1: hit = e; break
        if hit is None: return None
        f['typ'] = hit['t']; f['h'] = hit['h']; f['visible'] = hit['v']; f['idx'] = hit['i']; last = hit['i']
    last = -1
    for k, f in enumerate(us):
        if k == self_i:
            f['typ'] = my_type; f['h'] = my_handle; f['idx'] = None; continue
        hit = None
        for i in sorted(al):
            if i <= last: continue
            a = al[i]
            if abs(a['max'] - f['max']) < 1 and abs(a['hp'] - f['health']) < 1.5: hit = a; break
        if hit is None:
            for i in sorted(al):
                if i <= last: continue
                a = al[i]
                if abs(a['max'] - f['max']) < 1: hit = a; break
        if hit is None: return None
        f['typ'] = hit['t']; f['h'] = hit['h']; f['idx'] = hit['i']; last = hit['i']
    return us, them


def build(fs, X, r, durability=None):
    out = []
    for f in fs:
        foc = X.at(f['h'], r, 'foc') or 100
        raw_str = X.at(f['h'], r, 'str') or f['strength']
        scale = f['strength'] / raw_str if raw_str else 1.0
        g = SP.fighter(f['typ'], f['health'], f['max'], f['shield'], f['strength'], f['arrives'], f['ready'], foc, foc * scale,
                       taken=(durability or {}).get(f['h'], X.taken(f['h'], r)), ident=f['h'])
        if f['shield'] > 0: g.shield_until = X.shield_left(f['h'], r)
        out.append(g)
    return out


def run(sides, us, them, X, r, opts=None, trace=None, durability=None):
    U = SP.Side(build(us, X, r, durability), int(sides['self']), float(sides.get('camp', 0)))
    T = SP.Side(build(them, X, r, durability))
    res = SP.simulate(U, T, sides['first'] == 't', opts=opts, trace=trace)
    res['U'] = U; res['T'] = T
    return res


def agrees(res, t):
    """Port result vs the bot's printed Trade (early exits print 0s or the horizon)."""
    lost = res['they_kill'] > 0
    if t['falls'] == '1' and t['lost'] == 0 and t['tku'] == 0 and t['tkt'] == 0:
        return res['self_falls']  # ended at our fall, lost unknown
    if lost != bool(t['lost']): return False
    if t['lost'] and t['tku'] not in (0, SP.HORIZON) and t['tku'] != res['they_kill']: return False
    if not t['lost'] and t['tkt'] and t['tkt'] != res['we_kill']: return False
    if t['falls'] in '01' and t['falls'] == '1' and not res['self_falls'] and t['lost'] == 0: return False
    return True


def selfplay_games(spdir, exdir):
    idx = json.load(open(exdir + '/index.json'))['games']
    bysrc = {os.path.normpath(g['source']): g for g in idx}
    out = []
    for m in sorted(os.listdir(spdir)):
        for fn in os.listdir(os.path.join(spdir, m)):
            if fn.endswith('.repl26a'):
                p = os.path.normpath(os.path.join(spdir, m, fn))
                g = bysrc.get(p)
                if g: out.append((m, p, g['dir']))
    return out


def selfplay_lines(path, team):
    z = zipfile.ZipFile(path)
    return z.read('team-%s.stdout' % team).decode('utf-8', 'replace').splitlines()
