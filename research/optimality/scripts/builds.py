# Emblem families held at round 300 (shard-equivalents per champion), by team.
import json, gzip, os, collections
from concurrent.futures import ProcessPoolExecutor
ROOT = r'C:\Users\alext\Github\cambc-autumn\replays\.analysis'
TOPS = ['Intercontinental Fish', 'Mite', 'Sneaky Bush Campers', 'Univardisty of Shingtonwash', 'procless', 'PTN Hyperion']
FAMS = ['monster', 'power', 'durability', 'treasure', 'jungle', 'home', 'bruiser']


def game(args):
    g, items = args
    out = collections.Counter()
    try:
        m = json.load(open(os.path.join(ROOT, g['dir'], 'meta.json'), encoding='utf-8'))
        R = json.load(gzip.open(os.path.join(ROOT, g['dir'], 'rounds.json.gz')))
    except Exception:
        return out
    name_of = {c['id']: c['name'] for c in m['champions']}
    for c in R['champions']:
        t = g['teams'][c['team']]
        if t not in TOPS or not c['items']: continue
        it = c['items'][min(len(c['items']) - 1, 299)]
        cn = name_of[c['id']]
        for k in range(0, len(it) - 1, 2):
            nm = str(items[it[k]] if isinstance(items, list) else items.get(str(it[k]), it[k])).lower()
            fam = next((x for x in FAMS if x in nm), nm)
            stat = next((x for x in ('strength', 'health', 'focus') if x in nm), '?')
            w = 5 if 'emblem' in nm else 1
            out[(t, fam)] += it[k + 1] * w
            out[(t, cn, fam + '_' + stat)] += it[k + 1] * w
        out[(t, 'n')] += 1
        out[(t, cn, 'n')] += 1
    return out


if __name__ == '__main__':
    enums = json.load(open(os.path.join(ROOT, 'enums.json'), encoding='utf-8'))
    items = enums.get('items')
    idxj = json.load(open(os.path.join(ROOT, 'index.json'), encoding='utf-8'))
    gs = {}
    for g in idxj['games']:
        if g['kind'] == 'ladder' and g['ok'] and g['source'].split('/')[2][:8] >= '20261016' and any(t in g['teams'] for t in TOPS):
            gs[g['dir']] = g
    tot = collections.Counter()
    with ProcessPoolExecutor(16) as ex:
        for r in ex.map(game, [(g, items) for g in list(gs.values())[:2500]], chunksize=8):
            tot += r
    print('item names sample:', items[:14] if isinstance(items, list) else list(items.items())[:14])
    for t in TOPS:
        n = tot[(t, 'n')]
        if not n: continue
        fam = sorted(((tot[(t, f)] / n, f) for f in FAMS if tot[(t, f)]), reverse=True)
        print(f'{t[:22]:22s} shard-equivalents per champion at r300: ' + ', '.join(f'{f} {v:.2f}' for v, f in fam))
    for cn in ['Stellar', 'Cassi', 'Varg', 'Ryth', 'Ren', 'Issac']:
        print(f'--- {cn}')
        for t in TOPS:
            n = tot[(t, cn, 'n')]
            if not n: continue
            parts = sorted(((v / n, k[2]) for k, v in tot.items() if len(k) == 3 and k[0] == t and k[1] == cn and k[2] != 'n'), reverse=True)[:4]
            print(f'    {t[:22]:22s} ' + ', '.join(f'{k} {v:.1f}' for v, k in parts))
