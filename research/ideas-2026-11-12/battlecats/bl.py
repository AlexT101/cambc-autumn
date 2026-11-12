"""Loader for decoded BattleCats replays (extract.mjs --out ~/tmp-offload/battlecats/ana), joined to capture rows."""
import json, gzip, os, glob
import meta
ANA = os.path.expanduser('~/tmp-offload/battlecats/ana')
_rows = None; _maps = {}
def rows():
    global _rows
    if _rows is None: _rows = {r['match_id']: r for r in meta.rows()}
    return _rows
def version(t): return 'old' if t < '2026-11-09T06' else ('trans' if t < '2026-11-10T09' else 'cur')
def mapj(h):
    if h not in _maps: _maps[h] = json.load(open(f'{ANA}/maps/{h}.json'))
    return _maps[h]
def dirs():
    return sorted(d for d in glob.glob(f'{ANA}/*/meta.json'))
def load(d, rounds=True, events=True):
    m = json.load(open(d))
    if not m.get('validation', {}).get('ok', True): return None
    mid = os.path.basename(m['source']).split('.')[0]
    r = rows().get(mid)
    if r is None: return None
    g = {'meta': m, 'row': r, 'mid': mid, 'bc': 0 if r['bc_side'] == 'a' else 1, 'opp': r['opp'], 'kind': r['kind'],
         'created': r['created_at'], 'ver': version(r['created_at']), 'win': r['bc_win'], 'dir': os.path.dirname(d), 'mapname': r['map']}
    if events: g['ev'] = [json.loads(l) for l in gzip.open(g['dir'] + '/events.jsonl.gz', 'rt')]
    if rounds: g['rd'] = json.load(gzip.open(g['dir'] + '/rounds.json.gz'))
    g['map'] = mapj(m['map']['hash'])
    return g
def games(filt=None, limit=None, rounds=True, events=True):
    n = 0
    for d in dirs():
        g = load(d, rounds, events)
        if g is None or (filt and not filt(g)): continue
        yield g; n += 1
        if limit and n >= limit: return
def cheb(a, b): return max(abs(a[0] - b[0]), abs(a[1] - b[1]))
