#!/usr/bin/env python3
"""s3: the tables (markdown) from replays/.s3cache/rows.pkl (study.py) and endrace.pkl (endrace.py).
Usage: report.py > tables.md"""
import collections, os, pickle, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib import CACHE

R = pickle.load(open(os.path.join(CACHE, 'rows.pkl'), 'rb'))
E = pickle.load(open(os.path.join(CACHE, 'endrace.pkl'), 'rb'))
NG = len(R['game'])
BOTH = {g['sha'] for g in R['game'] if g['both']}


def q(xs, nd=0):
    xs = sorted(x for x in xs if x is not None)
    if not xs:
        return '-'
    f = (lambda v: f'{v:.{nd}f}')
    return f'{f(xs[len(xs) // 4])} / {f(xs[len(xs) // 2])} / {f(xs[3 * len(xs) // 4])}'


def pct(a, b):
    return f'{100 * a / b:.0f}%' if b else '-'


def table(head, rows):
    out = ['| ' + ' | '.join(head) + ' |', '|' + '---|' * len(head)]
    out += ['| ' + ' | '.join(str(c) for c in r) + ' |' for r in rows]
    return '\n'.join(out)


def shares(counter, n=8):
    t = sum(counter.values()) or 1
    return ' '.join(f'{k} {100 * v / t:.0f}' for k, v in counter.most_common(n))


print(f'# s3 tables\n\n{NG} games ({len(BOTH)} with a Prism on each side). 494 of the 512 map pairs are the same game '
      'played twice (mirror, sides swapped), so the independent sample is ~530 games; counts are over all 1,024.\n')

# ------------------------------------------------------------------ Q1
S = [e for e in R['enc'] if e['ratio'] >= 1.5]


def closer(e):
    cs, cw = e['cs'], e['cw']
    if cs <= -2 and cw <= -2:
        return 'both'
    if cs < cw and cs <= -2:
        return 'strong'
    if cw < cs and cw <= -2:
        return 'weak'
    return 'neither'


def wact(e):
    if 'E' in e['bw']:
        return 'E stop_ender'
    return {'F': 'F farm', 'R': 'R retreat', 'B': 'B bank', 'C': 'C chase', 'U': 'U altar guard', 'P': 'P hold',
            'T': 'T tribute', 'X': 'X contest', 'G': 'G siege'}.get(e['bw'][-1], 'other')


def sact(e):
    if 'T' in e['bs'][-3:]:
        return 'T'
    return e['bs'][-1]


print('## Q1 encounters (both Prisms alive within 6; a new one after 20 rounds apart)\n')
byr = collections.defaultdict(collections.Counter)
for e in R['enc']:
    k = '<1.2' if e['ratio'] < 1.2 else '1.2-1.5' if e['ratio'] < 1.5 else '1.5-2' if e['ratio'] < 2 else '2-3' if e['ratio'] < 3 else '3+'
    byr[k][e['out']] += 1
print(table(['Focus x health ratio', 'encounters', 'weak dies <=20 r', 'strong dies <=20 r'],
            [[k, sum(byr[k].values()), pct(byr[k]['weak_died'], sum(byr[k].values())), pct(byr[k]['strong_died'], sum(byr[k].values()))]
             for k in ['<1.2', '1.2-1.5', '1.5-2', '2-3', '3+']]))
print(f'\nRatio >= 1.5: {len(S)} encounters ({len(S) / len(BOTH):.2f} a both-Prism game), in {len({e["sha"] for e in S})} games.\n')
cc = collections.Counter(closer(e) for e in S)
print('Who closed the distance (sum over the 10 rounds before of each Prism\'s own step against the other\'s last tile; '
      'a side "closed" with a sum <= -2):\n')
rows = []
for k in ['weak', 'strong', 'both', 'neither']:
    sub = [e for e in S if closer(e) == k]
    rows.append([k, len(sub), pct(len(sub), len(S)), pct(sum(e['out'] == 'weak_died' for e in sub), len(sub))])
