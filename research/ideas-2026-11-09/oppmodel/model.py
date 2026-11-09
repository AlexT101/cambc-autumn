"""Opponent classifier {fish, mite, other}: pick order given champion, then priority tokens.

A side's observations are replayed in round order. An enemy champion's priority counts when it differs
from the last value this observer read for that champion (the in-bot rule). Each counted value is one
token (tokens.py); the posterior adds tau * log P(token | class), P smoothed and floored by eps.
"""
import math, collections
import numpy as np
from tokens import TOK, T, token, fish_ranks

CLASSES = ['fish', 'mite', 'other']
FISH, MITE = 'Intercontinental Fish', 'Mite'
US = 'stellar best girl'
PRIOR = np.log(np.array([0.25, 0.25, 0.5]))

def cls_of(team):
    return 0 if team == FISH else 1 if team == MITE else 2

def draft_items(side):
    """(champion, slot, npicks) for each pick: slot 0-based in pick order."""
    p = [x for x in side['pickIds'] if x >= 0]
    return [(c, k, len(p)) for k, c in enumerate(p)]

def stream(side, observer=None, **mode):
    """Counted tokens (round, token) for a side, from the opponent's whole view or one observer's."""
    roster = side['roster']; rk = fish_ranks(roster)
    last = {}; res0 = {}; n1 = len(roster) + 1
    out = []
    for o in side['obs']:
        if observer is not None and not (int(o[3]) >> observer) & 1: continue
        r, j, v = int(o[0]), int(o[1]), int(o[2])
        if last.get(j, 0) == v and j in last: continue
        last[j] = v
        out.append((r, token(v, j, roster, rk, o[4], o[5], o[6], o[7], res0.get(j), **mode)))
        if v != 0 and j not in res0: res0[j] = (-v) % n1
    return out

# Sub-models: (class, weight within class, token mode). The variants are the class's own games
# re-tokenised as if one part of its encoding had changed: a per-game mixture keeps the class
# recognisable from the parts that still hold.
SUBS = [(0, 0.8, {}), (0, 0.1, {'fish_level': False}), (0, 0.1, {'fish_rank': False}),
        (1, 0.85, {}), (1, 0.15, {'mite_quiet': False}), (2, 1.0, {})]

SUB_SETS = {
    'none': [(0, 1.0, {}), (1, 1.0, {}), (2, 1.0, {})],
    'F1M1': [(0, 0.9, {}), (0, 0.1, {'fish_level': False}), (1, 0.85, {}), (1, 0.15, {'mite_quiet': False}), (2, 1.0, {})],
    'F1': [(0, 0.9, {}), (0, 0.1, {'fish_level': False}), (1, 1.0, {}), (2, 1.0, {})],
    'M1': [(0, 1.0, {}), (1, 0.85, {}), (1, 0.15, {'mite_quiet': False}), (2, 1.0, {})],
    'all': SUBS,
}
SUB_SETS['F1gM1'] = SUB_SETS['F1M1']
SUBS = SUB_SETS['F1gM1']

