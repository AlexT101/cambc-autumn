"""Real Mite's emblem order by ordinal per champion (mite-re's decodes, 11-09 12:00+ vs us), as possq.py for Fish."""
import gzip, json, os, re, collections
from multiprocessing import Pool
A = os.path.expanduser('~/tmp-offload/miteRE/ana')
G = [json.loads(l) for l in open(os.path.expanduser('~/tmp-offload/miteRE/feats.jsonl'))]
G = list({g['mid']: g for g in G if 'err' not in g}.values())
def one(g):
    d = g['dir']; meta = json.load(open(f'{A}/{d}/meta.json'))
    team = {c['id']: c['team'] for c in meta['champions']}; nm = {c['id']: c['name'] for c in meta['champions']}
    order = collections.defaultdict(list)
    for l in gzip.open(f'{A}/{d}/events.jsonl.gz', 'rt'):
        e = json.loads(l)
        if e['k'] == 'shop' and team[e['a']] == g['ms']:
            for it, k in (e.get('items') or {}).items():
                m = re.match(r'(\w+) (Shard|Emblem) of (\w+)', it)
                if m and k > 0 and m.group(2) == 'Emblem': order[e['a']] += [m.group(1) + '-' + m.group(3)[0]] * k
    return [(nm[a], order[a]) for a in nm if team[a] == g['ms']]
if __name__ == '__main__':
    L = [g for g in G if g['cr'] >= '2026-11-09T12' and g['opp'] == 'stellar best girl']
    pos = collections.defaultdict(lambda: collections.defaultdict(collections.Counter)); n = collections.Counter()
    with Pool(12) as p:
        for res in p.imap_unordered(one, L, chunksize=4):
            for nm, o in res:
                n[nm] += 1
                for i, f in enumerate(o[:14]): pos[nm][i][f] += 1
    for nm in n:
        print(f"\n{nm} ({n[nm]})")
        for i in sorted(pos[nm]):
            t = sum(pos[nm][i].values())
            print(f"  {i:2d} n={t:4d} " + '  '.join(f"{k} {v/t:.2f}" for k, v in pos[nm][i].most_common(3)))