print(table(['closer', 'encounters', 'share', 'weak dies <=20 r'], rows))
print('\nBy the weak Prism\'s activity (E if it was in stop_ender in the 10 rounds before, else its branch at the encounter):\n')
rows = []
for k, n in collections.Counter(wact(e) for e in S).most_common():
    sub = [e for e in S if wact(e) == k]
    m = len(sub)
    rows.append([k, m, pct(sum(e['out'] == 'weak_died' for e in sub), m), pct(sum(closer(e) == 'weak' for e in sub), m),
                 pct(sum(closer(e) == 'strong' for e in sub), m), shares(collections.Counter(sact(e) for e in sub), 4),
                 pct(sum(e['w_sees'] for e in sub), m), pct(sum(e['w_sees'] or e['w_seen10'] for e in sub), m),
                 pct(sum(e['fg_d'] is not None and e['fg_d'] <= 4 for e in sub), m),
                 pct(sum(e['fg_d'] is not None and e['fg_d'] <= 8 for e in sub), m),
                 pct(sum(e['w_own'] for e in sub), m), q([e['w_gems'] for e in sub]), q([e['s_gems'] for e in sub]),
                 pct(sum(e['s_burst'] >= e['w_hp'] for e in sub), m), pct(sum(e['w_burst'] >= e['s_hp'] for e in sub), m)])
print(table(['weak doing', 'n', 'weak dies', 'weak closed', 'strong closed', 'strong branch %', 'weak sees strong',
             'seen <=10 r', 'weak farm target <=4 of strong', '<=8', 'weak on own ground', 'weak bag q1/med/q3',
             'strong bag', 'strong 2-turn burst >= weak hp', 'weak burst >= strong hp'], rows))
F = [e for e in S if wact(e) == 'F farm']
side = collections.Counter(e['wfg_side'] for e in F)
print(f'\nWeak farming ({len(F)}): its farm group on its own side {side["own"]}, middle {side["mid"]}, the strong side '
      f'{side["enemy"]}. Strong Prism standing on its own ground {sum(e["s_own"] for e in F)}.\n')

# ------------------------------------------------------------------ Q2
print('## Q2 Prism deaths\n')
D = R['death']
print('All Prism deaths by killer: ' + ', '.join(f'{k} {v}' for k, v in collections.Counter(d['kname'] for d in D).most_common(8)) + '\n')
first = {}
for d in sorted(D, key=lambda d: d['r']):
    if d['sha'] in BOTH and d['sha'] not in first:
        first[d['sha']] = d
FD = list(first.values())
print(f'First Prism death in both-Prism games: {len(FD)}; the victim\'s team lost {sum(d["winner"] != d["vteam"] for d in FD)}. '
      'Killers: ' + ', '.join(f'{k} {v}' for k, v in collections.Counter(d['kname'] for d in FD).most_common(6)) + '.\n')


def ctx(d):
    if 'E' in d['v_br_window'][:-1]:
        return 'E stop_ender'
    if d['k_chan_pre'] == 2:
        return 'killer tributing'
    if 'R' in d['v_br_window'][-6:-1]:
        return 'R retreat (last 5)'
    return 'other'


def death_rows(sub_all, label):
    rows = []
    for k in ['R retreat (last 5)', 'E stop_ender', 'other', 'killer tributing']:
        for wl, cond in (('weak', lambda d: d['k_pow_ratio_first'] >= 1.5), ('not weak', lambda d: d['k_pow_ratio_first'] < 1.5)):
            sub = [d for d in sub_all if ctx(d) == k and cond(d)]
            m = len(sub)
            if not m:
                continue
            mv = [sum(d['moves'][i] for d in sub) for i in range(3)]
            tm = sum(mv) or 1
            rows.append([k, wl, m, pct(sum(d['v_team_won'] for d in sub), m), q([d['window'] for d in sub]),
                         pct(sum(d['saw'] for d in sub), m), q([d['d_first'] for d in sub]),
                         f'{100 * mv[0] / tm:.0f}/{100 * mv[1] / tm:.0f}/{100 * mv[2] / tm:.0f}',
                         shares(collections.Counter(ch for d in sub for ch in d['v_br_window'][:-1]), 4),
                         shares(collections.Counter(ch for d in sub for ch in d['k_br_window'][:-1]), 3),
                         q([d['v_spawn_steps'] for d in sub]), q([d['v_ally'] for d in sub]), q([d['v_altar'] for d in sub]),
                         pct(sum(d['v_recall_hit'] > 0 for d in sub), m), pct(sum(d['v_dmg_to_k'] > 0 for d in sub), m),
                         q([d['v_dmg_to_k'] for d in sub]), q([d['k_hpfrac_end'] for d in sub], 2),
                         pct(sum(d['v_burst_first'] >= d['k_hp_first'] for d in sub), m),
                         pct(sum(d['k_burst_first'] >= d['v_hp_first'] for d in sub), m),
                         pct(sum(d['r_forgone'] > 0 for d in sub), m), sum(d['r_forgone_dmg'] >= d['k_hp_end'] for d in sub),
                         q([d['gems'] for d in sub])])
    print(f'\n{label}\n')
    print(table(['context', 'power', 'n', 'victim team won', 'rounds first sight -> death', 'victim saw killer',
                 'dist at first sight', 'victim steps away/toward/still %', 'victim branches %', 'killer branches %',
                 'victim spawn steps', 'nearest ally', 'nearest altar', 'kept recall cut', 'fought back (dmg>0)',
                 'dmg to killer', 'killer health at end', 'victim 2-turn burst >= killer hp at sight',
                 'killer burst >= victim hp', 'retreat walked in reach with a spell ready', 'forgone casts >= killer end hp',
                 'bag lost'], rows))


