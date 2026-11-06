"""Forced vs free audit of the ENGAGE, ECONOMY and TEAM rules (2026-11-06).

A reported rule only says something about Fish where the outcome it predicts was a choice: the
alternative was legal under cambc-rules.yaml. Every opportunity of each rule is classified from the
actor's own turn-start view (positions of visible champions, visible live camps) and the map:

  forced  only the predicted (or only one) outcome was legal; or it follows from another outcome of
          the same turn that the rule's selection or label conditions on (a ranged basic attack
          without a walk, or an excludes-walking cast, both forbid the step);
  free    the alternatives were legal.

Legality used here: one king step onto a tile that is in bounds, not a wall, hole or altar, not
the enemy spawn, not held by a visible champion or a visible live camp; a dash (if its slot is
ready) to a free tile within 2 whose path avoids walls, visible camps, visible enemies and the enemy
spawn; ranged basic attack range 3 (4 with a ready attack reset after a walk), melee 1 after an
optional walk or dash; damaging unit spells 4, ground spells 5 (3x3 at range 4), Heart of Ruin's
dash 3; stunned turns and teleport channels act not at all. Unseen units are ignored (acting onto
one fails), so "free" is the actor's own view of legality.

Rules (old definitions reproduced exactly, then re-scored on free rows with the same baseline):
  ENGAGE 1   range momentum: close iff the previous step closed (and its turn-level restatement
             that keeps the camp-hit turns the old selection dropped);
  ENGAGE 1a  forced route: progress iff hp > 0.5 when every progress step closes on the enemy;
  ENGAGE 1b  danger-weighted steps (camp tiles and the enemy spawn now block);
  ENGAGE 1c  camp continuation: keeps hitting iff the nearest enemy is beyond 4;
  ENGAGE 2   walking retreat (hp <= 0.36, ratio <= 1.3) and its homeward direction;
  ENGAGE 3   lost target and hunting;
  TACTICS 5  short of full health on spawn: stays;
  ECONOMY 4  walk vs recall (camp-aware walk distance);
  TEAM 3a    stays in camp range; TEAM 3d Willow ends beside the ally she started nearest.

  python3 tools/fish/engage_audit.py research/fish-2026-11-05/rule-audit-engage.json [--jobs 6]
"""
import argparse
import collections
import gzip
import json
import multiprocessing as mp
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from breadth import spawn  # noqa: E402
from combat_common import COHORTS, KIT, one_turn_damage  # noqa: E402
from engage_common import FIT, HELD, ROWS, RANGED, free, write  # noqa: E402

CACHE = {c[0]: c[2] for c in COHORTS}
TEAM_DIR = Path('replays/fish-engage/team-merged')
EPISODES = Path('replays/fish-econ/episodes-v1.jsonl.gz')
ALL = FIT + HELD + ['seventh']
NB = [(dx, dy) for dx in (-1, 0, 1) for dy in (-1, 0, 1) if dx or dy]
EXCL = {(0, 0), (3, 0), (5, 0), (5, 1), (6, 0), (6, 1), (7, 1), (9, 0), (11, 1)}   # (type, slot) excludes walking
DASH = {1: 1, 2: 1, 4: 1, 9: 1, 12: 1}                                              # type -> dash slot
CAMP_RANGE = {0: 3, 1: 4, 2: 0, 3: 0, 4: 5, 5: 4}
RETREAT_HP, RETREAT_RATIO, FORCED_HP = 0.36, 1.3, 0.5
WALK = 5
OB_ID, OB_ALIVE, OB_X, OB_Y = 0, 1, 2, 3


def cheb(a, b):
    return max(abs(a[0] - b[0]), abs(a[1] - b[1]))


def split_of(c):
    return 'fit' if c in FIT else 'held' if c in HELD else 'seventh'


def champ(e):
    return dict(type=e['type'], strength=e['str'], focus=e['foc'], cd=e['cd'], hp=e['hp'], maxHp=e['mhp'])


def sgn(v):
    return (v > 0) - (v < 0)


