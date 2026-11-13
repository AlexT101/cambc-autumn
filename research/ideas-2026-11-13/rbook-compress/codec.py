"""The book's stream coder (format 2): an LZMA-style binary range coder over adaptive bit models, with contexts fitted to
how our turns look. src/book/book.cc mirrors Dec and decode_turn exactly; the model's layout (LAYOUT) is written into
book_data.h, so the two cannot drift apart silently.

A body's stream is its turns in round order. A turn: [fp bits] roll, then actions until END.
- kind: 5-bit tree, context (previous kind this turn, the kind that followed that kind the last time).
- MOVE: one of the 8 steps from the current tile (context: the last step), else a general position. A ground cast
  may have moved us (a dash): a learned per-slot flag says which, and a bit corrects it.
- ATTACK and unit casts: one of the last 4 targets, the own tile, or a general position.
- PRIORITY: rank (high 16 bits): same, or one of the last 15, or new. Payload (low 16 bits): four nibbles, each
  same-or-changed, the bits under their own last four values. With the live mask's game seed (maskseed.py) the payload
  is stored plain: its top two bits the age of the round stamp, the rest the unmasked 14 bits.
- general position: dx, dy within 7 of the current tile, else absolute.
"""
import math

KINDS = 17  # 0 = end of turn, 1..16 = action kinds (book.cc's A_*)
END, MOVE, ATTACK, CAST, PRIORITY, RECALL, SUBMIT, BUY, SELL, BUY_CONS, WARD, CANCEL, LOCK, TELEPORT, BLOCKED, RESIGN, USE_CONS = range(17)
POSITIONAL = {MOVE, ATTACK, CAST, SUBMIT, WARD, LOCK, TELEPORT, BLOCKED, USE_CONS}
FIELDS = {BUY: 2, SELL: 2, BUY_CONS: 2, BLOCKED: 1, USE_CONS: 1}  # generic int fields p[, q]
FIELD_CLASS = {BUY: 0, SELL: 1, BUY_CONS: 2, BLOCKED: 3, USE_CONS: 4}
NEAR_CLASS = {MOVE: 0, ATTACK: 1, CAST: 2, SUBMIT: 4, WARD: 5, LOCK: 6, TELEPORT: 7, BLOCKED: 8, USE_CONS: 9}  # CAST: 2 + slot
SHIFT = 4  # adaptation rate of every bit model
RANKS = 15  # recent ranks kept
TARGETS = 4  # recent targets kept

# name -> number of bit models; offsets in this order (book_data.h's `m` namespace).
LAYOUT = [
    ('roll', 1),
    ('kind', KINDS * KINDS * 32),
    ('use_alt', 2),
    ('mdir', 10 * 10 * 16),
    ('near_x', 10 * 16),
    ('near_y', 10 * 16 * 16),
    ('abs_xy', 2 * 256),
    ('slot', 2),
    ('tkind', 3 * 8),
    ('target', 3 * 8 * 8),
    ('field', 5 * 2 * 256),
    ('field_big', 4 * 256),
    ('rank_same', 2),
    ('rank_idx', 16),
    ('rank_new', 2 * 256),
    ('nib_same', 4 * 4),
    ('nib_bit', 16 * 16),
]
OFF = {}
SIZE = 0
for _n, _s in LAYOUT:
    OFF[_n] = SIZE
    SIZE += _s