PD = [d for d in FD if d['kname'] == 'Prism' and 'window' in d]
death_rows(PD, f'First Prism death per game, by the enemy Prism ({len(PD)}). Power = killer/victim Focus x health at '
               'first sight; weak >= 1.5. Burst: both ready spells (1.5F stun, 1.0F ground) and two basics.')
AD = [d for d in D if d['kname'] == 'Prism' and 'window' in d]
death_rows(AD, f'Every Prism death by the enemy Prism ({len(AD)}, repeated deaths in one game included)')

# ------------------------------------------------------------------ Q3
print('\n## Q3 the dominant Prism (Focus >= 2x the enemy Prism\'s, both alive)\n')
Dm = R['dom']
ph = collections.Counter()
sd, sh, sg, nb, gate, know = (collections.Counter() for _ in range(6))
for d in Dm:
    ph.update(d['phase']); sd.update(d['seen_d']); sh.update(d['seen_hit']); sg.update(d['seen_got'])
    nb.update(d['nohit_br']); gate.update(d['gate'])
    if d['bd_team']:
        know.update(d['know'])
tot = sum(d['rounds'] for d in Dm)
print(f'{len(Dm)} dominant Prism-games, {tot} dominant rounds. "win": the dominant Prism\'s bag plus its team\'s score '
      'reaches 1,000 (keeps_gems lets go, it banks); "mid": before that.\n')
rows = []
for P in ['mid', 'win']:
    t = sum(v for (p, b), v in ph.items() if p == P)
    c = collections.Counter({b: v for (p, b), v in ph.items() if p == P})
    seen = sum(v for (p, k), v in sd.items() if p == P)
    rows.append([P, t, pct(t, tot), shares(c, 8), pct(seen, t)])
print(table(['phase', 'rounds', 'share', 'branch % (D lines)', 'sees the weak Prism'], rows))
print('\nRounds the dominant Prism sees the weak one, by distance: who hits whom that round (events), and what the '
      'dominant one does when it does not hit:\n')
rows = []
for P in ['mid', 'win']:
    for k in ['d<=4', 'd5-6', 'd7-8', 'd>8']:
        n = sd[(P, k)]
        c = collections.Counter({b: v for (p, db, b), v in nb.items() if p == P and db == k})
        rows.append([P, k, n, pct(sh[(P, k)], n), pct(sg[(P, k)], n), shares(c, 6)])
print(table(['phase', 'distance', 'rounds seen', 'dominant hits weak', 'weak hits dominant', 'no-hit branch %'], rows))
print('\nSeen, neither chasing (C) nor hitting: the chase gate (`preyable`, fight.cc:747) as the replay reads it '
      '(own_ground by walking steps; hurt = health < 0.453 max):\n')
rows = []
for P in ['mid', 'win']:
    c = {k: v for (p, k), v in gate.items() if p == P and not k.startswith('branch')}
    t = sum(c.values())
    rows.append([P, t] + [pct(c.get(k, 0), t) for k in ['their_ground_healthy_nobag', 'their_ground_healthy_bag',
                                                         'preyable_by_ground', 'd>8', 'near_enemy_spawn']])
print(table(['phase', 'rounds', 'weak healthy on its ground, no bag', '... with a bag (intercept_steps decides)',
             'preyable (our ground, hurt or <=3)', 'beyond 8', 'by its spawn'], rows))
