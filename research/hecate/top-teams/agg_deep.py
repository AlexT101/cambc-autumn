import pickle
from collections import Counter, defaultdict
from statistics import mean, median

from common import TOP, US, SHORT, ref

F = pickle.load(open(__file__.replace('agg_deep.py', 'deep.pkl'), 'rb'))
TEAMS = TOP + [US]


def pct(a, b):
    return f'{100 * a / b:.0f}%' if b else '-'


def camp_range():
    print('## Camp damage by attacker distance (camps hit only within 3)\n')
    st = defaultdict(Counter)
    ch = defaultdict(lambda: defaultdict(Counter))
    kinds = defaultdict(Counter)
    for f in F:
        T = f['team_of']
        for c, dd in f['camp_dmg_dist'].items():
            n = f['names'][T[c]]
            ty = f['types'][c]
            for d, amt in dd.items():
                st[n][d] += amt
                st[n]['tot'] += amt
                ch[n][ty][d] += amt
                ch[n][ty]['tot'] += amt
        for c, v in f['camp_taken'].items():
            st[f['names'][T[c]]]['taken'] += v
        for c, dd in f['camp_dmg_kind'].items():
            n = f['names'][T[c]]
            for (k, d), amt in dd.items():
                kinds[n][(k, d)] += amt
    print('| team | dmg from d<=1 | d=2 | d=3 | d=4+ | camp dmg taken per 1000 dealt |')
    print('|---|---|---|---|---|---|')
    for n in TEAMS:
        s = st[n]
        t = s['tot']
        if not t:
            continue
        print(f"| {SHORT[n]} | {pct(s[0]+s[1], t)} | {pct(s[2], t)} | {pct(s[3], t)} | {pct(s[4]+s[5], t)} | {1000*s['taken']/t:.0f} |")
    print()
    print('Per champion share of camp damage dealt from distance 4+ (team: champ share [total dmg]):')
    for ty in ('Stellar', 'Prism', 'Cassi', 'Tavi', 'Ren', 'Ryth', 'Marcella'):
        row = []
        for n in TEAMS:
            c = ch[n][ty]
            if c['tot'] > 20000:
                row.append(f"{SHORT[n]} {pct(c[4]+c[5], c['tot'])}")
        print(f'- {ty}: ' + ', '.join(row))
    print()
    for n in ('Intercontinental Fish', 'Mite', 'procless', US):
        k = kinds[n]
        far = {kk: v for kk, v in k.items() if kk[1] >= 4}
        tot = sum(far.values())
        print(f"- {SHORT[n]} d>=4 damage by ability: " + ', '.join(f'{kk[0]} {100*v/tot:.0f}%' for kk, v in sorted(far.items(), key=lambda x: -x[1])[:4]))
    print()


def kills():
    print('## Victim activity at death (kills made by team)\n')
    st = defaultdict(Counter)
    hp0 = defaultdict(list)
    chase = defaultdict(list)
    natt = defaultdict(list)
    kd0 = defaultdict(list)
    ex = defaultdict(list)
    for f in F:
        T = f['team_of']
        for d in f['kills']:
            n = f['names'][T[d['k']]]
            st[n]['n'] += 1
            for a in d['act']:
                st[n][a] += 1
            if 'farming' in d['act'] or 'camp_hurt' in d['act']:
                st[n]['farm_any'] += 1
                if len(ex[(n, 'farm')]) < 3 and n in TOP[:5]:
                    ex[(n, 'farm')].append(f"{ref(f['rec'], d['r0'])}-{d['r']} {f['types'][d['v']]}")
            if 'ambushed' in d['act'] and d['kbush0']:
                st[n]['amb_bush'] += 1
            hp0[n].append(d['hp0'])
            if d['chase'] is not None:
                chase[n].append(d['chase'])
            natt[n].append(d['n_att'])
            if d['kdist0'] is not None:
                kd0[n].append(d['kdist0'])
            st[n]['dur'] += d['r'] - d['r0']
    keys = ['farming', 'camp_hurt', 'farm_any', 'on_capture_tile', 'recalling', 'tributing', 'near_altar', 'bag30', 'ambushed', 'amb_bush']
    print('| team | kills | ' + ' | '.join(keys) + ' | victim hp at first hit (median) | victim moved from first hit to death (median, mean) | attackers (mean) | first-hit to kill rounds (mean) |')
    print('|' + '---|' * (len(keys) + 6))
    for n in TEAMS:
        s = st[n]
        if not s['n']:
            continue
        print(f"| {SHORT[n]} | {s['n']} | " + ' | '.join(pct(s[k], s['n']) for k in keys) + f" | {median(hp0[n]):.2f} | {median(chase[n])}, {mean(chase[n]):.1f} | {mean(natt[n]):.2f} | {s['dur']/s['n']:.1f} |")
    print()
    for n in TOP[:5]:
        for e in ex[(n, 'farm')][:2]:
            print(f'- {SHORT[n]} kill on farmer: {e}')
    print()


