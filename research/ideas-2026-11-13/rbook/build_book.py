"""Encodes book entries (extract.mjs output) into the bot's generated header src/book/book_data.h.
    py build_book.py ENTRIES.jsonl OUT_HEADER --team ours|opp --mode play|record|puppet [--fp FP.json] [--keys K1,K2]
                     [--cells CELLS] [--cap N]
--team: which team's turns the bot replays (opp = a puppet of the opponent, for local reruns).
--fp: fingerprints from a record run (key -> body -> hex nibbles); required for --mode play.
The strength dial (which cells the book plays; the bot plays the rest itself):
--cells: only these cells, a file of lines "MAP SIDE" (e.g. "02cuts a") or a comma list "02cuts:a,05abacus:b".
--cap N: at most N entries, the smallest first (most cells per byte); ties by key. Applied after --cells.
The cells kept are printed to stderr as "cell MAP SIDE KEY BYTES".
The coder must match src/book/book.cc exactly: an LZMA-style binary range coder over adaptive bit models."""
import argparse, base64, json, re, sys

KINDS = 17  # 0 = end of turn, 1..16 = action kinds (book.cc's A_*)
MOVE, ATTACK, CAST, PRIORITY, RECALL, SUBMIT, BUY, SELL, BUY_CONS, WARD, CANCEL, LOCK, TELEPORT, BLOCKED, RESIGN, USE_CONS = range(1, 17)
POSITIONAL = {MOVE, ATTACK, CAST, SUBMIT, WARD, LOCK, TELEPORT, BLOCKED, USE_CONS}
FIELDS = {ATTACK: 1, CAST: 2, BUY: 2, SELL: 2, BUY_CONS: 2, BLOCKED: 1, USE_CONS: 1}  # generic int fields p[, q]


class Enc:
    def __init__(self):
        self.low, self.range, self.cache, self.csize, self.out = 0, 0xFFFFFFFF, 0, 1, bytearray()

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

    def bit(self, probs, i, b):
        p = probs[i]
        bound = (self.range >> 11) * p
        if not b:
            self.range = bound
            probs[i] = p + ((2048 - p) >> 5)
        else:
            self.low += bound
            self.range -= bound
            probs[i] = p - (p >> 5)
        while self.range < 1 << 24:
            self.range = (self.range << 8) & 0xFFFFFFFF
            self.shift_low()

    def tree(self, probs, base, nbits, v):
        m = 1
        for k in range(nbits - 1, -1, -1):
            b = (v >> k) & 1
            self.bit(probs, base + m, b)
            m = (m << 1) | b

    def finish(self):
        for _ in range(5):
            self.shift_low()
        return bytes(self.out)


class Model:
    """Same layout as book.cc's Model."""
    def __init__(self):
        self.roll = [1024]
        self.kind = [1024] * (KINDS * 32)
        self.pos = [1024] * (KINDS * 2 * 64)
        self.absxy = [1024] * (2 * 256)
        self.f = [1024] * (KINDS * 2 * 256)
        self.fbig = [1024] * (KINDS * 2 * 4 * 256)
        self.pr_same = [1024]
        self.pr = [1024] * (2 * 256)
        self.prfull = [1024] * (4 * 256)


def zig(v):
    return (v << 1) ^ (v >> 31) if v >= 0 else ((-v) << 1) - 1


def enc_int(e, m, kind, field, v):
    z = zig(v) & 0xFFFFFFFF
    base = (kind * 2 + field) * 256
    if z < 255:
        e.tree(m.f, base, 8, z)
    else:
        e.tree(m.f, base, 8, 255)
        for k in range(4):
            e.tree(m.fbig, ((kind * 2 + field) * 4 + k) * 256, 8, (z >> (8 * k)) & 0xFF)


