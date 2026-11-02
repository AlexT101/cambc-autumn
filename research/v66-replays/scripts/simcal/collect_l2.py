# Level-2 sims (stand and chase, the port reproducing the bot's result) joined with what happened next.
# usage: collect_l2.py selfplay|ladder   -> replays/v66-analysis/simcal/l2_<src>.jsonl.gz
import sys, os, json, gzip
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor
sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'extract'))
import l2lib as L
import simport as SP

OUT = 'replays/v66-analysis/simcal'
W = 8  # rounds of realised exchange compared with the sim's first turns


class Truth:
    def __init__(self, X):
        self.X = X
        self.dmg = defaultdict(float)     # (r, attacker, victim)
        self.by_r = defaultdict(list)     # r -> [(attacker, victim, amount, kind)]
        self.heal = defaultdict(float)    # (r, target) from ally heals
        self.healer = defaultdict(float)  # (r, healer)
        self.stun = defaultdict(list)     # r -> [(caster, victim)]
        self.camp = defaultdict(float)    # (r, victim)
        self.deaths = defaultdict(list)
        self.attacks = defaultdict(int)   # (r, attacker): champion-damaging actions
        for e in X.ev:
            k = e['k']
            if k in ('attack', 'cast'):
                a = e['a']
                for v, amt in (e.get('dmg') or []):
                    if v in X.team and X.team[v] != X.team.get(a):
                        self.dmg[(e['r'], a, v)] += amt; self.by_r[e['r']].append((a, v, amt, e.get('ab') or 'basic'))
                        self.attacks[(e['r'], a)] += 1
                for v, amt in (e.get('heal') or []):
                    self.heal[(e['r'], v)] += amt; self.healer[(e['r'], a)] += amt
                for v in (e.get('stun') or []):
                    if v in X.team: self.stun[e['r']].append((a, v))
            elif k == 'camp_attack':
                if e.get('tgt') in X.team: self.camp[(e['r'], e['tgt'])] += e.get('dmg', 0)
            elif k == 'death':
                self.deaths[e['v']].append(e['r'])

    def death_in(self, cid, r, h):
        for d in self.deaths.get(cid, []):
            if r <= d <= r + h: return d - r
        return None


def margin(res):
    U, T = res['U'], res['T']
    if res['they_kill']:
        return -sum(max(0, f.health) for f in T.f) / max(1, sum(f.max_health for f in T.f))
    if res['we_kill']:
        return sum(max(0, f.health) for f in U.f) / max(1, sum(f.max_health for f in U.f))
    # horizon: both alive; their share of loss minus ours
    lu = 1 - sum(max(0, f.health) for f in U.f) / max(1, sum(f.health0 for f in U.f))
    lt = 1 - sum(max(0, f.health) for f in T.f) / max(1, sum(f.health0 for f in T.f))
    return 0.0 if lu == lt == 0 else (lt - lu) * 0.5


