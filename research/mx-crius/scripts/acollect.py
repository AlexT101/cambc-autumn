"""Collector mechanism counts by bot name, Prism teams only: Prism share of captured gems; Prism-sole captures
whose hold an ally began (collects); captures the Prism split with allies; non-contested capture resets."""
import json, gzip, glob, os, sys, collections
from concurrent.futures import ProcessPoolExecutor
ROOT = sys.argv[1]
CH = json.load(open(ROOT + '/enums.json'))['champions']


def one(d):
    meta = json.load(open(d + '/meta.json'))
    team = {c['id']: c['team'] for c in meta['champions']}
    typ = {c['id']: CH[c['type']] for c in meta['champions']}
    names = [t['name'] for t in meta['teams']]
    mp = json.load(open(os.path.join(d, meta['mapFile'])))
    groups = {g['id']: g for g in mp['groups']}
    R = json.load(gzip.open(d + '/rounds.json.gz'))
    ri = {r: i for i, r in enumerate(R['round'])}
    champ = {c['id']: c for c in R['champions']}
    prism = {t: [c['id'] for c in R['champions'] if c['team'] == t and typ[c['id']] == 'Prism'] for t in (0, 1)}
    out = {t: collections.Counter() for t in (0, 1)}
    hold_start = {}
    for l in gzip.open(d + '/events.jsonl.gz', 'rt'):
        e = json.loads(l)
        k = e['k']
        if k == 'capture_hold':
            hold_start[(e['team'], e['g'])] = e['r']
            continue
        if k == 'capture_reset':
            t = e['team']
            if prism[t] and not e.get('contested'):
                out[t]['resets'] += 1
            continue
        if k != 'capture':
            continue
        t = e['team']
        if not prism[t]:
            continue
        P = prism[t][0]
        G = groups.get(e['g'])
        gm = sum(s[1] for s in e['shares'])
        pg = sum(s[1] for s in e['shares'] if s[0] == P)
        o = out[t]
        o['team'] += gm
        o['prism'] += pg
        o['caps'] += 1
        if pg > 0 and len(e['shares']) > 1:
            o['split'] += 1
            o['split_gems_ally'] += gm - pg
        if pg > 0 and len(e['shares']) == 1 and G:
            h = hold_start.get((t, e['g']))
            i = ri.get(h - 1) if h is not None else None
            if i is not None:
                c = champ[P]
                tiles = {tuple(x) for x in G['tiles']}
                if (c['x'][i], c['y'][i]) not in tiles:
                    o['collects'] += 1
                    o['collect_gems'] += gm
        if pg == 0 and gm > 0:
            o['ally_caps'] += 1
            o['ally_gems'] += gm
    res = collections.defaultdict(collections.Counter)
    for t in (0, 1):
        if prism[t]:
            res[names[t]].update(out[t])
            res[names[t]]['games'] += 1
    return res


if __name__ == '__main__':
    ds = [os.path.dirname(p) for p in glob.glob(ROOT + '/*/meta.json')]
    tot = collections.defaultdict(collections.Counter)
    with ProcessPoolExecutor(32) as ex:
        for r in ex.map(one, ds, chunksize=8):
            for k, v in r.items():
                tot[k].update(v)
    for name, c in sorted(tot.items()):
        n = max(1, c['games'])
        print('%-14s prism-team-games %d  share %.3f  caps %.1f  collects %.2f (%.0f gems)  splits %.2f (ally gems %.1f)  '
              'ally-only caps %.1f (%.0f gems)  resets %.2f  per team-game' % (
                  name, c['games'], c['prism'] / max(1, c['team']), c['caps'] / n, c['collects'] / n, c['collect_gems'] / n,
                  c['split'] / n, c['split_gems_ally'] / n, c['ally_caps'] / n, c['ally_gems'] / n, c['resets'] / n))
