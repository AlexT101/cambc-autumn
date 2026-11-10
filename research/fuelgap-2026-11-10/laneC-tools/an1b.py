"""Parse FGC lines from bench game bundles (team-?.stdout of our side) and tabulate."""
import sys, zipfile, glob, os, statistics, collections, json

def lines(games_dir, side_of_bot=True):
    for d in sorted(glob.glob(os.path.join(games_dir, '*'))):
        if not os.path.isdir(d):
            continue
        side = d.rsplit('-', 1)[-1]
        for z in glob.glob(os.path.join(d, '*.zip')) + glob.glob(os.path.join(d, '*.repl26a')):
            try:
                zf = zipfile.ZipFile(z)
            except Exception:
                continue
            try:
                out = zf.read(f'team-{side}.stdout').decode('utf-8', 'replace')
            except KeyError:
                continue
            for l in out.splitlines():
                yield os.path.basename(d), l

def parse(l):
    t = l.split()
    r = {}
    r['round0'], r['round1'], r['h'], r['dec'] = int(t[1]), int(t[2]), int(t[3]), t[4]
    k, ev = t[6].split('/')
    r['k'], r['ev'] = int(k), int(ev)
    r['first'], r['prev'], r['best'] = int(t[8]), int(t[10]), int(t[12])
    r['qstage'], r['qdone'] = int(t[14]), int(t[15])
    r['prevq_round'], r['prev_left'], r['prev_qdone'], r['prev_dec'] = int(t[17]), int(t[18]), int(t[19]), t[20]
    r['n_sc'], r['sc_loop'], r['sc_exit'] = int(t[22]), int(t[23]), int(t[24])
    i = t.index('v')
    r['ne'], r['nd'] = int(t[i + 1]), int(t[i + 2])
    r['v'] = [int(x) for x in t[i + 3:i + 51]]
    j = t.index('end')
    r['end'] = int(t[j + 1])
    s = t.index('scs')
    p = t.index('passes') if 'passes' in t else len(t)
    r['scs'] = t[s + 1:p]
    r['passes'] = [tuple(int(y) for y in x.split(':')) for x in t[p + 1:]] if p < len(t) else []
    return r

def pct(xs, q):
    if not xs:
        return float('nan')
    xs = sorted(xs)
    return xs[min(len(xs) - 1, int(q * len(xs)))]

if __name__ == '__main__':
    rows = []
    for g, l in lines(sys.argv[1]):
        if l.startswith('FGC '):
            try:
                r = parse(l)
            except Exception as e:
                continue
            r['game'] = g
            rows.append(r)
    json.dump(rows, open(sys.argv[2], 'w'))
    print(len(rows), 'rows')