class Model:
    def __init__(self, tau=0.5, eps=0.02, a=1.0, draft_a=2.0, draft_w=1.0, draft_cap=None, subs=SUBS):
        self.tau, self.eps, self.a, self.draft_a, self.draft_w = tau, eps, a, draft_a, draft_w
        self.draft_cap, self.subs = draft_cap, subs

    def fit(self, sides):
        K = len(TOK)
        cnt = [np.zeros(K) for _ in range(2)]
        other_team = collections.defaultdict(lambda: np.zeros(K))
        # pick slot given champion and pick count: per class
        dc = [collections.defaultdict(lambda: np.zeros(5)) for _ in range(3)]
        dteam = collections.defaultdict(lambda: collections.defaultdict(lambda: np.zeros(5)))
        subcnt = [np.zeros(K) for _ in self.subs]
        for s in sides:
            c = cls_of(s['team'])
            for i, (sc, w, mode) in enumerate(self.subs):
                if sc != c or sc == 2: continue
                toks = [t for _, t in stream(s, **mode)]
                if toks: subcnt[i] += np.bincount(toks, minlength=K)
            if c == 2:
                toks = [t for _, t in stream(s)]
                if toks: other_team[s['team']] += np.bincount(toks, minlength=K)
            for ch, k, n in draft_items(s):
                if c < 2: dc[c][(ch, n)][k] += 1
                else: dteam[s['team']][(ch, n)][k] += 1
        P = []
        for i, (sc, w, mode) in enumerate(self.subs):
            if sc < 2: P.append((subcnt[i] + self.a) / (subcnt[i].sum() + self.a * K))
            else:
                # other: each team weighs equally
                ps = [(h + self.a) / (h.sum() + self.a * K) for h in other_team.values() if h.sum() > 20]
                P.append(np.mean(ps, axis=0) if ps else np.ones(K) / K)
        P = np.array(P)
        self.logP = np.log((1 - self.eps) * P + self.eps / K)  # per sub-model
        self.sub_cls = np.array([sc for sc, _, _ in self.subs])
        self.sub_logw = np.log(np.array([w for _, w, _ in self.subs]))
        # Rank-structure-only variants say nothing when N+1 divides 100: other bots' "per-champion
        # constant + multiples of 100" values then keep a residue too.
        self.sub_gated = np.array([not mode.get('fish_level', True) or not mode.get('fish_rank', True) for _, _, mode in self.subs])
        # draft: other pooled with team-equal weights
        keys = set(k for d in dc[:2] for k in d) | set(k for t in dteam.values() for k in t)
        dother = {}
        for key in keys:
            vs = [t[key] / t[key].sum() for t in dteam.values() if key in t and t[key].sum() > 0]
            dother[key] = np.mean(vs, axis=0) if vs else None
        self.draft = {}
        for key in keys:
            ch, n = key
            rows = []
            for c in range(3):
                v = dc[c].get(key) if c < 2 else (dother[key] * 10 if dother[key] is not None else None)
                v = np.zeros(5) if v is None else v.copy()
                v = v[:n]
                rows.append(np.log((v + self.draft_a / n) / (v.sum() + self.draft_a)))
            self.draft[key] = np.array(rows)
        self.P = P
        return self

    def draft_ll(self, side):
        ll = np.zeros(3)
        for ch, k, n in draft_items(side):
            t = self.draft.get((ch, n))
            if t is not None: ll += self.draft_w * t[:, k]
        if self.draft_cap is not None: ll = np.maximum(ll, ll.max() - self.draft_cap)
        return ll

    def class_lp(self, sub, n1=7):
        out = np.full(3, -np.inf)
        ok = ~self.sub_gated if 100 % n1 == 0 else np.ones(len(self.sub_cls), bool)
        for c in range(3):
            sel = (self.sub_cls == c) & ok
            x = self.sub_logw[sel] + sub[sel]
            # max, not log-sum-exp (as the bot: no transcendental calls in fight turns)
            w = np.exp(self.sub_logw[sel]).sum()
            out[c] = x.max() - (np.log(w) if w < 0.999 else 0.0)
        return out

    def trajectory(self, side, rounds, observer=None, use_draft=True, remap=None):
        """Posterior at the start of each round in `rounds` (after that round's reads)."""
        base = getattr(self, 'prior', PRIOR) + (self.draft_ll(side) if use_draft else 0)
        sub = np.zeros(len(self.sub_cls))
        st = stream(side, observer, **(remap if isinstance(remap, dict) else {}))
        out = []; i = 0
        for R in rounds:
            while i < len(st) and st[i][0] <= R:
                t = st[i][1]
                if remap is not None and not isinstance(remap, dict): t = remap[t]
                sub = sub + self.tau * self.logP[:, t]; i += 1
            lp = base + self.class_lp(sub, len(side['roster']) + 1)
            q = np.exp(lp - lp.max()); out.append(q / q.sum())
        return np.array(out)

def load_tables(path):
    """A Model with the bot's compiled tables (opp_tables.h), for exact comparison with the bot."""
    import re
    s = open(path).read()
    num = lambda block: [float(x.rstrip('f')) for x in re.findall(r'-?\d\.\d+e[+-]\d+f', block)]
    grab = lambda pat: re.search(pat, s, re.S).group(1)
    m = Model()
    m.tau = num(grab(r'tau = ([^;]+);'))[0]
    m.prior = np.array(num(grab(r'prior\[3\] = \{([^}]*)\}')), dtype=np.float32)
    m.sub_cls = np.array([int(x) for x in grab(r'sub_class\[subs\] = \{([^}]*)\}').split(',')])
    m.sub_logw = np.array(num(grab(r'sub_log_w\[subs\] = \{([^}]*)\}')), dtype=np.float32)
    m.sub_gated = np.array([x.strip() == 'true' for x in grab(r'sub_gated\[subs\] = \{([^}]*)\}').split(',')])
    m.logP = np.array(num(grab(r'log_p\[subs\]\[tokens\] = \{(.*?)\n\};')), dtype=np.float32).reshape(len(m.sub_cls), -1)
    D = np.array(num(grab(r'draft\[12\]\[3\]\[3\]\[5\] = \{(.*?)\n\};'))).reshape(12, 3, 3, 5)
    cap = num(grab(r'draft_cap = ([^;]+);'))[0]
    m.draft_cap = None if cap >= 1e8 else cap
    m.draft = {(ch, n + 3): D[ch, n].astype(np.float32) for ch in range(12) for n in range(3)}
    return m
