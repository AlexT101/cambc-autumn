"""Inclusive fuel by source line over inline frames: python query.py OUT.json [FILE [LO HI]] (no FILE: by file; N=rows)."""
import sys, json, collections
D = json.load(open(sys.argv[1])); sites = D['sites']
PF = ('vfprintf.c', 'printf', 'fwrite', '__stdio', 'snprintf', 'fputs', 'puts', 'putc', 'frexp', '__towrite', '__overflow', 'stdout', 'fputc', 'vsnprintf', 'wcrtomb', 'wctomb', 'strlen', 'memchr')
def printf_site(fr): return any(any(k in f for k in PF) for f, _ in fr[:3])
good = [(c, k, fr) for c, k, fr in sites if not printf_site(fr)]
tot = sum(c for c, _, _ in good); print('non-printf', tot, 'printf', sum(c for c, _, _ in sites) - tot)
inc = collections.Counter(); fileinc = collections.Counter()
for c, k, fr in good:
    seen = set()
    for f, l in fr:
        if (f, l) not in seen: seen.add((f, l)); inc[(f, l)] += c
    for f in {f for f, _ in fr}: fileinc[f] += c
sel = sys.argv[2] if len(sys.argv) > 2 else None
if not sel:
    for f, c in fileinc.most_common(30): print(f'{100*c/tot:6.2f}%  {f}')
else:
    lo, hi = (int(sys.argv[3]), int(sys.argv[4])) if len(sys.argv) > 4 else (0, 10**9)
    rows = [(c, f, l) for (f, l), c in inc.items() if f == sel and lo <= l <= hi]
    rows.sort(key=lambda x: (-x[0]))
    for c, f, l in rows[:int(__import__('os').environ.get('N', 40))]: print(f'{100*c/tot:6.2f}%  {f}:{l}')
