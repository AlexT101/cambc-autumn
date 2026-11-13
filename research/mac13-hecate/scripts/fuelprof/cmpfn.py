"""cmpfn.py A.json ASRC B.json BSRC [N]: self fuel by source function (byfn's rule), A vs B, absolute and per-turn difference."""
import sys, json, collections, re, bisect, os
sys.argv_save = sys.argv[:]
def prof(path, src):
    D = json.load(open(path)); sites = D['sites']
    outline = {}
    defre = re.compile(r'^(?:\[\[[^\]]*\]\]\s*)*(?:template\s*<[^>]*>\s*)?(?:(?:static|inline|constexpr|const|friend|explicit|virtual)\s+)*[A-Za-z_][\w:<>,\s\*&\[\]]*?[\s\*&]([A-Za-z_~][\w:~]*(?:<[^()]*>)?|operator[^\s(]+)\s*\([^;]*$')
    def load(f):
        if f in outline: return outline[f]
        starts, names = [], []
        p = os.path.join(src, f)
        if os.path.isfile(p):
            for i, l in enumerate(open(p, errors='replace'), 1):
                if l[:1] in ' \t/#}\n' or l.startswith(('namespace', 'using', 'struct', 'class', 'enum')): continue
                m = defre.match(l.rstrip())
                if m and not l.rstrip().endswith(';'): starts.append(i); names.append(m[1])
        outline[f] = (starts, names); return outline[f]
    def fn_of(f, line):
        s, n = load(f); k = bisect.bisect_right(s, line) - 1
        return n[k] if k >= 0 else '?'
    cnt = collections.Counter()
    for c, k, fr in sites:
        if not fr: continue
        j = 0
        while j + 1 < len(fr) and (fr[j][0] in ('util.h', 'cambc.h', 'imports.h') or '/' not in fr[j][0] and not fr[j][0].endswith('.cc')): j += 1
        f, l = fr[j][0], fr[j][1]
        cnt[(f, fn_of(f, l))] += c
    return cnt
A = prof(sys.argv[1], sys.argv[2]); B = prof(sys.argv[3], sys.argv[4]); N = int(sys.argv[5]) if len(sys.argv) > 5 else 40
sc = float(os.environ.get("SCALE", "1")); B = collections.Counter({k: int(v * sc) for k, v in B.items()})
ta, tb = sum(A.values()), sum(B.values())
print(f'total A {ta} B {tb} diff {ta - tb:+d}')
keys = sorted(set(A) | set(B), key=lambda k: -(A[k] - B[k]))
for k in keys[:N]: print(f'{A[k] - B[k]:+13d}  A {A[k]:12d}  B {B[k]:12d}  {k[0]}: {k[1]}')
print('...most negative')
for k in keys[-8:]: print(f'{A[k] - B[k]:+13d}  A {A[k]:12d}  B {B[k]:12d}  {k[0]}: {k[1]}')
