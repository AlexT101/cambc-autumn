"""Multi-phase camp clears, camp stealing, capture contests, respawn denial."""
import pickle
import sys
from collections import Counter, defaultdict

from common import TOP, US, SHORT, ref

F = pickle.load(open(__file__.replace('agg_camps.py', 'features.pkl'), 'rb'))
TEAMS = TOP + [US]


def tname(f, t):
    return f['names'][t]


def pct(a, b):
    return f'{100 * a / b:.0f}%' if b else '-'


def multiphase():
    print('## 1. Multi-phase camp clears\n')
    st = defaultdict(Counter)
    ex = defaultdict(list)
    bytype = defaultdict(Counter)
    champ = defaultdict(Counter)
    for f in F:
        types = f['types']
        for c in f.get('clears', []):
            t = c['team']
            if t is None:
                continue
            n = tname(f, t)
            st[n]['clears'] += 1
            own_sess = [s for s in c['sess'] if s[2][t] > 0]
            if len(own_sess) >= 2:
                st[n]['multi_own'] += 1
                bytype[n][f"{c['g']}"] += 0
            enemy = c['dmg'][1 - t]
            if enemy > 0.15 * sum(c['dmg']):
                st[n]['finish_enemy_dmg'] += 1
                if len(ex[(n, 'finish')]) < 4:
                    ex[(n, 'finish')].append(ref(f['rec'], c['r']))
        for p in f['partial']:
            n = tname(f, p['team'])
            st[n]['partial'] += 1
            a = p['acts']
            nx = p.get('next')
            st[n]['p_' + p['type']] += 1
            if nx:
                if nx['team'] == p['team']:
                    st[n]['resumed_own'] += 1
                    if nx['clear_team'] == p['team']:
                        st[n]['resumed_own_cleared'] += 1
                        st[n]['resume_gap_sum'] += nx['gap']
                        if a.get('home') or a.get('recall'):
                            st[n]['resumed_after_home'] += 1
                        if p['hp_left'] < 0.6:
                            st[n]['resumed_big'] += 1
                            if len(ex[(n, 'resume')]) < 4:
                                ex[(n, 'resume')].append(f"{ref(f['rec'], p['r1'])} {p['type']} left {p['hp_left']:.2f} back r{nx['r0']}")
                            for c in p['champs']:
                                champ[n][types[c]] += 1
                else:
                    st[n]['taken_by_enemy'] += 1
                    if nx['clear_team'] == 1 - p['team']:
                        st[n]['stolen_after_partial'] += 1
            else:
                st[n]['never_resumed'] += 1
            if a.get('died'):
                st[n]['p_died'] += 1
            if a.get('home') or a.get('recall'):
                st[n]['p_home'] += 1
            hps = [h for h in a.get('hpfrac', []) if h >= 0]
            if hps and min(hps) < 0.4:
                st[n]['p_lowhp'] += 1
        for d in f['camp_deaths']:
            n = tname(f, f['team_of'][d['v']])
            st[n]['camp_deaths'] += 1
            st[n]['camp_death_gems'] += d['gems']
        for t in (0, 1):
            st[tname(f, t)]['games'] += 1
            st[tname(f, t)]['rounds'] += f['N']
    print('| team | games | clears | clears w/ >=2 own sessions | partial sleeps (/game) | resumed by self & cleared | ...after going home | ...with <60% hp left | mean gap | partial then enemy cleared | low-hp (<40%) at sleep | camp deaths /game |')
    print('|---|---|---|---|---|---|---|---|---|---|---|---|')
    for n in TEAMS:
        s = st[n]
        if not s['games']:
            continue
        print(f"| {SHORT[n]} | {s['games']} | {s['clears']} | {pct(s['multi_own'], s['clears'])} | {s['partial']} ({s['partial']/s['games']:.1f}) | {pct(s['resumed_own_cleared'], s['partial'])} | {pct(s['resumed_after_home'], s['resumed_own_cleared'])} | {s['resumed_big']} | {s['resume_gap_sum']/max(1,s['resumed_own_cleared']):.0f} | {pct(s['stolen_after_partial'], s['partial'])} | {pct(s['p_lowhp'], s['partial'])} | {s['camp_deaths']/s['games']:.2f} |")
    print()
    for n in TEAMS:
        tp = {k[2:]: v for k, v in st[n].items() if k.startswith('p_') and len(k) <= 4}
        print(f'- {SHORT[n]}: partial by camp type {dict(tp)}; big-resume champions {dict(champ[n].most_common(6))}')
        for e in ex[(n, 'resume')][:2]:
            print(f'  - resume: {e}')
    print()
    return st, ex


