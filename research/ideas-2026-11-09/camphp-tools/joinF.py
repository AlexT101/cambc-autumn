import json, sys, zipfile, collections, os
B = sys.argv[1]
L = [json.loads(l) for l in open(sys.argv[2])]
L = [x for x in L if x['r'] is not None]
OC = 'camphp-dbg'
cache = {}
def lines(stem, side):
    if (stem, side) not in cache:
        z = zipfile.ZipFile(os.path.join(B, stem + '.repl26a'))
        D = collections.defaultdict(dict); F = collections.defaultdict(list)
        for line in z.read(f'team-{"ab"[side]}.stdout').decode('latin1').splitlines():
            p = line.split()
            if line.startswith('D ') and len(p) >= 6: D[int(p[2])][int(p[1])] = (p[3], int(p[4]))
            elif line.startswith('FSW '): F[(int(p[2]), int(p[3]))].append((int(p[1]), p[6], float(p[7]), int(p[8]), float(p[9]), float(p[4]), float(p[5]), p[12:]))
        cache[(stem, side)] = (D, F)
    return cache[(stem, side)]
ng = len(set(x['mid'] for x in L))
cat = collections.Counter(); exs = collections.defaultdict(list)
for x in L:
    if x['names'][x['by']] != OC or not (x['dps'] > 0 and x['left'] / x['dps'] < 3): continue
    D, F = lines(x['mid'], x['by'])
    sw = []
    for h in x['hitters']:
        for (r, w, fv, b, bv, hp, H, rest) in F.get((h, x['g']), []):
            if x["r"] - 1 <= r <= x["r"] + 2: sw.append((h, r, w, fv, b, bv, rest))
    if sw:
        w = ''.join(sorted(set(s[2] for s in sw)))
        cat['FSW:' + w] += 1; exs['FSW:' + w].append((x, sw))
    else:
        cat['noFSW'] += 1
print(ng, 'games')
for k, v in cat.most_common(): print(f'  {k:10s} {v} {v/ng:.3f}/game')
for k in exs:
    for x, sw in exs[k][:6]:
        print(k, x['mid'], 'g', x['g'], x['rem'], 'r', x['r'], 'resume', x['resume'], 'cap', x['cap'], sw[:3])