class Enc:
    """Range encoder. probs: bit models as P(bit = 0) * 2048, all starting at 1024 (or a prior)."""
    def __init__(self, probs=None):
        self.low, self.range, self.cache, self.csize, self.out = 0, 0xFFFFFFFF, 0, 1, bytearray()
        self.p = list(probs) if probs is not None else [1024] * SIZE
        self.cost = None  # tag -> bits, when measuring
        self.tag = ''

    def shift_low(self):
        if self.low < 0xFF000000 or self.low >= 1 << 32:
            carry = self.low >> 32
            temp = self.cache
            while True:
                self.out.append((temp + carry) & 0xFF)
                temp = 0xFF
                self.csize -= 1
                if self.csize == 0:
                    break
            self.cache = (self.low >> 24) & 0xFF
        self.csize += 1
        self.low = (self.low & 0x00FFFFFF) << 8

    def bit(self, i, b):
        p = self.p[i]
        if self.cost is not None:
            self.cost[self.tag] = self.cost.get(self.tag, 0.0) - math.log2((p if not b else 2048 - p) / 2048.0)
        bound = (self.range >> 11) * p
        if not b:
            self.range = bound
            self.p[i] = p + ((2048 - p) >> SHIFT)
        else:
            self.low += bound
            self.range -= bound
            self.p[i] = p - (p >> SHIFT)
        while self.range < 1 << 24:
            self.range = (self.range << 8) & 0xFFFFFFFF
            self.shift_low()

    def direct(self, nbits, v):
        if self.cost is not None:
            self.cost[self.tag] = self.cost.get(self.tag, 0.0) + nbits
        for k in range(nbits - 1, -1, -1):
            self.range >>= 1
            if (v >> k) & 1:
                self.low += self.range
            while self.range < 1 << 24:
                self.range = (self.range << 8) & 0xFFFFFFFF
                self.shift_low()

    def tree(self, base, nbits, v):
        m = 1
        for k in range(nbits - 1, -1, -1):
            b = (v >> k) & 1
            self.bit(base + m, b)
            m = (m << 1) | b

    def finish(self):
        for _ in range(5):
            self.shift_low()
        return bytes(self.out)


class Dec:
    """Range decoder over a bytes object (the Python mirror of book.cc's, for round-trip tests)."""
    def __init__(self, data, probs=None):
        self.d, self.at, self.range, self.code = data, 0, 0xFFFFFFFF, 0
        self.p = list(probs) if probs is not None else [1024] * SIZE
        for _ in range(5):
            self.code = (self.code << 8 | self.next()) & 0xFFFFFFFF

    def next(self):
        b = self.d[self.at] if self.at < len(self.d) else 0
        self.at += 1
        return b

    def bit(self, i):
        p = self.p[i]
        bound = (self.range >> 11) * p
        if self.code < bound:
            self.range = bound
            self.p[i] = p + ((2048 - p) >> SHIFT)
            b = 0
        else:
            self.range -= bound
            self.code -= bound
            self.p[i] = p - (p >> SHIFT)
            b = 1
        while self.range < 1 << 24:
            self.range = (self.range << 8) & 0xFFFFFFFF
            self.code = (self.code << 8 | self.next()) & 0xFFFFFFFF
        return b

    def direct(self, nbits):
        v = 0
        for _ in range(nbits):
            self.range >>= 1
            b = 0
            if self.code >= self.range:
                self.code -= self.range
                b = 1
            v = v << 1 | b
            while self.range < 1 << 24:
                self.range = (self.range << 8) & 0xFFFFFFFF
                self.code = (self.code << 8 | self.next()) & 0xFFFFFFFF
        return v

    def tree(self, base, nbits):
        m = 1
        for _ in range(nbits):
            m = m << 1 | self.bit(base + m)
        return m - (1 << nbits)


def zig(v):
    return ((v << 1) ^ (v >> 31)) & 0xFFFFFFFF


def unzig(z):
    v = (z >> 1) ^ (0xFFFFFFFF if z & 1 else 0)
    return v - (1 << 32) if v >> 31 else v


class State:
    """What both sides track along a stream."""
    def __init__(self):
        self.cx = self.cy = -1000  # the current tile, as far as the stream tells
        self.alt = None  # the other tile we may stand on after a ground cast: (x, y, slot)
        self.dash = [False, False]  # a ground cast of this slot moves us
        self.last_dir = 9
        self.follow = [0] * KINDS  # the kind that followed each kind the last time
        self.targets = []
        self.rank, self.ranks, self.rank_changed = 0, [], 0
        self.lo = 0
        self.nib_hist = [0] * 4  # each nibble's last two changed flags
        self.bit_hist = [0] * 16  # each payload bit's last four values


def sgn32(v):
    v &= 0xFFFFFFFF
    return v - (1 << 32) if v >> 31 else v


def near_fits(dx, dy):
    return -7 <= dx <= 7 and -7 <= dy <= 7