def record(src, key, opp, X, TR, r, c, tt, sides, res_line, typed, turn=()):
    us, them = typed
    res = L.run(sides, us, them, X, r)
    t = L.ptrade(res_line['t'])
    if not L.agrees(res, t): return None
    for side, fs in ((res['U'], us), (res['T'], them)):
        for g, f in zip(side.f, fs): g.health0 = f['health']
    U, T = res['U'], res['T']
    usid = [f['h'] for f in us]; thid = [f['h'] for f in them]
    self_h = c
    rr = range(r, r + W)
    row = dict(src=src, key=key, opp=opp, r=r, c=c, t=tt['t'], kind='stand' if res_line['k'] == 'home' else 'chase',
               why=res_line.get('why'), v=res_line.get('v'), take=res_line.get('take'), first=sides['first'],
               lost=int(res['they_kill'] > 0), tku=res['they_kill'], tkt=res['we_kill'], falls=int(res['self_falls']), fall_turn=res['fall_turn'],
               margin=round(margin(res), 3), n_us=len(us), n_them=len(them), hp=float(tt['hp']), mh=float(tt['mh']))
    row['us'] = [dict(h=f['h'], typ=f['typ'], hp=f['health'], mx=f['max'], sh=f['shield'], st=f['strength'], arr=f['arrives'], rd=f['ready'],
                      foc=g.focus_raw, fs=g.focus_scaled, tk=g.taken, shu=g.shield_until) for f, g in zip(us, U.f0)]
    row['them'] = [dict(h=f['h'], typ=f['typ'], hp=f['health'], mx=f['max'], sh=f['shield'], st=f['strength'], arr=f['arrives'], rd=f['ready'],
                        foc=g.focus_raw, fs=g.focus_scaled, tk=g.taken, shu=g.shield_until, vis=f.get('visible')) for f, g in zip(them, T.f0)]
    for side, S_ in (('us', U), ('them', T)):
        for f, g in zip(row[side], S_.f): f['pd'] = round(g.dealt5 / max(1, g.acts5), 1); f['pacts'] = g.acts5
    row['camp'] = float(sides.get('camp', 0)); row['self_i'] = int(sides['self'])
    # the sim's first target on our side: weakest by health + shield
    w = min(range(len(us)), key=lambda i: (us[i]['health'] + us[i]['shield'], i))
    row['sim_target'] = us[w]['h']
    # realised, per participant, per round of the window
    for side, ids, foes in (('us', usid, set(thid)), ('them', thid, set(usid))):
        for f, h in zip(row[side], ids):
            f['a_part'] = [round(sum(TR.dmg[(x, h, v)] for v in foes)) for x in rr]           # on sim participants
            f['a_any'] = [round(sum(a for (aa, v, a, _) in TR.by_r[x] if aa == h)) for x in rr]  # on any enemy champion
            f['a_hits'] = [TR.attacks[(x, h)] for x in rr]
            f['took'] = [round(sum(a for (aa, v, a, _) in TR.by_r[x] if v == h)) for x in rr]
            f['healed'] = [round(TR.heal[(x, h)]) for x in rr]
            f['heals_given'] = [round(TR.healer[(x, h)]) for x in rr]
            f['camp'] = [round(TR.camp[(x, h)]) for x in rr]
            f['death'] = TR.death_in(h, r, 20)
            f['alive_r'] = X.at(h, r, 'alive')
    # enemies outside the sim who hit our participants in the window
    ext = defaultdict(lambda: [0] * W)
    for k, x in enumerate(rr):
        for (a, v, amt, _) in TR.by_r[x]:
            if v in usid and a not in thid and X.team.get(a) != X.team.get(c): ext[a][k] += amt
    TN = {'Ryth': 'ryth', 'Vesper Vale': 'vesper', 'Vendetta': 'vendetta', 'Cassi': 'cassi', 'Issac': 'issac', 'Stellar': 'stellar', 'Prism': 'prism',
          'Marcella': 'marcella', 'Willow': 'willow', 'Ren': 'ren', 'Varg': 'varg', 'Tavi': 'tavi', 'Heart of Ruin': 'hor'}
    row['extra'] = [dict(h=a, typ=['ryth', 'vesper', 'vendetta', 'cassi', 'issac', 'stellar', 'prism', 'marcella', 'willow', 'ren', 'varg', 'tavi', 'hor'][X.ctype.get(a)], dmg=[round(z) for z in v], hp=X.at(a, r, 'hp'), mx=X.at(a, r, 'maxHp'),
                         st=X.at(a, r, 'str'), foc=X.at(a, r, 'foc'), cd=[X.at(a, r, 'cd0'), X.at(a, r, 'cd1')], tk=X.taken(a, r)) for a, v in ext.items()]
    row['stuns_on_us'] = sum(1 for x in rr for (a, v) in TR.stun[x] if v in usid)
    row['self_death'] = TR.death_in(self_h, r, 20)
    # enemies believed within 8 (seen in the last 2 rounds) but outside the sim, as the bot knew them
    me = tuple(map(int, tt['p'].split(','))) if tt.get('p') else None
    near = []
    for d in turn:
        if d['tag'] != 'TB' or d.get('s') != 'e' or d.get('al') != '1' or not d.get('p'): continue
        h = int(d['h'])
        if h in thid: continue
        try:
            q = tuple(map(int, d['p'].split(','))); age = r - int(d.get('pr', r))
        except Exception: continue
        if me is None or age > 2 or q[0] < 0: continue
        dist = max(abs(q[0] - me[0]), abs(q[1] - me[1]))
        if dist > 8: continue
        joined = any(a == h and v in usid for k in rr for (a, v, amt, _) in TR.by_r[k])
        near.append(dict(h=h, typ=d['t'], dist=dist, v=d.get('v') == '1', joined=joined, hp=X.at(h, r, 'hp'), mx=X.at(h, r, 'maxHp'),
                         st=X.at(h, r, 'str'), foc=X.at(h, r, 'foc'), cd=[X.at(h, r, 'cd0'), X.at(h, r, 'cd1')], tk=X.taken(h, r)))
    row['near'] = near
    return row


