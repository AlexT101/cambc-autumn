"""Where the current coder's bits go: per component, over a book's entries (ideal -log2 p of the adaptive models).
    py measure0.py BOOK.jsonl FP.json [N]"""
import json, math, sys, collections
sys.path.insert(0, '/home/ubuntu/cambc-autumn/research/ideas-2026-11-13/rbook')
import build_book as bb

cost = collections.Counter()
cnt = collections.Counter()
class CE(bb.Enc):
    tag = 'x'
    def bit(self, probs, i, b):
        p = probs[i] / 2048.0
        cost[self.tag] += -math.log2(p if not b else 1 - p)
        if not b: probs[i] += (2048 - probs[i]) >> 5
        else: probs[i] -= probs[i] >> 5
    def finish(self): return b''

def enc_body(turns):
    e, m = CE(), bb.Model()
    cx = cy = -1000
    prev_pr = 0
    for roll, acts in turns:
        e.tag = 'roll'; e.bit(m.roll, 0, roll)
        prev = 0
        for a in acts:
            kind, x, y, p, q = a
            e.tag = 'kind'; e.tree(m.kind, prev * 32, 5, kind)
            cnt[kind] += 1
            if kind in bb.POSITIONAL:
                e.tag = 'pos%d' % kind
                dx, dy = x - cx, y - cy
                if -31 <= dx <= 31 and -31 <= dy <= 31:
                    e.tree(m.pos, (kind * 2) * 64, 6, dx + 31)
                    e.tree(m.pos, (kind * 2 + 1) * 64, 6, dy + 31)
                else:
                    e.tree(m.pos, (kind * 2) * 64, 6, 63)
                    e.tree(m.absxy, 0, 8, x + 1)
                    e.tree(m.absxy, 256, 8, y + 1)
                if kind == bb.MOVE: cx, cy = x, y
            if kind == bb.PRIORITY:
                v = p & 0xFFFFFFFF
                if (v >> 16) == (prev_pr >> 16):
                    e.tag = 'pr_same'; e.bit(m.pr_same, 0, 0)
                    e.tag = 'pr_lo'
                    e.tree(m.pr, 0, 8, (v >> 8) & 0xFF)
                    e.tree(m.pr, 256, 8, v & 0xFF)
                else:
                    e.tag = 'pr_same'; e.bit(m.pr_same, 0, 1)
                    e.tag = 'pr_full'; cnt['pr_full'] += 1
                    for k in range(4):
                        e.tree(m.prfull, k * 256, 8, (v >> (8 * k)) & 0xFF)
                prev_pr = v
            nf = bb.FIELDS.get(kind, 0)
            e.tag = 'f%d' % kind
            if nf >= 1: bb.enc_int(e, m, kind, 0, p)
            if nf >= 2: bb.enc_int(e, m, kind, 1, q)
            prev = kind
        e.tag = 'kind'; e.tree(m.kind, prev * 32, 5, 0)

n = int(sys.argv[3]) if len(sys.argv) > 3 else 10**9
turns = 0; ents = 0; real = 0
for line in open(sys.argv[1]):
    r = json.loads(line)
    for b in r['ours']['bodies']:
        enc_body(b['turns']); turns += len(b['turns'])
        real += len(bb.enc_body(b['turns'])) if ents < 5 else 0
    ents += 1
    if ents >= n: break
tot = sum(cost.values())
print(f'{ents} entries, {turns} champion-turns, {tot/8/ents:.0f} B/entry streams + {turns/2/ents:.0f} B/entry fp; {tot/turns:.2f} bits/turn')
for k, v in sorted(cost.items(), key=lambda kv: -kv[1]):
    print(f'  {k:8s} {v/8/ents:8.0f} B/entry  {v/turns:6.2f} bits/turn  {100*v/tot:5.1f}%')
names = {1:'MOVE',2:'ATTACK',3:'CAST',4:'PRIORITY',5:'RECALL',6:'SUBMIT',7:'BUY',8:'SELL',9:'BUY_CONS',10:'WARD',11:'CANCEL',12:'LOCK',13:'TELEPORT',14:'BLOCKED',15:'RESIGN',16:'USE_CONS'}
for k, v in sorted(cnt.items(), key=lambda kv: -kv[1]):
    print(f'  count {names.get(k,k)}: {v} ({v/turns:.3f}/turn)')
