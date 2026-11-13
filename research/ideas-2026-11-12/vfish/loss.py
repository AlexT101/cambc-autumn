"""How the candidate (bot 1) loses to charybdis: deaths by killer type, bags lost, Prism's bag, game length, gem race."""
import json, gzip, os, sys, collections, statistics as st
ext = sys.argv[1]
idx = json.load(open(ext + '/index.json'))['games']
A = collections.defaultdict(list); killers = collections.Counter(); victims = collections.Counter(); ckill = collections.Counter(); cvict = collections.Counter()
for g in idx:
    mid = os.path.basename(g['source'])[:-8]; cand = 0 if mid.endswith('-12') else 1
    p = f"{ext}/{g['dir']}"; meta = json.load(open(p + '/meta.json')); R = json.load(gzip.open(p + '/rounds.json.gz'))
    ev = [json.loads(l) for l in gzip.open(p + '/events.jsonl.gz', 'rt')]
    typ = {c['id']: c['name'] for c in meta['champions']}; team = {c['id']: c['team'] for c in meta['champions']}
    ch = R['champions']; n = len(R['round'])
    w = meta['result'].get('winner') if isinstance(meta.get('result'), dict) else meta.get('winner')
    win = w == cand; k = 'W' if win else 'L'
    A['win'].append(win); A['rounds' + k].append(n)
    has_prism = any(typ[c['id']] == 'Prism' and c['team'] != cand for c in ch)
    A['prism' ].append(has_prism); A['win_p' if has_prism else 'win_np'].append(win)
    cd = od = 0; lost = 0; took = 0; pbag = 0; pkill_bag = []
    for e in ev:
        if e['k'] != 'death' or 'linked' in e: continue
        v = e['v']; by = e.get('by'); camp = by not in typ or team.get(by) == team[v]
        if team[v] == cand:
            cd += 1; lost += e.get('gems', 0) if not camp else 0
            killers[typ[by] if not camp else 'camp'] += 1; victims[typ[v]] += 1
        else:
            od += 1; took += e.get('gems', 0) if not camp else 0
            ckill[typ[by] if not camp else 'camp'] += 1; cvict[typ[v]] += 1
            if typ[v] == 'Prism' and not camp: pkill_bag.append(e.get('gems', 0))
    for c in ch:
        if typ[c['id']] == 'Prism' and c['team'] != cand: pbag = max(c['gems'])
    A['cd' + k].append(cd); A['od' + k].append(od); A['lost' + k].append(lost); A['took' + k].append(took)
    if has_prism: A['pbag' + k].append(pbag); A['pk' + k].append(len(pkill_bag)); A['pkbag' + k].append(sum(pkill_bag))
    for rr in (150, 300, 450, 600):
        if rr <= n:
            A[f'd{rr}{k}'].append(sum(c['deaths'][rr - 1] for c in ch if c['team'] == cand) - sum(c['deaths'][rr - 1] for c in ch if c['team'] != cand))
            A[f'g{rr}{k}'].append(R['gems'][cand][rr - 1] - R['gems'][1 - cand][rr - 1])
            A[f'e{rr}{k}'].append(sum(c['earned'][rr - 1] for c in ch if c['team'] == cand) - sum(c['earned'][rr - 1] for c in ch if c['team'] != cand))
            A[f'cg{rr}{k}'].append(sum(c['gems'][rr - 1] for c in ch if c['team'] == cand) - sum(c['gems'][rr - 1] for c in ch if c['team'] != cand))
m = lambda k: (sum(A[k]) / len(A[k]) if A[k] else float('nan'))
print(f"games {len(A['win'])} win {m('win'):.3f} | ref drafts Prism in {m('prism'):.2f}: win {m('win_p'):.3f} with, {m('win_np'):.3f} without ({len(A['win_np'])})")
for k in 'WL':
    print(f" {k}: rounds {st.median(A['rounds'+k])} | cand deaths {m('cd'+k):.1f} ref deaths {m('od'+k):.1f} | gems lost to kills {m('lost'+k):.0f} taken {m('took'+k):.0f} | ref Prism max bag {m('pbag'+k):.0f}, killed {m('pk'+k):.2f}x for {m('pkbag'+k):.0f} gems")
    for rr in (150, 300, 450, 600): print(f"    r{rr}: deaths diff {m(f'd{rr}{k}'):+.1f} tributed diff {m(f'g{rr}{k}'):+.0f} carried diff {m(f'cg{rr}{k}'):+.0f} gold diff {m(f'e{rr}{k}'):+.0f}  n={len(A[f'd{rr}{k}'])}")
tot = sum(killers.values()); print('cand killed by:', ', '.join(f'{a} {b / tot:.2f}' for a, b in killers.most_common(8)))
tot = sum(victims.values()); print('cand victims:', ', '.join(f'{a} {b / tot:.2f}' for a, b in victims.most_common(8)))
tot = sum(ckill.values()); print('ref killed by:', ', '.join(f'{a} {b / tot:.2f}' for a, b in ckill.most_common(8)))
tot = sum(cvict.values()); print('ref victims:', ', '.join(f'{a} {b / tot:.2f}' for a, b in cvict.most_common(8)))
