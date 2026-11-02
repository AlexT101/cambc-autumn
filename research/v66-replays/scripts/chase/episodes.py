# Chase episodes in the v66 ladder extract: P hits T, T then walks homeward; follow until it ends.
import sys, json
sys.path.insert(0, 'research/v66-replays/scripts/extract')
from common import *
from concurrent.futures import ProcessPoolExecutor
MELEE = {'Ryth','Vendetta','Marcella','Ren','Varg','Heart of Ruin','Issac'}
DASH = {'Vesper Vale','Vendetta','Ren','Heart of Ruin','Issac'}  # dash is slot 1 for all
def one(r):
    d = r['dir']; m = meta(d); R = rounds(d); us = r['us']; mp = mapj(m)
    F = [spawn_field(mp, 0), spawn_field(mp, 1)]; N = len(R['round']); CH = R['champions']
    NM = {c['id']: c['name'] for c in m['champions']}
    rix = {rr: i for i, rr in enumerate(R['round'])}
    hit = defaultdict(float)   # (i, attacker, victim) -> damage
    stun = defaultdict(int)
    acts = defaultdict(list)   # (i, actor) -> [(kind, ability)]
    for e in events(d):
        if 'a' in e and e['r'] in rix: acts[(rix[e['r']], e['a'])].append((e['k'], e.get('ab'), tuple(v for v, _ in (e.get('dmg') or []))))
        if e['k'] in ('attack', 'cast') and 'a' in e and e['r'] in rix:
            i = rix[e['r']]
            for v, x in (e.get('dmg') or []): hit[(i, e['a'], v)] += x
            for v in (e.get('stun') or []): stun[(i, e['a'], v)] += 1
    P_ = lambda c, i: (c['x'][i], c['y'][i])
    out = []
    busy = {}  # target id -> round index until which it is in an episode
    for i in range(3, N - 2):
        for T in CH:
            if not (T['alive'][i] and T['alive'][i-1]) or busy.get(T['id'], -1) >= i: continue
            fT = F[T['team']]
            h0, h1 = fT.get(P_(T, i-1)), fT.get(P_(T, i))
            if h0 is None or h1 is None or h1 == 0 or not h1 < h0: continue
            # pursuers: enemies within 3 who hit T in the last 3 rounds
            purs = [P for P in CH if P['team'] != T['team'] and P['alive'][i] and cheb(P_(P, i), P_(T, i)) <= 3
                    and any(hit[(j, P['id'], T['id'])] > 0 for j in range(i-2, i+1))]
            if not purs: continue
            P = max(purs, key=lambda P: sum(hit[(j, P['id'], T['id'])] for j in range(i-2, i+1)))
            fP = F[P['team']]
            st = dict(side='us' if P['team'] == us else 'them', opp=r['opp'], P=NM[P['id']], T=NM[T['id']],
                      r=R['round'][i], src=r['source'],
                      Thp=T['hp'][i] / T['maxHp'][i], Php=P['hp'][i] / P['maxHp'][i], Tmax=T['maxHp'][i], Pstr=P['str'][i],
                      d0=cheb(P_(P, i), P_(T, i)), Thome=h1, Phome=fP.get(P_(P, i)),
                      Pdash=NM[P['id']] in DASH and P['cd1'][i] == 0, Tdash=NM[T['id']] in DASH and T['cd1'][i] == 0,
                      allyP=sum(1 for c in CH if c['team'] == P['team'] and c is not P and c['alive'][i] and cheb(P_(c, i), P_(T, i)) <= 8),
                      allyT=sum(1 for c in CH if c['team'] == T['team'] and c is not T and c['alive'][i] and cheb(P_(c, i), P_(T, i)) <= 8))
            end, j, far, still = 'cap', i, 0, 0
            dmgPT = dmgTP = dmgOthT = 0.0; turnsAdj = 0; stunsT = 0; maxPdeep = 0
            for j in range(i + 1, min(N, i + 40)):
                dmgPT += hit[(j, P['id'], T['id'])]; dmgTP += hit[(j, T['id'], P['id'])]
                dmgOthT += sum(hit[(j, c['id'], T['id'])] for c in CH if c['team'] == P['team'] and c is not P)
                stunsT += sum(stun[(j, c['id'], T['id'])] for c in CH if c['team'] == P['team'])
                if not T['alive'][j]: end = 'kill'; break
                if not P['alive'][j]: end = 'P_died'; break
                if fT.get(P_(T, j)) == 0: end = 'home'; break
                dd = cheb(P_(P, j), P_(T, j))
                maxPdeep = max(maxPdeep, fT.get(P_(P, j), 99) and (st['Thome'] - fT.get(P_(P, j), 99)))
                if dd <= 1: turnsAdj += 1
                far = far + 1 if dd > 5 else 0
                if far >= 2:
                    # who broke contact: P walked away from T, or T outpaced P?
                    pm = cheb(P_(P, j-2), P_(T, j)) - cheb(P_(P, j), P_(T, j))  # >0 P closed toward T's tile
                    end = 'quit' if pm <= 0 else 'outrun'; break
                ht = fT.get(P_(T, j)); hp = fT.get(P_(T, j-1))
                still = still + 1 if ht is not None and hp is not None and ht >= hp else 0
                if still >= 3 and dd <= 3: end = 'stand'; break
            A = [a for jj in range(i + 1, j + 1) for a in acts[(jj, P['id'])]]
            helpers = {c['id'] for jj in range(i + 1, j + 1) for c in CH if c['team'] == P['team'] and c is not P and hit[(jj, c['id'], T['id'])] > 0}
            Tacts = [a for jj in range(i + 1, j + 1) for a in acts[(jj, T['id'])]]
            st.update(Pdash=sum(1 for k, ab, v in A if ab == 'Dash'), Pcast_hit=sum(1 for k, ab, v in A if k == 'cast' and T['id'] in v),
                      Patk_hit=sum(1 for k, ab, v in A if k == 'attack' and T['id'] in v), Pmoves=sum(1 for k, ab, v in A if k == 'move'),
                      helpers=len(helpers), Tmoves=sum(1 for k, ab, v in Tacts if k == 'move'), Tatk=sum(1 for k, ab, v in Tacts if k in ('attack','cast') and P['id'] in v),
                      Tdied20=any(not T['alive'][jj] for jj in range(i, min(N, i + 20))), Pdied20=any(not P['alive'][jj] for jj in range(i, min(N, i + 20))))
            st.update(end=end, len=j - i, dmgPT=dmgPT, dmgTP=dmgTP, dmgOthT=dmgOthT, stunsT=stunsT, adj=turnsAdj,
                      Thp_end=T['hp'][j] / T['maxHp'][j] if T['alive'][j] else 0, Thome_end=fT.get(P_(T, j)),
                      Php_end=P['hp'][j] / P['maxHp'][j] if P['alive'][j] else 0,
                      Phome_end=fP.get(P_(P, j)), killer=None)
            if end == 'kill':
                st['killer'] = 'P' if hit[(j, P['id'], T['id'])] > 0 else 'other'
            out.append(st); busy[T['id']] = j
    return out
if __name__ == '__main__':
    with ProcessPoolExecutor(60) as ex: res = [x for o in ex.map(one, games()) for x in o]
    json.dump(res, open(sys.argv[1], 'w'))
    print(len(res))