def enc_body(turns):
    e, m = Enc(), Model()
    cx = cy = -1000
    prev_pr = 0
    for roll, acts in turns:
        e.bit(m.roll, 0, roll)
        prev = 0
        for a in acts:
            kind, x, y, p, q = a
            e.tree(m.kind, prev * 32, 5, kind)
            if kind in POSITIONAL:
                dx, dy = x - cx, y - cy
                if -31 <= dx <= 31 and -31 <= dy <= 31:
                    e.tree(m.pos, (kind * 2) * 64, 6, dx + 31)
                    e.tree(m.pos, (kind * 2 + 1) * 64, 6, dy + 31)
                else:
                    e.tree(m.pos, (kind * 2) * 64, 6, 63)
                    assert -1 <= x <= 254 and -1 <= y <= 254, a
                    e.tree(m.absxy, 0, 8, x + 1)
                    e.tree(m.absxy, 256, 8, y + 1)
                if kind == MOVE:
                    cx, cy = x, y
            if kind == PRIORITY:
                v = p & 0xFFFFFFFF
                if (v >> 16) == (prev_pr >> 16):
                    e.bit(m.pr_same, 0, 0)
                    e.tree(m.pr, 0, 8, (v >> 8) & 0xFF)
                    e.tree(m.pr, 256, 8, v & 0xFF)
                else:
                    e.bit(m.pr_same, 0, 1)
                    for k in range(4):
                        e.tree(m.prfull, k * 256, 8, (v >> (8 * k)) & 0xFF)
                prev_pr = v
            nf = FIELDS.get(kind, 0)
            if nf >= 1:
                enc_int(e, m, kind, 0, p)
            if nf >= 2:
                enc_int(e, m, kind, 1, q)
            prev = kind
        e.tree(m.kind, prev * 32, 5, 0)
    return e.finish()


def cell_of(r):
    """(map, our side) from rbuild.py's keys "MAP-SIDE-vN-..."; other keys stand for their own cell."""
    m = re.match(r'^(.+)-([ab])-v\d+-', r['key'])
    return (m.group(1), m.group(2)) if m and m.group(2) == r['side'] else (r['key'], r['side'])


