"""Per-game behaviour metrics for one team (T) of an extracted replay dir."""
import gzip, json
def load(d):
    meta = json.load(open(d + '/meta.json'))
    rd = json.load(gzip.open(d + '/rounds.json.gz'))
    ev = [json.loads(l) for l in gzip.open(d + '/events.jsonl.gz', 'rt')]
    return meta, rd, ev
def metrics(d, T):
    meta, rd, ev = load(d)
    team = {c['id']: c['team'] for c in meta['champions']}
    typ = {c['id']: c['name'] for c in meta['champions']}
    f = {'rounds': rd['round'][-1], 'win': int(meta['result']['winner'] == T)}
    f['picks'] = meta['draft']['picks'][T]; f['opicks'] = meta['draft']['picks'][1 - T]
    def inc(k, x=1): f[k] = f.get(k, 0) + x
    # carried-bag exposure per champion-round
    for c in rd['champions']:
        side = 'us' if c['team'] == T else 'op'
        g = c['gems']
        for x in g:
            if x >= 100: inc(f'carry100_{side}')
            if x >= 150: inc(f'carry150_{side}')
            if x >= 40: inc(f'carry40_{side}')
        f[f'maxbag_{side}'] = max(f.get(f'maxbag_{side}', 0), max(g) if g else 0)
    R = rd['round']
    for side, tm in (('us', T), ('op', 1 - T)):
        cs = [c for c in rd['champions'] if c['team'] == tm]
        f[f'gold_{side}'] = sum(c['earned'][-1] for c in cs)
        i6 = min(len(R) - 1, 599); f[f'gold600_{side}'] = sum(c['earned'][i6] for c in cs)
        f[f'caps_{side}'] = 0
    starts = {}
    lastcancel = {}
    for e in ev:
        k = e['k']; r = e['r']
        if k == 'tribute_start':
            side = 'us' if team[e['a']] == T else 'op'
            inc(f'tstart_{side}'); g = e['gems']
            if g >= 100: inc(f'tstart100_{side}')
            if e['a'] in lastcancel and r - lastcancel[e['a']] <= 10: inc(f'restart10_{side}')
            starts[e['a']] = e
        elif k == 'tribute_end':
            side = 'us' if team[e['a']] == T else 'op'
            g = e.get('gems', 0); inc(f'trib_{side}'); inc(f'tribg_{side}', g)
            if g >= 100: inc(f'trib100_{side}'); inc(f'trib100g_{side}', g)
            if g < 40: inc(f'tribsmall_{side}')
        elif k == 'tribute_cancel':
            side = 'us' if team[e['a']] == T else 'op'
            cause = e.get('cause'); inc(f'tcan_{cause}_{side}')
            s = starts.get(e['a'])
            if s and cause == 'lock':
                ran = s['dur'] - e.get('left', 0)
                inc(f'lockcut_{side}'); inc(f'lockcut_ran_{side}', ran)
                if s['gems'] >= 100: inc(f'lockcut100_{side}')
                if e.get('left', 99) <= 2: inc(f'lockcut_late_{side}')
            lastcancel[e['a']] = r
        elif k == 'lock_place':
            side = 'us' if e['team'] == T else 'op'
            inc(f'lock_{"e" if r < 600 else "l"}_{side}')
        elif k == 'attack' and e.get('lock'):
            side = 'us' if team.get(e['a']) == T else 'op'
            inc(f'lockhit_{side}')
        elif k == 'capture':
            for sh in e.get('shares', []):
                if team.get(sh[0]) is not None: inc(f"capg_{'us' if team[sh[0]] == T else 'op'}", sh[1])
        elif k == 'death':
            vic = e['v']; side = 'us' if team[vic] == T else 'op'
            g = e.get('gems', 0) or 0
            inc(f'death_{side}'); inc(f'dgems_{side}', g)
            if g >= 40: inc(f'death40_{side}')
            if g >= 100: inc(f'death100_{side}')
            if e.get('cause') != 'Attack' and e.get('by') is None: inc(f'campdeath_{side}')
    return f
