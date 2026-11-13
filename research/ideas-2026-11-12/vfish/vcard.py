"""The Vesper scorecard: how far a team's play revolves around its Vesper (capture holders, gold and gem shares,
her stats and shop trips, cohesion, kills), per game and side.
    py vcard.py                    Fish r8 live (the 244 v117/v118 scrims): sides 'fish' and 'us' -> vfish.json
    py vcard.py EXT OUT.json       an ab.py batch's extract (bot 1, the candidate, is side 'fish'; bot 2 is 'us')
Read with vread.py."""
import json, gzip, os, sys, collections, statistics as st
from multiprocessing import Pool
LOCAL = len(sys.argv) > 1
ext = sys.argv[1] if LOCAL else '/home/ubuntu/tmp-offload/fishr8/live/ext'
rows = {} if LOCAL else json.load(open('/home/ubuntu/tmp-offload/fishr8/live/rows-r8-all.json'))
cheb = lambda a, b: max(abs(a[0] - b[0]), abs(a[1] - b[1]))
MAPS = {}
def game(job):
    d, mid = job
    if LOCAL: fish = 0 if mid.endswith('-12') else 1; r = None  # bot 1 (the candidate) plays the 'fish' role
    else: r = rows[mid]; fish = 1 if r['side'] == 'a' else 0
    p = f'{ext}/{d}'
    try:
        meta = json.load(open(p + '/meta.json')); R = json.load(gzip.open(p + '/rounds.json.gz'))
        ev = [json.loads(l) for l in gzip.open(p + '/events.jsonl.gz', 'rt')]
    except Exception as e: return None
    ch = R['champions']; n = len(R['round'])
    team = {c['id']: c['team'] for c in meta['champions']}; typ = {c['id']: c['name'] for c in meta['champions']}
    out = {}
    for side, t in (('fish', fish), ('us', 1 - fish)):
        V = [c for c in ch if c['team'] == t and typ[c['id']] == 'Vesper Vale']
        w = meta['result'].get('winner') if isinstance(meta.get('result'), dict) else meta.get('winner')
        o = {'has_v': bool(V), 'win': (w == t) if LOCAL else (r['result'] == 'win') == (side == 'us'), 'rounds': n}
        if not V: out[side] = o; continue
        v = V[0]; vid = v['id']
        mates = [c for c in ch if c['team'] == t and c['id'] != vid]
        caps = collections.Counter(); gold = collections.Counter(); gems = collections.Counter()
        clear_by = {}
        clearers = collections.Counter(); vnear_clear = []
        dmg_by = collections.defaultdict(collections.Counter)  # group -> champ -> dmg since respawn
        camp_g = {}
        for e in ev:
            k = e['k']
            if k == 'camp_attack': camp_g[e['camp']] = e['g']
            if k == 'camp_death': camp_g[e['camp']] = e['g']
        for e in ev:
            k = e['k']; rr = e['r']
            if k == 'attack' and 'cdmg' in e and team[e['a']] == t:
                for cid, dm in e['cdmg']:
                    g = camp_g.get(cid)
                    if g is not None: dmg_by[g][e['a']] += dm
            if k == 'cast' and team.get(e['a']) == t and 'cdmg' in e:
                for cid, dm in e['cdmg']:
                    g = camp_g.get(cid)
                    if g is not None: dmg_by[g][e['a']] += dm
            if k == 'group_clear': clear_by[e['g']] = (e.get('by'), rr)
            if k == 'group_respawn': dmg_by[e['g']] = collections.Counter()
            if k == 'capture' and e['team'] == t:
                sh = e['shares']; ids = [s[0] for s in sh]; ph = 'e' if rr <= 300 else 'l'
                kind = 'vsolo' if ids == [vid] else 'vshared' if vid in ids else 'osolo' if len(ids) == 1 else 'oshared'
                caps[(ph, kind)] += 1
                for cid, gm, go in sh:
                    gold[(ph, cid == vid)] += go; gems[(ph, cid == vid)] += gm
                # who did the damage on this group
                D = dmg_by.get(e['g'], {})
                tot = sum(D.values())
                if tot > 0 and kind in ('vsolo', 'vshared'):
                    o.setdefault('vdmg_share_on_vcaps_' + ph, []).append(D.get(vid, 0) / tot)
                    o.setdefault('ndmg_on_vcaps_' + ph, []).append(sum(1 for x in D.values() if x > 0.1 * tot))
                if kind == 'vsolo' and e['g'] in clear_by and clear_by[e['g']][0] is not None:
                    by, cr = clear_by[e['g']]; i = min(cr - 1, n - 1)
                    bp = (ch[by]['x'][i], ch[by]['y'][i])
                    if None not in bp:
                        o.setdefault('mates_near_vsolo_' + ph, []).append(sum(1 for m in mates if m['alive'][i] and m['x'][i] is not None and cheb((m['x'][i], m['y'][i]), bp) <= 5))
        for ph in 'el':
            tot = sum(caps[(ph, k)] for k in ('vsolo', 'vshared', 'osolo', 'oshared'))
            o['caps_' + ph] = tot
            for k in ('vsolo', 'vshared', 'osolo', 'oshared'): o[k + '_' + ph] = caps[(ph, k)]
            g = gold[(ph, True)] + gold[(ph, False)]; o['vgold_share_' + ph] = gold[(ph, True)] / g if g else None
            g = gems[(ph, True)] + gems[(ph, False)]; o['vgem_share_' + ph] = gems[(ph, True)] / g if g else None
        # tributes
        tg = collections.Counter(); 
        for e in ev:
            if e['k'] == 'tribute_end' and team[e['a']] == t: tg[e['a'] == vid] += e['gems']
        o['vtrib_share'] = tg[True] / (tg[True] + tg[False]) if tg[True] + tg[False] else None
        o['vtrib'] = tg[True]
        # shop
        shops = [e for e in ev if e['k'] == 'shop' and e['a'] == vid]
        o['vshop_rounds'] = sorted({e['r'] for e in shops})
        o['vrecalls'] = sum(1 for e in ev if e['k'] == 'recall_end' and e['a'] == vid)
        o['mrecalls'] = sum(1 for e in ev if e['k'] == 'recall_end' and team[e['a']] == t and e['a'] != vid) / max(1, len(mates))
        o['vtele'] = sum(1 for e in ev if e['k'] == 'teleport_start' and e['a'] == vid)
        seq = []
        for e in shops:
            for it, c in e.get('items', e.get('cons', {})).items(): seq.append((e['r'], it, c))
        o['vbuys'] = seq
        for rr in (100, 200, 300, 450, 600, 900):
            if rr <= n:
                i = rr - 1
                o[f'vearn_{rr}'] = v['earned'][i]; o[f'mearn_{rr}'] = sum(m['earned'][i] for m in mates) / max(1, len(mates))
                o[f'vstr_{rr}'] = v['str'][i]; o[f'vhp_{rr}'] = v['maxHp'][i]
                o[f'vgoldheld_{rr}'] = v['gold'][i]
                o[f'mhp_{rr}'] = sum(m['maxHp'][i] for m in mates) / max(1, len(mates))
        # cohesion: mates within 5 of Vesper when alive & off spawn
        for a, b in ((1, 100), (100, 300), (300, 600), (600, 2000)):
            xs = []
            for i in range(a - 1, min(b, n)):
                if not v['alive'][i] or v['x'][i] is None: continue
                vp = (v['x'][i], v['y'][i])
                xs.append(sum(1 for m in mates if m['alive'][i] and m['x'][i] is not None and cheb((m['x'][i], m['y'][i]), vp) <= 5) / max(1, len(mates)))
            if xs: o[f'coh_{a}'] = sum(xs) / len(xs)
        # mates' spend
        o['mbuys'] = collections.Counter()
        for e in ev:
            if e['k'] == 'shop' and team[e['a']] == t and e['a'] != vid:
                for it, c in e.get('items', {}).items(): o['mbuys'][typ[e['a']] + '|' + it] += c
        o['mbuys'] = dict(o['mbuys'])
        o['vkills'] = v['kills'][-1]; o['vdeaths'] = v['deaths'][-1]
        o['tkills'] = sum(c['kills'][-1] for c in ch if c['team'] == t); o['tdeaths'] = sum(c['deaths'][-1] for c in ch if c['team'] == t)
        s = next(c for c in meta['champions'] if c['id'] == vid)['stats']
        o['vchampdmg'] = s['championDamageDone']; o['vmondmg'] = s['monsterDamageDone']
        o['tchampdmg'] = sum(c['stats']['championDamageDone'] for c in meta['champions'] if c['team'] == t)
        o['tmondmg'] = sum(c['stats']['monsterDamageDone'] for c in meta['champions'] if c['team'] == t)
        o['picks'] = [typ[c['id']] for c in ch if c['team'] == t]
        T = [c for c in ch if c['team'] == t]
        for rr in (100, 300, 600):
            if rr <= n: o[f'tearn_{rr}'] = sum(c['earned'][rr - 1] for c in T)
        o['capgems300'] = sum(gm for e in ev if e['k'] == 'capture' and e['team'] == t and e['r'] <= 300 for _, gm, _ in e['shares'])
        o['capgems'] = sum(gm for e in ev if e['k'] == 'capture' and e['team'] == t for _, gm, _ in e['shares'])
        cl = {}; waits = {'v': [], 'o': []}
        for e in ev:
            if e['k'] == 'group_clear': cl[e['g']] = e['r']
            elif e['k'] == 'capture' and e['team'] == t and e['g'] in cl:
                waits['v' if vid in [s_[0] for s_ in e['shares']] else 'o'].append(e['r'] - cl.pop(e['g']))
        o['wait_v'] = waits['v']; o['wait_o'] = waits['o']
        o['gems_lost'] = sum(e.get('gems', 0) for e in ev if e['k'] == 'death' and team[e['v']] == t)
        o['v_gems_lost'] = sum(e.get('gems', 0) for e in ev if e['k'] == 'death' and e['v'] == vid)
        out[side] = o
    return out
if __name__ == '__main__':
    idx = json.load(open(ext + '/index.json'))['games']
    jobs = [(g['dir'], os.path.basename(g['source'])[:-8]) for g in idx if LOCAL or os.path.basename(g['source'])[:-8] in rows]
    with Pool(32) as p: res = [x for x in p.map(game, jobs, chunksize=2) if x]
    json.dump(res, open(sys.argv[2] if LOCAL else 'vfish.json', 'w'))
    print(len(res))