C = R['chase']
print(f'\nEngagement episodes (dominant sees weak and chases or hits it; ends at the first round it does neither): {len(C)}, '
      f'{sum(c["killed"] for c in C)} end in the dominant Prism\'s kill.\n')
rows = []
for k, n in collections.Counter(c['end'] for c in C).most_common():
    sub = [c for c in C if c['end'] == k]
    rows.append([k, n, sum(c['killed'] for c in sub), q([c['n'] for c in sub]),
                 shares(collections.Counter(c.get('end_br') for c in sub if c.get('end_br')), 4),
                 pct(sum(c.get('end_enemy_near', 0) >= 2 for c in sub), n), pct(sum(c.get('end_s_hpf', 1) < 0.4533 for c in sub), n),
                 pct(sum(bool(c.get('end_w_own')) for c in sub), n), pct(sum(c.get('end_w_hpf', 1) >= 0.4533 for c in sub), n),
                 pct(sum(c.get('end_w_gems', 0) > 0 for c in sub), n)])
print(table(['end', 'episodes', 'kills', 'length q', 'branch at end %', '2+ other enemies within 6',
             'dominant hurt', 'weak on its own ground', 'weak healthy', 'weak carries gems'], rows))
t = know.get('bd_n', 0)
print(f'\nBelief about the weak Prism (kr-beliefs side, dump every 10 rounds, {t} samples in dominant rounds): visible '
      f'{pct(know.get("bd_visible", 0), t)}, tracked with <=9 possible tiles {pct(know.get("bd_cnt<=9", 0), t)}, <=49 '
      f'{pct(know.get("bd_cnt<=49", 0), t)}, more {pct(know.get("bd_cnt<=200", 0) + know.get("bd_cnt>200", 0), t)}, '
      f'untracked {pct(know.get("bd_untracked", 0), t)} (`track_horizon` = 3 rounds after the last sight). Seen in the '
      f'last 10 rounds: {pct(sum(d["seen10"] for d in Dm), tot)} of dominant rounds.\n')
G = [g for g in R['game'] if g.get('dom') and g['sus']]
rows = []
for k, f in (('weak killed by the dominant Prism', lambda g: any(x[3] for x in g['w_deaths'])),
             ('weak died otherwise', lambda g: g['w_deaths'] and not any(x[3] for x in g['w_deaths'])),
             ('weak never died', lambda g: not g['w_deaths'])):
    sub = [g for g in G if f(g)]
    rows.append([k, len(sub), pct(sum(g['won'] for g in sub), len(sub))])
print(f'Sustained dominance (ratio held 10 rounds in a row; {len(G)} games), after its onset:\n')
print(table(['weak Prism', 'games', 'dominant team wins'], rows))

# ------------------------------------------------------------------ Q4
print('\n## Q4 dominant-team losses\n')
GD = [g for g in R['game'] if g.get('dom')]
L = [g for g in GD if not g['won']]


def cls(g):
    if g['w_trib_at_onset'] and g['end_gap'] <= 5:
        return '1 the weak Prism\'s winning tribute made the onset'
    if g['s_deaths']:
        return '2 dominant Prism killed later'
    if any(c in ('stun', 'lock') and gm + su >= 1000 for r, c, gm, l, su, th in g['s_tcancel_ctx']):
        return '3 winning tribute stunned or locked'
    if g['round_limit']:
        return '5 round limit'
    if g['s_alive_end'] and g['s_bag_end'] >= 50:
        return '4 out-tributed while holding its bag'
    return '6 out-raced after banking'


print(f'Onset as the brief defines it (first round Focus >= 2x, both alive): {len(GD)} games, the dominant team wins '
      f'{sum(g["won"] for g in GD)} ({pct(sum(g["won"] for g in GD), len(GD))}). Onset at the weak Prism\'s own tribute '
      f'(its bag left, Focus fell): {sum(g["w_trib_at_onset"] for g in GD)}.\n')
rows = []
for k in sorted({cls(g) for g in L}):
    sub = [g for g in L if cls(g) == k]
    br = collections.Counter()
    for g in sub:
        br.update(g['dom_branch'])
    rows.append([k, len(sub), sum(bool(g['sus']) for g in sub), q([g['dom'] for g in sub]), q([g['end_gap'] for g in sub]),
                 q([g['gems_us'] for g in sub]), q([g['s_bag_end'] for g in sub]), sum(g['gems_us'] + g['s_bag_end'] >= 1000 for g in sub),
                 sum(g['gems_us'] + g['bag_us_end'] >= 1000 for g in sub), shares(br, 5)])