def from_lines(src, key, opp, lines, X, r0=0, r1=1 << 30):
    TR = Truth(X)
    T = L.turns(lines, r0, r1)
    rows = []
    for (r, c), turn in T.items():
        tt = [d for d in turn if d['tag'] == 'TT']
        if not tt or tt[0].get('a') != '1': continue
        last = None
        for d in turn:
            if d['tag'] == 'TE' and d.get('k') == 'sides': last = d; continue
            if d['tag'] == 'TE' and last is not None and (d.get('k') == 'prey_fight' or (d.get('k') == 'home' and d.get('why', '').startswith('stand'))):
                typed = L.type_fighters(turn, last, tt[0]['t'], c)
                if typed is not None:
                    try:
                        x = record(src, key, opp, X, TR, r, c, tt[0], last, d, typed, turn)
                    except Exception as ex:
                        x = None
                    if x: rows.append(x)
                last = None
    return rows


def one_selfplay(arg):
    m, path, gdir = arg
    X = L.Extract(OUT + '/spex', gdir)
    rows = []
    for team in 'ab':
        rows += from_lines('self', m + '-' + team, 'self', L.selfplay_lines(path, team), X)
    return rows


def one_ladder(key):
    import common as C
    MAN = {g['group'][:8] + '-' + str(g['position']): g['replay'] for g in json.load(open('replays/v66/manifest.json'))['games']}
    SRC = {g['source']: g for g in C.games(distinct=False)}
    g = SRC[MAN[key]]
    v = json.load(open(f'{OUT}/l2batch/{key}/trace_validation.json'))
    if v.get('status') != 'ok': return []
    trust = v.get('ladder_trusted_through') or 0
    lo, hi = map(int, (v.get('window') or '0-0').split('-'))
    X = L.Extract(C.EX, g['dir'])
    lines = gzip.open(f'{OUT}/l2batch/{key}/trace.stdout.gz', 'rt', errors='replace').read().splitlines()
    return from_lines('ladder', key, g['opp'], lines, X, lo, min(hi, trust - W))


if __name__ == '__main__':
    src = sys.argv[1]
    if src == 'selfplay':
        args = L.selfplay_games(OUT + '/selfplay', OUT + '/spex'); fn = one_selfplay
    else:
        args = sorted(os.listdir(OUT + '/l2batch')); args = [k for k in args if os.path.exists(f'{OUT}/l2batch/{k}/trace_validation.json')]; fn = one_ladder
    n = 0
    with ProcessPoolExecutor(20) as ex, gzip.open(f'{OUT}/l2_{src}.jsonl.gz', 'wt') as f:
        for rows in ex.map(fn, args):
            for x in rows: f.write(json.dumps(x) + '\n'); n += 1
    print(src, 'games', len(args), 'rows', n)
