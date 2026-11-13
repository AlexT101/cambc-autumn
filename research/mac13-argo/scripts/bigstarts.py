"""500+ bag tribute starts (mirror): by starter type, the team winning the game, the team rich (wealth >= 1000) and
whether the bag alone wins (score + bag >= 1000); completion and the stop cause. py bigstarts.py ANALYSIS_DIR"""
import gzip, json, sys
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
def one(d):
    try:
        meta = json.loads((d / 'meta.json').read_text()); R = json.load(gzip.open(d / 'rounds.json.gz'))
        ev = [json.loads(l) for l in gzip.open(d / 'events.jsonl.gz', 'rt')]
    except Exception: return []
    w = meta['result']['winner']; rid = {r: i for i, r in enumerate(R['round'])}; C = R['champions']
    team = {c['id']: c['team'] for c in C}; name = {c['id']: c['name'] for c in meta['champions']}
    out, open_ = [], {}
    for e in ev:
        if e['k'] == 'tribute_start' and e['gems'] >= 500:
            a = e['a']; t = team[a]; i = rid.get(e['r'] - 1, 0)
            wealth = R['gems'][t][i] + sum(c['gems'][i] for c in C if c['team'] == t and c['alive'][i])
            open_[a] = (name[a], t == w, wealth >= 1000, R['gems'][t][i] + e['gems'] >= 1000, e['r'])
        elif e['k'] in ('tribute_end', 'tribute_cancel') and e.get('a') in open_:
            o = open_.pop(e['a']); out.append(o + (e['k'] == 'tribute_end', e.get('cause') or e.get('by') and 'stun' or '-'))
    return out
if __name__ == '__main__':
    dirs = [p for p in Path(sys.argv[1]).iterdir() if (p / 'meta.json').exists()]
    rows = []
    with ProcessPoolExecutor(24) as ex:
        for r in ex.map(one, dirs, chunksize=8): rows += r
    print('500+ starts', len(rows), 'by', Counter(r[0] for r in rows).most_common(4))
    for key, f in (('winner', lambda r: r[1]), ('loser', lambda r: not r[1])):
        s = [r for r in rows if f(r)]
        print(f'{key}: {len(s)} starts, done {100*sum(r[5] for r in s)/max(1,len(s)):.0f}%; bag wins alone {sum(r[3] for r in s)}, '
              f'done then {100*sum(r[5] for r in s if r[3])/max(1,sum(r[3] for r in s)):.0f}%; team rich but bag not winning {sum(r[2] and not r[3] for r in s)}; not rich {sum(not r[2] for r in s)}')
    print('cancel fields seen:', Counter(r[6] for r in rows if not r[5]).most_common(6))
