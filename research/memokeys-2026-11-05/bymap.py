import sys, re, json, glob, os, collections
M = '/home/ubuntu/cambc-autumn/maps'
meta = {}
def load(suite):
    if suite in meta: return
    p = f'{M}/{suite}/index.json'
    meta[suite] = {m['file']: m['metrics'] for m in json.load(open(p))['maps']} if os.path.exists(p) else {}
line = re.compile(r'\] (\S+\.map26a) A=\d B=\d: (bot (\d) wins|draw)')
def buckets(m):
    g = 2*m['groups_side'] + m.get('shared_groups', 0)
    gb = '<12' if g < 12 else '12-23' if g < 24 else '24-47' if g < 48 else '48+'
    a = m['area']; ab = '<2k' if a < 2000 else '2-4k' if a < 4000 else '4-7k' if a < 7000 else '7k+'
    return gb, ab
for run in sys.argv[1:]:
    tot = collections.defaultdict(lambda: [0, 0])
    for log in sorted(glob.glob(f'{run}/fresh-*.log')):
        suite = os.path.basename(log)[:-4]; load(suite)
        for l in open(log):
            mm = line.search(l)
            if not mm or mm.group(1) not in meta[suite]: continue
            w = 1.0 if mm.group(3) == '1' else 0.0 if mm.group(3) == '2' else 0.5
            gb, ab = buckets(meta[suite][mm.group(1)])
            for k in ('all', 'g' + gb, 'a' + ab):
                tot[k][0] += w; tot[k][1] += 1
    print(os.path.basename(run.rstrip('/')), '  '.join(f'{k}:{100*v[0]/v[1]:.1f}({v[1]})' for k, v in sorted(tot.items())))
