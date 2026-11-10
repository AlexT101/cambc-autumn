"""osc.py ANALYSIS_DIR TEAM_NAME_OR_INDEX... : period-2 position oscillation of our champions, from extract.mjs output.
An episode: a living, unchannelled champion's end-of-round tile alternates between two tiles (A,B,A,B...) for >= MINLEN
rounds. 'quiet': it dealt and took no champion damage in the episode. 'big': an enemy tribute channel of >= 100 gems
runs during it. Prints per-game rows (json) and a summary."""
import json, gzip, glob, os, sys, collections
MINLEN = 6
def episodes(R, ev, team):
    dmg = collections.defaultdict(set)  # champion id -> rounds it dealt/took champion damage
    for e in ev:
        if e['k'] in ('attack', 'cast') and e.get('tgt') is not None and 'dmg' in e:
            dmg[e['a']].add(e['r'])
            for v, _ in e['dmg']: dmg[v].add(e['r'])
    rounds = R['round']; cs = R['champions']
    big = [any(c['team'] != team and c['chan'][i] == 2 and c['gems'][i] >= 100 for c in cs) for i in range(len(rounds))]
    out = []
    for c in cs:
        if c['team'] != team: continue
        n = len(rounds); i = 2
        while i < n:
            ok = lambda k: c['alive'][k] and c['chan'][k] in (0, None) or (c['alive'][k] and c['chan'][k] == 0)
            j = i
            while j < n and c['alive'][j] and c['alive'][j-1] and c['alive'][j-2] \
                    and (c['x'][j], c['y'][j]) == (c['x'][j-2], c['y'][j-2]) and (c['x'][j], c['y'][j]) != (c['x'][j-1], c['y'][j-1]):
                j += 1
            L = j - i + 2
            if j > i and L >= MINLEN:
                rs = set(rounds[i-2:j])
                out.append({'id': c['id'], 'r0': rounds[i-2], 'len': L, 'quiet': not (rs & dmg[c['id']]),
                            'big': any(big[i-2:j]), 'tiles': [(c['x'][i-2], c['y'][i-2]), (c['x'][i-1], c['y'][i-1])]})
                i = j
            else:
                i = j + 1 if j > i else i + 1
    return out
def main():
    global SIDES
    root, names = sys.argv[1], sys.argv[2:]
    SIDES = None
    if names and names[0].startswith('@'):
        SIDES = {m['matchId']: next(0 if t['side'] == 'a' else 1 for t in m['teams'] if t['name'] == 'stellar best girl') for m in json.load(open(names[0][1:]))}
    rows = []
    for d in glob.glob(root + '/*/'):
        if not os.path.exists(d + 'meta.json'): continue
        m = json.load(open(d + 'meta.json'))
        tn = [t.get('name', '') for t in m['teams']]
        if SIDES is not None:
            mid = os.path.basename(m['source']).removesuffix('.repl26a'); team = SIDES.get(mid)
        else:
            team = next((k for k in (0, 1) if any(tn[k].startswith(x) for x in names)), None)
        if team is None: continue
        R = json.load(gzip.open(d + 'rounds.json.gz')); ev = [json.loads(l) for l in gzip.open(d + 'events.jsonl.gz', 'rt')]
        eps = episodes(R, ev, team)
        bigr = sum(any(c['team'] != team and c['chan'][i] == 2 and c['gems'][i] >= 100 for c in R['champions']) for i in range(len(R['round'])))
        rows.append({'dir': d, 'map': m['map']['name'], 'rounds': m['result']['rounds'], 'won': m['result']['winner'] == team,
                     'osc': sum(e['len'] for e in eps), 'quiet': sum(e['len'] for e in eps if e['quiet']),
                     'big': sum(e['len'] for e in eps if e['big']), 'bigrounds': bigr, 'eps': eps})
    n = len(rows); T = lambda k: sum(r[k] for r in rows)
    print(json.dumps({'games': n, 'rounds': T('rounds'), 'osc_rounds': T('osc'), 'quiet': T('quiet'), 'during_big': T('big'),
                      'big_tribute_rounds': T('bigrounds'), 'games_with_osc': sum(r['osc'] > 0 for r in rows),
                      'osc_per_game': round(T('osc') / max(1, n), 2), 'quiet_per_game': round(T('quiet') / max(1, n), 2),
                      'big_per_game': round(T('big') / max(1, n), 2), 'winrate_with_big_osc': [sum(r['won'] for r in rows if r['big']), sum(1 for r in rows if r['big'])]}))
    json.dump(rows, open(root + '/osc_rows.json', 'w'))
main()
