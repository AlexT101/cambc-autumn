#!/usr/bin/env python3
"""Where a fastrunner game spends its time, from `samply record --save-only` output.

    python3 tools/fastengine/runner/scripts/prof.py PROFILE.json.gz [--leaves 40] [--callers 25]

Resolves frames in the cambc executable (the engine) and libfastrunner.so (runner, wasmtime) with nm; frames in
no library are the bots' JIT code, and so are native mode's bot libraries (<hash>-<flags>.so)."""
import bisect, collections, gzip, json, os, re, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE = {}

def syms(path):
    if path in CACHE:
        return CACHE[path]
    out = subprocess.run(['nm', '-C', '-S', '--defined-only', path], capture_output=True, text=True).stdout
    rows = []
    for line in out.splitlines():
        m = re.match(r'^([0-9a-f]+) (?:([0-9a-f]+) )?([TtWw]) (.*)$', line)
        if m:
            rows.append((int(m.group(1), 16), re.sub(r'::h[0-9a-f]{16}$', '', m.group(4))))
    rows.sort()
    CACHE[path] = ([r[0] for r in rows], rows)
    return CACHE[path]

def short(n):
    n = re.sub(r'<[^<>]*(<[^<>]*(<[^<>]*>[^<>]*)*>[^<>]*)*>', '<..>', n)
    return n[:140]

def main():
    args = sys.argv[1:]
    prof = args[0]
    nleaves = int(args[args.index('--leaves') + 1]) if '--leaves' in args else 40
    ncallers = int(args[args.index('--callers') + 1]) if '--callers' in args else 25
    p = json.load(gzip.open(prof))
    libs = p['libs']
    paths = {i: l.get('debugPath') or l.get('path') for i, l in enumerate(libs)}
    leaves = collections.Counter(); cats = collections.Counter(); callers = collections.Counter()
    n = 0
    for t in p['threads']:
        st, ft, fn, rt = t['stackTable'], t['frameTable'], t['funcTable'], t['resourceTable']
        cache = {}
        def frame(fi):
            v = cache.get(fi)
            if v is None:
                res = fn['resource'][ft['func'][fi]]
                name = libs[rt['lib'][res]]['name'] if res is not None and res >= 0 else ''
                if res is None or res < 0 or name.endswith('.cwasm') or re.fullmatch(r'[0-9a-f]{32}-[0-9a-f]{8}\.so', name):
                    v = ('JIT', 'JIT')
                else:
                    li = rt['lib'][res]
                    lib = libs[li]['name']
                    path = paths[li]
                    if lib in ('cambc',) or lib.startswith('libfastrunner'):
                        a, rows = syms(path)
                        i = bisect.bisect_right(a, ft['address'][fi]) - 1
                        v = (lib, rows[i][1] if i >= 0 else '?')
                    else:
                        v = (lib, lib)
                cache[fi] = v
            return v
        for s in t['samples']['stack']:
            if s is None:
                continue
            frames = []
            while s is not None:
                frames.append(frame(st['frame'][s])); s = st['prefix'][s]
            n += 1
            lib, name = frames[0]
            leaves[(lib[:12], short(name))] += 1
            jit = any(f[0] == 'JIT' for f in frames)
            if lib == 'JIT':
                c = 'bot JIT'
            elif not jit:
                c = 'outside bots: ' + ('engine' if lib == 'cambc' else lib[:20])
            else:
                upto = next(i for i, f in enumerate(frames) if f[0] == 'JIT')
                inner = frames[:upto]
                if lib == 'cambc' or any(f[0] == 'cambc' for f in inner):
                    c = 'host call: engine'
                elif lib.startswith('libc'):
                    c = 'host call: libc'
                else:
                    c = 'host call: runner/wasmtime glue'
                # the runner function the JIT called into
                api = next((f[1] for f in reversed(inner) if f[0] == 'cambc' and re.match(r'(Game_|Bitboard_|DistanceField_)', f[1])), None)
                callers[api or 'glue only'] += 1
            cats[c] += 1
    print(f'{n} samples')
    for c, v in cats.most_common():
        print(f'{100*v/n:6.2f}%  {c}')
    print('-- leaves --')
    for (lib, name), v in leaves.most_common(nleaves):
        print(f'{100*v/n:6.2f}%  {lib:12s} {name}')
    print('-- host calls by runner entry --')
    for k, v in callers.most_common(ncallers):
        print(f'{100*v/n:6.2f}%  {k}')

main()