def enc_pos(e, s, cls, x, y):
    """A general position, from the current tile."""
    dx, dy = x - s.cx, y - s.cy
    if near_fits(dx, dy):
        e.tree(OFF['near_x'] + cls * 16, 4, dx + 7)
        e.tree(OFF['near_y'] + (cls * 16 + dx + 7) * 16, 4, dy + 7)
    else:
        assert -1 <= x <= 254 and -1 <= y <= 254, (x, y)
        e.tree(OFF['near_x'] + cls * 16, 4, 15)
        e.tree(OFF['abs_xy'], 8, x + 1)
        e.tree(OFF['abs_xy'] + 256, 8, y + 1)


def dec_pos(d, s, cls):
    sx = d.tree(OFF['near_x'] + cls * 16, 4)
    if sx == 15:
        x = d.tree(OFF['abs_xy'], 8) - 1
        y = d.tree(OFF['abs_xy'] + 256, 8) - 1
        return x, y
    sy = d.tree(OFF['near_y'] + (cls * 16 + sx) * 16, 4)
    return s.cx + sx - 7, s.cy + sy - 7


def enc_target(e, s, cls, x, y, tkind):
    """An attack's or a cast's target tile and kind. cls: 0 attack, 1 + slot a cast."""
    assert 0 <= tkind < 8, tkind
    e.tree(OFF['tkind'] + cls * 8, 3, tkind)
    base = OFF['target'] + (cls * 8 + tkind) * 8
    t = (x, y)
    if tkind != 0 and t in s.targets:
        i = s.targets.index(t)
        e.tree(base, 3, i)
        s.targets.pop(i)
        s.targets.insert(0, t)
        return
    if x == s.cx and y == s.cy:
        e.tree(base, 3, 4)
        return
    e.tree(base, 3, 5)
    enc_pos(e, s, NEAR_CLASS[ATTACK] if cls == 0 else NEAR_CLASS[CAST] + cls - 1, x, y)
    if tkind != 0:
        s.targets.insert(0, t)
        del s.targets[TARGETS:]


def dec_target(d, s, cls):
    tkind = d.tree(OFF['tkind'] + cls * 8, 3)
    sym = d.tree(OFF['target'] + (cls * 8 + tkind) * 8, 3)
    if sym < 4:
        if sym >= len(s.targets):
            return -1, -1, tkind  # a damaged stream
        t = s.targets.pop(sym)
        s.targets.insert(0, t)
        return t[0], t[1], tkind
    if sym == 4:
        return s.cx, s.cy, tkind
    x, y = dec_pos(d, s, NEAR_CLASS[ATTACK] if cls == 0 else NEAR_CLASS[CAST] + cls - 1)
    if tkind != 0:
        s.targets.insert(0, (x, y))
        del s.targets[TARGETS:]
    return x, y, tkind


def enc_int(e, cls, field, v):
    z = zig(v)
    base = OFF['field'] + (cls * 2 + field) * 256
    if z < 255:
        e.tree(base, 8, z)
    else:
        e.tree(base, 8, 255)
        for k in range(4):
            e.tree(OFF['field_big'] + k * 256, 8, (z >> (8 * k)) & 0xFF)


def dec_int(d, cls, field):
    z = d.tree(OFF['field'] + (cls * 2 + field) * 256, 8)
    if z == 255:
        z = 0
        for k in range(4):
            z |= d.tree(OFF['field_big'] + k * 256, 8) << (8 * k)
    return unzig(z)


