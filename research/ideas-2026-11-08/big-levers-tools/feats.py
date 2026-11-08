# Per-game features of decoded scrims (ours vs Fish/Mite) for the big-levers loss-mode study.
# usage: feats.py ANA_DIR GAMES_JSON OUT.pkl
# Gem accounting: owned = tributed + carried. Owned changes only by captures (+), kill transfers (+ to killer's
# team, - to victim's) and camp kills (-). So the owned-gem gap splits exactly into capture, kill and camp terms.
import json, gzip, os, sys, pickle, collections
import numpy as np

ana, gj, out = sys.argv[1:4]
games = json.load(open(gj))
idx = json.load(open(sys.argv[4] if len(sys.argv) > 4 else os.path.join(ana, 'index.json')))['games']
CK = [100, 200, 300, 400, 500, 600, 800, 1000, 1200, 1500, 2000]
rows = []
cache = {}
for g in idx:
    match = os.path.basename(g['source']).split('.')[0]
    if match not in games or not g.get('ok', True):
        continue
    gm = games[match]
    d = os.path.join(ana, g['dir'])
    if g['dir'] in cache:
        r0 = dict(cache[g['dir']]); r0['match'] = match; r0['dup'] = True; rows.append(r0); continue
    try:
        meta = json.load(open(d + '/meta.json'))
        R = json.load(gzip.open(d + '/rounds.json.gz'))
        ev = [json.loads(l) for l in gzip.open(d + '/events.jsonl.gz', 'rt')]
    except Exception as e:
        print('skip', d, e, file=sys.stderr)
        continue
    us = 0 if gm['side'] == 'a' else 1
    team = {c['id']: c['team'] for c in meta['champions']}
    name = {c['id']: c['name'] for c in meta['champions']}
    n = len(R['round'])
    rr = np.array(R['round'])
    trib = np.array(R['gems'], dtype=float)  # [2][n]
    carried = np.zeros((2, n)); alive = np.zeros((2, n)); oof = np.zeros(2); earned = np.zeros((2, n))
    idle = np.zeros(2)
    for c in R['champions']:
        t = c['team']
        carried[t] += np.array(c['gems'], dtype=float)
        alive[t] += np.array(c['alive'], dtype=float)
        earned[t] += np.array(c['earned'], dtype=float)
        tu = np.array(c['turn'])
        oof[t] += (tu == 6).sum()
    # per-round flows
    cap = np.zeros((2, n + 2)); killx = np.zeros((2, n + 2)); campl = np.zeros((2, n + 2)); deaths = np.zeros((2, n + 2))
    campdeaths = np.zeros(2); kills = np.zeros(2); gemsdied = np.zeros(2)
    lockcancel = np.zeros(2); lockplace = np.zeros(2); blocked = np.zeros(2); tribs = np.zeros(2); tribgems = np.zeros(2)
    stuncancel = np.zeros(2); capres = np.zeros(2)
    capg = collections.Counter()  # (group, team) -> gems
    big_deaths = []  # (round, victim team, gems)
    for e in ev:
        k = e['k']; r = e['r']
        if k == 'capture':
            for cid, gems, gold in e['shares']:
                cap[team[cid], r] += gems
                capg[(e['g'], team[cid])] += gems
        elif k == 'death':
            vt = team[e['v']]
            deaths[vt, r] += 1
            gemsdied[vt] += e.get('gems', 0)
            if e.get('gems', 0) >= 50:
                big_deaths.append((r, vt, e.get('gems', 0), 'camp' if 'camp' in e and e.get('by') is None else 'champ'))
            if e.get('by') is not None and e.get('linked') is None:
                kt = team[e['by']]
                kills[kt] += 1
                killx[kt, r] += e.get('gemsTo', 0)
                killx[vt, r] -= e.get('gems', 0)
            elif e.get('by') is not None:
                kt = team[e['by']]
                killx[kt, r] += e.get('gemsTo', 0)
                killx[vt, r] -= e.get('gems', 0)
            else:
                campl[vt, r] -= e.get('gems', 0)
                campdeaths[vt] += 1
        elif k == 'tribute_cancel':
            t = team[e['a']]
            if e.get('cause') == 'lock':
                lockcancel[t] += e.get('gems', 0)
            elif e.get('cause') == 'stun':
                stuncancel[t] += e.get('gems', 0)
        elif k == 'lock_place':
            lockplace[team[e['a']]] += 1
        elif k == 'tribute_blocked':
            blocked[team[e['a']]] += 1
        elif k == 'tribute_end':
            tribs[team[e['a']]] += 1; tribgems[team[e['a']]] += e['gems']
        elif k == 'capture_reset':
            capres[e['team']] += 1
    # owned gap from our view, per round index (rounds 1..n)
    owned = trib + carried
    me, op = us, 1 - us
    ck = {}
    for c in CK:
        i = min(c, n) - 1
        ck[c] = dict(trib=(trib[me, i], trib[op, i]), car=(carried[me, i], carried[op, i]),
                     gold=(earned[me, i], earned[op, i]), alive=(alive[me, i], alive[op, i]),
                     cap=(cap[me, :c + 1].sum(), cap[op, :c + 1].sum()), killx=(killx[me, :c + 1].sum(), killx[op, :c + 1].sum()),
                     campl=(campl[me, :c + 1].sum(), campl[op, :c + 1].sum()), past=c > n)
    diff = owned[me] - owned[op]
    tdiff = trib[me] - trib[op]
    win = gm['result'] == 'win'
    # last round the eventual loser led in owned gems
    lead_sign = np.sign(diff) * (1 if win else -1)  # positive = eventual winner ahead
    behind = np.where(lead_sign < 0)[0]
    last_lead = int(rr[behind[-1]]) if len(behind) else 0
    # worst 100-round window for the eventual loser, split into flows
    def win_flows(a, b):
        return dict(cap=cap[me, a:b].sum() - cap[op, a:b].sum(), kill=killx[me, a:b].sum() - killx[op, a:b].sum(),
                    camp=campl[me, a:b].sum() - campl[op, a:b].sum())
    swing = [(diff[min(i + 100, n - 1)] - diff[i], i) for i in range(0, max(1, n - 100), 10)]
    worst = min(swing) if not win else max(swing)
    rows.append(dict(
        match=match, dir=g['dir'], version=gm['version'], opp=gm['opp_name'], map=gm['map'], side=gm['side'], win=win,
        rounds=n, end=gm['end_reason'], our_picks=gm['our_picks'], opp_picks=gm['opp_picks'],
        trib_end=(trib[me, -1], trib[op, -1]), car_end=(carried[me, -1], carried[op, -1]),
        gold_end=(earned[me, -1], earned[op, -1]),
        cap=(cap[me].sum(), cap[op].sum()), killx=(killx[me].sum(), killx[op].sum()), campl=(campl[me].sum(), campl[op].sum()),
        kills=(kills[me], kills[op]), deaths=(deaths[me].sum(), deaths[op].sum()), campdeaths=(campdeaths[me], campdeaths[op]),
        gemsdied=(gemsdied[me], gemsdied[op]), lockcancel=(lockcancel[me], lockcancel[op]), stuncancel=(stuncancel[me], stuncancel[op]),
        lockplace=(lockplace[me], lockplace[op]), blocked=(blocked[me], blocked[op]), tribs=(tribs[me], tribs[op]),
        tribgems=(tribgems[me], tribgems[op]), capres=(capres[me], capres[op]), oof=(oof[me], oof[op]),
        ck=ck, last_lead=last_lead, worst=(worst[1], worst[0], win_flows(worst[1], min(worst[1] + 100, n))),
        diff=diff[::10].astype(np.float32), tdiff=tdiff[::10].astype(np.float32),
        alive_d=(alive[me] - alive[op])[::10].astype(np.float32),
        own_me=owned[me].astype(np.float32), own_op=owned[op].astype(np.float32),
        trib_me=trib[me].astype(np.float32), trib_op=trib[op].astype(np.float32),
        alive_me=alive[me].astype(np.int8), alive_op=alive[op].astype(np.int8),
        capr=(cap[me, :n + 1], cap[op, :n + 1]), killr=(killx[me, :n + 1], killx[op, :n + 1]),
        big_deaths=[(r, vt == me, gm_, how) for r, vt, gm_, how in big_deaths],
        capg={f'{gk}:{"me" if t == me else "op"}': v for (gk, t), v in capg.items()},
        mapHash=g['mapHash'], copies=g.get('copies', 1), dup=False,
    ))
    cache[g['dir']] = rows[-1]
pickle.dump(rows, open(out, 'wb'))
print(len(rows), 'rows')
