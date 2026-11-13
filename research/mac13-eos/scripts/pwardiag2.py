"""Follow-up tables on pwardiag.py's /tmp/pwardiag.pkl: end-of-turn distance (belief, visible) vs death, by branch and verdict."""
import pickle, collections, sys
E = pickle.load(open(sys.argv[1] if len(sys.argv) > 1 else '/tmp/pwardiag.pkl', 'rb'))


def pct(x, n): return f'{100 * x / max(1, n):.0f}%'


for role in ('small', 'big'):
    for era, f in (('r<600', lambda e: e['r'] < 600), ('r>=600', lambda e: e['r'] >= 600)):
        rows = [e for e in E if e['role'] == role and f(e) and e['pw'] and e['pw']['vis']]
        print(f'\n== {role} {era}, visible belief: {len(rows)} rounds')
        by = collections.defaultdict(list)
        for e in rows: by[min(e['pw']['d1'], 9)].append(e)
        for d in sorted(by):
            s = by[d]
            br = collections.Counter(e['br'] for e in s).most_common(4)
            print(f'  end dist {d}: n {len(s)}, our death {pct(sum(e["die_u"] for e in s), len(s))}, enemy death {pct(sum(e["die_e"] for e in s), len(s))},'
                  f' fight lost {pct(sum(e["pw"]["flost"] == 1 for e in s), len(s))}, falls {pct(sum(e["pw"]["falls"] for e in s), len(s))},'
                  f' lethal {pct(sum(e["pw"]["leth1"] for e in s), len(s))}, walked {pct(sum(e["pw"]["walked"] for e in s), len(s))},'
                  f' our stun cd>0 {pct(sum(e["pw"]["cd0"] > 0 for e in s), len(s))}, their stun ready {pct(sum(e["pw"]["erd0"] <= 1 for e in s), len(s))}, br {br}')
        # ended within 5 (enemy reach after a walk): by branch, with verdicts
        s5 = [e for e in rows if e['pw']['d1'] <= 5]
        print(f'  ended within 5: {len(s5)}')
        for b, c in collections.Counter(e['br'] for e in s5).most_common(8):
            s = [e for e in s5 if e['br'] == b]
            print(f'    {b}: n {c}, our death {pct(sum(e["die_u"] for e in s), c)}, enemy death {pct(sum(e["die_e"] for e in s), c)}, lost {pct(sum(e["pw"]["flost"] == 1 for e in s), c)},'
                  f' falls {pct(sum(e["pw"]["falls"] for e in s), c)}, nofight {pct(sum(e["pw"]["flost"] == -1 for e in s), c)}, walked {pct(sum(e["pw"]["walked"] for e in s), c)}, started within 5 {pct(sum(e["pw"]["d0"] <= 5 for e in s), c)},'
                  f' allies {sum(e["al"] for e in s) / c:.1f} enemies {sum(e["en"] for e in s) / c:.1f}')
# Smaller: deaths' last traced round before death
print('\n== small, deaths within 10: the round-by-round of the encounter start that led to death (first 25)')
seen = set()
S = [e for e in E if e['role'] == 'small' and e['r'] < 600]
idx = {(e['game'], e['r']): e for e in E}
k = 0
for e in sorted(S, key=lambda e: (e['game'], e['r'])):
    if not e['die_u'] or (e['game'], e['r'] - 1) in idx: continue
    k += 1
    if k > 25: break
    seq = []
    for r in range(e['r'], e['r'] + 11):
        x = idx.get((e['game'], r))
        if not x: continue
        p = x['pw']
        seq.append(f"{r}:{x['br']}{'v' if p and p['vis'] else 'u' if p else '-'}d{x['d']}" + (f"/{p['d1']}L{p['flost']}F{p['falls']}l{p['leth1']}" if p else '') + ('*' if x['enhit'] else ''))
    print(f"  {e['game'][:8]} ratio {e['ratio']:.2f} al {e['al']} en {e['en']} hp {e['hpu']:.2f} killer {e['killer_u']}: " + ' '.join(seq))
