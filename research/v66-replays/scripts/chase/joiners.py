# Fights after first contact: enemies (and allies) who join within 5 rounds; were the joiners in the team's sight at contact?
import sys, json
sys.path.insert(0, 'research/v66-replays/scripts/extract')
from common import *
from concurrent.futures import ProcessPoolExecutor
def one(r):
    d = r['dir']; R = rounds(d); us = r['us']; N = len(R['round']); CH = R['champions']
    rix = {rr: i for i, rr in enumerate(R['round'])}
    hit = defaultdict(float)
    for e in events(d):
        if e['k'] in ('attack', 'cast') and 'a' in e and e['r'] in rix:
            for v, x in (e.get('dmg') or []): hit[(rix[e['r']], e['a'], v)] += x
    P = lambda c, i: (c['x'][i], c['y'][i]); out = []
    mp = mapj(meta(d)); spawn_field_cache = [spawn_field(mp, 0), spawn_field(mp, 1)]
    for c in CH:
        t = c['team']; last = -99
        for i in range(1, N - 12):
            if not c['alive'][i]: continue
            p = P(c, i); en = [e for e in CH if e['team'] != t and e['alive'][i]]
            if not en: continue
            if min(cheb(P(e, i), p) for e in en) <= 8:
                if i - last >= 5 and any(hit[(j, c['id'], e['id'])] or hit[(j, e['id'], c['id'])] for j in range(i, i + 10) for e in en):
                    team = [a for a in CH if a['team'] == t]
                    seen = set(x for a in team for x in a['sees'][i]) | set(x for a in team for x in a['sees'][i - 1])
                    near0 = {e['id'] for e in en if cheb(P(e, i), p) <= 8}
                    q = P(c, i + 5) if c['alive'][i + 5] else p
                    join = [e for e in CH if e['team'] != t and e['alive'][i + 5] and cheb(P(e, i + 5), q) <= 8 and e['id'] not in near0]
                    ajoin = [a for a in team if a is not c and a['alive'][i + 5] and cheb(P(a, i + 5), q) <= 8 and not (a['alive'][i] and cheb(P(a, i), p) <= 8)]
                    # the first round an enemy not near at contact comes within 8, and what we do next
                    arr = None
                    for k in range(i + 1, min(N - 3, i + 8)):
                        if not c['alive'][k]: break
                        if any(e['alive'][k] and e['id'] not in near0 and cheb(P(e, k), P(c, k)) <= 8 for e in CH if e['team'] != t): arr = k; break
                    ext = {}
                    if arr is not None:
                        fh = spawn_field_cache[t]
                        h0 = fh.get(P(c, arr), 99)
                        ext = dict(arr_hp=c['hp'][arr] / c['maxHp'][arr], arr_adj=min(cheb(P(e, arr), P(c, arr)) for e in CH if e['team'] != t and e['alive'][arr]),
                                   home2=all(c['alive'][arr + k] and fh.get(P(c, arr + k), 99) < fh.get(P(c, arr + k - 1), 99) for k in (1, 2)),
                                   dmg_after=sum(hit[(j, e['id'], c['id'])] for j in range(arr + 1, min(N, arr + 6)) for e in CH if e['team'] != t) / c['maxHp'][arr],
                                   died_after=any(not c['alive'][j] for j in range(arr, min(N, arr + 15))),
                                   kills_after=sum(1 for e in CH if e['team'] != t and e['alive'][arr] and any(not e['alive'][j] for j in range(arr, min(N, arr + 15)))))
                    out.append(dict(ext, side='us' if t == us else 'them', joins=len(join), seen=sum(1 for e in join if e['id'] in seen),
                                    jdist=[cheb(P(e, i), p) for e in join if e['alive'][i]], ajoins=len(ajoin),
                                    adist=sorted(cheb(P(a, i), p) for a in team if a is not c and a['alive'][i]),
                                    died=any(not c['alive'][j] for j in range(i, min(N, i + 20)))))
                last = i
    return out
if __name__ == '__main__':
    with ProcessPoolExecutor(60) as ex: res = [x for o in ex.map(one, games()) for x in o]
    import statistics as S
    print('== the moment the first enemy joiner arrives (within 7 rounds of contact)')
    for s in ('us', 'them'):
        Y = [x for x in res if x['side'] == s and 'arr_hp' in x]
        hp = sorted(x['arr_hp'] for x in Y)
        print('%-4s n=%5d hp then q25/50/75 %s  in contact (enemy within 1) %.2f  heads home 2 rounds %.2f  damage next 5r %.2f maxhp  dies within 15r %.3f  enemy kills within 15r %.2f' % (
            s, len(Y), [round(hp[int(len(hp) * p)], 2) for p in (.25, .5, .75)], S.mean(x['arr_adj'] <= 1 for x in Y), S.mean(x['home2'] for x in Y), S.mean(x['dmg_after'] for x in Y), S.mean(x['died_after'] for x in Y), S.mean(x['kills_after'] for x in Y)))
        for lab, f in (('heads home', lambda x: x['home2']), ('stays', lambda x: not x['home2'])):
            for hl, hf in (('hp<.5', lambda x: x['arr_hp'] < .5), ('hp>=.5', lambda x: x['arr_hp'] >= .5)):
                Z = [x for x in Y if f(x) and hf(x)]
                print('      %-10s %-6s n=%5d dies %.3f  damage next 5r %.2f' % (lab, hl, len(Z), S.mean(x['died_after'] for x in Z), S.mean(x['dmg_after'] for x in Z)))
    for s in ('us', 'them'):
        Y = [x for x in res if x['side'] == s]; J = sum(x['joins'] for x in Y)
        jd = sorted(v for x in Y for v in x['jdist'])
        print('%-4s fights %5d  enemy joiners/fight %.2f (seen by the team at contact %.2f; their distance then q25/50/75 %s)  ally joiners/fight %.2f  died %.3f' % (
            s, len(Y), J / len(Y), sum(x['seen'] for x in Y) / max(1, J), [jd[int(len(jd) * p)] for p in (.25, .5, .75)], sum(x['ajoins'] for x in Y) / len(Y), S.mean(x['died'] for x in Y)))
        for k in (0, 1, 2):
            Z = [x for x in Y if (x['joins'] == k if k < 2 else x['joins'] >= 2)]
            print('      enemy joiners %s%s: share %.2f died %.3f' % (k, '+' if k == 2 else ' ', len(Z) / len(Y), S.mean(x['died'] for x in Z)))
        a = [x['adist'] for x in Y if x['adist']]
        for rad in (8, 12, 16):
            print('      allies within %2d at contact: %.2f' % (rad, S.mean(sum(1 for v in d if v <= rad) for d in a)))
