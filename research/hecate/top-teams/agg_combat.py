"""Combat, bushes, wards, team structure, tributes, recalls, shops."""
import pickle
from collections import Counter, defaultdict
from statistics import mean, median

from common import TOP, US, SHORT, ref

F = pickle.load(open(__file__.replace('agg_combat.py', 'features.pkl'), 'rb'))
TEAMS = TOP + [US]


def pct(a, b):
    return f'{100 * a / b:.0f}%' if b else '-'


def combat():
    print('## 4. Combat\n')
    st = defaultdict(Counter)
    ex = defaultdict(list)
    for f in F:
        T = f['team_of']
        for t in (0, 1):
            st[f['names'][t]]['games'] += 1
            st[f['names'][t]]['wins'] += f['winner'] == t
            st[f['names'][t]]['rounds'] += f['N']
        for d in f['deaths']:
            vt = d['vt']
            vn = f['names'][vt]
            if d['linked']:
                continue
            if d['by'] is None:
                st[vn]['camp_deaths'] += 1
                st[vn]['camp_death_gems'] += d['gems']
                continue
            kn = f['names'][1 - vt]
            st[vn]['deaths'] += 1
            st[kn]['kills'] += 1
            st[vn]['gems_lost'] += d['gems']
            st[kn]['gems_won'] += d['gems']
            if d['gems'] >= 30:
                st[kn]['k_bag30'] += 1
                if (d.get('to_altar') or 0) > 0 or (d.get('to_home') or 0) > 0:
                    st[kn]['k_bag_heading'] += 1
                    if len(ex[(kn, 'gank')]) < 3:
                        ex[(kn, 'gank')].append(f"{ref(f['rec'], d['r'])} victim {f['types'][d['v']]} {d['gems']}g")
            if d['altar'] is not None and d['altar'] <= 2:
                st[kn]['k_altar'] += 1
                if d['chan'] == 'tribute_cancel' or d.get('chan0') == 2:
                    st[kn]['k_tributing'] += 1
                    if len(ex[(kn, 'altar')]) < 3:
                        ex[(kn, 'altar')].append(f"{ref(f['rec'], d['r'])} {d['gems']}g")
            if d['chan'] == 'recall_cancel' or d.get('chan0') == 1:
                st[kn]['k_recalling'] += 1
            if d['half'] == vt:
                pass
            if d['half'] == 1:
                # victim died in its enemy's half (own frame: 1 = enemy half)
                st[vn]['d_enemy_half'] += 1
                st[kn]['k_in_own_half'] += 1
            elif d['half'] == 0:
                st[kn]['k_in_enemy_half'] += 1
            ne, na = d.get('near_enemy', 0), d.get('near_ally', 0)
            if ne >= na + 2:
                st[vn]['d_outnumbered'] += 1
            if na == 0:
                st[vn]['d_alone'] += 1
            if d.get('on_camp') is not None:
                st[kn]['k_on_camp'] += 1
        for fg in f['fights']:
            it = fg['init']
            n = f['names'][it]
            o = f['names'][1 - it]
            st[n]['init'] += 1
            st[o]['initd'] += 1
            pr = fg['present']
            st[n]['init_num_adv'] += pr[it] - pr[1 - it]
            if pr[it] > pr[1 - it]:
                st[n]['init_more'] += 1
            elif pr[it] < pr[1 - it]:
                st[n]['init_fewer'] += 1
            hf = fg['hpfrac']
            if hf[it] is not None and hf[1 - it] is not None:
                st[n]['init_hp_adv'] += hf[it] - hf[1 - it]
            if fg['init_from_bush']:
                st[n]['init_bush'] += 1
            sw = fg['swing'] * (1 if it == 0 else -1)
            st[n]['init_swing'] += sw
            k = fg['kills']
            if k[it] > k[1 - it]:
                st[n]['init_won'] += 1
            elif k[it] < k[1 - it]:
                st[n]['init_lost'] += 1
            for t in (0, 1):
                nm = f['names'][t]
                st[nm]['fights'] += 1
                st[nm]['fight_kills'] += k[t]
                st[nm]['fight_swing'] += fg['swing'] * (1 if t == 0 else -1)
                if k[t] > k[1 - t]:
                    st[nm]['fight_won'] += 1
                if fg['carried'][1 - t] >= 40:
                    st[nm]['fight_vs_bag'] += 1
        # focus fire: per round per team, share of champion damage on top target
        per = defaultdict(lambda: defaultdict(float))
        for r, a, v, amt, fb, seen, kind, ab in f['champ_atk']:
            per[(r, T[a])][v] += amt
        for (r, t), dv in per.items():
            if len(dv) >= 1:
                tot = sum(dv.values())
                st[f['names'][t]]['ff_rounds'] += 1
                st[f['names'][t]]['ff_share'] += max(dv.values()) / tot
                if len(dv) >= 2:
                    st[f['names'][t]]['ff_split'] += 1
        # multi-attacker rounds
        att = defaultdict(set)
        for r, a, v, amt, fb, seen, kind, ab in f['champ_atk']:
            att[(r, T[a], v)].add(a)
        for (r, t, v), s in att.items():
            st[f['names'][t]]['atk_target_rounds'] += 1
            if len(s) >= 2:
                st[f['names'][t]]['atk_multi'] += 1
        # stun chains
        sts = sorted(f['stuns'])
        last = {}
        for r, tt, a, v in sts:
            n = f['names'][T[a]]
            st[n]['stuns'] += 1
            if v in last and 0 < r - last[v][0] <= 2 and last[v][1] != a:
                st[n]['stun_chain'] += 1
                if len(ex[(n, 'chain')]) < 3:
                    ex[(n, 'chain')].append(ref(f['rec'], r))
            last[v] = (r, a)
        for c in f['tcancel']:
            n = f['names'][T[c['a']]]
            st[n]['tcancel_' + str(c['cause'])] += 1
            st[n]['tcancel_gems'] += c['gems']
    print('| team | games | win% | kills/g | deaths/g | camp deaths/g | gems won/lost per g | kills of 30+ bags heading home/altar | kills at altars (tributing) | kills of recallers | deaths outnumbered (>=2 more enemies within 6) | deaths alone | kills in own half / enemy half |')
    print('|---|---|---|---|---|---|---|---|---|---|---|---|---|')
    for n in TEAMS:
        s = st[n]
        G = s['games']
        if not G:
            continue
        print(f"| {SHORT[n]} | {G} | {pct(s['wins'], G)} | {s['kills']/G:.2f} | {s['deaths']/G:.2f} | {s['camp_deaths']/G:.2f} | {s['gems_won']/G:.0f}/{s['gems_lost']/G:.0f} | {s['k_bag_heading']} of {s['k_bag30']} | {s['k_altar']} ({s['k_tributing']}) | {s['k_recalling']} | {pct(s['d_outnumbered'], s['deaths'])} | {pct(s['d_alone'], s['deaths'])} | {s['k_in_own_half']}/{s['k_in_enemy_half']} |")
    print()
    print('| team | fights/g | initiates | init w/ more champs / fewer | mean numbers adv when init | mean hp-frac adv when init | init from bush | init won/lost (kills) | init net swing/fight | all fights won share | focus share (top target dmg share) | multi-attacker target-rounds | stuns/g | stun chains/g | tribute cancels by cause |')
    print('|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|')
    for n in TEAMS:
        s = st[n]
        G = s['games']
        if not G:
            continue
        I = max(1, s['init'])
        tc = {k[8:]: v for k, v in s.items() if k.startswith('tcancel_') and k != 'tcancel_gems'}
        print(f"| {SHORT[n]} | {s['fights']/G:.1f} | {pct(s['init'], s['init']+s['initd'])} | {pct(s['init_more'], I)} / {pct(s['init_fewer'], I)} | {s['init_num_adv']/I:+.2f} | {s['init_hp_adv']/I:+.2f} | {pct(s['init_bush'], I)} | {pct(s['init_won'], I)}/{pct(s['init_lost'], I)} | {s['init_swing']/I:+.1f} | {pct(s['fight_won'], s['fights'])} | {s['ff_share']/max(1,s['ff_rounds']):.2f} | {pct(s['atk_multi'], s['atk_target_rounds'])} | {s['stuns']/G:.1f} | {s['stun_chain']/G:.2f} | {tc} |")
    print()
    for n in TEAMS:
        for k in ('gank', 'altar', 'chain'):
            if ex[(n, k)]:
                print(f'- {SHORT[n]} {k}: ' + '; '.join(ex[(n, k)][:2]))
    print()


