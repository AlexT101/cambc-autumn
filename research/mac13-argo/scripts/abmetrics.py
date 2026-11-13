"""Per-bot macro metrics over an extracted A/B (extract.mjs --out DIR of the batch): win %, deaths by type a game,
pair deaths, Prism deaths, kills, captured gems @300/600, wealth race (rounds from first 1000 wealth to the end, for
the eventual winner), rich-tribute completion. Bots are named by meta.json teams[].name.
    py abmetrics.py EXTRACT_DIR [CAND_NAME]"""
import gzip, json, sys, statistics as st
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

def one(d):
    try:
        meta = json.loads((d / 'meta.json').read_text())
        R = json.load(gzip.open(d / 'rounds.json.gz'))
        ev = [json.loads(l) for l in gzip.open(d / 'events.jsonl.gz', 'rt')]
    except Exception:
        return None
    names = [meta['teams'][t]['name'] for t in (0, 1)]
    w = meta['result']['winner']; n = len(R['round']); C = R['champions']
    team = {c['id']: c['team'] for c in C}; ctype = {c['id']: c['name'] for c in meta['champions']}
    rid = {r: i for i, r in enumerate(R['round'])}
    o = {nm: defaultdict(float) for nm in names}
    for t in (0, 1):
        o[names[t]]['games'] += 1; o[names[t]]['wins'] += (t == w)
    cap = {0: Counter(), 1: Counter()}
    rich_from = [None, None]
    for i in range(n):
        for t in (0, 1):
            if rich_from[t] is None and R['gems'][t][i] + sum(c['gems'][i] for c in C if c['team'] == t and c['alive'][i]) >= 1000:
                rich_from[t] = R['round'][i]
    opn = {}
    for e in ev:
        k = e['k']
        if k == 'death':
            t = team[e['v']]; nm = names[t]
            if e.get('linked'): continue
            o[nm]['deaths'] += 1; o[nm]['d_' + ctype[e['v']]] += 1
            if ctype[e['v']] in ('Cassi', 'Issac'): o[nm]['pair_deaths'] += 1
            if e.get('by') is not None and team.get(e['by']) != t: o[names[1 - t]]['kills'] += 1
            o[nm]['bag_lost'] += e.get('gems', 0)
        elif k == 'capture':
            for cid, g, gold in e['shares']:
                t = team[cid]
                if e['r'] <= 300: o[names[t]]['cap300'] += g
                if e['r'] <= 600: o[names[t]]['cap600'] += g
                o[names[t]]['cap'] += g
        elif k == 'tribute_start' and e['gems'] >= 100:
            t = team[e['a']]
            if rich_from[t] is not None and e['r'] >= rich_from[t]:
                o[names[t]]['rich_starts'] += 1; opn[e['a']] = True
        elif k == 'tribute_end' and opn.pop(e.get('a'), False):
            o[names[team[e['a']]]]['rich_done'] += 1
        elif k == 'tribute_cancel' and opn.pop(e.get('a'), False):
            o[names[team[e['a']]]]['rich_cancel_' + str(e.get('cause'))] += 1
    for t in (0, 1):
        if rich_from[t] is not None:
            o[names[t]]['rich_games'] += 1
            o[names[t]]['rich_won'] += (t == w)
            if t == w: o[names[t]]['convert_rounds'] += meta['result']['rounds'] - rich_from[t]; o[names[t]]['convert_n'] += 1
        first = rich_from[t] is not None and (rich_from[1 - t] is None or rich_from[t] < rich_from[1 - t])
        if first: o[names[t]]['first_rich'] += 1; o[names[t]]['first_rich_won'] += (t == w)
    return {k: dict(v) for k, v in o.items()}

if __name__ == '__main__':
    root = Path(sys.argv[1]); dirs = [p for p in root.iterdir() if (p / 'meta.json').exists()]
    tot = defaultdict(lambda: defaultdict(float))
    with ProcessPoolExecutor(24) as ex:
        for r in ex.map(one, dirs, chunksize=16):
            if not r: continue
            for nm, v in r.items():
                for k, x in v.items(): tot[nm][k] += x
    for nm, v in tot.items():
        g = v['games']
        print(f"== {nm}: games {int(g)} win {100*v['wins']/g:.1f}%")
        print(f"   per game: deaths {v['deaths']/g:.2f} kills {v['kills']/g:.2f} pair deaths {v['pair_deaths']/g:.2f} Prism deaths {v['d_Prism']/g:.2f} bag lost {v['bag_lost']/g:.1f}")
        print(f"   capture gems @300 {v['cap300']/g:.1f} @600 {v['cap600']/g:.1f} all {v['cap']/g:.1f}")
        print(f"   first to 1000 wealth {int(v['first_rich'])} won {100*v['first_rich_won']/max(1,v['first_rich']):.1f}%; rich games {int(v['rich_games'])} won {100*v['rich_won']/max(1,v['rich_games']):.1f}%;"
              f" convert rounds (wins) {v['convert_rounds']/max(1,v['convert_n']):.1f}; rich tributes {v['rich_starts']/max(1,v['rich_games']):.2f}/game, {100*v['rich_done']/max(1,v['rich_starts']):.1f}% done;"
              f" cancels stun {v['rich_cancel_stun']/max(1,v['rich_games']):.2f} manual {v['rich_cancel_manual']/max(1,v['rich_games']):.2f} lock {v['rich_cancel_lock']/max(1,v['rich_games']):.2f}")
        print('   deaths by type /game', {k[2:]: round(x/g, 2) for k, x in sorted(v.items()) if k.startswith('d_')})
