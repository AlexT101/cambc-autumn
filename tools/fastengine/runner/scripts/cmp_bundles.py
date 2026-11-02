#!/usr/bin/env python3
"""cmp_bundles.py A.repl26a B.repl26a [...]: compare replay bundles member by member (pairs: a1 b1 a2 b2 ...).
Prints per pair: identical, or the members that differ (for .fuel files, the first differing turn)."""
import sys, zipfile, struct

def members(p):
    with zipfile.ZipFile(p) as z:
        return {n: z.read(n) for n in z.namelist()}

def fuel_turns(b):
    n = (len(b) - 13 - 64) // 8
    return struct.unpack_from(f'<{n}Q', b, 77)

def compare(a, b):
    ma, mb = members(a), members(b)
    diffs = []
    for n in sorted(set(ma) | set(mb)):
        if ma.get(n) != mb.get(n):
            d = n
            if n.endswith('.fuel') and n in ma and n in mb:
                ta, tb = fuel_turns(ma[n]), fuel_turns(mb[n])
                i = next((i for i, (x, y) in enumerate(zip(ta, tb)) if x != y), min(len(ta), len(tb)))
                d += f'(turn {i}: {ta[i] if i < len(ta) else None} vs {tb[i] if i < len(tb) else None}; {len(ta)} vs {len(tb)} turns)'
            elif n in ma and n in mb:
                x, y = ma[n], mb[n]
                i = next((i for i, (p, q) in enumerate(zip(x, y)) if p != q), min(len(x), len(y)))
                d += f'(byte {i}; {len(x)} vs {len(y)})'
            diffs.append(d)
    return diffs

if __name__ == '__main__':
    args = sys.argv[1:]
    same = 0
    for a, b in zip(args[::2], args[1::2]):
        d = compare(a, b)
        if d:
            print(f'DIFF {a}: ' + ', '.join(d))
        else:
            same += 1
    print(f'{same}/{len(args)//2} identical')