print(table(['class (first that applies)', 'losses', 'with a sustained onset', 'onset round', 'rounds onset -> end',
             'our score at end', 'dominant bag at end', 'score + its bag >= 1000', 'score + team bags >= 1000',
             'dominant branches after onset %'], rows))
k2 = [g for g in L if cls(g).startswith('2')]
print(f'\nClass 2 killers (first death after onset): ' + ', '.join(f'{k} {v}' for k, v in collections.Counter(g['s_deaths'][0][1] for g in k2).most_common()) +
      f'; bag lost {q([g["s_deaths"][0][2] for g in k2])}; rounds after onset {q([g["s_deaths"][0][0] - g["dom"] for g in k2])}.\n')

# ------------------------------------------------------------------ end of the race
print('## The end of the race (every game)\n')
P = [r for r in E if r['lo_prism'] and not r['rl']]
c = collections.Counter()
for r in P:
    c['score + carried bags >= 1000'] += r['lo_score'] + r['lo_bags'] >= 1000
    c['score + Prism bag >= 1000'] += r['lo_score'] + r['lo_p_bag'] >= 1000
    c['Prism in a tribute channel'] += r['lo_p_chan'] == 2
    c['Prism channelling a winning bag'] += r['lo_p_chan'] == 2 and r['lo_score'] + r['lo_p_bag'] >= 1000
    c['Prism\'s winning bag stunned or locked at least once'] += r['lo_p_winbag_from'] is not None and any(x[0] >= r['lo_p_winbag_from'] for x in r['lo_p_cancels'])
print(f'Losers with a Prism, game ended by the win ({len(P)}), at the winner\'s last tribute:\n')
print(table(['loser', 'games'], [[k, v] for k, v in c.items()]))
sz = [g for r in E for t, Lt in r['prism_tributes'].items() for (rr, g) in Lt]
st = [d for r in E for t, Lt in r['prism_starts'].items() for (rr, g, d) in Lt]
cc = collections.Counter(x[1] for r in E for t, Lt in r['prism_cancels'].items() for x in Lt)
npg = sum(len(r['prism_tributes']) for r in E)
W = [r for r in E if r['w_prism'] and r.get('w_p_winbag_from')]
print(f'\nPrism tributes: {len(sz)} completed ({len(sz) / npg:.2f} a Prism-game), bag {q(sz)}; {len(st)} channels started, '
      f'length {q(st)} turns; cancels: ' + ', '.join(f'{k} {v}' for k, v in cc.most_common()) + '.')
print(f'Winners whose Prism held a winning bag ({len(W)}): rounds from that to the end {q([r["T"] - r["w_p_winbag_from"] for r in W])}; '
      f'its channel stunned or locked at least once in {sum(any(x[0] >= r["w_p_winbag_from"] for x in r["w_p_cancels"]) for r in W)}. '
      'Winning tributes by: ' + ', '.join(f'{k} {v}' for k, v in collections.Counter(r['w_last'][2] for r in E if 'w_last' in r).most_common(4)) + '.')

# ------------------------------------------------------------------ duels
FS = pickle.load(open(os.path.join(CACHE, 'firststrike.pkl'), 'rb'))
print('\n## Prism duels: who stepped into cast reach (4) and who hit first (every Prism death by the enemy Prism)\n')
rows = []
for lab, cond in (('weak victim', lambda r: r['k_ratio'] >= 1.5), ('not weak', lambda r: r['k_ratio'] < 1.5)):
    for cl, cc in (('stop_ender in window', lambda r: 'E' in r['v_br']), ('no stop_ender', lambda r: 'E' not in r['v_br'])):
        sub = [r for r in FS if cond(r) and cc(r)]
        n = len(sub)
        en = collections.Counter((r['entry'][1] if r['entry'] else '-') for r in sub)
        fs = collections.Counter((r['first'][2] if r['first'] else '-') for r in sub)
        rows.append([lab, cl, n, pct(en['a'], n), pct(en['b'], n), pct(en['both'], n), pct(fs['a'], n), pct(fs['b'], n)])
print(table(['victim', 'context', 'deaths', 'victim stepped in', 'killer stepped in', 'both', 'victim hit first', 'killer hit first'], rows))
