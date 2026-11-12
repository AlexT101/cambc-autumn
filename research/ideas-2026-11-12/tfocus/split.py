"""Why strikes split: in conv.py's choice rounds, each striker that did not hit the round's modal target although it
was among its options, against one that did. Compares the chosen and the modal target's health fraction and
distance at the round's start, whether it acted before or after the modal target's first striker, and what
the modal target's first striker had done to it by then.

py split.py live | EXTRACT_DIR...
"""
import gzip, json, os, sys
from collections import Counter, defaultdict
from multiprocessing import Pool
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from conv import OPT, cheb, live_jobs, batch_jobs


def one(job):
    d, labels = job
    try:
        meta = json.load(open(d + '/meta.json'))
        R = json.load(gzip.open(d + '/rounds.json.gz'))
        ev = [json.loads(l) for l in gzip.open(d + '/events.jsonl.gz', 'rt')]
    except Exception:
        return None
    team = {c['id']: c['team'] for c in meta['champions']}
    names = {c['id']: c['name'] for c in meta['champions']}
    pick = {c['id']: c['id'] for c in meta['champions']}
    for t in (0, 1):
        cass = [c for c in team if team[c] == t and names[c] in ('Cassi', 'Issac')]
        if len(cass) == 2: pick[max(cass)] = min(cass)
    idx = {r: i for i, r in enumerate(R['round'])}
    ch = {c['id']: c for c in R['champions']}
    hits = defaultdict(lambda: defaultdict(Counter))
    first_t = defaultdict(dict)  # round -> actor -> first strike turn index
    for e in ev:
        if e['k'] in ('attack', 'cast') and e.get('dmg'):
            a = e['a']
            for v, amt in e['dmg']:
                if v in team and team[v] != team[a] and amt > 0:
                    hits[e['r']][a][pick[v]] += amt
                    first_t[e['r']].setdefault(a, e['t'])
    out = {}
    for t in (0, 1):
        lab = labels[t]
        if lab is None: continue
        C = Counter()
        for r, by in hits.items():
            st = {a: tg for a, tg in by.items() if team[a] == t}
            if len(st) < 2: continue
            prim = {a: max(tg, key=tg.get) for a, tg in st.items()}
            cnt = Counter(prim.values())
            modal, m = cnt.most_common(1)[0]
            if m == len(prim) or m == 1 and len(prim) == 2: pass
            i = idx.get(r - 1); ri = idx.get(r)
            if i is None or ri is None: continue

            def hpf(v): return ch[v]['hp'][i] / max(1, ch[v]['maxHp'][i])

            def pos(c): return (ch[c]['x'][i], ch[c]['y'][i])
            seen_of = {}
            for a in prim:
                if ch[a]['x'][i] is None or ch[a]['x'][i] < 0: continue
                seen_of[a] = {pick[v] for v in (ch[a]['sees'][ri] or []) if ch.get(v) and ch[v]['alive'][i] and ch[v]['x'][i] is not None and cheb(pos(a), pos(v)) <= OPT}
            al = sorted(seen_of)
            for x in range(len(al)):
                for y in range(x + 1, len(al)):
                    a, b = al[x], al[y]
                    if prim[a] in seen_of[b] and prim[b] in seen_of[a] and len(seen_of[a] | seen_of[b]) >= 2:
                        C['pairs'] += 1
                        if prim[a] == prim[b]: C['pair_same'] += 1
                        else:
                            ta, tb = prim[a], prim[b]
                            # a later striker that saw the earlier's target already hit
                            fa, fb = first_t[r][a], first_t[r][b]
                            late, early = (a, b) if fa > fb else (b, a)
                            C['split_late_lower'] += hpf(prim[late]) < hpf(prim[early])
                            C['split_late_closer'] += cheb(pos(late), pos(prim[late])) < cheb(pos(late), pos(prim[early]))
                            C['split_late_tgt_d'] += cheb(pos(late), pos(prim[late])); C['split_late_other_d'] += cheb(pos(late), pos(prim[early]))
                            C['split_late_tgt_hp'] += hpf(prim[late]); C['split_late_other_hp'] += hpf(prim[early])
                    elif len(seen_of[a] | seen_of[b]) >= 2:
                        C['pairs_noreach'] += 1; C['pairs_noreach_same'] += prim[a] == prim[b]
            for a, tgt in prim.items():
                if ch[a]['x'][i] is None or ch[a]['x'][i] < 0: continue
                seen = {pick[v] for v in (ch[a]['sees'][ri] or []) if ch.get(v) and ch[v]['alive'][i] and ch[v]['x'][i] is not None and cheb(pos(a), pos(v)) <= OPT}
                if modal not in seen or len(seen) < 2: continue
                if cnt[modal] == cnt[tgt] and tgt != modal: continue  # tie: no modal
                if tgt == modal:
                    C['on'] += 1
                    continue
                C['off'] += 1
                C['off_lower_hp'] += hpf(tgt) < hpf(modal)
                C['off_closer'] += cheb(pos(a), pos(tgt)) < cheb(pos(a), pos(modal))
                C['off_farther'] += cheb(pos(a), pos(tgt)) > cheb(pos(a), pos(modal))
                C['off_hp_sum'] += hpf(tgt); C['modal_hp_sum'] += hpf(modal)
                ms = [b for b in prim if prim[b] == modal]
                C['off_after_modal_hit'] += first_t[r][a] > min(first_t[r][b] for b in ms)
                C['off_d_modal'] += cheb(pos(a), pos(modal)); C['off_d_tgt'] += cheb(pos(a), pos(tgt))
                C['off_gems_tgt'] += (ch[tgt]['gems'][i] or 0); C['off_gems_modal'] += (ch[modal]['gems'][i] or 0)
        out[lab] = C
    return out