def read_cells(arg):
    try:
        text = open(arg).read()
        pairs = [l.split()[:2] for l in text.splitlines() if l.strip() and not l.startswith('#')]
    except FileNotFoundError:
        pairs = [x.split(':') for x in arg.split(',') if x]
    return {(m, s) for m, s in pairs}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('entries')
    ap.add_argument('out')
    ap.add_argument('--team', choices=['ours', 'opp'], default='ours')
    ap.add_argument('--mode', choices=['play', 'record', 'puppet'], default='play')
    ap.add_argument('--fp')
    ap.add_argument('--keys')
    ap.add_argument('--cells')
    ap.add_argument('--cap', type=int)
    ap.add_argument('--force', help="play mode: keys (comma list or file) whose picks the draft forces: entries whose picks the "
                    "host's own draft does not make (another version's). Record and puppet modes force every entry.")
    a = ap.parse_args()
    keys = set(a.keys.split(',')) if a.keys else None
    cells = read_cells(a.cells) if a.cells else None
    force_keys = set()
    if a.force:
        try:
            force_keys = {l.split()[0] for l in open(a.force) if l.strip() and not l.startswith('#')}
        except FileNotFoundError:
            force_keys = set(a.force.split(','))
    fps = json.load(open(a.fp)) if a.fp else {}
    blob = bytearray()
    rows = []
    stats = []
    chosen = []
    for line in open(a.entries):
        r = json.loads(line)
        if keys and r['key'] not in keys:
            continue
        if cells is not None and cell_of(r) not in cells:
            continue
        chosen.append(r)
    # One entry per map, side and picks: two opponents that pick alike on a cell keep the first input's entry, which
    # the other then leaves at its first difference.
    seen, kept = {}, []
    for r in chosen:
        k = (r['map_id'], r['side'], tuple(r['ours']['picks']), tuple(r['opp']['picks']))
        if k in seen:
            print(f'dropped {r["key"]}: same map, side and picks as {seen[k]}', file=sys.stderr)
            continue
        seen[k] = r['key']
        kept.append(r)
    chosen = kept
    if a.cap is not None:
        size = {r['key']: sum(len(enc_body(b['turns'])) for b in r[a.team]['bodies']) for r in chosen}
        chosen = sorted(sorted(chosen, key=lambda r: (size[r['key']], r['key']))[:a.cap], key=lambda r: r['key'])
    for r in chosen:
        me = r[a.team]
        other = r['opp' if a.team == 'ours' else 'ours']
        side = r['side'] if a.team == 'ours' else ('b' if r['side'] == 'a' else 'a')
        if a.mode == 'play' and r['key'] not in fps:
            print('no fingerprints for', r['key'], file=sys.stderr)
            continue
        offs, lens, fpo = [], [], []
        for k, b in enumerate(me['bodies']):
            s = enc_body(b['turns'])
            offs.append(len(blob)); lens.append(len(s)); blob += s
            if a.mode == 'play':
                nib = fps[r['key']][k]
                assert len(nib) >= len(b['turns']), (r['key'], k, len(nib), len(b['turns']))
                raw = bytearray((len(nib) + 1) // 2)
                for i, ch in enumerate(nib):
                    raw[i // 2] |= int(ch, 16) << (4 * (i & 1))
                fpo.append(len(blob)); blob += raw
            else:
                fpo.append(0xFFFFFFFF)
        stats.append(sum(lens))
        print('cell', *cell_of(r), r['key'], sum(lens), file=sys.stderr)
        rows.append(dict(map=int(r['map_id'], 16), side=0 if side == 'a' else 1, w=r['width'], h=r['height'], counts=r['counts'], layout=int(r['layout'], 16), force=r['key'] in force_keys,
                         ours=me['picks'], opp=other['picks'], last=len(me['bodies'][0]['turns']), offs=offs, lens=lens, fps=fpo, key=r['key']))
    rows.sort(key=lambda r: (r['side'], r['w'], r['h'], r['map']))  # book.cc finds a map's size by binary search
    b64 = base64.b64encode(bytes(blob)).decode()
    mode = {'play': 0, 'record': 1, 'puppet': 2}[a.mode]
    with open(a.out, 'w') as f:
        f.write('// Generated by research/ideas-2026-11-13/rbook/build_book.py: do not edit.\n#pragma once\n#include <cstdint>\n')
        f.write('namespace book_data {\n')
        f.write(f'inline constexpr int mode = {mode}; // 0 play, 1 record, 2 puppet\n')
        f.write(f'inline constexpr bool force_draft = {"true" if force_keys or a.mode != 'play' else "false"}; // the draft plays the entries\' picks\n')
        f.write(f'inline constexpr int entry_count = {len(rows)};\n')
        f.write('struct Entry { std::uint64_t map; std::uint8_t side, w, h, n_ours, n_opp; std::int8_t ours[5], opp[5]; std::uint8_t bodies; std::uint16_t last; std::uint32_t off[6], len[6], fp[6]; std::uint16_t counts[4]; std::uint64_t layout; bool force; };\n')
        f.write(f'inline constexpr Entry entries[{max(1, len(rows))}] = {{\n')
        for r in rows:
            pad = lambda l, n: (list(l) + [-1] * n)[:n]
            pad6 = lambda l, v: (list(l) + [v] * 6)[:6]
            f.write(f'  {{0x{r["map"]:016x}ull, {r["side"]}, {r["w"]}, {r["h"]}, {len(r["ours"])}, {len(r["opp"])}, '
                    f'{{{",".join(map(str, pad(r["ours"], 5)))}}}, {{{",".join(map(str, pad(r["opp"], 5)))}}}, {len(r["offs"])}, {r["last"]}, '
                    f'{{{",".join(map(str, pad6(r["offs"], 0)))}}}, {{{",".join(map(str, pad6(r["lens"], 0)))}}}, {{{",".join(f"{x}u" for x in pad6(r["fps"], 0xFFFFFFFF))}}}, {{{",".join(map(str, r["counts"]))}}}, 0x{r["layout"]:016x}ull, {"true" if r["force"] else "false"}}}, // {r["key"]}\n')
        if not rows:
            f.write('  {}\n')
        f.write('};\n')
        f.write(f'inline constexpr std::uint32_t blob_bytes = {len(blob)};\n')
        f.write('inline constexpr char blob[] =\n')
        for i in range(0, len(b64), 4096):
            f.write(f'"{b64[i:i + 4096]}"\n')
        if not b64:
            f.write('""\n')
        f.write(';\n}\n')
    print(f'{len(rows)} entries, streams {sum(stats)} bytes, blob {len(blob)} bytes, base64 {len(b64)}', file=sys.stderr)


if __name__ == '__main__':
    main()
