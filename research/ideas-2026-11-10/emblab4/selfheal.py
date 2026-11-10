"""Does the base policy heal a single forced deviation? For every dense-lab decision whose base arm is a passive
family F (the table's or the current logic's) and whose drawn arm is another family, whether the champion owns F
one, two and three emblems later anyway, against champions that took the base there.
    py selfheal.py LAB BATCH[,BATCH...]"""
import json, subprocess, sys, collections
lab, batches = sys.argv[1], sys.argv[2].split(',')
F = ["monster","power","durability","treasure","jungle","home","bruiser","tribute","capture","prospector","hunter","skirmish","greed","collectors"]
PASSIVE = {f for f in range(14) if F[f] not in ("power", "bruiser", "greed")}
champs = collections.defaultdict(dict)   # (id, team, type) -> k -> (base family, chosen family, owned set)
for b in batches:
    p = subprocess.Popen(['zstd', '-dc', f'replays/emblab/{lab}/decisions/b{int(b):03d}.jsonl.zst'], stdout=subprocess.PIPE, text=True)
    for l in p.stdout:
        d = json.loads(l)
        v = d['v']
        owned = frozenset(f for f in PASSIVE if v[3 * f] is None and v[3 * f + 1] is None and v[3 * f + 2] is None)
        champs[(d['id'], d['team'], d['type'])].setdefault(d['k'], (d['base'] // 3, d['chosen'] // 3, owned))
acc = collections.defaultdict(lambda: [[0, 0] for _ in range(8)])   # (family, took base?) -> per lag [owned, reached]
for seq in champs.values():
    for k, (bf, cf, owned) in seq.items():
        if bf not in PASSIVE or bf in owned or k < 0:
            continue
        for grp in ((F[bf], bf == cf), ('ALL passive', bf == cf), (F[bf] + (' k>=3' if k >= 3 else ' k<3'), bf == cf)):
            a = acc[grp]
            for lag in range(1, 5):
                nxt = seq.get(k + lag)
                if nxt is not None:
                    a[lag][1] += 1
                    a[lag][0] += bf in nxt[2]
            last = seq[max(seq)]
            if max(seq) > k:
                a[5][1] += 1; a[5][0] += bf in last[2]
print("base family F at a decision; owns F by the champion's next / 2nd / 3rd / 4th later decision, and by its last logged one")
for name in ['ALL passive', 'collectors', 'collectors k>=3', 'home', 'tribute', 'prospector', 'prospector k<3', 'capture', 'treasure', 'monster', 'jungle', 'durability', 'hunter', 'skirmish']:
    for took in (True, False):
        a = acc.get((name, took))
        if not a or a[1][1] < 200: continue
        print(f"  {name:16s} {'took the base ' if took else 'drawn away   '} n {a[1][1]:8d}: " + ' '.join(f"{100*a[l][0]/max(1,a[l][1]):5.1f}%" for l in (1, 2, 3, 4)) + f"   last {100*a[5][0]/max(1,a[5][1]):5.1f}%")
