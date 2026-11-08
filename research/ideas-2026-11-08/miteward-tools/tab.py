"""Tiny group-by helpers (no pandas here)."""
import collections, pickle


def load(p):
    return pickle.load(open(p, 'rb'))


def rate(rows, key, val, top=40, minn=1):
    s = collections.defaultdict(lambda: [0, 0])
    for r in rows:
        k = key(r); s[k][0] += 1; s[k][1] += bool(val(r))
    out = sorted(s.items(), key=lambda kv: (str(type(kv[0])), kv[0]))
    for k, (n, v) in out[:top]:
        if n >= minn: print(f'  {str(k):>28} n={n:>8} {100 * v / n:6.2f}%')


def count(rows, key, top=30):
    c = collections.Counter(key(r) for r in rows); n = sum(c.values())
    for k, v in c.most_common(top): print(f'  {str(k):>28} {v:>8} {100 * v / n:6.2f}%')


def bucket(x, edges):
    for e in edges:
        if x <= e: return f'<={e}'
    return f'>{edges[-1]}'