def stealing():
    print('## 2. Camp stealing, contests, respawn denial\n')
    st = defaultdict(Counter)
    ex = defaultdict(list)
    for f in F:
        for c in f['captures']:
            n = tname(f, c['team'])
            st[n]['caps'] += 1
            st[n]['cap_gems'] += c['gems']
            if c['side'] == 1 - c['team']:
                st[n]['enemy_side_caps'] += 1
                st[n]['enemy_side_gems'] += c['gems']
                if len(ex[(n, 'eside')]) < 3:
                    ex[(n, 'eside')].append(f"{ref(f['rec'], c['r'])} {c['type']} {c['gems']}g")
            elif c['side'] == -1:
                st[n]['mid_caps'] += 1
                st[n]['mid_gems'] += c['gems']
        for r in f['resets']:
            holder = tname(f, r['team'])
            if r['contested']:
                st[holder]['got_contested'] += 1
                st[tname(f, 1 - r['team'])]['contested_enemy'] += 1
                if len(ex[(tname(f, 1 - r['team']), 'contest')]) < 3:
                    ex[(tname(f, 1 - r['team']), 'contest')].append(ref(f['rec'], r['r']))
            else:
                st[holder]['reset_self'] += 1
        for fl in f['flips']:
            st[tname(f, fl['team'])]['flips'] += 1
        for d in f['denial']:
            occ_t = Counter(f['team_of'][c] for c in d['occ_all'])
            for t, k in occ_t.items():
                n = tname(f, t)
                if t != d['cap_team']:
                    st[n]['deny_enemy_respawn'] += 1
                    st[n]['deny_rounds'] += d['delay']
                    if len(ex[(n, 'deny')]) < 3:
                        ex[(n, 'deny')].append(f"{ref(f['rec'], d['exp'])} {d['type']} +{d['delay']}r")
                else:
                    st[n]['delay_own'] += 1
                    st[n]['delay_own_rounds'] += d['delay']
        for t in (0, 1):
            st[tname(f, t)]['games'] += 1
    print('| team | games | captures/game | gems/capture | enemy-side caps (share, gems share) | mid caps share | contested enemy holds /game | own holds contested /game | own resets (walked off/died) /game | enemy respawns delayed by standing /game (rounds) | own respawns delayed /game |')
    print('|---|---|---|---|---|---|---|---|---|---|---|')
    for n in TEAMS:
        s = st[n]
        if not s['games']:
            continue
        G = s['games']
        print(f"| {SHORT[n]} | {G} | {s['caps']/G:.1f} | {s['cap_gems']/max(1,s['caps']):.1f} | {pct(s['enemy_side_caps'], s['caps'])}, {pct(s['enemy_side_gems'], s['cap_gems'])} | {pct(s['mid_caps'], s['caps'])} | {s['contested_enemy']/G:.2f} | {s['got_contested']/G:.2f} | {s['reset_self']/G:.2f} | {s['deny_enemy_respawn']/G:.2f} ({s['deny_rounds']/max(1,s['deny_enemy_respawn']):.0f}) | {s['delay_own']/G:.2f} |")
    print()
    for n in TEAMS:
        for k in ('eside', 'contest', 'deny'):
            if ex[(n, k)]:
                print(f'- {SHORT[n]} {k}: ' + '; '.join(ex[(n, k)][:2]))
    print()


if __name__ == '__main__':
    multiphase()
    stealing()
