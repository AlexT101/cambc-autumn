"""symbolise2.py BOTDIR OUT.json PROFDIR...: tools/fuel/fuelprof/symbolise.py with the outermost frame's function fixed.
llvm-symbolizer names the outermost frame from the wasm symbol table, whose addresses are file offsets while DWARF's
are code-section offsets, so that name belongs to a function a little earlier in the code. A second query at
address + code offset reads the right symbol. Sites: [fuel, kind, [[file, line, function] innermost first]]."""
import sys, struct, glob, json, subprocess, collections, os, bisect
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '../../../tools/fuel/fuelprof'))
from wbodies import bodies
bot, outp, dirs = sys.argv[1], sys.argv[2], sys.argv[3:]
d = bot + '/.cambc/build/'
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
def run(off, inl):
    out = subprocess.run([sym, '--obj=' + d + 'bot.wasm', '--inlining' if inl else '--no-inlines', '--output-style=JSON'],
                         input='\n'.join(hex(addr(p) + off) for p in ps), capture_output=True, text=True).stdout
    return [json.loads(l) for l in out.splitlines() if l.strip()]
res = run(0, True); res2 = run(c1, False)
sites = []
for p, r, r2 in zip(ps, res, res2):
    fr = [[os.path.relpath(x.get('FileName', '?'), bot + '/src') if x.get('FileName', '').startswith(bot) else os.path.basename(x.get('FileName', '?')),
           x.get('Line', 0), x.get('FunctionName', '?')] for x in r.get('Symbol', [])]
    s2 = r2.get('Symbol', [])
    if fr and s2: fr[-1][2] = s2[-1].get('FunctionName', '?')
    sites.append((acc[p], kinds[p], fr))
json.dump({'files': nfiles, 'sites': sites}, open(outp, 'w'))
print('files', nfiles, 'total', sum(acc.values()), 'sites', len(sites))
