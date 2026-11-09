# What a CAND changes in play, paired by (member, map, side) against REF, one-site maps: feat_core's features plus
# deaths, kills and casts near the altar, by body set (old spar-*-F/M against new -Fl/-Mt3/-Mt4) and opponent.
#   [MEMBERS=regex] py skfeat.py ANA_DIR CANDTAG REFTAG [FEATURE...]
import gzip, json, math, os, re, sys, collections
from pathlib import Path
from multiprocessing import Pool
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, '/home/ubuntu/cambc-autumn/research/ideas-2026-11-09/liveforensic-tools')
import episodes as E, feat_core

def feats(job):
    key, d, T = job; d = Path(d)
    try:
        f = feat_core.features(d, T)
        meta = json.load(open(d / 'meta.json')); mp = json.load(open(d / meta['mapFile'])); alt = [tuple(a) for a in mp['altars']]
        team = {c['id']: c['team'] for c in meta['champions']}
        def near(p): return min(max(abs(p[0] - x), abs(p[1] - y)) for x, y in alt) <= 4
        for l in gzip.open(d / 'events.jsonl.gz', 'rt'):
            e = json.loads(l); ph = 'e' if e['r'] < 600 else 'l'; k = e['k']
            if k == 'death' and e.get('at'):
                who = 'us' if team[e['v']] == T else 'op'; a = 'alt' if near(e['at']) else 'far'
                f[f'die_{who}_{a}_{ph}'] = f.get(f'die_{who}_{a}_{ph}', 0) + 1
                f[f'diegems_{who}_{a}_{ph}'] = f.get(f'diegems_{who}_{a}_{ph}', 0) + (e.get('gems') or 0)
            elif k == 'cast' and team.get(e.get('a')) == T:
                f[f'cast_{ph}'] = f.get(f'cast_{ph}', 0) + 1
                if e.get('f') and near(e['f']): f[f'cast_alt_{ph}'] = f.get(f'cast_alt_{ph}', 0) + 1
        for r in E.scan(d, T, until=600)['eps']:
            if r['r'] >= 600: continue
            s = r['side']; f[f'ep_{s}_start'] = f.get(f'ep_{s}_start', 0) + 1
            f[f'ep_{s}_{r["end"]}'] = f.get(f'ep_{s}_{r["end"]}', 0) + 1
            if r['end'] == 'done': f[f'ep_{s}_gems'] = f.get(f'ep_{s}_gems', 0) + r.get('gems_end', r['gems'])
        f['win'] = meta['result']['winner'] == T
        return key, f
    except Exception as ex:
        return key, None

def main():
    ana, ct, rt = Path(sys.argv[1]), sys.argv[2], sys.argv[3]; want = sys.argv[4:]
    mem_re = os.environ.get('MEMBERS', r'spar-[^/]+')
    jobs = []
    for g in json.load(open(ana / 'index.json'))['games']:
        m = re.search(rf'of-({ct}|{rt})-({mem_re})-ladder/\d+-(.+)-(12|21)\.repl26a$', g['source'])
        if m and E.MC.get(m[3].replace('-', '_')) == 'one':
            jobs.append(((m[1], m[2], m[3], m[4]), str(ana / g['dir']), 0 if m[4] == '12' else 1))
    with Pool(int(os.environ.get('OMP_NUM_THREADS', 8))) as P: res = dict(P.map(feats, jobs, chunksize=2))
    d = collections.defaultdict(lambda: collections.defaultdict(list)); keys = set()
    for (t, mem, mp, sd), f in res.items():
        if t != ct or not f: continue
        q = res.get((rt, mem, mp, sd))
        if not q: continue
        body = re.sub(r'^spar-(o25|oc29|dvn\d+)-', '', mem)
        g = ('new ' if body in ('Fl', 'Mt3') else 'mt4 ' if body == 'Mt4' else 'old ') + ('Fish' if body.startswith('F') else 'Mite')
        ks = set(f) | set(q); keys |= ks
        for k in ks:
            v = f.get(k, 0) - q.get(k, 0)
            if isinstance(v, (int, float)): d[g][k].append(float(v)); d[g[:4] + 'all'][k].append(float(v))
    groups = sorted(d)
    show = want or sorted(k for k in keys if not k.startswith('buy_') or 'Tribute' in k)
    print(f"{'feature':34s}" + ''.join(f'{g:>22s}' for g in groups))
    for k in show:
        row = f'{k:34s}'
        for g in groups:
            v = d[g].get(k, []); n = len(v)
            if not n: row += f'{"":>22s}'; continue
            mu = sum(v) / n; sd = (sum((a - mu) ** 2 for a in v) / n) ** .5; se = 1.96 * sd / math.sqrt(n)
            mark = '*' if abs(mu) > se and se > 0 else ' '
            row += f'{mu:+11.2f} ±{se:7.2f}{mark} '
        print(row)
    print('n', {g: len(d[g]['win']) for g in groups})

if __name__ == '__main__':
    main()
