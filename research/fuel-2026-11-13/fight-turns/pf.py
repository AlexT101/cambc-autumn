"""pf.py P.json [N] [SRC] [MODE]: self fuel by source function, found from each frame's file:line (the symboliser's
names for outermost frames are unreliable). MODE outer (default): the real function holding the site; inner: innermost
non-utility frame; pair: (outer, inner) pairs; lines=FN: by outer line within outer function FN."""
import json, collections, os, sys, re, bisect
D = json.load(open(sys.argv[1])); sites = D['sites']; N = int(sys.argv[2]) if len(sys.argv) > 2 else 60
src = sys.argv[3] if len(sys.argv) > 3 else '/home/ubuntu/cambc-autumn/bots/variants/chy-525f/src'
mode = sys.argv[4] if len(sys.argv) > 4 else 'outer'
outline = {}
defre = re.compile(r'^(?:\[\[[^\]]*\]\]\s*)*(?:template\s*<[^>]*>\s*)?(?:(?:static|inline|constexpr|const|friend|explicit|virtual)\s+)*[A-Za-z_][\w:<>,\s\*&\[\]]*?[\s\*&]([A-Za-z_~][\w:~]*(?:<[^()]*>)?|operator[^\s(]+)\s*\([^;]*$')
def load(f):
    path = os.path.join(src, f)
    if f in outline: return outline[f]
    starts, names = [], []
    if os.path.isfile(path):
        for i, l in enumerate(open(path, errors='replace'), 1):
            if l[:1] in ' \t/#}\n' or l.startswith(('namespace', 'using', 'struct', 'class', 'enum')):
                if l.startswith(('struct', 'class')):
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
SKIP = ('draft/',)
SKIPFN = ('StaticMap::build', 'init_beliefs', 'measure_economy', 'measure_facts', 'decode_steps', 'PlanFacts')
cnt = collections.Counter(); tot = 0
for c, k, fr in sites:
    if not fr: continue
    f, l, _ = fr[-1]; ofn = fn_of(f, l)
    if f.startswith(SKIP) or ofn.startswith(SKIPFN): continue
    tot += c
    if mode == 'outer': cnt[(f, ofn)] += c
    elif mode == 'inner':
        j = 0
        while j + 1 < len(fr) and (fr[j][0] in ('util.h', 'cambc.h', 'imports.h') or ('/' not in fr[j][0] and not fr[j][0].endswith('.cc'))): j += 1
        cnt[(fr[j][0], fn_of(fr[j][0], fr[j][1]))] += c
    elif mode == 'host':
        if k == 2: cnt[(f, ofn, fr[0][2][:60])] += c
    elif mode.startswith('lines='):
        if ofn == mode[6:]: cnt[(f, l, k if len(fr) == 1 else fr[0][2][:50])] += c
    elif mode.startswith('ol='):
        if ofn == mode[3:]: cnt[(f, l)] += c
print('kept', tot)
for key, c in cnt.most_common(N): print(f'{100*c/tot:6.2f}%  {c:>11}  {key}')
if mode == 'toplines':
    cnt = collections.Counter()
    for c, k, fr in sites:
        if not fr: continue
        f, l, _ = fr[-1]; ofn = fn_of(f, l)
        if f.startswith(SKIP) or ofn.startswith(SKIPFN): continue
        cnt[(f, l, ofn)] += c
    for key, c in cnt.most_common(N): print(f'{100*c/tot:6.2f}%  {c:>11}  {key}')