def enc_priority(e, s, v, rnd, mask, body):
    v &= 0xFFFFFFFF
    hi, lo = v >> 16, v & 0xFFFF
    if mask is not None:
        age = (mask.tag_of(rnd) - (lo >> 14)) & 3
        lo = age << 14 | ((lo & 0x3FFF) ^ mask.mask_of(rnd - age, body))
    e.tag = 'rank'
    if hi == s.rank:
        e.bit(OFF['rank_same'] + s.rank_changed, 0)
        s.rank_changed = 0
    else:
        e.bit(OFF['rank_same'] + s.rank_changed, 1)
        s.rank_changed = 1
        if hi in s.ranks:
            i = s.ranks.index(hi)
            e.tree(OFF['rank_idx'], 4, i)
            s.ranks.pop(i)
        else:
            e.tree(OFF['rank_idx'], 4, 15)
            e.tree(OFF['rank_new'], 8, hi >> 8)
            e.tree(OFF['rank_new'] + 256, 8, hi & 0xFF)
        s.ranks.insert(0, s.rank)  # the list holds the ranks before this one, latest first
        del s.ranks[RANKS:]
        s.rank = hi
    e.tag = 'payload'
    for n in range(3, -1, -1):
        old, new = (s.lo >> (4 * n)) & 15, (lo >> (4 * n)) & 15
        changed = old != new
        e.bit(OFF['nib_same'] + n * 4 + s.nib_hist[n], changed)
        s.nib_hist[n] = (s.nib_hist[n] << 1 | changed) & 3
        for k in range(3, -1, -1):
            i = 4 * n + k
            b = (new >> k) & 1
            if changed:
                e.bit(OFF['nib_bit'] + i * 16 + s.bit_hist[i], b)
            s.bit_hist[i] = (s.bit_hist[i] << 1 | b) & 15
    s.lo = lo


def dec_priority(d, s, rnd, mask, body):
    if d.bit(OFF['rank_same'] + s.rank_changed):
        s.rank_changed = 1
        i = d.tree(OFF['rank_idx'], 4)
        if i < 15:
            hi = s.ranks.pop(i) if i < len(s.ranks) else 0
        else:
            hi = d.tree(OFF['rank_new'], 8) << 8
            hi |= d.tree(OFF['rank_new'] + 256, 8)
        s.ranks.insert(0, s.rank)
        del s.ranks[RANKS:]
        s.rank = hi
    else:
        s.rank_changed = 0
    lo = 0
    for n in range(3, -1, -1):
        old = (s.lo >> (4 * n)) & 15
        changed = d.bit(OFF['nib_same'] + n * 4 + s.nib_hist[n])
        s.nib_hist[n] = (s.nib_hist[n] << 1 | changed) & 3
        new = 0
        for k in range(3, -1, -1):
            i = 4 * n + k
            b = d.bit(OFF['nib_bit'] + i * 16 + s.bit_hist[i]) if changed else (old >> k) & 1
            s.bit_hist[i] = (s.bit_hist[i] << 1 | b) & 15
            new |= b << k
        lo |= new << (4 * n)
    s.lo = lo
    if mask is not None:
        w = rnd - (lo >> 14)
        lo = mask.tag_of(w) << 14 | ((lo & 0x3FFF) ^ mask.mask_of(w, body))
    return sgn32(s.rank << 16 | lo)


def enc_turn(e, s, roll, acts, rnd, mask, body):
    e.tag = 'roll'
    e.bit(OFF['roll'], roll)
    prev = 0
    for a in acts:
        kind, x, y, p, q = a
        e.tag = 'kind'
        e.tree(OFF['kind'] + (prev * KINDS + s.follow[prev]) * 32, 5, kind)
        s.follow[prev] = kind
        prev = kind
        e.tag = 'k%d' % kind
        if kind == MOVE:
            use = 0
            bx, by = s.cx, s.cy
            if s.alt is not None:
                ax, ay, slot = s.alt
                # The step from the tile we believe we stand on, unless only the other one is a step away.
                step = lambda u, v: -1 <= x - u <= 1 and -1 <= y - v <= 1
                use = 1 if step(ax, ay) and not step(bx, by) else 0
                e.bit(OFF['use_alt'] + slot, use)
                if use:
                    bx, by = ax, ay
                    s.dash[slot] = not s.dash[slot]
            dx, dy = x - bx, y - by
            sym = (dx + 1) * 3 + (dy + 1) if -1 <= dx <= 1 and -1 <= dy <= 1 else 9
            e.tree(OFF['mdir'] + s.last_dir * 16, 4, sym)
            s.cx, s.cy = bx, by
            if sym == 9:
                enc_pos(e, s, NEAR_CLASS[MOVE], x, y)
            s.last_dir = sym
            s.cx, s.cy, s.alt = x, y, None
        elif kind == ATTACK:
            assert q == 0
            enc_target(e, s, 0, x, y, p)
        elif kind == CAST:
            assert p in (0, 1), a
            e.bit(OFF['slot'], p)
            enc_target(e, s, 1 + p, x, y, q)
            if q == 0:  # a ground cast: a dash moves us there
                if s.dash[p]:
                    s.alt = (s.cx, s.cy, p)
                    s.cx, s.cy = x, y
                else:
                    s.alt = (x, y, p)
        elif kind == PRIORITY:
            assert x == 0 and y == 0 and q == 0
            enc_priority(e, s, p, rnd, mask, body)
        elif kind in POSITIONAL:
            enc_pos(e, s, NEAR_CLASS[kind], x, y)
        else:
            assert x == 0 and y == 0, a
        nf = FIELDS.get(kind, 0)
        if nf >= 1:
            enc_int(e, FIELD_CLASS[kind], 0, p)
        if nf >= 2:
            enc_int(e, FIELD_CLASS[kind], 1, q)
        elif kind not in (ATTACK, CAST, PRIORITY):
            assert q == 0 and (nf or p == 0), a
    e.tag = 'kind'
    e.tree(OFF['kind'] + (prev * KINDS + s.follow[prev]) * 32, 5, END)
    s.follow[prev] = END


