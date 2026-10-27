"""python3 retreat_swaps.py replays/BATCH. Swaps between an advancing state and retreat (A->B by state X, B->A by retreat): why retreat ran at B,
and whether the A->B move was checked by Advance."""
import sys, json, zipfile, collections
res = json.load(open(sys.argv[1] + "/results.json"))
c = collections.Counter(); adv = collections.Counter(); ex = collections.defaultdict(list); total = 0
for m in res['matches']:
    ours = 'team-a' if m['order'] == [0, 1] else 'team-b'
    try: z = zipfile.ZipFile(m['replay'])
    except Exception: continue
    text = z.read(ours + '.stdout').decode('latin1').replace('\0', '')
    T = {}; W = {}
    for line in text.splitlines():
        p = line.split()
        try:
            if len(p) == 11 and p[0] == 'AUD': T[(int(p[2]), int(p[1]))] = dict(s=p[3], fr=p[4], to=p[5], adv=int(p[10]))
            elif len(p) >= 17 and p[0] == 'WH': W[(int(p[2]), int(p[1]))] = dict(low=int(p[4]), pack=int(p[6]), trapped=int(p[8]), lethal=int(p[10]), seen=int(p[12]), cached=int(p[14]), hp=float(p[16]))
        except ValueError: pass
    mp = m['map'].split('/')[-1].replace('.map26a', '')
    for (i, r), a in T.items():
        b = T.get((i, r + 1))
        if not b or a['s'] == 'retreat' or b['s'] != 'retreat': continue
        if not (a['fr'] != a['to'] and b['fr'] == a['to'] and b['to'] == a['fr']): continue
        total += 1
        w = W.get((i, r + 1))
        if not w: why = 'retreat ran without leave (errand/recall keep)'
        else:
            parts = [k for k in ('low', 'pack', 'trapped') if w[k]]
            why = '+'.join(parts) if parts else ('stand lost (lethal)' if w['lethal'] else 'stand lost / willow (enemy seen)' if w['seen'] else 'other')
        wa = W.get((i, r))
        key = (a['s'], why, 'leave already true at A' if wa else '')
        c[key] += 1
        adv[(a['s'], {1: 'advance set', 0: 'NO advance', -1: 'no walk (dash/other)'}[a['adv']])] += 1
        if len(ex[key]) < 2: ex[key].append((mp, i, r, a['fr'], a['to'], w))
print('advance-then-retreat swaps', total)
for k, v in c.most_common(20): print(f'{v:6} {k}')
print('\nwas the advancing move checked by Advance?')
for k, v in adv.most_common(): print(f'{v:6} {k}')
for k, es in sorted(ex.items(), key=lambda kv: -c[kv[0]])[:6]:
    for e in es: print('  ex', k, e)