class Map:
    def __init__(self, m, side):
        self.W, self.H = m['width'], m['height']
        self.walls = set(map(tuple, m['walls']))
        self.block = self.walls | set(map(tuple, m['holes'])) | set(map(tuple, m['altars']))
        self.home = spawn(m, side)
        self.ehome = spawn(m, 1 - side)
        self.hf = self.bfs(sorted(self.home), self.block | self.ehome)

    def inb(self, q):
        return 0 <= q[0] < self.W and 0 <= q[1] < self.H

    def bfs(self, src, blocked, limit=10 ** 9):
        f = {p: 0 for p in src}
        dq = collections.deque(src)
        while dq:
            p = dq.popleft(); d = f[p] + 1
            if d > limit:
                continue
            for dx, dy in NB:
                q = (p[0] + dx, p[1] + dy)
                if self.inb(q) and q not in blocked and q not in f:
                    f[q] = d; dq.append(q)
        return f


class Turn:
    """Legal options at one turn start, from the actor's own view."""

    def __init__(self, M, x, start, actions):
        self.M = M
        self.p = (x['x'], x['y'])
        self.type = x['type']
        self.ranged = x['type'] in RANGED
        self.enemies = {(e['x'], e['y']) for e in x['E']}
        self.occ = self.enemies | {(a['x'], a['y']) for a in x['A'] if 'x' in a}
        self.camps = [c for c in (start or {}).get('camps', []) if c.get('hp', 1) > 0 and 'x' in c]
        self.camp_tiles = {(c['x'], c['y']) for c in self.camps}
        self.cd = x['cd']
        self.stunned = x['stn'] or x['ch'] == 3
        p = self.p
        self.steps = [] if self.stunned else [q for q in ((p[0] + dx, p[1] + dy) for dx, dy in NB) if self.free_tile(q)]
        slot = DASH.get(self.type)
        self.dash_ready = not self.stunned and slot is not None and self.cd[slot] == 0
        self.dash = self.landings(p) if self.dash_ready else []
        self._reach = None
        kinds = [a['kind'] for a in actions]
        self.moves = kinds.count('Move')
        self.attacked = 'Attack' in kinds
        self.excl = any(a['kind'] == 'Cast ability' and (self.type, a.get('slot')) in EXCL for a in actions)
        # Same-turn outcomes that forbid stepping: a ranged basic attack without a walk, an exclusive cast.
        self.step_forbidden = self.excl or (self.ranged and self.attacked and self.moves == 0)

    def inb(self, q):
        return self.M.inb(q)

    def free_tile(self, q):
        return self.inb(q) and q not in self.M.block and q not in self.M.ehome and q not in self.occ and q not in self.camp_tiles

    def landings(self, o):
        M = self.M; out = []
        for dx in range(-2, 3):
            for dy in range(-2, 3):
                q = (o[0] + dx, o[1] + dy)
                if max(abs(dx), abs(dy)) != 2 or q == self.p or not self.free_tile(q):
                    continue
                mids = [(o[0] + ax, o[1] + ay) for ax in (-1, 0, 1) for ay in (-1, 0, 1) if (ax or ay)
                        and cheb((o[0] + ax, o[1] + ay), q) == 1]
                if any(self.inb(m) and m not in M.walls and m not in self.camp_tiles and m not in self.enemies
                       and m not in M.ehome for m in mids):
                    out.append(q)
        return out + [q for q in ((o[0] + dx, o[1] + dy) for dx, dy in NB) if q != self.p and self.free_tile(q)]

    def reach(self):
        """Tiles other than the start reachable this turn: a walk, a dash, or a walk and a dash in either order."""
        if self._reach is None:
            R = set(self.steps)
            if self.dash_ready:
                R |= set(self.dash)
                for o in list(self.steps) + list(self.dash):
                    R |= set(self.landings(o)) if o in self.steps else {q for q in ((o[0] + dx, o[1] + dy) for dx, dy in NB)
                                                                       if q != self.p and self.free_tile(q)}
            R.discard(self.p)
            self._reach = sorted(R)
        return self._reach

    def can_hit_camp(self):
        if self.stunned or not self.camps:
            return False
        t = self.type; reset, _, abil = KIT[t]
        cs = [(c['x'], c['y']) for c in self.camps]
        near = lambda q, r: any(cheb(q, c) <= r for c in cs)
        if self.ranged:
            if near(self.p, 3):
                return True
            if reset is not None and self.cd[reset] == 0 and any(near(q, 3) for q in self.steps):
                return True
        elif near(self.p, 1) or any(near(q, 1) for q in self.reach()):
            return True
        for slot, _, kind in abil:
            if self.cd[slot] == 0 and near(self.p, {'unit': 4, 'ground': 5, 'hor': 3}[kind]):
                return True
        return False


