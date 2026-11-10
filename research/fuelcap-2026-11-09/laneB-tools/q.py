"""q.py P.json MODE [ARGS]
 fn            : self fuel by real (outermost) function
 file          : inclusive by file
 lines FILE    : inclusive by line in FILE (inline frames)
 under FILE:LINE : break down sites whose chain holds FILE:LINE by their innermost frame
 within FUNC   : lines (any file) of sites whose outermost function contains FUNC
"""
import sys, json, collections, os
D = json.load(open(sys.argv[1])); sites = D['sites']; mode = sys.argv[2]
PF = ('vfprintf.c', 'printf', 'fwrite', '__stdio', 'snprintf', 'fputs', 'puts', 'putc', 'frexp', '__towrite', '__overflow', 'stdout', 'fputc', 'vsnprintf', 'wcrtomb', 'wctomb', 'strlen', 'memchr')
good = [(c, k, fr) for c, k, fr in sites if not any(any(p in f for p in PF) for f, _, _ in fr[:3])]
tot = sum(c for c, _, _ in good); N = int(os.environ.get('N', 40))
def pr(cnt):
    for key, c in cnt.most_common(N): print(f'{100*c/tot:6.2f}%  {key}')
cnt = collections.Counter()
if mode == 'fn':
    for c, k, fr in good: cnt[fr[-1][2][:110] if fr else '?'] += c
elif mode == 'file':
    for c, k, fr in good:
        for f in {f for f, _, _ in fr}: cnt[f] += c
elif mode == 'lines':
    for c, k, fr in good:
        for x in {(f, l) for f, l, _ in fr if f == sys.argv[3]}: cnt[x] += c
elif mode == 'under':
    f0, l0 = sys.argv[3].split(':'); l0 = int(l0)
    for c, k, fr in good:
        idx = [i for i, (f, l, _) in enumerate(fr) if f == f0 and l == l0]
        if idx:
            i = idx[0]; cnt[' <- '.join(f'{f}:{l}' for f, l, _ in fr[max(0, i - 3):i + 1]) + f' k{k}'] += c
elif mode == 'within':
    for c, k, fr in good:
        if fr and sys.argv[3] in fr[-1][2]:
            for x in {(f, l) for f, l, _ in fr}: cnt[x] += c
print('total', tot); pr(cnt)
if mode == 'range':
    f0 = sys.argv[3]; lo, hi = int(sys.argv[4]), int(sys.argv[5]); s = 0; inner = collections.Counter()
    for c, k, fr in good:
        if any(f == f0 and lo <= l <= hi for f, l, _ in fr):
            s += c
            inner[(fr[0][0], fr[0][1], k)] += c
    print(f'range {f0}:{lo}-{hi} {100*s/tot:.2f}%'); 
    for key, c in inner.most_common(N): print(f'   {100*c/tot:6.2f}%  {key}')
if mode == 'outer':
    f0 = sys.argv[3]; lo, hi = int(sys.argv[4]), int(sys.argv[5]); out = collections.Counter()
    for c, k, fr in good:
        m = [l for f, l, _ in fr if f == f0 and lo <= l <= hi]
        if m: out[m[-1]] += c
    for key, c in out.most_common(N): print(f'   {100*c/tot:6.2f}%  {key}')
if mode == 'callers':
    f0, l0 = sys.argv[3].split(':'); l0 = int(l0); out = collections.Counter()
    for c, k, fr in good:
        idx = [i for i, (f, l, _) in enumerate(fr) if f == f0 and l == l0]
        if idx:
            i = idx[0]; out[' -> '.join(f'{f}:{l}' for f, l, _ in fr[i+1:i+4])] += c
    for key, c in out.most_common(N): print(f'   {100*c/tot:6.2f}%  {key}')