def bushes():
    print('## 3. Bushes and wards\n')
    st = defaultdict(Counter)
    for f in F:
        T = f['team_of']
        b = f['bush']
        if b['nbush'] == 0:
            continue
        for c, t in T.items():
            n = f['names'][t]
            st[n]['alive'] += b['alive'].get(c, 0)
            st[n]['bush'] += b['bush'].get(c, 0)
            st[n]['still'] += b['still'].get(c, 0)
        for t in (0, 1):
            st[f['names'][t]]['games_b'] += 1
        for r, a, v, amt, fb, seen, kind, ab in f['champ_atk']:
            n = f['names'][T[a]]
            st[n]['atk'] += 1
            st[n]['atk_dmg'] += amt
            if fb:
                st[n]['atk_bush'] += 1
                st[n]['atk_bush_dmg'] += amt
                if not seen:
                    st[n]['atk_bush_unseen'] += 1
            if not seen:
                st[n]['atk_unseen'] += 1
    for f in F:
        T = f['team_of']
        for w in f['wards']:
            n = f['names'][T[w['a']]]
            st[n]['wards'] += 1
            st[n]['w_bush'] += w['bush']
            st[n]['w_altar'] += w['altar'] <= 3
            st[n]['w_camp'] += w['camp'] <= 3
            st[n]['w_enemyhalf'] += w['half'] == 1
            st[n]['w_dead'] += w['alive'] is False
        for t in (0, 1):
            st[f['names'][t]]['games'] += 1
    print('| team | share of alive rounds in bush | in bush and not moving | attacks from bush | attacks unseen by victim | wards/g | wards in bush | near altar (<=3) | near camp (<=3) | enemy half | placed while dead |')
    print('|---|---|---|---|---|---|---|---|---|---|---|')
    for n in TEAMS:
        s = st[n]
        if not s['games']:
            continue
        W = max(1, s['wards'])
        print(f"| {SHORT[n]} | {pct(s['bush'], s['alive'])} | {pct(s['still'], s['alive'])} | {pct(s['atk_bush'], s['atk'])} | {pct(s['atk_unseen'], s['atk'])} | {s['wards']/s['games']:.0f} | {pct(s['w_bush'], W)} | {pct(s['w_altar'], W)} | {pct(s['w_camp'], W)} | {pct(s['w_enemyhalf'], W)} | {pct(s['w_dead'], W)} |")
    print()


