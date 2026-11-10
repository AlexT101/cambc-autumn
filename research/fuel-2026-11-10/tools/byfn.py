"""byfn.py P.json [N] [BOTSRC]: self fuel by innermost source function (file:line of the innermost inline frame mapped to the
enclosing definition found by a column-0 regex), and by outer chain root (the last frame's file:function)."""
import json, collections, os, sys, re, bisect
D = json.load(open(sys.argv[1])); sites = D['sites']; N = int(sys.argv[2]) if len(sys.argv) > 2 else 60
src = sys.argv[3] if len(sys.argv) > 3 else '/home/ubuntu/cambc-autumn/bots/variants/ocf-prof/src'
tot = sum(c for c, _, _ in sites)
outline = {}
defre = re.compile(r'^(?:\[\[[^\]]*\]\]\s*)*(?:template\s*<[^>]*>\s*)?(?:(?:static|inline|constexpr|const|friend|explicit|virtual)\s+)*[A-Za-z_][\w:<>,\s\*&\[\]]*?[\s\*&]([A-Za-z_~][\w:~]*(?:<[^()]*>)?|operator[^\s(]+)\s*\([^;]*$')
def load(f):
    path = os.path.join(src, f)
    if f in outline: return outline[f]
    starts, names = [], []
    if os.path.isfile(path):
        for i, l in enumerate(open(path, errors='replace'), 1):
            if l[:1] in ' \t/#}\n' or l.startswith('namespace') or l.startswith('using') or l.startswith('struct') or l.startswith('class') or l.startswith('enum'): 
                if l.startswith('struct') or l.startswith('class'):
                    m = re.match(r'(?:struct|class)\s+(\w+)', l)
                    if m and '{' in l and ';' not in l.split('{')[0]: starts.append(i); names.append('struct ' + m[1])
                continue
            m = defre.match(l.rstrip())
            if m and not l.rstrip().endswith(';'): starts.append(i); names.append(m[1])
    outline[f] = (starts, names)
    return outline[f]
def fn_of(f, line):
    starts, names = load(f)
    k = bisect.bisect_right(starts, line) - 1
    return names[k] if k >= 0 else '?'
cnt = collections.Counter()
for c, k, fr in sites:
    if not fr: continue
    f, l, _ = fr[0]
    # attribute host-call wrappers and tiny util inlines to their caller's function when innermost is util.h/cambc.h
    j = 0
    while j + 1 < len(fr) and (fr[j][0] in ('util.h', 'cambc.h', 'imports.h') or '/' not in fr[j][0] and not fr[j][0].endswith('.cc')): j += 1
    f, l, _ = fr[j]
    cnt[(f, fn_of(f, l))] += c
print('total', tot)
for key, c in cnt.most_common(N): print(f'{100*c/tot:6.2f}%  {key[0]}: {key[1]}')