class Tally:
    def __init__(self):
        self.c = collections.defaultdict(collections.Counter)

    def add(self, rule, subset, sp, **kw):
        k = self.c[f'{rule}|{subset}']
        k[f'{sp}:n'] += 1
        for f, v in kw.items():
            k[f'{sp}:{f}'] += v

    def merge(self, other):
        for k, v in other.items():
            self.c[k].update(v)


def index_turns(a):
    idx = {}
    for t in a['turns']:
        idx.setdefault((t['round'], t['id']), t)
    return idx


def init(arr_keys):
    ARR[0] = arr_keys


ARR = [None]


def one(line):
    g = json.loads(line)
    c, game = g['cohort'], g['game']
    sp = split_of(c)
    with gzip.open(Path(CACHE[c]) / f'{game}.json.gz') as f:
        A = json.load(f)
    M = Map(A['map'], A['side'])
    idx = index_turns(A)
    T = Tally()
    ex = collections.defaultdict(list)
    by = {int(a): rows for a, rows in g['actors'].items()}
    byr = {a: {r['r']: r for r in rows} for a, rows in by.items()}
    cache = {}

    def turn(aid, r):
        k = (aid, r['r'])
        if k not in cache:
            t = idx.get((r['r'], aid))
            cache[k] = Turn(M, r['x'], t['start'] if t else None, t['actions'] if t else [])
        return cache[k]

    for aid, rows in by.items():
        nxt = [None] * len(rows); cur = None
        for i in range(len(rows) - 1, -1, -1):
            r = rows[i]
            if not r['alive']:
                cur = None
            y = r.get('y')
            if y and y['camp']:
                cur = (r['r'], (y['ex'], y['ey']))
            nxt[i] = cur
        last_ret = None
        for i, r in enumerate(rows):
            x, y = r.get('x'), r.get('y')
            if not (x and y):
                continue
            p = (x['x'], x['y'])
            # ---------------- TACTICS 5: on own spawn short of full health.
            if r['alive'] and x['home'] and x['ch'] == 0:
                tt = turn(aid, r)
                exit_ok = any(q not in M.home for q in tt.steps + tt.dash)
                prev = rows[i - 1] if i else None
                if prev is None or prev['r'] != r['r'] - 1:
                    cause = 'unknown'
                elif not prev['alive'] or not prev.get('y'):
                    cause = 'respawn'
                elif prev['y']['ehw'] == 0:
                    cause = 'hit_on_spawn' if x['hp'] < x['mhp'] else 'stayed'
                else:
                    cause = 'arrival'
                short = x['hp'] < x['mhp']
                left = y['ehw'] != 0
                if exit_ok:
                    T.add('spawn_old', 'short' if short else 'full', sp, stay=not left)
                kind = 'stunned' if x['stn'] else 'no_exit' if not exit_ok else 'free'
                T.add('spawn', f"{'short' if short else 'full'}|{cause}|{kind}", sp, stay=not left)
            if not free(x):
                continue
            E = x['E']
            # ---------------- ENGAGE 1: range momentum.
            if E and 4 <= x['d1'] <= 8 and x['gst'] != 2:
                e = E[0]; E0 = (e['x'], e['y'])
                tt = turn(aid, r)
                close = y['ed'][str(e['id'])] < x['d1']
                close_legal = [q for q in tt.reach() if cheb(q, E0) < x['d1']]
                geo = 'no_closing_step' if not close_legal else 'free'
                if not y['camp']:
                    prev = rows[i - 1] if i else None
                    px, py = (prev.get('x'), prev.get('y')) if prev else (None, None)
                    mom = None
                    if px and py and prev['r'] == r['r'] - 1:
                        v = (py['ex'] - px['x'], py['ey'] - px['y'])
                        if max(abs(v[0]), abs(v[1])) == 1 and (py['ex'], py['ey']) == p:
                            mom = sgn(cheb((p[0] + v[0], p[1] + v[1]), E0) - e['d'])
                        elif v == (0, 0):
                            mom = 0
                    kind = geo if geo != 'free' else 'outcome' if tt.step_forbidden else 'free'
                    pred = mom == -1
                    for sub in ('old', kind) + (('one_closing_step',) if kind == 'free' and len(close_legal) == 1 else ()):
                        T.add('momentum', sub, sp, ok=pred == close, base=not close, close=close, pred=pred)
                    if kind == 'free':
                        T.add('momentum', f'free|mom={mom}', sp, close=close)
                # Turn-level restatement: camp-hit turns stay in (their step was given up by choice).
                prev = rows[i - 1] if i else None
                px, py = (prev.get('x'), prev.get('y')) if prev else (None, None)
                mom2 = None
                if px and py and prev['r'] == r['r'] - 1:
                    v = (py['ex'] - px['x'], py['ey'] - px['y'])
                    if max(abs(v[0]), abs(v[1])) == 1 and (py['ex'], py['ey']) == p:
                        mom2 = sgn(cheb((p[0] + v[0], p[1] + v[1]), E0) - e['d'])
                pred = mom2 == -1
                T.add('momentum_turn', 'all', sp, ok=pred == close, base=not close, close=close)
                T.add('momentum_turn', geo, sp, ok=pred == close, base=not close, close=close, camp=bool(y['camp']))
            # ---------------- ENGAGE 1a: route geometry (hindsight goal).
            if E and 4 <= x['d1'] <= 8 and not y['camp'] and x['gst'] != 2 and not y['dash']:
                nf = nxt[i + 1] if i + 1 < len(rows) else None
                if nf is not None and nf[0] - r['r'] <= 40 and cheb(p, nf[1]) > 1:
                    G = nf[1]; e = E[0]; E0 = (e['x'], e['y'])
                    tt = turn(aid, r)
                    Pg = [d for d in NB if cheb((p[0] + d[0], p[1] + d[1]), G) < cheb(p, G)]
                    safe = [d for d in Pg if cheb((p[0] + d[0], p[1] + d[1]), E0) >= e['d']]
                    mv = (y['ex'] - p[0], y['ey'] - p[1])
                    prog = mv in Pg
                    PgL = [q for q in tt.steps if cheb(q, G) < cheb(p, G)]
                    safeL = [q for q in PgL if cheb(q, E0) >= e['d']]
                    hp = x['hp'] / x['mhp']
                    old = 'forced' if not safe else 'free'
                    new = 'no_legal_progress' if not PgL else 'outcome' if tt.step_forbidden else 'trade' if not safeL else 'safe'
                    T.add('route', f'old_{old}', sp, ok=(hp > FORCED_HP) == prog, base=prog, prog=prog)
                    T.add('route', f'old_{old}|{new}', sp, ok=(hp > FORCED_HP) == prog, base=prog, prog=prog)
                    T.add('route', f'new_{new}', sp, ok=(hp > FORCED_HP) == prog, base=prog, prog=prog)
                    if new in ('trade', 'safe'):
                        T.add('route', f"new_{new}|{'hurt' if hp < FORCED_HP else 'ok'}", sp, prog=prog)
            # ---------------- ENGAGE 1b: danger-weighted steps.
            if E and 3 <= x['d1'] <= 8 and not y['camp'] and x['gst'] != 2 and not y['dash'] and not y['hitc'] and y['moves'] == 1:
                nf = nxt[i + 1] if i + 1 < len(rows) else None
                if nf is not None and nf[0] - r['r'] <= 40 and cheb(p, nf[1]) > 1:
                    G = nf[1]
                    tt = turn(aid, r)
                    occ = {(q['x'], q['y']) for q in E} | {(a['x'], a['y']) for a in x['A']}
                    P = [(p[0] + d[0], p[1] + d[1]) for d in NB]
                    P = [q for q in P if q not in M.block and q not in occ and M.inb(q) and cheb(q, G) < cheb(p, G)]
                    e1 = (y['ex'], y['ey'])
                    eh = max(1, x['hp'] + x['sh'])
                    dang = lambda q: round(sum(0 if q2['stn'] else one_turn_damage(champ(q2), cheb(q, (q2['x'], q2['y']))) for q2 in E) / eh, 4)
                    hk = 'hurt' if x['hp'] / x['mhp'] < 0.5 else 'ok'
                    for name, PP in (('old', P), ('legal', [q for q in P if q not in tt.camp_tiles and q not in M.ehome])):
                        if e1 in PP and len(PP) >= 2:
                            dg = {q: dang(q) for q in PP}
                            if len(set(dg.values())) >= 2:
                                mn = min(dg.values())
                                rnd = sum(1 for q in PP if dg[q] == mn) / len(PP)
                                for sub in (name, f'{name}|{hk}'):
                                    T.add('danger', sub, sp, ok=dg[e1] == mn, rand=rnd)
                            elif name == 'legal':
                                T.add('danger', 'dropped_no_spread', sp)
                        elif name == 'legal' and e1 in P:
                            T.add('danger', 'dropped_lt2_legal', sp)
            # ---------------- ENGAGE 1c: camp continuation.
            if i and rows[i - 1].get('y') and rows[i - 1]['y']['camp'] and rows[i - 1]['r'] == r['r'] - 1 and x['aggro'] and E:
                tt = turn(aid, r)
                hit = bool(y['camp'])
                pred = x['d1'] > 4
                kind = 'free' if tt.can_hit_camp() else 'no_camp_in_reach'
                db = 'd1-3' if x['d1'] <= 3 else f"d{x['d1']}" if x['d1'] <= 8 else 'far'
                for sub in ('old', kind, f'{kind}|{db}'):
                    T.add('camp', sub, sp, ok=pred == hit, base=hit, hit=hit)
            # ---------------- ENGAGE 2: walking retreat.
            if E and x['d1'] <= 3:
                e = E[0]; E0 = (e['x'], e['y'])
                seq = rows[i:i + 3]
                ok = len(seq) == 3 and all(q.get('x') and q.get('y') and q['r'] == r['r'] + k for k, q in enumerate(seq))
                if ok and not (x['d1'] <= 1 and not x['ranged']):
                    hit = any(q['y']['hitc'] for q in seq)
                    p3 = (seq[-1]['y']['ex'], seq[-1]['y']['ey'])
                    rec_arr = any(seq[k]['x']['home'] and seq[k - 1]['y']['ehw'] != 0 for k in (1, 2))
                    retreat = cheb(p3, E0) - cheb(p, E0) >= 2 and not hit and not rec_arr
                    eh = x['hp'] + x['sh']
                    ratio = (eh + sum(a['hp'] + a['sh'] for a in x['A'] if a['d'] <= 8)) / max(1, sum(q['hp'] + q['sh'] for q in E if q['d'] <= 8))
                    pred = x['hp'] / x['mhp'] <= RETREAT_HP and ratio <= RETREAT_RATIO
                    tt = turn(aid, r)
                    blocked = M.block | M.ehome | tt.occ | tt.camp_tiles
                    f = M.bfs([p], blocked, 3 + (2 if tt.dash_ready else 0))
                    possible = any(cheb(q, E0) >= x['d1'] + 2 for q in f)
                    kind = 'free' if possible else 'cannot_gain_2'
                    for sub in ('old', kind):
                        T.add('retreat', sub, sp, ok=pred == retreat, base=not retreat, retreat=retreat)
                    if retreat:
                        if last_ret is None or r['r'] - last_ret > 3:
                            # Episode: direction of the first step and over the 3 turns.
                            hf = M.hf
                            away = [q for q in tt.steps if cheb(q, E0) > x['d1'] and q in hf]
                            h0 = hf.get(p)
                            home = [q for q in away if h0 is not None and hf[q] < h0]
                            cls = 'no_away_step' if not away else 'all_homeward' if len(home) == len(away) else 'none_homeward' if not home else 'mixed'
                            p1 = (y['ex'], y['ey'])
                            dhw = seq[-1]['y']['ehw'] - x['hw']
                            first_away = p1 in away
                            T.add('retreat_dir', cls, sp, hw3_shorter=dhw < 0, first_away=first_away,
                                  first_home=first_away and p1 in home,
                                  placebo_home=(len(home) / len(away)) if away else 0)
                            T.add('retreat_dir', 'all', sp, hw3_shorter=dhw < 0)
                        last_ret = r['r']
            # ---------------- ENGAGE 3: lost target, hunting.
            if not E and not x['later'] and i:
                cand = [m for m in x['M'] if m['r'] == r['r'] - 1 and m.get('alive')]
                if cand and rows[i - 1]['r'] == r['r'] - 1:
                    m = min(cand, key=lambda q: q['d'])
                    L = (m['x'], m['y'])
                    target = x['lhit'] is not None and x['lhit'][1] == m['id'] and x['lhit'][0] <= 2
                    for q in rows[i:i + 5]:
                        qx, qy = q.get('x'), q.get('y')
                        if not (qx and qy):
                            break
                        a0 = (qx['x'], qx['y']); b0 = (qy['ex'], qy['ey'])
                        tq = turn(aid, q)
                        P_ = (2 * p[0] - L[0], 2 * p[1] - L[1])
                        cl_legal = any(cheb(s, L) < cheb(a0, L) for s in tq.reach())
                        kind = 'no_closing_step' if not cl_legal else 'outcome' if tq.step_forbidden else 'free'
                        for sub in ('target' if target else 'other',):
                            T.add('lost', f'{sub}|all', sp, close=cheb(b0, L) < cheb(a0, L), open=cheb(b0, L) > cheb(a0, L),
                                  closeP=cheb(b0, P_) < cheb(a0, P_))
                            T.add('lost', f'{sub}|{kind}', sp, close=cheb(b0, L) < cheb(a0, L), open=cheb(b0, L) > cheb(a0, L),
                                  closeP=cheb(b0, P_) < cheb(a0, P_))
                if not (y['camp'] or x['gst'] == 2 or (x['lc'] is not None and x['lc'] <= 1)):
                    mem = [m for m in x['M'] if m.get('alive') and 2 <= r['r'] - m['r'] <= 10 and m['d'] >= 9]
                    if mem and p != (y['ex'], y['ey']):
                        m = min(mem, key=lambda q: q['d'])
                        L = (m['x'], m['y']); P_ = (2 * p[0] - L[0], 2 * p[1] - L[1]); e1 = (y['ex'], y['ey'])
                        tt = turn(aid, r)
                        both = any(cheb(s, L) < cheb(p, L) for s in tt.reach()) and any(cheb(s, P_) < cheb(p, P_) for s in tt.reach())
                        for sub in ('old', 'free' if both else 'one_side_blocked'):
                            T.add('hunt', sub, sp, close=cheb(e1, L) < cheb(p, L), closeP=cheb(e1, P_) < cheb(p, P_))
    # ---------------- ECONOMY 4: camp-aware walk home for the gated arrivals of this game.
    arr = {}
    for aid, rr in (ARR[0] or {}).get(game, []):
        r = byr.get(aid, {}).get(rr)
        if not r or not r.get('x'):
            continue
        tt = turn(aid, r)
        f = M.bfs(sorted(M.home), M.block | M.ehome | tt.camp_tiles)
        p = (r['x']['x'], r['x']['y'])
        arr[f'{game}:{aid}:{rr}'] = (M.hf.get(p), f.get(p), bool(tt.steps), r['x']['stn'])
    # ---------------- TEAM 3a (stays in camp range) and 3d (Willow).
    tp = TEAM_DIR / f'{game}.json.gz'
    if tp.exists():
        with gzip.open(tp) as f:
            O = json.load(f)
        teamcampfight(O, byr, turn, idx, T, sp)
    willow(A, M, byr, turn, idx, T, sp)
    return dict(T.c), dict(ex), arr