def structure():
    print('## 5. Team structure (largest connected group, link <=4, every 5 rounds)\n')
    st = defaultdict(lambda: defaultdict(Counter))
    for f in F:
        for r, row in f['struct']:
            ph = '1-60' if r <= 60 else '61-200' if r <= 200 else '201-500' if r <= 500 else '500+'
            for t in (0, 1):
                n = f['names'][t]
                sizes = row[t]
                if not sizes:
                    continue
                st[n][ph]['n'] += 1
                st[n][ph]['solo'] += sum(1 for s in sizes if s == 1)
                st[n][ph]['bodies'] += sum(sizes)
                st[n][ph]['max'] += max(sizes)
                st[n][ph]['ngroups'] += len(sizes)
    print('| team | phase | mean largest group | mean groups | share of bodies solo |')
    print('|---|---|---|---|---|')
    for n in TEAMS:
        for ph in ('1-60', '61-200', '201-500', '500+'):
            s = st[n][ph]
            if s['n']:
                print(f"| {SHORT[n]} | {ph} | {s['max']/s['n']:.2f} | {s['ngroups']/s['n']:.2f} | {pct(s['solo'], s['bodies'])} |")
    print()


def economy():
    print('## 7. Tributes, recalls, shops, locks\n')
    st = defaultdict(Counter)
    bags = defaultdict(list)
    rec_hp = defaultdict(list)
    rec_gems = defaultdict(list)
    first_shop = defaultdict(list)
    items = defaultdict(Counter)
    lockex = defaultdict(list)
    for f in F:
        T = f['team_of']
        for t in (0, 1):
            st[f['names'][t]]['games'] += 1
            st[f['names'][t]]['rounds'] += f['N']
        for x in f['trib']:
            n = f['names'][T[x['a']]]
            if 'end' in x:
                st[n]['trib_end'] += 1
                bags[n].append(x['gems'])
        starts = {}
        for x in f['recalls']:
            n = f['names'][T[x['a']]]
            if 'end' in x:
                st[n]['recall_end'] += 1
                rec_gems[n].append(x['gems'])
                s = starts.get(x['a'])
                if s:
                    rec_hp[n].append(s['hpfrac'])
            else:
                starts[x['a']] = x
        seen = set()
        for x in f['shops']:
            n = f['names'][T[x['a']]]
            if 'items' in x:
                st[n]['shops'] += 1
                if x['alive'] is False:
                    st[n]['shop_dead'] += 1
                for k, v in x['items'].items():
                    if v > 0:
                        items[n][k] += v
                if x['a'] not in seen and x['gold'] < 0:
                    seen.add(x['a'])
                    first_shop[n].append(x['r'])
            elif 'cons' in x:
                for k, v in x['cons'].items():
                    if v > 0:
                        st[n]['cons_' + k] += v
        for x in f['locks']:
            if x['k'] == 'lock_place':
                n = f['names'][x['team']] if x['team'] is not None else f['names'][T[x['a']]]
                st[n]['locks'] += 1
                if len(lockex[n]) < 2:
                    lockex[n].append(ref(f['rec'], x['r']))
            elif x['k'] == 'tribute_blocked':
                n = f['names'][T[x['a']]]
                st[n]['blocked'] += 1
    print('| team | tributes/g | median bag | mean bag | bags >=100 | recalls completed /g | recall median hp-frac | recall median gems | median first shop round | shops while dead | locks/g | own tributes blocked/g | consumables |')
    print('|---|---|---|---|---|---|---|---|---|---|---|---|---|')
    for n in TEAMS:
        s = st[n]
        G = s['games']
        if not G:
            continue
        b = bags[n] or [0]
        cons = {k[5:]: v for k, v in s.items() if k.startswith('cons_')}
        print(f"| {SHORT[n]} | {s['trib_end']/G:.1f} | {median(b):.0f} | {mean(b):.0f} | {pct(sum(1 for x in b if x >= 100), len(b))} | {s['recall_end']/G:.1f} | {median(rec_hp[n] or [0]):.2f} | {median(rec_gems[n] or [0]):.0f} | {median(first_shop[n] or [0]):.0f} | {pct(s['shop_dead'], s['shops'])} | {s['locks']/G:.2f} | {s['blocked']/G:.2f} | {cons} |")
    print()
    for n in TEAMS:
        tot = sum(items[n].values())
        print(f"- {SHORT[n]} items: " + ', '.join(f'{k} {100*v/tot:.0f}%' for k, v in items[n].most_common(6)) + (f"; locks e.g. {lockex[n][0]}" if lockex[n] else ''))
    print()


if __name__ == '__main__':
    bushes()
    combat()
    structure()
    economy()
