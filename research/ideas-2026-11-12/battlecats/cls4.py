"""Four-class opponent classifier {fish, mite, bc, other}: the 11-09 oppmodel (pick order given champion, then
priority tokens) with BattleCats tokens added. Offline evaluation only.

usage: cls4.py SPLIT_ISO [--no-bc-tokens] [--bc-variant]
Data: ds_bc.pkl (both sides of BattleCats' games, 11-08..11-12, build_ds.py on this pull) plus the oppmodel's
ds_others/ds_fish/ds_mite (11-07..11-09)."""
import sys, os, pickle, collections
import numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'ideas-2026-11-09', 'oppmodel'))
import tokens as T0

FISH, MITE, BC, US = 'Intercontinental Fish', 'Mite', 'BattleCats', 'stellar best girl'
CLASSES = ['fish', 'mite', 'bc', 'other']
def cls_of(team): return 0 if team == FISH else 1 if team == MITE else 2 if team == BC else 3

# BattleCats' fixed type order for its quiet priorities (highest acts first); Tavi/Stellar never seen.
BC_ORDER = ['Heart of Ruin', 'Varg', 'Ryth', 'Marcella', 'Ren', 'Issac', 'Vendetta', 'Willow', 'Vesper Vale', 'Prism', 'Cassi']
def bc_lo(roster):
    """quiet carrying value per body: 13 - (number of teammates above it in BC_ORDER); None if a type is unknown."""
    out = []
    for nm in roster:
        if nm not in BC_ORDER: out.append(None); continue
        above = sum(1 for x in roster if x in BC_ORDER and BC_ORDER.index(x) < BC_ORDER.index(nm))
        out.append(13 - above)
    return out

TOK = T0.TOK + ['bc_quiet', 'bc_level', 'bc_flag']
TI = {n: i for i, n in enumerate(TOK)}

def token(v, j, roster, ranks, lo, hp, maxhp, gems, shield, res0, bc_tokens=True, bc_levels=True):
    v = int(v)
    if bc_tokens and v != 0:
        L = lo[j]
        if L is not None:
            if bc_levels and (v == L or v == L + 7): return TI['bc_quiet']
            if v < 0 and v >= -300 and (L - v) % 7 == 0: return TI['bc_level']
        elif 8 <= v <= 20 and bc_levels: return TI['bc_quiet']
        if v in (35, 38, 40): return TI['bc_flag']
    return T0.token(v, j, roster, ranks, hp, maxhp, gems, shield, res0)

def stream(side, observer=None, **mode):
    roster = side['roster']; rk = T0.fish_ranks(roster); lo = bc_lo(roster)
    last = {}; res0 = {}; n1 = len(roster) + 1; out = []
    for o in side['obs']:
        if observer is not None and not (int(o[3]) >> observer) & 1: continue
        r, j, v = int(o[0]), int(o[1]), int(o[2])
        if j in last and last[j] == v: continue
        last[j] = v
        out.append((r, token(v, j, roster, rk, lo, o[4], o[5], o[6], o[7], res0.get(j), **mode)))
        if v != 0 and j not in res0: res0[j] = (-v) % n1
    return out

def draft_items(side):
    p = [x for x in side['pickIds'] if x >= 0]
    return [(c, k, len(p)) for k, c in enumerate(p)]

class Model:
    def __init__(self, tau=0.5, eps=0.02, a=1.0, draft_a=2.0, prior=(0.2, 0.2, 0.2, 0.4), mode=None, use_tokens=True):
        self.tau, self.eps, self.a, self.draft_a = tau, eps, a, draft_a
        self.prior = np.log(np.array(prior)); self.mode = mode or {}; self.use_tokens = use_tokens
    def fit(self, sides):
        K = len(TOK); cnt = [np.zeros(K) for _ in range(3)]; other = collections.defaultdict(lambda: np.zeros(K))
        dc = [collections.defaultdict(lambda: np.zeros(5)) for _ in range(3)]
        dteam = collections.defaultdict(lambda: collections.defaultdict(lambda: np.zeros(5)))
        for s in sides:
            c = cls_of(s['team'])
            toks = [t for _, t in stream(s, **self.mode)]
            if toks:
                if c < 3: cnt[c] += np.bincount(toks, minlength=K)
                else: other[s['team']] += np.bincount(toks, minlength=K)
            for ch, k, n in draft_items(s):
                if c < 3: dc[c][(ch, n)][k] += 1
                else: dteam[s['team']][(ch, n)][k] += 1
        P = [(cnt[c] + self.a) / (cnt[c].sum() + self.a * K) for c in range(3)]
        ps = [(h + self.a) / (h.sum() + self.a * K) for h in other.values() if h.sum() > 20]
        P.append(np.mean(ps, axis=0))
        self.P = np.array(P); self.logP = np.log((1 - self.eps) * self.P + self.eps / K)
        keys = set(k for d in dc for k in d) | set(k for t in dteam.values() for k in t)
        self.draft = {}
        for key in keys:
            ch, n = key; rows = []
            vs = [t[key] / t[key].sum() for t in dteam.values() if key in t and t[key].sum() > 0]
            for c in range(4):
                v = (dc[c].get(key) if c < 3 else (np.mean(vs, axis=0) * 10 if vs else None))
                v = np.zeros(5) if v is None else v.copy(); v = v[:n]
                rows.append(np.log((v + self.draft_a / n) / (v.sum() + self.draft_a)))
            self.draft[key] = np.array(rows)
        return self
    def trajectory(self, side, rounds, observer=None, use_draft=True, mode=None):
        lp0 = self.prior.copy()
        if use_draft:
            for ch, k, n in draft_items(side):
                t = self.draft.get((ch, n))
                if t is not None: lp0 = lp0 + t[:, k]
        st = stream(side, observer, **(mode if mode is not None else self.mode)) if self.use_tokens else []
        acc = np.zeros(4); out = []; i = 0
        for R in rounds:
            while i < len(st) and st[i][0] <= R:
                acc = acc + self.tau * self.logP[:, st[i][1]]; i += 1
            lp = lp0 + acc; q = np.exp(lp - lp.max()); out.append(q / q.sum())
        return np.array(out)