def teamcampfight(g, byr, turn, idx, T, sp):
    side = g['side']
    team = {q['id']: q['team'] for q in g['roster']}
    camps = g['camps']
    rs = {R['r']: R for R in g['rounds'] if R['cp']}
    for r in sorted(rs):
        R, R1 = rs[r], rs.get(r + 1)
        if not R1:
            continue
        dmg, grp = collections.Counter(), collections.defaultdict(set)
        for cid, tid, hb, ha in R['attacks']:
            if tid >= 0 and team[tid] == side and hb is not None and hb > ha:
                dmg[tid] += hb - ha; grp[tid].add(camps[cid]['group'])
        aw1 = collections.defaultdict(list)
        for cid, _ in R1['cp']['awake']:
            aw1[camps[cid]['group']].append(camps[cid])
        ch1 = {q[OB_ID]: q for q in R1['cp']['ch']}
        turns = {t['id']: t for t in R['turns']}
        for tid in dmg:
            t = turns.get(tid)
            if not t or not t['start'] or not t['start'][4]:
                continue
            gs = [q for q in grp[tid] if aw1.get(q)]
            if not gs or not ch1[tid][OB_ALIVE]:
                continue
            c1 = ch1[tid]
            mem = [m for q in gs for m in aw1[q]]
            inr = lambda q: any(cheb(q, (m['x'], m['y'])) <= CAMP_RANGE[m['type']] for m in mem)
            stay = inr((c1[OB_X], c1[OB_Y]))
            row = byr.get(tid, {}).get(r)
            if not row or not row.get('x'):
                T.add('stepout', 'no_row', sp, stay=stay)
                continue
            tt = turn(tid, row)
            opts = [tt.p] + tt.reach()
            can_leave = any(not inr(q) for q in opts)
            can_stay = any(inr(q) for q in opts)
            kind = ('stunned' if tt.stunned else 'cannot_leave' if not can_leave else 'cannot_stay' if not can_stay
                    else 'outcome' if tt.step_forbidden and inr(tt.p) else 'free')
            T.add('stepout', 'old', sp, stay=stay)
            T.add('stepout', kind, sp, stay=stay)
            if kind == 'free':
                dmin = min(cheb(tt.p, (m['x'], m['y'])) - CAMP_RANGE[m['type']] for m in mem)
                T.add('stepout', f"free|{'ranged' if tt.ranged else 'melee'}", sp, stay=stay)
                T.add('stepout', f'free|edge{dmin}', sp, stay=stay)


