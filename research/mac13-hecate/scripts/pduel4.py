# pduel4.py EXTRACT: Prism-on-Prism kills of 50+ bags, killer >1.1x victim Focus: sight history of the killer by the
# victim's TEAM and by the victim itself over the last 40 rounds
import sys, json, gzip, collections, statistics as S
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
def one(d):
    try:
        meta = json.loads((d/'meta.json').read_text()); R = json.load(gzip.open(d/'rounds.json.gz'))
    except Exception: return None
    name = {c['id']: c['name'] for c in meta['champions']}; team = {c['id']: c['team'] for c in meta['champions']}
    r0 = R['round'][0]; ch = {c['id']: c for c in R['champions']}; out = []
    for l in gzip.open(d/'events.jsonl.gz', 'rt'):
        e = json.loads(l)
        if e.get('k') != 'death' or name.get(e['v']) != 'Prism' or name.get(e.get('by')) != 'Prism' or e['gems'] < 50: continue
        v, k = e['v'], e['by']; i = e['r'] - r0; V, K = ch[v], ch[k]
        j = max(0, i - 1)
        if K['foc'][j] / max(1, V['foc'][j]) <= 1.1: continue
        mates = [c for c in team if team[c] == team[v]]
        selfseen = [v in K['seenBy'][jj] for jj in range(max(0, i - 40), i)]
        teamseen = [any(m in K['seenBy'][jj] for m in mates) for jj in range(max(0, i - 40), i)]
        # first round within 10 tiles
        first10 = None
        for jj in range(max(0, i - 40), i):
            if V['x'][jj] is not None and K['x'][jj] is not None and max(abs(V['x'][jj]-K['x'][jj]), abs(V['y'][jj]-K['y'][jj])) <= 10:
                first10 = i - jj; break
        lastgap = next((g for g, s in enumerate(reversed(selfseen)) if s), None)
        out.append(dict(self=sum(selfseen), team=sum(teamseen), first10=first10, lastgap=lastgap, firstself=(len(selfseen) - selfseen.index(True)) if True in selfseen else None, gems=e['gems']))
    return out
if __name__ == '__main__':
    ds = [p for p in Path(sys.argv[1]).iterdir() if (p/'meta.json').exists()]; rows = []
    with ProcessPoolExecutor(24) as ex:
        for o in ex.map(one, ds, chunksize=8):
            if o: rows += o
    print('n', len(rows), 'per game', len(rows) / len(ds))
    print('rounds (of 40) victim saw killer: median', S.median(x['self'] for x in rows), 'team saw', S.median(x['team'] for x in rows))
    print('first within 10 tiles, rounds before death: median', S.median(x['first10'] for x in rows if x['first10']))
    print('victim first saw killer, rounds before death: quartiles', sorted(x['firstself'] or 0 for x in rows)[len(rows)//4::len(rows)//4])
    print('never saw it in 40 rounds', sum(x['firstself'] is None for x in rows), 'last seen gap before death >3', sum((99 if x['lastgap'] is None else x['lastgap']) > 3 for x in rows), 'gap quartiles', sorted(99 if x['lastgap'] is None else x['lastgap'] for x in rows)[len(rows)//4::len(rows)//4])
    print('team saw but victim not in 40 rounds', sum(x['self'] == 0 and x['team'] > 0 for x in rows))