ROUNDS = [1, 25, 50, 100, 200, 300, 500, 1000]

def load(paths):
    seen = set(); rows = []
    for f in paths:
        if not os.path.exists(f): continue
        for s in pickle.load(open(f, 'rb')):
            k = (s['mid'], s['side'])
            if k in seen or s['team'] == US or s['created'] < '2026-11-08': continue
            seen.add(k); rows.append(s)
    return rows

def report(m, test, label, observer=True, use_draft=True, mode=None, only=None):
    acc = collections.defaultdict(lambda: np.zeros((4, 4))); wrong9 = collections.defaultdict(lambda: np.zeros(4)); right8 = collections.defaultdict(lambda: np.zeros(4))
    for s in test:
        c = cls_of(s['team'])
        if only is not None and c != only: continue
        for o in ([None] if not observer else range(len(s['opp_roster']))):
            for R, p in zip(ROUNDS, m.trajectory(s, ROUNDS, o, use_draft, mode)):
                if R > s['rounds']: continue
                acc[R][c, int(np.argmax(p))] += 1
                wrong9[R][c] += max(p[k] for k in range(4) if k != c) > 0.9; right8[R][c] += p[c] > 0.8
    print(f'== {label}')
    print('round      n   acc   recall fish/mite/bc/other    precision bc   bc p>0.8   wrong>0.9 fish/mite/bc/other')
    for R in ROUNDS:
        M = acc[R]; n = M.sum()
        if n == 0: continue
        rec = [M[i, i] / max(1, M[i].sum()) for i in range(4)]
        print(f'{R:5d} {int(n):6d} {np.trace(M) / n:.3f}   ' + '/'.join(f'{x:.3f}' for x in rec) +
              f'      {M[2, 2] / max(1, M[:, 2].sum()):.3f}      {right8[R][2] / max(1, M[2].sum()):.3f}     ' +
              '/'.join(f'{wrong9[R][i] / max(1, M[i].sum()):.3f}' for i in range(4)))

if __name__ == '__main__':
    split = sys.argv[1]
    base = os.path.expanduser('~/tmp-offload/oppcls/')
    rows = load([os.path.expanduser('~/tmp-offload/battlecats/ds_bc.pkl')] + [base + f for f in ('ds_others.pkl', 'ds_fish.pkl', 'ds_mite.pkl')])
    train = [s for s in rows if s['created'] < split]; test = [s for s in rows if s['created'] >= split]
    cnt = lambda rs: dict(collections.Counter(CLASSES[cls_of(s['team'])] for s in rs))
    print('train', cnt(train), 'test', cnt(test))
    np.set_printoptions(precision=3, suppress=True)
    for label, kw, ev in [('3 tokens, draft', {}, {}), ('no BC tokens (current classifier tokens), draft', {'mode': {'bc_tokens': False}}, {}),
                          ('draft only', {'use_tokens': False}, {}), ('tokens only, no draft', {}, {'use_draft': False})]:
        m = Model(**kw).fit(train)
        if label.startswith('3'): print('tokens', TOK); print(m.P)
        report(m, test, label + ', per instance', **ev)
    # robustness: BC changes its quiet levels (keeps only the level/flag structure)
    m = Model().fit(train)
    report(m, test, 'BC drops its quiet tiers (bc_quiet read as other), per instance', mode={'bc_levels': False}, only=2)
    # leave-one-team-out for 'other': misread as BC
    print('== leave-one-team-out (other teams): share read as bc at r100 / r300, and bc>0.9')
    teams = collections.Counter(s['team'] for s in rows if cls_of(s['team']) == 3)
    for t, n in teams.most_common(14):
        if n < 40: continue
        mt = Model().fit([s for s in train if s['team'] != t])
        ts = [s for s in rows if s['team'] == t]
        b = collections.Counter()
        for s in ts:
            for o in range(len(s['opp_roster'])):
                for R, p in zip(ROUNDS, mt.trajectory(s, ROUNDS, o)):
                    if R not in (100, 300) or R > s['rounds']: continue
                    b[(R, 'n')] += 1; b[(R, 'bc')] += int(np.argmax(p)) == 2; b[(R, 'bc9')] += p[2] > 0.9
        print(f'{t[:26]:26s} sides={n:4d} ' + ' '.join(f'r{R}: {b[(R, "bc")] / max(1, b[(R, "n")]):.3f} ({b[(R, "bc9")] / max(1, b[(R, "n")]):.3f})' for R in (100, 300)))