def willow(a, M, byr, turn, idx, T, sp):
    home = M.home
    for t in a['turns']:
        m0 = t['start']['me']
        if m0['type'] != 8 or not m0['alive'] or not t.get('end') or not any(q['kind'] == 'Move' for q in t['actions']):
            continue
        m1 = t['end']['me']
        endpos = {q['id']: (q['x'], q['y']) for q in t['end']['allies'] if 'x' in q}
        al = [q for q in t['start']['allies'] if 'x' in q and (q['x'], q['y']) not in home and q['id'] in endpos]
        if len(al) < 2:
            continue

        def label(pos):
            de = {q['id']: cheb(endpos[q['id']], pos) for q in al}
            best = min(de.values())
            lab = [k for k, v in de.items() if v == best]
            return lab[0] if len(lab) == 1 else None
        lab = label((m1['x'], m1['y']))
        if lab is None:
            continue
        p0 = (m0['x'], m0['y'])
        ds = {q['id']: cheb((q['x'], q['y']), p0) for q in al}
        pred = min(al, key=lambda q: (ds[q['id']], q['id']))['id']
        row = byr.get(m0['id'], {}).get(t['round'])
        if not row or not row.get('x'):
            continue
        tt = turn(m0['id'], row)
        labs = [label(q) for q in tt.steps]
        labs = [v for v in labs if v is not None]
        kind = 'free' if len(set(labs)) >= 2 else 'forced'
        plc = sum(v == pred for v in labs) / len(labs) if labs else 0
        for sub in ('old', kind):
            T.add('willow', sub, sp, ok=pred == lab, placebo=plc)