def main():
    jobs = live_jobs() if sys.argv[1:] == ['live'] else [j for ex in sys.argv[1:] for j in batch_jobs(ex)]
    with Pool(int(os.environ.get('NPROC', 8))) as p: res = [x for x in p.map(one, jobs, chunksize=4) if x]
    tot = defaultdict(Counter)
    for o in res:
        for lab, C in o.items(): tot[lab].update(C)
    for lab, C in sorted(tot.items()):
        p = C['pairs'] or 1; sp = (C['pairs'] - C['pair_same']) or 1
        print(f"{lab}: mutually reachable striker pairs {C['pairs']}: same target {100 * C['pair_same'] / p:.1f}%; "
              f"other pairs (2+ options) {C['pairs_noreach']}: same {100 * C['pairs_noreach_same'] / max(1, C['pairs_noreach']):.1f}%")
        print(f"   in split reachable pairs, the later striker's target: lower hp frac {100 * C['split_late_lower'] / sp:.0f}%, closer {100 * C['split_late_closer'] / sp:.0f}%; "
              f"hp {C['split_late_tgt_hp'] / sp:.2f} vs other {C['split_late_other_hp'] / sp:.2f}; dist {C['split_late_tgt_d'] / sp:.2f} vs other {C['split_late_other_d'] / sp:.2f}")
        n = C['off'] or 1
        print(f"{lab}: strikers with the modal target in reach: on it {C['on']}, off it {C['off']} ({100 * C['off'] / max(1, C['on'] + C['off']):.1f}%)")
        print(f"   off-modal strikes: chosen target lower health fraction {100 * C['off_lower_hp'] / n:.0f}%, closer {100 * C['off_closer'] / n:.0f}%, "
              f"farther {100 * C['off_farther'] / n:.0f}%; mean hp frac chosen {C['off_hp_sum'] / n:.2f} vs modal {C['modal_hp_sum'] / n:.2f}; "
              f"dist chosen {C['off_d_tgt'] / n:.2f} vs modal {C['off_d_modal'] / n:.2f}; gems chosen {C['off_gems_tgt'] / n:.0f} vs modal {C['off_gems_modal'] / n:.0f}; "
              f"struck after the modal's first hit {100 * C['off_after_modal_hit'] / n:.0f}%")


if __name__ == '__main__':
    main()
