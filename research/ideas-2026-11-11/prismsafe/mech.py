"""Winning-bag mechanism metrics from extracted replays (tools/replay/extract.mjs --out DIR).

    python3 mech.py EXTROOT TAG [TAG ...]      # EXTROOT/TAG holds one bot's extracted games against the rt bodies

A winning bag: our Prism alive with gems + our tributed score >= 1000. Per game: whether one arose, the round it
first did (W), whether the Prism died carrying one (the bag lost: a kill hands it over, a camp kill destroys it), the
Prism's health share at W, the enemy's score at W, whether the enemy drafted a Prism, the game's end and result.
The first TAG is the reference: games are paired by (opponent, map, side) and the rest are read against it.
"""
import gzip, json, os, sys, collections
from multiprocessing import Pool


def one(d):
    try:
        meta = json.load(open(os.path.join(d, 'meta.json')))
        R = json.load(gzip.open(os.path.join(d, 'rounds.json.gz')))
        ev = [json.loads(l) for l in gzip.open(os.path.join(d, 'events.jsonl.gz'), 'rt')]
    except Exception:
        return None
    names = [t['name'] for t in meta['teams']]
    us = 0 if not names[0].startswith('rt-') else 1
    src = os.path.basename(meta['source']); bdir = os.path.basename(os.path.dirname(meta['source']))
    opp = 'Flp4' if 'Flp4' in bdir else 'Mt3q'
    stem = src.rsplit('.', 1)[0]; mp, side = stem.split('-', 1)[1].rsplit('-', 1)
    picks = meta['draft']['picks']
    res = meta['result']; win = res['winner'] == us; end = res['rounds']
    ch = {c['id']: c for c in R['champions']}
    team = {c['id']: c['team'] for c in meta['champions']}; typ = {c['id']: c['name'] for c in meta['champions']}
    prisms = [c for c in ch if typ[c] == 'Prism' and team[c] == us]
    row = dict(key=(opp, mp, side), opp=opp, win=win, end=end, prism='Prism' in picks[us], eprism='Prism' in picks[1 - us],
               W=None, lost=0, lost_gems=0, hp=None, them=None, them_rate=None, deaths_big=0)
    S = R['gems']
    rounds = R['round']
    idx = {r: i for i, r in enumerate(rounds)}
    for e in ev:
        if e['k'] == 'death' and e['v'] in prisms and e.get('gems', 0) >= 40:
            row['deaths_big'] += 1
    for p in prisms:
        P = ch[p]
        for i, r in enumerate(rounds):
            if P['alive'][i] and P['gems'][i] + S[us][i] >= 1000 and S[us][i] < 1000:
                if row['W'] is None:
                    row['W'] = r; row['hp'] = P['hp'][i] / max(1, P['maxHp'][i]); row['them'] = S[1 - us][i]
                    j = idx.get(max(1, r // 2), 0)
                    row['them_rate'] = (S[1 - us][i] - S[1 - us][j]) / max(1, r - rounds[j])
                break
    if row['W'] is not None:
        for e in ev:
            if e['k'] == 'death' and e['v'] in prisms and e['r'] >= row['W']:
                i = idx.get(e['r'] - 1, idx.get(e['r'], 0))
                if e.get('gems', 0) + S[us][i] >= 1000:
                    row['lost'] += 1; row['lost_gems'] += e.get('gems', 0)
    return row


def load(root):
    dirs = [os.path.join(root, x) for x in os.listdir(root) if os.path.isfile(os.path.join(root, x, 'meta.json'))]
    with Pool(16) as pool:
        rows = [r for r in pool.map(one, dirs, chunksize=8) if r]
    return {r['key']: r for r in rows}


def summary(tag, rows):
    n = len(rows); wb = [r for r in rows if r['W'] is not None]
    lost = [r for r in wb if r['lost']]
    print(f'{tag}: {n} games, win {100 * sum(r["win"] for r in rows) / n:.2f}%, Prism games {sum(r["prism"] for r in rows)}, '
          f'big-bag (40+) Prism deaths {sum(r["deaths_big"] for r in rows) / max(1, sum(r["prism"] for r in rows)):.3f} a Prism game')
    if not wb: return
    print(f'  winning bag in {len(wb)} games ({100 * len(wb) / n:.1f}%); lost carrying it in {len(lost)} '
          f'({100 * len(lost) / len(wb):.1f}% of them), {sum(r["lost"] for r in wb)} deaths; those games won {sum(r["win"] for r in lost)}')
    won = [r for r in wb if r['win']]
    print(f'  games with a winning bag won {100 * len(won) / len(wb):.1f}%; mean rounds from W to the end in wins '
          f'{sum(r["end"] - r["W"] for r in won) / max(1, len(won)):.1f}')
    for name, f in [('enemy Prism', lambda r: r['eprism']), ('no enemy Prism', lambda r: not r['eprism'])]:
        s = [r for r in wb if f(r)]
        if s: print(f'    {name}: {len(s)} games, lost {sum(1 for r in s if r["lost"])} ({100 * sum(1 for r in s if r["lost"]) / len(s):.1f}%), won {100 * sum(r["win"] for r in s) / len(s):.1f}%')
    for lo, hi in [(0, .5), (.5, .8), (.8, 1.01)]:
        s = [r for r in wb if lo <= r['hp'] < hi]
        if s: print(f'    health at W {lo:.1f}-{hi:.1f}: {len(s)} games, lost {sum(1 for r in s if r["lost"])} ({100 * sum(1 for r in s if r["lost"]) / len(s):.1f}%), won {100 * sum(r["win"] for r in s) / len(s):.1f}%')
    for lo, hi in [(0, 500), (500, 800), (800, 1000)]:
        s = [r for r in wb if lo <= r['them'] < hi]
        if s: print(f'    enemy score at W {lo}-{hi}: {len(s)} games, lost {sum(1 for r in s if r["lost"])} ({100 * sum(1 for r in s if r["lost"]) / len(s):.1f}%), won {100 * sum(r["win"] for r in s) / len(s):.1f}%')


def main():
    root, tags = sys.argv[1], sys.argv[2:]
    data = {t: load(os.path.join(root, t)) for t in tags}
    for t in tags: summary(t, list(data[t].values()))
    ref = data[tags[0]]
    for t in tags[1:]:
        both = [k for k in data[t] if k in ref]
        ch = [k for k in both if (data[t][k]['win'], data[t][k]['end']) != (ref[k]['win'], ref[k]['end'])]
        d = sum(data[t][k]['win'] - ref[k]['win'] for k in both)
        print(f'{t} against {tags[0]}: {len(both)} paired games, {len(ch)} changed ({100 * len(ch) / max(1, len(both)):.1f}%), '
              f'net wins {d:+d} ({100 * d / max(1, len(both)):+.2f} points)')
        wb = [k for k in both if ref[k]['W'] is not None]
        lr = sum(1 for k in wb if ref[k]['lost']); lc = sum(1 for k in wb if data[t][k]['lost'])
        dt = [data[t][k]['end'] - ref[k]['end'] for k in wb if ref[k]['win'] and data[t][k]['win']]
        print(f'  REF winning-bag games {len(wb)}: bag lost REF {lr}, CAND {lc}; both won {len(dt)}, mean end round change '
              f'{sum(dt) / max(1, len(dt)):+.1f}; net wins there {sum(data[t][k]["win"] - ref[k]["win"] for k in wb):+d}')
        flips = collections.Counter((ref[k]['win'], data[t][k]['win']) for k in ch)
        print(f'  changed games by (REF won, CAND won): {dict(flips)}; with a REF winning bag {sum(1 for k in ch if ref[k]["W"] is not None)}')
        if os.environ.get('FLIPS'):
            for k in ch:
                if ref[k]['win'] != data[t][k]['win']:
                    r, c = ref[k], data[t][k]
                    print(f'    {k} REF win={r["win"]} end={r["end"]} W={r["W"]} lost={r["lost"]} | CAND win={c["win"]} end={c["end"]} W={c["W"]} lost={c["lost"]}')
        for o in ('Flp4', 'Mt3q'):
            b = [k for k in both if k[0] == o]
            print(f'    {o}: {len(b)} games, net {sum(data[t][k]["win"] - ref[k]["win"] for k in b):+d}')


if __name__ == '__main__':
    main()
