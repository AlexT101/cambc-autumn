"""Farm target switches (FG lines) over a batch, by why the old target lost, and which were stepped back from at once.
    python3 farm_switches.py replays/BATCH VARIANT   (VARIANT: the instrument.py copy, for its line numbers)"""
import sys, json, zipfile, re, collections
batch = sys.argv[1]
src = open(f"bots/variants/{sys.argv[2] if len(sys.argv) > 2 else 'aud'}/src/champions/shared/farm.inl").read().splitlines()
L = {}; cur = None
for line in src:
    m = re.match(r'#line (\d+) ', line)
    if m: cur = int(m.group(1)); continue
    if cur is not None: L[cur] = line.strip(); cur += 1
def skip_text(n):
    t = L.get(n, '?')
    t = re.sub(r'\{ debug_block.*', '', t).strip()
    return t[:70] or L.get(n - 1, '?').strip()[:70]
res = json.load(open(batch + "/results.json"))
cat = collections.Counter(); cyc = collections.Counter(); ex = collections.defaultdict(list); n = 0
for m in res['matches']:
    ours = 'team-a' if m['order'] == [0, 1] else 'team-b'
    try: z = zipfile.ZipFile(m['replay'])
    except Exception: continue
    text = z.read(ours + '.stdout').decode('latin1').replace('\0', '')
    aud = {}
    for line in text.splitlines():
        p = line.split()
        if len(p) in (10, 11) and p[0] == 'AUD':
            try: aud[(int(p[2]), int(p[1]))] = (p[3], p[4], p[5])
            except ValueError: pass
    mp = m['map'].split('/')[-1].replace('.map26a', '')
    for line in text.splitlines():
        if not line.startswith('FG '): continue
        g = re.match(r'FG (\d+) (\d+) (-?\d+) (-?\d+) (-?\d+) (-?\d+) (-?\d+) \| prev l(\d+) r(-?\d+) v(-?[0-9.]+) d(-?[0-9.]+) s(-?[0-9.]+) p(-?[0-9.]+) e(\d) c(\d) st(-?\d+) \| was r(-?\d+) v(-?[0-9.]+) d(-?[0-9.]+) s(-?[0-9.]+) p(-?[0-9.]+) e(\d) c(\d) st(-?\d+) \| new r(-?\d+) v(-?[0-9.]+) st(-?\d+) c(\d) was_new l(-?\d+) \| hp (-?[0-9.]+) (-?[0-9.]+) rl (-?[0-9.]+) (-?[0-9.]+)', line)
        if not g: continue
        n += 1
        r, i, old, new, pick, shared, helpg = map(int, g.groups()[:7])
        line_no, risky_now = int(g.group(8)), int(g.group(9))
        was_risky = int(g.group(17)); was_claimed, now_claimed = int(g.group(23)), int(g.group(15))
        s_was, s_now = float(g.group(20)), float(g.group(12))
        rl0, rl1 = float(g.group(32)), float(g.group(33)); hp0, hp1 = float(g.group(30)), float(g.group(31))
        st_was, st_now = int(g.group(24)), int(g.group(16))
        if helpg >= 0 and new == helpg: why = 'help override'
        elif shared >= 0 and new == shared and pick == -2: why = 'crew (shared) override'
        elif line_no:
            why = 'old target skipped: ' + skip_text(line_no)
        elif risky_now == 1 and was_risky == 0:
            why = 'old target turned RISKY: ' + ('recall line rose %.2f->%.2f' % (rl0, rl1) if rl1 > rl0 else 'hp fell' if hp1 < hp0 else 'damage/partner/engaged changed')
        elif risky_now == 0 and was_risky == 1: why = 'old target turned safe (risky fallback lost)'
        elif was_claimed != now_claimed: why = 'old target claim status changed'
        else:
            why = 'value: old ' + ('fell' if float(g.group(10)) < float(g.group(18)) else 'rose') + ', another beat it'
        moved = aud.get((i, r - 1)); back = aud.get((i, r))
        is_cycle = bool(moved and back and moved[1] != moved[2] and back[2] == moved[1])
        cat[why] += 1
        if is_cycle: cyc[why] += 1
        if len(ex[why]) < 3: ex[why].append((mp, i, r, old, new, f'steps {st_was}->{st_now}', f'spare {s_was:.0f}->{s_now:.0f}', f'rl {rl0}->{rl1}', 'cycle' if is_cycle else ''))
print('farm target switches', n, ' of which an immediate step back', sum(cyc.values()))
for k, v in cat.most_common(): print(f'{v:6} {cyc[k]:6}  {k}')
print()
for k, es in sorted(ex.items(), key=lambda kv: -cat[kv[0]])[:10]:
    for e in es[:2]: print('  ex', k[:50], e)
# second pass: the new target's status on the previous turn, for value switches
print('\n== value switches: how the new target fared last turn')
wn = collections.Counter()
for m in res['matches']:
    ours = 'team-a' if m['order'] == [0, 1] else 'team-b'
    try: z = zipfile.ZipFile(m['replay'])
    except Exception: continue
    text = z.read(ours + '.stdout').decode('latin1').replace('\0', '')
    for line in text.splitlines():
        if not line.startswith('FG '): continue
        g = re.match(r'FG (\d+) (\d+) (-?\d+) (-?\d+) (-?\d+) (-?\d+) (-?\d+) \| prev l(\d+) r(-?\d+) v(-?[0-9.]+) .* \| was r(-?\d+) v(-?[0-9.]+) .* \| new r(-?\d+) v(-?[0-9.]+) st(-?\d+) c(\d) was_new l(-?\d+)', line)
        if not g: continue
        r, i, old, new, pick, shared, helpg = map(int, g.groups()[:7])
        if int(g.group(8)) or (helpg >= 0 and new == helpg) or (shared >= 0 and new == shared and pick == -2): continue
        if int(g.group(9)) != 0 or int(g.group(11)) != 0: continue
        vold_now, vold_was, vnew = float(g.group(10)), float(g.group(12)), float(g.group(14))
        l = int(g.group(17))
        status = 'scored safe last turn' if l == -1 else 'scored risky last turn' if l == -2 else 'no record (not farming last turn?)' if l == -9 else 'skipped last turn: ' + skip_text(l)
        wn[('old rose' if vold_now >= vold_was else 'old fell', status)] += 1
for k, v in wn.most_common(14): print(f'{v:6} {k}')