def dec_turn(d, s, rnd, mask, body):
    roll = d.bit(OFF['roll'])
    acts = []
    prev = 0
    while True:
        kind = d.tree(OFF['kind'] + (prev * KINDS + s.follow[prev]) * 32, 5)
        if kind >= KINDS:
            kind = END  # a damaged stream
        s.follow[prev] = kind
        prev = kind
        if kind == END:
            break
        x = y = p = q = 0
        if kind == MOVE:
            bx, by = s.cx, s.cy
            if s.alt is not None:
                ax, ay, slot = s.alt
                if d.bit(OFF['use_alt'] + slot):
                    bx, by = ax, ay
                    s.dash[slot] = not s.dash[slot]
            sym = d.tree(OFF['mdir'] + s.last_dir * 16, 4)
            s.cx, s.cy = bx, by
            if sym < 9:
                x, y = bx + sym // 3 - 1, by + sym % 3 - 1
            else:
                sym = 9
                x, y = dec_pos(d, s, NEAR_CLASS[MOVE])
            s.last_dir = sym
            s.cx, s.cy, s.alt = x, y, None
        elif kind == ATTACK:
            x, y, p = dec_target(d, s, 0)
        elif kind == CAST:
            p = d.bit(OFF['slot'])
            x, y, q = dec_target(d, s, 1 + p)
            if q == 0:
                if s.dash[p]:
                    s.alt = (s.cx, s.cy, p)
                    s.cx, s.cy = x, y
                else:
                    s.alt = (x, y, p)
        elif kind == PRIORITY:
            p = dec_priority(d, s, rnd, mask, body)
        elif kind in POSITIONAL:
            x, y = dec_pos(d, s, NEAR_CLASS[kind])
        nf = FIELDS.get(kind, 0)
        if nf >= 1:
            p = dec_int(d, FIELD_CLASS[kind], 0)
        if nf >= 2:
            q = dec_int(d, FIELD_CLASS[kind], 1)
        acts.append([kind, x, y, p, q])
    return roll, acts


def enc_body(turns, mask=None, body=0, fp=None, fp_bits=0, cost=None, probs=None):
    """turns: [[roll, [[kind, x, y, p, q], ...]], ...] from round 1. fp: a hex digit per turn (play mode)."""
    e, s = Enc(probs), State()
    e.cost = cost
    for i, (roll, acts) in enumerate(turns):
        if fp_bits:
            e.tag = 'fp'
            e.direct(fp_bits, int(fp[i], 16) & ((1 << fp_bits) - 1))
        enc_turn(e, s, roll, acts, i + 1, mask, body)
    return e.finish()


def dec_body(data, n_turns, mask=None, body=0, fp_bits=0, probs=None):
    d, s = Dec(data, probs), State()
    turns, fps = [], []
    for i in range(n_turns):
        if fp_bits:
            fps.append(d.direct(fp_bits))
        roll, acts = dec_turn(d, s, i + 1, mask, body)
        turns.append([roll, acts])
    return turns, fps
