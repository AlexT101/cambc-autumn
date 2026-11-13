"""Per-site fuel symbolised by source line: python symbolise.py BOTDIR OUT.json PROFDIR... (BOTDIR built with -g: CXXFLAGS=-g cambc build BOTDIR)."""
import sys, struct, glob, json, subprocess, collections, os, bisect
from wbodies import bodies  # same directory
bot, outp, dirs = sys.argv[1], sys.argv[2], sys.argv[3:]
d = bot + '/.cambc/' + __import__('os').environ.get('BUILD_DIR', 'build-release') + '/'
b1, c1, o1 = bodies(d + 'bot.wasm'); b2, c2, o2 = bodies(d + 'bot-injected.wasm')
tag = sum(e - s for s, e in o2); starts = [s for s, e in o2]
acc = collections.Counter(); kinds = {}; nfiles = 0
for D in dirs:
    for f in glob.glob(D + '/prof-*.bin'):
        b = open(f, 'rb').read(); nf, tot, n = struct.unpack_from('<III', b, 4)
        if tot != tag: continue
        nfiles += 1
        pos = struct.unpack_from('<%dI' % n, b, 16); kd = b[16 + 4 * n:16 + 5 * n]; cnt = struct.unpack_from('<%dQ' % n, b, 16 + 5 * n)
        for p, k, c in zip(pos, kd, cnt):
            if c: acc[p] += c; kinds[p] = k
ps = list(acc)
def addr(p):
    k = bisect.bisect_right(starts, p) - 1
    return o1[k][0] + (p - o2[k][0]) - c1
sym = os.path.expanduser('~/.cache/cambc/wasi-sdk-33/bin/llvm-symbolizer')
out = subprocess.run([sym, '--obj=' + d + 'bot.wasm', '--inlining', '--output-style=JSON'], input='\n'.join(hex(addr(p)) for p in ps), capture_output=True, text=True).stdout
res = [json.loads(l) for l in out.splitlines() if l.strip()]
sites = []
for p, r in zip(ps, res):
    fr = [(os.path.relpath(x.get('FileName', '?'), bot + '/src') if x.get('FileName', '').startswith(bot) else os.path.basename(x.get('FileName', '?')), x.get('Line', 0)) for x in r.get('Symbol', [])]
    sites.append((acc[p], kinds[p], fr))
json.dump({'files': nfiles, 'sites': sites}, open(outp, 'w'))
print('files', nfiles, 'total', sum(acc.values()), 'sites', len(sites))