def wards():
    print('## Wards\n')
    st = defaultdict(Counter)
    for f in F:
        T = f['team_of']
        for t in (0, 1):
            n = f['names'][t]
            st[n]['games'] += 1
            if f['nbush'] == 0:
                st[n]['nobush_games'] += 1
        for w in f['wards']:
            n = f['names'][T[w['a']]]
            st[n]['w'] += 1
            if f['nbush'] == 0:
                st[n]['w_nobush'] += 1
            st[n]['bush'] += w['bush']
            st[n]['me_bush'] += bool(w['me_bush'])
            if w['d'] is not None:
                st[n]['d' + str(w['d'])] += 1
    print('| team | wards/g | games on bushless maps | wards on bushless maps | ward in bush | placer in bush | placed at distance 0/1/2 |')
    print('|---|---|---|---|---|---|---|')
    for n in TEAMS:
        s = st[n]
        if not s['games']:
            continue
        W = max(1, s['w'])
        print(f"| {SHORT[n]} | {s['w']/s['games']:.0f} | {s['nobush_games']} | {s['w_nobush']} | {pct(s['bush'], W)} | {pct(s['me_bush'], W)} | {pct(s['d0'], W)}/{pct(s['d1'], W)}/{pct(s['d2'], W)} |")
    print()


def tcancel():
    print('## Tribute cancels and recalls\n')
    st = defaultdict(Counter)
    for f in F:
        T = f['team_of']
        for c in f['tcancel']:
            n = f['names'][T[c['a']]]
            st[n]['c_' + str(c['cause'])] += 1
            if c['cause'] == 'manual':
                st[n]['m_gems'] += c['gems']
                st[n]['m_near'] += c['near_enemy'] > 0
                st[n]['m_dur'] += (c['r'] - c['started']) if c['started'] else 0
        for t in (0, 1):
            st[f['names'][t]]['games'] += 1
        for r in f['recall_end']:
            n = f['names'][T[r['a']]]
            st[n]['rec'] += 1
            st[n]['rec_lowhp'] += r['hp'] < 0.5
            st[n]['rec_fullhp'] += r['hp'] > 0.95
            st[n]['rec_gold60'] += r['gold'] >= 60
            st[n]['rec_bag'] += r['gems'] > 0
            st[n]['rec_dist'] += r['dist']
    print('| team | manual tribute cancels/g | their mean bag | enemy within 6 | mean channel rounds before cancel | recalls/g | at <50% hp | at >95% hp | with >=60 gold | carrying gems | mean distance |')
    print('|---|---|---|---|---|---|---|---|---|---|---|')
    for n in TEAMS:
        s = st[n]
        G = s['games']
        if not G:
            continue
        m = max(1, s['c_manual'])
        R = max(1, s['rec'])
        print(f"| {SHORT[n]} | {s['c_manual']/G:.2f} | {s['m_gems']/m:.0f} | {pct(s['m_near'], m)} | {s['m_dur']/m:.1f} | {s['rec']/G:.1f} | {pct(s['rec_lowhp'], R)} | {pct(s['rec_fullhp'], R)} | {pct(s['rec_gold60'], R)} | {pct(s['rec_bag'], R)} | {s['rec_dist']/R:.1f} |")
    print()


if __name__ == '__main__':
    camp_range()
    kills()
    wards()
    tcancel()