def econ_keys():
    """Gated arrivals of ECONOMY section 4 (six cohorts): game -> [(actor, decision round)]."""
    keys = collections.defaultdict(list); rows = []
    with gzip.open(EPISODES, 'rt') as f:
        for line in f:
            if '"arrival"' not in line[:40]:
                continue
            e = json.loads(line)
            if e['kind'] != 'arrival':
                continue
            x = e['x']
            if x['hp'] / x['maxhp'] <= 0.63 or x['gold'] >= 30:
                keys[e['game']].append((e['actor'], x['r']))
                rows.append(e)
    return dict(keys), rows


def summarise(c):
    out = {}
    for key, cnt in sorted(c.items()):
        rule, sub = key.split('|', 1)
        d = {}
        for sp in ('fit', 'held', 'seventh'):
            n = cnt.get(f'{sp}:n', 0)
            if not n:
                continue
            s = dict(n=n)
            for f in sorted({k.split(':', 1)[1] for k in cnt if k.startswith(sp + ':')} - {'n'}):
                s[f] = round(cnt[f'{sp}:{f}'] / n, 4)
            d[sp] = s
        out.setdefault(rule, {})[sub] = d
    return out


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('out')
    p.add_argument('--jobs', type=int, default=6)
    p.add_argument('--limit', type=int, default=None, help='games per cohort (testing)')
    a = p.parse_args()
    if Path(a.out).exists():
        raise SystemExit(f'refusing to overwrite {a.out}')
    keys, arrivals = econ_keys()
    T = Tally(); arr = {}
    with mp.Pool(a.jobs, initializer=init, initargs=(keys,)) as pool:
        for c in ALL:
            with gzip.open(ROWS / f'{c}-rows-v1.jsonl.gz', 'rt') as fh:
                lines = (l for k, l in enumerate(fh) if a.limit is None or k < a.limit)
                for cg, _, ar in pool.imap_unordered(one, lines, chunksize=1):
                    T.merge(cg)
                    for k, v in ar.items():
                        arr[k] = v
            print('pass', c, flush=True)
    res = dict(definition=__doc__, splits=dict(fit=FIT, held=HELD, seventh=['seventh']),
               note='Every value is a fraction of its n (n is a count of opportunities).',
               audit=summarise(T.c))
    # ECONOMY 4 joined to the episodes.
    W = collections.defaultdict(collections.Counter)
    for e in arrivals:
        sp = 'fit' if e['cohort'] in FIT else 'held'
        v = arr.get(f"{e['game']}:{e['actor']}:{e['x']['r']}")
        kind = e['y']['kind']
        hw = e['x']['home_walk']
        W[sp]['n'] += 1; W[sp]['ok'] += ('walk' if hw <= WALK else 'recall') == kind; W[sp]['base'] += kind == 'recall'
        if v is None:
            W[sp]['unmatched'] += 1
            continue
        hs, hc, step_ok, stn = v
        hc = 99 if hc is None else hc
        W[sp]['matched'] += 1
        W[sp]['camp_longer'] += hc > hw
        W[sp]['camp_crosses_5'] += (hc <= WALK) != (hw <= WALK)
        W[sp]['camp_rule_ok'] += ('walk' if hc <= WALK else 'recall') == kind
        forced = stn or not step_ok or hc >= 99
        W[sp]['forced'] += forced
        W[sp][f'free_n'] += not forced
        W[sp]['free_ok'] += not forced and ('walk' if hc <= WALK else 'recall') == kind
        W[sp]['free_base'] += not forced and kind == 'recall'
        b = 'le4' if hc <= 4 else 'eq5' if hc == 5 else 'ge6'
        W[sp][f'{b}_n'] += 1; W[sp][f'{b}_walk'] += kind == 'walk'
    res['economy_walk_vs_recall'] = {sp: dict(v) for sp, v in W.items()}
    # Tavi buys shards anywhere: does she still go home on the gold gate?
    tv = collections.Counter()
    for e in arrivals:
        if e['y']['kind'] == 'recall' and e['type'] == 'Tavi':
            x = e['x']; healthy = x['hp'] / x['maxhp'] > 0.63
            tv['n'] += 1; tv['healthy_gold'] += healthy and x['gold'] >= 30
    res['economy_tavi_recalls'] = dict(tv)
    write(a.out, res)
    for rule, subs in res['audit'].items():
        for sub, d in subs.items():
            print(rule, sub, json.dumps(d))
    print(json.dumps(res['economy_walk_vs_recall']))


if __name__ == '__main__':
    main()
